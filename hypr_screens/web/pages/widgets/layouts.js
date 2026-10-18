/* Widget layouts: the bar on the Widgets page (load, save) and the dialog
 * that manages them (automatic with the screens connected now, rename, delete). */
import { api } from "../../core/api.js";
import { busy, change, showError } from "../../core/change.js";
import { $, esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S } from "../../core/state.js";
import { k, on, render } from "../../core/view.js";
import { group } from "../../ui/controls.js";
import { closeDialog, confirmDialog, dialog, openDialog } from "../../ui/dialog.js";
import { ic } from "../../ui/icons.js";
import { emptyState } from "../../ui/layout.js";
import { Pop } from "../../ui/popover.js";
import { toast } from "../../ui/toast.js";
import { scr, sname } from "../screens/model.js";

const NAME_MAX = 40;

/* Undo brings back the widgets exactly as they were, also when unsaved. */
const loadLayout = (name) =>
  change(() => api.loadLayout(name), (result) => api.restoreWidgets(result.previous), { reload: ["widgets"], msg: t("Layout “{name}” loaded", { name }) });

async function saveLayout(name) {
  if (S.layouts.items.includes(name) && name !== S.layouts.current) {
    const ok = await confirmDialog({ title: t("Replace “{name}”?", { name }), text: t("The layout of this name keeps the widgets as they are now instead."), ok: t("Replace") });
    if (!ok) return;
  }
  change(() => api.saveLayout(name), null, { reload: ["widgets"], msg: t("Layout “{name}” saved", { name }) });
}

/* The small popover to save the widgets as a layout (or update the one shown now). */
function savePopover(anchor) {
  const current = S.layouts.current;
  const update = current ? `<div class="pop-sep"></div><button type="button" class="opt" data-pf="update">${ic("cycle", "sm")}<span class="opt-l">${esc(t("Update “{name}”", { name: current }))}</span></button>` : "";
  Pop.open(anchor, `<div class="pop-h">${esc(t("Save layout"))}</div><div class="pop-field"><label class="field" style="min-width:240px">${ic("widgets")}<input id="layout-name" maxlength="${NAME_MAX}" placeholder="${esc(t("Name, e.g. Presentation"))}" aria-label="${esc(t("Name of the layout"))}"></label></div><div class="pop-foot"><button type="button" class="btn" data-pf="cancel">${esc(t("Cancel"))}</button><button type="button" class="btn primary" data-pf="save">${esc(t("Save"))}</button></div>${update}`, {
    minWidth: false, label: t("Save layout"),
    onClick: (ev) => {
      const b = ev.target.closest("[data-pf]");
      if (!b) return;
      if (b.dataset.pf === "cancel") Pop.close();
      else if (b.dataset.pf === "update") { Pop.close(); saveLayout(current); }
      else save();
    },
    onKey: (ev) => { if (ev.key !== "Enter") return false; ev.preventDefault(); save(); return true; },
  });
  const save = () => {
    const input = $("#layout-name");
    const name = input.value.trim();
    if (!name) { input.focus(); return; }
    Pop.close();
    saveLayout(name);
  };
}

export function layoutBar() {
  const L = S.layouts;
  const chips = group("layout", L.items.map((name) => {
    const l = (L.layouts || []).find((x) => x.name === name) || {};
    return { v: name, label: name, auto: l.auto, title: l.auto ? t("Loads by itself with: {screens}", { screens: (l.screenNames || []).join(", ") }) : "" };
  }), L.current, loadLayout, { cls: "chips", itemCls: "chip", label: t("Layout"), item: (o) => `${o.auto ? ic("plug") : ""}${esc(o.label)}` });
  on("savelayout", { click: (_e, el) => savePopover(el) });
  on("managelayouts", { click: layoutsDialog });
  return `<div class="layouts" data-sid="widgets.layouts"><span class="lbl">${esc(t("Layout:"))}</span>${L.items.length ? chips : `<span class="muted small">${esc(t("none saved yet"))}</span>`}<button type="button" class="chip dashed" aria-haspopup="dialog" ${k("savelayout")}>${ic("plus")}${esc(t("Save"))}</button>${L.items.length ? `<button type="button" class="chip ghost" aria-haspopup="dialog" ${k("managelayouts")}>${ic("sliders")}${esc(t("Manage"))}</button>` : ""}</div>`;
}

function layoutRow(L, l, i, screens) {
  return `<div class="row lay-row" data-i="${i}">
          ${ic(l.auto ? "plug" : "widgets")}
          <div class="row-text"><div class="row-title"><span class="t">${esc(l.name)}</span>${L.current === l.name ? `<span class="pill">${esc(t("Shown now"))}</span>` : ""}</div>
            <div class="row-desc">${esc(l.auto ? t("Automatic with: {screens}", { screens: (l.screenNames || []).join(", ") || "–" }) : t("Only by hand"))}</div></div>
          <div class="row-end">
            <button type="button" class="sw" role="switch" aria-checked="${!!l.auto}" aria-label="${esc(t("Load “{name}” automatically with {screens}", { name: l.name, screens }))}" title="${esc(t("Automatic with the screens connected now"))}" data-d="auto" data-i="${i}"><span class="sw-label">${esc(t("Automatic"))}</span><span class="sw-track"></span></button>
            <button type="button" class="btn ghost icon" aria-label="${esc(t("Rename “{name}”", { name: l.name }))}" title="${esc(t("Rename"))}" data-d="rename" data-i="${i}">${ic("edit", "sm")}</button>
            <button type="button" class="btn ghost icon danger" aria-label="${esc(t("Delete “{name}”", { name: l.name }))}" title="${esc(t("Delete"))}" data-d="delete" data-i="${i}">${ic("trash", "sm")}</button>
          </div></div>`;
}

function layoutsDialog() {
  const draw = () => {
    const L = S.layouts;
    const screens = (L.connected || []).map((id) => sname(scr(id))).join(", ");
    return `<div class="dlg-body wide">
        <h2>${esc(t("Widget layouts"))}</h2>
        <p>${esc(t("A layout keeps where every widget is. “Automatic” loads it whenever exactly the screens connected now are connected."))}</p>
        <div class="stack lay-list">${L.layouts.length ? L.layouts.map((l, i) => layoutRow(L, l, i, screens)).join("") : emptyState("widgets", esc(t("No layout saved yet")))}</div>
      </div>
      <div class="dlg-foot"><button type="button" class="btn primary" data-d="close" autofocus>${esc(t("Done"))}</button></div>`;
  };
  const redraw = (focus) => {
    dialog.innerHTML = draw();
    ((focus && $(focus, dialog)) || $('[data-d="close"]', dialog)).focus();
  };
  const run = async (call, focus) => {
    await busy(async () => { try { S.layouts = await call(); } catch (err) { showError(err); } });
    render();
    if (dialog.open) redraw(focus);
  };
  const at = (b) => S.layouts.layouts[+b.dataset.i];
  const rename = (b) => {
    const i = b.dataset.i, name = at(b).name;
    $(`.lay-row[data-i="${i}"] .row-text`, dialog).innerHTML = `<label class="field">${ic("edit")}<input id="lay-rename" maxlength="${NAME_MAX}" value="${esc(name)}" aria-label="${esc(t("New name for “{name}”", { name }))}"></label>`;
    const input = $("#lay-rename", dialog);
    input.focus(); input.select();
    let done = false;
    const finish = (ok) => {
      if (done) return;
      done = true;
      const next = input.value.trim();
      const focus = `[data-d="rename"][data-i="${i}"]`;
      if (ok && next && next !== name) run(() => api.renameLayout(name, next), focus);
      else redraw(focus);
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); finish(true); }
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(false); }
    });
    input.addEventListener("blur", () => finish(true));
  };
  openDialog(draw(), {
    close: () => closeDialog(),
    auto: (b) => { const l = at(b); run(() => api.setLayoutAuto(l.name, !l.auto), `[data-d="auto"][data-i="${b.dataset.i}"]`); },
    delete: (b) => { const name = at(b).name; run(() => api.deleteLayout(name)).then(() => toast(t("Layout “{name}” deleted", { name }))); },
    rename,
  }, { label: t("Widget layouts") });
}
