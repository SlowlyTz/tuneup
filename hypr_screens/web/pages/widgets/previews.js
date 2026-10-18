/* Small previews of the widgets: how each one looks with its settings
 * (in the overview cards, on a widget's page and in its style cards). */
import { esc } from "../../core/dom.js";
import { dtf, minutes, pct } from "../../core/format.js";
import { loc, t } from "../../core/i18n.js";
import { S } from "../../core/state.js";
import { ic } from "../../ui/icons.js";
import { tzName } from "./timezones.js";

const p2 = (n) => String(n).padStart(2, "0");
/* Qt's date pattern (as the widget uses it): d dd ddd dddd M MM MMM MMMM yy yyyy, 'text'. */
const qtDate = (p, d = new Date()) => String(p || "").replace(/'([^']*)'|dddd|ddd|dd|d|MMMM|MMM|MM|M|yyyy|yy/g, (tok, quoted) => {
  if (quoted !== undefined) return quoted;
  return ({
    dddd: dtf({ weekday: "long" }, d), ddd: dtf({ weekday: "short" }, d), dd: p2(d.getDate()), d: d.getDate(),
    MMMM: dtf({ month: "long" }, d), MMM: dtf({ month: "short" }, d), MM: p2(d.getMonth() + 1), M: d.getMonth() + 1,
    yyyy: d.getFullYear(), yy: String(d.getFullYear()).slice(2),
  })[tok];
});
export function fmtDate(fmt, d = new Date(), pattern = "") {
  switch (fmt) {
    case "long": return dtf({ day: "numeric", month: "long" }, d);
    case "medium": return dtf({ day: "numeric", month: "short", year: "numeric" }, d);
    case "short": return dtf({ dateStyle: "short" }, d);
    case "iso": return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
    case "custom": return qtDate(pattern || "dddd d MMMM", d);
    default: return "";
  }
}
const clockDate = (c, d = new Date()) => {
  const date = fmtDate(c.date_format, d, c.date_pattern);
  return c.weekday && c.date_format !== "custom" ? `${dtf({ weekday: "long" }, d)}, ${date}` : date;
};
const fmtTime = (c, d = new Date(), zone) => dtf({ hour: "2-digit", minute: "2-digit", ...(c.seconds ? { second: "2-digit" } : {}), hour12: c.hours === "12", ...(zone ? { timeZone: zone } : {}) }, d);
function wordClock(d = new Date()) {
  let h = d.getHours() % 12, m = Math.round(d.getMinutes() / 5) * 5;
  if (m === 60) { m = 0; h = (h + 1) % 12; }
  if (loc().startsWith("de")) {
    const HN = ["zwölf", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf"];
    const cur = HN[h], nxt = HN[(h + 1) % 12];
    const P = { 0: [cur === "eins" ? "ein" : cur, " Uhr"], 5: ["fünf nach ", cur], 10: ["zehn nach ", cur], 15: ["viertel nach ", cur], 20: ["zwanzig nach ", cur], 25: ["fünf vor halb ", nxt], 30: ["halb ", nxt], 35: ["fünf nach halb ", nxt], 40: ["zwanzig vor ", nxt], 45: ["viertel vor ", nxt], 50: ["zehn vor ", nxt], 55: ["fünf vor ", nxt] }[m];
    return m === 0 ? `ES IST <b>${P[0].toUpperCase()}</b>${P[1].toUpperCase()}` : `ES IST ${P[0].toUpperCase()}<b>${P[1].toUpperCase()}</b>`;
  }
  const HN = ["twelve", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven"];
  const cur = HN[h], nxt = HN[(h + 1) % 12];
  const P = { 0: ["", cur, " o’clock"], 5: ["five past ", cur], 10: ["ten past ", cur], 15: ["quarter past ", cur], 20: ["twenty past ", cur], 25: ["twenty-five past ", cur], 30: ["half past ", cur], 35: ["twenty-five to ", nxt], 40: ["twenty to ", nxt], 45: ["quarter to ", nxt], 50: ["ten to ", nxt], 55: ["five to ", nxt] }[m];
  return `IT IS ${P[0].toUpperCase()}<b>${P[1].toUpperCase()}</b>${(P[2] || "").toUpperCase()}`;
}
function analogSvg(d = new Date(), seconds = false) {
  const hA = ((d.getHours() % 12) + d.getMinutes() / 60) * 30, mA = d.getMinutes() * 6, sA = d.getSeconds() * 6;
  const ticks = Array.from({ length: 12 }, (_, i) => `<line x1="32" y1="5" x2="32" y2="${i % 3 ? 8 : 10}" transform="rotate(${i * 30} 32 32)" stroke="currentColor" stroke-opacity="${i % 3 ? 0.4 : 0.8}" stroke-width="${i % 3 ? 1.5 : 2.2}" stroke-linecap="round"/>`).join("");
  return `<svg class="wv-analog" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="rgb(17 17 27 / .55)" stroke="rgb(255 255 255 / .12)"/>${ticks}<line x1="32" y1="32" x2="32" y2="17" transform="rotate(${hA} 32 32)" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><line x1="32" y1="32" x2="32" y2="10" transform="rotate(${mA} 32 32)" stroke="var(--c-accent)" stroke-width="2" stroke-linecap="round"/>${seconds ? `<line x1="32" y1="36" x2="32" y2="8" transform="rotate(${sA} 32 32)" stroke="var(--c-red)" stroke-width="1" stroke-linecap="round"/>` : ""}<circle cx="32" cy="32" r="2.5" fill="var(--c-accent)"/></svg>`;
}
const isoWeek = (d) => { const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); const day = x.getUTCDay() || 7; x.setUTCDate(x.getUTCDate() + 4 - day); return Math.ceil(((x - new Date(Date.UTC(x.getUTCFullYear(), 0, 1))) / 864e5 + 1) / 7); };
function calGrid(c) {
  const d = new Date(), y = d.getFullYear(), m = d.getMonth();
  const mon = c.week_start !== "sunday";
  const first = new Date(y, m, 1).getDay();
  const off = mon ? (first + 6) % 7 : first;
  const days = new Date(y, m + 1, 0).getDate();
  const heads = Array.from({ length: 7 }, (_, i) => `<b>${esc(dtf({ weekday: "narrow" }, new Date(2024, 0, (mon ? 1 : 7) + i)))}</b>`).join("");
  const cells = [];
  for (let i = 0; i < off + days; i++) {
    if (c.show_weeks && i % 7 === 0) cells.push(`<b class="wk">${isoWeek(new Date(y, m, Math.max(1, i - off + 1)))}</b>`);
    cells.push(i < off ? "<span></span>" : `<span${i - off + 1 === d.getDate() ? ' class="t"' : ""}>${i - off + 1}</span>`);
  }
  return `<div class="w box cal">${c.show_month ? `<div class="wv-s" style="margin-bottom:4px;font-weight:600;opacity:.9">${esc(dtf({ month: "long", year: "numeric" }, d))}</div>` : ""}<div class="wv-cal${c.show_weeks ? " wk" : ""}">${c.show_weeks ? "<b></b>" : ""}${heads}${cells.join("")}</div></div>`;
}
const VIS_H = [14, 26, 38, 30, 44, 22, 34, 18, 40, 28, 16, 32, 24, 12, 36, 20];
function visPreview(c) {
  const n = Math.max(8, Math.min(16, Math.round((c.bars || 32) / 3)));
  const hs = Array.from({ length: n }, (_, i) => VIS_H[i % VIS_H.length]);
  switch (c.style) {
    case "wave": return `<div class="w"><svg viewBox="0 0 120 50" width="130" height="50"><path d="M0 25 C10 5 20 45 30 25 S50 2 60 25 80 48 90 25 110 8 120 25" fill="none" stroke="var(--c-accent)" stroke-width="2.2" stroke-linecap="round"/><path d="M0 25 C12 15 22 35 34 25 S56 12 66 25 86 38 98 25 114 18 120 25" fill="none" stroke="var(--c-red)" stroke-width="1.4" opacity=".7"/></svg></div>`;
    case "dots": return `<div class="w"><div class="wv-dots">${hs.map((h) => `<i>${"<b></b>".repeat(Math.max(1, Math.round(h / 9)))}</i>`).join("")}</div></div>`;
    case "circle": return `<div class="w"><svg viewBox="0 0 64 64" width="64" height="64">${hs.concat(hs).map((h, i, all) => `<line x1="32" y1="17" x2="32" y2="${17 - h / 5}" transform="rotate(${(i * 360) / all.length} 32 32)" stroke="var(--c-accent)" stroke-width="2.4" stroke-linecap="round"/>`).join("")}<circle cx="32" cy="32" r="13" fill="none" stroke="rgb(255 255 255 / .18)"/></svg></div>`;
    case "mirrored": return `<div class="w"><div class="wv-vis mirror">${hs.map((h) => `<i style="height:${h * 1.1}px"></i>`).join("")}</div></div>`;
    default: return `<div class="w"><div class="wv-vis">${hs.map((h) => `<i style="height:${h}px"></i>`).join("")}</div></div>`;
  }
}
function npPreview(c) {
  const text = `<div class="np-t">${c.show_title ? `<div style="font-weight:600;font-size:12px">Nachtfahrt</div>` : ""}${c.show_artist ? `<div class="wv-s">Kollektiv Ost</div>` : ""}${c.show_album ? `<div class="wv-s" style="opacity:.5">Stadtlichter</div>` : ""}${c.show_progress ? `<div class="wv-bar" style="width:84px;height:3px;margin-top:6px"><i style="width:40%"></i></div>` : ""}${c.show_time ? `<div class="wv-s mono" style="font-size:8.5px;margin-top:2px">1:24 / 3:41</div>` : ""}${c.show_controls ? `<div class="np-ctl"><svg viewBox="0 0 24 24"><path d="M7 6v12M18 6l-8 6 8 6z"/></svg><svg viewBox="0 0 24 24"><path d="M8 6v12M16 6v12"/></svg><svg viewBox="0 0 24 24"><path d="M17 6v12M6 6l8 6-8 6z"/></svg></div>` : ""}</div>`;
  return `<div class="w box"><div class="np ${c.np_layout === "column" ? "col" : ""}">${c.show_cover ? '<span class="wv-art"></span>' : ""}${text}</div></div>`;
}
function wPreview(w) {
  const c = w.content;
  const level = (S.samsung && S.samsung.level) ?? 76;
  switch (w.kind) {
    case "clock": {
      if (c.clock_style === "analog") return `<div class="w">${analogSvg(new Date(), c.seconds)}</div>`;
      if (c.clock_style === "words") return `<div class="w box"><div class="wv-words">${wordClock()}</div></div>`;
      const time = fmtTime(c);
      const zone = c.zone2 ? `<div class="wv-s" style="margin-top:3px">${esc(tzName(c.zone2))} ${esc(fmtTime({ ...c, seconds: false }, new Date(), c.zone2))}</div>` : "";
      const date = c.date ? `<div class="wv-date">${esc(clockDate(c))}</div>` : "";
      if (c.clock_style === "flip") {
        const parts = time.split(/[:.\s]/).filter((x) => /\d/.test(x)).slice(0, c.seconds ? 3 : 2);
        return `<div class="w"><div class="wv-flip">${parts.map((x) => `<span>${esc(x)}</span>`).join("")}</div>${date}${zone}</div>`;
      }
      return `<div class="w"><div class="wv-time">${esc(time)}</div>${date}${zone}</div>`;
    }
    case "calendar": return calGrid(c);
    case "weather": {
      const deg = (n) => `${c.units === "f" ? Math.round(n * 1.8 + 32) : n}°`;
      const days = [1, 2, 3].map((i) => dtf({ weekday: "short" }, new Date(Date.now() + i * 864e5)));
      return `<div class="w box">${c.show_place ? `<div class="wv-s" style="margin-bottom:2px">Berlin</div>` : ""}<div class="wv-row"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke-width="1.6" stroke-linecap="round"><circle cx="9" cy="9" r="3.5" stroke="var(--c-yellow)"/><path d="M9 2.5v1.5M2.5 9H4M4.4 4.4l1 1M13.6 4.4l-1 1" stroke="var(--c-yellow)"/><path d="M8 19a3.5 3.5 0 0 1-.4-7 4.7 4.7 0 0 1 9-.1A3.5 3.5 0 0 1 17 19z" fill="rgb(205 214 244 / .9)" stroke="none"/></svg><span class="wv-big">${deg(12)}</span></div>${c.show_details ? `<div class="wv-s">${esc(t("Partly cloudy"))} · ${esc(pct(64))}</div>` : ""}${c.show_forecast ? `<div class="wv-s" style="display:flex;gap:8px;margin-top:4px;font-family:var(--mono)"><span>${esc(days[0])} ${deg(14)}</span><span>${esc(days[1])} ${deg(11)}</span><span>${esc(days[2])} ${deg(10)}</span></div>` : ""}</div>`;
    }
    case "battery": {
      const low = level <= (c.low || 20);
      return `<div class="w box"><div class="wv-row">${ic("battery")}<span class="wv-big">${c.show_percent ? esc(pct(level)) : ""}</span></div><div class="wv-bar" style="margin-top:6px"><i style="width:${level}%;background:${low ? "var(--c-red)" : "var(--c-green)"}"></i></div>${c.show_remaining ? `<div class="wv-s" style="margin-top:4px">${esc(t("{time} left", { time: minutes((S.samsung && S.samsung.remainingMinutes) || 320) }))}</div>` : ""}</div>`;
    }
    case "system": {
      const parts = [c.cpu && ["CPU", 23], c.memory && ["RAM", 41], c.temperature && ["°C", 52]].filter(Boolean);
      return `<div class="w box wv-bars">${(parts.length ? parts : [["CPU", 23]]).map(([n, v]) => `<div class="wv-row"><span>${n}</span>${c.curves ? `<svg viewBox="0 0 80 14" width="80" height="14"><path d="M0 12 10 9 20 10 30 6 40 8 50 3 60 6 70 4 80 7" fill="none" stroke="var(--c-accent)" stroke-width="1.4"/></svg>` : `<div class="wv-bar"><i style="width:${v}%"></i></div>`}</div>`).join("")}</div>`;
    }
    case "network": return `<div class="w box">${c.curves ? `<svg viewBox="0 0 110 34" width="110" height="34"><path d="M0 28 10 24 20 26 30 18 40 21 50 10 60 15 70 8 80 16 90 12 100 19 110 14" fill="none" stroke="var(--c-accent)" stroke-width="1.8" stroke-linejoin="round"/><path d="M0 31 15 30 30 28 45 30 60 26 75 29 90 27 110 29" fill="none" stroke="var(--c-green)" stroke-width="1.4" opacity=".8"/></svg>` : ""}<div class="wv-s mono" style="display:flex;gap:10px;margin-top:2px"><span>↓ 2.4 MB/s</span><span>↑ 180 kB/s</span></div></div>`;
    case "disk": return `<div class="w box"><div class="wv-row"><svg class="wv-ring" viewBox="0 0 44 44"><circle cx="22" cy="22" r="17" stroke="rgb(255 255 255 / .12)"/><circle cx="22" cy="22" r="17" stroke="var(--c-accent)" stroke-dasharray="${(c.show_free ? 0.38 : 0.62) * 107} 107" stroke-linecap="round" transform="rotate(-90 22 22)"/></svg><div><div style="font-weight:600;font-size:13px">${c.show_free ? "312 GB" : esc(pct(62))}</div><div class="wv-s">${esc(c.show_free ? t("free") : t("used"))}</div></div></div></div>`;
    case "nowplaying": return npPreview(c);
    case "lyrics": {
      const lines = [t("and the lights pass by"), t("we drive through the night"), t("until the morning comes"), t("and the city is asleep")];
      const n = Math.max(1, Math.min(4, c.lines || 3));
      const shown = n === 1 ? [1] : n === 2 ? [0, 1] : n === 3 ? [0, 1, 2] : [0, 1, 2, 3];
      const hl = (i) => i === 1 ? (c.highlight === "word" ? `<span style="font-weight:700;font-size:12px">${esc(lines[1]).replace(/^(\S+\s+\S+)/, '<span style="color:var(--c-accent)">$1</span>')}</span>` : `<span class="${c.highlight === "off" ? "" : "hl"}" style="${c.highlight === "off" ? "font-size:12px;font-weight:600" : ""}">${esc(lines[1])}</span>`) : `<span class="dim">${esc(lines[i])}</span>`;
      return `<div class="w"><div class="wv-lines">${shown.map(hl).join("")}</div></div>`;
    }
    case "visualizer": return visPreview(c);
    default: return "";
  }
}
export const wpBox = (w, big = false) => `<div class="wp${big ? " big" : ""}" aria-hidden="true">${wPreview(w)}</div>`;
export const thumb = (w, content) => `<div class="wp" style="height:100%;border:0">${wPreview({ ...w, content: { ...w.content, ...content } })}</div>`;
