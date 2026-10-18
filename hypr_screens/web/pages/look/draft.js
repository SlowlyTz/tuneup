/* The window look being edited: a draft that Hyprland shows live (previewLook);
 * "Discard" ends the preview (revertLook), "Apply" keeps it (saveLook) and
 * asks "keep it?" for 15 s. The bar at the bottom offers both while the draft
 * differs from what is kept. */
import { api } from "../../core/api.js";
import { busy, showError } from "../../core/change.js";
import { $, clone, eq, esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { reload, S, takeLook } from "../../core/state.js";
import { reg, render } from "../../core/view.js";
import { keepDialog } from "../../ui/dialog.js";
import { ic } from "../../ui/icons.js";
import { toast } from "../../ui/toast.js";
import { lpVars } from "./preview.js";

const PREVIEW_DELAY_MS = 120;

export const lookDirty = () => !!(S.look && S.lookDraft && (S.look.previewing || !eq(S.lookDraft, S.lookBase)));

/* One preview call at a time; the newest draft wins. */
const preview = { timer: 0, running: null, again: false };
function queuePreview() {
  clearTimeout(preview.timer);
  preview.timer = setTimeout(runPreview, PREVIEW_DELAY_MS);
}
async function runPreview() {
  if (preview.running) { preview.again = true; return; }
  const draft = clone(S.lookDraft);
  preview.running = (async () => {
    try {
      if (eq(draft, S.lookBase) && !S.look.previewing) await api.revertLook();
      else await api.previewLook(draft);
    } catch (err) { showError(err); }
  })();
  await preview.running;
  preview.running = null;
  if (preview.again) { preview.again = false; runPreview(); }
}
async function previewSettled() {
  clearTimeout(preview.timer);
  preview.again = false;
  if (preview.running) await preview.running;
}

/* Changes the draft. full: render the page again (else only the preview and the bar). */
export function setDraft(changes, { full = true, live = true } = {}) {
  Object.assign(S.lookDraft, changes);
  if (live) queuePreview();
  if (full) { render(); return; }
  const lp = $("#lp .lp");
  if (lp) lp.setAttribute("style", lpVars(S.lookDraft));
  renderApplyBar(true);
}

/* Sets the look from an API call that answers with look(). */
async function settle(call, message) {
  await previewSettled();
  await busy(async () => {
    try { takeLook(await call()); S.lookDraft = clone(S.look.values); if (message) toast(message); }
    catch (err) { showError(err); }
  });
  render();
}
const discardLook = () => settle(() => api.revertLook(), t("Discarded"));
export const resetLook = () => settle(() => api.resetLook(), t("Back to Omarchy’s look"));

async function applyLook() {
  await previewSettled();
  const before = { values: clone(S.lookBase), saved: clone(S.look.saved || {}) };
  try { takeLook(await busy(() => api.saveLook(clone(S.lookDraft)))); }
  catch (err) { showError(err); render(); return; }
  S.lookDraft = clone(S.look.values);
  render();
  keepDialog(async () => {
    try {
      takeLook(Object.keys(before.saved).length
        ? await api.saveLook({ ...before.values, borderColors: before.saved.borderColors ?? null })
        : await api.resetLook());
    } catch (err) { showError(err); await reload("look"); }
    S.lookDraft = clone(S.look.values);
    render();
  }, t("Keep this look?"));
}

/* The bar at the bottom of the Windows page (shown: the page is open and the draft differs). */
export function renderApplyBar(shown) {
  const bar = $("#applybar");
  const show = shown && !S.err.look && lookDirty();
  document.body.classList.toggle("has-bar", show);
  if (!show) { bar.hidden = true; bar.innerHTML = ""; return; }
  bar.innerHTML = `${ic("eye")}<p><b>${esc(t("Preview – not applied yet"))}</b></p>
      <button type="button" class="btn" ${reg("discard", { click: discardLook })}>${esc(t("Discard"))}</button>
      <button type="button" class="btn primary" ${reg("applylook", { click: applyLook })}>${ic("check", "sm")}${esc(t("Apply"))}</button>`;
  bar.hidden = false;
}

/* Leaving the app with a preview on: Hyprland goes back to the kept look. */
export const endPreview = () => { if (lookDirty()) api.revertLook().catch(() => {}); };
