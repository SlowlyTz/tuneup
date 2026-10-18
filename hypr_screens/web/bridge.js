/* hypr-screens – the bridge to Python.
 *
 * Inside the app's WebKit window `window.webkit.messageHandlers.api` exists:
 * every `api.someMethod(a, b)` is sent there and answered by
 * hypr_screens.api.some_method(a, b). Opened in a plain browser there is no
 * bridge, and mock.js provides `window.api` instead.
 */
(function () {
  "use strict";

  const boot = window.hyprBoot || {};
  const root = document.documentElement;
  const names = { lighter_background: "lighter-background", dark_background: "dark-background",
                  darker_background: "darker-background", dark_foreground: "dark-foreground",
                  light_foreground: "light-foreground" };
  for (const [name, value] of Object.entries(boot.theme || {})) {
    if (/^#[0-9a-fA-F]{6}$/.test(value)) root.style.setProperty(`--c-${names[name] || name}`, value);
  }
  if (boot.mode) root.dataset.mode = boot.mode === "light" ? "light" : "dark";
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
