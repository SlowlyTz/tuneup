/* General → Info: Tuneup and its version, updates (check, update, the
 * progress until Tuneup starts again), the links to the project, and
 * uninstalling. Every call is optional: an older backend has none of them,
 * then their rows are left out. */
import { api, optional } from "../core/api.js";
import { showError } from "../core/change.js";
import { $, esc } from "../core/dom.js";
import { errText } from "../core/format.js";
import { t } from "../core/i18n.js";
import { route } from "../core/router.js";
import { S } from "../core/state.js";
import { afterRender, render } from "../core/view.js";
import { button } from "../ui/controls.js";
import { closeDialog, confirmDialog, dialog, openDialog } from "../ui/dialog.js";
import { ic } from "../ui/icons.js";
import { notice, row, sec, spinner } from "../ui/layout.js";

const STATUS_MS = 1000;
/* Why an update cannot run here, by the backend's reason. */
const REASONS = {
  not_git: () => t("Installed without git: update with the installer."),
  local_changes: () => t("The Tuneup folder has changes of its own: update it by hand."),
  diverged: () => t("Your copy differs from GitHub: update it by hand."),
  offline: () => t("No connection to GitHub. Try again later."),
};

/* known: the backend can update (and uninstall); checked: asked for a new version once. */
const U = { known: false, checked: false, checking: false, check: null, checkError: null, status: null, timer: 0 };

/* Updating and uninstalling are there (the backend has them). */
export const canMaintain = () => U.known;

const busyStatus = () => U.status && (U.status.state === "running" || U.status.state === "done");

/* Asks once whether the backend can update (and how an update is going). */
export async function learnUpdates() {
  try { U.status = (await optional("updateStatus")) ?? null; } catch { U.status = null; }
  U.known = U.status !== null;
  if (U.known && U.status.state === "running") follow();
}

async function check() {
  U.checking = true; U.checkError = null;
  render();
  try { U.check = (await api.checkUpdate()) || null; }
  catch (err) { U.checkError = err; }
  U.checking = false;
  render();
}

/* Polls the update until it is done or failed (Tuneup then starts again). */
function follow() {
  clearTimeout(U.timer);
  const step = async () => {
    try { U.status = await api.updateStatus(); } catch (err) { U.status = { state: "failed", error: errText(err) }; }
    if (route().page === "general") render();
    if (U.status && U.status.state === "running") U.timer = setTimeout(step, STATUS_MS);
  };
  U.timer = setTimeout(step, STATUS_MS);
}

async function update() {
  const to = U.check.latest;
  const ok = await confirmDialog({
    title: t("Update to version {version}?", { version: to }),
    text: t("Tuneup gets the new version and starts again. This window closes and opens again by itself."),
    ok: t("Update"),
  });
  if (!ok) return;
  try {
    await api.runUpdate();
    U.status = { state: "running", from: U.check.current, to };
    render();
    follow();
  } catch (err) { showError(err); }
}

/* The update's log: its last lines (a list, or one text). */
const logText = (log) => (Array.isArray(log) ? log.join("\n") : String(log || ""));

/* The update failed: why, and its log to fold out. */
const failedNotice = (s) => `<div class="notice warn">${ic("alert")}<div class="notice-b"><p>${esc(t("The update failed: {error}", { error: REASONS[s.error] ? REASONS[s.error]() : s.error || t("Something went wrong.") }))}</p>${logText(s.log) ? `<details class="log"><summary>${esc(t("Show the log"))}</summary><pre>${esc(logText(s.log))}</pre></details>` : ""}</div></div>`;

/* The update row's state on the right and below. */
function updateRow() {
  const s = U.status, c = U.check;
  let desc, end = "", below = "";
  if (s && s.state === "running") {
    desc = t("Updating to {version} … Tuneup starts again in a moment", { version: s.to || (c && c.latest) || "" });
    end = spinner();
  } else if (s && s.state === "done") {
    desc = t("Updated to {version}. Tuneup starts again …", { version: s.to || "" });
    end = `<span class="pill ok">${ic("check")}${esc(t("Done"))}</span>`;
  } else if (U.checking) {
    desc = t("Looking for a new version …");
    end = spinner();
  } else {
    const again = button("upd-check", `${ic("cycle", "sm")}${esc(t("Check again"))}`, check, { cls: "btn ghost" });
    if (U.checkError) {
      desc = errText(U.checkError);
      end = again;
    } else if (c && c.available) {
      desc = c.commitsBehind ? t("Version {version} is available ({n} changes)", { version: c.latest, n: c.commitsBehind }) : t("Version {version} is available", { version: c.latest });
      end = c.canUpdate ? button("upd-run", `${ic("bolt", "sm")}${esc(t("Update"))}`, update, { cls: "btn primary" }) : again;
      if (!c.canUpdate && REASONS[c.reason]) below = notice("info", esc(REASONS[c.reason]()));
    } else if (c) {
      desc = REASONS[c.reason] ? REASONS[c.reason]() : t("Version {version} is the newest", { version: c.current });
      end = `${REASONS[c.reason] ? "" : `<span class="pill ok">${esc(t("Up to date"))}</span>`}${again}`;
    } else {
      desc = "";
      end = again;
    }
    if (s && s.state === "failed") below = `${failedNotice(s)}${below}`;
  }
  return `${row({ sid: "general.update", icon: "cycle", title: esc(t("Check for updates")), desc: esc(desc), end })}${below ? `<div class="row-below">${below}</div>` : ""}`;
}

/* "Uninstall Tuneup": asks first (keep the settings or not), then removes it. */
async function uninstall() {
  openDialog(`
      <div class="dlg-body">
        <h2>${esc(t("Uninstall Tuneup?"))}</h2>
        <p>${esc(t("Removes Tuneup: the tray icon, this window, the widgets and its keys. System packages it installed (such as cava) stay."))}</p>
        <label class="check"><input type="checkbox" id="keep-settings" checked><span>${esc(t("Keep the settings"))}</span></label>
      </div>
      <div class="dlg-foot">
        <button type="button" class="btn" data-d="no" autofocus>${esc(t("Cancel"))}</button>
        <button type="button" class="btn danger solid" data-d="yes">${ic("trash", "sm")}${esc(t("Uninstall"))}</button>
      </div>`, {
    no: () => closeDialog(),
    yes: async () => {
      const keep = $("#keep-settings", dialog).checked;
      closeDialog();
      try { await api.uninstall(keep); } catch (err) { showError(err); return; }
      removing();
    },
  }, { label: t("Uninstall Tuneup?") });
}

/* While Tuneup removes itself: nothing more to do here. */
function removing() {
  openDialog(`<div class="dlg-body removing">${spinner()}<h2>${esc(t("Tuneup is being removed …"))}</h2><p>${esc(t("This window closes by itself."))}</p></div>`,
    {}, { onCancel: () => {}, label: t("Tuneup is being removed …") });
}

const external = (sid, icon, title, desc, url) =>
  `<a class="row" data-sid="${sid}" href="${esc(url)}" target="_blank" rel="noopener">${ic(icon)}<div class="row-text"><div class="row-title"><span class="t">${esc(title)}</span></div><div class="row-desc">${esc(desc)}</div></div>${ic("external", "chev")}</a>`;

export function infoSection() {
  const A = S.about;
  // The first time Info shows: look for a new version (once per opening).
  if (U.known && !U.checked && !busyStatus()) { U.checked = true; afterRender(() => queueMicrotask(check)); }
  const version = row({
    sid: "general.version", lead: '<img class="row-logo" src="img/tuneup.svg" alt="">', title: "Tuneup",
    desc: esc(t("The settings app Omarchy is missing")), end: `<span class="num muted">${esc(t("Version {version}", { version: A.version }))}</span>`,
  });
  const links = [
    A.releasesUrl ? external("general.releases", "sparkle", t("What's new"), t("All versions and their changes, on GitHub"), A.releasesUrl) : "",
    A.repoUrl ? external("general.repo", "book", t("Tuneup on GitHub"), A.repoUrl.replace(/^https?:\/\//, ""), A.repoUrl) : "",
  ].join("");
  const uninstallRow = U.known ? row({
    sid: "general.uninstall", icon: "trash", title: esc(t("Uninstall Tuneup")), desc: esc(t("Removes Tuneup from this computer")),
    end: button("uninstall", esc(t("Uninstall …")), uninstall, { cls: "btn danger", attrs: busyStatus() ? "disabled" : "" }),
  }) : "";
  // The destructive row comes last.
  return sec(esc(t("About")), `<div class="stack">${version}${U.known ? updateRow() : ""}${links}${uninstallRow}</div>`);
}
