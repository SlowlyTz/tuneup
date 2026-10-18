/* Screens: the arrangement canvas, then the settings of the screen picked on it. */
import { api } from "../../core/api.js";
import { change } from "../../core/change.js";
import { clone, esc, NB } from "../../core/dom.js";
import { hz, nf, pct, res } from "../../core/format.js";
import { loc, t } from "../../core/i18n.js";
import { S, UI } from "../../core/state.js";
import { afterRender, k, on, reg, render } from "../../core/view.js";
import { button, group, radios, seg, toggle } from "../../ui/controls.js";
import { confirmDialog } from "../../ui/dialog.js";
import { ic, monGlyph } from "../../ui/icons.js";
import { block, expander, notice, ph, row } from "../../ui/layout.js";
import { openListbox } from "../../ui/popover.js";
import { bindArrange } from "./arrange.js";
import {
  canDrag, conn, laptopId, oneDesktopByDefault, parseMode, rotLabel, ROT, SCALES, scaleLabel, scr, SIDES, sideText, sname,
} from "./model.js";

const keepIfApplied = (key) => (r) => key !== "one_desktop" && r && r.applied && r.applied.length > 0;

/* Sets one setting of screen `s` (undo puts the old value and condition back). */
function setScreen(s, key, value, when = null, msg = undefined) {
  const old = clone(s.settings[key]);
  return change(
    () => api.setScreenSetting(s.id, key, value, when),
    () => api.setScreenSetting(s.id, key, old.value, old.value == null ? [] : old.when),
    { reload: ["screens"], confirm: keepIfApplied(key), msg },
  );
}

const swapFixed = () => change(() => api.swapFixed(), () => api.swapFixed(), { reload: ["screens"], msg: t("Swapped until the monitor is unplugged") });
export const swapButton = (key, label) => button(key, `${ic("swap", "sm")}${esc(label)}`, swapFixed, { attrs: key === "swap" ? 'data-sid="screens.swap"' : "" });

/* "Always" / "Only with <screen>": one other screen at most. */
function whenChip(s, key) {
  const st = s.settings[key];
  if (st.value == null) return "";
  const other = st.when.length ? scr(st.when[0]) : null;
  const label = !st.when.length ? t("Always") : t("Only with {name}", { name: other ? sname(other) : st.when[0] });
  const name = `when-${key}`;
  on(name, {
    select: (el) => openListbox(el, {
      header: t("Applies"),
      value: st.when[0] || "",
      options: [
        { v: "", label: t("Always") },
        { head: t("Only while this one is connected:") },
        ...S.screens.filter((o) => o.id !== s.id).map((o) => ({ v: o.id, label: sname(o), sub: o.connected ? "" : t("not connected") })),
      ],
      onPick: (v) => { if (v !== (st.when[0] || "")) setScreen(s, key, st.value, v ? [v] : [], t("Applies: {when}", { when: v ? t("Only with {name}", { name: sname(scr(v)) }) : t("Always") })); },
    }),
  });
  return `<button type="button" class="when${st.when.length ? " on" : ""}" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(t("Applies: {when}", { when: label }))}" title="${esc(t("When does this setting apply?"))}" ${k(name)}><span>${esc(label)}</span>${ic("chevD")}</button>`;
}

/* The end of a setting's head: "not set" (what Hyprland does) or "Reset", and the condition. */
function settingHead(s, key, hyprText) {
  const st = s.settings[key];
  if (st.value == null) {
    return `<span class="unset-note">${esc(hyprText ? t("Not set · Hyprland: {value}", { value: hyprText }) : t("Not set"))}</span>`;
  }
  const idle = st.active || !s.connected ? "" : `<span class="pill neutral" title="${esc(t("Its screen is not connected now"))}">${esc(t("Not in force now"))}</span>`;
  return `${idle}<button type="button" class="link" ${reg(`reset-${key}`, { click: () => setScreen(s, key, null) })}>${esc(t("Reset"))}</button>${whenChip(s, key)}`;
}

/* The tile's size: what the screen shows (physical pixels and scale). */
function tileSize(s) {
  if (!s.hypr) return res(s.position.w, s.position.h);
  const m = parseMode(s.hypr.mode);
  return s.hypr.scale && s.hypr.scale !== 1 ? `${res(m.w, m.h)} · ${pct(Math.round(s.hypr.scale * 100))}` : res(m.w, m.h);
}

function arrangeCard(sel, cs) {
  const fx = S.fixed || {};
  const tiles = cs.map((s) => {
    const fixed = fx.fixed === s.id && cs.length > 1;
    const tip = [
      !canDrag(s) ? (cs.length > 1 ? t("Drag one of the other screens: the laptop stays where it is") : "") : t("Drag to arrange · arrow keys put it next to the laptop"),
      s.hypr && s.hypr.scale !== 1 ? t("Desktop size {size}", { size: res(s.position.w, s.position.h) }) : "",
    ].filter(Boolean).join("\n");
    return `<button type="button" class="scr${s.id === sel.id ? " sel" : ""}" data-scr="${esc(s.id)}" aria-pressed="${s.id === sel.id}" aria-label="${esc(sname(s))}${fixed ? `, ${esc(t("fixed"))}` : ""}"${tip ? ` title="${esc(tip)}"` : ""}>
        ${ic(s.laptop ? "laptop" : "monitor", "glyph-ic")}
        <span class="n">${esc(sname(s))}</span><span class="m">${tileSize(s)}</span>
        ${fixed ? `<span class="pill fixed-badge">${ic("pin")}${esc(t("Fixed"))}</span>` : ""}</button>`;
  }).join("");
  const known = S.screens.filter((s) => !s.connected);
  const strip = known.length ? `<div class="known"><span class="known-h">${esc(t("Known screens"))}</span>${known.map((s) => {
    const m = s.modes.find((x) => x.preferred) || s.modes[0] || { w: 16, h: 9 };
    const h = Math.round((26 * m.h) / m.w);
    return `<button type="button" class="kscr${s.id === sel.id ? " sel" : ""}" aria-pressed="${s.id === sel.id}" ${reg(`known-${s.id}`, { click: () => { UI.sel = s.id; render(); } })}><span class="mini" style="width:26px;height:${h}px"></span><span><b>${esc(sname(s))}</b><small>${m.w ? res(m.w, m.h) : ""}</small></span>${s.favorite ? `<span title="${esc(t("Favorite"))}">${ic("star", "xs")}</span>` : ""}</button>`;
  }).join("")}</div>` : "";
  return `<div class="card arr-card" data-sid="screens.arrange">
      <div class="arr-bar"><span class="hint">${ic("drag", "sm")}${esc(cs.length > 1 ? t("Drag to arrange · click to select") : t("Only one screen is connected"))}</span>${fx.swapped ? `<span class="pill">${esc(t("Swapped"))}</span>` : ""}${fx.canSwap ? swapButton("swap", t("Swap the fixed screen")) : ""}</div>
      <div class="arrange" id="arrange">${tiles}</div>${strip}</div>`;
}

/* "For new monitors": global, so on the page (not in a screen's settings). */
function newMonitorsRow() {
  const value = S.keys.options.default_fixed;
  return row({
    sid: "screens.newmon", icon: "monitor", title: esc(t("For new monitors")), desc: esc(t("Which screen becomes fixed when an unknown monitor arrives")),
    end: seg("newmon", [{ v: "off", label: t("Off") }, { v: "external", label: t("External monitor") }, { v: "panel", label: t("Laptop") }], value,
      (v) => change(() => api.setOption("default_fixed", v), () => api.setOption("default_fixed", value), { reload: ["keys", "screens"] }),
      { label: t("For new monitors") }),
  });
}

function screenHead(sel, cs) {
  const pref = sel.modes.find((m) => m.preferred) || sel.modes[0];
  const fixedNow = (S.fixed || {}).fixed === sel.id && cs.length > 1 ? `<span class="pill">${ic("pin")}${esc(t("Fixed now"))}</span>` : "";
  const meta = [
    `<span class="state-dot${sel.connected ? "" : " off"}"></span>${esc(sel.connected ? t("Connected") : t("Not connected"))}`,
    `<span class="mono">${esc(sel.connector)}</span>`,
    pref ? `<span class="num">${res(pref.w, pref.h)}</span>` : "",
    sel.description && !sel.laptop ? `<span class="desc" title="${esc(sel.description)}">${esc(sel.description)}</span>` : "",
  ].filter(Boolean).join('<span class="dotsep"></span>');
  const away = sel.connected ? "" : `<div style="margin-bottom:var(--s1)">${notice("info", esc(sel.lastSeen
    ? t("Not connected (last seen {date}). The settings apply as soon as it is back.", { date: new Date(sel.lastSeen).toLocaleDateString(loc()) })
    : t("Not connected. The settings apply as soon as it is back.")))}</div>`;
  return `<div class="scr-head">
      <span class="icon-tile">${ic(sel.laptop ? "laptop" : "monitor")}</span>
      <div><h2>${esc(sname(sel))}</h2><div class="meta">${meta}</div></div>
      <div class="end">${fixedNow}</div>
    </div>${away}`;
}

function rotationBlock(sel) {
  const live = sel.hypr ? sel.hypr.rotation : undefined;
  return block({
    sid: "screens.rotation", icon: "rotate", title: esc(t("Rotation")), desc: esc(t("For screens that stand upright or upside down")),
    head: settingHead(sel, "rotation", sel.hypr ? rotLabel(sel.hypr.rotation) : ""),
    body: group("rot", ROT(), sel.settings.rotation.value, (v) => setScreen(sel, "rotation", v, null, `${t("Rotation")}: ${rotLabel(v)}`), {
      cls: "choices", itemCls: "choice", label: t("Rotation"), mark: live,
      item: (o) => `<span class="tick">${ic("check")}</span>${monGlyph(o.v)}<span>${esc(o.label)}</span>`,
    }),
  });
}

function scaleBlock(sel) {
  const opts = SCALES();
  const value = sel.settings.scale.value;
  if (value != null && !opts.some((o) => o.v === value)) opts.push({ v: value, label: scaleLabel(value) });
  return block({
    sid: "screens.scale", icon: "scale", title: esc(t("Scale")), desc: esc(t("Makes text and windows bigger or smaller")),
    head: settingHead(sel, "scale", sel.hypr ? scaleLabel(sel.hypr.scale) : ""),
    body: seg("scale", opts, value, (v) => setScreen(sel, "scale", v, null, `${t("Scale")}: ${scaleLabel(v)}`), { label: t("Scale"), unset: true, mark: sel.hypr ? sel.hypr.scale : undefined }),
  });
}

/* Resolution: the sizes as a list (recommended first), the refresh rates of the chosen one. */
function modeBlock(sel) {
  const live = sel.hypr ? parseMode(sel.hypr.mode) : null;
  const pref = sel.modes.find((m) => m.preferred) || sel.modes[0];
  const stored = sel.settings.mode.value;
  const cur = stored && stored !== "preferred" ? parseMode(stored) : null;
  const shown = cur || (stored === "preferred" ? pref : live);
  const size = shown ? sel.modes.find((m) => m.w === shown.w && m.h === shown.h) : null;
  const sizes = [...sel.modes].sort((a, b) => Number(b.preferred) - Number(a.preferred));
  const opts = [
    ...(pref ? [{ v: "preferred", label: t("What the screen prefers"), sub: res(pref.w, pref.h) }] : []),
    ...sizes.map((m) => ({ v: `${m.w}x${m.h}`, label: res(m.w, m.h), badge: m.preferred ? t("Recommended") : "", sub: `${m.rates.map((r) => nf(r, 2)).join(" / ")}${NB}Hz` })),
  ];
  const value = stored === "preferred" ? "preferred" : cur ? `${cur.w}x${cur.h}` : null;
  const pick = (v) => {
    if (v === "preferred") { setScreen(sel, "mode", "preferred"); return; }
    const m = sel.modes.find((x) => `${x.w}x${x.h}` === v);
    setScreen(sel, "mode", m.modes[m.rates.indexOf(Math.max(...m.rates))]);
  };
  const rates = size ? size.rates.map((r, i) => ({ v: size.modes[i], label: hz(r) })) : [];
  const rateChips = rates.length > 1 || (rates.length && cur)
    ? `<div class="rates"><span class="row-desc">${esc(t("Refresh rate"))}</span>${group("rate", rates, cur && size ? stored : null, (m) => setScreen(sel, "mode", m), {
      cls: "chips", itemCls: "chip", label: t("Refresh rate"), mark: live && !cur ? sel.hypr.mode : undefined,
      item: (o) => `${ic("hz")}<span class="num">${esc(o.label)}</span>`,
    })}</div>` : "";
  return block({
    sid: "screens.mode", icon: "resolution", title: esc(t("Resolution")),
    head: settingHead(sel, "mode", live ? `${res(live.w, live.h)} @ ${hz(live.rate)}` : ""),
    body: `${radios("mode", opts, value, pick, { label: t("Resolution"), unset: true, mark: live ? `${live.w}x${live.h}` : undefined })}${rateChips}`,
  });
}

function positionBlock(sel) {
  if (sel.laptop) return "";
  return block({
    sid: "screens.position", icon: "arrange", title: esc(t("Position")), desc: esc(sel.side ? sideText(sel.side) : t("Next to the laptop")),
    head: settingHead(sel, "position", ""),
    body: seg("side", SIDES(), sel.settings.position.value, (v) => setScreen(sel, "position", v, null, `${t("Position")}: ${sideText(v)}`), { label: t("Position"), unset: true, mark: sel.side || undefined }),
  });
}

/* "Always shows the same desktop": while not set, the default of "For new monitors" shows. */
function oneDesktopRow(sel) {
  const od = sel.settings.one_desktop;
  const unset = od.value == null;
  const byDefault = oneDesktopByDefault(sel);
  const shown = unset ? byDefault : od.value;
  const desc = unset
    ? (byDefault ? t("Default: on (For new monitors)") : t("Default: off (For new monitors)"))
    : od.value ? t("Stays on one desktop; the desktops 1–10 are on the other screen") : t("Has its own desktops");
  const title = t("Always shows the same desktop");
  const reset = unset ? "" : `<button type="button" class="link" ${reg("reset-od", { click: () => setScreen(sel, "one_desktop", null) })}>${esc(t("Reset"))}</button>`;
  return row({
    sid: "screens.one", icon: "pin", title: esc(title), desc: esc(desc),
    end: `${reset}${whenChip(sel, "one_desktop")}${toggle("od", shown, (v) => setScreen(sel, "one_desktop", v, null, `${title}: ${v ? t("On") : t("Off")}`), { label: title, unset })}`,
  });
}

function advanced(sel) {
  const forget = async () => {
    const name = sname(sel);
    const ok = await confirmDialog({ title: t("Forget “{name}”?", { name }), text: t("All settings of this screen are deleted. If you connect it again, it starts like new."), ok: t("Forget"), danger: true });
    if (!ok) return;
    await change(() => api.forgetScreen(sel.id), null, { reload: ["screens"], msg: t("“{name}” forgotten", { name }) });
    if (!scr(UI.sel)) { UI.sel = laptopId(); render(); }
  };
  return expander("scr-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("Favorite, forget")) }, [
    row({
      sid: "screens.fav", cls: "sub", title: esc(t("Favorite")), desc: esc(t("Comes first in the list")),
      end: toggle("fav", sel.favorite, () => change(() => api.toggleFavorite(sel.id), () => api.toggleFavorite(sel.id), { reload: ["screens"] }), { label: t("Favorite") }),
    }),
    row({
      sid: "screens.forget", cls: "sub", title: esc(t("Forget this screen")),
      desc: esc(sel.laptop ? t("The laptop screen cannot be forgotten") : sel.connected ? t("Only possible while it is not connected") : t("Deletes all settings of this screen")),
      end: button("forget", `${ic("trash", "sm")}${esc(t("Forget"))}`, forget, { cls: "btn danger", attrs: sel.connected || sel.laptop ? "disabled" : "" }),
    }),
  ].join(""));
}

export function pageScreens() {
  if (!scr(UI.sel)) UI.sel = laptopId();
  const sel = scr(UI.sel);
  const cs = conn();
  afterRender(() => bindArrange({
    onDrop: (s, at, drop) => {
      const old = clone(drop.target.settings.position);
      change(() => api.setScreenSetting(s.id, "position", at),
        () => api.setScreenSetting(drop.target.id, "position", old.value, old.value == null ? [] : old.when),
        { reload: ["screens"], confirm: keepIfApplied("position") });
    },
    onSide: (target, side) => setScreen(target, "position", side),
  }));
  return `${ph(esc(t("Screens")), esc(t("Drag the screens to where they stand on your desk.")))}
      ${arrangeCard(sel, cs)}
      <div class="stack" style="margin-bottom:var(--s5)">${newMonitorsRow()}</div>
      ${screenHead(sel, cs)}
      <div class="stack">${positionBlock(sel)}${rotationBlock(sel)}${scaleBlock(sel)}${modeBlock(sel)}${oneDesktopRow(sel)}</div>
      <div class="stack" style="margin-top:var(--s1)">${advanced(sel)}</div>`;
}
