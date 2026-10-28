/* The screens as the backend reports them, and the geometry of arranging them. */
import { t } from "../../core/i18n.js";
import { pct } from "../../core/format.js";
import { S } from "../../core/state.js";

export const scr = (id) => (S.screens || []).find((s) => s.id === id);
/* Connected screens with a place on the desk. */
export const conn = () => (S.screens || []).filter((s) => s.connected && s.position);
/* Connected screens that show the laptop's picture (no place of their own). */
export const mirrors = () => (S.screens || []).filter((s) => s.connected && s.hypr && s.hypr.mirror);
export const laptopId = () => ((S.screens || []).find((s) => s.laptop) || (S.screens || [])[0] || {}).id;
export const sname = (s) => (s ? (s.laptop ? t("Laptop") : s.name) : "?");

/* "1920x1080@60.00" → {w, h, rate}. */
export function parseMode(mode) {
  const [size, rate] = String(mode).split("@");
  const [w, h] = size.split("x").map(Number);
  return { w, h, rate: Number(rate) };
}

export const OPP = { left: "right", right: "left", above: "below", below: "above" };
export const ROT = () => [
  { v: 0, label: t("Normal") }, { v: 90, label: t("Portrait, right") },
  { v: 180, label: t("Upside down") }, { v: 270, label: t("Portrait, left") },
];
export const SIDES = () => [
  { v: "left", label: t("Left") }, { v: "right", label: t("Right") },
  { v: "above", label: t("Above") }, { v: "below", label: t("Below") },
];
export const sideText = (side) => ({ left: t("Left of the laptop"), right: t("Right of the laptop"), above: t("Above the laptop"), below: t("Below the laptop") })[side] || "";
export const SCALES = () => [{ v: "auto", label: t("Auto") }, ...[1, 1.25, 1.5, 2].map((v) => ({ v, label: pct(v * 100) }))];
export const scaleLabel = (v) => (v === "auto" ? t("Auto") : pct(Math.round(v * 100)));
export const rotLabel = (v) => (ROT().find((o) => o.v === v) || { label: `${v}°` }).label;

/* Which side of `anchor` a rectangle is on, by their middles (as api.side_of). */
function sideOf(r, a) {
  const dx = ((r.x + r.w / 2) - (a.x + a.w / 2)) / Math.max(1, (r.w + a.w) / 2);
  const dy = ((r.y + r.h / 2) - (a.y + a.h / 2)) / Math.max(1, (r.h + a.h) / 2);
  if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? "right" : "left";
  return dy > 0 ? "below" : "above";
}

/* Edge to edge with `a` on `side`, centred along that edge (as apply.layout). */
function placeBeside({ w, h }, a, side) {
  return {
    left: { x: a.x - w, y: a.y + (a.h - h) / 2 }, right: { x: a.x + a.w, y: a.y + (a.h - h) / 2 },
    above: { x: a.x + (a.w - w) / 2, y: a.y - h }, below: { x: a.x + (a.w - w) / 2, y: a.y + a.h },
  }[side];
}

/* Dropping screen `s` with its top-left at `want`: whose side changes, to what, and where it lands. */
export function dropOf(s, want) {
  const live = conn();
  const others = live.filter((x) => x.id !== s.id).sort((a, b) => a.connector.localeCompare(b.connector));
  const anchor = live.find((x) => x.laptop) || others[0];
  if (!anchor) return null;
  const size = { w: s.position.w, h: s.position.h };
  if (anchor.id !== s.id) {
    const side = sideOf({ ...want, ...size }, anchor.position);
    return { target: s, side, spot: placeBeside(size, anchor.position, side) };
  }
  if (others.length !== 1) return null;
  const side = sideOf({ ...want, ...size }, others[0].position);
  return { target: others[0], side: OPP[side], spot: placeBeside(size, others[0].position, side) };
}

/* The laptop stays put while there are three or more screens. */
export const canDrag = (s) => conn().length > 1 && (!s.laptop || conn().length === 2);

/* The edges two screens share (drawn as the line the mouse crosses). */
export function sharedEdges(rects) {
  const out = [];
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    const y1 = Math.max(a.y, b.y), y2 = Math.min(a.y + a.h, b.y + b.h);
    const x1 = Math.max(a.x, b.x), x2 = Math.min(a.x + a.w, b.x + b.w);
    if (y2 > y1) {
      if (Math.abs(a.x + a.w - b.x) < 2) out.push({ v: true, x: b.x, y1, y2 });
      if (Math.abs(b.x + b.w - a.x) < 2) out.push({ v: true, x: a.x, y1, y2 });
    }
    if (x2 > x1) {
      if (Math.abs(a.y + a.h - b.y) < 2) out.push({ v: false, y: b.y, x1, x2 });
      if (Math.abs(b.y + b.h - a.y) < 2) out.push({ v: false, y: a.y, x1, x2 });
    }
  }
  return out;
}

export const rectOf = (s) => ({ id: s.id, ...s.position });

/* The bounding box of rectangles: {minX, minY, w, h}. */
export function bounds(rects) {
  const minX = Math.min(...rects.map((r) => r.x)), minY = Math.min(...rects.map((r) => r.y));
  return { minX, minY, w: Math.max(...rects.map((r) => r.x + r.w)) - minX, h: Math.max(...rects.map((r) => r.y + r.h)) - minY };
}
