/* Texts: every text is written in English and goes through t(). The table of
 * the app's language (English → translation) comes with window.hyprBoot in the
 * app's window, or from api.translations() in a browser preview.
 *
 * tests/test_i18n.py finds every t() with a plain English text in these modules and checks
 * that it is translated; texts the backend sends go through t(variable). */
import { api, BOOT } from "./api.js";
import { esc } from "./dom.js";

let texts = (BOOT && BOOT.strings) || {};
let language = (BOOT && BOOT.language) || document.documentElement.lang || "en";

/* t(englishText, {name: value}) → the text in the app's language, placeholders filled. */
export function t(text, values) {
  let s = Object.prototype.hasOwnProperty.call(texts, text) && texts[text] ? texts[text] : text;
  if (values) s = s.replace(/\{(\w+)\}/g, (m, name) => (name in values ? String(values[name]) : m));
  return s;
}

/* A translated text with one placeholder replaced by ready HTML (the rest escaped). */
export const tHtml = (text, name, html, values) => esc(t(text, values)).split(`{${name}}`).join(html);

/* The app's language, for Intl formatting. */
export const loc = () => language || "en";

/* The texts came with the page (app window): a language change reloads it. */
export const bootTexts = () => !!(BOOT && BOOT.strings);

/* Without boot data: the table from the backend (English when that fails). */
export async function loadTranslations() {
  try {
    const table = await api.translations();
    texts = (table && table.texts) || {};
    language = (table && table.code) || language;
  } catch { /* English then */ }
}
