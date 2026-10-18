/* Camera: the rotated virtual camera for every app, its preview and rotation.
 *
 * The preview: in the app the frames come straight from the camera feeder
 * (tuneup://camera/preview.jpg, about 10 a second; asking for them
 * keeps the camera running); in a browser from api.cameraPreview(). Each frame
 * is loaded in the background and only then shown, and a new render starts
 * from the last frame, so nothing blinks. */
import { api, inApp } from "../core/api.js";
import { change } from "../core/change.js";
import { $, esc } from "../core/dom.js";
import { t } from "../core/i18n.js";
import { route } from "../core/router.js";
import { S, UI } from "../core/state.js";
import { afterRender, render } from "../core/view.js";
import { button, seg, toggle } from "../ui/controls.js";
import { ic } from "../ui/icons.js";
import { ph, row, spinner } from "../ui/layout.js";

const FRAME_MS = 100;
const RETRY_MS = 500;
/* No frame for this long: say why instead of spinning on. */
const NO_PICTURE_MS = 5000;
const cam = { on: false, n: 0, last: "", since: 0 };

const wanted = () => route().page === "camera" && S.camera && S.camera.installed && S.camera.enabled && !document.hidden && !S.err.camera;

function loadFrame(src) {
  return new Promise((done) => {
    const next = new Image();
    next.onload = () => done(src);
    next.onerror = () => done("");
    next.src = src;
  });
}

/* Why there is no picture (after a while without one). */
function noPicture(p) {
  const c = S.camera || {};
  if (p && p.reason === "off") return t("The camera is off");
  if (p && p.reason === "not_set_up") return t("Not set up");
  if (c.state == null) return t("No preview – the background service is not running");
  if (c.state === "busy") return t("No preview – another app holds the camera");
  return t("No preview – the camera sends no picture");
}

async function frame() {
  if (inApp()) {
    const src = await loadFrame(`tuneup://camera/preview.jpg?n=${++cam.n}`);
    if (src) return { src };
  }
  let p = null;
  try { p = await api.cameraPreview(); } catch { p = null; }
  return { src: p && p.image ? await loadFrame(p.image) : "", p };
}

function show(src, p) {
  const img = $("#cam-img"), msg = $("#cam-msg");
  if (img && src) {
    cam.last = src; cam.since = performance.now();
    img.src = src; img.hidden = false;
    if (msg) msg.hidden = true;
    return;
  }
  if (!msg || cam.last) return;
  msg.hidden = false;
  if (img) img.hidden = true;
  const waited = performance.now() - cam.since > NO_PICTURE_MS;
  msg.classList.toggle("stuck", waited);
  $(".cam-msg-t", msg).textContent = waited ? noPicture(p) : t("Starting the camera …");
}

/* Runs while the page shows the preview. */
function previewLoop() {
  if (cam.on) return;
  cam.on = true;
  cam.since = performance.now();
  const step = async () => {
    if (!wanted()) { cam.on = false; cam.last = ""; return; }
    const began = performance.now();
    const { src, p } = await frame();
    show(src, p);
    const wait = src && inApp() ? FRAME_MS - (performance.now() - began) : RETRY_MS;
    setTimeout(step, Math.max(0, wait));
  };
  step();
}
export const resumePreview = () => { if (route().page === "camera") previewLoop(); };

function camState(c) {
  if (c.state == null) return { text: t("The background service is not running"), cls: "warn" };
  return ({
    off: { text: t("Off"), cls: "neutral" },
    idle: { text: t("Ready · no app uses it"), cls: "neutral" },
    live: { text: c.users === 1 ? t("1 app uses it") : t("{n} apps use it", { n: c.users }), cls: "ok" },
    busy: { text: t("The camera is busy (another app holds it)"), cls: "warn" },
  })[c.state] || { text: String(c.state), cls: "neutral" };
}

const howItWorks = (c) => `<div class="howto"><h3>${esc(t("How it works"))}</h3><ol>
      <li>${esc(t("Pick the rotation here"))}</li>
      <li>${esc(t("In the app, pick “{name}” as the camera", { name: c.virtualName }))}</li>
      <li>${esc(t("The camera light is only on while an app uses it"))}</li>
    </ol></div>`;

function setupPage(c, intro) {
  const setup = async () => {
    UI.camBusy = true; render();
    await change(() => api.setupCamera(), null, { reload: ["camera"], msg: t("The camera is set up") });
    UI.camBusy = false; render();
  };
  return `${ph(esc(t("Camera")), intro)}
      <div class="stack">${row({
        sid: "camera.setup", lead: `<span class="icon-tile">${ic("camera")}</span>`, title: esc(t("Not set up")),
        desc: esc(UI.camBusy ? t("Setting up … enter your password in the dialog") : t("Set up once: takes about a minute and needs your password. Then every app finds the camera “{name}”.", { name: c.virtualName })),
        end: button("camsetup", UI.camBusy ? `${spinner()}${esc(t("Setting up …"))}` : `${esc(t("Set it up"))}${ic("chevR", "sm")}`, setup, { cls: "btn primary", attrs: UI.camBusy ? "disabled" : "" }),
      })}</div>
      ${howItWorks(c)}`;
}

function previewCard(c) {
  const body = c.enabled
    ? `<img id="cam-img" alt="${esc(t("Camera preview"))}"${cam.last ? ` src="${esc(cam.last)}"` : " hidden"}><span class="cam-msg" id="cam-msg" role="status"${cam.last ? " hidden" : ""}>${spinner()}<span class="cam-msg-t">${esc(t("Starting the camera …"))}</span></span>`
    : `<span class="cam-msg">${ic("camera", "lg")}<span>${esc(t("The camera is off"))}</span></span>`;
  const label = c.enabled ? t("Preview · {device}", { device: c.device || t("Camera") }) : t("Apps do not see the camera");
  return `<div class="card pad"><div class="cam${c.enabled ? "" : " off"}">${body}<span class="label"><span class="rec"></span>${esc(label)}</span></div></div>`;
}

export function pageCamera() {
  const c = S.camera;
  const intro = esc(t("Turns the camera picture for every app, like a monitor."));
  if (!c.hasCamera) {
    return `${ph(esc(t("Camera")), intro)}<div class="stack">${row({ lead: `<span class="icon-tile">${ic("camera")}</span>`, title: esc(t("No camera found")), desc: esc(t("Connect a camera; it shows up here.")) })}</div>`;
  }
  if (!c.installed) return setupPage(c, intro);
  const rotations = (c.rotations || [0, 90, 180, 270]).map((v) => ({ v, label: `${v}°` }));
  const set = (enabled, rotation) => change(() => api.setCamera(enabled, rotation), () => api.setCamera(c.enabled, c.rotation), { reload: ["camera"] });
  const state = camState(c);
  afterRender(previewLoop);
  return `${ph(esc(t("Camera")), intro)}
      <div class="stack">
        ${row({ sid: "camera.toggle", icon: "camera", title: esc(t("Rotated camera for apps")), desc: esc(t("In Discord, the browser or Zoom pick “{name}”", { name: c.virtualName })), end: toggle("camon", c.enabled, (v) => set(v, c.rotation), { label: t("Rotated camera for apps") }) })}
        ${previewCard(c)}
        ${row({ sid: "camera.rotation", icon: "rotate", title: esc(t("Rotation")), end: seg("camrot", rotations, c.rotation, (v) => set(c.enabled, v), { label: t("Rotation") }) })}
        ${row({ icon: "info", title: esc(t("Status")), desc: esc(t("The real camera only runs while an app uses it")), end: `<span class="pill ${state.cls}">${esc(state.text)}</span>` })}
      </div>`;
}
