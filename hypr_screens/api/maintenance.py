"""The welcome after an install or an update, updating, and uninstalling.

An update and an uninstall run detached (their own session): both stop the
tray, which is this window's process. The update reports through its status
file (updates.read_status); the uninstall ends with the app gone.
"""
import subprocess
import sys

from hypr_screens import brand, config, updates
from hypr_screens.api.core import ApiError, endpoint, need


def welcome_view(cfg: dict) -> dict:
    """Shown once after the install (no version seen yet) and once after each
    update (the version seen is older than this one)."""
    current, seen = updates.current_version(), cfg["seen_version"]
    kind = "installed" if seen is None else "updated" if updates.version_key(seen) < updates.version_key(current) \
        else None
    return {"show": kind is not None, "kind": kind, "from": seen if kind == "updated" else None, "to": current,
            "releasesUrl": brand.RELEASES_URL}


@endpoint
def welcome() -> dict:
    return welcome_view(config.read())


@endpoint
def dismiss_welcome() -> dict:
    current = updates.current_version()
    return welcome_view(config.update(lambda cfg: cfg.__setitem__("seen_version", current)))


@endpoint
def check_update() -> dict:
    """{current, latest, available, commitsBehind, canUpdate, reason}; reason:
    null | "not_git" | "local_changes" | "diverged" | "offline"."""
    return updates.check()


def detached(*args: str, log_name: str) -> None:
    log = open(config.runtime_home() / log_name, "w")
    try:
        subprocess.Popen([sys.executable, str(brand.ROOT / brand.COMMAND), *args], stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True, cwd=str(brand.ROOT))
    except OSError as error:
        raise ApiError("unavailable", f"cannot start {brand.COMMAND} {args[0]}: {error}") from error
    finally:
        log.close()


@endpoint
def run_update() -> dict:
    """Starts the update; follow it with update_status(). The window closes
    while the tray restarts and opens again at the end."""
    need(updates.read_status()["state"] != "running", "busy", "an update is running already")
    updates.write_status(state="running", **{"from": updates.current_version(), "to": None}, log=[], error=None)
    detached("update", "--report", log_name=f"{brand.DIR}-update.log")
    return {"started": True}


@endpoint
def update_status() -> dict:
    """{state: "idle" | "running" | "done" | "failed", from, to, log (last lines), error}."""
    return updates.read_status()


@endpoint
def uninstall(keep_settings: bool) -> dict:
    """Starts removing Tuneup (see uninstall.py); the app is gone afterwards."""
    need(isinstance(keep_settings, bool), "bad_value", "keepSettings must be true or false")
    detached("uninstall", "--yes", *(["--keep-settings"] if keep_settings else []),
             log_name=f"{brand.DIR}-uninstall.log")
    return {"started": True}
