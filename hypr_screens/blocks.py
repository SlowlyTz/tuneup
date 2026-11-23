"""Omarchy's workspaces per monitor (default/hypr/monitor-workspaces.lua).

With that module every monitor owns a block of ten workspace ids -- block b
holds b*10+1 ... b*10+10 -- and Omarchy renumbers a workspace that sits on a
monitor outside that monitor's block, on every config reload and monitor
change. Tuneup's desktops therefore take their ids from these blocks; this
reads them (never assigns any): from Omarchy's state file, and for a monitor
not listed there yet from Omarchy's own function, which assigns and records it.

Without the module (an older Omarchy) none of this applies: available() is
False and Tuneup keeps its fixed ids.
"""
import os
from pathlib import Path

from hypr_screens import hypr

SLOTS = 10


def omarchy_path() -> Path:
    return Path(os.environ.get("OMARCHY_PATH") or "/usr/share/omarchy")


def available() -> bool:
    return (omarchy_path() / "default" / "hypr" / "monitor-workspaces.lua").is_file()


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "omarchy"


def first_id(block: int) -> int:
    return block * SLOTS + 1


def block_of(workspace: int) -> int:
    return (workspace - 1) // SLOTS


def read() -> dict[str, int]:
    """Connector -> block of the monitors plugged in (as Omarchy last wrote it)."""
    found: dict[str, int] = {}
    try:
        lines = (state_dir() / "monitor-workspaces").read_text().splitlines()
    except OSError:
        return found
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].isdigit() and parts[1]:
            found[parts[1]] = int(parts[0])
    return found


def of(names: list[str]) -> dict[str, int] | None:
    """Connector -> block for these monitors; None without Omarchy's module or
    when one of them has no block (Omarchy's Lua did not answer)."""
    if not available():
        return None
    found = read()
    missing = [name for name in names if name not in found]
    for name in missing:
        hypr.eval_lua(f"local monitor = hl.get_monitor({hypr.lua_string(name)}) "
                      "if monitor and o and o.workspaces then o.workspaces.workspace_id(monitor, 1) end")
    if missing:
        found = read()
    return found if all(name in found for name in names) else None


def merged() -> dict[int, int]:
    """Workspaces Omarchy moved into another monitor's block while theirs was
    unplugged: their id now -> the id they had."""
    found: dict[int, int] = {}
    try:
        lines = (state_dir() / "monitor-workspaces-merged").read_text().splitlines()
    except OSError:
        return found
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            found[int(parts[0])] = int(parts[1])
    return found
