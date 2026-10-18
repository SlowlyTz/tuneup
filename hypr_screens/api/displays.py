"""Screens: the list, their settings, dragging one next to the laptop, the fixed screen."""
import copy
import re

from hypr_screens import apply, config, desktops, hypr
from hypr_screens.api.core import ApiError, endpoint, need, is_number, settings, recorded, run_sync

TRANSFORM_DEGREES = {0: 0, 1: 90, 2: 180, 3: 270}
MODE_PATTERN = re.compile(r"^\d{2,5}x\d{2,5}(@\d{1,3}(\.\d{1,3})?)?$")
SCALE_RANGE = (0.25, 4)


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
