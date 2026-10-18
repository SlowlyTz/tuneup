"""Enforcement: what Tuneup sets stays set, even when another app (or a
reload) changes it. The watcher runs audit() every AUDIT_SECONDS and soon
after events that can mean drift: it compares Hyprland's live state with what
the settings want and puts back only what drifted, in one go.

  screens   monitor mode, scale, rotation and place (apply.drifted)
  desktops  the fixed desktop on its screen, desktops 1-10 on the other one
  look      gaps, rounding, border, blur, opacity and the border colors
  keys      our shortcuts (and the desktop keys) bound to us, nobody else
  screens   a screen Hyprland drives but the kernel does not (drm.py)

Force mute (sound.guard) and the Samsung charge limit and mode (samsung.guard)
are kept by their own threads every second; they report what they put back
here too. Force mute never backs off: a muted speaker must stay muted.

A fight with another app would never end, so an item put back more than
MAX_FIXES times in WINDOW_SECONDS is left alone for a while (BACKOFF_FIRST
seconds, doubling each time up to BACKOFF_MAX; forgotten after QUIET_SECONDS
without trouble). The status (recent fixes, items backed off, a heartbeat of
the watcher) lives in the runtime dir, for the settings window.
"""
import fcntl
import json
import os
import threading
import time
from contextlib import contextmanager

from hypr_screens import config

AUDIT_SECONDS = 5.0
WINDOW_SECONDS = 60.0
MAX_FIXES = 3
BACKOFF_FIRST, BACKOFF_MAX = 30.0, 1800.0
QUIET_SECONDS = 600.0
KEEP_FIXES = 20
# One fix shown once while it repeats within this time (its time moves on).
COALESCE_SECONDS = 60.0
HEARTBEAT_STALE = 3 * AUDIT_SECONDS
AREAS = ("screens", "desktops", "look", "keys", "sound", "samsung")
# What was put back, as the settings window names it (English i18n source texts).
WHAT = {
    "layout": "Screen arrangement",
    "picture": "Screen without a picture",
    "desktops": "Desktops on their screens",
    "look": "Window look",
    "keys": "Shortcuts",
    "force_mute": "Force mute",
    "charge_limit": "Charge limit",
    "mode": "Performance mode",
}
# Items that are put back however often it takes.
NEVER_BACK_OFF = {"force_mute"}

_threads = threading.Lock()


def status_file():
    return config.runtime_dir() / "enforce.json"


def enabled(cfg: dict) -> bool:
    return bool(cfg.get("enforce", True))


def empty_status() -> dict:
    return {"heartbeat": 0.0, "pid": 0, "fixes": [], "history": {}, "backoff": {}}


def load_status() -> dict:
    try:
        raw = json.loads(status_file().read_text())
    except (OSError, json.JSONDecodeError):
        return empty_status()
    status = empty_status()
    if isinstance(raw, dict):
        status.update({key: raw[key] for key in status if isinstance(raw.get(key), type(status[key]))})
    return status


@contextmanager
def changing_status():
    """The status, locked across threads and processes, saved in one step."""
    with _threads, open(config.runtime_dir() / "enforce.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        status = load_status()
        yield status
        temporary = status_file().with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=1) + "\n")
        temporary.replace(status_file())


# --- back-off --------------------------------------------------------------------------


def item_key(area: str, what: str) -> str:
    return f"{area}:{what}"


def backed_off(area: str, what: str, now: float | None = None) -> bool:
    """Whether this item is left alone right now (it kept coming back)."""
    if what in NEVER_BACK_OFF:
        return False
    now = time.time() if now is None else now
    entry = load_status()["backoff"].get(item_key(area, what)) or {}
    return now < float(entry.get("until") or 0)


def record(area: str, what: str, detail: str = "", now: float | None = None) -> bool:
    """Note that `what` was put back; True when it is backed off from now on."""
    now = time.time() if now is None else now
    with changing_status() as status:
        add_fix(status, area, what, detail, now)
        key = item_key(area, what)
        times = [t for t in status["history"].get(key, []) if now - t < WINDOW_SECONDS] + [now]
        status["history"][key] = times
        if what in NEVER_BACK_OFF or len(times) <= MAX_FIXES:
            return False
        entry = status["backoff"].get(key) or {}
        quiet = now - float(entry.get("until") or 0) > QUIET_SECONDS
        level = 1 if quiet else int(entry.get("level") or 0) + 1
        status["backoff"][key] = {"level": level, "until": now + min(BACKOFF_MAX, BACKOFF_FIRST * 2 ** (level - 1))}
        status["history"][key] = []
        return True


def add_fix(status: dict, area: str, what: str, detail: str, now: float) -> None:
    fixes = status["fixes"]
    same = next((f for f in fixes if (f["area"], f["what"], f["detail"]) == (area, WHAT[what], detail)), None)
    if same is not None and now - same["time"] < COALESCE_SECONDS:
        fixes.remove(same)
    fixes.insert(0, {"time": round(now, 1), "area": area, "what": WHAT[what], "detail": detail})
    del fixes[KEEP_FIXES:]


def heartbeat(now: float | None = None) -> None:
    with changing_status() as status:
        status["heartbeat"], status["pid"] = time.time() if now is None else now, os.getpid()


def alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def watcher_running(status: dict, now: float) -> bool:
    """A heartbeat from a watcher that still runs."""
    fresh = now - float(status.get("heartbeat") or 0) <= HEARTBEAT_STALE
    return fresh and alive(int(status.get("pid") or 0))


def view(cfg: dict, now: float | None = None) -> dict:
    """The settings window's enforcement() shape."""
    now = time.time() if now is None else now
    status = load_status()
    backed = []
    for key, entry in status["backoff"].items():
        area, _, what = key.partition(":")
        if now < float(entry.get("until") or 0) and what in WHAT:
            backed.append({"area": area, "what": WHAT[what], "until": round(float(entry["until"]), 1)})
    return {"enabled": enabled(cfg), "running": watcher_running(status, now),
            "fixes": status["fixes"][:KEEP_FIXES], "backedOff": sorted(backed, key=lambda b: b["until"])}
