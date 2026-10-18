/* The frame of the app: the navigation, the page (rendered from the route)
 * and the texts of index.html. */
import { $, esc } from "../core/dom.js";
import { errText } from "../core/format.js";
import { loc, t } from "../core/i18n.js";
import { pageOf, route, shownPages } from "../core/router.js";
import { loaded, reload, S, UI } from "../core/state.js";
import { beginRender, k, on, setRenderer, takeHooks } from "../core/view.js";
import { ic } from "../ui/icons.js";
import { emptyState, ph } from "../ui/layout.js";
import { Pop } from "../ui/popover.js";
import { pageCamera } from "../pages/camera.js";
import { GLOBAL_HANDLERS, pageGeneral } from "../pages/general.js";
import { pageHome } from "../pages/home.js";
import { pageKeys } from "../pages/keys/page.js";
import { lookDirty, renderApplyBar } from "../pages/look/draft.js";
import { pageLook } from "../pages/look/page.js";
import { pagePower } from "../pages/power.js";
import { pageScreens } from "../pages/screens/page.js";
import { pageSound } from "../pages/sound.js";
import { pageWidgets } from "../pages/widgets/page.js";
import { afterJump, searchTexts } from "./search.js";

const PAGE_HTML = { home: pageHome, screens: pageScreens, keys: pageKeys, look: pageLook, widgets: pageWidgets, sound: pageSound, camera: pageCamera, power: pagePower, general: pageGeneral };
const main = $("#main"), page = $("#page");
let lastRoute = "";

function renderNav(r) {
  $("#nav-list").innerHTML = shownPages().map((p) => {
    const label = p.label();
    const dot = p.id === "look" && lookDirty() && r.page !== "look";
    return `<li><a class="nav-item" href="#/${p.id}"${p.id === r.page ? ' aria-current="page"' : ""} title="${esc(label)}">${ic(p.icon)}<span>${esc(label)}</span>${dot ? `<i class="dot" role="img" aria-label="${esc(t("Windows: preview not applied yet"))}" title="${esc(t("Windows: preview not applied yet"))}"></i>` : ""}</a></li>`;
  }).join("");
}

/* A page whose data did not load (yet): the reason and "try again". */
function pageMissing(p) {
  const failed = p.needs.filter((n) => S.err[n]);
  if (!failed.length) return `${ph(esc(p.label()))}${emptyState("spinner", esc(t("Loading …")))}`;
  on("retry", { click: async () => { await reload(...p.needs); render(); } });
  return `${ph(esc(p.label()))}${emptyState("alert", esc(t("This page could not be loaded")), `<span class="small" style="max-width:520px">${esc(errText(S.err[failed[0]]))}</span><button type="button" class="btn" ${k("retry")}>${ic("cycle", "sm")}${esc(t("Try again"))}</button>`)}`;
}

/* The key of the focused control (to focus it again after the render). */
function focusedKey() {
  const el = document.activeElement;
  if (!el || !el.closest || !el.closest("#page, #applybar")) return null;
  const owner = el.closest("[data-k]");
  return owner ? owner.dataset.k : null;
}

export function render(enter = false) {
  const r = route();
  const key = `${r.page}/${r.sub || ""}`;
  if (key !== lastRoute) { enter = true; lastRoute = key; UI.wtab = UI.wtabNext || "content"; UI.wtabNext = null; }
  if (r.page === "power" && S.samsung && !S.samsung.available) { location.replace("#/home"); return; }
  const focus = focusedKey();
  const top = main.scrollTop;
  Pop.close(false);
  beginRender(GLOBAL_HANDLERS);
  const p = pageOf(r.page);
  const ready = (p.core || p.needs).every(loaded);
  page.innerHTML = ready ? PAGE_HTML[r.page](r) : pageMissing(p);
  renderNav(r);
  renderApplyBar(r.page === "look");
  document.title = `${p.label()} – ${t("Settings")}`;
  if (enter) {
    page.classList.remove("enter"); void page.offsetWidth; page.classList.add("enter");
    main.scrollTop = 0;
  } else main.scrollTop = top;
  takeHooks().forEach((f) => f());
  if (focus && !enter) {
    const el = $(`[data-k="${CSS.escape(focus)}"]`);
    if (el && !el.disabled) el.focus({ preventScroll: true });
  }
  afterJump();
}
setRenderer(render);

/* The texts written in index.html, in the app's language. */
export function staticTexts() {
  document.documentElement.lang = loc();
  $(".nav").setAttribute("aria-label", t("Sections"));
  $(".nav-head-text small").textContent = t("Settings");
  $(".search-hint").textContent = t("Ctrl F");
  $("#applybar").setAttribute("aria-label", t("Changes not applied yet"));
  searchTexts();
}
