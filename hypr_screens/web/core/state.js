/* What the page knows: the backend's answers (S) and the UI's own state (UI).
 *
 * Each part of S has a loader. A part that fails to load keeps its error in
 * S.err (the page that needs it shows the reason and "try again"). */
import { api } from "./api.js";
import { clone } from "./dom.js";

export const S = { err: {} };

export const UI = {
  sel: null,          // the screen picked on the Screens page
  open: {},           // expanders that are open, by key
  wtab: "content",    // the tab of a widget's page
  wtabNext: null,     // the tab to open with the next widget page (search)
  busy: 0,            // changes on their way to the backend
  pressed: false,     // a pointer is down (no live refresh while dragging)
  camBusy: false, samBusy: false, cavaBusy: false,
};

/* Only the look's draft survives a reload while it is being previewed. */
export function takeLook(look) {
  S.look = look;
  S.lookBase = clone(look.values);
  if (!S.lookDraft || !look.previewing) S.lookDraft = clone(look.values);
}

/* name: [load, the field that shows it is loaded]. */
const LOADERS = {
  screens: [async () => { [S.screens, S.fixed] = [await api.screens(), await api.fixedStatus()]; }, () => S.screens],
  keys: [async () => { S.keys = await api.keys(); }, () => S.keys],
  look: [async () => { takeLook(await api.look()); }, () => S.look],
  sound: [async () => { S.sound = await api.soundState(); }, () => S.sound],
  camera: [async () => { S.camera = await api.camera(); }, () => S.camera],
  samsung: [async () => { S.samsung = await api.samsung(); }, () => S.samsung],
  widgets: [async () => { [S.widgets, S.layouts] = [await api.widgets(), await api.layouts()]; }, () => S.widgets],
  general: [async () => { [S.lang, S.about] = [await api.language(), await api.about()]; }, () => S.lang],
  /* Optional: an older backend has no enforcer; then its card is not shown. */
  enforcement: [async () => { S.enforcement = await enforcement(); }, () => true],
};
export const PARTS = Object.keys(LOADERS);

async function enforcement() {
  if (typeof api.enforcement !== "function") return null;
  try { return await api.enforcement(); } catch { return null; }
}

/* Load parts of the state; a part that fails keeps its error. */
export const reload = (...names) => Promise.all(names.map(async (name) => {
  try { await LOADERS[name][0](); delete S.err[name]; } catch (err) { S.err[name] = err; }
}));

export const loaded = (name) => !S.err[name] && !!LOADERS[name][1]();
