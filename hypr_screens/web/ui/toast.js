/* The toast at the bottom: a message, with "Undo" or one other action. */
import { $, esc } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { ic } from "./icons.js";

const el = $("#toast");
let timer = 0;

export const hideToast = () => el.classList.remove("show");

/* undo: async function run by "Undo"; action: {label, run}. */
export function toast(message, undo = null, { error = false, action = null } = {}) {
  const act = undo ? `${ic("undo", "sm")}${esc(t("Undo"))}` : action ? esc(action.label) : "";
  el.innerHTML = `${ic(error ? "alert" : "check", error ? "err" : "ok")}<span>${esc(message)}</span>${act ? `<span class="sep"></span><button type="button" class="btn ghost" id="toast-act">${act}</button>` : ""}`;
  el.classList.toggle("error", error);
  el.setAttribute("role", error ? "alert" : "status");
  el.classList.add("show");
  clearTimeout(timer);
  timer = setTimeout(hideToast, act ? 6000 : error ? 5000 : 3000);
  const b = $("#toast-act");
  if (b) b.onclick = async () => {
    hideToast();
    if (undo) { await undo(); toast(t("Undone")); } else action.run();
  };
}
