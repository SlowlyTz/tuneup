/* The search above the navigation: finds pages and single settings (by their
 * title, description and a few more words) and jumps there. */
import { $, esc, norm, reducedMotion } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { pageOf, shownPages } from "../core/router.js";
import { S, UI } from "../core/state.js";
import { render } from "../core/view.js";
import { ic } from "../ui/icons.js";
import { canMaintain } from "../pages/about.js";
import { W_ICON, wid } from "../pages/widgets/model.js";

const MAX_HITS = 8;
const input = $("#search-input"), results = $("#search-results");

/* id: the data-sid of the place; r: its route; exp: an expander to open first;
 * syn: more words it is found by. */
function fixedEntries() {
  return [
    { id: "screens.arrange", r: "screens", t: t("Arrange screens"), syn: t("position left right above below beside drag layout monitor") },
    { id: "screens.swap", r: "screens", t: t("Swap the fixed screen"), syn: t("fixed swap one desktop") },
    { id: "screens.mirror", r: "screens", t: t("Mirror the laptop screen"), syn: t("mirror duplicate same picture projector beamer tv presentation") },
    { id: "screens.position", r: "screens", t: t("Position"), syn: t("left right above below beside laptop") },
    { id: "screens.rotation", r: "screens", t: t("Rotation"), d: t("Turn the screen"), syn: t("rotate portrait upside down landscape") },
    { id: "screens.scale", r: "screens", t: t("Scale"), d: t("Makes text and windows bigger or smaller"), syn: t("size zoom dpi big small") },
    { id: "screens.mode", r: "screens", t: t("Resolution"), d: t("Resolution and refresh rate"), syn: t("hz hertz frequency pixels refresh rate") },
    { id: "screens.newmon", r: "screens", t: t("For new monitors"), syn: t("new unknown default fixed") },
    { id: "screens.fav", r: "screens", t: t("Favorite"), exp: "scr-adv", syn: t("star top") },
    { id: "screens.forget", r: "screens", t: t("Forget this screen"), exp: "scr-adv", syn: t("delete remove forget") },
    ...((S.keys && S.keys.actions) || []).map((a) => ({ id: `keys.${a.id}`, r: "keys", t: t(a.title), d: t(a.desc || ""), syn: t("key shortcut minimize") })),
    { id: "keys.desktop", r: "keys", t: t("Desktop keys"), syn: t("super 1 tab workspace switch") },
    { id: "keys.scratch", r: "keys", t: t("Scratch desktops"), syn: t("scratchpad super s stash") },
    { id: "keys.scratch.kept", r: "keys", t: t("Always there"), d: t("Scratch desktops"), exp: "exp-scratch", syn: t("scratchpad persistent empty") },
    { id: "look.presets", r: "look", t: t("Window style"), d: ((S.look && S.look.presets) || []).map((p) => t(p.name)).join(", "), syn: t("preset template look theme") },
    { id: "look.gapsIn", r: "look", t: t("Inner gaps"), syn: t("gaps space between windows") },
    { id: "look.gapsOut", r: "look", t: t("Outer gaps"), syn: t("gaps edge of the screen") },
    { id: "look.rounding", r: "look", t: t("Corners"), syn: t("rounding round radius") },
    { id: "look.border", r: "look", t: t("Border"), syn: t("border width") },
    { id: "look.activeOpacity", r: "look", t: t("Opacity"), syn: t("transparent see-through opacity") },
    { id: "look.blur", r: "look", t: t("Blur"), exp: "look-adv", syn: t("blur frosted") },
    { id: "look.anim", r: "look", t: t("Animation speed"), exp: "look-adv", syn: t("animation fast slow") },
    { id: "look.colors", r: "look", t: t("Own border colors"), exp: "look-adv", syn: t("color border active gradient") },
    { id: "look.apps", r: "look", t: t("See-through apps"), exp: "look-adv", syn: t("transparent app opacity") },
    { id: "widgets.arrange", r: "widgets", t: t("Arrange widgets"), syn: t("desktop move colors font effects") },
    { id: "widgets.layouts", r: "widgets", t: t("Widget layouts"), syn: t("layout save load") },
    { id: "sound.out", r: "sound", t: t("Output"), d: t("Speakers, headphones, HDMI"), syn: t("speakers headphones hdmi volume default") },
    { id: "sound.in", r: "sound", t: t("Input"), d: t("Microphone"), syn: t("microphone mic recording") },
    { id: "sound.out", r: "sound", t: t("Force mute"), syn: t("force mute silent lock") },
    { id: "sound.apps", r: "sound", t: t("App volume"), syn: t("spotify firefox app volume output") },
    { id: "camera.toggle", r: "camera", t: t("Rotated camera for apps"), syn: t("webcam camera on off") },
    { id: "camera.rotation", r: "camera", t: t("Turn the camera"), syn: t("webcam rotation turn") },
    { id: "camera.setup", r: "camera", t: t("Set up the camera"), syn: t("webcam setup v4l2loopback") },
    { id: "power.battery", r: "power", t: t("Battery level"), syn: t("battery health charge cycles") },
    { id: "power.limit", r: "power", t: t("Charge limit"), syn: t("charging 80 limit protect battery") },
    { id: "power.full", r: "power", t: t("Charge fully once"), syn: t("100 full charge") },
    { id: "power.mode", r: "power", t: t("Performance mode"), syn: t("saver quiet balanced performance fan") },
    { id: "power.fan", r: "power", t: t("Fan and temperature"), syn: t("cpu temperature fan") },
    { id: "power.kbd", r: "power", t: t("Keyboard light"), syn: t("backlight light keyboard") },
    { id: "power.usb", r: "power", t: t("USB charging while the laptop is off"), exp: "pow-adv", syn: t("usb charge phone") },
    { id: "power.lid", r: "power", t: t("Switch on when the lid opens"), exp: "pow-adv", syn: t("lid open switch on") },
    { id: "power.off", r: "power", t: t("Switch off the Samsung control"), exp: "pow-adv", syn: t("samsung off disable") },
    { id: "general.lang", r: "general", t: t("Language"), syn: "language english deutsch español français italiano" },
    ...(S.enforcement ? [{ id: "general.enforce", r: "general", t: t("Keep my settings"), syn: t("enforce protect put back other apps") }] : []),
    { id: "general.guide", r: "general", t: t("Open the guide"), syn: t("help docs manual") },
    { id: "general.folder", r: "general", t: t("Open the settings folder"), syn: t("config folder file") },
    { id: "general.version", r: "general", t: t("Version"), syn: t("info about tuneup") },
    ...(canMaintain() ? [
      { id: "general.update", r: "general", t: t("Check for updates"), syn: t("update upgrade new version") },
      { id: "general.uninstall", r: "general", t: t("Uninstall Tuneup"), syn: t("remove delete uninstall") },
    ] : []),
  ];
}

/* Every widget, its content settings, and (once) the "where & when" settings. */
function widgetEntries() {
  const list = [];
  const W = S.widgets || [];
  for (const w of W) {
    list.push({ id: `widgets.${w.kind}`, r: `widgets/${w.kind}`, t: t(w.name), d: t(w.description || ""), syn: "widget", top: true });
    for (const f of w.schema.filter((x) => x.group === "content")) list.push({ id: `w.${w.kind}.${f.key}`, r: `widgets/${w.kind}`, t: `${t(w.name)}: ${t(f.label)}`, syn: f.section ? t(f.section) : "" });
  }
  const first = W.find((w) => w.enabled) || W[0];
  for (const f of first ? first.schema.filter((x) => x.group === "where") : []) {
    const sid = f.key === "screens" || f.key === "desktops" ? `w.where.${f.key}` : `w.${first.kind}.${f.key}`;
    list.push({ id: sid, r: `widgets/${first.kind}`, tab: "where", t: t(f.label), d: t("Widgets · where & when"), syn: "widget" });
  }
  return list;
}

const placeName = (r) => {
  const [page, sub] = r.split("/");
  const name = pageOf(page).label();
  return sub && wid(sub) ? `${name} › ${t(wid(sub).name)}` : name;
};

function hits(query) {
  const n = norm(query.trim());
  if (!n) return [];
  const words = n.split(/\s+/);
  const power = S.samsung && S.samsung.available;
  const pages = shownPages().map((p) => ({ id: `page.${p.id}`, r: p.id, t: p.label(), page: true }));
  const entries = [...fixedEntries(), ...widgetEntries()].filter((e) => !e.r.startsWith("power") || power);
  return [...pages, ...entries].map((e) => {
    const title = norm(e.t), hay = `${title} ${norm(e.d || "")} ${norm(e.syn || "")}`;
    if (!words.every((w) => hay.includes(w))) return null;
    const score = (title.startsWith(n) ? 0 : title.includes(n) ? 1 : 2) - (e.page ? 0.5 : 0) - (e.top ? 0.2 : 0);
    return { e, score };
  }).filter(Boolean).sort((a, b) => a.score - b.score).slice(0, MAX_HITS).map((x) => x.e);
}

const mark = (text, query) => {
  const q = query.trim();
  const i = norm(text).indexOf(norm(q));
  if (i < 0 || !q) return esc(text);
  return `${esc(text.slice(0, i))}<mark>${esc(text.slice(i, i + q.length))}</mark>${esc(text.slice(i + q.length))}`;
};

const state = { hits: [], active: 0 };
let pendingJump = null;

function draw() {
  const q = input.value;
  if (!q.trim()) { results.hidden = true; input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant"); return; }
  state.hits = hits(q);
  state.active = Math.min(state.active, Math.max(0, state.hits.length - 1));
  results.innerHTML = state.hits.length ? state.hits.map((e, i) => {
    const icon = e.r.includes("/") ? W_ICON[e.r.split("/")[1]] : pageOf(e.r.split("/")[0]).icon;
    return `<div class="sr-item" role="option" id="sr-${i}" data-i="${i}" aria-selected="${i === state.active}">${ic(icon)}<span><b>${mark(e.t, q)}</b><small>${e.page ? esc(t("Page")) : esc(placeName(e.r))}</small></span></div>`;
  }).join("") : `<div class="sr-empty">${esc(t("Nothing found for “{query}”", { query: q.trim() }))}</div>`;
  results.hidden = false;
  input.setAttribute("aria-expanded", "true");
  if (state.hits.length) input.setAttribute("aria-activedescendant", `sr-${state.active}`); else input.removeAttribute("aria-activedescendant");
}

/* Opens the place of entry `e`: scrolls to it, flashes it and focuses its control. */
function jump(e) {
  input.value = ""; draw(); input.blur();
  if (e.exp) UI.open[e.exp] = true;
  if (e.r.startsWith("widgets/")) { UI.wtab = e.tab || "content"; UI.wtabNext = UI.wtab; }
  const finish = () => {
    if (e.page) { $("#main").focus({ preventScroll: true }); return; }
    const el = $(`[data-sid="${CSS.escape(e.id)}"]`);
    if (!el) return;
    el.scrollIntoView({ block: "center", behavior: reducedMotion() ? "auto" : "smooth" });
    const box = el.classList.contains("row") || el.classList.contains("card") ? el : el.closest(".row, .card") || el;
    box.classList.remove("flash"); void box.offsetWidth; box.classList.add("flash");
    const control = el.matches("button, [tabindex]") ? el
      : ['[role="radio"][tabindex="0"]', '[role="switch"]', "input", "button", "[tabindex='0']"].map((q) => $(q, el)).find(Boolean);
    if (control) control.focus({ preventScroll: true });
  };
  const target = `#/${e.r}`;
  if (location.hash === target) { render(); finish(); }
  else { pendingJump = finish; location.hash = target; }
}

/* After a render: finish a jump that had to open another page first. */
export function afterJump() {
  if (!pendingJump) return;
  const f = pendingJump;
  pendingJump = null;
  requestAnimationFrame(f);
}

export const focusSearch = () => { input.focus(); input.select(); };
export const searchFocused = () => document.activeElement === input;

export function bindSearch() {
  input.addEventListener("input", () => { state.active = 0; draw(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!state.hits.length) return;
      state.active = (state.active + (e.key === "ArrowDown" ? 1 : -1) + state.hits.length) % state.hits.length;
      draw();
      const a = $(`#sr-${state.active}`); if (a) a.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (state.hits[state.active]) jump(state.hits[state.active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (input.value) { input.value = ""; draw(); } else input.blur();
    }
  });
  input.addEventListener("blur", () => setTimeout(() => {
    if (document.activeElement !== input) { results.hidden = true; input.setAttribute("aria-expanded", "false"); }
  }, 120));
  input.addEventListener("focus", () => { if (input.value) draw(); });
  results.addEventListener("mousedown", (e) => e.preventDefault());
  results.addEventListener("click", (e) => { const it = e.target.closest(".sr-item"); if (it) jump(state.hits[+it.dataset.i]); });
}

/* The texts of the search in index.html. */
export function searchTexts() {
  input.placeholder = t("Search a setting");
  input.setAttribute("aria-label", t("Search a setting"));
  results.setAttribute("aria-label", t("Search results"));
}
