/* The one popover of the page (#popover) and the listbox shown in it. */
import { $, $$, eq, esc } from "../core/dom.js";
import { ic } from "./icons.js";
import { hideToast } from "./toast.js";

const pop = $("#popover");
const MARGIN = 8;

export const Pop = {
  anchor: null,
  onKey: null,
  get el() { return pop; },
  get isOpen() { return !pop.hidden; },

  open(anchor, html, { onKey, onClick, minWidth = true, keepFocus = false, label = "" } = {}) {
    this.close(false);
    hideToast();  // it would cover the lower part of the list
    this.anchor = anchor;
    this.onKey = onKey || null;
    pop.innerHTML = html;
    pop.onclick = onClick || null;
    if (label) pop.setAttribute("aria-label", label); else pop.removeAttribute("aria-label");
    pop.hidden = false;
    this.place(minWidth);
    if (anchor.hasAttribute("aria-expanded")) anchor.setAttribute("aria-expanded", "true");
    if (!keepFocus) { const f = $(".lb", pop) || $("input, button", pop); if (f) f.focus({ preventScroll: true }); }
  },

  /* Below the anchor, or above it when there is more room there; never
   * taller than the room (the list scrolls then). */
  place(minWidth = true) {
    if (!this.anchor) return;
    const r = this.anchor.getBoundingClientRect();
    pop.style.minWidth = minWidth ? `${Math.max(200, r.width)}px` : "";
    pop.style.left = "0px"; pop.style.top = "0px"; pop.style.maxHeight = "";
    const below = innerHeight - r.bottom - 4 - MARGIN, above = r.top - 4 - MARGIN;
    const natural = pop.getBoundingClientRect().height;
    const up = natural > below && above > below;
    pop.style.maxHeight = `${Math.min(innerHeight - 2 * MARGIN, Math.max(120, up ? above : below))}px`;
    const pr = pop.getBoundingClientRect();
    const top = up ? Math.max(MARGIN, r.top - pr.height - 4) : r.bottom + 4;
    let left = r.left;
    if (left + pr.width > innerWidth - MARGIN) left = Math.max(MARGIN, innerWidth - MARGIN - pr.width);
    pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  },

  close(refocus = true) {
    if (pop.hidden) return;
    pop.hidden = true;
    pop.innerHTML = "";
    const a = this.anchor;
    this.anchor = null; this.onKey = null;
    if (!a) return;
    if (a.hasAttribute("aria-expanded")) a.setAttribute("aria-expanded", "false");
    if (refocus && document.contains(a)) a.focus({ preventScroll: true });
  },
};

/* A listbox in the popover. options: [{v, label, sub, badge, icon, checked, sep, head, disabled}];
 * multi: several can be checked (onPick returns the new options to redraw);
 * keepFocus: the anchor's input keeps the focus (a combobox). */
export function openListbox(anchor, { options, value, onPick, multi = false, header = "", keepFocus = false, footer = "", onFooter }) {
  const usable = (i) => options[i] && !options[i].sep && !options[i].head && !options[i].disabled;
  let active = options.findIndex((o, i) => usable(i) && (multi ? o.checked : eq(o.v, value)));
  if (active < 0) active = options.findIndex((_, i) => usable(i));
  const label = header || anchor.getAttribute("aria-label") || "";

  const option = (o, i) => {
    if (o.sep) return '<div class="pop-sep" role="separator"></div>';
    if (o.head) return `<div class="pop-h" role="presentation">${esc(o.head)}</div>`;
    const sel = multi ? !!o.checked : eq(o.v, value);
    return `<div class="opt${i === active ? " active" : ""}" role="option" id="opt-${i}" data-i="${i}" aria-selected="${sel}"${o.disabled ? ' aria-disabled="true"' : ""}${multi ? ` aria-checked="${sel}"` : ""}>${multi ? `<span class="chk">${ic("check")}</span>` : ""}${o.icon || ""}<span class="opt-l">${esc(o.label)}${o.sub ? ` <span class="opt-sub">· ${esc(o.sub)}</span>` : ""}</span>${o.badge ? `<span class="pill">${esc(o.badge)}</span>` : ""}</div>`;
  };
  const html = () => `${header ? `<div class="pop-h">${esc(header)}</div>` : ""}<div class="lb" role="listbox" tabindex="-1" aria-label="${esc(label)}"${multi ? ' aria-multiselectable="true"' : ""} aria-activedescendant="opt-${active}">${options.map(option).join("")}</div>${footer}`;

  const scrollActive = () => { const a = $(`#opt-${active}`, pop); if (a) a.scrollIntoView({ block: "nearest" }); };
  const redraw = () => {
    const scroll = $(".lb", pop) ? $(".lb", pop).scrollTop : 0;
    pop.innerHTML = html();
    const lb = $(".lb", pop);
    lb.scrollTop = scroll;
    if (!keepFocus) lb.focus({ preventScroll: true });
    scrollActive();
  };
  const pick = (i) => {
    if (!usable(i)) return;
    if (!multi) { Pop.close(); onPick(options[i].v); return; }
    const next = onPick(options[i].v);
    if (next) { options = next; redraw(); }
  };
  const move = (step) => {
    let i = active;
    for (let n = 0; n < options.length; n++) { i = (i + step + options.length) % options.length; if (usable(i)) break; }
    active = i;
    $$(".opt", pop).forEach((el) => el.classList.toggle("active", +el.dataset.i === active));
    $(".lb", pop).setAttribute("aria-activedescendant", `opt-${active}`);
    if (keepFocus) anchor.querySelector("input")?.setAttribute("aria-activedescendant", `opt-${active}`);
    scrollActive();
  };
  let typed = "", typedTimer = 0;
  const typeAhead = (char) => {
    clearTimeout(typedTimer);
    typed += char.toLowerCase();
    typedTimer = setTimeout(() => (typed = ""), 600);
    const i = options.findIndex((o, j) => usable(j) && String(o.label).toLowerCase().startsWith(typed));
    if (i >= 0) { active = i - 1; move(1); }
  };

  Pop.open(anchor, html(), {
    keepFocus, label,
    onClick: (e) => {
      const o = e.target.closest(".opt");
      if (o) pick(+o.dataset.i);
      const f = e.target.closest("[data-pf]");
      if (f && onFooter) onFooter(f.dataset.pf);
    },
    onKey: (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Home" && !keepFocus) { e.preventDefault(); active = -1; move(1); }
      else if (e.key === "End" && !keepFocus) { e.preventDefault(); active = 0; move(-1); }
      else if (e.key === "Enter" || (e.key === " " && !keepFocus)) { e.preventDefault(); pick(active); }
      else if (e.key === "Tab") Pop.close(false);
      else if (!keepFocus && e.key.length === 1) typeAhead(e.key);
      else return false;
      return true;
    },
  });
  scrollActive();
}
