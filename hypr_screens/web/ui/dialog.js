/* The one modal dialog of the page (#dialog): open/close, "keep it?" with a
 * countdown, and a yes/no question. */
import { $, esc } from "../core/dom.js";
import { t, tHtml } from "../core/i18n.js";
import { Pop } from "./popover.js";
import { hideToast, toast } from "./toast.js";

export const dialog = $("#dialog");
let cleanup = null;
let returnTo = null;

/* Runs once when the dialog closes, however it closes (e.g. the key capture's keymap). */
export const onDialogClose = (fn) => { cleanup = fn; };
export const runDialogCleanup = () => { if (cleanup) { const c = cleanup; cleanup = null; c(); } };

/* actions: {name: (button) => …} for buttons with data-d="name". */
export function openDialog(html, actions, { onCancel, onKey, focus, label } = {}) {
  if (dialog.open) closeDialog();
  returnTo = document.activeElement;
  hideToast();
  Pop.close(false);
  dialog.innerHTML = html;
  const heading = $("h2", dialog);
  if (heading) { heading.id = "dlg-title"; dialog.setAttribute("aria-labelledby", "dlg-title"); } else dialog.removeAttribute("aria-labelledby");
  if (label) dialog.setAttribute("aria-label", label); else dialog.removeAttribute("aria-label");
  dialog.onclick = (e) => {
    const b = e.target.closest("[data-d]");
    if (b && !b.disabled && actions[b.dataset.d]) actions[b.dataset.d](b);
  };
  dialog.oncancel = (e) => { e.preventDefault(); if (onCancel) onCancel(); else closeDialog(); };
  dialog.onkeydown = onKey || null;
  dialog.showModal();
  const f = focus ? $(focus, dialog) : $("[autofocus]", dialog);
  if (f) f.focus();
}

export function closeDialog() {
  runDialogCleanup();
  dialog.onkeyup = null;
  if (dialog.open) dialog.close();
  const back = returnTo;
  returnTo = null;
  if (back && document.contains(back)) back.focus({ preventScroll: true });
  else if (back && back.dataset && back.dataset.k) {
    const el = $(`[data-k="${CSS.escape(back.dataset.k)}"]`);
    if (el) el.focus({ preventScroll: true });
  }
}

const KEEP_SECONDS = 15;
const RING = 2 * Math.PI * 19;

/* "Keep this?" with a countdown; going back (or letting it run out) runs `undo`. */
export function keepDialog(undo, title) {
  let left = KEEP_SECONDS;
  const draw = () => {
    const ring = $(".count-ring .fg", dialog);
    if (ring) ring.style.strokeDashoffset = String(RING * (1 - left / KEEP_SECONDS));
    for (const id of ["#keep-n", "#keep-s"]) { const n = $(id, dialog); if (n) n.textContent = left; }
  };
  const back = async () => { closeDialog(); if (undo) await undo(); toast(t("Reverted")); };
  openDialog(`
      <div class="dlg-body">
        <h2>${esc(title || t("Keep this display setting?"))}</h2>
        <div class="count-ring"><span class="wrap"><svg viewBox="0 0 44 44" aria-hidden="true"><circle class="bg" cx="22" cy="22" r="19"/><circle class="fg" cx="22" cy="22" r="19" stroke-dasharray="${RING}" stroke-dashoffset="0"/></svg><span class="n" id="keep-n" aria-hidden="true">${left}</span></span>
        <p style="margin:0">${tHtml("Goes back in {seconds} s unless you press something.", "seconds", `<span class="num" id="keep-s">${left}</span>`)}</p></div>
      </div>
      <div class="dlg-foot">
        <button type="button" class="btn" data-d="revert">${esc(t("Revert"))}</button>
        <button type="button" class="btn primary" data-d="keep" autofocus>${esc(t("Keep"))}</button>
      </div>`, {
    keep: () => { closeDialog(); toast(t("Saved")); },
    revert: back,
  }, { onCancel: back });
  const timer = setInterval(() => {
    left -= 1;
    draw();
    if (left <= 0) back();
  }, 1000);
  onDialogClose(() => clearInterval(timer));
}

/* A yes/no question; resolves true for `ok`. */
export function confirmDialog({ title, text, ok, danger = false }) {
  return new Promise((resolve) => {
    const answer = (yes) => { closeDialog(); resolve(yes); };
    openDialog(`
        <div class="dlg-body"><h2>${esc(title)}</h2><p>${esc(text)}</p></div>
        <div class="dlg-foot">
          <button type="button" class="btn" data-d="no" autofocus>${esc(t("Cancel"))}</button>
          <button type="button" class="btn ${danger ? "danger solid" : "primary"}" data-d="yes">${esc(ok)}</button>
        </div>`, {
      yes: () => answer(true),
      no: () => answer(false),
    }, { onCancel: () => answer(false) });
  });
}
