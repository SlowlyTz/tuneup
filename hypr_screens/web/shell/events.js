/* One set of delegated DOM listeners for the whole app: they hand the events
 * to the handlers the current render registered (core/view.js), and add the
 * keyboard behaviour of radio groups, tabs and the popover. */
import { $$ } from "../core/dom.js";
import { UI } from "../core/state.js";
import { handler } from "../core/view.js";
import { dialog } from "../ui/dialog.js";
import { Pop } from "../ui/popover.js";
import { focusSearch, searchFocused } from "./search.js";

const handlerOf = (el) => el && el.dataset && handler(el.dataset.on);
const ARROWS = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 };

function onClick(e) {
  const el = e.target.closest("[data-on]");
  if (!el || el.disabled || el.closest("#dialog")) return;
  const h = handlerOf(el);
  if (!h) return;
  if (h.pick && el.dataset.i != null) h.pick(+el.dataset.i);
  else if (h.select) { if (Pop.isOpen && Pop.anchor === el) Pop.close(); else h.select(el); }
  else if (h.click) h.click(e, el);
}

function onInput(e) {
  const el = e.target;
  const h = handlerOf(el);
  if (!h) return;
  if (el.type === "range") {
    const v = Number(el.value);
    el.style.setProperty("--p", `${((v - h.min) / (h.max - h.min)) * 100}%`);
    const shown = el.parentElement.querySelector(`[data-val="${CSS.escape(el.dataset.on)}"]`);
    if (shown) shown.textContent = h.fmt(v);
    el.setAttribute("aria-valuetext", h.fmt(v));
    if (h.input) h.input(v);
  } else if (el.type === "color" && h.color) {
    el.parentElement.querySelector("i").style.background = el.value;
    h.color(el.value);
  } else if (h.combo) h.combo(el);
  else if (h.typing) h.typing(el.value);
}

function onChange(e) {
  const el = e.target;
  const h = handlerOf(el);
  if (!h) return;
  if (el.type === "range") h.change(Number(el.value));
  else if (el.type === "color" && h.colorDone) h.colorDone(el.value);
  else if (h.text) h.text(el.value);
}

/* Arrow keys move through a radio group (and pick), Home/End to its ends. */
function radioKey(e, el) {
  if (!(e.key in ARROWS) && e.key !== "Home" && e.key !== "End") return false;
  const items = $$('[role="radio"]:not(:disabled)', el.closest('[role="radiogroup"]'));
  let i = items.indexOf(el);
  i = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (i + ARROWS[e.key] + items.length) % items.length;
  e.preventDefault();
  items[i].focus();
  items[i].click();
  return true;
}

function tabKey(e, el) {
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return false;
  const tabs = $$('[role="tab"]', el.parentElement);
  const next = tabs[(tabs.indexOf(el) + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
  e.preventDefault(); next.focus(); next.click();
  return true;
}

function onKey(e) {
  if (dialog.open) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") { e.preventDefault(); Pop.close(false); focusSearch(); return; }
  if (Pop.isOpen) {
    if (e.key === "Escape") { e.preventDefault(); Pop.close(); return; }
    const inside = Pop.el.contains(e.target) || (Pop.anchor && Pop.anchor.contains(e.target));
    if (Pop.onKey && inside && Pop.onKey(e)) return;
  }
  const el = e.target;
  const h = handlerOf(el);
  if (h && h.combo && e.key === "ArrowDown" && !Pop.isOpen) { e.preventDefault(); h.combo(el); return; }
  if (h && h.select && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); h.select(el); return; }
  if (h && h.stepKey && el.getAttribute("aria-disabled") !== "true" && h.stepKey(e)) return;
  const role = el.getAttribute && el.getAttribute("role");
  if (role === "radio" && radioKey(e, el)) return;
  if (role === "tab" && tabKey(e, el)) return;
  if (role === "button" && el.tagName !== "BUTTON" && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); el.click(); return; }
  if (e.key === "Escape" && searchFocused()) el.blur();
}

export function bindEvents({ onResize }) {
  document.addEventListener("click", onClick);
  document.addEventListener("input", onInput);
  document.addEventListener("change", onChange);
  document.addEventListener("focusin", (e) => {
    const h = handlerOf(e.target);
    if (h && h.combo && !e.target.value) h.combo(e.target);
  });
  document.addEventListener("keydown", onKey);
  document.addEventListener("pointerdown", (e) => {
    UI.pressed = true;
    if (Pop.isOpen && !Pop.el.contains(e.target) && !(Pop.anchor && Pop.anchor.contains(e.target))) Pop.close(false);
  });
  const released = () => { UI.pressed = false; };
  document.addEventListener("pointerup", released);
  document.addEventListener("pointercancel", released);
  document.querySelector("#main").addEventListener("scroll", () => { if (Pop.isOpen) Pop.place(false); }, { passive: true });
  addEventListener("resize", () => { Pop.close(false); onResize(); });
}
