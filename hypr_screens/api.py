"""The backend of the HTML settings window (hypr_screens/web/).

The page calls `window.api.someMethod(a, b)`; the WebKit bridge turns that
into `some_method(a, b)` here (camelCase -> snake_case, positional JSON
arguments, the return value as JSON). `call(name, args)` does exactly that,
for the bridge. An ApiError rejects the page's promise with {code, message};
every endpoint turns any other exception into ApiError("internal", ...).

Each change goes the way the old GTK window did it: the settings through
config.update() (locked, atomic, never over an unreadable file), then what
makes it live -- engine.sync() for screens, the Lua file and go_live for
keys, widgets.apply() for widgets, look.apply() for the window look.

The shapes, the error codes and where they differ from the old mock are in
hypr_screens/web/API.md; web/mock.js returns the same shapes.
"""
import base64
import copy
import functools
import inspect
import re
import subprocess
import time
from pathlib import Path

from hypr_screens import apply, config, desktops, engine, hypr, i18n, install, keybinds, sound, widget_schema
# Aliased: the page's methods camera(), look(), samsung(), widgets() and theme() take the plain names.
from hypr_screens import camera as camera_mod
from hypr_screens import look as look_mod
from hypr_screens import samsung as samsung_mod
from hypr_screens import theme as theme_mod
from hypr_screens import widgets as widgets_mod

DOCS_URL = "https://github.com/SlowlyTz/hypr-minimizer/tree/master/docs"
TRANSFORM_DEGREES = {0: 0, 1: 90, 2: 180, 3: 270}
MODE_PATTERN = re.compile(r"^\d{2,5}x\d{2,5}(@\d{1,3}(\.\d{1,3})?)?$")
SCALE_RANGE = (0.25, 4)
ARRANGE_TRIES, ARRANGE_PAUSE = 20, 0.25
RESET_SETTLE_SECONDS = 0.8
PREVIEW_FRESH_SECONDS = 3.0
# Shortcut actions as the settings window names them (English i18n source texts).
ACTION_TITLES = {
    "minimizer_menu": "Open window list",
    "stash": "Hide window",
    "stash_others": "Hide all others",
    "pop": "Bring back last",
    "pop_all": "Bring back all",
    "undo": "Undo",
}
ACTION_HELP = {
    "minimizer_menu": "Opens the list of minimized windows (there: Enter, Shift+Enter, “-” to peek).",
    "stash": "Hides the active window.",
    "stash_others": "Hides all other windows on this desktop.",
    "pop": "Brings back the window hidden last.",
    "pop_all": "Brings back all hidden windows of this desktop.",
    "undo": "Undoes the last hiding or bringing back.",
}
DEFAULT_FIXED_LABELS = {"off": "Off – both screens have desktops", "external": "The external monitor",
                        "panel": "The laptop"}
SOUND_ICONS = {"audio-input-microphone-symbolic": "mic", "audio-headphones-symbolic": "headphones",
               "video-display-symbolic": "tv", "audio-speakers-symbolic": "speaker"}
# The window look: config key -> the page's key.
LOOK_KEYS = {"gaps_in": "gapsIn", "gaps_out": "gapsOut", "rounding": "rounding", "border_size": "border",
             "blur": "blur", "blur_size": "blurSize", "blur_passes": "blurPasses",
             "active_opacity": "activeOpacity", "inactive_opacity": "inactiveOpacity",
             "anim_speed": "animSpeed", "border_colors": "borderColors", "border_angle": "borderAngle",
             "apps": "apps"}
LOOK_FROM_JS = {js: key for key, js in LOOK_KEYS.items()}
SAMSUNG_ATTRIBUTES = {"usbCharging": "usb_charging", "lidPower": "power_on_lid_open"}


class ApiError(Exception):
    """Rejects the page's promise with {code, message}. Codes are stable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_json(self) -> dict:
        return {"code": self.code, "message": self.message}


METHODS: dict = {}


def endpoint(function):
    """A method the page can call: wrong arguments and any failure become ApiError."""
    signature = inspect.signature(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            signature.bind(*args, **kwargs)
        except TypeError as error:
            raise ApiError("bad_args", f"{function.__name__}: {error}") from None
        try:
            return function(*args, **kwargs)
        except ApiError:
            raise
        except config.ConfigError as error:
            raise ApiError("config_unreadable", f"{error}. Fix or remove the file; nothing was saved.") from error
        except samsung_mod.NotSetUp as error:
            raise ApiError("not_set_up", str(error)) from error
        except ValueError as error:
            raise ApiError("bad_value", str(error)) from error
        except Exception as error:  # never let a raw exception reach the page
            raise ApiError("internal", f"{type(error).__name__}: {error}") from error

    METHODS[function.__name__] = wrapper
    return wrapper


def snake_case(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def call(method: str, args: list | None = None) -> object:
    """For the bridge: `api.call("setScreenSetting", [...])`."""
    function = METHODS.get(snake_case(str(method)))
    if function is None:
        raise ApiError("unknown_method", f"no such method: {method}")
    return function(*(args or []))


# --- helpers ---------------------------------------------------------------------------


def settings() -> dict:
    """The settings, strictly (an unreadable file is an error, not the defaults)."""
    return config.read()


def recorded() -> tuple[dict, list[dict]]:
    """The settings with every connected monitor recorded, and all monitors."""
    monitors = hypr.monitors(include_disabled=True)
    return config.update(lambda cfg: config.record(cfg, monitors)), monitors


def changing(function, *args):
    """A config.update() mutation from a backend helper `function(cfg, *args)`."""
    def mutate(cfg: dict) -> None:
        function(cfg, *args)
    return mutate


def need(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ApiError(code, message)


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def run_sync() -> list[str]:
    try:
        return engine.sync()
    except Exception as error:
        raise ApiError("apply_failed", f"Saved, but applying it failed: {error}") from error


def open_uri(uri: str) -> None:
    try:
        subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as error:
        raise ApiError("unavailable", f"cannot open {uri}: {error}") from error


# --- screens ---------------------------------------------------------------------------


def mode_groups(modes: list[str]) -> list[dict]:
    """"2560x1440@59.95", ... -> [{w, h, rates (highest first), modes, preferred}]; the
    first mode Hyprland lists is the screen's preferred one."""
    groups: dict[tuple[int, int], dict] = {}
    for mode in modes:
        size = apply.parse_size(mode)
        if size is None:
            continue
        group = groups.setdefault(size, {"w": size[0], "h": size[1], "rates": [], "modes": [],
                                         "preferred": not groups})
        try:
            rate = round(float(mode.partition("@")[2]), 3)
        except ValueError:
            continue
        if rate not in group["rates"]:
            group["rates"].append(rate)
            group["modes"].append(mode)
    for group in groups.values():
        pairs = sorted(zip(group["rates"], group["modes"]), reverse=True)
        group["rates"], group["modes"] = [r for r, _m in pairs], [m for _r, m in pairs]
    return list(groups.values())


def live_values(monitor: dict, fixed_id: str | None, sid: str) -> dict:
    """What Hyprland uses for the screen right now."""
    transform = int(monitor.get("transform") or 0)
    rate = float(monitor.get("refreshRate") or 0)
    return {
        "rotation": TRANSFORM_DEGREES[transform % 4],
        "flipped": transform >= 4,
        "scale": round(float(monitor.get("scale") or 1), 4),
        "mode": f"{monitor.get('width')}x{monitor.get('height')}@{rate:.2f}",
        "one_desktop": fixed_id == sid,
    }


def live_position(monitor: dict) -> dict:
    width, height = apply.logical_size(monitor, {})
    return {"x": int(monitor.get("x") or 0), "y": int(monitor.get("y") or 0), "w": width, "h": height}


def setting_view(cfg: dict, sid: str, key: str, connected_ids: set[str]) -> dict:
    setting = config.get_setting(cfg, sid, key)
    if setting is None:
        return {"value": None, "when": [], "active": False}
    when = setting.get("when")
    return {"value": setting.get("value"), "when": [when] if when else [],
            "active": config.active_value(cfg, sid, key, connected_ids) is not None}


def fixed_view(cfg: dict) -> dict:
    status = desktops.status(cfg)
    role = status.get("fixed")
    panel, external = status.get("panel_id"), status.get("external_id")
    fixed = panel if role == "panel" else external if role == "external" else None
    desk = (external if role == "panel" else panel) if role else None
    return {"fixed": fixed, "desk": desk, "role": role, "swapped": bool(status.get("swapped")),
            "panel": panel, "external": external, "canSwap": bool(status.get("external")),
            "fixedWorkspace": status.get("fixed_workspace")}


def screen_view(cfg: dict, sid: str, live: dict[str, dict], fixed_id: str | None) -> dict:
    screen = cfg["screens"][sid]
    internal = bool(screen.get("internal"))
    monitor = live.get(sid)
    ids = set(live)
    keys = [key for key in config.SETTING_KEYS if not (internal and key == "position")]
    position = config.get_setting(cfg, sid, "position") if not internal else None
    return {
        "id": sid,
        "name": screen.get("name", sid),
        "description": screen.get("description", ""),
        "connector": screen.get("connector", ""),
        "laptop": internal,
        "connected": monitor is not None,
        "favorite": bool(screen.get("favorite")),
        "lastSeen": screen.get("last_seen"),
        "modes": mode_groups(screen.get("modes") or []),
        "hypr": live_values(monitor, fixed_id, sid) if monitor else None,
        "settings": {key: setting_view(cfg, sid, key, ids) for key in keys},
        "position": live_position(monitor) if monitor else None,
        "side": (position or {}).get("value"),
        "summary": config.summary(cfg, sid),
    }


def screen_order(cfg: dict, live: dict) -> list[str]:
    def order(sid):
        screen = cfg["screens"][sid]
        section = 0 if screen.get("internal") else 1 if screen.get("favorite") else 2
        return section, sid not in live, screen.get("name", "")
    return sorted(cfg["screens"], key=order)


def one_screen(sid: str, cfg: dict | None = None) -> dict:
    if cfg is None:
        cfg = settings()
    monitors = hypr.monitors(include_disabled=True)
    live = config.connected(monitors)
    return screen_view(cfg, sid, live, fixed_view(cfg)["fixed"])


@endpoint
def screens() -> list[dict]:
    """Every known screen: connected ones (recorded first) and the remembered ones."""
    cfg, monitors = recorded()
    live = config.connected(monitors)
    fixed_id = fixed_view(cfg)["fixed"]
    return [screen_view(cfg, sid, live, fixed_id) for sid in screen_order(cfg, live)]


def known_screen(cfg: dict, sid: object) -> str:
    need(isinstance(sid, str) and sid in cfg["screens"], "unknown_screen", f"unknown screen: {sid!r}")
    return sid


def condition(cfg: dict, sid: str, when: object) -> str | None:
    """[] -> always (None), [other] or "other" -> only while that screen is connected."""
    if isinstance(when, list):
        need(len(when) <= 1, "bad_value", "a setting can only depend on one other screen")
        when = when[0] if when else None
    if when in (None, ""):
        return None
    need(isinstance(when, str) and when in cfg["screens"] and when != sid, "bad_value",
         f"when must name another known screen, not {when!r}")
    return when


def clean_value(cfg: dict, sid: str, key: str, value: object) -> object:
    if value is None:
        return None
    if key == "rotation":
        need(value in config.ROTATIONS and not isinstance(value, bool), "bad_value",
             f"rotation must be one of {config.ROTATIONS}")
        return int(value)
    if key == "scale":
        if value == "auto":
            return value
        need(is_number(value) and SCALE_RANGE[0] <= value <= SCALE_RANGE[1], "bad_value",
             "scale must be \"auto\" or a number from 0.25 to 4")
        return value
    if key == "mode":
        need(isinstance(value, str) and (value == "preferred" or MODE_PATTERN.match(value)), "bad_value",
             "mode must be \"preferred\" or like \"2560x1440@59.95\"")
        return value
    if key == "position":
        need(not cfg["screens"][sid].get("internal"), "bad_value",
             "the laptop stays where it is; place the other screen next to it")
        need(value in config.POSITIONS, "bad_value", f"position must be one of {config.POSITIONS} or {{x, y}}")
        return value
    need(isinstance(value, bool), "bad_value", "one_desktop must be true, false or null")
    return value


def side_of(rect: tuple, anchor: tuple) -> str:
    """Which side of `anchor` the rectangle (x, y, w, h) is on, by their middles."""
    x, y, w, h = rect
    ax, ay, aw, ah = anchor
    dx = ((x + w / 2) - (ax + aw / 2)) / max(1, (w + aw) / 2)
    dy = ((y + h / 2) - (ay + ah / 2)) / max(1, (h + ah) / 2)
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "below" if dy > 0 else "above"


OPPOSITE = {"left": "right", "right": "left", "above": "below", "below": "above"}


def side_from_point(cfg: dict, sid: str, point: dict, monitors: list[dict]) -> tuple[str, str]:
    """A dragged screen's top-left corner {x, y} (layout coordinates, as in
    `position`) -> (the screen whose side to set, the side). apply.layout then
    puts it edge to edge with the laptop (the anchor), centred along that edge.
    Dragging the laptop itself sets the side of the one other screen."""
    need(is_number(point.get("x")) and is_number(point.get("y")), "bad_value", "position needs numbers x and y")
    live = config.connected(monitors)
    need(sid in live, "not_connected", "only a connected screen can be dragged; pick a side instead")
    internal = [other for other, monitor in live.items() if config.is_internal(monitor)]
    others = sorted((other for other in live if other != sid), key=lambda other: str(live[other].get("name")))
    anchor = internal[0] if internal else (others[0] if others else None)
    need(anchor is not None, "bad_value", "there is no other screen to place it next to")

    def rect(other: str, at: dict | None = None) -> tuple:
        place = at or live_position(live[other])
        return (place["x"], place["y"], *apply.logical_size(live[other], {}))
    if anchor != sid:
        return sid, side_of(rect(sid, point), rect(anchor))
    need(len(others) == 1, "bad_value", "drag one of the other screens: the laptop stays where it is")
    other = others[0]
    return other, OPPOSITE[side_of(rect(sid, point), rect(other))]


KEEP = object()


@endpoint
def set_screen_setting(sid: str, key: str, value: object, when: object = None) -> dict:
    """key: rotation | scale | mode | position | one_desktop; value None unsets.
    when: None (or left out) keeps the condition, [] = always, [other id] = only
    while that screen is connected. position also takes {x, y} from a drag."""
    cfg, monitors = recorded()
    sid = known_screen(cfg, sid)
    need(key in config.SETTING_KEYS, "bad_value", f"unknown setting: {key!r}")
    target = sid
    if key == "position" and isinstance(value, dict):
        target, value = side_from_point(cfg, sid, value, monitors)
    value = clean_value(cfg, target, key, value)
    wanted_when = KEEP if when is None else condition(cfg, target, when)

    changed = []

    def mutate(fresh):
        known_screen(fresh, target)
        before = copy.deepcopy(config.get_setting(fresh, target, key))
        config.set_setting(fresh, target, key, value)
        if value is not None and wanted_when is not KEEP:
            config.set_condition(fresh, target, key, wanted_when)
        changed.append(config.get_setting(fresh, target, key) != before)
        return changed[-1]
    config.update(mutate)
    applied = run_sync() if changed and changed[-1] else []
    return {**one_screen(sid), "applied": applied}


@endpoint
def forget_screen(sid: str) -> dict:
    """Removes a screen that is not connected, with its settings."""
    cfg, monitors = recorded()
    sid = known_screen(cfg, sid)
    need(not cfg["screens"][sid].get("internal"), "internal_screen", "the laptop screen cannot be forgotten")
    need(sid not in config.connected(monitors), "connected_screen", "unplug it first, then forget it")

    def mutate(fresh):
        if sid not in fresh["screens"]:
            return False
        del fresh["screens"][sid]
        for screen in fresh["screens"].values():
            for setting in screen.get("settings", {}).values():
                if setting.get("when") == sid:
                    setting["when"] = None
    config.update(mutate)
    run_sync()
    return {"ok": True}


@endpoint
def toggle_favorite(sid: str) -> dict:
    cfg = settings()
    sid = known_screen(cfg, sid)

    def mutate(fresh):
        screen = fresh["screens"][known_screen(fresh, sid)]
        screen["favorite"] = not screen.get("favorite")
    return one_screen(sid, config.update(mutate))


@endpoint
def fixed_status() -> dict:
    return fixed_view(settings())


@endpoint
def swap_fixed() -> dict:
    try:
        desktops.swap(settings())
    except RuntimeError as error:
        raise ApiError("no_external", "no external monitor connected") from error
    return fixed_view(settings())


# --- keys ------------------------------------------------------------------------------


KEY_NAMES = {code: name for name, code in keybinds.KEYCODES.items()}


def bind_combo(bind: dict) -> str:
    mods = keybinds.mods_text(int(bind.get("modmask") or 0))
    key = str(bind.get("key") or "")
    if not key and bind.get("keycode"):
        code = int(bind["keycode"])
        key = KEY_NAMES.get(code, f"code:{code}")
    if not key:
        return ""
    return keybinds.normalize(f"{mods} + {key}" if mods else key)


def hypr_binds() -> dict[str, str]:
    """Keys Hyprland (Omarchy) has bound right now, apart from ours: combo -> what it does."""
    own = keybinds.own_descriptions()
    found = {}
    for bind in hypr.query_list("binds"):
        description = str(bind.get("description") or "")
        if bind.get("submap") or description in own:
            continue
        combo = bind_combo(bind)
        if combo and combo not in found:
            found[combo] = description or f"{bind.get('dispatcher', '')} {bind.get('arg', '')}".strip() or "?"
    return found


def action_view(cfg: dict, action: str) -> dict:
    return {"id": action, "title": ACTION_TITLES[action], "desc": ACTION_HELP[action],
            "slots": [combo or None for combo in cfg["keybinds"][action]]}


def options_view(cfg: dict) -> dict:
    return {"desktop_keys": bool(cfg["desktop_keys"]), "default_fixed": cfg["default_fixed"]}


@endpoint
def keys() -> dict:
    cfg = settings()
    return {
        "actions": [action_view(cfg, action) for action, _label, _command in config.ACTIONS],
        "hyprBinds": hypr_binds(),
        "options": options_view(cfg),
        "defaultFixedChoices": [{"value": v, "label": DEFAULT_FIXED_LABELS[v]} for v in config.FIXED_DEFAULTS],
    }


@endpoint
def set_key(action: str, slot: int, combo: str | None) -> dict:
    """Puts `combo` ("SUPER + M"; "" or None removes) on one of an action's two
    slots. Another action of ours with that key loses it; a Hyprland key on it
    is replaced while hypr-screens runs (listed in "conflicts")."""
    need(action in config.DEFAULT_KEYBINDS, "bad_value", f"unknown action: {action!r}")
    need(slot in (0, 1) and not isinstance(slot, bool), "bad_value", "slot must be 0 or 1")
    need(combo is None or isinstance(combo, str), "bad_value", "combo must be text")
    raw = (combo or "").strip()
    combo = keybinds.normalize(raw) if raw else ""
    need(not raw or combo, "bad_value", f"not a key combination: {raw!r}")
    before = []

    def mutate(cfg):
        before.append(copy.deepcopy(cfg))
        for other, combos in cfg["keybinds"].items():
            for index, existing in enumerate(combos):
                if combo and (other, index) != (action, slot) and keybinds.normalize(existing) == combo:
                    combos[index] = ""
        keybinds.set_key(cfg, action, slot, combo)
        return cfg["keybinds"] != before[0]["keybinds"]
    cfg = config.update(mutate)
    if cfg["keybinds"] != before[0]["keybinds"]:
        keybinds.write(cfg)
        keybinds.go_live(before[0], cfg)
    return {**action_view(cfg, action), "conflicts": keybinds.conflicts(combo) if combo else []}


@endpoint
def begin_key_capture() -> dict:
    """While the page records a shortcut: an empty Hyprland keymap, so keys that
    are bound already reach the page instead of firing (Esc always gets out)."""
    hypr.dispatch(f'hl.dsp.submap("{keybinds.RECORD_SUBMAP}")')
    return {"ok": True}


@endpoint
def end_key_capture() -> dict:
    hypr.dispatch('hl.dsp.submap("reset")')
    return {"ok": True}


@endpoint
def set_option(name: str, value: object) -> dict:
    """desktop_keys: true/false; default_fixed: "off" | "external" | "panel"."""
    if name == "desktop_keys":
        need(isinstance(value, bool), "bad_value", "desktop_keys must be true or false")
    elif name == "default_fixed":
        need(value in config.FIXED_DEFAULTS, "bad_value", f"default_fixed must be one of {config.FIXED_DEFAULTS}")
    else:
        raise ApiError("bad_value", f"unknown option: {name!r}")
    before = []

    def mutate(cfg):
        before.append(copy.deepcopy(cfg))
        if cfg[name] == value:
            return False
        cfg[name] = value
    cfg = config.update(mutate)
    if before[0][name] != value:
        if name == "desktop_keys":
            keybinds.write(cfg)
            keybinds.go_live(before[0], cfg)
        run_sync()
    return options_view(cfg)


# --- window look -----------------------------------------------------------------------

# A look shown but not saved yet: {"before": shown before the first preview,
# "shown": shown now, "file": True once the Lua file holds it (a reload was needed)}.
_preview: dict | None = None


def look_to_js(values: dict) -> dict:
    out = {LOOK_KEYS[key]: copy.deepcopy(value) for key, value in values.items() if key in LOOK_KEYS}
    out.setdefault("animSpeed", 1.0)
    out.setdefault("borderColors", None)
    out.setdefault("borderAngle", 0)
    out.setdefault("apps", [])
    return out


def look_from_js(values: object, base: dict) -> dict:
    """The page's values (all or some) on top of `base`, the look shown now."""
    need(isinstance(values, dict), "bad_value", "the look must be an object")
    unknown = sorted(set(values) - set(LOOK_FROM_JS))
    need(not unknown, "bad_value", f"unknown look settings: {unknown}")
    raw = {LOOK_FROM_JS[key]: value for key, value in values.items()}
    colors = raw.get("border_colors")
    if colors is None:
        raw.pop("border_colors", None)
        raw.pop("border_angle", None)
        if "borderColors" in values:  # null: back to the theme's border
            base = {k: v for k, v in base.items() if k not in ("border_colors", "border_angle")}
    else:
        need(isinstance(colors, list) and len(colors) == 2
             and all(isinstance(c, str) and look_mod.HEX_COLOR.match(c) for c in colors), "bad_value",
             "borderColors must be null or two colors like \"#89b4fa\"")
    apps = raw.get("apps", [])
    need(isinstance(apps, list) and all(isinstance(a, dict) and str(a.get("class") or "").strip() for a in apps),
         "bad_value", "apps must be a list of {class, active, inactive}")
    for key, value in raw.items():
        if key in look_mod.OPTIONS:
            kind = look_mod.OPTIONS[key][2]
            need(isinstance(value, bool) if kind == "bool" else is_number(value), "bad_value",
                 f"{LOOK_KEYS[key]} must be {'true or false' if kind == 'bool' else 'a number'}")
    return look_mod.normalize({**base, **raw})


def live_look(saved: dict) -> dict:
    """What Hyprland shows now. It can tell gaps or blur, not our animation speed
    or app rules: those count as shown as they are saved."""
    live = {**look_mod.current(), **{k: v for k, v in saved.items() if k in ("anim_speed", "apps")}}
    if "border_colors" in saved:
        live["border_colors"], live["border_angle"] = look_mod.current_border()
    return live


def shown_look(cfg: dict) -> dict:
    """The look on screen: the preview, or Hyprland's values with the saved ones on top."""
    return _preview["shown"] if _preview else {**live_look(cfg["look"]), **cfg["look"]}


def show_look(cfg: dict, shown: dict, wanted: dict) -> bool:
    """Put `wanted` on screen; True when that took a reload (the Lua file holds it then)."""
    if look_mod.needs_reload(shown, wanted):
        look_mod.show_by_reload(cfg, wanted)
        return True
    look_mod.apply(wanted)
    return False


@endpoint
def look() -> dict:
    cfg = settings()
    saved = cfg["look"]
    live = _preview["shown"] if _preview else live_look(saved)
    values = live if _preview else {**live, **saved}
    border, angle = look_mod.current_border()
    classes = sorted({str(c.get("class")) for c in hypr.query_list("clients") if c.get("class")})
    return {
        "values": look_to_js(values),
        "saved": {LOOK_KEYS[k]: v for k, v in saved.items() if k in LOOK_KEYS},
        "previewing": _preview is not None,
        "apps": [{"id": name, "name": name} for name in classes],
        "presets": [{"name": name, "values": look_to_js(preset)} for name, preset in look_mod.PRESETS.items()],
        "ranges": {**{LOOK_KEYS[key]: {"min": low, "max": high, "step": step}
                      for key, (_o, _p, kind, low, high, step) in look_mod.OPTIONS.items() if kind != "bool"},
                   "animSpeed": {"min": look_mod.ANIM_RANGE[0], "max": look_mod.ANIM_RANGE[1], "step": 0.05},
                   "borderAngle": {"min": 0, "max": 355, "step": 5},
                   "appOpacity": {"min": 0.3, "max": 1.0, "step": 0.01}},
        "themeBorder": {"colors": border, "angle": angle},
    }


@endpoint
def preview_look(values: dict) -> dict:
    """Shows a look without saving it; revert_look() or save_look() ends it."""
    global _preview
    cfg = settings()
    shown = _preview["shown"] if _preview else live_look(cfg["look"])
    wanted = look_from_js(values, shown_look(cfg))
    reloaded = show_look(cfg, shown, wanted)
    _preview = {"before": _preview["before"] if _preview else shown, "shown": wanted,
                "file": bool(_preview and _preview["file"]) or reloaded}
    return {"ok": True, "values": look_to_js(wanted), "reloaded": reloaded}


@endpoint
def revert_look() -> dict:
    """Takes a preview back: the look from before it (the saved one) is shown again."""
    global _preview
    if _preview is not None:
        cfg = settings()
        shown, before = _preview["shown"], _preview["before"]
        if look_mod.needs_reload(shown, before) or look_mod.needs_reload(before, shown):
            look_mod.show_by_reload(cfg, cfg["look"])
        else:
            if _preview["file"]:
                keybinds.write(cfg)  # the Lua file still holds an earlier preview
            look_mod.apply(before)
        _preview = None
    return look()


@endpoint
def save_look(values: dict) -> dict:
    """Shows (if not shown yet) and keeps this look; it is written into the Lua file."""
    global _preview
    cfg = settings()
    wanted = look_from_js(values, shown_look(cfg))
    if _preview is None or _preview["shown"] != wanted:
        shown = _preview["shown"] if _preview else live_look(cfg["look"])
        show_look(cfg, shown, wanted)
    cfg = config.update(lambda fresh: fresh.__setitem__("look", wanted))
    keybinds.write(cfg)
    _preview = None
    return look()


@endpoint
def reset_look() -> dict:
    """Forgets the own look: Omarchy's theme decides again (Hyprland reloads)."""
    global _preview
    cfg = config.update(lambda fresh: fresh.__setitem__("look", {}))
    keybinds.write(cfg)
    look_mod.reset_to_omarchy()
    _preview = None
    time.sleep(RESET_SETTLE_SECONDS)  # before Hyprland reports the theme's values
    return look()


# --- sound -----------------------------------------------------------------------------


def device_view(device: dict, forced: dict) -> dict:
    return {
        "key": device["key"], "kind": device["kind"], "name": device["label"], "sub": device["detail"],
        "icon": SOUND_ICONS.get(device["icon"], "speaker"), "volume": device["volume"], "muted": device["mute"],
        "isDefault": device["default"], "forceMute": device["key"] in forced, "active": device["active"],
        "connected": True, "node": device["name"] or None,
    }


def absent_view(key: str, entry: dict) -> dict:
    kind = entry.get("kind", "sink")
    return {"key": key, "kind": kind, "name": entry.get("label") or key, "sub": "",
            "icon": "mic" if kind == "source" else "speaker", "volume": 0, "muted": True, "isDefault": False,
            "forceMute": True, "active": False, "connected": False, "node": None}


def app_view(app: dict, outputs: list[dict]) -> dict:
    output = next((d["key"] for d in outputs if d["name"] and d["name"] == app["sink"]), None)
    return {"key": f"app:{app['index']}", "index": app["index"], "name": app["label"], "sub": app["detail"],
            "icons": app["icons"], "volume": app["volume"], "muted": app["mute"], "paused": app["paused"],
            "output": output}


def sound_view(snapshot: dict, forced: dict) -> dict:
    present = {d["key"] for d in snapshot["outputs"] + snapshot["inputs"]}
    out = {}
    for name, kind in (("outputs", "sink"), ("inputs", "source")):
        out[name] = [device_view(d, forced) for d in snapshot[name]]
        out[name] += [absent_view(key, entry) for key, entry in forced.items()
                      if entry.get("kind") == kind and key not in present]
    out["apps"] = [app_view(app, snapshot["outputs"]) for app in snapshot["apps"]]
    return out


def find_sound(key: object) -> tuple[str, dict, dict, dict]:
    """("device" | "app", the raw entry, the snapshot, forced) for a key from sound_state()."""
    need(isinstance(key, str), "unknown_device", f"unknown device: {key!r}")
    snapshot = sound.snapshot()
    forced = sound.forced(settings())
    if key.startswith("app:"):
        app = next((a for a in snapshot["apps"] if f"app:{a['index']}" == key), None)
        need(app is not None, "unknown_device", f"that app is not playing any more: {key}")
        return "app", app, snapshot, forced
    device = next((d for d in snapshot["outputs"] + snapshot["inputs"] if d["key"] == key), None)
    need(device is not None, "unknown_device", f"unknown or unplugged device: {key}")
    return "device", device, snapshot, forced


def fresh_sound_item(key: str) -> dict | None:
    state = sound_state()
    return next((item for name in ("outputs", "inputs", "apps") for item in state[name] if item["key"] == key), None)


@endpoint
def sound_state() -> dict:
    return sound_view(sound.snapshot(), sound.forced(settings()))


def usable_device(device: dict, forced: dict, changing_volume: bool = True) -> None:
    need(device["active"], "inactive", "the sound card uses another profile: switch the device on first")
    if changing_volume:
        need(device["key"] not in forced, "force_muted", "Force Mute keeps this device silent; switch it off first")


@endpoint
def set_volume(key: str, value: int) -> dict | None:
    need(is_number(value) and 0 <= value <= sound.VOLUME_MAX, "bad_value", "volume must be 0 to 100")
    what, item, _snapshot, forced = find_sound(key)
    if what == "app":
        sound.set_volume("sink-input", str(item["index"]), value)
    else:
        usable_device(item, forced)
        sound.set_volume(item["kind"], item["name"], value)
    return fresh_sound_item(key)


@endpoint
def set_mute(key: str, on: bool) -> dict | None:
    need(isinstance(on, bool), "bad_value", "on must be true or false")
    what, item, _snapshot, forced = find_sound(key)
    if what == "app":
        sound.set_mute("sink-input", str(item["index"]), on)
    else:
        usable_device(item, forced, changing_volume=not on)
        sound.set_mute(item["kind"], item["name"], on)
    return fresh_sound_item(key)


@endpoint
def set_default(key: str) -> dict:
    what, item, _snapshot, forced = find_sound(key)
    need(what == "device", "bad_value", "an app cannot be the default device")
    usable_device(item, forced, changing_volume=False)
    sound.set_default(item["kind"], item["name"])
    return sound_state()


@endpoint
def switch_on_device(key: str) -> dict:
    """A device the sound card's profile does not drive: switch the card to one
    that does (the default devices stay as they are)."""
    what, item, _snapshot, _forced = find_sound(key)
    need(what == "device" and not item["active"], "bad_value", "that device is on already")
    sound.switch_on(item["card"], item["profile"])
    return sound_state()


@endpoint
def set_force_mute(key: str, on: bool) -> dict | None:
    """Keeps a device silent for good (also an unplugged one, to switch it off)."""
    need(isinstance(on, bool), "bad_value", "on must be true or false")
    need(isinstance(key, str) and not key.startswith("app:"), "bad_value", "only devices can be force muted")
    snapshot = sound.snapshot()
    device = next((d for d in snapshot["outputs"] + snapshot["inputs"] if d["key"] == key), None)
    previous = {}

    def mutate(cfg):
        entries = sound.forced(cfg)
        previous.update(entries.get(key) or {})
        target = device
        if target is None:
            need(key in entries, "unknown_device", f"unknown or unplugged device: {key}")
            target = {"key": key, "kind": entries[key].get("kind"), "label": entries[key].get("label"),
                      "active": False}
        if (key in entries) == on:
            return False
        sound.set_forced(cfg, target, on)
    cfg = config.update(mutate)
    if on:
        sound.enforce(cfg)
    elif device is not None and previous:
        sound.release(device, previous)
    return fresh_sound_item(key)


@endpoint
def set_app_output(app: str, device: str) -> dict | None:
    what, item, snapshot, _forced = find_sound(app)
    need(what == "app", "bad_value", f"not an app: {app!r}")
    output = next((d for d in snapshot["outputs"] if d["key"] == device), None)
    need(output is not None and output["active"], "unknown_device", f"not an output that is on: {device!r}")
    sound.move_app(item["index"], output["name"])
    return fresh_sound_item(app)


# --- camera ----------------------------------------------------------------------------


@endpoint
def camera() -> dict:
    cfg = settings()
    real = camera_mod.real_device()
    name = next((n for path, n, _i in camera_mod.nodes() if path == real), None) if real else None
    status = camera_mod.status()
    users = int(status.get("users") or 0)
    return {
        "installed": camera_mod.is_set_up(),
        "enabled": camera_mod.enabled(cfg),
        "rotation": camera_mod.rotation(cfg),
        "rotations": list(camera_mod.ROTATIONS),
        "state": status.get("state"),
        "inUse": users > 0,
        "users": users,
        "device": name,
        "hasCamera": real is not None,
        "virtualName": camera_mod.CARD_LABEL,
    }


@endpoint
def set_camera(enabled: bool, rotation: int) -> dict:
    need(isinstance(enabled, bool), "bad_value", "enabled must be true or false")
    need(rotation in camera_mod.ROTATIONS and not isinstance(rotation, bool), "bad_value",
         f"rotation must be one of {camera_mod.ROTATIONS}")
    config.update(lambda cfg: cfg["camera"].update({"enabled": enabled, "rotation": int(rotation)}))
    return camera()


@endpoint
def setup_camera() -> dict:
    """The one-time root setup of the virtual camera (asks for the password)."""
    if not camera_mod.is_set_up():
        done = camera_mod.setup(graphical=True)
        need(done and camera_mod.is_set_up(), "cancelled", "the camera setup was cancelled or failed")
    return camera()


@endpoint
def camera_preview() -> dict:
    """The newest preview frame as a data: URL (the watcher's feeder writes it
    while asked to; call this a few times a second while the preview shows)."""
    module = camera_mod
    if not module.is_set_up():
        return {"image": None, "reason": "not_set_up"}
    if not module.enabled():
        return {"image": None, "reason": "off"}
    module.request_preview()
    path = module.preview_file()
    try:
        stamp = path.stat().st_mtime
        if time.time() - stamp > PREVIEW_FRESH_SECONDS:
            return {"image": None, "reason": "starting"}
        data = path.read_bytes()
    except OSError:
        return {"image": None, "reason": "starting"}
    return {"image": "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii"), "time": stamp}


# --- Samsung ---------------------------------------------------------------------------


def battery_minutes() -> tuple[int | None, int | None]:
    """(minutes left on battery, minutes until full), from the battery's own numbers."""
    battery = samsung_mod.battery_dir()
    if battery is None:
        return None, None
    status = samsung_mod.read(battery / "status")
    now = samsung_mod.number(battery / "energy_now") or samsung_mod.number(battery / "charge_now")
    full = samsung_mod.number(battery / "energy_full") or samsung_mod.number(battery / "charge_full")
    rate = samsung_mod.number(battery / "power_now") if samsung_mod.number(battery / "energy_now") \
        else samsung_mod.number(battery / "current_now")
    if not now or not rate:
        return None, None
    if status == "Discharging":
        return round(60 * now / rate), None
    if status == "Charging" and full and full > now:
        return None, round(60 * (full - now) / rate)
    return None, None


def samsung_view() -> dict:
    if not samsung_mod.present():
        return {"available": False, "active": False}
    status = samsung_mod.status(settings())
    battery = status["battery"]
    left, full_in = battery_minutes()
    keyboard = status["keyboard"]
    return {
        "available": True,
        "active": samsung_mod.active(),
        "writable": status["writable"],
        "level": battery.get("percent"),
        "status": battery.get("status") or None,
        "charging": battery.get("status") == "Charging",
        "plugged": status["ac"],
        "health": battery.get("health"),
        "cycles": battery.get("cycles"),
        "power": battery.get("watts"),
        "remainingMinutes": left,
        "fullInMinutes": full_in,
        "chargeLimit": status["limit"],
        "wantedLimit": status["wanted_limit"],
        "fullOnce": status["full_once"],
        "mode": status["mode"] or None,
        "modes": [{"value": mode, "label": label} for mode, label in status["modes"]],
        "fanRpm": status["fan"]["rpm"],
        "fanRunning": status["fan"]["running"],
        "cpuTemp": status["cpu_temperature"],
        "kbdLight": keyboard[0] if keyboard else None,
        "kbdMax": keyboard[1] if keyboard else None,
        "usbCharging": status["attributes"].get("usb_charging"),
        "lidPower": status["attributes"].get("power_on_lid_open"),
        "attributesWritable": status["attributes_writable"],
    }


@endpoint
def samsung() -> dict:
    """Battery, charge limit, performance mode and the firmware switches of a
    Galaxy Book; {"available": False, "active": False} on other laptops."""
    return samsung_view()


@endpoint
def set_samsung(field: str, value: object) -> dict:
    """field: active | chargeLimit | fullOnce | mode | usbCharging | lidPower | kbdLight."""
    module = samsung_mod
    need(module.present(), "unavailable", "not a Samsung Galaxy Book (or the samsung-galaxybook driver is not loaded)")
    if field == "active":
        need(isinstance(value, bool), "bad_value", "active must be true or false")
        if value != module.active():
            done = module.setup(graphical=True) if value else module.teardown(graphical=True)
            need(done, "cancelled", "it was cancelled or failed")
            install.sync_power_panel(module.active())
    elif field == "chargeLimit":
        need(is_number(value) and 50 <= value <= 100, "bad_value", "chargeLimit must be 50 to 100")
        config.update(lambda cfg: module.set_limit(cfg, int(value)))
    elif field == "fullOnce":
        need(isinstance(value, bool), "bad_value", "fullOnce must be true or false")
        need(not value or module.ac_online(), "not_plugged", "plug in the charger first")
        config.update(lambda cfg: module.full_once(cfg, value))
    elif field == "mode":
        config.update(lambda cfg: module.set_mode(cfg, value))
    elif field in SAMSUNG_ATTRIBUTES:
        need(isinstance(value, bool), "bad_value", f"{field} must be true or false")
        need(module.set_attribute(SAMSUNG_ATTRIBUTES[field], value), "not_set_up",
             "could not change it (is the one-time setup done?)")
    elif field == "kbdLight":
        keyboard = module.keyboard()
        need(keyboard is not None, "unavailable", "this laptop has no keyboard backlight")
        need(is_number(value) and 0 <= value <= keyboard[1], "bad_value", f"kbdLight must be 0 to {keyboard[1]}")
        module.set_keyboard(int(value))
    else:
        raise ApiError("bad_value", f"unknown field: {field!r}")
    return samsung_view()


# --- widgets ---------------------------------------------------------------------------


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
    module = widgets_mod
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
                widget.update(module.CENTER)  # first time: in the middle, to be dragged from there
            widget["enabled"] = enabled
        for key, value in updates:
            widget[key] = value
        fresh["widgets"] = module.normalize(fresh["widgets"])
    cfg = config.update(mutate)
    module.apply(cfg)
    return widget_schema.view(kind, cfg["widgets"][kind], cfg)


@endpoint
def install_cava() -> dict:
    """The visualizer needs the program cava (installed with the password)."""
    module = widgets_mod
    if not module.has_cava():
        need(module.install_cava(graphical=True) and module.has_cava(), "cancelled",
             "installing cava was cancelled or failed")
        module.apply(settings())
        module.shell_ipc("reload")
    cfg = settings()
    return widget_schema.view("visualizer", cfg["widgets"]["visualizer"], cfg)


def layouts_view(cfg: dict) -> dict:
    module = widgets_mod
    connected = sorted(config.connected(hypr.monitors()))
    names = {sid: screen.get("name", sid) for sid, screen in cfg["screens"].items()}
    current = next((layout["name"] for layout in cfg["widget_layouts"]
                    if module.normalize(layout["widgets"]) == cfg["widgets"]), None)
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
    module = widgets_mod
    cfg = settings()
    need(any(layout["name"] == name for layout in cfg["widget_layouts"])
         or len(cfg["widget_layouts"]) < module.MAX_LAYOUTS, "bad_value",
         f"there are {module.MAX_LAYOUTS} layouts already; delete one first")
    return layouts_view(config.update(changing(module.save_layout, name)))


@endpoint
def load_layout(name: str) -> dict:
    module = widgets_mod
    known_layout(settings(), name)
    cfg = config.update(changing(module.load_layout, name))
    module.apply(cfg)
    return layouts_view(cfg)


@endpoint
def delete_layout(name: str) -> dict:
    module = widgets_mod
    known_layout(settings(), name)
    return layouts_view(config.update(changing(module.delete_layout, name)))


@endpoint
def rename_layout(name: str, new_name: str) -> dict:
    module = widgets_mod
    cfg = settings()
    known_layout(cfg, name)
    new_name = layout_name(new_name)
    if new_name == name:
        return layouts_view(cfg)
    need(not any(layout["name"] == new_name for layout in cfg["widget_layouts"]), "conflict",
         f"there is a layout called {new_name!r} already")
    return layouts_view(config.update(changing(module.rename_layout, name, new_name)))


@endpoint
def set_layout_auto(name: str, on: bool) -> dict:
    """On: the layout loads by itself whenever exactly the screens connected now
    are (another layout with those screens gives them up). Off: only by hand."""
    module = widgets_mod
    known_layout(settings(), name)
    need(isinstance(on, bool), "bad_value", "on must be true or false")
    connected = sorted(config.connected(hypr.monitors())) if on else []
    return layouts_view(config.update(changing(module.set_layout_screens, name, connected)))


@endpoint
def arrange_widgets() -> dict:
    """Starts arranging on the desktop (drag, resize, turn, colors); the overlay
    saves by itself (`hypr-screens widgets save`)."""
    module = widgets_mod
    cfg = settings()
    need(any(module.on_desktop(cfg["widgets"][kind], kind) for kind in module.KINDS), "nothing_to_arrange",
         "switch a widget on first")
    for _ in range(ARRANGE_TRIES):  # a plugin that was just switched on needs a moment
        if module.start_editing():
            return {"ok": True}
        time.sleep(ARRANGE_PAUSE)
    raise ApiError("not_ready", "the widgets are not ready yet – try again in a moment")


# --- general ---------------------------------------------------------------------------


def language_view(code: str) -> dict:
    return {"code": code, "items": [{"code": c, "name": n} for c, n in i18n.LANGUAGES.items()]}


@endpoint
def language() -> dict:
    return language_view(config.load()["language"])


@endpoint
def set_language(code: str) -> dict:
    need(code in config.LANGUAGE_CODES, "bad_value", f"language must be one of {config.LANGUAGE_CODES}")
    cfg = config.update(lambda fresh: fresh.__setitem__("language", code))
    i18n.set_language(code)
    widgets_mod.export(cfg)  # the widgets' own texts and date format
    return language_view(code)


@endpoint
def translations() -> dict:
    """{english text: translation} for the chosen language ({} for English)."""
    code = config.load()["language"]
    return {"code": code, "texts": i18n.load_table(code)}


def version() -> str:
    try:
        from importlib import metadata

        return metadata.version("hypr-minimizer")
    except Exception:
        pass
    try:
        import tomllib

        project = tomllib.loads((Path(__file__).resolve().parent.parent / "pyproject.toml").read_text())
        return str(project["project"]["version"])
    except Exception:
        return "?"


@endpoint
def about() -> dict:
    folder = config.config_file().parent
    home = Path.home()
    shown = f"~/{folder.relative_to(home)}" if folder.is_relative_to(home) else str(folder)
    return {"version": version(), "configDir": shown, "configPath": str(folder),
            "configFile": str(config.config_file()), "guideUrl": DOCS_URL}


@endpoint
def open_guide() -> dict:
    open_uri(DOCS_URL)
    return {"ok": True}


@endpoint
def open_config_folder() -> dict:
    folder = config.config_file().parent
    folder.mkdir(parents=True, exist_ok=True)
    open_uri(folder.as_uri())
    return {"ok": True}


@endpoint
def theme() -> dict:
    """The Omarchy theme for the page: its colors, light or dark, font, rounding."""
    colors = theme_mod.palette()
    mode = colors.pop("mode")
    return {"mode": mode, "colors": colors, "font": theme_mod.font(), "rounding": theme_mod.rounding()}
