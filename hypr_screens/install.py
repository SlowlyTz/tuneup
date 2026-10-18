"""Wiring into the system, and taking it out again: launchers, the desktop
entry and icon, Omarchy shell plugins and the bar widgets, and Tuneup's own
background processes (the watcher and the tray)."""
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from hypr_screens import brand, hypr

REPO = brand.ROOT
LAUNCHERS = {brand.COMMAND: REPO / brand.COMMAND, **{alias: REPO / brand.COMMAND for alias in brand.ALIASES},
             "hypr-minimizer": REPO / "minimizer.py"}
PLUGINS = {
    "hypr-minimizer.picker": REPO / "omarchy-plugin",
    "hypr-screens.workspaces": REPO / "omarchy-workspaces",
    "hypr-screens.power": REPO / "omarchy-power",
    "hypr-screens.widgets": REPO / "omarchy-widgets",
}
# Replaced by the settings window; removed on setup.
RETIRED_PLUGINS = ["hypr-screens.menu"]
WORKSPACES_WIDGET = "hypr-screens.workspaces"
POWER_WIDGET = "hypr-screens.power"
OMARCHY_WIDGETS = {WORKSPACES_WIDGET: "omarchy.workspaces", POWER_WIDGET: "omarchy.power"}
OMARCHY_POWER_WIDGET = OMARCHY_WIDGETS[POWER_WIDGET]
# Bar widgets live in shell.json's bar layout; they are not enabled as plugins.
BAR_WIDGETS = {WORKSPACES_WIDGET, POWER_WIDGET}
BACKUP_SUFFIXES = (".bak-tuneup", ".bak-hypr-screens")
ICON_SOURCE = REPO / "assets" / "tuneup.svg"
# From the official Arch repositories (the installer installs them; uninstalling keeps them).
PACKAGES = ["python-gobject", "libadwaita", "webkitgtk-6.0", "inter-font", "ffmpeg", "brightnessctl", "git"]
OPTIONAL_PACKAGES = ["cava", "v4l2loopback-dkms"]  # the visualizer, the rotated camera (+ kernel headers)
PROCESS_KINDS = ("watch", "tray", "settings")
STOP_SECONDS = 3.0


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def bin_dir() -> Path:
    return Path.home() / ".local" / "bin"


def clone_dir() -> Path:
    """Where the installer puts Tuneup when it is not run from a checkout."""
    return data_home() / brand.DIR


def desktop_file() -> Path:
    return data_home() / "applications" / f"{brand.APP_ID}.desktop"


def icon_file() -> Path:
    return data_home() / "icons" / "hicolor" / "scalable" / "apps" / f"{brand.COMMAND}.svg"


def omarchy_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "omarchy"


def plugins_dir() -> Path:
    return omarchy_dir() / "plugins"


def shell_json() -> Path:
    return omarchy_dir() / "shell.json"


def has_omarchy_shell() -> bool:
    return shutil.which("omarchy-shell") is not None and shutil.which("omarchy") is not None


def link(target: Path, link_path: Path) -> str:
    """Symlink link_path -> target; leaves foreign files alone."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.is_symlink() or not link_path.exists():
        if link_path.is_symlink() and link_path.resolve() == target.resolve():
            return "ok"
        if link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(target)
        return "linked"
    backup = link_path.with_name(link_path.name + BACKUP_SUFFIXES[0])
    if not backup.exists():
        link_path.rename(backup)
        link_path.symlink_to(target)
        return f"linked (old one kept as {backup.name})"
    return "skipped: exists"


OUR_TARGETS = {brand.COMMAND, *brand.ALIASES, "minimizer.py", *(path.name for path in PLUGINS.values()),
               *RETIRED_PLUGINS, "omarchy-menu"}


def ours(link_path: Path) -> bool:
    """A symlink into this checkout, or to one of our files elsewhere (another
    checkout, a clone that is gone)."""
    if not link_path.is_symlink():
        return False
    target = Path(os.readlink(link_path))
    return str(link_path.resolve()).startswith(str(REPO.resolve())) or target.name in OUR_TARGETS


def unlink(link_path: Path) -> str:
    """Remove our symlink and put back what link() kept aside."""
    if not ours(link_path):
        return "not ours" if link_path.exists() else "gone"
    link_path.unlink()
    for suffix in BACKUP_SUFFIXES:
        backup = link_path.with_name(link_path.name + suffix)
        if backup.exists() or backup.is_symlink():
            backup.rename(link_path)
            return f"removed, {backup.name} put back"
    return "removed"


def install_launchers() -> dict[str, str]:
    return {name: link(target, bin_dir() / name) for name, target in LAUNCHERS.items()}


def remove_launchers() -> dict[str, str]:
    return {name: unlink(bin_dir() / name) for name in LAUNCHERS}


# --- the desktop entry and the icon ---------------------------------------------------------


def desktop_entry() -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={brand.NAME}",
        f"Comment={brand.TAGLINE}",
        "Comment[de]=Die Einstellungs-App, die Omarchy fehlt",
        f"Exec={bin_dir() / brand.COMMAND} settings",
        f"Icon={brand.COMMAND}",
        "Terminal=false",
        "Categories=Settings;DesktopSettings;",
        "Keywords=Hyprland;Omarchy;Monitor;Display;Screen;Settings;",
        f"StartupWMClass={brand.APP_ID}",
        "",
    ])


def install_desktop_entry() -> list[str]:
    done = []
    desktop_file().parent.mkdir(parents=True, exist_ok=True)
    desktop_file().write_text(desktop_entry())
    done.append(f"desktop entry {desktop_file()}")
    if ICON_SOURCE.exists():
        icon_file().parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ICON_SOURCE, icon_file())
        done.append(f"icon {icon_file()}")
    else:
        done.append("no icon in this version")
    return done


def remove_desktop_entry() -> list[str]:
    removed = []
    for path in (desktop_file(), icon_file()):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


def install_plugins(ids: list[str]) -> dict[str, str]:
    results = {plugin: link(PLUGINS[plugin], plugins_dir() / plugin) for plugin in ids}
    subprocess.run(["omarchy-shell", "shell", "rescanPlugins"], capture_output=True, text=True)
    for plugin in ids:
        if plugin in BAR_WIDGETS:
            continue
        # A fresh rescan takes a moment before the plugin is known.
        for _ in range(10):
            done = subprocess.run(["omarchy", "plugin", "enable", plugin], capture_output=True, text=True)
            if done.returncode == 0:
                break
            time.sleep(0.5)
        else:
            results[plugin] += "; enable failed"
    return results


def remove_retired_plugins() -> list[str]:
    removed = []
    for plugin in RETIRED_PLUGINS:
        link_path = plugins_dir() / plugin
        if link_path.is_symlink():
            subprocess.run(["omarchy", "plugin", "disable", plugin], capture_output=True, text=True)
            link_path.unlink()
            removed.append(plugin)
    return removed


def gui_available() -> str:
    """"" when the settings window can run, else what is missing."""
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        gi.require_version("WebKit", "6.0")
        from gi.repository import Adw, Gtk, WebKit  # noqa: F401
    except (ImportError, ValueError) as error:
        return str(error)
    return ""


def use_bar_widget(ours: str = WORKSPACES_WIDGET) -> str:
    """Swap the bar's workspaces (or power) widget for ours; shell.json reloads itself."""
    kind = ours.rsplit(".", 1)[-1]
    path = shell_json()
    try:
        cfg = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "no shell.json"
    layout = (cfg.get("bar") or {}).get("layout") or {}
    replaced = None
    for section in layout.values():
        for widget in section if isinstance(section, list) else []:
            if isinstance(widget, dict) and str(widget.get("id", "")).endswith(f".{kind}"):
                replaced = widget["id"]
                widget["id"] = ours
    if replaced is None:
        return f"no {kind} widget in the bar"
    if replaced == ours:
        return "ok"
    backup = path.with_name("shell.json" + BACKUP_SUFFIXES[0])
    if not backup.exists():
        backup.write_text(path.read_text())
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    return f"replaced {replaced}"


def restore_bar_widget(ours_id: str) -> str:
    """Put Omarchy's own widget back where ours is."""
    path = shell_json()
    try:
        cfg = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "no shell.json"
    restored = False
    for section in ((cfg.get("bar") or {}).get("layout") or {}).values():
        for widget in section if isinstance(section, list) else []:
            if isinstance(widget, dict) and widget.get("id") == ours_id:
                widget["id"] = OMARCHY_WIDGETS[ours_id]
                restored = True
    if not restored:
        return "ok"
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    return f"restored {OMARCHY_WIDGETS[ours_id]}"


def restore_power_widget() -> str:
    """Put Omarchy's own battery panel back where ours is."""
    return restore_bar_widget(POWER_WIDGET)


def remove_from_shell() -> list[str]:
    """Uninstalling: Omarchy's bar widgets back, our plugins out of shell.json,
    our plugin links gone (disabled first)."""
    done = [restore_bar_widget(widget) for widget in BAR_WIDGETS]
    path = shell_json()
    try:
        cfg = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        cfg = None
    if isinstance(cfg, dict):
        ids = set(PLUGINS) | set(RETIRED_PLUGINS)
        plugins = [p for p in cfg.get("plugins", []) if not (isinstance(p, dict) and p.get("id") in ids)]
        layout = (cfg.get("bar") or {}).get("layout") or {}
        sections = {name: [w for w in section if not (isinstance(w, dict) and w.get("id") in ids)]
                    for name, section in layout.items() if isinstance(section, list)}
        if plugins != cfg.get("plugins", []) or any(sections[n] != layout[n] for n in sections):
            cfg["plugins"] = plugins
            layout.update(sections)
            path.write_text(json.dumps(cfg, indent=2) + "\n")
            done.append("shell.json")
    for plugin in [*PLUGINS, *RETIRED_PLUGINS]:
        link_path = plugins_dir() / plugin
        if ours(link_path):
            run_quietly(["omarchy", "plugin", "disable", plugin])
            done.append(f"{plugin}: {unlink(link_path)}")
    for backup in (path.with_name(path.name + suffix) for suffix in BACKUP_SUFFIXES):
        backup.unlink(missing_ok=True)
    return done


def run_quietly(command: list[str]) -> None:
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def sync_power_panel(active: bool) -> str:
    """Our battery panel (Samsung's four modes) exactly while Samsung control is
    active, Omarchy's otherwise. Cheap when nothing changes: runs on every start."""
    if not has_omarchy_shell():
        return "no omarchy-shell"
    if not active:
        return restore_power_widget()
    link_path = plugins_dir() / POWER_WIDGET
    if not (link_path.is_symlink() and link_path.resolve() == PLUGINS[POWER_WIDGET].resolve()):
        install_plugins([POWER_WIDGET])
    return use_bar_widget(POWER_WIDGET)




# --- Tuneup's own processes ---------------------------------------------------------------


def session_of(pid: int) -> tuple[str, str] | None:
    """(HOME, XDG_RUNTIME_DIR) of a process, None when it is not readable (not ours)."""
    try:
        environ = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return None
    values = dict(item.split(b"=", 1) for item in environ if b"=" in item)
    return values.get(b"HOME", b"").decode(errors="replace"), values.get(b"XDG_RUNTIME_DIR", b"").decode(errors="replace")


def kind_of(argv: list[str]) -> str | None:
    """"watch" for `tuneup watch` (or `python3 /…/hypr-screens watch`), ..."""
    for index, arg in enumerate(argv[:3]):
        if Path(arg).name in (brand.COMMAND, *brand.ALIASES) and index + 1 < len(argv):
            return argv[index + 1] if argv[index + 1] in PROCESS_KINDS else None
    return None


def processes(kinds: tuple[str, ...] = PROCESS_KINDS) -> dict[int, str]:
    """{pid: kind} of Tuneup's background processes in this session (same HOME
    and runtime dir: another session's are not ours to stop)."""
    here = (str(Path.home()), os.environ.get("XDG_RUNTIME_DIR", ""))
    found = {}
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            argv = [part.decode(errors="replace") for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
        except OSError:
            continue
        kind = kind_of(argv)
        if kind in kinds and session_of(int(proc.name)) == here:
            found[int(proc.name)] = kind
    return found


def stop(kinds: tuple[str, ...] = PROCESS_KINDS) -> list[str]:
    """SIGTERM, then SIGKILL for what is still there after STOP_SECONDS."""
    found = processes(kinds)
    for pid in found:
        signal_quietly(pid, signal.SIGTERM)
    deadline = time.monotonic() + STOP_SECONDS
    while time.monotonic() < deadline and any(Path(f"/proc/{pid}").exists() for pid in found):
        time.sleep(0.1)
    for pid in found:
        if Path(f"/proc/{pid}").exists():
            signal_quietly(pid, signal.SIGKILL)
    return [f"stopped {kind} ({pid})" for pid, kind in found.items()]


def signal_quietly(pid: int, number: int) -> None:
    try:
        os.kill(pid, number)
    except OSError:
        pass


def start(*args: str) -> str:
    """`tuneup <args>` started by Hyprland, so it gets the session's environment
    and outlives the terminal; detached by ourselves if Hyprland does not answer."""
    command = " ".join([str(bin_dir() / brand.COMMAND) if (bin_dir() / brand.COMMAND).exists()
                        else str(LAUNCHERS[brand.COMMAND]), *args])
    reply = hypr.dispatch(f"hl.dsp.exec_cmd({hypr.lua_string(command)})")
    if hypr.rejected(reply) or not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        subprocess.Popen(command.split(" "), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    return command


def restart(open_window: bool = False) -> list[str]:
    """The watcher and the tray anew (an update or a fresh install), the window too if asked."""
    done = stop()
    done += [f"started {start('watch')}", f"started {start('tray')}"]
    if open_window:
        done.append(f"started {start('settings')}")
    return done
