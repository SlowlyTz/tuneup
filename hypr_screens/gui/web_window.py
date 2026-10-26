"""The settings window: the HTML app in hypr_screens/web/ in a WebKit view.

The page asks through `window.webkit.messageHandlers.api` (web/bridge.js);
each call runs hypr_screens.api.<name> on a worker thread, one at a time, and
the answer goes back as {"value": ...} or {"error": {"code", "message"}}.
The page gets the Omarchy colors and the texts of the chosen language before
it starts (window.hyprBoot), and is told to refresh when config.json changes
from outside (the tray, the CLI, the watcher).

The page is served as tuneup://app/… (so it may use ES modules), and
tuneup://camera/preview.jpg is the camera preview's newest frame, read
straight from the file the camera feeder writes -- no round trip through the
api worker, so the preview runs at the feeder's own frame rate.
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

from hypr_screens import brand, camera, config, i18n, theme  # noqa: E402
from hypr_screens.gui import placement  # noqa: E402

WEB = Path(__file__).resolve().parent.parent / "web"
SCHEME = brand.COMMAND
APP_URI = f"{SCHEME}://app/"
TYPES = {".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
         ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
         ".woff2": "font/woff2", ".md": "text/plain"}
# A change the page made itself also changes config.json: no refresh for that.
OWN_CHANGE_SECONDS = 1.5


def method_name(name: str) -> str:
    """someMethod -> some_method."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def web_file(path: str) -> Path | None:
    """A file of the page, never one outside hypr_screens/web (or ../locales.json)."""
    target = (WEB / path.lstrip("/")).resolve()
    allowed = target.is_relative_to(WEB) or target == WEB.parent / "locales.json"
    return target if allowed and target.is_file() else None


def serve(request) -> None:
    """tuneup://app/<file> and tuneup://camera/preview.jpg."""
    uri = GLib.Uri.parse(request.get_uri(), GLib.UriFlags.NONE)
    host, path = uri.get_host(), uri.get_path()
    if host == "camera" and path == "/preview.jpg":
        camera.request_preview()
        target, kind = camera.preview_file(), "image/jpeg"
    elif host == "app":
        target = web_file(path or "/index.html")
        kind = TYPES.get(target.suffix, "application/octet-stream") if target else ""
    else:
        target, kind = None, ""
    try:
        data = GLib.Bytes.new(target.read_bytes()) if target else None
    except OSError:
        data = None
    if data is None:
        request.finish_error(GLib.Error.new_literal(Gio.io_error_quark(), "not found", Gio.IOErrorEnum.NOT_FOUND))
        return
    request.finish(Gio.MemoryInputStream.new_from_bytes(data), data.get_size(), kind)


def register_scheme() -> None:
    """Once per process: the scheme lives in the shared WebKit context."""
    if getattr(register_scheme, "done", False):
        return
    context = WebKit.WebContext.get_default()
    context.register_uri_scheme(SCHEME, serve)
    security = context.get_security_manager()
    security.register_uri_scheme_as_secure(SCHEME)
    security.register_uri_scheme_as_cors_enabled(SCHEME)
    register_scheme.done = True


def theme_colors() -> tuple[dict, str]:
    """The theme's colors (without the mode) and "dark" or "light"."""
    colors = theme.palette()
    return {key: value for key, value in colors.items() if key != "mode"}, colors.get("mode", "dark")


def boot_script() -> str:
    colors, mode = theme_colors()
    language = i18n.use_configured()
    boot = {
        "theme": colors,
        "mode": mode,
        "language": language,
        "strings": i18n.load_table(language),
    }
    return f"window.hyprBoot = {json.dumps(boot, ensure_ascii=False)};"


class WebWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title=brand.NAME,
                         default_width=placement.WIDTH, default_height=placement.HEIGHT)
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="api")
        self.last_call = 0.0
        self.refresh_source = 0
        self.closed = False

        self.content = WebKit.UserContentManager()
        self.content.register_script_message_handler_with_reply("api", None)
        self.content.connect("script-message-with-reply-received", self.on_message)
        self.add_boot_script()

        register_scheme()
        self.view = WebKit.WebView(user_content_manager=self.content)
        settings = self.view.get_settings()
        settings.set_enable_developer_extras(bool(GLib.getenv("HYPR_SCREENS_DEBUG")))
        settings.set_enable_back_forward_navigation_gestures(False)
        self.view.set_background_color(self.background())
        self.view.connect("decide-policy", self.on_policy)
        self.view.connect("context-menu", lambda *_args: not GLib.getenv("HYPR_SCREENS_DEBUG"))
        self.view.load_uri(APP_URI + "index.html")
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
        future.add_done_callback(lambda done: done.cancelled() or GLib.idle_add(self.answer, value, reply, done.result()))
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
        if self.closed:
            return False  # the page is gone: its reply must not be touched
        try:
            text = json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as error:
            text = json.dumps({"error": {"code": "internal", "message": repr(error)}})
        reply.return_value(JavaScriptCore.Value.new_from_json(value.get_context(), text))
        return False

    def reload_language(self) -> bool:
        """Texts come with the page: load it again in the new language."""
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
            self.run_js("window.hyprScreens && window.hyprScreens.refresh()")
        return False

    def run_js(self, script: str) -> None:
        self.view.evaluate_javascript(script, -1, None, None, None, None, None)

    def show_again(self) -> None:
        """Shown from the tray while open: theme and data may have changed."""
        colors, mode = theme_colors()
        self.view.set_background_color(self.background())
        self.run_js(f"if (window.hyprScreens) {{ window.hyprScreens.setTheme({json.dumps(colors)}); "
                    f"window.hyprScreens.setMode({json.dumps(mode)}); window.hyprScreens.refresh(); }}")

    def on_policy(self, _view, decision, kind) -> bool:
        """Only the app itself loads here; links open in the browser (also
        those meant for a new window, target="_blank")."""
        if kind not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        if uri.startswith(APP_URI) or uri == "about:blank":
            return False
        decision.ignore()
        Gio.AppInfo.launch_default_for_uri_async(uri, None, None, None, None)
        return True

    def on_destroy(self, _window) -> None:
        self.closed = True
        from hypr_screens.api import shortcuts

        shortcuts.release_key_capture()
        self.monitor.cancel()
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
        self.worker.shutdown(wait=False, cancel_futures=True)
