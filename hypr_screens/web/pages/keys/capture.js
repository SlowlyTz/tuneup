/* The dialog that records a new key combination for one slot of an action.
 * Hyprland gets an empty keymap while it records (so Super+Q reaches us). */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { $, clone, esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S, UI } from "../../core/state.js";
import { render } from "../../core/view.js";
import { closeDialog, dialog, onDialogClose, openDialog } from "../../ui/dialog.js";
import { ic } from "../../ui/icons.js";
import { notice } from "../../ui/layout.js";
import { caps, comboFrom, comboText, heldCaps } from "./combo.js";

const SAVED_MS = 1400;

/* Marks the slot as just saved for a moment. */
function flashSaved(action, slot) {
  UI.savedSlot = `${action}:${slot}`;
  setTimeout(() => { if (UI.savedSlot === `${action}:${slot}`) { UI.savedSlot = null; render(); } }, SAVED_MS);
}

export function captureDialog(action, slot) {
  const a = S.keys.actions.find((x) => x.id === action);
  const old = a.slots[slot];
  let combo = null, held = [];
  api.beginKeyCapture().catch(() => {});

  const conflict = () => {
    if (!combo) return "";
    const other = S.keys.actions.find((x) => x.id !== action && x.slots.includes(combo)) || (a.slots[1 - slot] === combo ? a : null);
    if (other) return notice("alert", `${esc(t("Already used by “{action}”.", { action: t(other.title) }))}<small>${esc(t("Taking it over removes it there."))}</small>`, "warn");
    const hypr = S.keys.hyprBinds[combo];
    if (hypr) return notice("alert", `${esc(t("Hyprland uses it for “{action}”.", { action: t(hypr) }))}<small>${esc(t("Taking it over replaces that while hypr-screens runs."))}</small>`, "warn");
    return "";
  };
  const shown = () => combo ? caps(combo)
    : held.length ? heldCaps(held)
    : `<span class="wait"><span class="blink"></span>${esc(t("Waiting for keys …"))}</span>`;
  const draw = () => {
    const cap = $("#cap", dialog);
    cap.innerHTML = shown();
    cap.classList.toggle("live", !!(combo || held.length));
    $("#cap-conf", dialog).innerHTML = conflict();
    $('[data-d="ok"]', dialog).disabled = !combo || combo === old;
  };
  const apply = async () => {
    const before = clone(S.keys.actions);
    const chosen = combo;
    closeDialog();
    const done = await change(() => api.setKey(action, slot, chosen), async () => {
      for (const b of before) for (let i = 0; i < b.slots.length; i++) await api.setKey(b.id, i, b.slots[i]);
    }, { reload: ["keys"], msg: (r) => (r && r.conflicts && r.conflicts.length ? t("Saved · replaces Hyprland’s {keys} while hypr-screens runs", { keys: r.conflicts.map(comboText).join(", ") }) : t("Saved")) });
    if (done) { flashSaved(action, slot); render(); }
  };
  const remove = async () => {
    closeDialog();
    await change(() => api.setKey(action, slot, ""), () => api.setKey(action, slot, old), { reload: ["keys"], msg: t("Key removed") });
  };

  openDialog(`
      <div class="dlg-body">
        <h2>${esc(t(a.title))}</h2>
        <p>${esc(old ? t("Press the new key combination … Esc cancels, Backspace removes it.") : t("Press the new key combination … Esc cancels."))}</p>
        <div class="capture" id="cap" tabindex="0" aria-live="polite" aria-label="${esc(t("Record a key combination"))}">${shown()}</div>
        <div id="cap-conf"></div>
      </div>
      <div class="dlg-foot">
        ${old ? `<button type="button" class="btn danger" data-d="remove">${ic("trash", "sm")}${esc(t("Remove"))}</button><span class="spacer"></span>` : ""}
        <button type="button" class="btn" data-d="cancel">${esc(t("Cancel"))}</button>
        <button type="button" class="btn primary" data-d="ok" disabled>${esc(t("Apply"))}</button>
      </div>`, {
    cancel: () => closeDialog(),
    ok: apply,
    remove,
  }, {
    focus: "#cap",
    onKey: (e) => {
      if (e.target.id !== "cap" || e.key === "Escape") return;  // Esc: the dialog's cancel
      const plain = !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey;
      if (plain && e.key === "Tab") return;
      if (plain && e.key === "Enter" && combo) { e.preventDefault(); if (combo !== old) apply(); return; }
      if (plain && e.key === "Backspace") { e.preventDefault(); if (old) remove(); return; }
      e.preventDefault();
      const r = comboFrom(e);
      if (r.key) { combo = r.combo; held = []; } else { held = r.mods; combo = null; }
      draw();
    },
  });
  dialog.onkeyup = (e) => {
    if (e.target.id !== "cap" || combo) return;
    held = comboFrom(e).mods;
    draw();
  };
  // Back to the normal keymap however the dialog ends: OK, cancel, Esc, remove, errors.
  onDialogClose(() => { api.endKeyCapture().catch(() => {}); });
}
