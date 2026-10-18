"""The turned virtual camera: its state, switching it, the one-time setup, the preview."""
import base64
import time

from hypr_screens import config
from hypr_screens import camera as camera_mod
from hypr_screens.api.core import endpoint, need, settings

PREVIEW_FRESH_SECONDS = 3.0


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
