"""Screens without a picture, read from the kernel (/sys/class/drm, read only).

A known aquamarine bug: after an MST dock is unplugged, a CRTC can stay bound
to the dock's connector that is gone; a screen plugged in next (HDMI) is then
given that CRTC and stays dark although Hyprland lists it. The kernel shows
it: the new connector is "connected" but "disabled" (no CRTC drives it),
while a connector that is "disconnected" is still "enabled".

recover() switches the dark screen off and on again through its monitor rule,
so it is set up from scratch; if it stays dark, the user is told what helps.
"""
import shutil
import subprocess
import time
from pathlib import Path

from hypr_screens import apply, hypr
from hypr_screens.i18n import t

SYSFS = Path("/sys")
RECOVER_PAUSE = 1.0


def read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def connectors() -> dict[str, dict]:
    """{"DP-3": {"status": "connected", "enabled": "enabled"}, ...} (card0-DP-3 -> DP-3)."""
    found = {}
    for path in sorted((SYSFS / "class/drm").glob("card*-*")):
        name = path.name.partition("-")[2]
        if name and (path / "status").exists():
            found[name] = {"status": read(path / "status"), "enabled": read(path / "enabled")}
    return found


def stale(found: dict[str, dict]) -> list[str]:
    """Connectors that are gone but still hold a CRTC."""
    return sorted(name for name, c in found.items() if c["status"] == "disconnected" and c["enabled"] == "enabled")


def dark(monitors: list[dict], found: dict[str, dict] | None = None) -> list[str]:
    """Screens Hyprland drives that the kernel has no CRTC on."""
    found = connectors() if found is None else found
    return sorted(str(m["name"]) for m in monitors if not m.get("disabled")
                  and (found.get(str(m["name"])) or {}).get("status") == "connected"
                  and found[str(m["name"])]["enabled"] == "disabled")


def recover(monitor: dict, fields: dict) -> bool:
    """Off and on again, so aquamarine picks a CRTC anew; True if it shows now."""
    name = str(monitor["name"])
    hypr.eval_lua(f"hl.monitor({{ output = {hypr.lua_string(name)}, disabled = true }})")
    time.sleep(RECOVER_PAUSE)
    hypr.eval_lua(apply.monitor_rule(monitor, fields))
    time.sleep(RECOVER_PAUSE)
    return name not in dark([monitor])


def tell_user(name: str) -> None:
    notify = shutil.which("notify-send")
    if not notify:
        return
    body = t("{screen} is connected but shows nothing (a known Hyprland bug after unplugging a dock). "
             "Unplug it and plug it in again; if it stays dark, switch to another console and back "
             "(Ctrl+Alt+F2, then Ctrl+Alt+F1) or log out and in.", screen=name)
    try:
        subprocess.run([notify, "-a", "hypr-screens", t("Screen without a picture"), body],
                       check=False, capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass
