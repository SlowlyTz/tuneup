"""The window look: shown live while previewing, kept in the Lua file when saved."""
import copy
import time

from hypr_screens import config, drift, hypr, keybinds
from hypr_screens import look as look_mod
from hypr_screens.api.core import endpoint, need, is_number, settings

RESET_SETTLE_SECONDS = 0.8
LOOK_KEYS = {"gaps_in": "gapsIn", "gaps_out": "gapsOut", "rounding": "rounding", "border_size": "border",
             "blur": "blur", "blur_size": "blurSize", "blur_passes": "blurPasses",
             "active_opacity": "activeOpacity", "inactive_opacity": "inactiveOpacity",
             "anim_speed": "animSpeed", "border_colors": "borderColors", "border_angle": "borderAngle",
             "apps": "apps"}
LOOK_FROM_JS = {js: key for key, js in LOOK_KEYS.items()}


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
    drift.mark_preview(True)  # the watcher's audit leaves the look alone meanwhile
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
        drift.mark_preview(False)
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
    drift.mark_preview(False)
    return look()


@endpoint
def reset_look() -> dict:
    """Forgets the own look: Omarchy's theme decides again (Hyprland reloads)."""
    global _preview
    cfg = config.update(lambda fresh: fresh.__setitem__("look", {}))
    keybinds.write(cfg)
    look_mod.reset_to_omarchy()
    _preview = None
    drift.mark_preview(False)
    time.sleep(RESET_SETTLE_SECONDS)  # before Hyprland reports the theme's values
    return look()
