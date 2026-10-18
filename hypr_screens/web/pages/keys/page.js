/* Keyboard: the minimizer's keys (two slots per action) and the desktop keys. */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S, UI } from "../../core/state.js";
import { reg } from "../../core/view.js";
import { toggle } from "../../ui/controls.js";
import { ic } from "../../ui/icons.js";
import { ph, row, sec } from "../../ui/layout.js";
import { captureDialog } from "./capture.js";
import { caps, comboText } from "./combo.js";

const KEY_ICON = { stash: "minimize", stash_others: "minOthers", pop: "restore", pop_all: "restoreAll", undo: "undo", minimizer_menu: "list" };

/* Slot i of action a: its keys, "set a key" / "second key", or an empty place (columns stay aligned). */
function slot(a, i, title) {
  const combo = a.slots[i];
  const saved = UI.savedSlot === `${a.id}:${i}` ? " saved" : "";
  const attrs = reg(`slot-${a.id}-${i}`, { click: () => captureDialog(a.id, i) });
  if (combo) return `<button type="button" class="keyslot${saved}" aria-label="${esc(t("{action}, key {n}: {keys}. Change", { action: title, n: i + 1, keys: comboText(combo) }))}" ${attrs}>${caps(combo)}${saved ? `<span class="saved-mark">${ic("check", "xs")}</span>` : ""}</button>`;
  if (i === 1 && !a.slots[0]) return '<span class="keyslot spacer" aria-hidden="true"></span>';
  return `<button type="button" class="keyslot empty" aria-label="${esc(i ? t("{action}: add a second key", { action: title }) : t("{action}: set a key", { action: title }))}" ${attrs}>${ic("plus")}${esc(i ? t("Second key") : t("Set a key"))}</button>`;
}

export function pageKeys() {
  const actions = S.keys.actions.map((a) => {
    const title = t(a.title);
    return row({ sid: `keys.${a.id}`, icon: KEY_ICON[a.id] || "keyboard", title: esc(title), desc: esc(t(a.desc || "")), end: `<div class="slots">${slot(a, 0, title)}${slot(a, 1, title)}</div>` });
  }).join("");
  const on = S.keys.options.desktop_keys;
  const desktops = row({
    sid: "keys.desktop", icon: "desktops", title: esc(t("Desktop keys")),
    desc: esc(t("Super + 1…0 and Super + Tab only switch the desktops 1–10 on the other screen")),
    end: toggle("dk", on, (v) => change(() => api.setOption("desktop_keys", v), () => api.setOption("desktop_keys", !v), { reload: ["keys"] }), { label: t("Desktop keys") }),
  });
  return `${ph(esc(t("Keyboard")), esc(t("Click a key to change it. Every action has two places.")))}
      ${sec(esc(t("Minimize windows")), `<div class="stack">${actions}</div>`)}
      ${sec(esc(t("Desktops")), `<div class="stack">${desktops}</div>`)}`;
}
