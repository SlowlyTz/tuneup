/* Widgets: the overview (a card per widget, layouts) and a widget's own page
 * (its content, and where & when it shows). Colors, font and effects are set
 * on the desktop itself (the arrange tool). */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { go } from "../../core/router.js";
import { S, UI } from "../../core/state.js";
import { k, on, render } from "../../core/view.js";
import { button, toggle } from "../../ui/controls.js";
import { ic } from "../../ui/icons.js";
import { notice, ph, row, spinner } from "../../ui/layout.js";
import { renderFields } from "./fields.js";
import { layoutBar } from "./layouts.js";
import { arrange, setEnabled, W_ICON, wid } from "./model.js";
import { wpBox } from "./previews.js";

const arrangeButton = () => button("arrange", `${ic("arrange", "sm")}${esc(t("Arrange on the desktop"))}`, arrange, { cls: "btn primary lg", attrs: 'data-sid="widgets.arrange"' });

function badge(w) {
  if (w.missing && w.missing.length) return { cls: "warn", text: t("Not installed: {what} is missing", { what: w.missing.join(", ") }) };
  if (w.enabled && !w.placed) return { cls: "", text: t("Not arranged yet") };
  if (w.enabled && !w.onDesktop) return { cls: "neutral", text: t("Only in the bar") };
  return null;
}

function card(w) {
  const b = badge(w);
  on(`w-${w.kind}`, { click: () => { UI.wtab = "content"; go(`#/widgets/${w.kind}`); } });
  return `<div class="wcard${w.enabled ? "" : " off"}" data-sid="widgets.${w.kind}">
        <button type="button" class="wcard-open" aria-label="${esc(t("Open {name}", { name: t(w.name) }))}" title="${esc(t(w.description || ""))}" ${k(`w-${w.kind}`)}>${wpBox(w)}</button>
        ${b ? `<span class="pill wcard-badge ${b.cls}">${esc(b.text)}</span>` : ""}
        <div class="wcard-foot">${ic(W_ICON[w.kind] || "widgets", "sm")}<b>${esc(t(w.name))}</b>${toggle(`wt-${w.kind}`, w.enabled, (v) => setEnabled(w, v), { label: t(w.name), text: false })}</div></div>`;
}

function overview() {
  const shown = S.widgets.filter((w) => w.enabled).length;
  return `${ph(esc(t("Widgets")), esc(t("{on} of {all} are on. Click a widget to set it up.", { on: shown, all: S.widgets.length })), arrangeButton())}
      <div class="layouts-row">${layoutBar()}</div>
      <div class="wgrid">${S.widgets.map(card).join("")}</div>`;
}

function cavaMissing(w) {
  if (!w.missing || !w.missing.length) return "";
  const install = async () => {
    UI.cavaBusy = true; render();
    await change(() => api.installCava(), null, { reload: ["widgets"], msg: t("cava is installed") });
    UI.cavaBusy = false; render();
  };
  return `<div class="sec">${notice("alert", esc(t("Not installed: {what} is missing. The visualizer needs this program to hear the sound.", { what: w.missing.join(", ") })), "warn")}
      <div style="margin-top:var(--s2)">${button("installcava", UI.cavaBusy ? `${spinner()}${esc(t("Installing …"))}` : `${ic("plus", "sm")}${esc(t("Install cava"))}`, install, { cls: "btn primary", attrs: UI.cavaBusy ? "disabled" : "" })}</div></div>`;
}

function tabs(tab) {
  on("tab-content", { click: () => { UI.wtab = "content"; render(); } });
  on("tab-where", { click: () => { UI.wtab = "where"; render(); } });
  const one = (id, short, label) => `<button type="button" class="tab" role="tab" id="tab-${short}" aria-controls="tabpanel" aria-selected="${tab === id}" tabindex="${tab === id ? 0 : -1}" ${k(`tab-${id}`)}>${esc(label)}</button>`;
  return `<div class="tabs" role="tablist" aria-label="${esc(t("Sections"))}">${one("content", "c", t("Content"))}${one("where", "w", t("Where & when"))}</div>`;
}

function detail(w) {
  const tab = UI.wtab;
  const name = t(w.name);
  on("crumb", { click: (e) => { e.preventDefault(); go("#/widgets"); } });
  const missing = cavaMissing(w);
  const unplaced = w.enabled && !w.placed && !missing ? `<div class="sec">${notice("info", esc(t("It starts in the middle of the screen. Put it where you want it on the desktop.")))}</div>` : "";
  const hint = `<div class="row hint-card" style="margin-top:var(--s5)">${ic("palette")}<div class="row-text"><div class="row-title"><span class="t">${esc(t("Colors, font and effects are set right on the desktop"))}</span></div></div>${button("arrange2", `${esc(t("Arrange"))}${ic("chevR", "sm")}`, arrange)}</div>`;
  const state = w.enabled ? (w.onDesktop ? t("Shown") : t("Only in the bar")) : t("Off: hidden, the settings stay");
  return `<header class="ph"><div class="ph-text"><nav class="crumbs" aria-label="${esc(t("Path"))}"><a href="#/widgets" ${k("crumb")}>${esc(t("Widgets"))}</a>${ic("chevR")}<span aria-current="page">${esc(name)}</span></nav>${w.description ? `<p>${esc(t(w.description))}</p>` : ""}</div><div class="ph-actions">${arrangeButton()}</div></header>
      <div class="wd-head">${wpBox(w, true)}
        <div class="stack">${row({ sid: `widgets.${w.kind}.on`, icon: W_ICON[w.kind], title: esc(t("On the desktop")), desc: esc(state), end: toggle(`wt-${w.kind}`, w.enabled, (v) => setEnabled(w, v), { label: t("{name} on the desktop", { name }) }) })}</div>
      </div>
      ${missing}${unplaced}
      ${tabs(tab)}
      <div role="tabpanel" id="tabpanel" aria-labelledby="${tab === "content" ? "tab-c" : "tab-w"}">${tab === "content" ? renderFields(w, "content") + hint : renderFields(w, "where")}</div>`;
}

export const pageWidgets = (r) => (r.sub && wid(r.sub) ? detail(wid(r.sub)) : overview());
