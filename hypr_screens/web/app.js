/* hypr-screens – settings UI (entry point).
 *
 * Talks only to `window.api`: the Python bridge (bridge.js → hypr_screens/api)
 * in the app's window, mock.js in a plain browser. Shapes: API.md.
 *
 *   core/   state, api, texts, formatting, routing, the render/handler registry
 *   ui/     icons, layout blocks, controls, popover, dialog, toast
 *   pages/  one module (or folder) per page
 *   shell/  navigation and page render, delegated events, search, live updates
 */
import { bootTexts, loadTranslations } from "./core/i18n.js";
import { PARTS, reload, UI } from "./core/state.js";
import { render } from "./core/view.js";
import { runDialogCleanup } from "./ui/dialog.js";
import { resumePreview } from "./pages/camera.js";
import { LANGUAGE_EVENT } from "./pages/general.js";
import { endPreview } from "./pages/look/draft.js";
import { layoutArrange } from "./pages/screens/arrange.js";
import { laptopId } from "./pages/screens/model.js";
import { bindEvents } from "./shell/events.js";
import { startLive } from "./shell/live.js";
import { staticTexts } from "./shell/render.js";
import { bindSearch } from "./shell/search.js";

bindEvents({ onResize: layoutArrange });
bindSearch();
addEventListener("hashchange", () => render());
document.addEventListener("visibilitychange", () => { if (!document.hidden) resumePreview(); });
document.addEventListener(LANGUAGE_EVENT, () => { staticTexts(); render(); });
addEventListener("pagehide", () => {
  runDialogCleanup();  // e.g. the key capture's keymap
  endPreview();
});

(async function start() {
  const mode = new URLSearchParams(location.search).get("mode");
  if (mode) window.hyprTheme.mode(mode);
  if (!bootTexts()) await loadTranslations();
  staticTexts();
  startLive();
  await reload(...PARTS);
  UI.sel = laptopId();
  if (!location.hash) history.replaceState(null, "", "#/home");
  render(true);
})();
