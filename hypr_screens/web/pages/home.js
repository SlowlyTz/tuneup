/* Home: the most important things at a glance – screens, sound, battery, widgets. */
import { esc } from "../core/dom.js";
import { nf, pct } from "../core/format.js";
import { t } from "../core/i18n.js";
import { S } from "../core/state.js";
import { button, chipsMulti, seg } from "../ui/controls.js";
import { ic } from "../ui/icons.js";
import { ph } from "../ui/layout.js";
import { battState, MODE_INFO, modeLabel, setSam } from "./power.js";
import { bounds, conn, rectOf, scr, sname } from "./screens/model.js";
import { swapButton } from "./screens/page.js";
import { muteButton, volumeSlider } from "./sound.js";
import { arrange, setEnabled, W_ICON, wid } from "./widgets/model.js";

const MAP_W = 220, MAP_H = 72;

const tileHead = (icon, title, href) =>
  `<div class="tile-h">${ic(icon)}<b>${esc(title)}</b><a href="${href}" aria-label="${esc(t("Open {name}", { name: title }))}" title="${esc(t("Open"))}">${ic("chevR", "sm")}</a></div>`;

/* The connected screens as a little map. */
function minimap(cs, fixed) {
  const rects = cs.map(rectOf);
  if (!rects.length) return "";
  const b = bounds(rects);
  const f = Math.min(MAP_W / b.w, MAP_H / b.h);
  return rects.map((r) => `<span class="mm${fixed === r.id && cs.length > 1 ? " fixed" : ""}" style="left:calc(50% + ${(r.x - b.minX - b.w / 2) * f + 2}px);top:calc(50% + ${(r.y - b.minY - b.h / 2) * f + 2}px);width:${r.w * f - 4}px;height:${r.h * f - 4}px">${esc(sname(scr(r.id)))}</span>`).join("");
}

function screensTile() {
  const cs = conn(), fx = S.fixed || {};
  const fixedName = fx.fixed && scr(fx.fixed) ? sname(scr(fx.fixed)) : null;
  return `<div class="card tile">${tileHead("monitor", t("Screens"), "#/screens")}
      <div class="minimap" aria-hidden="true">${minimap(cs, fx.fixed)}</div>
      <div class="tile-foot"><span class="muted">${esc(fixedName && cs.length > 1 ? t("Fixed: {name}", { name: fixedName }) : t("{n} connected", { n: cs.length }))}</span>${fx.canSwap ? swapButton("hswap", t("Swap")) : ""}</div>
    </div>`;
}

function soundTile() {
  const snd = S.sound;
  const lines = [snd.outputs.find((o) => o.isDefault), snd.inputs.find((o) => o.isDefault)].map((d, i) => {
    if (!d) return "";
    const name = t(d.name);
    const opts = { input: i === 1, disabled: d.forceMute || !d.active, key: `home${i}` };
    return `<div class="mini-vol">${muteButton(d, name, opts)}<div class="mini-vol-b"><span class="t">${esc(name)}</span>${volumeSlider(d, name, opts)}</div></div>`;
  }).join("");
  const playing = snd.apps.length ? t("Playing: {apps}", { apps: snd.apps.map((a) => a.name).join(", ") }) : t("No app is playing right now");
  return `<div class="card tile">${tileHead("speaker", t("Sound"), "#/sound")}${lines}<div class="tile-foot"><span class="muted">${esc(playing)}</span></div></div>`;
}

function batteryTile() {
  const sm = S.samsung;
  const modes = (sm.modes || []).map((m) => ({ v: m.value, label: "", title: t(m.label), aria: t(m.label), icon: (MODE_INFO[m.value] || { icon: "gauge" }).icon }));
  return `<div class="card tile">${tileHead("battery", t("Battery & mode"), "#/power")}
      <div class="hero-big sm"><span class="num">${sm.level == null ? "–" : nf(sm.level)}<small>%</small></span><span class="st">${esc(battState(sm))}</span></div>
      <div class="meter" aria-hidden="true"><i style="width:${sm.level || 0}%"></i><b style="left:${sm.chargeLimit}%"></b></div>
      <div class="muted small">${esc(modeLabel(sm, sm.mode))} · ${esc(t("Charge limit"))} <span class="num">${esc(pct(sm.chargeLimit))}</span></div>
      ${modes.length ? `<div class="tile-foot">${seg("hmode", modes, sm.mode, (v) => setSam("mode", v, modeLabel(sm, v)), { cls: "seg wide", label: t("Performance mode"), item: (m) => ic(m.icon, "sm") })}</div>` : ""}
    </div>`;
}

function widgetsTile() {
  const W = S.widgets;
  const on = W.filter((w) => w.enabled);
  return `<div class="card tile">${tileHead("widgets", t("Widgets"), "#/widgets")}
      <div class="wmini">${chipsMulti("hwid", W.map((w) => ({ v: w.kind, label: t(w.name), icon: W_ICON[w.kind] })), on.map((w) => w.kind), (v, en) => setEnabled(wid(v), en), { label: t("Widgets on and off") })}</div>
      <div class="tile-foot"><span class="muted">${esc(t("{on} of {all} on", { on: on.length, all: W.length }))}</span>${button("harr", `${ic("arrange", "sm")}${esc(t("Arrange"))}`, arrange)}</div>
    </div>`;
}

export function pageHome() {
  const sm = S.samsung || {};
  return `${ph(esc(t("Home")), esc(t("The most important things at a glance.")))}
      <div class="tiles">
        ${S.screens ? screensTile() : ""}
        ${S.sound ? soundTile() : ""}
        ${sm.available && sm.active ? batteryTile() : ""}
        ${S.widgets ? widgetsTile() : ""}
      </div>`;
}
