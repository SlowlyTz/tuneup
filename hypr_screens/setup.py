"""`tuneup setup`: wires Tuneup into the desktop, without asking anything (keys
and everything else are set in the app). The installer runs it, and so does
every update; existing settings are kept.

1. the commands in ~/.local/bin: tuneup, hypr-screens (the old name), hypr-minimizer
2. hypr-screens' files moved to Tuneup's names (migrate.py)
3. the settings file (created with the defaults if there is none)
4. the Lua file with the keys and the autostart, loaded from hyprland.lua
5. the scratch desktops in place of Omarchy's scratchpad: SUPER + SHIFT + S is
   taken only if nothing of the user's is on it (decided once), and windows
   left in the scratchpad move to the first scratch desktop
6. the Omarchy shell plugins: the window list, the bar widgets, the desktop widgets
7. the desktop entry and the icon
"""
from pathlib import Path

from hypr_screens import brand, config, hypr, install, keybinds, migrate, samsung, scratch, widgets


def lua(cfg: dict, moved: bool) -> list[str]:
    """Write the Lua file and make sure hyprland.lua loads it. A file Hyprland
    has not loaded yet takes a reload; otherwise the keys go live by eval."""
    done = [f"wrote {keybinds.write(cfg)}"]
    if not keybinds.hyprland_file().exists():
        return done + [f"no {keybinds.hyprland_file()}: Tuneup needs Hyprland >= 0.56 with a Lua config; "
                       f"load the file with {keybinds.REQUIRE_LINE}"]
    added = not keybinds.is_required()
    if added:
        keybinds.add_require()
        done.append(f"{keybinds.hyprland_file()}: {keybinds.REQUIRE_LINE}")
    if added or moved:
        hypr.hyprctl("reload")
        done.append("reloaded Hyprland")
    else:
        keybinds.go_live(None, cfg)
    return done


def scratch_desktops(cfg: dict) -> tuple[dict, list[str]]:
    if not scratch.enabled(cfg):
        return cfg, []
    done = []
    if cfg["scratch_shift_s"] is None:
        others = keybinds.conflicts(scratch.SHIFT_S)
        take = scratch.may_take_shift_s(others)
        cfg = config.update(lambda fresh: fresh.__setitem__("scratch_shift_s", take))
        done.append(f"{scratch.SHIFT_S}: " + ("moves a window to a scratch desktop" if take
                                             else f"left to {', '.join(others)}"))
    moved = scratch.rescue_scratchpad()
    if moved:
        done.append(f"from the scratchpad to scratch desktop 1: {', '.join(moved)}")
    return cfg, done


def shell(cfg: dict) -> list[str]:
    if not install.has_omarchy_shell():
        return ["no omarchy-shell: no window list and no bar widgets; everything else works"]
    done = [f"removed old {plugin}" for plugin in install.remove_retired_plugins()]
    plugins = ["hypr-minimizer.picker", install.WORKSPACES_WIDGET]
    done += [f"{plugin}: {result}" for plugin, result in install.install_plugins(plugins).items()]
    if cfg["desktop_keys"]:
        done.append(f"bar: {install.use_bar_widget()}")
    done += [f"widgets: {result}" for result in widgets.wire_shell(cfg["widgets"])]
    done.append(f"battery panel: {install.sync_power_panel(samsung.active())}")
    return done


def run() -> list[str]:
    """Everything above; returns what was done. Raises config.ConfigError for a
    settings file that cannot be read (nothing is written over it)."""
    done = [f"{name}: {result}" for name, result in install.install_launchers().items()]
    moved = migrate.run()
    done += [f"moved {item}" for item in moved]
    cfg = config.update(lambda fresh: None)  # creates the file; keeps what is there
    cfg, notes = scratch_desktops(cfg)
    done += notes
    done += lua(cfg, any(".lua" in item for item in moved))
    done += shell(cfg)
    widgets.export(cfg)
    done += install.install_desktop_entry()
    if missing := install.gui_available():
        done.append(f"the window needs GTK 4, libadwaita, WebKitGTK 6.0 and PyGObject ({missing}): "
                    "sudo pacman -S python-gobject libadwaita webkitgtk-6.0")
    return done


def main() -> int:
    try:
        done = run()
    except config.ConfigError as error:
        print(f"{brand.COMMAND}: {error}\n  Fix or remove it, then run `{brand.COMMAND} setup` again.")
        return 1
    home = str(Path.home())
    for line in done:
        print(f"  {line.replace(home, '~')}")
    return 0
