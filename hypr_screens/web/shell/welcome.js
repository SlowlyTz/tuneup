/* The welcome, once: after Tuneup was installed ("Welcome to Tuneup") or
 * updated ("Tuneup was updated", from → to, what is new). Asked from the
 * backend (welcome()); closing it in any way calls dismissWelcome(). */
import { optional } from "../core/api.js";
import { esc } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { closeDialog, dialog, onDialogClose, openDialog } from "../ui/dialog.js";

const logo = '<img class="welcome-logo" src="img/tuneup.svg" alt="">';

function installedHtml() {
  return `<div class="welcome">${logo}
      <h2>${esc(t("Welcome to Tuneup"))}</h2>
      <p class="tagline">${esc(t("The settings app Omarchy is missing"))}</p>
      <p>${esc(t("Tuneup now lives in the tray – a click on its icon opens these settings."))}</p>
      <div class="welcome-foot"><button type="button" class="btn primary lg" data-d="go" autofocus>${esc(t("Let's go"))}</button></div>
    </div>`;
}

function updatedHtml(w) {
  const news = w.releasesUrl ? `<a class="btn lg" href="${esc(w.releasesUrl)}" target="_blank" rel="noopener">${esc(t("What's new?"))}</a>` : "";
  return `<div class="welcome">${logo}
      <h2>${esc(t("Tuneup was updated"))}</h2>
      <p class="versions" aria-label="${esc(t("from {from} to {to}", { from: w.from || "?", to: w.to || "?" }))}"><span class="num">${esc(w.from || "?")}</span><span class="arrow" aria-hidden="true">→</span><span class="num to">${esc(w.to || "?")}</span></p>
      <div class="welcome-foot">${news}<button type="button" class="btn primary lg" data-d="go" autofocus>${esc(t("Continue"))}</button></div>
    </div>`;
}

export async function showWelcome() {
  let w;
  try { w = await optional("welcome"); } catch { return; }
  if (!w || !w.show || dialog.open) return;
  openDialog(w.kind === "updated" ? updatedHtml(w) : installedHtml(), { go: () => closeDialog() },
    { label: w.kind === "updated" ? t("Tuneup was updated") : t("Welcome to Tuneup") });
  dialog.classList.add("welcome-dlg");
  onDialogClose(() => {
    dialog.classList.remove("welcome-dlg");
    optional("dismissWelcome").catch(() => {});
  });
}
