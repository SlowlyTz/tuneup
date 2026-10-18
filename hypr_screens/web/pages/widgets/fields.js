/* A widget's settings, rendered from its schema (api.widgets()[].schema):
 * each field becomes a row or block with the control its type asks for. */
import { $, eq, esc, NB } from "../../core/dom.js";
import { nf, pct } from "../../core/format.js";
import { t } from "../../core/i18n.js";
import { block, row, sec } from "../../ui/layout.js";
import { chipsMulti, chipsOne, radios, seg, select, slider, stepper, tcards, textField, toggle } from "../../ui/controls.js";
import { setField, valueOf } from "./model.js";
import { fmtDate, thumb } from "./previews.js";
import { tzField } from "./timezones.js";

const FIELD_ICON = {
  player: "music", bars: "wave", style: "wave", sensitivity: "gauge", smoothing: "sliders", peaks: "sparkle",
  highlight: "lyrics", lines: "lyrics", hide_paused: "eye", clock_style: "clock", hours: "clock", seconds: "clock",
  date: "calendar", weekday: "calendar", date_format: "calendar", date_pattern: "lyrics", zone2: "globe",
  cpu: "cpu", memory: "cpu", temperature: "temp", curves: "hz", units: "temp", show_place: "globe", show_details: "info",
  show_forecast: "calendar", week_start: "calendar", show_month: "calendar", show_weeks: "lyrics", show_percent: "battery",
  show_remaining: "clock", low: "alert", show_free: "disk", np_layout: "widgets", hide_idle: "eye",
  screens: "monitor", desktops: "desktops", same_place: "arrange", only_empty: "desktops", hide_on_battery: "battery",
  above: "window", where: "widgets",
};
/* Choices shown as cards with a preview of the widget in that style. */
const CARD_FIELDS = {
  "clock.clock_style": (w, v) => thumb(w, { clock_style: v, zone2: "" }),
  "visualizer.style": (w, v) => thumb(w, { style: v }),
  "nowplaying.np_layout": (w, v) => thumb(w, { np_layout: v }),
};
const SCREEN_ICON = { laptop: "laptop", external: "monitor", all: "desktops" };
/* "Same place on every screen" only means something on more than one screen. */
const MANY_SCREENS = ["all", "external"];

const shownField = (w, f) => {
  if (f.key === "same_place" && f.group === "where") return MANY_SCREENS.includes(w.where.screens);
  return !f.showIf || Object.entries(f.showIf).every(([key, v]) => valueOf(w, key) === v);
};

const unitFmt = (unit) => (unit === "%" ? (x) => pct(x) : unit ? (x) => `${nf(x)}${NB}${unit}` : (x) => nf(x));
/* Short choices fit a segmented control; longer ones get a select. */
const fitsSegments = (opts) => opts.length <= 5 && opts.every((o) => o.label.length <= 16) && opts.reduce((n, o) => n + o.label.length, 0) <= 46;

function dateFormatField(w, f, ctx) {
  const now = new Date();
  const opts = f.choices.map((c) => {
    const full = t(c.label);
    const name = full.replace(/\s*\(.*\)\s*$/, "") || full;
    const example = c.value === "custom" ? (ctx.val === "custom" ? fmtDate("custom", now, w.content.date_pattern) : "") : fmtDate(c.value, now);
    return { v: c.value, label: name, ex: example };
  });
  return block({ ...ctx.head, body: radios(ctx.key, opts, ctx.val, ctx.set, { label: t(f.label), disabled: ctx.off }) });
}

function desktopsField(w, f, ctx) {
  const all = ctx.val.includes("all");
  const opts = [...f.choices.map((c) => (c.value === "fixed" ? { v: c.value, label: t(c.label), icon: "pin" } : { v: c.value, label: t(c.label), square: /^\d+$/.test(c.value) })), { v: "all", label: t("All") }];
  const pick = (v, on) => {
    let picked = ctx.val.filter((x) => x !== "all");
    if (v === "all") picked = ["all"];
    else picked = on ? [...picked, v] : picked.filter((x) => x !== v);
    ctx.set(picked.length ? picked : ["all"]);
  };
  return block({ ...ctx.head, sid: "w.where.desktops", desc: esc(t("On which desktops the widget shows")), body: chipsMulti(ctx.key, opts, all ? ["all"] : ctx.val, pick, { label: t(f.label), disabled: ctx.off }) });
}

function textFieldOf(w, f, ctx) {
  const pattern = f.key === "date_pattern";
  const showExample = (v) => { const ex = $('[data-ex="custom"]'); if (ex) ex.textContent = fmtDate("custom", new Date(), v); };
  const body = `${textField(ctx.key, { value: ctx.val || "", label: t(f.label), maxLength: f.maxLength, disabled: ctx.off, mono: pattern, onChange: ctx.set, onInput: pattern ? showExample : null })}${pattern ? `<div class="row-desc" style="margin-top:6px">${esc(t("d = day · dddd = weekday · MMMM = month · yyyy = year · 'text' as it is"))}</div>` : ""}`;
  return block({ ...ctx.head, body });
}

/* One field: {html} for a row or block, {section} for card fields that stand on their own. */
function fieldHtml(w, f) {
  const key = `f-${w.kind}-${f.key}`;
  const val = valueOf(w, f.key);
  const off = f.enabledBy && !valueOf(w, f.enabledBy);
  const label = t(f.label);
  const head = {
    sid: `w.${w.kind}.${f.key}`, title: esc(label), desc: f.hint ? esc(t(f.hint)) : "", cls: off ? "dim" : "",
    // In a titled section the heading says what the rows are about: no icon each.
    icon: f.section ? "" : FIELD_ICON[f.key] || "sliders",
  };
  const set = (v) => setField(w, f, v);
  const ctx = { key, val, off, set, head };
  const card = CARD_FIELDS[`${w.kind}.${f.key}`];
  if (card) {
    const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label), thumb: card(w, c.value) }));
    return { section: sec(esc(label), `<div data-sid="${esc(head.sid)}">${tcards(key, opts, val, set, { label, cls: `tcards n${opts.length}` })}</div>`) };
  }
  if (f.key === "date_format") return { html: dateFormatField(w, f, ctx) };
  if (f.key === "zone2") return { html: row({ ...head, desc: head.desc || esc(t("Shows a second time below")), end: tzField(w.content.zone2, set, off) }) };
  if (f.key === "player") {
    const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label), ...(c.value ? { app: c.value } : { icon: "speaker" }) }));
    if (val != null && !opts.some((o) => o.v === val)) opts.push({ v: val, label: val, app: val });
    return { html: block({ ...head, body: chipsOne(key, opts, val, set, { label, disabled: off }) }) };
  }
  if (f.key === "screens" && f.group === "where") {
    const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label), icon: SCREEN_ICON[c.value] || "monitor" }));
    return { html: block({ ...head, sid: "w.where.screens", body: chipsOne(key, opts, val, set, { label, disabled: off }) }) };
  }
  if (f.key === "desktops" && f.type === "multi") return { html: desktopsField(w, f, ctx) };
  switch (f.type) {
    case "toggle":
      return { html: row({ ...head, end: toggle(key, !!val, set, { label, disabled: off }) }) };
    case "choice": {
      const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label) }));
      const ctl = fitsSegments(opts) ? seg(key, opts, val, set, { label, disabled: off })
        : select(key, { options: opts, value: val, onChange: set, label, width: 220, disabled: off });
      return { html: row({ ...head, end: ctl }) };
    }
    case "number": {
      const fmt = unitFmt(f.unit);
      const spec = { min: f.min, max: f.max, step: f.step || 1, value: val, fmt, onChange: set, label, disabled: off };
      const few = (f.max - f.min) / (f.step || 1) <= 10 && !f.unit;
      return { html: row({ ...head, end: few ? stepper(key, spec) : slider(key, spec) }) };
    }
    case "text":
      return { html: textFieldOf(w, f, ctx) };
    case "multi": {
      const opts = (f.choices || []).map((c) => ({ v: c.value, label: t(c.label) }));
      return { html: block({ ...head, body: chipsMulti(key, opts, val || [], (v, on) => set(on ? [...val, v] : val.filter((x) => x !== v)), { label, disabled: off }) }) };
    }
    default:
      return { html: "" };
  }
}

/* All fields of one group in schema order: loose ones in a stack, `section`
 * ones under their heading, card fields as their own section. */
export function renderFields(w, groupName) {
  const out = [];
  let stack = [], title = null;
  const flush = () => {
    if (!stack.length) return;
    const body = `<div class="stack">${stack.join("")}</div>`;
    out.push(title ? sec(esc(t(title)), body) : `<div class="sec">${body}</div>`);
    stack = []; title = null;
  };
  for (const f of w.schema.filter((x) => x.group === groupName && shownField(w, x))) {
    const r = fieldHtml(w, f);
    if (r.section) { flush(); out.push(r.section); continue; }
    if ((f.section || null) !== title) flush();
    title = f.section || null;
    stack.push(r.html);
  }
  flush();
  return out.join("");
}
