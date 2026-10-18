/* General: language, keeping the settings (the watcher's enforcer), help and version. */
import { api } from "../core/api.js";
import { change, showError } from "../core/change.js";
import { esc } from "../core/dom.js";
import { ago, dtf } from "../core/format.js";
import { bootTexts, loadTranslations, t } from "../core/i18n.js";
import { S } from "../core/state.js";
import { k } from "../core/view.js";
import { radios, toggle } from "../ui/controls.js";
import { ic } from "../ui/icons.js";
import { notice, ph, row, sec } from "../ui/layout.js";
import { toast } from "../ui/toast.js";

/* Sent when the texts changed without a reload. */
export const LANGUAGE_EVENT = "hypr-language";
/* How many corrections the card lists. */
const FIXES_SHOWN = 5;
const AREAS = {
  screens: { icon: "monitor", name: () => t("Screens") },
  desktops: { icon: "desktops", name: () => t("Desktops") },
  look: { icon: "window", name: () => t("Windows") },
  keys: { icon: "keyboard", name: () => t("Keyboard") },
  sound: { icon: "speaker", name: () => t("Sound") },
  samsung: { icon: "battery", name: () => t("Battery & power") },
};
const area = (id) => AREAS[id] || { icon: "sliders", name: () => id };

/* Button handlers that do not belong to one render. */
export const GLOBAL_HANDLERS = {
  guide: { click: () => api.openGuide().then(() => toast(t("The guide opens in the browser")), showError) },
  folder: { click: () => api.openConfigFolder().then(() => toast(t("Folder opened")), showError) },
};

function language() {
  const L = S.lang;
  const pick = async (code) => {
    const old = L.code;
    const done = await change(() => api.setLanguage(code), () => api.setLanguage(old), { reload: ["general"], msg: false });
    if (!done) return;
    // In the app's window the page loads again in the new language by itself;
    // in a browser the shell takes the new texts (shell/render.js).
    if (!bootTexts()) { await loadTranslations(); document.dispatchEvent(new Event(LANGUAGE_EVENT)); }
    toast(t("Saved"));
  };
  return `<div data-sid="general.lang">${radios("lang", L.items.map((x) => ({ v: x.code, label: x.name })), L.code, pick, { label: t("Language") })}</div>`;
}

/* One correction: what was put back, where, and when. */
function fixItem(fix) {
  const a = area(fix.area);
  const where = [a.name(), fix.detail].filter(Boolean).join(" · ");
  return `<li>${ic(a.icon)}<span class="fix-t"><b>${esc(t(fix.what))}</b><small>${esc(where)}</small></span><time class="muted small num" datetime="${new Date(fix.time * 1000).toISOString()}">${esc(ago(fix.time))}</time></li>`;
}

/* "Keep my settings": another app changes something → hypr-screens puts it back. */
function enforcement() {
  const E = S.enforcement;
  if (!E) return "";
  const set = (on) => change(() => api.setEnforcement(on), () => api.setEnforcement(!on), { reload: ["enforcement"], msg: on ? t("Your settings are kept") : t("Other apps may change your settings") });
  const state = !E.enabled ? "" : E.running
    ? `<span class="pill ok">${esc(t("Watching"))}</span>`
    : `<span class="pill warn" title="${esc(t("Nothing is put back while it does not run."))}">${esc(t("The background service is not running"))}</span>`;
  const main = row({
    sid: "general.enforce", icon: "lock", title: esc(t("Put back what other apps change")),
    desc: esc(t("When another app changes a setting made here, hypr-screens sets it back.")),
    end: `${state}${toggle("enforce", E.enabled, set, { label: t("Keep my settings") })}`,
  });
  const until = (b) => dtf({ hour: "2-digit", minute: "2-digit" }, new Date(b.until * 1000));
  const backedOff = (E.backedOff || []).map((b) => notice("alert", `${esc(t("“{what}” keeps being changed by another app. hypr-screens leaves it alone until {time}.", { what: t(b.what), time: until(b) }))}<small>${esc(area(b.area).name())}</small>`, "warn")).join("");
  const fixes = (E.fixes || []).slice().sort((a, b) => b.time - a.time).slice(0, FIXES_SHOWN);
  const list = !E.enabled ? "" : `<div class="card fixes"><div class="sub-h">${esc(t("Put back lately"))}</div>${fixes.length
    ? `<ul>${fixes.map(fixItem).join("")}</ul>`
    : `<p class="muted small">${esc(t("Nothing had to be put back yet."))}</p>`}</div>`;
  return sec(esc(t("Keep my settings")), `<div class="stack">${main}${list}</div>${backedOff ? `<div class="backoffs">${backedOff}</div>` : ""}`);
}

const link = (key, sid, icon, title, desc, { mono = false, tip = "" } = {}) =>
  `<button type="button" class="row" data-sid="${sid}" ${k(key)}>${ic(icon)}<div class="row-text"><div class="row-title"><span class="t">${esc(title)}</span></div><div class="row-desc${mono ? " mono" : ""}"${tip ? ` title="${esc(tip)}"` : ""}>${esc(desc)}</div></div>${ic("external", "chev")}</button>`;

export function pageGeneral() {
  const A = S.about;
  return `${ph(esc(t("General")), esc(t("Language, help and version.")))}
      ${sec(esc(t("Language")), language())}
      ${enforcement()}
      ${sec(esc(t("Help")), `<div class="stack">
        ${link("guide", "general.guide", "book", t("Open the guide"), t("All about screens, keys and widgets, on GitHub"))}
        ${link("folder", "general.folder", "folder", t("Open the settings folder"), A.configPath || A.configDir, { mono: true, tip: A.configFile || "" })}
      </div>`)}
      ${sec(esc(t("About")), `<div class="stack">${row({ sid: "general.version", icon: "info", title: "hypr-screens", desc: esc(t("For Hyprland and Omarchy")), end: `<span class="num muted">${esc(t("Version {version}", { version: A.version }))}</span>` })}</div>`)}`;
}
