/* The dialog that records a new key combination for one slot of an action.
 * Hyprland gets an empty keymap while it records (so Super+Q reaches us). */
import { api, optional } from "../../core/api.js";
import { change, showError } from "../../core/change.js";
import { $, clone, esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S, UI } from "../../core/state.js";
import { render } from "../../core/view.js";
import { closeDialog, dialog, onDialogClose, openDialog } from "../../ui/dialog.js";
import { ic } from "../../ui/icons.js";
import { notice } from "../../ui/layout.js";
import { caps, comboFrom, comboText, heldCaps, isModifierKey, needsModifier, resetSuper } from "./combo.js";

const SAVED_MS = 1400;
const POLL_MS = 300;

/* Marks the slot as just saved for a moment. */
function flashSaved(action, slot) {
  UI.savedSlot = `${action}:${slot}`;
  setTimeout(() => { if (UI.savedSlot === `${action}:${slot}`) { UI.savedSlot = null; render(); } }, SAVED_MS);
}

export function captureDialog(action, slot) {
  const a = S.keys.actions.find((x) => x.id === action);
  const old = a.slots[slot];
  let combo = null, held = [], unusable = false, ready = false, poll = 0;
  resetSuper();  // a stuck Super from an earlier keyup that never came

  const conflict = () => {
    if (unusable) return notice("alert", esc(t("This key cannot be used here. Try another one.")), "warn");
    if (combo && needsModifier(combo)) return notice("alert", `${esc(t("A key alone would stop working in every app."))}<small>${esc(t("Add Super, Ctrl, Alt or Shift."))}</small>`, "warn");
    if (!combo) return "";
    const other = S.keys.actions.find((x) => x.id !== action && x.slots.includes(combo)) || (a.slots[1 - slot] === combo ? a : null);
    if (other) return notice("alert", `${esc(t("Already used by “{action}”.", { action: t(other.title) }))}<small>${esc(t("Taking it over removes it there."))}</small>`, "warn");
    const hypr = S.keys.hyprBinds[combo];
    if (hypr) return notice("alert", `${esc(t("Hyprland uses it for “{action}”.", { action: t(hypr) }))}<small>${esc(t("Taking it over replaces that while Tuneup runs."))}</small>`, "warn");
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
    $('[data-d="ok"]', dialog).disabled = !combo || combo === old || needsModifier(combo);
  };
  const apply = async () => {
    const chosen = combo;
    // What this takes from other slots, so Undo puts back just these (not every slot as it was).
    const taken = [];
    for (const b of clone(S.keys.actions)) b.slots.forEach((c, i) => { if (c === chosen && !(b.id === action && i === slot)) taken.push([b.id, i]); });
    closeDialog();
    const holds = (id, i, value) => (S.keys.actions.find((x) => x.id === id) || { slots: [] }).slots[i] === value;
    const done = await change(() => api.setKey(action, slot, chosen), async () => {
      if (holds(action, slot, chosen)) await api.setKey(action, slot, old || "");  // not if it was changed meanwhile
      for (const [id, i] of taken) if (holds(id, i, null)) await api.setKey(id, i, chosen);
    }, { reload: ["keys"], msg: (r) => (r && r.live === false ? t("Saved, but Hyprland has not taken it yet. It will after the next reload.")
      : r && r.conflicts && r.conflicts.length ? t("Saved · replaces Hyprland’s {keys} while Tuneup runs", { keys: r.conflicts.map(comboText).join(", ") }) : t("Saved")) });
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
      const r = comboFrom(e);
      const plain = !r.mods.length;  // Super counts too, though WebKitGTK sets no metaKey for it
      if (plain && e.key === "Tab") return;
      if (!ready) { e.preventDefault(); return; }  // Hyprland is not in the empty keymap yet
      if (plain && e.key === "Enter" && combo) { e.preventDefault(); if (combo !== old && !needsModifier(combo)) apply(); return; }
      if (plain && e.key === "Backspace") { e.preventDefault(); if (old) remove(); return; }
      e.preventDefault();
      unusable = !r.key && !isModifierKey(e);
      if (r.key) { combo = r.combo; held = []; } else { held = r.mods; combo = null; }
      draw();
    },
  });
  // The keymap must really be the empty one before keys are taken; if it cannot be, nothing is recorded
  // (the keys would fire their real actions).
  api.beginKeyCapture().then(() => {
    ready = true;
    // Hyprland leaves the keymap on its own (Esc, anything else): the dialog follows.
    poll = setInterval(async () => {
      const r = await optional("keyCaptureActive").catch(() => undefined);
      if (r && r.active === false) closeDialog();
    }, POLL_MS);
  }).catch((err) => { closeDialog(); showError(err); });
  dialog.onkeyup = (e) => {
    if (e.target.id !== "cap" || combo) return;
    held = comboFrom(e).mods;
    draw();
  };
  // Back to the normal keymap however the dialog ends: OK, cancel, Esc, remove, errors.
  onDialogClose(() => { clearInterval(poll); api.endKeyCapture().catch(() => {}); });
}
