/* Controls. Each takes a stable `key` (its handler and focus survive renders)
 * and calls onChange with the new value; the page then renders again. */
import { eq, esc } from "../core/dom.js";
import { nf } from "../core/format.js";
import { t } from "../core/i18n.js";
import { k, on } from "../core/view.js";
import { appIcon, ic } from "./icons.js";
import { openListbox } from "./popover.js";

const disabledAttr = (off) => (off ? " disabled" : "");

/* unset: shows a default, not a value of its own (drawn dashed). */
export function toggle(key, value, onChange, { label = "", disabled = false, text = true, unset = false } = {}) {
  on(key, { click: () => onChange(!value) });
  return `<button type="button" class="sw${unset ? " unset" : ""}" role="switch" aria-checked="${!!value}" aria-label="${esc(label)}"${disabledAttr(disabled)} ${k(key)}>${text ? `<span class="sw-label">${value ? t("On") : t("Off")}</span>` : ""}<span class="sw-track"></span></button>`;
}

/* One choice of `opts` ({v, label, icon, title, aria, disabled}) – segmented by
 * default; `cls`/`itemCls`/`item` give the other looks. Roving tabindex. */
export function group(key, opts, value, onChange, { cls = "seg", itemCls = "seg-btn", label = "", item, unset = false, disabled = false, mark = undefined } = {}) {
  on(key, { pick: (i) => { if (!eq(opts[i].v, value)) onChange(opts[i].v); } });
  const picked = opts.findIndex((o) => eq(o.v, value));
  const inner = opts.map((o, i) => {
    const chosen = i === picked;
    const tab = (picked < 0 ? i === 0 : chosen) ? 0 : -1;
    const body = item ? item(o, chosen, i) : `${o.icon ? ic(o.icon, "sm") : ""}${esc(o.label)}`;
    const now = mark !== undefined && picked < 0 && eq(o.v, mark) ? " now" : "";
    return `<button type="button" class="${itemCls}${now}" role="radio" aria-checked="${chosen}" tabindex="${tab}"${disabledAttr(disabled || o.disabled)}${o.title ? ` title="${esc(o.title)}"` : ""}${o.aria ? ` aria-label="${esc(o.aria)}"` : ""} data-on="${esc(key)}" data-k="${esc(key)}:${i}" data-i="${i}">${body}</button>`;
  }).join("");
  return `<div class="${cls}${unset && picked < 0 ? " unset" : ""}" role="radiogroup" aria-label="${esc(label)}">${inner}</div>`;
}
export const seg = group;
export const chipsOne = (key, opts, value, onChange, o = {}) =>
  group(key, opts, value, onChange, { cls: "chips", itemCls: "chip", item: (x) => `${x.app ? appIcon(x.app) : x.icon ? ic(x.icon) : ""}${esc(x.label)}`, ...o });
export const radios = (key, opts, value, onChange, o = {}) =>
  group(key, opts, value, onChange, {
    cls: "card radios", itemCls: "radio",
    item: (x) => `<span class="dot"></span><span class="r-l">${esc(x.label)}${x.badge ? `<span class="pill">${esc(x.badge)}</span>` : ""}${x.sub ? `<span class="r-sub">${esc(x.sub)}</span>` : ""}</span>${x.ex ? `<span class="r-ex" data-ex="${esc(x.v)}">${esc(x.ex)}</span>` : ""}${x.end || ""}`, ...o,
  });
export const tcards = (key, opts, value, onChange, o = {}) =>
  group(key, opts, value, onChange, {
    cls: "tcards", itemCls: "tcard",
    item: (x) => `<div class="tcard-thumb">${x.thumb}</div><div class="tcard-body"><b>${esc(x.label)}${x.sub ? `<small>${esc(x.sub)}</small>` : ""}</b><span class="tick">${ic("check")}</span></div>`, ...o,
  });

/* Several of `opts`: each chip toggles on its own; onChange(value, on). */
export function chipsMulti(key, opts, values, onChange, { label = "", disabled = false } = {}) {
  on(key, { pick: (i) => onChange(opts[i].v, !values.includes(opts[i].v)) });
  return `<div class="chips" role="group" aria-label="${esc(label)}">${opts.map((o, i) =>
    `<button type="button" class="chip${o.square ? " square" : ""}" aria-pressed="${values.includes(o.v)}"${disabledAttr(disabled)}${o.title ? ` title="${esc(o.title)}"` : ""} data-on="${esc(key)}" data-k="${esc(key)}:${i}" data-i="${i}">${o.icon ? ic(o.icon) : ""}${esc(o.label)}</button>`).join("")}</div>`;
}

/* A range slider with its value; onInput while dragging, onChange when let go. */
export function slider(key, { min, max, step = 1, value, fmt = (v) => v, onInput, onChange, label = "", disabled = false }) {
  on(key, { input: (v) => onInput && onInput(v), change: (v) => onChange(v), fmt, min, max });
  const v = Math.min(max, Math.max(min, value ?? min));
  const p = ((v - min) / (max - min)) * 100;
  return `<div class="slider"><input type="range" min="${min}" max="${max}" step="${step}" value="${v}" style="--p:${p}%" aria-label="${esc(label)}" aria-valuetext="${esc(fmt(v))}"${disabledAttr(disabled)} ${k(key)}><span class="val num" data-val="${esc(key)}">${esc(fmt(v))}</span></div>`;
}

/* − value + for small whole-number ranges. */
export function stepper(key, { min, max, step = 1, value, fmt = (v) => nf(v), onChange, label = "", disabled = false }) {
  const set = (v) => { const n = Math.min(max, Math.max(min, v)); if (n !== value) onChange(n); };
  const keys = { ArrowUp: step, ArrowRight: step, ArrowDown: -step, ArrowLeft: -step, PageUp: step * 5, PageDown: -step * 5 };
  on(`${key}-dn`, { click: () => set(value - step) });
  on(`${key}-up`, { click: () => set(value + step) });
  on(key, { stepKey: (e) => {
    const target = e.key in keys ? value + keys[e.key] : e.key === "Home" ? min : e.key === "End" ? max : null;
    if (target == null) return false;
    e.preventDefault();
    set(target);
    return true;
  } });
  return `<div class="stepper">
      <button type="button" class="btn icon" tabindex="-1" aria-hidden="true"${disabledAttr(disabled || value <= min)} ${k(`${key}-dn`)}>${ic("minus", "sm")}</button>
      <span class="stepper-v num" role="spinbutton" tabindex="${disabled ? -1 : 0}" aria-label="${esc(label)}" aria-valuemin="${min}" aria-valuemax="${max}" aria-valuenow="${value}" aria-valuetext="${esc(fmt(value))}"${disabled ? ' aria-disabled="true"' : ""} ${k(key)}>${esc(fmt(value))}</span>
      <button type="button" class="btn icon" tabindex="-1" aria-hidden="true"${disabledAttr(disabled || value >= max)} ${k(`${key}-up`)}>${ic("plus", "sm")}</button>
    </div>`;
}

/* A text field, saved on Enter or when it loses focus; onInput while typing. */
export function textField(key, { value, onChange, onInput, label = "", placeholder = "", icon = "lyrics", maxLength, disabled = false, width = 300, mono = false }) {
  on(key, { text: (v) => { if (v !== value) onChange(v); }, typing: onInput });
  return `<label class="field${mono ? " mono" : ""}" style="max-width:${width}px;width:100%">${ic(icon)}<input type="text" value="${esc(value)}" aria-label="${esc(label)}" placeholder="${esc(placeholder)}" spellcheck="false" autocomplete="off"${maxLength ? ` maxlength="${maxLength}"` : ""}${disabledAttr(disabled)} ${k(key)}></label>`;
}

/* A button that opens a listbox of `options` ({v, label, sub, badge, icon}). */
export function select(key, { options, value, placeholder, onChange, label = "", width, disabled = false }) {
  const current = options.find((o) => eq(o.v, value));
  on(key, { select: (el) => openListbox(el, { options, value, onPick: (v) => { if (!eq(v, value)) onChange(v); } }) });
  const shown = current
    ? `${current.icon || ""}<span class="sel-v">${esc(current.label)}</span>${current.badge ? `<span class="pill">${esc(current.badge)}</span>` : ""}`
    : `<span class="sel-v ph">${esc(placeholder ?? t("Choose"))}</span>`;
  return `<button type="button" class="select" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(label)}"${disabledAttr(disabled)}${width ? ` style="min-width:${width}px"` : ""} ${k(key)}>${shown}${ic("chevD")}</button>`;
}

export function button(key, inner, onClick, { cls = "btn", attrs = "", label = "" } = {}) {
  on(key, { click: onClick });
  return `<button type="button" class="${cls}"${label ? ` aria-label="${esc(label)}" title="${esc(label)}"` : ""} ${attrs} ${k(key)}>${inner}</button>`;
}
