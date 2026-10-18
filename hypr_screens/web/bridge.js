/* Tuneup – the bridge to Python, and the Omarchy theme.
 *
 * A plain script that runs before the app (app.js, a module). Inside the
 * app's WebKit window `window.webkit.messageHandlers.api` exists: every
 * `api.someMethod(a, b)` is sent there and answered by
 * hypr_screens.api.some_method(a, b). Opened in a plain browser there is no
 * bridge, and mock.js provides `window.api` instead.
 *
 * window.hyprTheme applies the theme's colors and mode (the boot data now,
 * later window.hyprScreens.setTheme/setMode from Python).
 */
(function () {
  "use strict";

  const boot = window.hyprBoot || {};
  const root = document.documentElement;
  const NAMES = { lighter_background: "lighter-background", dark_background: "dark-background",
                  darker_background: "darker-background", dark_foreground: "dark-foreground",
                  light_foreground: "light-foreground" };

  window.hyprTheme = {
    colors(colors) {
      for (const [name, value] of Object.entries(colors || {})) {
        if (/^#[0-9a-fA-F]{6}$/.test(value)) root.style.setProperty(`--c-${NAMES[name] || name}`, value);
      }
    },
    mode(mode) { root.dataset.mode = mode === "light" ? "light" : "dark"; },
  };
  window.hyprTheme.colors(boot.theme);
  if (boot.mode) window.hyprTheme.mode(boot.mode);
  if (boot.language) root.lang = boot.language;

  const handler = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.api;
  if (!handler) return;

  window.api = new Proxy({}, {
    get(_target, method) {
      if (typeof method !== "string" || method === "then") return undefined;
      return async (...args) => {
        const answer = await handler.postMessage({ method, args });
        if (answer && answer.error) {
          const error = new Error(answer.error.message || answer.error.code);
          error.code = answer.error.code;
          throw error;
        }
        return answer ? answer.value : undefined;
      };
    },
  });
})();
