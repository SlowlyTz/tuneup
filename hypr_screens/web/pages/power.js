/* Battery & power (Samsung Galaxy Book): charge limit, performance mode, fan,
 * keyboard light and the firmware switches. */
import { api } from "../core/api.js";
import { change } from "../core/change.js";
import { esc, NB } from "../core/dom.js";
import { minutes, nf, pct } from "../core/format.js";
import { t } from "../core/i18n.js";
import { S, UI } from "../core/state.js";
import { render } from "../core/view.js";
import { button, group, seg, slider, toggle } from "../ui/controls.js";
import { confirmDialog } from "../ui/dialog.js";
import { ic } from "../ui/icons.js";
import { block, expander, notice, ph, row, sec, spinner } from "../ui/layout.js";

export const MODE_INFO = {
  "low-power": { icon: "leaf", desc: () => t("Longest battery life, slowed down") },
  quiet: { icon: "moon", desc: () => t("The fan stays almost silent") },
  balanced: { icon: "balance", desc: () => t("For every day") },
  performance: { icon: "bolt", desc: () => t("Full power, the fan can be heard") },
};
const LIMITS = [60, 80, 90, 100];
const HOT_CPU = 80;
const INTRO = "Samsung Galaxy Book";

export const modeLabel = (s, v) => { const m = (s.modes || []).find((x) => x.value === v); return m ? t(m.label) : v || "–"; };

export function setSam(field, value, msg) {
  const old = S.samsung[field];
  return change(() => api.setSamsung(field, value), field === "active" ? null : () => api.setSamsung(field, old), { reload: ["samsung"], msg });
}

export function battState(s) {
  if (s.charging) return s.fullInMinutes != null ? t("Charging · full in {time}", { time: minutes(s.fullInMinutes) }) : t("Charging");
  if (s.plugged) return t("Plugged in, not charging");
  return s.remainingMinutes != null ? t("On battery · {time} left", { time: minutes(s.remainingMinutes) }) : t("On battery");
}

function setupPage() {
  const setup = async () => {
    UI.samBusy = true; render();
    await setSam("active", true, t("The Samsung control is set up"));
    UI.samBusy = false; render();
  };
  return `${ph(esc(t("Battery & power")), INTRO)}
      <div class="stack">${row({
        sid: "power.setup", lead: `<span class="icon-tile">${ic("battery")}</span>`, title: esc(t("The Samsung control is off")),
        desc: esc(t("Set it up once: needs your password. Then Tuneup takes over the charge limit and the modes.")),
        end: button("samon", UI.samBusy ? `${spinner()}${esc(t("Setting up …"))}` : esc(t("Set it up")), setup, { cls: "btn primary", attrs: UI.samBusy ? "disabled" : "" }),
      })}</div>`;
}

function hero(s) {
  const level = s.level ?? 0;
  const stat = (label, value) => `<div class="stat"><small>${esc(label)}</small><b>${value}</b></div>`;
  const stats = [
    s.health != null ? stat(t("Health"), esc(pct(s.health))) : "",
    s.cycles != null ? stat(t("Charge cycles"), nf(s.cycles)) : "",
    s.power != null ? stat(t("Power draw"), `${nf(s.power, 1)}${NB}W`) : "",
    stat(t("Charge limit"), s.fullOnce ? esc(t("once 100 %")) : esc(pct(s.chargeLimit))),
  ].join("");
  return `<div class="card hero" data-sid="power.battery">
      <div class="batt" aria-hidden="true"><div class="shell"><i style="width:${level}%"></i></div><span class="cap"></span><span class="limit" style="left:calc(6.5px + (100% - 21px) * ${s.chargeLimit / 100} - 1px)"></span></div>
      <div>
        <div class="hero-big"><span class="num">${s.level == null ? "–" : nf(level)}<small>%</small></span><span class="st">${esc(battState(s))}</span></div>
        <div class="stats">${stats}</div>
      </div>
    </div>`;
}

function limitBlock(s) {
  const limits = [...LIMITS];
  if (s.wantedLimit != null && !limits.includes(s.wantedLimit)) limits.push(s.wantedLimit);
  const head = s.fullOnce
    ? `<span class="pill">${ic("bolt")}${esc(t("Charges once to 100 %"))}</span>${button("fullstop", esc(t("Cancel")), () => setSam("fullOnce", false))}`
    : `${s.plugged ? "" : `<span class="muted small">${esc(t("Plug in the charger first."))}</span>`}${button("full", `${ic("bolt", "sm")}${esc(t("Charge fully once"))}`, () => setSam("fullOnce", true, t("Charges once to 100 %")), { attrs: `data-sid="power.full"${s.plugged ? "" : " disabled"}` })}`;
  return block({
    sid: "power.limit", icon: "heart", title: esc(t("Charge limit")), desc: esc(t("A limit below 100 % is easier on the battery")), head,
    body: seg("limit", limits.sort((a, b) => a - b).map((v) => ({ v, label: pct(v) })), s.wantedLimit, (v) => setSam("chargeLimit", v), { label: t("Charge limit") }),
  });
}

function advanced(s) {
  const off = s.attributesWritable === false;
  const switchOff = async () => {
    const ok = await confirmDialog({ title: t("Switch off the Samsung control?"), text: t("Charge limit and the four modes go back to Omarchy. You can set them up again later."), ok: t("Switch off"), danger: true });
    if (ok) setSam("active", false, t("Switched off"));
  };
  return expander("pow-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("USB charging, opening the lid, Samsung control")) }, [
    s.usbCharging == null ? "" : row({ sid: "power.usb", cls: "sub", title: esc(t("USB charging while the laptop is off")), desc: esc(t("Charges the phone even when the laptop is off")), end: toggle("usb", s.usbCharging, (v) => setSam("usbCharging", v), { label: t("USB charging while the laptop is off"), disabled: off }) }),
    s.lidPower == null ? "" : row({ sid: "power.lid", cls: "sub", title: esc(t("Switch on when the lid opens")), end: toggle("lid", s.lidPower, (v) => setSam("lidPower", v), { label: t("Switch on when the lid opens"), disabled: off }) }),
    row({ sid: "power.off", cls: "sub", title: esc(t("Switch off the Samsung control")), desc: esc(t("Gives Omarchy its battery menu and the modes back")), end: button("samoff", esc(t("Switch off")), switchOff, { cls: "btn danger" }) }),
  ].join(""));
}

export function pagePower() {
  const s = S.samsung;
  if (!s.active) return setupPage();
  const readOnly = s.writable === false ? `<div class="sec">${notice("alert", esc(t("Some values cannot be changed right now. Run the setup again if this stays.")), "warn")}</div>` : "";
  const modes = group("pmode", (s.modes || []).map((m) => ({ v: m.value, label: t(m.label), ...(MODE_INFO[m.value] || { icon: "gauge", desc: () => "" }) })), s.mode, (v) => setSam("mode", v, modeLabel(s, v)), {
    cls: "mcards", itemCls: "mcard", label: t("Performance mode"),
    item: (m) => `${ic(m.icon)}<b>${esc(m.label)}</b><small>${esc(m.desc())}</small>`,
  });
  const fan = s.fanRpm ? t("The fan runs at {rpm} rpm", { rpm: nf(s.fanRpm) }) : s.fanRunning ? t("The fan is running") : t("The fan is still");
  const temp = s.cpuTemp != null ? `<span class="pill ${s.cpuTemp > HOT_CPU ? "warn" : "neutral"}">${ic("temp")}CPU <span class="num">${nf(s.cpuTemp)}${NB}°C</span></span>` : "";
  const keyboard = s.kbdLight == null ? "" : row({
    sid: "power.kbd", icon: "sun", title: esc(t("Keyboard light")),
    end: slider("kbd", { min: 0, max: s.kbdMax || 3, value: s.kbdLight, label: t("Keyboard light"), fmt: (v) => (v ? t("Level {n}", { n: v }) : t("Off")), onChange: (v) => setSam("kbdLight", v) }),
  });
  return `${ph(esc(t("Battery & power")), INTRO)}
      ${readOnly}${hero(s)}
      ${sec(esc(t("Battery charging")), `<div class="stack">${limitBlock(s)}</div>`)}
      ${s.modes && s.modes.length ? sec(esc(t("Performance mode")), `<div data-sid="power.mode">${modes}</div>`) : ""}
      <div class="stack" style="margin-top:var(--s2)">
        ${row({ sid: "power.fan", icon: "fan", title: esc(t("Fan and temperature")), desc: esc(fan), end: temp })}
        ${keyboard}
        ${advanced(s)}
      </div>`;
}
