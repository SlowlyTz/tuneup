"""Moving hypr-screens' files to Tuneup's names, once (run by `tuneup setup`,
which the installer and every update run).

- $XDG_RUNTIME_DIR/hypr-screens -> tuneup (first: the config lock lives there)
- ~/.config/hypr-screens -> ~/.config/tuneup
- ~/.config/hypr/hypr_screens.lua -> tuneup.lua, and the require line in
  hyprland.lua; the watcher and tray lines in autostart.lua, if any

A folder is renamed in one step and its old name stays as a symlink to the new
one, so what still uses the old path (a running watcher, an old widget plugin)
finds the same files. When both folders exist, nothing in the new one is
replaced: what only the old one has is moved over, the rest of the old one is
kept as hypr-screens.old. Running it again changes nothing.
"""
import re
from pathlib import Path

from hypr_screens import brand, config, keybinds

AUTOSTART_COMMAND = re.compile(r"\bhypr-screens(?=\s+(watch|tray)\b)")
# Our processes started from autostart.lua, under either name (uninstalling removes them).
OUR_AUTOSTART = re.compile(r"\b(tuneup|hypr-screens)\s+(watch|tray)\b")


def move_folder(old: Path, new: Path) -> list[str]:
    if not old.is_dir() or old.is_symlink():
        return []
    if not new.exists():
        old.rename(new)
    else:
        for item in sorted(old.iterdir()):
            if not (new / item.name).exists():
                item.rename(new / item.name)
        if any(old.iterdir()):
            old.rename(unused(old.with_name(old.name + ".old")))
        else:
            old.rmdir()
    old.symlink_to(new)
    return [f"{old} -> {new}"]


def unused(path: Path) -> Path:
    candidate, number = path, 1
    while candidate.exists():
        number += 1
        candidate = path.with_name(f"{path.name}.{number}")
    return candidate


def move_lua() -> list[str]:
    """The new Lua file first (rendered anew, with Tuneup's commands), then the
    require line, then the old file: Hyprland may reload in between, and every
    step leaves a config that loads."""
    old, new = keybinds.old_lua_file(), keybinds.hypr_dir() / f"{brand.LUA_MODULE}.lua"
    done = []
    if old.exists() and not old.is_symlink():
        try:
            keybinds.replace_text(new, keybinds.render(config.read()))
        except config.ConfigError:
            keybinds.replace_text(new, old.read_text())  # its commands still work through the alias
        done.append(f"{old} -> {new}")
    path = keybinds.hyprland_file()
    try:
        text = path.read_text()
    except OSError:
        text = ""
    if keybinds.OLD_REQUIRE_LINE in text and new.exists():
        text = text.replace(keybinds.OLD_REQUIRE_COMMENT, keybinds.REQUIRE_COMMENT)
        keybinds.replace_text(path, text.replace(keybinds.OLD_REQUIRE_LINE, keybinds.REQUIRE_LINE))
        done.append(f"{path}: {keybinds.REQUIRE_LINE}")
    if old.exists() and not old.is_symlink() and new.exists():
        old.unlink()
    return done


def autostart_file() -> Path:
    return keybinds.hypr_dir() / "autostart.lua"


def fix_autostart() -> list[str]:
    """`hypr-screens watch` / `tray` started from autostart.lua (comments stay)."""
    path = autostart_file()
    try:
        text = path.read_text()
    except OSError:
        return []
    lines = [line if line.lstrip().startswith("--") else AUTOSTART_COMMAND.sub(brand.COMMAND, line)
             for line in text.split("\n")]
    if "\n".join(lines) == text:
        return []
    keybinds.replace_text(path, "\n".join(lines))
    return [f"{path}: {brand.COMMAND} watch/tray"]


def run() -> list[str]:
    """Everything to move; returns what was moved."""
    done = move_folder(config.runtime_home() / brand.OLD_DIR, config.runtime_home() / brand.DIR)
    with config.locked():
        done += move_folder(config.config_home() / brand.OLD_DIR, config.config_home() / brand.DIR)
        done += move_lua()
        done += fix_autostart()
    return done
