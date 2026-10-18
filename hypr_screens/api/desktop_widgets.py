"""Desktop widgets: their settings by schema, layouts, arranging on the desktop."""
import time

from hypr_screens import config, hypr, widget_schema
from hypr_screens import widgets as widgets_mod
from hypr_screens.api.core import ApiError, endpoint, need, settings, changing

ARRANGE_TRIES, ARRANGE_PAUSE = 20, 0.25


def known_kind(kind: object) -> str:
    need(widget_schema.known_kind(kind), "unknown_widget", f"unknown widget: {kind!r}")
    return kind


@endpoint
def widgets() -> list[dict]:
    """Every widget: on or off, its content and where it shows, with the schema
    of what can be set here (no look: that is set on the desktop)."""
    cfg = settings()
    return [widget_schema.view(kind, cfg["widgets"][kind], cfg) for kind in widgets_mod.KINDS]


@endpoint
def update_widget(kind: str, changes: dict) -> dict:
    """changes: {"enabled": bool, "content": {key: value}, "where": {key: value}},
    each part optional and partial; checked against the widget's schema."""
    kind = known_kind(kind)
    need(isinstance(changes, dict), "bad_value", "changes must be an object")
    extra = sorted(set(changes) - {"enabled", "content", "where"})
    need(not extra, "bad_value", f"only enabled, content and where can be changed here, not {extra}")
    cfg = settings()
    updates = []
    for group in ("content", "where"):
        part = changes.get(group) or {}
        need(isinstance(part, dict), "bad_value", f"{group} must be an object")
        for key, value in part.items():
            try:
                updates.append(widget_schema.check(kind, group, key, value, cfg))
            except widget_schema.Invalid as error:
                raise ApiError("bad_value", str(error)) from None
    enabled = changes.get("enabled")
    need(enabled is None or isinstance(enabled, bool), "bad_value", "enabled must be true or false")

    def mutate(fresh):
        widget = fresh["widgets"][kind]
        if enabled is not None:
            if enabled and not widget["enabled"] and not widget["placed"]:
                widget.update(widgets_mod.CENTER)  # first time: in the middle, to be dragged from there
            widget["enabled"] = enabled
        for key, value in updates:
            widget[key] = value
        fresh["widgets"] = widgets_mod.normalize(fresh["widgets"])
    cfg = config.update(mutate)
    widgets_mod.apply(cfg)
    return widget_schema.view(kind, cfg["widgets"][kind], cfg)


@endpoint
def install_cava() -> dict:
    """The visualizer needs the program cava (installed with the password)."""
    if not widgets_mod.has_cava():
        need(widgets_mod.install_cava(graphical=True) and widgets_mod.has_cava(), "cancelled",
             "installing cava was cancelled or failed")
        widgets_mod.apply(settings())
        widgets_mod.shell_ipc("reload")
    cfg = settings()
    return widget_schema.view("visualizer", cfg["widgets"]["visualizer"], cfg)


def layouts_view(cfg: dict) -> dict:
    connected = sorted(config.connected(hypr.monitors()))
    names = {sid: screen.get("name", sid) for sid, screen in cfg["screens"].items()}
    current = next((layout["name"] for layout in cfg["widget_layouts"]
                    if widgets_mod.normalize(layout["widgets"]) == cfg["widgets"]), None)
    return {
        "current": current,
        "items": [layout["name"] for layout in cfg["widget_layouts"]],
        "layouts": [{"name": layout["name"], "screens": layout["screens"],
                     "screenNames": [names.get(sid, sid) for sid in layout["screens"]],
                     "auto": bool(layout["screens"]), "matchesNow": bool(layout["screens"])
                     and layout["screens"] == connected} for layout in cfg["widget_layouts"]],
        "connected": connected,
    }


def layout_name(name: object) -> str:
    need(isinstance(name, str) and name.strip(), "bad_value", "a layout needs a name")
    return name.strip()[:60]


def known_layout(cfg: dict, name: object) -> str:
    need(isinstance(name, str) and any(layout["name"] == name for layout in cfg["widget_layouts"]),
         "unknown_layout", f"no layout called {name!r}")
    return name


@endpoint
def layouts() -> dict:
    return layouts_view(settings())


@endpoint
def save_layout(name: str) -> dict:
    """Keeps all widgets as they are now under this name (replacing one of that name)."""
    name = layout_name(name)
    cfg = settings()
    need(any(layout["name"] == name for layout in cfg["widget_layouts"])
         or len(cfg["widget_layouts"]) < widgets_mod.MAX_LAYOUTS, "bad_value",
         f"there are {widgets_mod.MAX_LAYOUTS} layouts already; delete one first")
    return layouts_view(config.update(changing(widgets_mod.save_layout, name)))


@endpoint
def load_layout(name: str) -> dict:
    """The layout's widgets, live at once; "previous" holds the widgets as they
    were (saved or not), for restore_widgets() to undo the load."""
    before = settings()
    known_layout(before, name)
    cfg = config.update(changing(widgets_mod.load_layout, name))
    widgets_mod.apply(cfg)
    return {**layouts_view(cfg), "previous": widgets_mod.normalize(before["widgets"])}


@endpoint
def restore_widgets(previous: dict) -> dict:
    """Undoes load_layout(): all widgets back as in its "previous"."""
    need(isinstance(previous, dict) and bool(previous), "bad_value", "previous must be the widgets from load_layout")

    def mutate(cfg: dict) -> None:
        cfg["widgets"] = widgets_mod.normalize(previous)
    cfg = config.update(mutate)
    widgets_mod.apply(cfg)
    return layouts_view(cfg)


@endpoint
def delete_layout(name: str) -> dict:
    known_layout(settings(), name)
    return layouts_view(config.update(changing(widgets_mod.delete_layout, name)))


@endpoint
def rename_layout(name: str, new_name: str) -> dict:
    cfg = settings()
    known_layout(cfg, name)
    new_name = layout_name(new_name)
    if new_name == name:
        return layouts_view(cfg)
    need(not any(layout["name"] == new_name for layout in cfg["widget_layouts"]), "conflict",
         f"there is a layout called {new_name!r} already")
    return layouts_view(config.update(changing(widgets_mod.rename_layout, name, new_name)))


@endpoint
def set_layout_auto(name: str, on: bool) -> dict:
    """On: the layout loads by itself whenever exactly the screens connected now
    are (another layout with those screens gives them up). Off: only by hand."""
    known_layout(settings(), name)
    need(isinstance(on, bool), "bad_value", "on must be true or false")
    connected = sorted(config.connected(hypr.monitors())) if on else []
    return layouts_view(config.update(changing(widgets_mod.set_layout_screens, name, connected)))


@endpoint
def arrange_widgets() -> dict:
    """Starts arranging on the desktop (drag, resize, turn, colors); the overlay
    saves by itself (`tuneup widgets save`)."""
    cfg = settings()
    need(any(widgets_mod.on_desktop(cfg["widgets"][kind], kind) for kind in widgets_mod.KINDS), "nothing_to_arrange",
         "switch a widget on first")
    for _ in range(ARRANGE_TRIES):  # a plugin that was just switched on needs a moment
        if widgets_mod.start_editing():
            return {"ok": True}
        time.sleep(ARRANGE_PAUSE)
    raise ApiError("not_ready", "the widgets are not ready yet – try again in a moment")
