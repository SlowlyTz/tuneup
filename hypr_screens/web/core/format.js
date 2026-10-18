/* Numbers, times and error texts in the app's language. */
import { NB } from "./dom.js";
import { loc, t } from "./i18n.js";
import { S } from "./state.js";

export const nf = (n, digits = 0) => new Intl.NumberFormat(loc(), { maximumFractionDigits: digits }).format(n);
export const pct = (n) => new Intl.NumberFormat(loc(), { style: "percent", maximumFractionDigits: 0 }).format(n / 100);
export const hz = (rate) => `${nf(rate, 2)}${NB}Hz`;
export const res = (w, h) => `${w}${NB}×${NB}${h}`;

export function minutes(m) {
  if (m == null) return "";
  const h = Math.floor(m / 60), rest = m % 60;
  if (!h) return t("{m} min", { m: rest });
  return rest ? t("{h} h {m} min", { h, m: rest }) : t("{h} h", { h });
}

/* Intl.DateTimeFormat that never throws (a bad time zone gives ""). */
export const dtf = (options, date = new Date()) => {
  try { return new Intl.DateTimeFormat(loc(), options).format(date); } catch { return ""; }
};

/* "5 min ago", "in 2 h" – `epoch` in seconds. */
export function ago(epoch, now = Date.now()) {
  const seconds = Math.round(epoch - now / 1000);
  const rtf = new Intl.RelativeTimeFormat(loc(), { numeric: "auto", style: "short" });
  const abs = Math.abs(seconds);
  if (abs < 60) return rtf.format(Math.round(seconds), "second");
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), "hour");
  return rtf.format(Math.round(seconds / 86400), "day");
}

/* What the backend's error codes mean (else its English message). */
const ERRORS = {
  config_unreadable: () => t("The settings file cannot be read. Fix or remove {file}.", { file: (S.about && S.about.configFile) || "config.json" }),
  unknown_screen: () => t("This screen is not known any more."),
  unknown_device: () => t("This device is gone."),
  unknown_widget: () => t("This widget is not known."),
  unknown_layout: () => t("This layout does not exist any more."),
  connected_screen: () => t("Unplug the screen first, then forget it."),
  internal_screen: () => t("The laptop screen cannot be forgotten."),
  not_connected: () => t("Only a connected screen can be dragged."),
  no_external: () => t("No external monitor is connected."),
  conflict: () => t("There is a layout with this name already."),
  force_muted: () => t("Force mute keeps this device silent. Switch it off first."),
  inactive: () => t("This device is switched off. Switch it on first."),
  not_set_up: () => t("This needs the one-time setup first."),
  not_plugged: () => t("Plug in the charger first."),
  unavailable: () => t("Not available on this computer."),
  cancelled: () => t("Cancelled or failed."),
  nothing_to_arrange: () => t("Switch a widget on first."),
  not_ready: () => t("The widgets are not ready yet. Try again in a moment."),
  apply_failed: () => t("Saved, but it could not be applied right now."),
  busy: () => t("An update is already running."),
};
export const errText = (err) => (err && ERRORS[err.code] ? ERRORS[err.code]() : (err && err.message) || t("Something went wrong."));
