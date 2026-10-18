/* Keeping the page current: values that change from outside (keys, apps,
 * the charger, the watcher) are polled while their page shows, and Python
 * calls window.hyprScreens when config.json or the theme changed. */
import { route } from "../core/router.js";
import { PARTS, reload, S, UI } from "../core/state.js";
import { render } from "../core/view.js";
import { dialog } from "../ui/dialog.js";
import { Pop } from "../ui/popover.js";

const TICK_MS = 1000;
/* Every how many ticks a part is polled on the pages that show it. */
const POLLS = [
  { part: "sound", every: 1, pages: ["sound", "home"] },
  { part: "samsung", every: 10, pages: ["power", "home"], when: () => S.samsung && S.samsung.available },
  { part: "camera", every: 3, pages: ["camera"] },
  { part: "enforcement", every: 5, pages: ["general"], when: () => S.enforcement },
];

let tick = 0, polling = false;
const quiet = () => document.hidden || dialog.open || Pop.isOpen || UI.pressed || UI.busy > 0 || polling;
const typing = () => { const el = document.activeElement; return el && el.matches && el.matches("input[type=text], input[type=search]"); };

async function poll() {
  tick += 1;
  if (quiet()) return;
  const page = route().page;
  const due = POLLS.filter((p) => p.pages.includes(page) && tick % p.every === 0 && (!p.when || p.when())).map((p) => p.part);
  if (!due.length) return;
  polling = true;
  const before = due.map((n) => JSON.stringify(S[n] || null));
  await reload(...due);
  polling = false;
  const changed = due.some((n, i) => JSON.stringify(S[n] || null) !== before[i]);
  if (changed && !quiet() && !typing()) render();
}

/* Called by Python (gui/web_window.py); the theme is applied by bridge.js. */
function bridgeHooks() {
  window.hyprScreens = {
    setTheme: (colors) => window.hyprTheme.colors(colors),
    setMode: (mode) => window.hyprTheme.mode(mode),
    async refresh() {
      if (UI.busy || dialog.open) return;
      await reload(...PARTS);
      render();
    },
  };
}

export function startLive() {
  bridgeHooks();
  setInterval(poll, TICK_MS);
}
