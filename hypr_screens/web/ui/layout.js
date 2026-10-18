/* The building blocks of a page: header, section, row, block, notice, expander.
 * Titles and descriptions are passed as ready (escaped) HTML. */
import { esc } from "../core/dom.js";
import { UI } from "../core/state.js";
import { k, on, render } from "../core/view.js";
import { ic } from "./icons.js";

const sidAttr = (sid) => (sid ? ` data-sid="${esc(sid)}"` : "");
const text = (title, desc, extra = "") =>
  `<div class="row-text"><div class="row-title"><span class="t">${title}</span>${extra}</div>${desc ? `<div class="row-desc">${desc}</div>` : ""}</div>`;

/* The page's title, its one-line intro and actions on the right. */
export const ph = (title, intro, actions = "") =>
  `<header class="ph"><div class="ph-text"><h1>${title}</h1>${intro ? `<p>${intro}</p>` : ""}</div>${actions ? `<div class="ph-actions">${actions}</div>` : ""}</header>`;

export const sec = (title, body, { sub = "", end = "" } = {}) =>
  `<section class="sec"><div class="sec-h"><h2>${title}</h2>${sub ? `<span class="sub">${sub}</span>` : ""}${end ? `<span class="end">${end}</span>` : ""}</div>${body}</section>`;

/* One setting: icon (or `lead`), title, description and its control at the end. */
export const row = ({ sid, icon, title, desc, end = "", cls = "", extra = "", lead = "" }) =>
  `<div class="row ${cls}"${sidAttr(sid)}>${lead || (icon ? ic(icon) : "")}${text(title, desc, extra)}${end ? `<div class="row-end">${end}</div>` : ""}</div>`;

/* A row with its control below it (choices that need the width). */
export const block = ({ sid, icon, title, desc, head = "", body = "", cls = "" }) =>
  `<div class="row block ${cls}"${sidAttr(sid)}><div class="row-head">${icon ? ic(icon) : ""}${text(title, desc)}${head ? `<div class="row-end">${head}</div>` : ""}</div>${body ? `<div class="body">${body}</div>` : ""}</div>`;

export const notice = (icon, html, cls = "") => `<div class="notice ${cls}">${ic(icon)}<p>${html}</p></div>`;

export const spinner = () => '<span class="spin" aria-hidden="true"></span>';

export const emptyState = (icon, title, more = "") =>
  `<div class="card empty-state">${icon === "spinner" ? spinner() : ic(icon)}<b>${title}</b>${more}</div>`;

/* A row that folds out `body`; stays open across renders (UI.open). */
export function expander(key, { icon, title, desc, sid }, body) {
  const open = !!UI.open[key];
  on(key, { click: () => { UI.open[key] = !open; render(); } });
  return `<div class="exp" data-open="${open}"${sidAttr(sid)}><div class="row" role="button" tabindex="0" aria-expanded="${open}" ${k(key)}>${ic(icon)}${text(title, desc)}${ic("chevD", "exp-chev")}</div>${open ? `<div class="exp-body">${body}</div>` : ""}</div>`;
}
