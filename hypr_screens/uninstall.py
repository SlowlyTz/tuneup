"""`tuneup uninstall`: takes out everything Tuneup brought, and gives Omarchy
back what it changed. The system packages stay (the end of the run lists
them); the settings stay too with --keep-settings.

In this order: the watcher and the tray stop; minimized windows and the fixed
desktop's windows come back; our lines leave hyprland.lua and autostart.lua and
the Lua file goes; the shell plugins and bar widgets, the commands, the desktop
entry and the icon go; the root files of the Galaxy Book and camera setups go
(one password); the runtime files, the settings (unless kept) and the clone in
~/.local/share/tuneup go; then Hyprland reloads -- Omarchy's own keys, look and
monitor settings are back.
"""
import shutil
import sys

from hypr_screens import brand, camera, config, desktops, hypr, install, keybinds, migrate, root, samsung, scratch

MINIMIZED = "special:minimized"


def bring_back_windows() -> list[str]:
    """Minimized windows to the desktop shown now; the fixed desktop's windows
    to a normal one (without the watcher nothing would ever show them)."""
    scratch.unpark_all()  # scratch desktops put away while closed: normal workspaces again
    hidden = [c for c in hypr.query_list("clients") if (c.get("workspace") or {}).get("name") == MINIMIZED]
    focused = next((m for m in hypr.monitors() if m.get("focused")), {})
    shown = (focused.get("activeWorkspace") or {}).get("id") or 1
    for client in hidden:
        hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{shown}", follow = false, '
                      f'window = "address:{client["address"]}" }})')
    try:
        desktops.fold_fixed(desktops.resolve(config.load()))
    except Exception as error:  # the windows are a nicety; the uninstall goes on
        return [f"fixed desktop: {error!r}"]
    return [f"brought back {len(hidden)} minimized windows"] if hidden else []


def lua_files() -> list[str]:
    done = ["hyprland.lua: our lines removed"] if keybinds.remove_require() else []
    for path in (keybinds.hypr_dir() / f"{brand.LUA_MODULE}.lua", keybinds.old_lua_file(), *keybinds.backups()):
        if path.exists() or path.is_symlink():
            path.unlink()
            done.append(f"removed {path}")
    path = migrate.autostart_file()
    try:
        text = path.read_text()
    except OSError:
        return done
    kept = [line for line in text.split("\n") if line.lstrip().startswith("--")
            or not migrate.OUR_AUTOSTART.search(line)]
    if kept != text.split("\n"):
        keybinds.replace_text(path, "\n".join(kept))
        done.append(f"{path}: our lines removed")
    return done


def root_script() -> str:
    """The Galaxy Book and camera teardowns in one script (one password), or ""."""
    parts = []
    if samsung.root_files():
        parts.append(samsung.teardown_script())
    if camera.root_files():
        parts.append(camera.teardown_script())
    return "\n".join(parts)


def root_files(graphical: bool) -> list[str]:
    script = root_script()
    if not script:
        return []
    files = [str(p) for p in samsung.root_files() + camera.root_files()]
    if root.run_as_root(script, graphical):
        return [f"removed {name}" for name in files]
    return [f"kept {', '.join(files)}: the password was not given (run `{brand.COMMAND} uninstall` again)"]


def folders(keep_settings: bool) -> list[str]:
    places = [config.runtime_home() / name for name in (brand.DIR, brand.OLD_DIR, "hypr-minimizer")]
    if not keep_settings:
        home = config.config_home()
        places += [home / brand.DIR, home / brand.OLD_DIR, *sorted(home.glob(f"{brand.OLD_DIR}.old*"))]
    done = []
    for place in places:
        if place.is_symlink() or place.is_file():
            place.unlink()
        elif place.is_dir():
            shutil.rmtree(place)
        else:
            continue
        done.append(f"removed {place}")
    return done


def run(keep_settings: bool = False, graphical: bool = False) -> list[str]:
    """Everything above; returns what was done."""
    done = install.stop()
    done += bring_back_windows()
    samsung.end_full_charge(config.load())
    done += lua_files()
    done += install.remove_from_shell()
    done += [f"{name}: {result}" for name, result in install.remove_launchers().items()]
    done += install.remove_desktop_entry()
    done += root_files(graphical)
    done += folders(keep_settings)
    hypr.hyprctl("reload")
    done.append("reloaded Hyprland: Omarchy's keys, look and monitor settings are back")
    if install.REPO.resolve() == install.clone_dir().resolve():
        shutil.rmtree(install.REPO, ignore_errors=True)
        done.append(f"removed {install.REPO}")
    return done


PACKAGES_NOTE = ("The system packages stay (other apps may use them): {packages}. "
                 "Remove what you do not need with: sudo pacman -Rns <name>")


def confirmed(keep_settings: bool) -> bool:
    if not sys.stdin.isatty():
        return False
    what = "Tuneup (your settings stay)" if keep_settings else "Tuneup and its settings"
    try:
        answer = input(f"Remove {what}? (y/N) ")
    except EOFError:
        return False
    return answer.strip().lower().startswith(("y", "j"))


def main(keep_settings: bool, yes: bool) -> int:
    if not yes and not confirmed(keep_settings):
        print("Nothing removed.")
        return 1
    for line in run(keep_settings, graphical=not sys.stdin.isatty()):
        print(f"  {line}")
    print(PACKAGES_NOTE.format(packages=", ".join(install.PACKAGES + install.OPTIONAL_PACKAGES)))
    return 0

