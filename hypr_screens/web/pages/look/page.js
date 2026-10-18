/* Windows: presets, gaps and borders, opacity, and the advanced look (blur,
 * animations, border colors, see-through apps). */
import { esc, NB } from "../../core/dom.js";
import { nf, pct } from "../../core/format.js";
import { t } from "../../core/i18n.js";
import { S } from "../../core/state.js";
import { k, on, reg } from "../../core/view.js";
import { button, seg, slider, tcards, toggle } from "../../ui/controls.js";
import { confirmDialog } from "../../ui/dialog.js";
import { appIcon, ic } from "../../ui/icons.js";
import { expander, ph, row, sec } from "../../ui/layout.js";
import { openListbox } from "../../ui/popover.js";
import { resetLook, setDraft } from "./draft.js";
import { lookPreview } from "./preview.js";

/* What a preset sets (the rest stays as it is). */
const PRESET_KEYS = ["gapsIn", "gapsOut", "rounding", "border", "blur", "blurSize", "blurPasses", "activeOpacity", "inactiveOpacity"];
const PRESET_SUB = { Clean: () => t("Tight, square, no blur"), Soft: () => t("Airy and round"), Glass: () => t("See-through and blurred") };
const presetValues = (p) => Object.fromEntries(PRESET_KEYS.map((key) => [key, p.values[key]]));
const presetOf = (v) => ((S.look.presets || []).find((p) => PRESET_KEYS.every((key) => p.values[key] === v[key])) || {}).name || null;
const solidHex = (c) => String(c || "").slice(0, 7);

/* The slider of `key` within its range from the backend (else min…max). */
function lookSlider(key, v, { min, max, step = 1, fmt, title, scale = 1, live = true, disabled = false }) {
  const r = { min, max, step, ...((S.look.ranges || {})[key] || {}) };
  const toUi = (x) => Math.round(x * scale * 1000) / 1000;
  return slider(`lk-${key}`, {
    min: r.min * scale, max: r.max * scale, step: r.step * scale, value: toUi(v[key]), label: title, fmt, disabled,
    onInput: (x) => setDraft({ [key]: x / scale }, { full: false, live }),
    onChange: (x) => setDraft({ [key]: x / scale }),
  });
}

function presets(v) {
  return tcards("preset", (S.look.presets || []).map((p) => ({
    v: p.name, label: t(p.name), sub: PRESET_SUB[p.name] ? PRESET_SUB[p.name]() : "",
    thumb: lookPreview({ ...v, ...presetValues(p) }, true),
  })), presetOf(v), (name) => setDraft(presetValues(S.look.presets.find((x) => x.name === name))), { label: t("Style") });
}

/* See-through apps: an own opacity per window class. */
function appsBlock(v) {
  const apps = (v.apps || []).map((a, i) => {
    const setApp = (changes) => setDraft({ apps: v.apps.map((x, j) => (j === i ? { ...x, ...changes } : x)) });
    const part = (which, label, small) => `<span class="app-sl"><small>${esc(small)}</small>${slider(`app-${which[0]}-${i}`, {
      min: 30, max: 100, value: Math.round(a[which] * 100), label, fmt: pct, onChange: (x) => setApp({ [which]: x / 100 }),
    })}</span>`;
    return `<div class="app-row">${appIcon(a.class)}<b title="${esc(a.class)}">${esc(a.class)}</b>
        ${part("active", t("{app}: active", { app: a.class }), t("Active"))}
        ${part("inactive", t("{app}: not active", { app: a.class }), t("Others"))}
        <button type="button" class="btn ghost icon" aria-label="${esc(t("Remove {app}", { app: a.class }))}" title="${esc(t("Remove"))}" ${reg(`rmapp-${i}`, { click: () => setDraft({ apps: v.apps.filter((_, j) => j !== i) }) })}>${ic("x", "sm")}</button></div>`;
  }).join("");
  const addable = (S.look.apps || []).filter((a) => !(v.apps || []).some((x) => x.class === a.id));
  on("addapp", {
    select: (el) => openListbox(el, {
      header: t("Open apps"), value: null,
      options: addable.map((a) => ({ v: a.id, label: a.name, icon: appIcon(a.id) })),
      onPick: (id) => setDraft({ apps: [...(v.apps || []), { class: id, active: 0.9, inactive: 0.8 }] }),
    }),
  });
  const add = addable.length
    ? `<button type="button" class="btn" aria-haspopup="listbox" aria-expanded="false" ${k("addapp")}>${ic("plus", "sm")}${esc(t("Add an app"))}</button>`
    : `<span class="muted small">${esc(t("No other app is open"))}</span>`;
  return `<div class="row sub block" data-sid="look.apps"><div class="row-head"><div class="row-text"><div class="row-title"><span class="t">${esc(t("See-through apps"))}</span></div><div class="row-desc">${esc(t("These apps get their own opacity"))}</div></div><div class="row-end">${add}</div></div>${apps ? `<div class="body app-list">${apps}</div>` : ""}</div>`;
}

/* Own border colors: two color wells of the gradient and its switch. */
function borderColors(v) {
  const own = !!v.borderColors;
  const theme = (S.look.themeBorder && S.look.themeBorder.colors) || ["#89b4fa", "#89b4fa"];
  const well = (i, title, label) => {
    const set = (c) => { const both = [...S.lookDraft.borderColors]; both[i] = c; return { borderColors: both }; };
    return `<label class="swatch" title="${esc(title)}"><i style="background:${esc(v.borderColors[i])}"></i><span>${i + 1}</span><input type="color" value="${esc(solidHex(v.borderColors[i]))}" aria-label="${esc(label)}" ${reg(`col-${i + 1}`, { color: (c) => setDraft(set(c), { full: false }), colorDone: (c) => setDraft(set(c)) })}></label>`;
  };
  const wells = own ? `${well(0, t("Gradient start"), t("Border color 1"))}${well(1, t("Gradient end"), t("Border color 2"))}` : "";
  const switchTo = (x) => setDraft(x
    ? { borderColors: [solidHex(theme[0]), solidHex(theme[1] || theme[0])], borderAngle: S.look.themeBorder ? S.look.themeBorder.angle || 0 : 0 }
    : { borderColors: null, borderAngle: 0 });
  return row({
    sid: "look.colors", cls: "sub", title: esc(t("Own border colors")), desc: esc(own ? t("A gradient around the active window") : t("Off: the colors come from the Omarchy theme")),
    end: `${wells}${toggle("custcol", own, switchTo, { label: t("Own border colors") })}`,
  });
}

function advanced(v) {
  const px = (x) => `${nf(x)}${NB}px`;
  return expander("look-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("Blur, animations, border colors, see-through apps")) }, [
    row({ sid: "look.blur", cls: "sub", title: esc(t("Blur")), desc: esc(t("Blurs what is behind see-through windows")),
      end: toggle("lk-blur", v.blur, (x) => setDraft({ blur: x }), { label: t("Blur") }) }),
    row({ sid: "look.blurSize", cls: "sub", title: esc(t("Blur strength")),
      end: lookSlider("blurSize", v, { min: 1, max: 20, title: t("Blur strength"), fmt: px, disabled: !v.blur }) }),
    row({ sid: "look.blurPasses", cls: "sub", title: esc(t("Blur quality")),
      end: seg("passes", [{ v: 1, label: t("Fast") }, { v: 2, label: t("Balanced") }, { v: 3, label: t("Fine") }, { v: 4, label: t("Finest") }], v.blurPasses, (x) => setDraft({ blurPasses: x }), { label: t("Blur quality"), disabled: !v.blur }) }),
    row({ sid: "look.anim", cls: "sub", title: esc(t("Animation speed")), desc: esc(t("1× is Omarchy’s speed, 2× twice as fast")),
      end: lookSlider("animSpeed", v, { min: 0.25, max: 3, step: 0.05, title: t("Animation speed"), fmt: (x) => `${nf(x, 2)}×`, live: false }) }),
    borderColors(v),
    v.borderColors ? row({ sid: "look.angle", cls: "sub", title: esc(t("Gradient angle")),
      end: lookSlider("borderAngle", v, { min: 0, max: 355, step: 5, title: t("Gradient angle"), fmt: (x) => `${nf(x)}°` }) }) : "",
    appsBlock(v),
  ].join(""));
}

function resetButton() {
  if (!Object.keys(S.look.saved || {}).length) return "";
  return button("lookreset", `${ic("undo", "sm")}${esc(t("Reset to Omarchy"))}`, async () => {
    const ok = await confirmDialog({ title: t("Back to Omarchy’s look?"), text: t("Forgets your own window look; the Omarchy theme decides again."), ok: t("Reset") });
    if (ok) resetLook();
  }, { attrs: 'data-sid="look.reset"' });
}

export function pageLook() {
  const v = S.lookDraft;
  const px = (x) => `${nf(x)}${NB}px`;
  const gap = (key, title, icon, desc) => row({ sid: `look.${key}`, icon, title: esc(title), desc: esc(desc), end: lookSlider(key, v, { min: 0, max: 30, title, fmt: px }) });
  const opacity = (key, title, desc) => row({ sid: `look.${key}`, icon: "opacity", title: esc(title), desc: esc(desc), end: lookSlider(key, v, { min: 0.3, max: 1, step: 0.01, scale: 100, title, fmt: pct }) });
  const preset = presetOf(v);
  return `${ph(esc(t("Windows")), esc(t("How windows look. You see every change right away as a preview – “Apply” keeps it.")), resetButton())}
      <div class="card lp-card" id="lp">${lookPreview(v)}</div>
      ${sec(esc(t("Style")), `<div data-sid="look.presets">${presets(v)}</div>`, { sub: preset ? "" : esc(t("Own settings")) })}
      ${sec(esc(t("Gaps and borders")), `<div class="stack">
        ${gap("gapsIn", t("Inner gaps"), "gapIn", t("Between the windows"))}
        ${gap("gapsOut", t("Outer gaps"), "gapOut", t("To the edge of the screen"))}
        ${gap("rounding", t("Corners"), "corner", t("Rounding of the window corners"))}
        ${gap("border", t("Border"), "border", t("Width of the window border"))}
      </div>`)}
      ${sec(esc(t("Opacity")), `<div class="stack">
        ${opacity("activeOpacity", t("Active window"), t("100 % = solid"))}
        ${opacity("inactiveOpacity", t("Other windows"), t("100 % = solid"))}
      </div>`)}
      <div class="stack" style="margin-top:var(--s1)">${advanced(v)}</div>`;
}
