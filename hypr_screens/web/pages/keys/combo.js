/* Key combinations as Hyprland writes them ("SUPER + SHIFT + M"): shown as
 * keycaps, and read from a keyboard event. */
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";

const COPILOT = "SUPER + SHIFT + F23";

const keyName = (part) => ({
  SUPER: "Super", SHIFT: "Shift", CTRL: t("Ctrl"), CONTROL: t("Ctrl"), ALT: "Alt", PERIOD: ".", COMMA: ",", SLASH: "/", MINUS: "-",
  RETURN: "Enter", SPACE: t("Space"), TAB: "Tab", LEFT: "←", RIGHT: "→", UP: "↑", DOWN: "↓", BACKSPACE: "⌫", DELETE: t("Del"), ESCAPE: "Esc",
})[part] || part;

const parts = (combo) => combo.split(/\s*\+\s*/);
const kbd = (names) => names.map((p) => `<kbd>${esc(p)}</kbd>`).join('<span class="plus">+</span>');

/* The keycaps of a combination (the Copilot key is one key). */
export const caps = (combo) => `<span class="keys">${combo === COPILOT ? kbd([t("Copilot key")]) : kbd(parts(combo).map(keyName))}</span>`;
/* Modifiers held so far, waiting for the key. */
export const heldCaps = (mods) => `<span class="keys">${kbd(mods.map(keyName))}<span class="plus">+ …</span></span>`;
export const comboText = (combo) => (combo === COPILOT ? t("Copilot key") : parts(combo).map(keyName).join(" + "));

const KEYS = {
  Period: "PERIOD", Comma: "COMMA", Slash: "SLASH", Minus: "MINUS", Space: "SPACE", Enter: "RETURN", Tab: "TAB",
  ArrowLeft: "LEFT", ArrowRight: "RIGHT", ArrowUp: "UP", ArrowDown: "DOWN", Delete: "DELETE", Backspace: "BACKSPACE",
  Home: "HOME", End: "END", PageUp: "PAGEUP", PageDown: "PAGEDOWN",
};

/* {mods, key, combo} of a key event; key and combo are null while only modifiers are held. */
export function comboFrom(e) {
  const mods = [];
  if (e.metaKey || e.getModifierState("OS") || e.getModifierState("Super") || e.getModifierState("Meta")) mods.push("SUPER");
  if (e.ctrlKey) mods.push("CTRL");
  if (e.altKey) mods.push("ALT");
  if (e.shiftKey) mods.push("SHIFT");
  const c = e.code;
  const key = /^Key[A-Z]$/.test(c) ? c.slice(3) : /^Digit\d$/.test(c) ? c.slice(5) : /^F\d{1,2}$/.test(c) ? c : KEYS[c] || null;
  return { mods, key, combo: key ? [...mods, key].join(" + ") : null };
}
