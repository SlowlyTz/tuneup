"""Sound: outputs, inputs, app streams and force mute."""

from hypr_screens import config, sound
from hypr_screens.api.core import endpoint, need, is_number, settings

SOUND_ICONS = {"audio-input-microphone-symbolic": "mic", "audio-headphones-symbolic": "headphones",
               "video-display-symbolic": "tv", "audio-speakers-symbolic": "speaker"}


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
