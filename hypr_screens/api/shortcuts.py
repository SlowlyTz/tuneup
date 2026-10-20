"""Keys: the minimizer's shortcuts, recording one, the desktop key options."""
import copy

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
DEFAULT_FIXED_LABELS = {"off": "Off – both screens have desktops", "external": "The external monitor",
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
            "slots": [combo or None for combo in cfg["keybinds"][action]]}


def options_view(cfg: dict) -> dict:
    return {"desktop_keys": bool(cfg["desktop_keys"]), "default_fixed": cfg["default_fixed"],
            "fixed_desktops": cfg["fixed_desktops"]}


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
    is replaced while Tuneup runs (listed in "conflicts")."""
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
    """desktop_keys: true/false; default_fixed: "off" | "external" | "panel"; fixed_desktops: 1-10."""
    if name == "fixed_desktops":
        need(isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 10, "bad_value",
             "fixed_desktops must be 1-10")
    elif name == "desktop_keys":
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
        if name in ("desktop_keys", "fixed_desktops"):
            keybinds.write(cfg)
            keybinds.go_live(before[0], cfg)
        run_sync()
    return options_view(cfg)
