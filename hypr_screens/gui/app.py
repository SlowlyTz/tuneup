"""One running instance: the tray icon, and the settings window on demand.

`tuneup tray` starts it in the background (autostart). `tuneup settings`, or
a click on the tray icon, shows the window; a second start just forwards the
request to the running instance (GApplication uniqueness).
"""
import os
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from hypr_screens import brand, config, desktops, hypr, i18n, theme  # noqa: E402
from hypr_screens.i18n import t  # noqa: E402
from hypr_screens.gui import placement  # noqa: E402

APP_ID = brand.APP_ID


PACKAGE = Path(__file__).resolve().parent.parent
CODE_CHECK_SECONDS = 30


def new_code_loads() -> bool:
    """The changed files import at all: a tray restarted on broken code would
    be gone until the next login."""
    try:
        probe = subprocess.run([sys.executable, "-c", "import hypr_screens.gui.app"], check=False,
                               capture_output=True, timeout=60, cwd=str(PACKAGE.parent))
    except (OSError, subprocess.SubprocessError):
        return False
    return probe.returncode == 0


def code_stamp() -> tuple:
    """Which code is on disk: the newest change time and the number of the
    package's Python files. An update that changes it leaves this process old."""
    newest, count = 0, 0
    for path in PACKAGE.rglob("*.py"):
        try:
            newest = max(newest, path.stat().st_mtime_ns)
        except OSError:
            continue
        count += 1
    return newest, count


def in_background(function, *args):
    """A GLib callback that runs `function(*args)` on a thread: hyprctl and
    the shell can take seconds, and the main thread draws the window and tray."""
    def start() -> bool:
        threading.Thread(target=function, args=args, daemon=True).start()
        return False
    return start
# The tray icon's title and tooltip: the app's name, the same in every language.
TRAY_TITLE = brand.NAME
# The app's icon (installed into the icon theme), else a stock one.
TRAY_ICON, TRAY_ICON_FALLBACK = brand.COMMAND, "video-display-symbolic"


def focused_workspace() -> int | None:
    """The desktop on the screen you are on."""
    monitor = next((m for m in hypr.monitors() if m.get("focused")), None)
    workspace = (monitor or {}).get("activeWorkspace") or {}
    return workspace.get("id")


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.tray = None
        self.respawn = False  # set when the code on disk is newer than this process
        self.stamp = code_stamp()
        self.new_stamp = None
        self.external = False  # a screen besides the laptop's, as of the last look (the tray menu reads it)

    def do_startup(self):
        Adw.Application.do_startup(self)
        light = theme.palette().get("mode") == "light"
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_LIGHT if light else Adw.ColorScheme.FORCE_DARK)

    def do_command_line(self, command_line):
        """The first start is always the tray instance, also from the app
        launcher (`tuneup settings`): closing the window leaves it in the tray.
        Later starts reach this one and just show the window."""
        self.start_tray()
        if "--tray" not in command_line.get_arguments()[1:]:
            self.show_settings()
        return 0

    def do_shutdown(self):
        from hypr_screens.api import shortcuts

        shortcuts.release_key_capture()
        from hypr_screens.gui import web_window

        web_window.release_pending()
        Adw.Application.do_shutdown(self)

    def tray_entries(self) -> list:
        return [(t("Open settings"), self.show_settings),
                (t("Swap the own desktops"), self.swap, lambda: self.external),
                (t("Arrange widgets"), self.arrange),
                None,
                (t("Quit"), self.quit)]

    def start_tray(self) -> None:
        if self.tray is not None:
            return
        from hypr_screens.gui.tray import Tray

        i18n.use_configured()
        self.tray = Tray(TRAY_TITLE, tray_icon(), self.show_settings, self.tray_entries(),
                         on_open=lambda: threading.Thread(target=self.look_for_screens, daemon=True).start())
        self.tray.start()
        threading.Thread(target=self.look_for_screens, daemon=True).start()
        self.hold()  # keep running without a window
        GLib.timeout_add_seconds(CODE_CHECK_SECONDS, self.check_code)

    def check_code(self) -> bool:
        """A long-lived tray with old code must not keep writing the settings
        with old logic: when the code changed (and has stopped changing, so an
        update is through) and no window is open, restart cleanly (run())."""
        stamp = code_stamp()
        if stamp == self.stamp:
            self.new_stamp = None
        elif stamp == self.new_stamp and self.window is None:
            if not new_code_loads():
                self.stamp = stamp  # broken files: keep the running code until they change again
                return True
            self.respawn = True
            self.quit()
            return False
        else:
            self.new_stamp = stamp
        return True

    def look_for_screens(self) -> None:
        """Off the main thread: asks Hyprland, and when the answer differs from
        what the menu shows, has the bar ask for the menu again."""
        try:
            external = external_connected()
        except Exception:  # noqa: BLE001 - the menu keeps its last answer
            return
        if external != self.external:
            self.external = external
            GLib.idle_add(self.relabel_tray)

    def relabel_tray(self) -> None:
        if self.tray is not None:
            i18n.use_configured()
            self.tray.update(TRAY_TITLE, self.tray_entries())

    def show_settings(self) -> bool:
        from hypr_screens.gui.web_window import WebWindow

        if self.window is None:
            self.window = WebWindow(self)
            self.window.connect("close-request", self.on_closed)
            self.window.present()
            GLib.timeout_add(150, in_background(placement.float_centered))
            return False
        # Open on another desktop: bring it to this one (asked before present(),
        # which may switch to the window's desktop).
        here = None if not self.window.get_visible() else focused_workspace()
        self.window.show_again()
        self.window.present()
        GLib.timeout_add(150, in_background(placement.bring_here, here))
        return False

    def on_closed(self, window) -> bool:
        """Closed: the next show builds a new window; the tray keeps the app
        running. Not on "destroy": GTK 4 sends that only once nothing holds the
        window any more, and self.window does -- a closed window shown again has
        lost its app (wrong class, no window rule) and no longer closes."""
        if self.window is window:
            self.window = None
        return False

    def swap(self) -> bool:
        threading.Thread(target=self.swap_now, daemon=True).start()
        return False

    def swap_now(self) -> None:
        try:
            desktops.swap(config.load())
        except RuntimeError:
            pass
        except Exception as error:  # noqa: BLE001 - a tray click must not end the app
            print(f"{brand.COMMAND}: swapping failed: {error!r}", file=sys.stderr)
        GLib.idle_add(self.window_changed)

    def window_changed(self) -> bool:
        if self.window is not None:
            self.window.show_again()
        return False

    def arrange(self) -> bool:
        """Can wait for the widgets plugin for many seconds: not on the main thread."""
        threading.Thread(target=self.arrange_now, daemon=True).start()
        return False

    def arrange_now(self) -> None:
        from hypr_screens import api

        try:
            api.arrange_widgets()
        except Exception as error:  # noqa: BLE001 - a tray click must not end the app
            print(f"{brand.COMMAND}: arranging failed: {error!r}", file=sys.stderr)


def tray_icon() -> str:
    """Tuneup's icon when the icon theme has it (the installer puts it there)."""
    display = Gdk.Display.get_default()
    if display is not None and Gtk.IconTheme.get_for_display(display).has_icon(TRAY_ICON):
        return TRAY_ICON
    return TRAY_ICON_FALLBACK


def external_connected() -> bool:
    return any(not config.is_internal(m) for m in hypr.monitors())


def run(tray: bool) -> int:
    app = App()
    code = app.run([sys.argv[0], "--tray"] if tray else [sys.argv[0]])
    if app.respawn:  # the app has quit (its D-Bus name is free): the same command, new code
        argv = [sys.executable, *sys.orig_argv[1:]]
        if argv[-1] == "settings":
            argv[-1] = "tray"  # no window is open: back as the tray alone, not with the window
        try:
            os.execv(sys.executable, argv)
        except OSError as error:
            print(f"{brand.COMMAND}: restarting with the new code failed: {error!r}", file=sys.stderr)
    return code
