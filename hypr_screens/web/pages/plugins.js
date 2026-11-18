/* Plugins: Tuneup's own extras from the plugins/ folder. Installing puts one
 * into the bar at once; its settings are drawn from what the plugin declares. */
import { api } from "../core/api.js";
import { change } from "../core/change.js";
import { esc } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { S, UI } from "../core/state.js";
import { render } from "../core/view.js";
import { button, select, stepper, toggle } from "../ui/controls.js";
import { confirmDialog } from "../ui/dialog.js";
import { ic } from "../ui/icons.js";
import { emptyState, expander, ph, row, spinner } from "../ui/layout.js";

async function install(p) {
  UI.pluginBusy = p.id; render();
  await change(() => api.installPlugin(p.id), () => api.removePlugin(p.id), {
    reload: ["plugins"], msg: t("{name} is in the bar now", { name: p.name }),
  });
  UI.pluginBusy = null; render();
}

async function remove(p) {
  const ok = await confirmDialog({
    title: t("Remove {name}?", { name: p.name }),
    text: t("It leaves the bar. Its settings are kept for when you install it again."), ok: t("Remove"), danger: true,
  });
  if (!ok) return;
  UI.pluginBusy = p.id; render();
  await change(() => api.removePlugin(p.id), () => api.installPlugin(p.id), { reload: ["plugins"], msg: t("{name} removed", { name: p.name }) });
  UI.pluginBusy = null; render();
}

const setValue = (p, key, value) => {
  const old = p.values[key];
  return change(() => api.setPluginSetting(p.id, key, value), () => api.setPluginSetting(p.id, key, old), { reload: ["plugins"] });
};

function control(p, s) {
  const key = `pl.${p.id}.${s.key}`;
  const value = p.values[s.key];
  if (s.type === "bool") return toggle(key, value, (v) => setValue(p, s.key, v), { label: s.label });
  if (s.type === "enum") {
    return select(key, { options: s.options.map((o) => ({ v: o.value, label: o.label })), value, label: s.label, onChange: (v) => setValue(p, s.key, v) });
  }
  return stepper(key, { min: s.min ?? 0, max: s.max ?? 100, value, label: s.label, onChange: (v) => setValue(p, s.key, v) });
}

/* What the plugin found (an app it works with, say): one line each in its fold. */
const checkRow = (p, c) => row({
  sid: `plugins.${p.id}.check.${c.id}`, cls: "sub",
  title: esc(c.label), desc: esc(c.text || (c.ok ? t("Found") : t("Not found"))),
  end: c.ok ? `<span class="pill">${ic("check", "sm")}${esc(t("Ready"))}</span>` : "",
});

function card(p) {
  const busyHere = UI.pluginBusy === p.id;
  const action = p.installed
    ? button(`pl.rm.${p.id}`, esc(t("Remove")), () => remove(p), { attrs: busyHere ? "disabled" : "" })
    : button(`pl.in.${p.id}`, busyHere ? `${spinner()}${esc(t("Installing …"))}` : `${ic("plus", "sm")}${esc(t("Install"))}`, () => install(p),
      { cls: "btn primary", attrs: busyHere ? "disabled" : "" });
  const status = p.installed ? `<span class="pill">${ic("check", "sm")}${esc(t("Installed"))}</span>` : "";
  const title = `${esc(p.name)}${p.version ? ` <span class="muted small">${esc(p.version)}</span>` : ""}`;
  const settings = p.installed ? p.settings.map((s) => row({
    sid: `plugins.${p.id}.${s.key}`, cls: "sub", title: esc(s.label), desc: s.description ? esc(s.description) : "", end: control(p, s),
  })) : [];
  const body = [...p.checks.map((c) => checkRow(p, c)), ...settings];
  if (!body.length) {
    return row({ sid: `plugins.${p.id}`, lead: `<span class="icon-tile">${ic(p.icon)}</span>`, title, desc: esc(p.description), end: `${status}${action}` });
  }
  /* The checks and the settings fold out below the plugin. */
  return expander(`pl.x.${p.id}`, { sid: `plugins.${p.id}`, icon: p.icon, title, desc: esc(p.description), end: `${status}${action}` }, body.join(""));
}

export function pagePlugins() {
  const list = S.plugins || [];
  const intro = t("Extras for your desktop. An installed plugin goes into the bar at once.");
  if (!list.length) return `${ph(esc(t("Plugins")), esc(intro))}${emptyState("plugin", esc(t("No plugins found")))}`;
  return `${ph(esc(t("Plugins")), esc(intro))}
      <div class="plugin-list" data-sid="plugins.list">${list.map(card).join("")}</div>`;
}
