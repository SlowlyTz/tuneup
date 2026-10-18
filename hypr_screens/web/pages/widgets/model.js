/* The widgets as the backend reports them, and the changes made to them. */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { clone } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S } from "../../core/state.js";
import { toast } from "../../ui/toast.js";

export const W_ICON = { clock: "clock", calendar: "calendar", weather: "cloud", battery: "battery", system: "cpu", network: "wifi", disk: "disk", nowplaying: "play", lyrics: "lyrics", visualizer: "wave" };

export const wid = (kind) => (S.widgets || []).find((w) => w.kind === kind);

/* A field's value: content fields and "where & when" fields live apart. */
export const valueOf = (w, key) => (key in w.content ? w.content[key] : w.where[key]);

export const arrange = () => change(() => api.arrangeWidgets(), null, { msg: t("Arranging is open on the desktop") });

export async function setEnabled(w, on) {
  const name = t(w.name);
  const r = await change(() => api.updateWidget(w.kind, { enabled: on }), () => api.updateWidget(w.kind, { enabled: !on }), {
    reload: ["widgets"],
    msg: (x) => (on && x && !x.placed ? false : on ? t("{name} is on", { name }) : t("{name} is off", { name })),
  });
  // Never placed yet: it starts in the middle of the screen; offer to arrange it.
  if (r && on && !r.placed) toast(t("{name} is on – it starts in the middle of the screen", { name }), null, { action: { label: t("Arrange"), run: arrange } });
}

export function setField(w, f, value) {
  const old = clone(w[f.group][f.key]);
  return change(() => api.updateWidget(w.kind, { [f.group]: { [f.key]: value } }), () => api.updateWidget(w.kind, { [f.group]: { [f.key]: old } }), { reload: ["widgets"] });
}
