/* Small DOM and value helpers used everywhere. */

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
/* Text made safe for HTML (also for attribute values). */
export const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);

export const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
export const clone = (value) => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

/* A no-break space: between a number and its unit. */
export const NB = " ";

/* Lower case without accents, for searching: "Größe" finds "grosse". */
export const norm = (text) => String(text).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ß/g, "ss");

export const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
