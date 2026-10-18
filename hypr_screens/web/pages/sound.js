/* Sound: every output and input device (not only the default one) and the apps playing. */
import { api } from "../core/api.js";
import { change } from "../core/change.js";
import { esc } from "../core/dom.js";
import { pct } from "../core/format.js";
import { t } from "../core/i18n.js";
import { S } from "../core/state.js";
import { button, chipsOne, select, slider } from "../ui/controls.js";
import { appIcon, ic } from "../ui/icons.js";
import { emptyState, ph, sec } from "../ui/layout.js";

const DEV_ICON = { speaker: "speaker", headphones: "headphones", tv: "tv", mic: "mic" };
const AGAIN = { reload: ["sound"] };
/* More outputs than this: a select instead of chips. */
const CHIPS_MAX = 3;

const setVolume = (x, v) => change(() => api.setVolume(x.key, v), () => api.setVolume(x.key, x.volume), AGAIN);
const toggleMute = (x) => change(() => api.setMute(x.key, !x.muted), () => api.setMute(x.key, x.muted), { ...AGAIN, msg: x.muted ? t("Sound on") : t("Sound off") });

/* The mute button of a device or app (key: its handler key, if not its own). */
export function muteButton(x, name, { input = false, disabled = false, key = x.key } = {}) {
  const icon = input ? (x.muted ? "micX" : "mic") : (x.muted ? "volX" : "speaker");
  return button(`mute-${key}`, ic(icon), () => toggleMute(x), { cls: "btn icon ghost mute", attrs: `aria-pressed="${x.muted}"${disabled ? " disabled" : ""}`, label: x.muted ? t("Unmute {name}", { name }) : t("Mute {name}", { name }) });
}
export const volumeSlider = (x, name, { disabled = false, key = x.key } = {}) =>
  slider(`vol-${key}`, { min: 0, max: 100, value: x.volume, label: t("Volume {name}", { name }), fmt: pct, onChange: (v) => setVolume(x, v), disabled });
const volumeLine = (x, name, opts = {}) => `${muteButton(x, name, opts)}${volumeSlider(x, name, opts)}`;

function deviceActions(d, name, usable) {
  const locked = d.forceMute;
  const input = d.kind === "source";
  const switchOn = d.connected && !d.active ? button(`on-${d.key}`, `${ic("power", "sm")}${esc(t("Switch on"))}`, () =>
    change(() => api.switchOnDevice(d.key), null, { ...AGAIN, msg: t("{name} is on", { name }) }), { attrs: `title="${esc(t("Switches the sound card to the profile that drives this device"))}"` }) : "";
  const makeDefault = d.isDefault || locked || !usable ? "" : button(`def-${d.key}`, esc(t("Make default")), () => {
    const prev = (input ? S.sound.inputs : S.sound.outputs).find((x) => x.isDefault);
    change(() => api.setDefault(d.key), prev ? () => api.setDefault(prev.key) : null, { ...AGAIN, msg: t("{name} is the default", { name }) });
  });
  const lockLabel = t("Force mute: {name}", { name });
  const lock = button(`fm-${d.key}`, locked ? `${ic("lock", "sm")}${esc(t("Force muted"))}` : ic("lock", "sm"), () =>
    change(() => api.setForceMute(d.key, !locked), d.connected ? () => api.setForceMute(d.key, locked) : null, { ...AGAIN, msg: locked ? t("Free again") : t("Stays muted") }),
  { cls: `btn lockbtn${locked ? "" : " icon ghost"}`, attrs: `aria-pressed="${locked}" aria-label="${esc(lockLabel)}" title="${esc(t("Force mute: keeps the device muted at 0 %, even when an app turns it up"))}"` });
  return `${switchOn}${makeDefault}${lock}`;
}

function deviceCard(d) {
  const locked = d.forceMute;
  const usable = d.active && d.connected;
  const name = t(d.name);
  const pills = [
    d.isDefault ? `<span class="pill">${ic("check")}${esc(t("Default"))}</span>` : "",
    locked ? `<span class="pill danger">${ic("lock")}${esc(t("Stays muted"))}</span>` : "",
    !d.connected ? `<span class="pill neutral">${esc(t("Not connected"))}</span>` : !d.active ? `<span class="pill neutral">${esc(t("Switched off"))}</span>` : "",
  ].join("");
  return `<div class="card dev${locked ? " locked" : ""}${usable ? "" : " inactive"}">
      <div class="dev-top">
        <span class="icon-tile">${ic(locked ? "lock" : DEV_ICON[d.icon] || "speaker")}</span>
        <div class="row-text"><div class="row-title"><b>${esc(name)}</b>${pills}</div><div class="row-desc">${esc(d.sub || "")}</div></div>
        <div class="row-end">${deviceActions(d, name, usable)}</div>
      </div>
      ${usable ? `<div class="dev-vol">${volumeLine(d, name, { input: d.kind === "source", disabled: locked })}</div>` : ""}
    </div>`;
}

function appCard(a) {
  const outs = S.sound.outputs.filter((o) => o.active && o.connected && (!o.forceMute || o.key === a.output));
  const out = S.sound.outputs.find((o) => o.key === a.output);
  const setOut = (v) => change(() => api.setAppOutput(a.key, v), a.output ? () => api.setAppOutput(a.key, a.output) : null, AGAIN);
  const label = t("Output for {app}", { app: a.name });
  const outCtl = outs.length <= CHIPS_MAX
    ? chipsOne(`aout-${a.key}`, outs.map((o) => ({ v: o.key, label: t(o.name), icon: DEV_ICON[o.icon] || "speaker" })), a.output, setOut, { label })
    : select(`aout-${a.key}`, { options: outs.map((o) => ({ v: o.key, label: t(o.name) })), value: a.output, onChange: setOut, label });
  const sub = [a.sub, out ? t("Plays on {device}", { device: t(out.name) }) : ""].filter(Boolean).join(" · ");
  return `<div class="card dev">
      <div class="dev-top"><span class="icon-tile bare">${appIcon([...(a.icons || []), a.name], "app-ic")}</span>
        <div class="row-text"><div class="row-title"><b>${esc(a.name)}</b>${a.paused ? `<span class="pill neutral">${esc(t("Paused"))}</span>` : ""}</div><div class="row-desc">${esc(sub)}</div></div></div>
      <div class="dev-vol">${volumeLine(a, a.name)}</div>
      ${outs.length > 1 ? `<div class="dev-vol out"><span class="row-desc">${esc(t("Output"))}</span>${outCtl}</div>` : ""}
    </div>`;
}

export function pageSound() {
  const s = S.sound;
  const none = (text) => emptyState("speaker", esc(text));
  const apps = s.apps.length ? s.apps.map(appCard).join("")
    : emptyState("music", esc(t("No app is playing right now")), `<span class="small">${esc(t("As soon as an app plays sound, it shows up here."))}</span>`);
  return `${ph(esc(t("Sound")), esc(t("Volume and devices. For every device, not only the default one.")))}
      ${sec(esc(t("Output")), `<div class="stack" data-sid="sound.out">${s.outputs.map(deviceCard).join("") || none(t("No output device"))}</div>`)}
      ${sec(esc(t("Input")), `<div class="stack" data-sid="sound.in">${s.inputs.map(deviceCard).join("") || none(t("No input device"))}</div>`)}
      ${sec(esc(t("Apps")), `<div class="stack" data-sid="sound.apps">${apps}</div>`)}`;
}
