"""The fixed screen: with one external monitor attached, one screen keeps its
own desktops (workspace FIXED_WS, plus FIXED_WS+1 ... with the "fixed_desktops"
option above 1) and never shows desktops 1-10; the other holds desktops 1-10.
With several fixed desktops, the desktop keys act on the focused screen.

Which screen is fixed (the "role": "panel" = laptop, "external"):
  1. a temporary swap (`tuneup swap`), until the monitor is unplugged,
  2. the global default ("default_fixed": off, the external screen or the laptop).
A monitor that mirrors the laptop is no screen of its own here. Without a
role, desktops behave like stock Hyprland.

When an external fixed screen goes (unplugged, or set to mirror the laptop),
its windows go where the "unplug_windows" option says: onto the desktop the
laptop shows ("fold"), spread over desktops 6-10 (its desktop 1 onto 6, 2 onto
7 ..., the sixth and up all onto 10) and back once it is a screen again
("spread"), or closed ("close"). The scratch desktops
(scratch.FIRST and up) may show on any screen, the fixed one too.

The ids: with Omarchy's workspaces per monitor (see blocks.py) every screen's
desktops lie in that screen's block -- desktop n of the desk screen is its
block's n-th id, the fixed screen's desktop n likewise -- so Omarchy never
renumbers them. Without that module desktops 1-10 are workspaces 1-10 and the
fixed screen's are FIXED_WS and up, as before. Which ids are in use is written
to desktops.json in the runtime dir (the bar, the dock and the widgets read
it); when they change (a swap, another block, the first start after an
update), arrange() renumbers the workspaces from the ids written there before.
"""
import json
import os
from dataclasses import dataclass, field

from hypr_screens import blocks, config, hypr, scratch

FIXED_WS = int(os.environ.get("HYPR_SCREENS_FIXED_WS", "99"))
DESKTOPS = range(1, 11)
SLOTS = 10
# Out of every block (and below the scratch desktops' parked names): where a
# workspace waits while ids are handed round.
PARK_FROM = 9001


def fixed_count(cfg: dict) -> int:
    """How many desktops the fixed screen has (1-10)."""
    count = cfg.get("fixed_desktops", 1)
    return count if isinstance(count, int) and 1 <= count <= 10 else 1


def fixed_workspaces(count: int, first: int = FIXED_WS) -> range:
    """The fixed screen's desktops: `first` is its desktop 1, the next ids follow."""
    return range(first, first + count)


# --- the ids in use ------------------------------------------------------------------


def layout_file():
    return config.runtime_dir() / "desktops.json"


# Before desktops.json existed: Tuneup's own ids.
LEGACY = {"omarchy": False, "role": None, "desk_first": 1, "fixed_first": FIXED_WS, "fixed_count": 1}


def load_layout() -> dict:
    try:
        layout = json.loads(layout_file().read_text())
    except (OSError, json.JSONDecodeError):
        return dict(LEGACY)
    return layout if isinstance(layout, dict) else dict(LEGACY)


def save_layout(screens: "Screens") -> None:
    """What the bar, the dock, the widgets and the swipe guard go by -- and the
    ids the next change starts from."""
    layout = {
        "omarchy": screens.omarchy,
        "role": screens.role,
        "desk_monitor": screens.desk if screens.role else None,
        "desk_first": screens.desk_first,
        "fixed_monitor": screens.fixed if screens.role else None,
        # Tuneup's own ids never change; Omarchy's blocks have none without a role.
        "fixed_first": screens.fixed_first if screens.role or not screens.omarchy else None,
        "fixed_count": screens.count,
        "blocks": screens.blocks,
    }
    if layout != load_layout():
        layout_file().write_text(json.dumps(layout) + "\n")


def renumbered_file():
    return config.runtime_dir() / "renumbered.json"


def load_renumbered() -> dict[int, int]:
    try:
        notes = json.loads(renumbered_file().read_text())
        return {int(old): int(new) for old, new in notes.items()}
    except (OSError, json.JSONDecodeError, ValueError, AttributeError):
        return {}


def renumbered(lines: list[bytes]) -> None:
    """Omarchy renumbered workspaces (socket2: changeworkspaceid>>old,new). A
    scratch desktop goes back at once: those belong to no screen's block. While
    the desktops still have Tuneup's own ids (the first start after Omarchy
    brought its blocks), where they went is noted, so arrange() finds them."""
    pairs = []
    for line in lines:
        name, _, data = line.decode(errors="replace").partition(">>")
        old, _, new = data.partition(",")
        if name == "changeworkspaceid" and old.strip().isdigit() and new.strip().isdigit():
            pairs.append((int(old), int(new)))
    if not pairs:
        return
    layout = load_layout()
    notes = None if layout.get("omarchy") else load_renumbered()
    ours = set(ids_from(layout, "desk")) | set(ids_from(layout, "fixed"))
    for old, new in pairs:
        if old >= scratch.FIRST and new < scratch.FIRST and old < PARK_FROM:
            hypr.dispatch(f'hl.dsp.workspace.change_id({{ workspace = "{new}", id = {old} }})')
        elif notes is not None and old < PARK_FROM and new < PARK_FROM:
            earlier = [first for first, now in notes.items() if now == old]
            for first in earlier:
                notes[first] = new
            if not earlier and old in ours:
                notes[old] = new
    if notes:
        renumbered_file().write_text(json.dumps(notes) + "\n")


def ids_from(layout: dict, key: str) -> range:
    """All ten ids desktops of that kind ("desk", "fixed") had: none when there were none."""
    first = layout.get(f"{key}_first")
    return range(first, first + SLOTS) if isinstance(first, int) and first > 0 else range(0)


def override_file():
    return config.runtime_dir() / "fixed.json"


def load_override() -> dict:
    try:
        override = json.loads(override_file().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return override if isinstance(override, dict) else {}


def save_override(external_id: str, role: str) -> None:
    override_file().write_text(json.dumps({"external": external_id, "role": role}) + "\n")


def clear_override() -> None:
    override_file().unlink(missing_ok=True)


# Which screen was fixed: once it is unplugged, Hyprland no longer tells.
def role_file():
    return config.runtime_dir() / "fixed-role"


def remember_role(role: str | None) -> None:
    if role:
        role_file().write_text(role + "\n")
    else:
        role_file().unlink(missing_ok=True)


def last_role() -> str:
    try:
        return role_file().read_text().strip()
    except OSError:
        return ""


# Windows spread over desktops 6-10: address -> [the fixed desktop they came from, where they went].
def spread_file():
    return config.runtime_dir() / "spread.json"


def load_spread() -> dict:
    try:
        spread = json.loads(spread_file().read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return spread if isinstance(spread, dict) else {}


@dataclass
class Screens:
    monitors: list[dict] = field(default_factory=list)
    panel: str = ""
    external: str = ""
    panel_id: str = ""
    external_id: str = ""
    role: str | None = None
    count: int = 1
    omarchy: bool = False       # Omarchy's blocks decide the ids
    desk_first: int = 1         # desktop 1 of the desk screen (the laptop's without a role)
    fixed_first: int = FIXED_WS  # desktop 1 of the fixed screen
    blocks: dict = field(default_factory=dict)

    @property
    def fixed_set(self) -> range:
        return fixed_workspaces(self.count, self.fixed_first)

    @property
    def desk_set(self) -> range:
        return range(self.desk_first, self.desk_first + SLOTS)

    @property
    def fixed(self) -> str:
        return self.external if self.role == "external" else self.panel

    @property
    def desk(self) -> str:
        return self.panel if self.role == "external" else self.external

    def workspace_on(self, name: str) -> int:
        for monitor in self.monitors:
            if monitor.get("name") == name:
                return int((monitor.get("activeWorkspace") or {}).get("id") or 0)
        return 0

    def at_home(self, name: str) -> bool:
        """The fixed screen shows one of its desktops, or a scratch desktop."""
        showing = self.workspace_on(name)
        return showing in self.fixed_set or scratch.FIRST <= showing < PARK_FROM

    @property
    def focused(self) -> dict:
        return next((monitor for monitor in self.monitors if monitor.get("focused")), {})


def decide_role(cfg: dict, panel_id: str, external_id: str, ids: set[str], swaps: bool = True) -> str | None:
    override = load_override() if swaps else {}
    if override.get("external") == external_id and override.get("role") in ("panel", "external"):
        return override["role"]
    default = cfg.get("default_fixed", "off")
    return default if default in ("panel", "external") else None


def resolve(cfg: dict, monitors: list[dict] | None = None) -> Screens:
    monitors = [m for m in (monitors if monitors is not None else hypr.monitors()) if not m.get("disabled") and not config.is_mirror(m)]
    screens = Screens(monitors=monitors, count=fixed_count(cfg))
    panel = next((m for m in monitors if config.is_internal(m)), None)
    external = next((m for m in monitors if not config.is_internal(m)), None)
    if panel:
        screens.panel, screens.panel_id = str(panel["name"]), config.screen_id(panel)
    if external:
        screens.external, screens.external_id = str(external["name"]), config.screen_id(external)
    if panel and external:
        ids = set(config.connected(monitors))
        screens.role = decide_role(cfg, screens.panel_id, screens.external_id, ids)
    place_ids(screens)
    return screens


def place_ids(screens: Screens) -> None:
    """The ids of the desktops: from Omarchy's blocks when it has them."""
    names = [str(monitor["name"]) for monitor in screens.monitors]
    found = blocks.of(names) if names else None
    if found is None:
        return
    screens.omarchy, screens.blocks = True, {name: found[name] for name in names}
    home = screens.desk if screens.role else screens.panel or screens.external
    if home:
        screens.desk_first = blocks.first_id(found[home])
    if screens.role:
        screens.fixed_first = blocks.first_id(found[screens.fixed])


# --- building blocks -----------------------------------------------------------


def move_windows(source: int, target: int) -> None:
    """Move every window of workspace `source` to `target` without following."""
    for client in hypr.query_list("clients"):
        if (client.get("workspace") or {}).get("id") == source:
            hypr.dispatch(
                f'hl.dsp.window.move({{ workspace = "{target}", follow = false, window = "address:{client["address"]}" }})'
            )


def pin(workspace: int, monitor: str, persistent: bool = False) -> None:
    """The rule covers a workspace that does not exist yet; the move pulls over
    one that already sits elsewhere -- without it, focusing it would just jump
    to whichever monitor owns it. Persistent: it exists even while empty (the
    fixed screen's desktops, so the bar and swiping know all of them)."""
    keep = ", persistent = true" if persistent else ""
    hypr.eval_lua(f'hl.workspace_rule({{ workspace = "{workspace}", monitor = {hypr.lua_string(monitor)}{keep} }})')
    hypr.dispatch(f'hl.dsp.workspace.move({{ workspace = "{workspace}", monitor = {hypr.lua_string(monitor)} }})')


def hold_fixed(screens: Screens) -> None:
    """Keep the fixed screen on one of its desktops, without stealing focus."""
    fresh = resolve_names(screens)
    if fresh.at_home(screens.fixed):
        return
    first = screens.fixed_set[0]
    pin(first, screens.fixed)
    refocus = fresh.focused.get("name", "")
    hypr.dispatch(f"hl.dsp.focus({{ monitor = {hypr.lua_string(screens.fixed)} }})")
    hypr.dispatch(f'hl.dsp.focus({{ workspace = "{first}" }})')
    if refocus and refocus != screens.fixed:
        hypr.dispatch(f"hl.dsp.focus({{ monitor = {hypr.lua_string(refocus)} }})")


def resolve_names(screens: Screens) -> Screens:
    """Same roles and ids, fresh monitor data."""
    return Screens(
        monitors=[m for m in hypr.monitors() if not m.get("disabled") and not config.is_mirror(m)],
        panel=screens.panel,
        external=screens.external,
        panel_id=screens.panel_id,
        external_id=screens.external_id,
        role=screens.role,
        count=screens.count,
        omarchy=screens.omarchy,
        desk_first=screens.desk_first,
        fixed_first=screens.fixed_first,
        blocks=screens.blocks,
    )


def cursor() -> tuple[int, int] | None:
    try:
        x, y = hypr.hyprctl("cursorpos").replace(",", " ").split()[:2]
        return int(float(x)), int(float(y))
    except ValueError:
        return None


def mark_rules(active: bool) -> None:
    marker = config.runtime_dir() / "rules"
    if active:
        marker.touch()
    else:
        marker.unlink(missing_ok=True)


def rules_marked() -> bool:
    return (config.runtime_dir() / "rules").exists()


def misplaced(screens: Screens, workspaces: list[dict], rules: list[dict]) -> list[str]:
    """What is not where the role wants it (empty: all in place): the fixed
    screen off its desktops, a desktop 1-10 on it (or one of its desktops
    elsewhere), a rule pinning a desktop elsewhere; without a fixed screen,
    windows left on the fixed desktops."""
    if not screens.role:
        if screens.omarchy:
            return []  # every screen has desktops of its own (Omarchy's)
        left = [w["id"] for w in workspaces if w.get("id") in screens.fixed_set and w.get("windows")]
        return [f"windows on desktop {ws}" for ws in left]
    found = []
    if not screens.at_home(screens.fixed):
        found.append(f"{screens.fixed} does not show desktop {screens.fixed_set[0]}")
    found += [f"desktop {w['id']} on {screens.fixed}" for w in workspaces
              if w.get("id") in screens.desk_set and w.get("monitor") == screens.fixed]
    found += [f"desktop {w['id']} on {w.get('monitor')}" for w in workspaces
              if w.get("id") in screens.fixed_set and w.get("windows") and w.get("monitor") != screens.fixed]
    pinned = {str(rule.get("workspaceString")): rule.get("monitor") for rule in rules}
    if pinned:
        wanted = {**{str(ws): screens.fixed for ws in screens.fixed_set},
                  **{str(ws): screens.desk for ws in screens.desk_set}}
        found += [f"rule for desktop {ws} on {pinned.get(ws) or 'no screen'}"
                  for ws, monitor in wanted.items() if pinned.get(ws) != monitor]
    return found


# --- actions ---------------------------------------------------------------------


def renumber(moves: dict[int, int], keep: bool = True) -> dict[int, int]:
    """Workspaces to other ids (old -> new), by way of ids out of every block
    (PARK_FROM and up), so two kinds of desktops can trade theirs. keep: the
    workspace itself gets the new id (windows, layout and view stay together);
    else its windows move into the new id -- a workspace created that way is a
    new one to Omarchy, which drops what it remembered under that id. A new id
    another workspace holds gets the windows. Returns new -> where each one
    waits when `new` is None (just parked)."""
    present = {int(w["id"]) for w in hypr.query_list("workspaces") if isinstance(w.get("id"), int)}
    moves = {old: new for old, new in moves.items() if old in present and old != new}
    parked: dict[int, int] = {}
    wait = PARK_FROM - 1
    for old in sorted(moves):
        wait += 1
        while wait in present:
            wait += 1
        hypr.dispatch(f'hl.dsp.workspace.change_id({{ workspace = "{old}", id = {wait} }})')
        parked[wait] = moves[old]
    taken = present - set(moves)
    for wait, new in parked.items():
        if new is None:
            continue
        if keep and new not in taken:
            hypr.dispatch(f'hl.dsp.workspace.change_id({{ workspace = "{wait}", id = {new} }})')
        else:
            move_windows(wait, new)
    return parked


def realign(before: dict, screens: Screens, showing: int = 0) -> None:
    """Desktops still on the ids they had before (desktops.json) -- another
    block, a swap, Tuneup's own ids before Omarchy's blocks -- go to today's.
    showing: a desk desktop that becomes the fixed screen's desktop 1 (the
    laptop's, docking with the laptop fixed)."""
    moves = {}
    notes = load_renumbered()  # where Omarchy put them meanwhile
    for key, first in (("desk", screens.desk_first), ("fixed", screens.fixed_first)):
        old = ids_from(before, key)
        if old and old[0] != first:
            moves.update({notes.get(ws, ws): first + index for index, ws in enumerate(old)})
    if showing:
        moves[showing] = screens.fixed_set[0]
    renumber(moves)
    renumbered_file().unlink(missing_ok=True)
    # The old fixed desktops were kept by persistent rules: those go.
    now = set(screens.desk_set) | set(range(screens.fixed_first, screens.fixed_first + SLOTS))
    for workspace in ids_from(before, "fixed"):
        if workspace not in now and ids_from(before, "fixed")[0] != screens.fixed_first:
            hypr.eval_lua(f'hl.workspace_rule({{ workspace = "{workspace}", persistent = false }})')


def arrange(screens: Screens, docking: bool = False) -> None:
    """Put the fixed desktops and desktops 1-10 where the role wants them.

    On docking, the laptop's visible windows stay on the laptop when it becomes
    the fixed screen, and focus goes to the desk screen (the pointer stays put).
    """
    if not screens.role:
        return
    before = load_layout()
    first = screens.fixed_set[0]
    showing = screens.workspace_on(screens.fixed) if docking and screens.role == "panel" else 0
    if screens.omarchy:
        # The desktop the laptop showed becomes its desktop 1, the others go to the desk screen's block.
        realign(before, screens, showing if showing in ids_from(before, "desk") else 0)
    elif showing in screens.desk_set:
        # What the laptop showed is now one of the desk screen's desktops: its windows stay.
        pin(first, screens.fixed)
        move_windows(showing, first)
    position = cursor() if docking else None
    pin(first, screens.fixed)
    for workspace in screens.fixed_set[1:]:
        pin(workspace, screens.fixed, persistent=True)
    for workspace in screens.desk_set:
        pin(workspace, screens.desk)
    mark_rules(True)
    remember_role(screens.role)
    save_layout(screens)
    if screens.role == "external":
        bring_back(screens)
    hold_fixed(screens)
    if docking:
        hypr.dispatch(f"hl.dsp.focus({{ monitor = {hypr.lua_string(screens.desk)} }})")
        if position:
            hypr.dispatch(f"hl.dsp.cursor.move({{ x = {position[0]}, y = {position[1]} }})")


def left_behind(layout: dict, key: str) -> dict[int, int]:
    """Where the desktops of that kind ("fixed", "desk") in `layout` are now:
    workspace id -> desktop number. Omarchy moves those of an unplugged screen
    into the laptop's block (and remembers where they came from)."""
    ids = ids_from(layout, key)
    if not ids:
        return {}
    merged = blocks.merged() if layout.get("omarchy") else {}
    # an id Omarchy gave to a desktop from elsewhere is that one's
    found = {ws: ws - ids[0] + 1 for ws in ids if merged.get(ws, ws) == ws}
    for now, was in merged.items():
        if was in ids:
            found[now] = was - ids[0] + 1
    return found


def park(sources: dict[int, int]) -> dict[int, int]:
    """Omarchy's blocks: those workspaces out of the laptop's block first, so
    their ids are free and what Omarchy remembers about them does not bring
    them back later. Returns the waiting id -> desktop number."""
    if not sources:
        return {}
    present = {w["id"] for w in hypr.query_list("workspaces")}
    order = sorted(ws for ws in sources if ws in present)
    parked = renumber({ws: None for ws in order})
    by_old = dict(zip(order, sorted(parked)))
    return {by_old[ws]: sources[ws] for ws in order}


def fold_fixed(screens: Screens, sources: dict[int, int] | None = None) -> None:
    """Without a fixed screen its desktops mean nothing: move their windows to
    the desktop the laptop shows, or desktop 1. (All ten possible ones: the
    option may have been larger before.)"""
    layout = load_layout()
    if sources is None:
        sources = left_behind(layout, "fixed")
    first = ids_from(layout, "fixed")
    # Tuneup's fixed desktop 1 as long as it exists (as before); the others,
    # kept by their persistent rule until a reload, only while windows are left on them
    left = [w["id"] for w in hypr.query_list("workspaces")
            if w.get("id") in sources and (w.get("windows") or (first and w.get("id") == first[0]))]
    if not left:
        return
    target = screens.workspace_on(screens.panel)
    if target not in screens.desk_set or target in sources:
        target = screens.desk_first
    for workspace in left:
        move_windows(workspace, target)
    hypr.dispatch(f'hl.dsp.focus({{ workspace = "{target}" }})')


SPREAD_FROM = 6


def spread_target(slot: int, desk_first: int = 1) -> int:
    """The fixed screen's desktop 1 onto desktop 6, 2 onto 7 ..., the sixth and up onto 10."""
    return desk_first - 1 + min(SPREAD_FROM + slot - 1, SLOTS)


def left_on_fixed(sources: dict[int, int] | None = None) -> dict[int, list[str]]:
    """The fixed desktops that still have windows: workspace -> window addresses."""
    if sources is None:
        sources = left_behind(load_layout(), "fixed")
    found: dict[int, list[str]] = {}
    for client in hypr.query_list("clients"):
        workspace = (client.get("workspace") or {}).get("id")
        if workspace in sources:
            found.setdefault(workspace, []).append(str(client["address"]))
    return found


def spread(screens: Screens, sources: dict[int, int] | None = None) -> None:
    """The external screen's windows onto desktops 6-10, joining what is there already."""
    if sources is None:
        sources = left_behind(load_layout(), "fixed")
    alive = {str(client.get("address")) for client in hypr.query_list("clients")}
    moved = {address: entry for address, entry in load_spread().items() if address in alive}
    for workspace, addresses in left_on_fixed(sources).items():
        target = spread_target(sources[workspace], screens.desk_first)
        for address in addresses:
            hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{target}", follow = false, window = "address:{address}" }})')
            moved[address] = [sources[workspace], target]
    if moved:
        spread_file().write_text(json.dumps(moved) + "\n")
    showing = screens.workspace_on(screens.panel)
    if showing in sources:
        hypr.dispatch(f'hl.dsp.focus({{ workspace = "{spread_target(sources[showing], screens.desk_first)}" }})')


def close_left(screens: Screens, sources: dict[int, int] | None = None) -> None:
    """Close the external screen's windows (as SUPER + W would: an app may still ask to save)."""
    if sources is None:
        sources = left_behind(load_layout(), "fixed")
    for addresses in left_on_fixed(sources).values():
        for address in addresses:
            hypr.dispatch(f'hl.dsp.window.close({{ window = "address:{address}" }})')
    if screens.workspace_on(screens.panel) in sources:
        hypr.dispatch(f'hl.dsp.focus({{ workspace = "{screens.desk_first}" }})')


def bring_back(screens: Screens) -> None:
    """Spread windows back onto the external screen's desktops -- those still where they were put
    (onto its last desktop when it has fewer now)."""
    moved = load_spread()
    if not moved:
        return
    spread_file().unlink(missing_ok=True)
    where = {str(c.get("address")): (c.get("workspace") or {}).get("id") for c in hypr.query_list("clients")}
    for address, (desktop, target) in moved.items():
        if where.get(address) == target:
            # Written before the slots: Tuneup's own id of that desktop.
            slot = desktop - FIXED_WS + 1 if desktop >= FIXED_WS else desktop
            workspace = screens.fixed_set[min(max(slot, 1), screens.count) - 1]
            hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{workspace}", follow = false, window = "address:{address}" }})')


def would_close(cfg: dict) -> bool:
    """Unplugging now would close windows: the option says "close", the fixed
    screen was the external one, and windows sit on its desktops."""
    return cfg.get("unplug_windows") == "close" and last_role() == "external" and bool(left_on_fixed())


def external_listed() -> bool:
    """Hyprland still lists a screen that is not the laptop's -- mirrored, or
    asleep -- so the external screen is not really gone."""
    return any(not config.is_internal(m) and not m.get("disabled") for m in hypr.monitors(include_disabled=True))


def undock(screens: Screens, windows: str = "fold") -> None:
    """No external screen any more: the fixed desktops' windows go where `windows`
    says ("fold", "spread", "close") -- if they were the external screen's.

    With Omarchy's blocks the external screen's desktops may already sit in the
    laptop's block (Omarchy moves them there at once): they are found by what
    Omarchy remembers, put aside, and the desk desktops of an external desk
    screen get their numbers back in the laptop's block."""
    clear_override()
    was_external = last_role() == "external"
    remember_role(None)
    before = load_layout()
    sources = left_behind(before, "fixed")
    if screens.omarchy:
        sources = park(sources)
        old_desk = ids_from(before, "desk")
        if old_desk and old_desk[0] != screens.desk_first:
            desk = left_behind(before, "desk")
            moves = {ws: screens.desk_first + slot - 1 for ws, slot in desk.items()}
            showing = screens.workspace_on(screens.panel)
            renumber(moves, keep=False)
            if showing in moves:
                hypr.dispatch(f'hl.dsp.focus({{ workspace = "{moves[showing]}" }})')
    if was_external and windows == "spread":
        spread(screens, sources)
    elif was_external and windows == "close":
        close_left(screens, sources)
    else:
        fold_fixed(screens, sources)
    save_layout(screens)


def swap(cfg: dict, want: str | None = None) -> Screens:
    """Make `want` ("panel"/"external") the fixed screen, or toggle; lasts until
    the monitor is unplugged. Windows and layouts travel with their workspaces."""
    screens = resolve(cfg)
    if not screens.external:
        raise RuntimeError("no external monitor")
    current = screens.role or "panel"
    want = want or ("external" if current == "panel" else "panel")
    if want != screens.role:
        if screens.role:
            hypr.dispatch(
                f"hl.dsp.workspace.swap_monitors({{ monitor1 = {hypr.lua_string(screens.panel)}, "
                f"monitor2 = {hypr.lua_string(screens.external)} }})"
            )
        ids = set(config.connected(screens.monitors))
        if want == decide_role(cfg, screens.panel_id, screens.external_id, ids, swaps=False):
            clear_override()  # back to what the settings say
        else:
            save_override(screens.external_id, want)
        screens.role = want
    fresh = resolve_names(screens)
    place_ids(fresh)
    arrange(fresh, docking=screens.role is not None)
    return screens


def on_fixed(screens: Screens) -> bool:
    """The focused screen is the fixed one and has more than one desktop: the
    desktop keys act on its own desktops."""
    return bool(screens.role) and screens.count > 1 and screens.focused.get("name") == screens.fixed


# Omarchy's own desktop actions: desktop n of the focused screen.
OMARCHY_ACTIONS = {"switch": "o.workspaces.focus({n})", "move": "o.workspaces.move_window({n})",
                   "move-silent": "o.workspaces.move_window({n}, false)"}


def switch(cfg: dict, action: str, index: int, fixed: bool | None = None) -> None:
    """Desktop `index` of the focused screen -- of the fixed one when it has the
    focus and several desktops (or with fixed=True), else desktops 1-10."""
    if index not in DESKTOPS:
        raise ValueError("desktop must be 1-10")
    screens = resolve(cfg)
    if screens.omarchy and not screens.role:
        hypr.dispatch(OMARCHY_ACTIONS[action].format(n=index))
        return
    there = on_fixed(screens) if fixed is None else bool(fixed and screens.role)
    if there and index > screens.count:
        return  # the fixed screen has fewer desktops
    workspace = screens.fixed_set[0] + index - 1 if there else screens.desk_first + index - 1
    if screens.role:
        pin(workspace, screens.fixed if there else screens.desk, persistent=there and workspace != screens.fixed_set[0])
    if action == "switch":
        hypr.dispatch(f'hl.dsp.focus({{ workspace = "{workspace}" }})')
    elif action == "move":
        hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{workspace}" }})')
    else:
        hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{workspace}", follow = false }})')
    if screens.role:
        hold_fixed(screens)


def step(cfg: dict, direction: int) -> None:
    """Switch to the next/previous desktop that has windows (of the fixed screen
    when it has the focus and several desktops)."""
    screens = resolve(cfg)
    if on_fixed(screens):
        current = screens.workspace_on(screens.fixed)
        used = sorted(
            {w["id"] for w in hypr.query_list("workspaces") if w.get("id") in screens.fixed_set and w.get("windows", 0) > 0}
            | ({current} if current in screens.fixed_set else set())
        )
        if used:
            target = used[0] if current not in used else used[(used.index(current) + direction) % len(used)]
            switch(cfg, "switch", target - screens.fixed_set[0] + 1, fixed=True)
        return
    focused = screens.focused
    if screens.role:
        current = screens.workspace_on(screens.desk)
        desk = screens.desk_set
    else:
        current = int((focused.get("activeWorkspace") or {}).get("id") or 0)
        block = screens.blocks.get(str(focused.get("name", ""))) if screens.omarchy else None
        desk = range(blocks.first_id(block), blocks.first_id(block) + SLOTS) if block is not None else DESKTOPS
    used = sorted(
        {w["id"] for w in hypr.query_list("workspaces") if w.get("id") in desk and w.get("windows", 0) > 0}
        | ({current} if current in desk else set())
    )
    if not used:
        return
    target = used[0] if current not in used else used[(used.index(current) + direction) % len(used)]
    switch(cfg, "switch", target - desk[0] + 1)


def cycle(direction: int) -> None:
    """Focus the next visible window in screen order (left to right)."""
    monitors = [m for m in hypr.monitors() if not m.get("disabled") and not config.is_mirror(m)]
    visible = {(m.get("activeWorkspace") or {}).get("id") for m in monitors}
    focused_id = next((m.get("id") for m in monitors if m.get("focused")), None)
    active = str((hypr.query("activewindow") or {}).get("address") or "")
    windows = sorted(
        (
            c
            for c in hypr.query_list("clients")
            if c.get("mapped") and (c.get("workspace") or {}).get("id") in visible
        ),
        key=lambda c: (c["at"][0], c["at"][1], c["address"]),
    )
    if not windows:
        return
    addresses = [c["address"] for c in windows]
    target = windows[0] if active not in addresses else windows[(addresses.index(active) + direction) % len(windows)]
    # Focusing a window on another monitor makes Hyprland focus that monitor
    # first, which briefly activates its last window -- a border flicker.
    # Warping the pointer onto the target focuses it in one step (follow_mouse).
    if target.get("monitor") != focused_id:
        x = target["at"][0] + target["size"][0] // 2
        y = target["at"][1] + target["size"][1] // 2
        hypr.dispatch(f"hl.dsp.cursor.move({{ x = {x}, y = {y} }})")
    hypr.dispatch(f'hl.dsp.focus({{ window = "address:{target["address"]}" }})')


def status(cfg: dict) -> dict:
    screens = resolve(cfg)
    swapped = False
    if screens.external_id and load_override().get("external") == screens.external_id:
        ids = set(config.connected(screens.monitors))
        swapped = screens.role != decide_role(cfg, screens.panel_id, screens.external_id, ids, swaps=False)
    return {
        "panel": screens.panel or None,
        "external": screens.external or None,
        "panel_id": screens.panel_id or None,
        "external_id": screens.external_id or None,
        "fixed": screens.role,
        "swapped": swapped,
        "fixed_workspace": screens.fixed_set[0],
        "fixed_workspaces": list(screens.fixed_set),
    }
