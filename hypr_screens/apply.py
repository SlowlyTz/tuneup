"""Put the per-screen settings in force on the connected monitors.

Only settings whose condition holds are applied, through `hl.monitor`; fields a
screen has no setting for keep their current value. A setting that stops
applying on a connected screen (its condition went away) cannot be "unset" at
runtime, so the Hyprland config is reloaded once to get the configured values
back, and the remaining settings are applied on top. A position is the
exception: it is handed back to Hyprland with position "auto". A screen that
is unplugged needs nothing: its rule only matters when it comes back, and is
checked then (another screen on that connector gets a reload, so it does not
inherit the rule).

A position ("above" the laptop, ...) becomes explicit coordinates for both
screens (layout()): Hyprland's auto-up/-left/... only stack a screen along one
axis at 0, and the laptop (placed "auto", to the right of everything) then
touches it at a corner only -- the mouse cannot cross.
"""
import fcntl
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from hypr_screens import config, hypr

TRANSFORMS = {0: 0, 90: 1, 180: 2, 270: 3}
MONITOR_FIELDS = ("rotation", "scale", "mode", "position")
RELOAD_SETTLE_SECONDS = 0.5


@contextmanager
def locked(name: str = "apply"):
    """Serialize appliers (watcher, menu, CLI) across processes."""
    with open(config.runtime_dir() / f"{name}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def busy(name: str = "sync") -> bool:
    """Whether someone holds that lock right now (it is not taken)."""
    with open(config.runtime_dir() / f"{name}.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(lock, fcntl.LOCK_UN)
        return False


def applied_file() -> Path:
    return config.runtime_dir() / "applied.json"


def load_applied() -> dict:
    try:
        applied = json.loads(applied_file().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return applied if isinstance(applied, dict) else {}


def save_applied(applied: dict) -> None:
    temporary = applied_file().with_suffix(".tmp")
    temporary.write_text(json.dumps(applied, indent=2, sort_keys=True) + "\n")
    temporary.replace(applied_file())


def reload_mark() -> Path:
    return config.runtime_dir() / "reloaded"


def reset() -> None:
    """Hyprland's config back (it drops every rule set at runtime) and nothing
    counted as applied. The watcher knows the reload event that follows as ours."""
    save_applied({})
    reload_mark().write_text(f"{time.time()}\n")
    hypr.hyprctl("reload")
    time.sleep(RELOAD_SETTLE_SECONDS)


def reloaded_by_us(within: float) -> bool:
    try:
        return time.time() - float(reload_mark().read_text()) < within
    except (OSError, ValueError):
        return False


def usable(key: str, value: object) -> bool:
    """A value Hyprland can take; a hand-edited config must not stop the sync."""
    if value is None:
        return False
    if key == "rotation":
        return value in TRANSFORMS and not isinstance(value, bool)
    if key == "scale":
        return value == "auto" or (isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0)
    if key == "position":
        return value in config.POSITIONS
    return isinstance(value, str) and bool(value)


def desired(cfg: dict, monitors: list[dict]) -> dict[str, dict]:
    """{connector: {"id", "fields"}} for every enabled monitor; a position is
    resolved to "XxY" coordinates, the anchor screen then gets one too."""
    live = config.connected(monitors)
    ids = set(live)
    result = {}
    for sid, monitor in live.items():
        fields = {}
        for key in MONITOR_FIELDS:
            value = config.active_value(cfg, sid, key, ids)
            if not usable(key, value) or (key == "position" and config.is_internal(monitor)):
                continue
            fields[key] = value
        result[str(monitor["name"])] = {"id": sid, "fields": fields}
    by_name = {str(monitor["name"]): monitor for monitor in live.values()}
    sides = {name: entry["fields"].pop("position") for name, entry in result.items() if "position" in entry["fields"]}
    anchor = pick_anchor(list(by_name.values()), sides)
    if anchor is not None:
        sides.pop(anchor, None)
    if anchor is not None and sides:
        sizes = {name: logical_size(by_name[name], result[name]["fields"]) for name in result}
        for name, (x, y) in layout(sizes, anchor, sides).items():
            result[name]["fields"]["position"] = f"{x}x{y}"
    return result


# --- placing screens edge to edge ---------------------------------------------------------


def pick_anchor(monitors: list[dict], sides: dict[str, str]) -> str | None:
    """The screen the others are placed around: the laptop, else the first
    screen without a position, else the first screen."""
    names = sorted(str(monitor["name"]) for monitor in monitors)
    internal = [str(monitor["name"]) for monitor in monitors if config.is_internal(monitor)]
    return next(iter(internal), None) or next((name for name in names if name not in sides), None) \
        or next(iter(names), None)


def parse_size(mode: str) -> tuple[int, int] | None:
    try:
        width, height = (int(part) for part in str(mode).partition("@")[0].split("x"))
    except ValueError:
        return None
    return width, height


def logical_size(monitor: dict, fields: dict) -> tuple[int, int]:
    """Width and height in layout coordinates once `fields` are in force: the
    mode divided by the scale, swapped by a quarter turn. A mode or scale only
    Hyprland can work out ("preferred", "auto") counts as the current one."""
    width, height = parse_size(fields.get("mode", "")) or (int(monitor["width"]), int(monitor["height"]))
    scale = fields.get("scale", "auto")
    scale = float(monitor.get("scale") or 1) if scale == "auto" else float(scale)
    transform = TRANSFORMS[fields["rotation"]] if "rotation" in fields else int(monitor.get("transform") or 0)
    width, height = round(width / scale), round(height / scale)
    return (height, width) if transform % 2 else (width, height)


def layout(sizes: dict[str, tuple[int, int]], anchor: str, sides: dict[str, str]) -> dict[str, tuple[int, int]]:
    """Top-left corners: every screen in `sides` edge to edge with the anchor,
    centred along that edge; several on one side line up outwards (by
    connector name). Shifted so that no coordinate is negative."""
    anchor_width, anchor_height = sizes[anchor]
    spots = {anchor: (0, 0)}
    reach = {"left": 0, "right": anchor_width, "above": 0, "below": anchor_height}
    for name in sorted(sides):
        side, (width, height) = sides[name], sizes[name]
        if side == "left":
            reach["left"] -= width
            spots[name] = (reach["left"], (anchor_height - height) // 2)
        elif side == "right":
            spots[name] = (reach["right"], (anchor_height - height) // 2)
            reach["right"] += width
        elif side == "above":
            reach["above"] -= height
            spots[name] = ((anchor_width - width) // 2, reach["above"])
        elif side == "below":
            spots[name] = ((anchor_width - width) // 2, reach["below"])
            reach["below"] += height
    left = min(x for x, _y in spots.values())
    top = min(y for _x, y in spots.values())
    return {name: (x - left, y - top) for name, (x, y) in spots.items()}


def snapshot(monitor: dict) -> dict:
    return {
        key: monitor.get(key)
        for key in ("x", "y", "width", "height", "refreshRate", "scale", "transform")
    }


def mode_matches(monitor: dict, mode: str) -> bool:
    size, rate = parse_size(mode), mode.partition("@")[2]
    if size is None or (monitor.get("width"), monitor.get("height")) != size:
        return False
    try:
        return not rate or abs(float(monitor.get("refreshRate") or 0) - float(rate)) < 0.5
    except ValueError:
        return False


def already_there(monitor: dict, fields: dict) -> bool:
    """Whether the live monitor shows these fields, as far as that can be read."""
    if fields.get("scale") == "auto":
        return False
    if "position" in fields and fields["position"] != f"{monitor.get('x', 0)}x{monitor.get('y', 0)}":
        return False
    if "rotation" in fields and monitor.get("transform") != TRANSFORMS[fields["rotation"]]:
        return False
    if "scale" in fields and abs(float(monitor.get("scale") or 1) - float(fields["scale"])) > 0.01:
        return False
    return "mode" not in fields or mode_matches(monitor, str(fields["mode"]))


def monitor_rule(monitor: dict, fields: dict) -> str:
    transform = TRANSFORMS[fields["rotation"]] if "rotation" in fields else int(monitor.get("transform") or 0)
    if "mode" in fields:
        mode = str(fields["mode"])
    else:
        mode = f"{monitor['width']}x{monitor['height']}@{float(monitor.get('refreshRate') or 60):.2f}"
    if "position" in fields:
        position = str(fields["position"])
    elif transform % 2 != int(monitor.get("transform") or 0) % 2:
        # Width and height swap; the old spot could overlap the other screen.
        position = "auto"
    else:
        position = f"{monitor.get('x', 0)}x{monitor.get('y', 0)}"
    scale = fields.get("scale", monitor.get("scale") or 1)
    scale_lua = hypr.lua_string("auto") if scale == "auto" else repr(float(scale))
    return (
        f"hl.monitor({{ output = {hypr.lua_string(monitor['name'])}, mode = {hypr.lua_string(mode)}, "
        f"position = {hypr.lua_string(position)}, scale = {scale_lua}, transform = {transform} }})"
    )


def needs_reset(applied: dict, wanted: dict) -> bool:
    """A connected screen still has a rule it should not have: another screen's
    (same connector) or a field whose setting went away (but a position)."""
    for name, now in wanted.items():
        entry = applied.get(name)
        if entry is None:
            continue
        if now["id"] != entry.get("id"):
            return True
        if set(entry.get("fields", {})) - set(now["fields"]) - {"position"}:
            return True
    return False


def rule_fields(previous: dict | None, fields: dict) -> dict:
    """What to send: the fields, and "auto" for a position that went away."""
    if previous and "position" in previous.get("fields", {}) and "position" not in fields:
        return {**fields, "position": "auto"}
    return fields


def in_place(monitor: dict, fields: dict) -> bool:
    """Whether the screen stands where its position says (no position: anywhere)."""
    return "position" not in fields or fields["position"] == f"{monitor.get('x', 0)}x{monitor.get('y', 0)}"


def in_force(previous: dict | None, monitor: dict, fields: dict) -> bool:
    """Whether the rule sent last is still what the screen shows."""
    return bool(previous) and previous.get("fields") == fields and previous.get("after") == snapshot(monitor) \
        and in_place(monitor, fields)


def drifted(cfg: dict, monitors: list[dict]) -> list[str]:
    """Connected screens that do not show what their settings want (any more):
    a reload, another app or a hotplug changed them. Empty while nothing is due."""
    wanted = desired(cfg, monitors)
    applied = load_applied()
    if needs_reset(applied, wanted):
        return sorted(wanted)
    by_name = {str(monitor.get("name")): monitor for monitor in monitors}
    found = []
    for name, entry in wanted.items():
        previous, monitor = applied.get(name), by_name[name]
        if not rule_fields(previous, entry["fields"]) or in_force(previous, monitor, entry["fields"]):
            continue
        if previous is None and already_there(monitor, entry["fields"]):
            continue
        found.append(name)
    return found


def put_in_force(wanted: dict, monitors: list[dict], applied: dict) -> list[str]:
    """Send the rules that are not in force yet; records them in `applied`."""
    done = []
    by_name = {str(monitor.get("name")): monitor for monitor in monitors}
    for name, entry in wanted.items():
        fields = entry["fields"]
        monitor = by_name.get(name)
        previous = applied.get(name)
        if not rule_fields(previous, fields) or monitor is None:
            continue
        if in_force(previous, monitor, fields):
            continue
        if previous is None and already_there(monitor, fields):
            applied[name] = {"id": entry["id"], "fields": fields, "after": snapshot(monitor)}
            continue
        reply = hypr.eval_lua(monitor_rule(monitor, rule_fields(previous, fields)))
        if hypr.rejected(reply):
            # Not recorded: the next sync tries again instead of believing it is in force.
            print(f"hypr-screens: Hyprland rejected the rule for {name}: {reply.strip()}",
                  file=sys.stderr, flush=True)
            continue
        done.append(name)
        applied[name] = {"id": entry["id"], "fields": fields}
    return done


def apply(cfg: dict) -> list[str]:
    """Bring the monitors in line with the settings; returns what was done."""
    done = []
    with locked():
        monitors = hypr.monitors()
        wanted = desired(cfg, monitors)
        applied = load_applied()

        if needs_reset(applied, wanted):
            reset()
            applied = {}
            done.append("reload")
            monitors = hypr.monitors()
            wanted = desired(cfg, monitors)

        done += put_in_force(wanted, monitors, applied)
        if any("after" not in entry for entry in applied.values()):
            time.sleep(RELOAD_SETTLE_SECONDS)
            monitors = hypr.monitors()
            # A "preferred" mode or an "auto" scale shows its size only now;
            # if that moves the edges, place the screens once more. So too a
            # screen Hyprland put elsewhere while it placed the next one.
            by_name = {str(monitor.get("name")): monitor for monitor in monitors}
            moved = {name: entry for name, entry in desired(cfg, monitors).items()
                     if name in applied and (entry["fields"] != applied[name]["fields"]
                                             or not in_place(by_name.get(name, {}), entry["fields"]))}
            for name in moved:
                applied[name].pop("after", None)
            if moved:
                done += [name for name in put_in_force(moved, monitors, applied) if name not in done]
                time.sleep(RELOAD_SETTLE_SECONDS)
                monitors = hypr.monitors()
            by_name = {str(monitor.get("name")): monitor for monitor in monitors}
            for name, entry in applied.items():
                if name in by_name:
                    entry["after"] = snapshot(by_name[name])
        save_applied(applied)
    return done
