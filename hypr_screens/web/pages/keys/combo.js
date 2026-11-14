/* Key combinations as Hyprland writes them ("SUPER + SHIFT + M"): shown as
 * keycaps, and read from a keyboard event. */
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";

const COPILOT = "SUPER + SHIFT + F23";

const keyName = (part) => ({
  SUPER: "Super", SHIFT: "Shift", CTRL: t("Ctrl"), CONTROL: t("Ctrl"), ALT: "Alt", PERIOD: ".", COMMA: ",", SLASH: "/", MINUS: "-",
  RETURN: "Enter", SPACE: t("Space"), TAB: "Tab", LEFT: "←", RIGHT: "→", UP: "↑", DOWN: "↓", BACKSPACE: "⌫", DELETE: t("Del"), ESCAPE: "Esc",
  PRIOR: "PgUp", NEXT: "PgDn", PAGEUP: "PgUp", PAGEDOWN: "PgDn", EQUAL: "=", SEMICOLON: ";", APOSTROPHE: "'", GRAVE: "`",
  BRACKETLEFT: "[", BRACKETRIGHT: "]", BACKSLASH: "\\", KP_ENTER: "Num Enter", KP_ADD: "Num +", KP_SUBTRACT: "Num -",
  KP_MULTIPLY: "Num *", KP_DIVIDE: "Num /", KP_DECIMAL: "Num .", SCROLL_LOCK: "Scroll", MENU: "Menu",
})[part] || (/^KP_\d$/.test(part) ? `Num ${part.slice(3)}` : part) || part;

const parts = (combo) => combo.split(/\s*\+\s*/);
const kbd = (names) => names.map((p) => `<kbd>${esc(p)}</kbd>`).join('<span class="plus">+</span>');

/* The keycaps of a combination (the Copilot key is one key). */
export const caps = (combo) => `<span class="keys">${combo === COPILOT ? kbd([t("Copilot key")]) : kbd(parts(combo).map(keyName))}</span>`;
/* Modifiers held so far, waiting for the key. */
export const heldCaps = (mods) => `<span class="keys">${kbd(mods.map(keyName))}<span class="plus">+ …</span></span>`;
export const comboText = (combo) => (combo === COPILOT ? t("Copilot key") : parts(combo).map(keyName).join(" + "));

/* KeyboardEvent.code → the key's xkb name, which is what Hyprland takes ("Prior", not "PageUp"). */
const KEYS = {
  Period: "PERIOD", Comma: "COMMA", Slash: "SLASH", Minus: "MINUS", Space: "SPACE", Enter: "RETURN", Tab: "TAB",
  ArrowLeft: "LEFT", ArrowRight: "RIGHT", ArrowUp: "UP", ArrowDown: "DOWN", Delete: "DELETE", Backspace: "BACKSPACE",
  Home: "HOME", End: "END", PageUp: "PRIOR", PageDown: "NEXT", Insert: "INSERT", Print: "PRINT", Pause: "PAUSE",
  ScrollLock: "SCROLL_LOCK", ContextMenu: "MENU", Equal: "EQUAL", Semicolon: "SEMICOLON", Quote: "APOSTROPHE",
  Backquote: "GRAVE", BracketLeft: "BRACKETLEFT", BracketRight: "BRACKETRIGHT", Backslash: "BACKSLASH",
  IntlBackslash: "code:94",
  NumpadEnter: "KP_ENTER", NumpadAdd: "KP_ADD", NumpadSubtract: "KP_SUBTRACT", NumpadMultiply: "KP_MULTIPLY",
  NumpadDivide: "KP_DIVIDE", NumpadDecimal: "KP_DECIMAL",
};
const keyFrom = (c) => /^Key[A-Z]$/.test(c) ? c.slice(3) : /^Digit\d$/.test(c) ? c.slice(5) : /^F\d{1,2}$/.test(c) ? c
  : /^Numpad\d$/.test(c) ? `KP_${c.slice(6)}` : KEYS[c] || null;

/* Keys that may stand alone; any other would stop working in every app (Hyprland binds it globally). */
const BARE = /^(F\d{1,2}|XF86\w+|PRINT|PAUSE)$/i;
export const needsModifier = (combo) => { const p = parts(combo); return p.length === 1 && !BARE.test(p[0]); };

/* WebKitGTK reports the Super key itself (key "Super", code "OSLeft") but sets
 * neither metaKey nor a modifier state while it is held, so it is tracked here. */
let superHeld = false;
const isSuper = (e) => ["Super", "Meta", "OS"].includes(e.key) || /^(OS|Meta)(Left|Right)$/.test(e.code);
for (const type of ["keydown", "keyup"]) window.addEventListener(type, (e) => { if (isSuper(e)) superHeld = type === "keydown"; }, true);
/* A keyup that never came (focus lost, window hidden) must not leave Super "held". */
export const resetSuper = () => { superHeld = false; };
for (const type of ["blur", "focus"]) window.addEventListener(type, resetSuper);
document.addEventListener("visibilitychange", resetSuper);

/* A modifier key itself (the combination then waits for its key). */
export const isModifierKey = (e) => isSuper(e) || /^(Shift|Control|Alt)(Left|Right)$|^AltGraph$|^CapsLock$|^NumLock$/.test(e.code || e.key);

/* {mods, key, combo} of a key event; key and combo are null while only modifiers are held. */
export function comboFrom(e) {
  const mods = [];
  if (superHeld || e.metaKey || e.getModifierState("OS") || e.getModifierState("Super") || e.getModifierState("Meta")) mods.push("SUPER");
  if (e.ctrlKey) mods.push("CTRL");
  if (e.altKey) mods.push("ALT");
  if (e.shiftKey) mods.push("SHIFT");
  const key = keyFrom(e.code);
  return { mods, key, combo: key ? [...mods, key].join(" + ") : null };
}
