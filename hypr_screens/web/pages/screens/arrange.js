/* The arrangement canvas of the Screens page: the connected screens to scale,
 * dragged (or moved with the arrow keys) to where they stand on the desk.
 * Positions are computed once the page is in the DOM. */
import { $, $$ } from "../../core/dom.js";
import { UI } from "../../core/state.js";
import { render } from "../../core/view.js";
import { bounds, canDrag, conn, dropOf, OPP, rectOf, scr, sharedEdges } from "./model.js";

const GAP = 3;
const PAD = 32;
const MAX_SCALE = 0.14;
const view = { f: 0, ox: 0, oy: 0 };

export function layoutArrange() {
  const cv = $("#arrange");
  if (!cv) return;
  const rects = conn().map(rectOf);
  if (!rects.length) return;
  const b = bounds(rects);
  view.f = Math.min((cv.clientWidth - PAD * 2) / b.w, (cv.clientHeight - PAD * 2) / b.h, MAX_SCALE);
  view.ox = (cv.clientWidth - b.w * view.f) / 2 - b.minX * view.f;
  view.oy = (cv.clientHeight - b.h * view.f) / 2 - b.minY * view.f;
  for (const r of rects) placeTile(cv, r);
  drawEdges(cv, rects);
}

function placeTile(cv, r) {
  const el = $(`.scr[data-scr="${CSS.escape(r.id)}"]`, cv);
  if (!el) return;
  Object.assign(el.style, {
    left: `${r.x * view.f + view.ox + GAP}px`, top: `${r.y * view.f + view.oy + GAP}px`,
    width: `${r.w * view.f - GAP * 2}px`, height: `${r.h * view.f - GAP * 2}px`,
  });
  el.classList.toggle("tight", r.h * view.f < 100);
  el.classList.toggle("tiny", r.h * view.f < 72);
}

function drawEdges(cv, rects) {
  $$(".edge", cv).forEach((e) => e.remove());
  for (const e of sharedEdges(rects)) {
    const d = document.createElement("div");
    d.className = "edge";
    if (e.v) Object.assign(d.style, { left: `${e.x * view.f + view.ox - 2}px`, top: `${e.y1 * view.f + view.oy + 10}px`, width: "4px", height: `${Math.max(0, (e.y2 - e.y1) * view.f - 20)}px` });
    else Object.assign(d.style, { top: `${e.y * view.f + view.oy - 2}px`, left: `${e.x1 * view.f + view.ox + 10}px`, height: "4px", width: `${Math.max(0, (e.x2 - e.x1) * view.f - 20)}px` });
    cv.appendChild(d);
  }
}

/* onDrop(screen, {x, y}, drop): a screen was dropped somewhere new;
 * onSide(screen, side): the arrow keys put it on that side. */
export function bindArrange({ onDrop, onSide }) {
  const cv = $("#arrange");
  if (!cv) return;
  layoutArrange();
  let drag = null;
  let justDragged = false;

  cv.addEventListener("pointerdown", (e) => {
    const el = e.target.closest(".scr");
    if (!el || e.button !== 0) return;
    const s = scr(el.dataset.scr);
    if (!s || !canDrag(s)) return;
    drag = { el, s, x0: e.clientX, y0: e.clientY, pos0: { x: s.position.x, y: s.position.y }, moved: false, want: null, drop: null };
    el.setPointerCapture(e.pointerId);
  });
  cv.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
    if (!drag.moved && Math.hypot(dx, dy) < 4) return;
    drag.moved = true;
    drag.el.classList.add("drag");
    drag.want = { x: drag.pos0.x + dx / view.f, y: drag.pos0.y + dy / view.f };
    drag.drop = dropOf(drag.s, drag.want);
    if (!drag.drop) return;
    // Where it will land: edge to edge, centred.
    const r = { id: drag.s.id, ...drag.drop.spot, w: drag.s.position.w, h: drag.s.position.h };
    placeTile(cv, r);
    drawEdges(cv, conn().map((s) => (s.id === drag.s.id ? r : rectOf(s))));
  });
  const end = () => {
    if (!drag) return;
    const d = drag;
    drag = null;
    d.el.classList.remove("drag");
    if (!d.moved) return;
    justDragged = true;
    setTimeout(() => (justDragged = false), 0);
    UI.sel = d.s.id;
    if (!d.drop || d.drop.side === d.drop.target.side) { render(); return; }
    onDrop(d.s, { x: Math.round(d.want.x), y: Math.round(d.want.y) }, d.drop);
  };
  cv.addEventListener("pointerup", end);
  cv.addEventListener("pointercancel", end);
  cv.addEventListener("click", (e) => {
    const el = e.target.closest(".scr");
    if (!el || justDragged) return;
    if (UI.sel !== el.dataset.scr) { UI.sel = el.dataset.scr; render(); }
  });
  cv.addEventListener("keydown", (e) => {
    const el = e.target.closest(".scr");
    const side = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "above", ArrowDown: "below" }[e.key];
    if (!el || !side) return;
    const s = scr(el.dataset.scr);
    if (!s || !canDrag(s)) return;
    e.preventDefault();
    UI.sel = s.id;
    // The laptop does not move: the other screen goes to the opposite side.
    const target = s.laptop ? conn().find((x) => x.id !== s.id) : s;
    const want = s.laptop ? OPP[side] : side;
    if (target.side === want) { render(); return; }
    onSide(target, want);
  });
}
