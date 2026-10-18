"""The enforcer's audit (see enforce.py): find what drifted, put it back.

Every check only looks; then what drifted is put back in one go -- the
screens by one sync (which places the desktops too), the desktops alone, the
look and the keys each by one eval -- unless that item is backed off. While
someone else's sync runs (the settings window, the CLI) the state is in
motion: the audit waits for its next round then.

A screen without a picture (drm.py) counts only once it is seen in two audits
in a row, so a screen that is still being set up is not taken for one; it is
dealt with once each time it goes dark.
"""
import os

from hypr_screens import apply, config, desktops, drm, engine, enforce, hypr, keybinds, look

PREVIEW_MARK = "look-preview"
# Screens seen dark in the last audit, and those dealt with while they stay dark.
_dark_before: set[str] = set()
_handled: set[str] = set()


class Audit:
    """One look at Hyprland: each query is made once, when first needed."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cache: dict[tuple, list[dict]] = {}

    def query(self, what: str, *args: str) -> list[dict]:
        if (what, *args) not in self.cache:
            self.cache[(what, *args)] = hypr.query_list(what, *args)
        return self.cache[(what, *args)]

    @property
    def monitors(self) -> list[dict]:
        return self.query("monitors")


# --- the settings window's look preview ------------------------------------------------


def mark_preview(on: bool) -> None:
    """The settings window shows a look it has not saved (this process): the
    audit leaves the look alone meanwhile."""
    path = config.runtime_dir() / PREVIEW_MARK
    if on:
        path.write_text(f"{os.getpid()}\n")
    else:
        path.unlink(missing_ok=True)


def previewing() -> bool:
    try:
        return enforce.alive(int((config.runtime_dir() / PREVIEW_MARK).read_text()))
    except (OSError, ValueError):
        return False


# --- the checks: what drifted (empty: nothing) ------------------------------------------


def screens(audit: Audit) -> list[str]:
    return [f"{name} moved or changed" for name in apply.drifted(audit.cfg, audit.monitors)]


def placement(audit: Audit) -> list[str]:
    screens_now = desktops.resolve(audit.cfg, audit.monitors)
    return desktops.misplaced(screens_now, audit.query("workspaces"), audit.query("workspacerules"))


def window_look(audit: Audit) -> list[str]:
    if not audit.cfg["look"] or previewing():
        return []
    return look.drifted(audit.cfg["look"])


def keys(audit: Audit) -> list[str]:
    return keybinds.missing(audit.cfg, audit.query("binds"))


# --- putting it back ------------------------------------------------------------------------


def fix_screens(cfg: dict) -> None:
    engine.sync()


def fix_desktops(cfg: dict) -> None:
    with apply.locked("sync"):
        engine.place_desktops(cfg)


def fix_look(cfg: dict) -> None:
    look.apply(cfg["look"])


def fix_keys(cfg: dict) -> None:
    keybinds.go_live(None, cfg)


# (area, item, check, fix); a sync for the screens places the desktops as well.
CHECKS = [
    ("screens", "layout", screens, fix_screens),
    ("desktops", "desktops", placement, fix_desktops),
    ("look", "look", window_look, fix_look),
    ("keys", "keys", keys, fix_keys),
]


def summary(details: list[str]) -> str:
    return "; ".join(details[:3]) + (f" (+{len(details) - 3})" if len(details) > 3 else "")


def run(cfg: dict | None = None) -> list[str]:
    """One audit; returns what was put back ("area: detail")."""
    if apply.busy("sync") or apply.busy("apply"):
        return []
    cfg = config.load() if cfg is None else cfg
    if not enforce.enabled(cfg):
        return dark_screens(Audit(cfg), recover=False)
    audit = Audit(cfg)
    found = [(area, item, check(audit), fix) for area, item, check, fix in CHECKS]
    due = [(area, item, details, fix) for area, item, details, fix in found
           if details and not enforce.backed_off(area, item)]
    synced = False
    fixed = []
    for area, item, details, fix in due:
        if not (synced and area == "desktops"):
            fix(cfg)
        synced = synced or area == "screens"
        enforce.record(area, item, summary(details))
        fixed.append(f"{area}: {summary(details)}")
    return fixed + dark_screens(Audit(cfg), recover=True)


def dark_screens(audit: Audit, recover: bool) -> list[str]:
    """Dark screens, once per time one goes dark: off and on again (with
    enforcement on); if that does not help, or may not be tried, tell the user
    what does."""
    global _dark_before
    dark = set(drm.dark(audit.monitors))
    new = (dark & _dark_before) - _handled
    _dark_before = dark
    _handled.intersection_update(dark)
    if not new:
        return []
    wanted = apply.desired(audit.cfg, audit.monitors)
    done = []
    for monitor in (m for m in audit.monitors if m["name"] in new):
        name = str(monitor["name"])
        _handled.add(name)
        shows = recover and drm.recover(monitor, wanted.get(name, {}).get("fields", {}))
        enforce.record("screens", "picture", f"{name} switched off and on" if shows
                       else f"{name} is dark" + (" after switching it off and on" if recover else ""))
        if not shows:
            drm.tell_user(name)
        done.append(f"screens: {name} without a picture")
    return done
