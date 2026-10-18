/* The clock's second time zone: a search field over well-known cities (or any
 * "Area/City" zone typed in) and the chip of the chosen one. */
import { esc, norm } from "../../core/dom.js";
import { dtf } from "../../core/format.js";
import { t } from "../../core/i18n.js";
import { k, on, reg } from "../../core/view.js";
import { ic } from "../../ui/icons.js";
import { openListbox, Pop } from "../../ui/popover.js";

const SHOWN = 7;
const CITIES = () => [
  ["America/New_York", t("New York")], ["Europe/London", t("London")], ["Asia/Tokyo", t("Tokyo")], ["America/Los_Angeles", t("Los Angeles")],
  ["Australia/Sydney", t("Sydney")], ["Asia/Dubai", t("Dubai")], ["Asia/Singapore", t("Singapore")], ["America/Sao_Paulo", t("São Paulo")],
  ["Europe/Moscow", t("Moscow")], ["Europe/Istanbul", t("Istanbul")], ["Asia/Kolkata", t("Mumbai")], ["Asia/Hong_Kong", t("Hong Kong")],
  ["Africa/Johannesburg", t("Johannesburg")], ["America/Mexico_City", t("Mexico City")], ["Atlantic/Reykjavik", t("Reykjavík")],
  ["Europe/Lisbon", t("Lisbon")], ["Europe/Madrid", t("Madrid")], ["Europe/Rome", t("Rome")], ["Europe/Paris", t("Paris")], ["Europe/Berlin", t("Berlin")],
  ["America/Toronto", t("Toronto")], ["America/Chicago", t("Chicago")], ["Pacific/Honolulu", t("Honolulu")], ["Pacific/Auckland", t("Auckland")],
  ["Asia/Shanghai", t("Shanghai")], ["Asia/Seoul", t("Seoul")], ["America/Denver", t("Denver")], ["Asia/Bangkok", t("Bangkok")], ["Africa/Cairo", t("Cairo")],
];

export const tzName = (zone) => { const city = CITIES().find((z) => z[0] === zone); return city ? city[1] : String(zone).split("/").pop().replace(/_/g, " "); };
const tzTime = (zone) => dtf({ hour: "2-digit", minute: "2-digit", timeZone: zone });
const validZone = (zone) => { try { new Intl.DateTimeFormat("en", { timeZone: zone }); return true; } catch { return false; } };

/* The search field's suggestions for what is typed in `input`. */
function suggest(input, onPick) {
  const raw = input.value.trim(), q = norm(raw);
  const hits = CITIES().filter(([z, n]) => !q || norm(n).includes(q) || norm(z).includes(q)).slice(0, SHOWN);
  const typed = raw.includes("/") && validZone(raw) && !hits.some(([z]) => z === raw) ? [[raw, t("Use “{zone}”", { zone: raw })]] : [];
  const list = [...typed, ...hits];
  const field = input.closest(".field");
  if (!list.length) Pop.open(field, `<div class="sr-empty">${esc(t("No city found"))}</div>`, { keepFocus: true });
  else openListbox(field, { keepFocus: true, value: null, onPick, options: list.map(([z, n]) => ({ v: z, label: n, sub: tzTime(z), icon: ic("globe", "sm") })) });
  input.setAttribute("aria-expanded", "true");
}

/* The control: the chosen zone as a chip (with ×), else the search field. */
export function tzField(zone, set, disabled) {
  if (zone) {
    return `<span class="chip" aria-pressed="true">${ic("globe")}${esc(tzName(zone))}<span class="num" style="opacity:.75">${esc(tzTime(zone))}</span><button type="button" class="btn ghost icon tz-x" aria-label="${esc(t("Remove the second time zone"))}"${disabled ? " disabled" : ""} ${reg("tz-rm", { click: () => set("") })}>${ic("x", "xs")}</button></span>`;
  }
  on("tz", { combo: (input) => suggest(input, set) });
  return `<label class="field" style="min-width:260px">${ic("search")}<input type="text" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="popover" aria-label="${esc(t("Search a second time zone"))}" placeholder="${esc(t("Search a city, e.g. Tokyo"))}" autocomplete="off" spellcheck="false"${disabled ? " disabled" : ""} ${k("tz")}></label>`;
}
