/* App to desktop: up to five apps per scratch desktop and per desktop 1–10
 * that always start there (tiled or floating) and stay there for 5 seconds. */
import { api } from "../core/api.js";
import { change } from "../core/change.js";
import { esc, norm } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { S, UI } from "../core/state.js";
import { afterRender, k, on, render } from "../core/view.js";
import { appIcon, ic } from "../ui/icons.js";
import { notice, ph } from "../ui/layout.js";
import { openListbox, Pop } from "../ui/popover.js";

const AGAIN = { reload: ["apps"] };
const DESKTOPS = 10;

/* The app's own icon (from its desktop entry) or a drawn one. */
const icon = (a, cls = "app-ic") => (a.icon ? `<img class="${cls}" src="${esc(a.icon)}" alt="">` : appIcon([a.id, a.name], cls));

const listOf = (key) => (S.apps.desktops[key] || []).map((a) => ({ id: a.id, mode: a.mode }));
/* Where an app is now (another desktop loses it when it is added here). */
const homeOf = (id) => Object.keys(S.apps.desktops).find((key) => S.apps.desktops[key].some((a) => a.id === id));

function setApps(key, apps, msg) {
  const before = Object.fromEntries(Object.keys(S.apps.desktops).map((d) => [d, listOf(d)]));
  // Back: every desktop the change touched (an app added here left its old one).
  const undo = async () => {
    for (const d of new Set([...Object.keys(before), key])) {
      if (JSON.stringify(before[d] || []) !== JSON.stringify(listOf(d))) await api.setAppDesktop(d, before[d] || []);
    }
  };
  return change(() => api.setAppDesktop(key, apps), undo, { ...AGAIN, msg });
}

export function desktopName(key) {
  const [group, n] = key.split(":");
  return group === "scratch" ? t("Scratch desktop {n}", { n }) : t("Desktop {n}", { n });
}

/* An app: only its icon (floating ones with a small window mark); a click
 * opens its choices: tiled or floating, remove. */
function appTile(key, a, i) {
  const apps = listOf(key);
  const setMode = (mode) => setApps(key, apps.map((x, j) => (j === i ? { ...x, mode } : x)),
    mode === "float" ? t("{app} starts floating", { app: a.name }) : t("{app} starts tiled", { app: a.name }));
  const remove = () => setApps(key, apps.filter((_, j) => j !== i), t("{app} starts anywhere again", { app: a.name }));
  on(`ad-app-${key}-${i}`, {
    select: (el) => openListbox(el, {
      header: a.installed ? a.name : `${a.name} · ${t("Not installed")}`, value: a.mode,
      options: [
        { v: "tile", label: t("Tiled"), icon: ic("arrange", "sm") },
        { v: "float", label: t("Floating"), icon: ic("window", "sm") },
        { sep: true },
        { v: "remove", label: t("Remove"), icon: ic("x", "sm") },
      ],
      onPick: (v) => (v === "remove" ? remove() : v !== a.mode && setMode(v)),
    }),
  });
  const how = a.mode === "float" ? t("Floating") : t("Tiled");
  return `<button type="button" class="ad-app${a.installed ? "" : " gone"}" aria-haspopup="listbox" aria-expanded="false"
      aria-label="${esc(`${a.name}, ${how}`)}" title="${esc(`${a.name} · ${how}`)}" ${k(`ad-app-${key}-${i}`)}>${icon(a)}${a.mode === "float" ? `<span class="ad-mark">${ic("window", "xs")}</span>` : ""}</button>`;
}

/* The apps that fit `query` and are not on this desktop yet (their current desktop beside them). */
function suggest(input, key) {
  const apps = S.apps.desktops[key] || [];
  const q = norm(input.value.trim());
  const hits = (S.installed || []).filter((a) => !apps.some((x) => x.id === a.id) && (!q || norm(a.name).includes(q) || norm(a.id).includes(q)));
  const field = input.closest(".field");
  if (!hits.length) Pop.open(field, `<div class="sr-empty">${esc(t("No app found"))}</div>`, { keepFocus: true });
  else {
    openListbox(field, {
      keepFocus: true, value: null,
      options: hits.map((a) => { const home = homeOf(a.id); return { v: a.id, label: a.name, icon: icon(a), sub: home ? desktopName(home) : "" }; }),
      onPick: (id) => {
        const app = (S.installed || []).find((a) => a.id === id);
        UI.adAdding = null;
        setApps(key, [...listOf(key), { id, mode: "tile" }], t("{app} starts on {desktop}", { app: app ? app.name : id, desktop: desktopName(key) }));
      },
    });
  }
  input.setAttribute("aria-expanded", "true");
}

/* "Add an app", or while adding: the search field over every app of the launcher. */
function addControl(key) {
  if (UI.adAdding !== key) {
    on(`ad-add-${key}`, { click: () => { UI.adAdding = key; render(); } });
    return `<button type="button" class="btn ghost" ${k(`ad-add-${key}`)}>${ic("plus", "sm")}${esc(t("Add an app"))}</button>`;
  }
  on(`ad-find-${key}`, { combo: (input) => suggest(input, key) });
  on(`ad-stop-${key}`, { click: () => { UI.adAdding = null; Pop.close(false); render(); } });
  afterRender(() => { const el = document.querySelector(`[data-k="ad-find-${CSS.escape(key)}"]`); if (el) el.focus(); });
  return `<label class="field ad-find">${ic("search")}<input type="text" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="popover" aria-label="${esc(t("Search apps"))}" placeholder="${esc(t("Search apps"))}" autocomplete="off" spellcheck="false" ${k(`ad-find-${key}`)}></label>
      <button type="button" class="btn ghost icon" aria-label="${esc(t("Cancel"))}" title="${esc(t("Cancel"))}" ${k(`ad-stop-${key}`)}>${ic("x", "sm")}</button>`;
}

function desktopRow(key, label, disabled) {
  const apps = S.apps.desktops[key] || [];
  const full = apps.length >= S.apps.max;
  const add = full || disabled ? "" : addControl(key);
  return `<div class="ad-desk${apps.length ? " used" : ""}${disabled ? " off" : ""}" data-sid="apps.${esc(key)}">
      <div class="ad-head"><span class="ad-num">${esc(label)}</span><b>${esc(desktopName(key))}</b>
        <span class="ad-count">${apps.length ? esc(t("{n} of {max}", { n: apps.length, max: S.apps.max })) : ""}</span>${add}</div>
      ${apps.length ? `<div class="ad-apps">${apps.map((a, i) => appTile(key, a, i)).join("")}</div>` : ""}
    </div>`;
}

const rows = (groupName, prefix, disabled = false) =>
  Array.from({ length: DESKTOPS }, (_, i) => desktopRow(`${groupName}:${i + 1}`, `${prefix}${i + 1}`, disabled)).join("");

/* A group of desktops that folds away (open at first); folded, it says how many apps it has. */
function foldable(groupName, title, sub, body) {
  const key = `ad-fold-${groupName}`;
  const open = !UI.open[key];
  on(key, { click: () => { UI.open[key] = open; if (open && UI.adAdding && UI.adAdding.startsWith(`${groupName}:`)) UI.adAdding = null; render(); } });
  const count = Object.entries(S.apps.desktops).filter(([d]) => d.startsWith(`${groupName}:`)).reduce((n, [, apps]) => n + apps.length, 0);
  return `<section class="sec ad-sec" data-open="${open}">
      <button type="button" class="ad-fold" aria-expanded="${open}" ${k(key)}>${ic("chevD", "exp-chev")}<h2>${title}</h2>
        ${open ? `<span class="sub">${sub}</span>` : `<span class="sub">${esc(count === 1 ? t("1 app") : count ? t("{n} apps", { n: count }) : t("No apps"))}</span>`}</button>
      ${open ? body : ""}</section>`;
}

export function pageApps() {
  const scratchOff = !S.apps.scratch;
  return `${ph(esc(t("App to desktop")), esc(t("Chosen apps always start on their desktop, in the background; a rocket shows when one starts out of sight. For 5 seconds they are kept there, after that they can be moved.")))}
      ${foldable("scratch", esc(t("Scratch desktops")), esc(t("SUPER + S. While they are closed, an app waits there unseen.")),
        `${scratchOff ? notice("info", esc(t("The scratch desktops are off (Keyboard). Their apps start anywhere until they are on again."))) : ""}
        <div class="ad-list" data-sid="apps.scratch">${rows("scratch", "S", scratchOff)}</div>`)}
      ${foldable("desk", esc(t("Desktops")), esc(t("Desktops 1 to 10, on the laptop while the external screen keeps its own.")),
        `<div class="ad-list" data-sid="apps.desk">${rows("desk", "")}</div>`)}`;
}
