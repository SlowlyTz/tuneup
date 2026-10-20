"""Glue: sync everything, and the state `tuneup state` prints."""
from hypr_screens import apply, config, desktops, hypr


def sync(event: str = "") -> list[str]:
    """Record connected screens, apply their settings, arrange desktops.

    event: "added" (a monitor was plugged in), "removed", "reload" or "".
    """
    with apply.locked("sync"):
        monitors = hypr.monitors(include_disabled=True)
        cfg = config.update(lambda fresh: config.record(fresh, monitors))
        done = apply.apply(cfg)
        if "reload" in done:
            desktops.mark_rules(False)  # a reload drops the workspace rules too
        return done + place_desktops(cfg, docking=event == "added")


def place_desktops(cfg: dict, docking: bool = False) -> list[str]:
    """The fixed desktop and desktops 1-10 where the role wants them; ["reload",
    ...] when rules pinning them to a screen had to go (call it under the sync lock)."""
    screens = desktops.resolve(cfg)
    if not screens.monitors:
        return []  # Hyprland did not answer (busy setting up a screen): not "all unplugged"
    if not screens.external:
        # The rules pinning desktops stay until a reload; harmless while
        # their screen is away, and replaced when it comes back.
        desktops.undock(screens)
    elif screens.role:
        desktops.arrange(screens, docking=docking)
    else:
        desktops.fold_fixed(screens)
        if desktops.rules_marked() and len(screens.monitors) > 1:
            # Workspace rules pinning desktops to one screen only go away
            # with a reload; the monitor settings are applied again after.
            # (With one screen on -- the lid closed -- they pin nothing.)
            desktops.mark_rules(False)
            apply.reset()
            return ["reload", *apply.apply(cfg)]
    return []


# --- the screen list and the state -------------------------------------------------

SETTING_LABELS = {
    "rotation": "Rotation",
    "scale": "Scale",
    "mode": "Resolution",
    "position": "Position",
    "one_desktop": "One desktop",
}


def screen_rows(cfg: dict, connected_ids: set[str]) -> list[dict]:
    def order(item):
        sid, screen = item
        section = 0 if screen.get("internal") else 1 if screen.get("favorite") else 2
        return (section, sid not in connected_ids, screen.get("name", ""))

    rows = []
    for sid, screen in sorted(cfg["screens"].items(), key=order):
        section = "Laptop" if screen.get("internal") else "Favorites" if screen.get("favorite") else "Known screens"
        settings = []
        for key in config.SETTING_KEYS:
            if key == "position" and screen.get("internal"):
                continue
            setting = config.get_setting(cfg, sid, key) or {}
            value = setting.get("value")
            when = setting.get("when")
            label = config.value_label(key, value)
            if key == "one_desktop" and value is None:
                label = f"default ({cfg.get('default_fixed', 'off')})"
            settings.append({
                "key": key,
                "label": SETTING_LABELS[key],
                "value": label,
                "set": value is not None,
                "when": "always" if not when else f"if {cfg['screens'].get(when, {}).get('name', '?')} connected",
                "active": value is not None and (not when or when in connected_ids),
            })
        rows.append({
            "id": sid,
            "name": screen.get("name", sid),
            "description": screen.get("description", ""),
            "connector": screen.get("connector", ""),
            "internal": bool(screen.get("internal")),
            "favorite": bool(screen.get("favorite")),
            "connected": sid in connected_ids,
            "section": section,
            "summary": config.summary(cfg, sid),
            "settings": settings,
        })
    return rows


def state(cfg: dict | None = None, message: str = "") -> dict:
    if cfg is None:
        everything = hypr.monitors(include_disabled=True)
        cfg = config.update(lambda fresh: config.record(fresh, everything))
    monitors = hypr.monitors()
    connected_ids = set(config.connected(monitors))
    return {
        "message": message,
        "status": desktops.status(cfg),
        "screens": screen_rows(cfg, connected_ids),
        "keybinds": [
            {"action": action, "label": label, "keys": cfg["keybinds"][action]}
            for action, label, _command in config.ACTIONS
        ],
        "options": [
            {"key": "desktop_keys", "label": "Desktop keys",
             "value": "on" if cfg["desktop_keys"] else "off"},
            {"key": "default_fixed", "label": "One desktop on new screens",
             "value": {"off": "off", "external": "external screen", "panel": "laptop"}[cfg["default_fixed"]]},
            {"key": "fixed_desktops", "label": "Desktops on the fixed screen", "value": str(cfg["fixed_desktops"])},
        ],
    }
