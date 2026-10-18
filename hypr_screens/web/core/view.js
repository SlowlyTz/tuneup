/* Rendering: each page is a function returning an HTML string. Controls
 * register their handlers under a stable key (data-on / data-k); one set of
 * delegated listeners (shell/events.js) dispatches the DOM events to them.
 * After every change the page is rendered again and focus is restored by key.
 *
 * This module holds the handlers of the current render and the hooks that run
 * once its HTML is in the DOM; shell/render.js owns the render itself. */
import { esc } from "./dom.js";

let handlers = {};
let hooks = [];
let renderer = () => {};

/* Starts a render: no handlers but `base`, no hooks. */
export function beginRender(base = {}) {
  handlers = { ...base };
  hooks = [];
}
/* The hooks of the render just done (to run them once the HTML is in place). */
export const takeHooks = () => { const out = hooks; hooks = []; return out; };

export const handler = (key) => handlers[key];

/* The attributes that tie an element to the handler under `key`. */
export const k = (key) => `data-k="${esc(key)}" data-on="${esc(key)}"`;
/* Registers `spec` (click, pick, select, input, change, …) under `key`; returns k(key). */
export const reg = (key, spec) => { handlers[key] = spec; return k(key); };
/* Registers without the attributes (for controls that write them themselves). */
export const on = (key, spec) => { handlers[key] = spec; };

/* Runs `fn` after the page is in the DOM. */
export const afterRender = (fn) => { hooks.push(fn); };

export const setRenderer = (fn) => { renderer = fn; };
/* Renders the current page again (`enter`: as if it was just opened). */
export const render = (enter = false) => renderer(enter);
