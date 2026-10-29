/* Keyboard: the minimizer's keys (two slots per action) and the desktop keys. */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S, UI } from "../../core/state.js";
import { reg } from "../../core/view.js";
import { stepper, toggle } from "../../ui/controls.js";
import { ic } from "../../ui/icons.js";
import { expander, ph, row, sec } from "../../ui/layout.js";
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
      ${sec(esc(t("Desktops")), `<div class="stack">${desktops}${scratchCard(S.keys.options)}</div>`)}`;
}

/* Scratch desktops: on/off in the header, the details folded inside. */
function scratchCard(o) {
  if (o.scratch === undefined) return "";
  const set = (name, value, before) =>
    change(() => api.setOption(name, value), () => api.setOption(name, before), { reload: ["keys"] });
  const keys = [
    ["Super + S", t("Opens the scratch desktops, and closes them again")],
    ["Super + 1…0", t("In the row: scratch desktop 1 to 10")],
    ["Super + Shift + 1…0", t("In the row: moves the active window there")],
    ["Super + Alt + S", t("Moves the active window to the last scratch desktop")],
    ["Super + Ctrl + S", t("Moves the active window in, or out onto your desktop")],
  ].map(([combo, what]) => `<div class="kv"><span class="mono">${esc(combo)}</span><span>${esc(what)}</span></div>`).join("");
  const body = `<div class="stack">
      ${row({ sid: "keys.scratch.kept", title: esc(t("Always there")),
              desc: esc(t("Scratch desktops that stay while the row is open, even when empty; further ones go when they are empty")),
              end: stepper("scratch-kept", { min: 1, max: 10, value: o.scratch_kept, disabled: !o.scratch,
                                             label: t("Scratch desktops that are always there"),
                                             onChange: (v) => set("scratch_kept", v, o.scratch_kept) }) })}
      ${row({ sid: "keys.scratch.shifts", title: esc(t("Super + Shift + S too")),
              desc: esc(t("Also moves the active window to the last scratch desktop (off: the key keeps its own use)")),
              end: toggle("scratch-shift-s", o.scratch_shift_s, (v) => set("scratch_shift_s", v, !v),
                          { label: t("Super + Shift + S too"), disabled: !o.scratch }) })}
      ${row({ sid: "keys.scratch.swipe", title: esc(t("Swipe with three fingers")),
              desc: esc(t("Up on the touchpad opens the scratch desktops, down closes them")),
              end: toggle("scratch-swipe", o.scratch_swipe, (v) => set("scratch_swipe", v, !v),
                          { label: t("Swipe with three fingers"), disabled: !o.scratch }) })}
      ${row({ title: esc(t("Keys")), desc: `<div class="kvs">${keys}</div>` })}
    </div>`;
  return expander("exp-scratch", {
    sid: "keys.scratch", icon: "desktops", title: esc(t("Scratch desktops")),
    desc: esc(t("Super + S brings a row of extra desktops in from below, in place of Omarchy's scratchpad")),
    end: toggle("scratch-on", o.scratch, (v) => set("scratch", v, !v), { label: t("Scratch desktops") }),
  }, body);
}
