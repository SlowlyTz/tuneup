/* One change from the user: send it, reload what it touched, render, and
 * offer "Undo" (or ask "keep it?"). Failures become a toast. */
import { keepDialog } from "../ui/dialog.js";
import { toast } from "../ui/toast.js";
import { errText } from "./format.js";
import { t } from "./i18n.js";
import { reload, UI } from "./state.js";
import { render } from "./view.js";

export const showError = (err) => toast(errText(err), null, { error: true });

/* Counts as busy (no live refresh) while `work` runs. */
export async function busy(work) {
  UI.busy += 1;
  try { return await work(); } finally { UI.busy -= 1; }
}

/* apply(): the API call; revert(result): undoes it (or null: no undo).
 * reload: state parts to load again afterwards.
 * confirm: true, or a function of the result, to ask "keep it?" instead of a toast.
 * msg: the toast's text (a function of the result, or false for none). */
export async function change(apply, revert, { reload: names = [], confirm = false, msg, keepTitle } = {}) {
  let result;
  try {
    result = await busy(apply);
  } catch (err) {
    if (err && err.code === "apply_failed" && names.length) await reload(...names);
    render();
    showError(err);
    return undefined;
  }
  await busy(() => reload(...names));
  render();
  const undo = revert ? async () => {
    await busy(async () => {
      try { await revert(result); } catch (err) { showError(err); }
      await reload(...names);
    });
    render();
  } : null;
  if (typeof confirm === "function" ? confirm(result) : confirm) { keepDialog(undo, keepTitle); return result; }
  const text = typeof msg === "function" ? msg(result) : msg;
  if (text !== false) toast(text || t("Saved"), undo);
  return result;
}
