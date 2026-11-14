"""Keys: the minimizer's shortcuts, recording one, the desktop key options."""
import copy
import threading
import time

from hypr_screens import config, hypr, keybinds
from hypr_screens.api.core import ApiError, endpoint, need, settings, run_sync

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
DEFAULT_FIXED_LABELS = {"off": "Off – both screens share desktops 1–10", "external": "The external monitor",
                        "panel": "The laptop"}

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
            "slots": [keybinds.normalize(combo) or combo or None for combo in cfg["keybinds"][action]]}


def options_view(cfg: dict) -> dict:
    return {"desktop_keys": bool(cfg["desktop_keys"]), "default_fixed": cfg["default_fixed"],
            "fixed_desktops": cfg["fixed_desktops"], "unplug_windows": cfg["unplug_windows"],
            "scratch": bool(cfg["scratch"]),
            "scratch_shift_s": bool(cfg["scratch_shift_s"]), "scratch_kept": cfg["scratch_kept"],
            "scratch_swipe": bool(cfg["scratch_swipe"]),
            **{name: bool(cfg[name]) for name in config.SWITCHES}}


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
    is replaced while Tuneup runs (listed in "conflicts"). A key alone (Q, Space)
    is refused: it would stop working in every app. "live" is false when
    Hyprland did not take the change (it holds after the next reload)."""
    need(isinstance(action, str) and action in config.DEFAULT_KEYBINDS, "bad_value", f"unknown action: {action!r}")
    need(type(slot) is int and slot in (0, 1), "bad_value", "slot must be 0 or 1")
    need(combo is None or isinstance(combo, str), "bad_value", "combo must be text")
    raw = (combo or "").strip()
    combo = keybinds.normalize(raw) if raw else ""
    need(not raw or combo, "bad_value", f"not a key combination: {raw!r}")
    if combo:
        combo = keybinds.check_combo(combo)
    others = keybinds.conflicts(combo) if combo else []  # asked of Hyprland before the lock is taken
    before = []

    def mutate(cfg):
        before.append(copy.deepcopy(cfg))
        for other, combos in cfg["keybinds"].items():
            for index, existing in enumerate(combos):
                if combo and (other, index) != (action, slot) and keybinds.normalize(existing) == combo:
                    combos[index] = ""
        keybinds.set_key(cfg, action, slot, combo, others)
        return cfg["keybinds"] != before[0]["keybinds"]
    live = True
    with config.locked():  # the Lua file follows the settings, whoever else writes
        cfg = config.update(mutate)
        changed = cfg["keybinds"] != before[0]["keybinds"]
        if changed:
            keybinds.write(cfg)
    if changed:
        live = keybinds.go_live(before[0], cfg)
    return {**action_view(cfg, action), "conflicts": others, "live": live}


# A capture is running: Hyprland is in the empty keymap, where none of the
# usual keys (Super+W included) work until it ends.
_capturing = False
_capture_until = 0.0
_capture_lock = threading.Lock()
# The page asks key_capture_active() while it records; without a question for
# this long (the page is gone, the window closed in a race) the keys come back.
CAPTURE_GRACE_SECONDS = 4.0
CAPTURE_START_SECONDS = 10.0


def _watch_capture() -> None:
    """Gives the keys back when the page stops asking."""
    while True:
        time.sleep(0.5)
        with _capture_lock:
            if not _capturing:
                return
            expired = time.monotonic() > _capture_until
        if expired:
            end_key_capture()
            return


@endpoint
def begin_key_capture() -> dict:
    """While the page records a shortcut: an empty Hyprland keymap, so keys that
    are bound already reach the page instead of firing (Esc gets out of it and
    reaches the page as well). Fails when Hyprland does not switch."""
    global _capturing, _capture_until
    with _capture_lock:
        if hypr.rejected(hypr.dispatch(f'hl.dsp.submap("{keybinds.RECORD_SUBMAP}")')):
            raise ApiError("capture_failed", "Hyprland did not switch to the recording keymap.")
        _capturing = True
        _capture_until = time.monotonic() + CAPTURE_START_SECONDS
    threading.Thread(target=_watch_capture, daemon=True).start()
    return {"ok": True}


@endpoint
def key_capture_active() -> dict:
    """Whether Hyprland is still in the recording keymap (the page asks about
    twice a second while it records; Esc or anything else may have left it)."""
    global _capturing, _capture_until
    reply = hypr.hyprctl("submap").strip()
    with _capture_lock:
        if _capturing and not hypr.rejected(reply) and reply != keybinds.RECORD_SUBMAP:
            _capturing = False
        _capture_until = time.monotonic() + CAPTURE_GRACE_SECONDS
        return {"active": _capturing}


@endpoint
def end_key_capture() -> dict:
    global _capturing
    with _capture_lock:
        hypr.dispatch('hl.dsp.submap("reset")')
        _capturing = False
    return {"ok": True}


def release_key_capture() -> None:
    """The window closes or the app quits while recording: give the keys back
    (the page may be gone before it could end the capture itself)."""
    if _capturing:
        end_key_capture()


# Only these change where desktops live or what happens to windows of an unplugged screen.
SYNC_OPTIONS = ("default_fixed", "fixed_desktops", "unplug_windows", "desktop_keys", "scratch", "scratch_kept")


@endpoint
def set_option(name: str, value: object) -> dict:
    """desktop_keys, scratch, scratch_shift_s, scratch_swipe and config.SWITCHES (dock, taskbar,
    minimize_animation, float_in_front, resize_swipe, no_warps): true/false; default_fixed: "off" |
    "external" | "panel"; fixed_desktops, scratch_kept: 1-10; unplug_windows: "fold" | "spread" | "close"."""
    if name in ("fixed_desktops", "scratch_kept"):
        need(isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 10, "bad_value",
             f"{name} must be 1-10")
    elif name in ("desktop_keys", "scratch", "scratch_shift_s", "scratch_swipe", *config.SWITCHES):
        need(isinstance(value, bool), "bad_value", f"{name} must be true or false")
    elif name == "default_fixed":
        need(value in config.FIXED_DEFAULTS, "bad_value", f"default_fixed must be one of {config.FIXED_DEFAULTS}")
    elif name == "unplug_windows":
        need(value in config.UNPLUG_CHOICES, "bad_value", f"unplug_windows must be one of {config.UNPLUG_CHOICES}")
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
        keybinds.option_changed(before[0], cfg, name)
        reloaded = name in keybinds.RELOAD_OPTIONS and before[0][name] and not value
        if name in SYNC_OPTIONS or reloaded:
            run_sync()  # a reload resets the screens' settings too
    return options_view(cfg)
