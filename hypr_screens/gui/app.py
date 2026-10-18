"""One running instance: the tray icon, and the settings window on demand.

`hypr-screens tray` starts it in the background (autostart). `hypr-screens
settings`, or a click on the tray icon, shows the window; a second start just
forwards the request to the running instance (GApplication uniqueness).
"""
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from hypr_screens import config, desktops, hypr, i18n, theme  # noqa: E402
from hypr_screens.i18n import t  # noqa: E402
from hypr_screens.gui import placement  # noqa: E402

APP_ID = "io.github.slowlytz.HyprScreens"
# The tray icon's title and tooltip: the app's name, the same in every language.
TRAY_TITLE = "hypr-screens"


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

    def do_startup(self):
        Adw.Application.do_startup(self)
        light = theme.palette().get("mode") == "light"
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_LIGHT if light else Adw.ColorScheme.FORCE_DARK)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if "--tray" in args:
            self.start_tray()
        else:
            self.show_settings()
        return 0

    def tray_entries(self) -> list:
        return [(t("Open settings"), self.show_settings),
                (t("Swap the fixed screen"), self.swap, external_connected),
                (t("Arrange widgets"), self.arrange),
                None,
                (t("Quit"), self.quit)]

    def start_tray(self) -> None:
        if self.tray is not None:
            return
        from hypr_screens.gui.tray import Tray

        i18n.use_configured()
        self.tray = Tray(TRAY_TITLE, "video-display-symbolic", self.show_settings, self.tray_entries())
        self.tray.start()
        self.hold()  # keep running without a window

    def relabel_tray(self) -> None:
        if self.tray is not None:
            i18n.use_configured()
            self.tray.update(TRAY_TITLE, self.tray_entries())

    def show_settings(self) -> bool:
        from hypr_screens.gui.web_window import WebWindow

        if self.window is None:
            self.window = WebWindow(self)
            self.window.connect("destroy", self.on_destroyed)
            self.window.present()
            GLib.timeout_add(150, placement.float_centered)
            return False
        # Open on another desktop: bring it to this one (asked before present(),
        # which may switch to the window's desktop).
        here = None if not self.window.get_visible() else focused_workspace()
        self.window.show_again()
        self.window.present()
        GLib.timeout_add(150, placement.bring_here, here)
        return False

    def on_destroyed(self, window) -> None:
        """Closed: the web view goes with it (no memory held while hidden); the
        tray keeps the app running."""
        if self.window is window:
            self.window = None

    def swap(self) -> bool:
        try:
            desktops.swap(config.load())
        except RuntimeError:
            pass
        if self.window is not None:
            self.window.show_again()
        return False

    def arrange(self) -> bool:
        from hypr_screens import api

        try:
            api.arrange_widgets()
        except Exception as error:  # noqa: BLE001 - a tray click must not end the app
            print(f"hypr-screens: arranging failed: {error!r}", file=sys.stderr)
        return False


def external_connected() -> bool:
    return any(not config.is_internal(m) for m in hypr.monitors())


def run(tray: bool) -> int:
    return App().run([sys.argv[0], "--tray"] if tray else [sys.argv[0]])
