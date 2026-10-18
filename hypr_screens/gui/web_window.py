"""The settings window: the HTML app in hypr_screens/web/ in a WebKit view.

The page asks through `window.webkit.messageHandlers.api` (web/bridge.js);
each call runs hypr_screens.api.<name> on a worker thread, one at a time, and
the answer goes back as {"value": ...} or {"error": {"code", "message"}}.
The page gets the Omarchy colors and the texts of the chosen language before
it starts (window.hyprBoot), and is told to refresh when config.json changes
from outside (the tray, the CLI, the watcher).
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
gi.require_version("JavaScriptCore", "6.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, JavaScriptCore, WebKit  # noqa: E402

from hypr_screens import config, i18n  # noqa: E402
from hypr_screens.gui import placement, theme  # noqa: E402
from hypr_screens.i18n import t  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent / "web" / "index.html"
# A change the page made itself also changes config.json: no refresh for that.
OWN_CHANGE_SECONDS = 1.5


def method_name(name: str) -> str:
    """someMethod -> some_method."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def boot_script() -> str:
    colors = theme.palette()
    language = i18n.use_configured()
    boot = {
        "theme": {key: value for key, value in colors.items() if key != "mode"},
        "mode": colors.get("mode", "dark"),
        "language": language,
        "strings": i18n.load_table(language),
    }
    return f"window.hyprBoot = {json.dumps(boot, ensure_ascii=False)};"


class WebWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title=t("Settings"),
                         default_width=placement.WIDTH, default_height=placement.HEIGHT)
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="api")
        self.last_call = 0.0
        self.refresh_source = 0

        self.content = WebKit.UserContentManager()
        self.content.register_script_message_handler_with_reply("api", None)
        self.content.connect("script-message-with-reply-received", self.on_message)
        self.add_boot_script()

        self.view = WebKit.WebView(user_content_manager=self.content)
        settings = self.view.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_enable_developer_extras(bool(GLib.getenv("HYPR_SCREENS_DEBUG")))
        settings.set_enable_back_forward_navigation_gestures(False)
        self.view.set_background_color(self.background())
        self.view.connect("decide-policy", self.on_policy)
        self.view.connect("context-menu", lambda *_args: not GLib.getenv("HYPR_SCREENS_DEBUG"))
        self.view.load_uri(PAGE.as_uri())
        self.set_content(self.view)

        keys = Gtk.ShortcutController()
        keys.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Control>q|<Control>w"),
                                           Gtk.CallbackAction.new(lambda *_args: self.close() or True)))
        self.add_controller(keys)

        self.monitor = Gio.File.new_for_path(str(config.config_file())).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self.on_config_changed)
        self.connect("destroy", self.on_destroy)

    def add_boot_script(self) -> None:
        self.content.remove_all_scripts()
        self.content.add_script(WebKit.UserScript.new(
            boot_script(), WebKit.UserContentInjectedFrames.TOP_FRAME,
            WebKit.UserScriptInjectionTime.START, None, None))

    def background(self) -> Gdk.RGBA:
        color = Gdk.RGBA()
        color.parse(theme.palette().get("background", "#1e1e2e"))
        return color

    # --- calls from the page ---------------------------------------------------------------

    def on_message(self, _manager, value, reply) -> bool:
        try:
            message = json.loads(value.to_json(0))
            name, args = method_name(str(message["method"])), list(message.get("args") or [])
        except (ValueError, KeyError, TypeError):
            self.answer(value, reply, {"error": {"code": "bad_call", "message": "Malformed call"}})
            return True
        future = self.worker.submit(self.call, name, args)
        future.add_done_callback(lambda done: GLib.idle_add(self.answer, value, reply, done.result()))
        return True

    def call(self, name: str, args: list) -> dict:
        from hypr_screens import api

        try:
            result = {"value": api.call(name, args)}
        except api.ApiError as error:
            result = {"error": error.to_json()}
        except Exception as error:  # the page shows it; the window must stay usable
            result = {"error": {"code": "internal", "message": repr(error)}}
        self.last_call = time.monotonic()
        if name == "set_language" and "value" in result:
            GLib.idle_add(self.reload_language)
        return result

    def answer(self, value, reply, result: dict) -> bool:
        try:
            text = json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as error:
            text = json.dumps({"error": {"code": "internal", "message": repr(error)}})
        reply.return_value(JavaScriptCore.Value.new_from_json(value.get_context(), text))
        return False

    def reload_language(self) -> bool:
        """Texts come with the page: load it again in the new language."""
        self.set_title(t("Settings"))
        self.add_boot_script()
        self.view.reload()
        application = self.get_application()
        if hasattr(application, "relabel_tray"):
            application.relabel_tray()
        return False

    # --- outside changes, links ------------------------------------------------------------

    def on_config_changed(self, _monitor, _file, _other, event) -> None:
        if event not in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED):
            return
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
        self.refresh_source = GLib.timeout_add(400, self.refresh)

    def refresh(self) -> bool:
        self.refresh_source = 0
        if time.monotonic() - self.last_call > OWN_CHANGE_SECONDS:
            self.view.evaluate_javascript("window.hyprScreens && window.hyprScreens.refresh()", -1,
                                          None, None, None, None, None)
        return False

    def show_again(self) -> None:
        """Shown from the tray while open: theme and data may have changed."""
        self.view.evaluate_javascript("window.hyprScreens && window.hyprScreens.refresh()", -1,
                                      None, None, None, None, None)

    def on_policy(self, _view, decision, kind) -> bool:
        """Only the app itself loads here; links open in the browser."""
        if kind != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        if uri.startswith(PAGE.as_uri()) or uri == "about:blank":
            return False
        decision.ignore()
        Gio.AppInfo.launch_default_for_uri_async(uri, None, None, None, None)
        return True

    def on_destroy(self, _window) -> None:
        self.monitor.cancel()
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
        self.worker.shutdown(wait=False, cancel_futures=True)
