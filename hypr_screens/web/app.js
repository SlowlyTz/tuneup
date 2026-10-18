/* hypr-screens – settings UI
 *
 * Plain script (no modules) so it also runs from file://.
 * Talks only to `window.api`: the Python bridge (bridge.js → hypr_screens/api.py)
 * in the app's window, mock.js in a plain browser. Shapes: API.md.
 *
 * Texts: every text is written in English and goes through t(); the table of
 * the app's language comes with window.hyprBoot.strings (English → translation),
 * or from api.translations() when there is no boot data (browser preview).
 * tests/test_i18n.py checks that every literal text given to t() here is translated.
 *
 * Rendering: each page is a function returning an HTML string. Controls
 * register their handlers in `H` under a stable key (data-on / data-k); one
 * set of delegated listeners dispatches events. After every change the page
 * is re-rendered and focus is restored by that key.
 */
(function () {
  "use strict";

  const api = window.api;
  const BOOT = window.hyprBoot || null;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
  const NB = " ";

  /* ================================================================ texts */
  let STR = (BOOT && BOOT.strings) || {};
  let LANG = (BOOT && BOOT.language) || document.documentElement.lang || "en";
  /* t(englishText, {name: value}) → the text in the app’s language, placeholders filled. */
  function t(text, values) {
    let s = Object.prototype.hasOwnProperty.call(STR, text) && STR[text] ? STR[text] : text;
    if (values) s = s.replace(/\{(\w+)\}/g, (m, name) => (name in values ? String(values[name]) : m));
    return s;
  }
  /* A translated text with one placeholder replaced by ready HTML (the rest escaped). */
  const tHtml = (text, name, html, values) => esc(t(text, values)).split(`{${name}}`).join(html);
  const loc = () => LANG || "en";
  const nf = (n, digits = 0) => new Intl.NumberFormat(loc(), { maximumFractionDigits: digits }).format(n);
  const pct = (n) => new Intl.NumberFormat(loc(), { style: "percent", maximumFractionDigits: 0 }).format(n / 100);
  const minutes = (m) => {
    if (m == null) return "";
    const h = Math.floor(m / 60), r = m % 60;
    return h ? (r ? t("{h} h {m} min", { h, m: r }) : t("{h} h", { h })) : t("{m} min", { m: r });
  };
  const hz = (r) => `${nf(r, 2)}${NB}Hz`;

  /* What the backend's error codes mean, for the toast (else its English message). */
  const ERRORS = {
    config_unreadable: () => t("The settings file cannot be read. Fix or remove ~/.config/hypr-screens/config.json."),
    unknown_screen: () => t("This screen is not known any more."),
    unknown_device: () => t("This device is gone."),
    unknown_widget: () => t("This widget is not known."),
    unknown_layout: () => t("This layout does not exist any more."),
    connected_screen: () => t("Unplug the screen first, then forget it."),
    internal_screen: () => t("The laptop screen cannot be forgotten."),
    not_connected: () => t("Only a connected screen can be dragged."),
    no_external: () => t("No external monitor is connected."),
    conflict: () => t("There is a layout with this name already."),
    force_muted: () => t("Force mute keeps this device silent. Switch it off first."),
    inactive: () => t("This device is switched off. Switch it on first."),
    not_set_up: () => t("This needs the one-time setup first."),
    not_plugged: () => t("Plug in the charger first."),
    unavailable: () => t("Not available on this computer."),
    cancelled: () => t("Cancelled or failed."),
    nothing_to_arrange: () => t("Switch a widget on first."),
    not_ready: () => t("The widgets are not ready yet. Try again in a moment."),
    apply_failed: () => t("Saved, but it could not be applied right now."),
  };
  const errText = (err) => (err && ERRORS[err.code] ? ERRORS[err.code]() : (err && err.message) || t("Something went wrong."));

  /* ================================================================ icons */
  const ICON = {
    home: '<path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z"/>',
    monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/>',
    laptop: '<path d="M5 6.5A1.5 1.5 0 0 1 6.5 5h11A1.5 1.5 0 0 1 19 6.5V15H5z"/><path d="M2.5 18.5h19"/>',
    keyboard: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M6.5 14h.01M17.5 14h.01M9.5 14h5"/>',
    window: '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M3 9h18M6.5 6.8h.01M9 6.8h.01"/>',
    widgets: '<rect x="4" y="4" width="7" height="7" rx="1.75"/><rect x="13" y="4" width="7" height="7" rx="1.75"/><rect x="4" y="13" width="7" height="7" rx="1.75"/><rect x="13" y="13" width="7" height="7" rx="3.5"/>',
    speaker: '<path d="M4 9.5h3l4.5-4v13L7 14.5H4z"/><path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11"/>',
    volX: '<path d="M4 9.5h3l4.5-4v13L7 14.5H4z"/><path d="m15.5 10 4 4m0-4-4 4"/>',
    camera: '<rect x="2.5" y="6.5" width="13" height="11" rx="2.5"/><path d="m15.5 10.5 5-3v9l-5-3"/>',
    battery: '<rect x="2.5" y="7" width="17" height="10" rx="2.5"/><path d="M21.5 10.5v3"/><path d="m11.5 9-2 3h3l-2 3"/>',
    sliders: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    search: '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.3-4.3"/>',
    chevR: '<path d="m9 6 6 6-6 6"/>',
    chevD: '<path d="m6 9 6 6 6-6"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    swap: '<path d="M7 4 3.5 7.5 7 11M3.5 7.5H17M17 13l3.5 3.5L17 20M20.5 16.5H7"/>',
    pin: '<path d="M9 4h6l-1 5 3 3v1.5H7V12l3-3z"/><path d="M12 13.5V20"/>',
    star: '<path d="m12 4 2.4 5 5.4.6-4 3.7 1.1 5.4L12 16l-4.9 2.7 1.1-5.4-4-3.7 5.4-.6z"/>',
    trash: '<path d="M4.5 7h15M10 4h4M6.5 7l.8 12a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4l.8-12M10 11v5.5M14 11v5.5"/>',
    rotate: '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3L4.5 9"/><path d="M4.5 4.5V9H9"/>',
    scale: '<path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/>',
    resolution: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 11V9h2.5M17 13v2h-2.5"/>',
    lock: '<rect x="5" y="10.5" width="14" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
    mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>',
    micX: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5M4 4l16 16"/>',
    headphones: '<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3.5" y="14" width="4" height="6" rx="1.5"/><rect x="16.5" y="14" width="4" height="6" rx="1.5"/>',
    tv: '<rect x="2.5" y="5" width="19" height="12.5" rx="2"/><path d="M8 20.5h8"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z"/>',
    book: '<path d="M5 4.5h10.5a2 2 0 0 1 2 2V20H7a2 2 0 0 1-2-2z"/><path d="M5 18a2 2 0 0 1 2-2h10.5"/>',
    folder: '<path d="M3.5 7a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
    leaf: '<path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14z"/><path d="M5 19c3-4 6-6.5 9-8"/>',
    moon: '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
    balance: '<path d="M12 4v16M8 20h8M5 7.5h14M5 7.5 2.8 13a2.3 2.3 0 0 0 4.4 0zM19 7.5 16.8 13a2.3 2.3 0 0 0 4.4 0z"/>',
    bolt: '<path d="M13 3 5.5 13.5H11L10 21l7.5-10.5H12z"/>',
    fan: '<circle cx="12" cy="12" r="1.8"/><path d="M12 10.2C10 6 11 3.5 13.5 3.5c2.4 0 2.6 3.4-1.5 6.7zM13.8 12c4.2-2 6.7-1 6.7 1.5 0 2.4-3.4 2.6-6.7-1.5zM12 13.8c2 4.2 1 6.7-1.5 6.7-2.4 0-2.6-3.4 1.5-6.7zM10.2 12C6 14 3.5 13 3.5 10.5c0-2.4 3.4-2.6 6.7 1.5z"/>',
    sun: '<circle cx="12" cy="12" r="3.5"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
    plug: '<path d="M9 3v4M15 3v4M7 7h10v4a5 5 0 0 1-10 0zM12 16v5"/>',
    power: '<path d="M12 3.5v8M7 6.5a7 7 0 1 0 10 0"/>',
    undo: '<path d="M9 7 4.5 11.5 9 16"/><path d="M4.5 11.5H15a4.5 4.5 0 0 1 0 9h-2"/>',
    external: '<path d="M14 4.5h5.5V10M19.5 4.5 11 13M17 14v4.5a1 1 0 0 1-1 1H5.5a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1H10"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    cloud: '<path d="M7 18.5a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 9.6a4.5 4.5 0 0 1-.5 8.9z"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    wifi: '<path d="M3 9.5a13 13 0 0 1 18 0M6 13a8.5 8.5 0 0 1 12 0M9 16.5a4 4 0 0 1 6 0"/><path d="M12 19.5h.01"/>',
    disk: '<rect x="3" y="6" width="18" height="12" rx="2.5"/><path d="M7 14.5h.01M10.5 14.5h6"/>',
    play: '<circle cx="12" cy="12" r="8.5"/><path d="M10 8.8v6.4l5-3.2z"/>',
    lyrics: '<path d="M4 6h16M4 10.5h10M4 15h16M4 19.5h7"/>',
    wave: '<path d="M4 10v4M8 6v12M12 9v6M16 4v16M20 10v4"/>',
    arrange: '<rect x="3.5" y="4" width="8" height="7" rx="1.5"/><rect x="12.5" y="13" width="8" height="7" rx="1.5"/><path d="M15 4.5h3.5a2 2 0 0 1 2 2V10M9 19.5H5.5a2 2 0 0 1-2-2V14"/>',
    alert: '<path d="M10.3 4.9 2.9 18a2 2 0 0 0 1.7 3h14.8a2 2 0 0 0 1.7-3L13.7 4.9a2 2 0 0 0-3.4 0z"/><path d="M12 10v4M12 17.3h.01"/>',
    fullscreen: '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
    desktops: '<rect x="3" y="5" width="8" height="6" rx="1.2"/><rect x="13" y="5" width="8" height="6" rx="1.2"/><rect x="3" y="13" width="8" height="6" rx="1.2"/><rect x="13" y="13" width="8" height="6" rx="1.2"/>',
    drop: '<path d="M12 3.5c3.5 4 6 7.3 6 10.5a6 6 0 0 1-12 0c0-3.2 2.5-6.5 6-10.5z"/>',
    corner: '<path d="M5 20v-7a8 8 0 0 1 8-8h6"/>',
    border: '<rect x="4" y="4" width="16" height="16" rx="3"/><rect x="7.5" y="7.5" width="9" height="9" rx="1"/>',
    gapIn: '<rect x="3.5" y="4" width="7" height="16" rx="1.5"/><rect x="13.5" y="4" width="7" height="16" rx="1.5"/>',
    gapOut: '<rect x="3" y="3" width="18" height="18" rx="3" stroke-dasharray="2.2 2.6"/><rect x="7.5" y="7.5" width="9" height="9" rx="1.5"/>',
    opacity: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>',
    palette: '<path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.2 0 1.8-.9 1.4-2-.5-1.2.3-2.5 1.6-2.5H17a3.5 3.5 0 0 0 3.5-3.5c0-5-3.8-9-8.5-9z"/><path d="M7.5 11.5h.01M10 7.5h.01M14.5 7.5h.01"/>',
    gauge: '<path d="M4.5 17a8.5 8.5 0 1 1 15 0"/><path d="m12 14 4-5"/>',
    sparkle: '<path d="M12 3.5 13.8 10 20.5 12l-6.7 2-1.8 6.5-1.8-6.5L3.5 12l6.7-2z"/>',
    drag: '<path d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01" stroke-width="2.6"/>',
    heart: '<path d="M12 19.5s-7.5-4.4-7.5-10A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 2.5c0 5.6-7.5 10-7.5 10z"/>',
    minimize: '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M12 8.5v6M9 12l3 3 3-3"/>',
    minOthers: '<rect x="3" y="7" width="12" height="11" rx="2"/><path d="M8 4.5h11a2 2 0 0 1 2 2V15M18 11l2-2 2 2" /><path d="M17 20.5h4"/>',
    restore: '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M12 15.5v-6M9 12l3-3 3 3"/>',
    restoreAll: '<rect x="6" y="7" width="15" height="13" rx="2.5"/><path d="M3 15V6a2 2 0 0 1 2-2h11M13.5 16.5v-5M11 14l2.5-2.5L16 14"/>',
    list: '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M7 9h.01M10 9h7M7 12h.01M10 12h7M7 15h.01M10 15h7"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    hz: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
    cycle: '<path d="M20 12a8 8 0 0 1-14.3 4.9M4 12a8 8 0 0 1 14.3-4.9"/><path d="M18.5 3.5v3.8h-3.8M5.5 20.5v-3.8h3.8"/>',
    temp: '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a3.5 3.5 0 1 1-4 0z"/><path d="M12 9v7"/>',
    usb: '<path d="M12 3v14M12 3l-2 2.5M12 3l2 2.5M8 10v2l4 2.5M16 8v3l-4 2.5"/><circle cx="12" cy="19" r="2"/>',
    music: '<path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
    minus: '<path d="M5 12h14"/>',
    edit: '<path d="M4.5 19.5h4L19 9a2.1 2.1 0 0 0-3-3L5.5 16.5z"/><path d="m14 8 3 3"/>',
    lid: '<path d="M5 15 7 5.5A1.5 1.5 0 0 1 8.5 4.3h7A1.5 1.5 0 0 1 17 5.5L19 15"/><path d="M2.5 18.5h19M12 8v3"/>',
  };
  const ic = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[n] || ""}</svg>`;

  /* Small colored app marks (the bridge will hand real icon-theme PNGs later). */
  const APP_IC = {
    spotify: '<circle cx="12" cy="12" r="10" fill="#1ed760"/><path d="M7 9.5c3.6-1 7.3-.6 10.2 1M7.6 12.6c2.9-.8 5.9-.4 8.3.9M8.2 15.5c2.3-.6 4.5-.3 6.3.7" stroke="#0e0e0e" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
    firefox: '<circle cx="12" cy="12" r="10" fill="#6e3fd8"/><path d="M12 2a10 10 0 0 1 9.6 7.2c-1-1.6-2.4-2.3-3.4-2.3.9 1.4 1.3 2.9 1.2 4.4A7.5 7.5 0 0 1 5.6 16 7 7 0 0 0 16.3 12c0-2.2-1.4-3.6-2.8-4 .9 1.5.2 3.3-1.6 3.3-1.3 0-2.3-1-2.3-2.4 0-2.5 2.2-4 4.3-4.4A9.8 9.8 0 0 0 12 2z" fill="#ff8a24"/>',
    alacritty: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#2b2b36"/><path d="m7 9 3 3-3 3M12 15.5h5" stroke="#f5a742" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    nautilus: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#3b82f6"/><path d="M6.5 8.5h4l1.2 1.5h5.8v6.5h-11z" fill="#dbeafe"/>',
    code: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#1f6feb"/><path d="m9.5 8.5-3.5 3.5 3.5 3.5M14.5 8.5 18 12l-3.5 3.5" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    obsidian: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#2a1f45"/><path d="m12 5 5 5-2 8.5H9L7 10z" fill="#a78bfa"/>',
    signal: '<circle cx="12" cy="12" r="10" fill="#3a76f0"/><path d="M12 6.5a5.5 5.5 0 0 0-4.8 8.2L6.5 17.5l2.8-.7A5.5 5.5 0 1 0 12 6.5z" fill="#fff"/>',
  };

  /* Monitor glyph for the rotation choices. */
  const monGlyph = (rot) =>
    `<svg class="glyph rot${rot}" viewBox="0 0 40 40" aria-hidden="true"><rect x="6" y="8" width="28" height="18" rx="2.5"/><path d="M15 32.5h10M20 26v6.5"/><path d="M10.5 12.5h8" stroke-width="2.4"/></svg>`;

  /* An app mark for a window class / icon names ("org.gnome.Nautilus", ["spotify-client", "spotify"]). */
  const appIcon = (names, cls = "app-ic") => {
    const list = (Array.isArray(names) ? names : [names]).map((n) => String(n || "").toLowerCase());
    const hit = Object.keys(APP_IC).find((id) => list.some((n) => n === id || n.split(/[.\-_ ]/).includes(id)));
    const first = (list.find(Boolean) || "?").split(".").pop();
    const body = hit ? APP_IC[hit] : `<rect x="2" y="2" width="20" height="20" rx="5" fill="var(--ctl-hover)"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">${esc(first[0].toUpperCase())}</text>`;
    return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
  };

  /* ================================================================ state */
  const S = { err: {} };
  const UI = { sel: null, open: {}, wtab: "content", busy: 0, pressed: false, camBusy: false, samBusy: false };
  let H = {};           // handlers of the current page render
  let after = [];       // callbacks after the page is in the DOM

  const loaders = {
    screens: async () => { const [list, fixed] = [await api.screens(), await api.fixedStatus()]; S.screens = list; S.fixed = fixed; },
    keys: async () => { S.keys = await api.keys(); },
    look: async () => { S.look = await api.look(); S.lookBase = clone(S.look.values); if (!S.lookDraft || !S.look.previewing) S.lookDraft = clone(S.look.values); },
    sound: async () => { S.sound = await api.soundState(); },
    camera: async () => { S.camera = await api.camera(); },
    samsung: async () => { S.samsung = await api.samsung(); },
    widgets: async () => { const [w, l] = [await api.widgets(), await api.layouts()]; S.widgets = w; S.layouts = l; },
    general: async () => { const [l, a] = [await api.language(), await api.about()]; S.lang = l; S.about = a; },
  };
  /* Load parts of the state; a part that fails keeps its error (the page shows it). */
  const reload = (...names) => Promise.all(names.map(async (n) => {
    try { await loaders[n](); delete S.err[n]; } catch (err) { S.err[n] = err; }
  }));

  /* ================================================================ pages & routing */
  const PAGES = [
    { id: "home", label: () => t("Home"), icon: "home", needs: ["screens", "sound", "samsung", "widgets"] },
    { id: "screens", label: () => t("Screens"), icon: "monitor", needs: ["screens", "keys"] },
    { id: "keys", label: () => t("Keyboard"), icon: "keyboard", needs: ["keys"] },
    { id: "look", label: () => t("Windows"), icon: "window", needs: ["look"] },
    { id: "widgets", label: () => t("Widgets"), icon: "widgets", needs: ["widgets", "screens"] },
    { id: "sound", label: () => t("Sound"), icon: "speaker", needs: ["sound"] },
    { id: "camera", label: () => t("Camera"), icon: "camera", needs: ["camera"] },
    { id: "power", label: () => t("Battery & power"), icon: "battery", needs: ["samsung"], when: () => S.samsung && S.samsung.available },
    { id: "general", label: () => t("General"), icon: "sliders", needs: ["general"] },
  ];
  const pageOf = (id) => PAGES.find((p) => p.id === id);

  function route() {
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    const page = pageOf(parts[0]) ? parts[0] : "home";
    return { page, sub: parts[1] || null };
  }
  const go = (hash) => { if (location.hash !== hash) location.hash = hash; else render(true); };

  /* ================================================================ component helpers */
  const k = (key) => `data-k="${esc(key)}" data-on="${esc(key)}"`;
  const reg = (key, spec) => { H[key] = spec; return k(key); };

  function ph(title, intro, actions = "") {
    return `<header class="ph"><div class="ph-text"><h1>${title}</h1>${intro ? `<p>${intro}</p>` : ""}</div>${actions ? `<div class="ph-actions">${actions}</div>` : ""}</header>`;
  }
  const sec = (title, body, { sub = "", end = "" } = {}) =>
    `<section class="sec"><div class="sec-h"><h2>${title}</h2>${sub ? `<span class="sub">${sub}</span>` : ""}${end ? `<span class="end">${end}</span>` : ""}</div>${body}</section>`;

  function row({ sid, icon, title, desc, end = "", cls = "", extra = "", lead = "" }) {
    return `<div class="row ${cls}"${sid ? ` data-sid="${esc(sid)}"` : ""}>${lead || (icon ? ic(icon) : "")}<div class="row-text"><div class="row-title"><span class="t">${title}</span>${extra}</div>${desc ? `<div class="row-desc">${desc}</div>` : ""}</div>${end ? `<div class="row-end">${end}</div>` : ""}</div>`;
  }
  function block({ sid, icon, title, desc, head = "", body = "", cls = "" }) {
    return `<div class="row block ${cls}"${sid ? ` data-sid="${esc(sid)}"` : ""}><div class="row-head">${icon ? ic(icon) : ""}<div class="row-text"><div class="row-title"><span class="t">${title}</span></div>${desc ? `<div class="row-desc">${desc}</div>` : ""}</div>${head ? `<div class="row-end">${head}</div>` : ""}</div>${body ? `<div class="body">${body}</div>` : ""}</div>`;
  }
  const notice = (icon, html, cls = "") => `<div class="notice ${cls}">${ic(icon)}<p>${html}</p></div>`;

  function toggle(key, on, onChange, { label = "", disabled = false, text = true } = {}) {
    H[key] = { click: () => onChange(!on) };
    return `<button type="button" class="sw" role="switch" aria-checked="${!!on}" aria-label="${esc(label)}"${disabled ? " disabled" : ""} ${k(key)}>${text ? `<span class="sw-label">${on ? t("On") : t("Off")}</span>` : ""}<span class="sw-track"></span></button>`;
  }

  /* Single choice group (segmented, cards, radios, chips) with roving tabindex. */
  function group(key, opts, value, onChange, { cls = "seg", itemCls = "seg-btn", label = "", item, unset = false, disabled = false } = {}) {
    H[key] = { pick: (i) => { if (!eq(opts[i].v, value)) onChange(opts[i].v); } };
    const idx = opts.findIndex((o) => eq(o.v, value));
    const inner = opts.map((o, i) => {
      const on = i === idx;
      const tab = (idx < 0 ? i === 0 : on) ? 0 : -1;
      const body = item ? item(o, on, i) : `${o.icon ? ic(o.icon, "sm") : ""}${esc(o.label)}`;
      return `<button type="button" class="${itemCls}" role="radio" aria-checked="${on}" tabindex="${tab}"${disabled || o.disabled ? " disabled" : ""}${o.title ? ` title="${esc(o.title)}"` : ""}${o.aria ? ` aria-label="${esc(o.aria)}"` : ""} data-on="${esc(key)}" data-k="${esc(key)}:${i}" data-i="${i}">${body}</button>`;
    }).join("");
    return `<div class="${cls}${unset && idx < 0 ? " unset" : ""}" role="radiogroup" aria-label="${esc(label)}">${inner}</div>`;
  }
  const seg = (key, opts, value, onChange, o = {}) => group(key, opts, value, onChange, o);
  const chipsOne = (key, opts, value, onChange, o = {}) =>
    group(key, opts, value, onChange, { cls: "chips", itemCls: "chip", item: (x) => `${x.app ? appIcon(x.app) : x.icon ? ic(x.icon) : ""}${esc(x.label)}`, ...o });
  const radios = (key, opts, value, onChange, o = {}) =>
    group(key, opts, value, onChange, {
      cls: "card radios", itemCls: "radio",
      item: (x) => `<span class="dot"></span><span class="r-l">${esc(x.label)}${x.sub ? `<span class="r-sub">${esc(x.sub)}</span>` : ""}</span>${x.ex ? `<span class="r-ex" data-ex="${esc(x.v)}">${esc(x.ex)}</span>` : ""}`, ...o,
    });
  const tcards = (key, opts, value, onChange, o = {}) =>
    group(key, opts, value, onChange, {
      cls: "tcards", itemCls: "tcard",
      item: (x) => `<div class="tcard-thumb">${x.thumb}</div><div class="tcard-body"><b>${esc(x.label)}${x.sub ? `<small>${esc(x.sub)}</small>` : ""}</b><span class="tick">${ic("check")}</span></div>`, ...o,
    });

  /* Multi-select chips (each one a toggle button). */
  function chipsMulti(key, opts, values, onChange, { label = "", disabled = false } = {}) {
    H[key] = { pick: (i) => onChange(opts[i].v, !values.includes(opts[i].v)) };
    return `<div class="chips" role="group" aria-label="${esc(label)}">${opts.map((o, i) =>
      `<button type="button" class="chip${o.square ? " square" : ""}" aria-pressed="${values.includes(o.v)}"${disabled ? " disabled" : ""}${o.title ? ` title="${esc(o.title)}"` : ""} data-on="${esc(key)}" data-k="${esc(key)}:${i}" data-i="${i}">${o.icon ? ic(o.icon) : ""}${esc(o.label)}</button>`).join("")}</div>`;
  }

  function slider(key, { min, max, step = 1, value, fmt = (v) => v, onInput, onChange, label = "", disabled = false }) {
    H[key] = { input: (v) => onInput && onInput(v), change: (v) => onChange(v), fmt, min, max };
    const v = Math.min(max, Math.max(min, value ?? min));
    const p = ((v - min) / (max - min)) * 100;
    return `<div class="slider"><input type="range" min="${min}" max="${max}" step="${step}" value="${v}" style="--p:${p}%" aria-label="${esc(label)}" aria-valuetext="${esc(fmt(v))}"${disabled ? " disabled" : ""} ${k(key)}><span class="val num" data-val="${esc(key)}">${esc(fmt(v))}</span></div>`;
  }

  /* − value + for small whole-number ranges. */
  function stepper(key, { min, max, step = 1, value, fmt = (v) => nf(v), onChange, label = "", disabled = false }) {
    const set = (v) => { const n = Math.min(max, Math.max(min, v)); if (n !== value) onChange(n); };
    H[`${key}-dn`] = { click: () => set(value - step) };
    H[`${key}-up`] = { click: () => set(value + step) };
    H[key] = { stepKey: (e) => {
      const d = { ArrowUp: step, ArrowRight: step, ArrowDown: -step, ArrowLeft: -step, PageUp: step * 5, PageDown: -step * 5 }[e.key];
      if (d) { e.preventDefault(); set(value + d); return true; }
      if (e.key === "Home") { e.preventDefault(); set(min); return true; }
      if (e.key === "End") { e.preventDefault(); set(max); return true; }
      return false;
    } };
    return `<div class="stepper">
      <button type="button" class="btn icon" tabindex="-1" aria-hidden="true"${disabled || value <= min ? " disabled" : ""} ${k(`${key}-dn`)}>${ic("minus", "sm")}</button>
      <span class="stepper-v num" role="spinbutton" tabindex="${disabled ? -1 : 0}" aria-label="${esc(label)}" aria-valuemin="${min}" aria-valuemax="${max}" aria-valuenow="${value}" aria-valuetext="${esc(fmt(value))}"${disabled ? ' aria-disabled="true"' : ""} ${k(key)}>${esc(fmt(value))}</span>
      <button type="button" class="btn icon" tabindex="-1" aria-hidden="true"${disabled || value >= max ? " disabled" : ""} ${k(`${key}-up`)}>${ic("plus", "sm")}</button>
    </div>`;
  }

  /* Text field: saved on Enter or when it loses focus. */
  function textField(key, { value, onChange, onInput, label = "", placeholder = "", icon = "lyrics", maxLength, disabled = false, width = 300, mono = false }) {
    H[key] = { text: (v) => { if (v !== value) onChange(v); }, typing: onInput };
    return `<label class="field${mono ? " mono" : ""}" style="max-width:${width}px;width:100%">${ic(icon)}<input type="text" value="${esc(value)}" aria-label="${esc(label)}" placeholder="${esc(placeholder)}" spellcheck="false" autocomplete="off"${maxLength ? ` maxlength="${maxLength}"` : ""}${disabled ? " disabled" : ""} ${k(key)}></label>`;
  }

  /* Custom select: a button that opens a listbox popover. */
  function select(key, { options, value, placeholder, onChange, label = "", width, disabled = false }) {
    const cur = options.find((o) => eq(o.v, value));
    H[key] = { select: (el) => openListbox(el, { options, value, onPick: (v) => { if (!eq(v, value)) onChange(v); } }) };
    return `<button type="button" class="select" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(label)}"${disabled ? " disabled" : ""}${width ? ` style="min-width:${width}px"` : ""} ${k(key)}>${cur
      ? `${cur.icon || ""}<span class="sel-v">${esc(cur.label)}</span>${cur.badge ? `<span class="pill">${esc(cur.badge)}</span>` : ""}`
      : `<span class="sel-v ph">${esc(placeholder ?? t("Choose"))}</span>`}${ic("chevD")}</button>`;
  }

  function button(key, inner, onClick, { cls = "btn", attrs = "", label = "" } = {}) {
    H[key] = { click: onClick };
    return `<button type="button" class="${cls}"${label ? ` aria-label="${esc(label)}" title="${esc(label)}"` : ""} ${attrs} ${k(key)}>${inner}</button>`;
  }
  const spinner = () => '<span class="spin" aria-hidden="true"></span>';

  function expander(key, { icon, title, desc, sid }, body) {
    const open = !!UI.open[key];
    H[key] = { click: () => { UI.open[key] = !open; render(); } };
    return `<div class="exp" data-open="${open}"${sid ? ` data-sid="${esc(sid)}"` : ""}><div class="row" role="button" tabindex="0" aria-expanded="${open}" ${k(key)}>${ic(icon)}<div class="row-text"><div class="row-title"><span class="t">${title}</span></div>${desc ? `<div class="row-desc">${desc}</div>` : ""}</div>${ic("chevD", "exp-chev")}</div>${open ? `<div class="exp-body">${body}</div>` : ""}</div>`;
  }

  /* ================================================================ change / toast / undo */
  /* Runs apply(); reloads `names`; then a toast with undo, or the "keep it?" dialog
   * when confirm (true or a function of the result) says so. Errors become a toast. */
  async function change(apply, revert, { reload: names = [], confirm = false, msg, keepTitle } = {}) {
    let result;
    UI.busy += 1;
    try { result = await apply(); }
    catch (err) {
      if (err && err.code === "apply_failed" && names.length) await reload(...names);
      UI.busy -= 1;
      render();
      showError(err);
      return undefined;
    }
    await reload(...names);
    UI.busy -= 1;
    render();
    const undo = revert ? async () => {
      UI.busy += 1;
      try { await revert(result); } catch (err) { showError(err); }
      await reload(...names);
      UI.busy -= 1;
      render();
    } : null;
    if (typeof confirm === "function" ? confirm(result) : confirm) keepDialog(undo, keepTitle);
    else if (msg !== false) toast(typeof msg === "function" ? msg(result) : msg || t("Saved"), undo);
    return result;
  }
  const showError = (err) => toast(errText(err), null, { error: true });

  let toastTimer = 0;
  function toast(msg, undo, { error = false, action = null } = {}) {
    const el = $("#toast");
    const extra = undo ? `<span class="sep"></span><button type="button" class="btn ghost" id="toast-act">${ic("undo", "sm")}${esc(t("Undo"))}</button>`
      : action ? `<span class="sep"></span><button type="button" class="btn ghost" id="toast-act">${esc(action.label)}</button>` : "";
    el.innerHTML = `${ic(error ? "alert" : "check", error ? "err" : "ok")}<span>${esc(msg)}</span>${extra}`;
    el.classList.toggle("error", error);
    el.setAttribute("role", error ? "alert" : "status");
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), undo || action ? 6000 : error ? 5000 : 3000);
    const b = $("#toast-act");
    if (b) b.onclick = async () => {
      el.classList.remove("show");
      if (undo) { await undo(); toast(t("Undone")); } else action.run();
    };
  }

  /* ================================================================ dialog */
  const dlg = $("#dialog");
  let dlgCleanup = null;
  let dlgReturn = null;
  function openDialog(html, actions, { onCancel, onKey, focus, label } = {}) {
    if (dlg.open) closeDialog();
    dlgReturn = document.activeElement;
    $("#toast").classList.remove("show");
    Pop.close(false);
    dlg.innerHTML = html;
    const h = $("h2", dlg);
    if (h) { h.id = "dlg-title"; dlg.setAttribute("aria-labelledby", "dlg-title"); } else dlg.removeAttribute("aria-labelledby");
    if (label) dlg.setAttribute("aria-label", label); else dlg.removeAttribute("aria-label");
    dlg.onclick = (e) => {
      const b = e.target.closest("[data-d]");
      if (b && !b.disabled && actions[b.dataset.d]) actions[b.dataset.d](b);
    };
    dlg.oncancel = (e) => { e.preventDefault(); onCancel ? onCancel() : closeDialog(); };
    dlg.onkeydown = onKey || null;
    dlg.showModal();
    const f = focus ? $(focus, dlg) : $("[autofocus]", dlg);
    if (f) f.focus();
  }
  function closeDialog() {
    if (dlgCleanup) { const c = dlgCleanup; dlgCleanup = null; c(); }
    dlg.onkeyup = null;
    if (dlg.open) dlg.close();
    const r = dlgReturn;
    dlgReturn = null;
    if (r && document.contains(r)) r.focus({ preventScroll: true });
    else if (r && r.dataset && r.dataset.k) { const el = $(`[data-k="${CSS.escape(r.dataset.k)}"]`); if (el) el.focus({ preventScroll: true }); }
  }

  /* "Keep this?" with a 15 s countdown; going back runs `undo`. */
  function keepDialog(undo, title) {
    const total = 15;
    let n = total;
    const C = 2 * Math.PI * 19;
    const draw = () => {
      const ring = $(".count-ring .fg", dlg);
      if (ring) ring.style.strokeDashoffset = String(C * (1 - n / total));
      const a = $("#keep-n", dlg); if (a) a.textContent = n;
      const b = $("#keep-s", dlg); if (b) b.textContent = n;
    };
    const back = async () => { closeDialog(); if (undo) await undo(); toast(t("Reverted")); };
    openDialog(`
      <div class="dlg-body">
        <h2>${esc(title || t("Keep this display setting?"))}</h2>
        <div class="count-ring"><span class="wrap"><svg viewBox="0 0 44 44" aria-hidden="true"><circle class="bg" cx="22" cy="22" r="19"/><circle class="fg" cx="22" cy="22" r="19" stroke-dasharray="${C}" stroke-dashoffset="0"/></svg><span class="n" id="keep-n" aria-hidden="true">${n}</span></span>
        <p style="margin:0">${tHtml("Goes back in {seconds} s unless you press something.", "seconds", `<span class="num" id="keep-s">${n}</span>`)}</p></div>
      </div>
      <div class="dlg-foot">
        <button type="button" class="btn" data-d="revert">${esc(t("Revert"))}</button>
        <button type="button" class="btn primary" data-d="keep" autofocus>${esc(t("Keep"))}</button>
      </div>`, {
      keep: () => { closeDialog(); toast(t("Saved")); },
      revert: back,
    }, { onCancel: back });
    const timer = setInterval(() => {
      n -= 1; draw();
      if (n <= 0) back();
    }, 1000);
    dlgCleanup = () => clearInterval(timer);
  }

  function confirmDialog({ title, text, ok, danger = false }) {
    return new Promise((resolve) => {
      openDialog(`
        <div class="dlg-body"><h2>${esc(title)}</h2><p>${esc(text)}</p></div>
        <div class="dlg-foot">
          <button type="button" class="btn" data-d="no" autofocus>${esc(t("Cancel"))}</button>
          <button type="button" class="btn ${danger ? "danger solid" : "primary"}" data-d="yes">${esc(ok)}</button>
        </div>`, {
        yes: () => { closeDialog(); resolve(true); },
        no: () => { closeDialog(); resolve(false); },
      }, { onCancel: () => { closeDialog(); resolve(false); } });
    });
  }

  /* ================================================================ popover / listbox */
  const pop = $("#popover");
  const Pop = {
    anchor: null, onKey: null,
    open(anchor, html, { onKey, onClick, minWidth = true, keepFocus = false, label = "" } = {}) {
      this.close(false);
      this.anchor = anchor;
      this.onKey = onKey || null;
      pop.innerHTML = html;
      pop.onclick = onClick || null;
      if (label) pop.setAttribute("aria-label", label); else pop.removeAttribute("aria-label");
      pop.hidden = false;
      this.place(minWidth);
      if (anchor.hasAttribute("aria-expanded")) anchor.setAttribute("aria-expanded", "true");
      if (!keepFocus) { const f = $(".lb", pop) || $("input, button", pop); if (f) f.focus({ preventScroll: true }); }
    },
    place(minWidth = true) {
      if (!this.anchor) return;
      const r = this.anchor.getBoundingClientRect();
      pop.style.minWidth = minWidth ? `${Math.max(200, r.width)}px` : "";
      pop.style.left = "0px"; pop.style.top = "0px";
      const pr = pop.getBoundingClientRect();
      let top = r.bottom + 4;
      if (top + pr.height > innerHeight - 8) top = Math.max(8, r.top - pr.height - 4);
      let left = r.left;
      if (left + pr.width > innerWidth - 8) left = Math.max(8, innerWidth - 8 - pr.width);
      pop.style.left = `${left}px`; pop.style.top = `${top}px`;
    },
    close(refocus = true) {
      if (pop.hidden) return;
      pop.hidden = true;
      pop.innerHTML = "";
      const a = this.anchor;
      this.anchor = null; this.onKey = null;
      if (a) {
        if (a.hasAttribute("aria-expanded")) a.setAttribute("aria-expanded", "false");
        if (refocus && document.contains(a)) a.focus({ preventScroll: true });
      }
    },
    get isOpen() { return !pop.hidden; },
  };

  /* options: [{v,label,sub,badge,icon,checked,sep,head}] */
  function openListbox(anchor, { options, value, onPick, multi = false, header = "", keepFocus = false, footer = "", onFooter }) {
    const usable = (i) => options[i] && !options[i].sep && !options[i].head && !options[i].disabled;
    let active = options.findIndex((o, i) => usable(i) && (multi ? o.checked : eq(o.v, value)));
    if (active < 0) active = options.findIndex((_, i) => usable(i));
    const label = header || anchor.getAttribute("aria-label") || "";
    const html = () => `${header ? `<div class="pop-h">${esc(header)}</div>` : ""}<div class="lb" role="listbox" tabindex="-1" aria-label="${esc(label)}"${multi ? ' aria-multiselectable="true"' : ""} aria-activedescendant="opt-${active}">${options.map((o, i) => {
      if (o.sep) return '<div class="pop-sep" role="separator"></div>';
      if (o.head) return `<div class="pop-h" role="presentation">${esc(o.head)}</div>`;
      const sel = multi ? !!o.checked : eq(o.v, value);
      return `<div class="opt${i === active ? " active" : ""}" role="option" id="opt-${i}" data-i="${i}" aria-selected="${sel}"${o.disabled ? ' aria-disabled="true"' : ""}${multi ? ` aria-checked="${sel}"` : ""}>${multi ? `<span class="chk">${ic("check")}</span>` : ""}${o.icon || ""}<span class="opt-l">${esc(o.label)}${o.sub ? ` <span class="opt-sub">· ${esc(o.sub)}</span>` : ""}</span>${o.badge ? `<span class="pill">${esc(o.badge)}</span>` : ""}</div>`;
    }).join("")}</div>${footer}`;
    const redraw = () => {
      const lb = $(".lb", pop);
      const st = lb ? lb.scrollTop : 0;
      pop.innerHTML = html();
      const nlb = $(".lb", pop);
      nlb.scrollTop = st;
      if (!keepFocus) nlb.focus({ preventScroll: true });
      scrollActive();
    };
    const scrollActive = () => { const a = $(`#opt-${active}`, pop); if (a) a.scrollIntoView({ block: "nearest" }); };
    const pick = (i) => {
      if (!usable(i)) return;
      if (multi) {
        const next = onPick(options[i].v);
        if (next) { options = next; redraw(); }
      } else { Pop.close(); onPick(options[i].v); }
    };
    const move = (d) => {
      let i = active;
      for (let n = 0; n < options.length; n++) { i = (i + d + options.length) % options.length; if (usable(i)) break; }
      active = i;
      $$(".opt", pop).forEach((el) => el.classList.toggle("active", +el.dataset.i === active));
      $(".lb", pop).setAttribute("aria-activedescendant", `opt-${active}`);
      if (keepFocus) anchor.querySelector("input")?.setAttribute("aria-activedescendant", `opt-${active}`);
      scrollActive();
    };
    let typed = "", typedT = 0;
    Pop.open(anchor, html(), {
      keepFocus, label,
      onClick: (e) => {
        const o = e.target.closest(".opt");
        if (o) pick(+o.dataset.i);
        const f = e.target.closest("[data-pf]");
        if (f && onFooter) onFooter(f.dataset.pf);
      },
      onKey: (e) => {
        if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
        else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
        else if (e.key === "Home" && !keepFocus) { e.preventDefault(); active = -1; move(1); }
        else if (e.key === "End" && !keepFocus) { e.preventDefault(); active = 0; move(-1); }
        else if (e.key === "Enter" || (e.key === " " && !keepFocus)) { e.preventDefault(); pick(active); }
        else if (e.key === "Tab") { Pop.close(false); }
        else if (!keepFocus && e.key.length === 1) {
          clearTimeout(typedT); typed += e.key.toLowerCase(); typedT = setTimeout(() => (typed = ""), 600);
          const i = options.findIndex((o, j) => usable(j) && String(o.label).toLowerCase().startsWith(typed));
          if (i >= 0) { active = i - 1; move(1); }
        } else return false;
        return true;
      },
    });
    scrollActive();
    return { move, pick: () => pick(active), get active() { return active; } };
  }

  /* ================================================================ screens model */
  const scr = (id) => (S.screens || []).find((s) => s.id === id);
  const conn = () => (S.screens || []).filter((s) => s.connected && s.position);
  const laptopId = () => ((S.screens || []).find((s) => s.laptop) || (S.screens || [])[0] || {}).id;
  const sname = (s) => (s ? (s.laptop ? t("Laptop") : s.name) : "?");
  const parseMode = (m) => { const [wh, r] = String(m).split("@"); const [w, h] = wh.split("x").map(Number); return { w, h, rate: Number(r) }; };
  const res = (w, h) => `${w}${NB}×${NB}${h}`;
  const OPP = { left: "right", right: "left", above: "below", below: "above" };
  const ROT = () => [
    { v: 0, label: t("Normal") }, { v: 90, label: t("Portrait, right") },
    { v: 180, label: t("Upside down") }, { v: 270, label: t("Portrait, left") },
  ];
  const SIDES = () => [
    { v: "left", label: t("Left") }, { v: "above", label: t("Above") },
    { v: "below", label: t("Below") }, { v: "right", label: t("Right") },
  ];
  const sideText = (side) => ({ left: t("Left of the laptop"), right: t("Right of the laptop"), above: t("Above the laptop"), below: t("Below the laptop") })[side] || "";
  const SCALES = () => [{ v: "auto", label: t("Auto") }, ...[1, 1.25, 1.5, 2].map((v) => ({ v, label: pct(v * 100) }))];
  const scaleLabel = (v) => (v === "auto" ? t("Auto") : pct(Math.round(v * 100)));
  const rotLabel = (v) => (ROT().find((o) => o.v === v) || { label: `${v}°` }).label;

  /* Which side of `anchor` a rectangle is on, by their middles (as api.side_of). */
  function sideOf(r, a) {
    const dx = ((r.x + r.w / 2) - (a.x + a.w / 2)) / Math.max(1, (r.w + a.w) / 2);
    const dy = ((r.y + r.h / 2) - (a.y + a.h / 2)) / Math.max(1, (r.h + a.h) / 2);
    if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? "right" : "left";
    return dy > 0 ? "below" : "above";
  }
  /* Edge to edge with `a` on `side`, centred along that edge (as apply.layout). */
  function placeBeside(size, a, side) {
    const { w, h } = size;
    return {
      left: { x: a.x - w, y: a.y + (a.h - h) / 2 }, right: { x: a.x + a.w, y: a.y + (a.h - h) / 2 },
      above: { x: a.x + (a.w - w) / 2, y: a.y - h }, below: { x: a.x + (a.w - w) / 2, y: a.y + a.h },
    }[side];
  }
  /* Dropping screen `s` with its top-left at `want`: whose side changes, to what, and where it lands. */
  function dropOf(s, want) {
    const live = conn();
    const others = live.filter((x) => x.id !== s.id).sort((a, b) => a.connector.localeCompare(b.connector));
    const lap = live.find((x) => x.laptop);
    const anchor = lap || others[0];
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
  const canDrag = (s) => conn().length > 1 && (!s.laptop || conn().length === 2);
  function sharedEdges(rects) {
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

  /* Arrangement canvas: positions are computed after the page is in the DOM. */
  const Arr = { f: 0, ox: 0, oy: 0 };
  const GAP = 3;
  const rectOf = (s) => ({ id: s.id, ...s.position });
  function layoutArrange() {
    const cv = $("#arrange");
    if (!cv) return;
    const rects = conn().map(rectOf);
    if (!rects.length) return;
    const minX = Math.min(...rects.map((r) => r.x)), minY = Math.min(...rects.map((r) => r.y));
    const maxX = Math.max(...rects.map((r) => r.x + r.w)), maxY = Math.max(...rects.map((r) => r.y + r.h));
    const pad = 32;
    const W = cv.clientWidth - pad * 2, Hh = cv.clientHeight - pad * 2;
    Arr.f = Math.min(W / (maxX - minX), Hh / (maxY - minY), 0.14);
    Arr.ox = (cv.clientWidth - (maxX - minX) * Arr.f) / 2 - minX * Arr.f;
    Arr.oy = (cv.clientHeight - (maxY - minY) * Arr.f) / 2 - minY * Arr.f;
    for (const r of rects) placeTile(cv, r);
    drawEdges(cv, rects);
  }
  function placeTile(cv, r) {
    const el = $(`.scr[data-scr="${CSS.escape(r.id)}"]`, cv);
    if (!el) return;
    el.style.left = `${r.x * Arr.f + Arr.ox + GAP}px`;
    el.style.top = `${r.y * Arr.f + Arr.oy + GAP}px`;
    el.style.width = `${r.w * Arr.f - GAP * 2}px`;
    el.style.height = `${r.h * Arr.f - GAP * 2}px`;
    el.classList.toggle("tight", r.h * Arr.f < 100);
    el.classList.toggle("tiny", r.h * Arr.f < 72);
  }
  function drawEdges(cv, rects) {
    $$(".edge", cv).forEach((e) => e.remove());
    for (const e of sharedEdges(rects)) {
      const d = document.createElement("div");
      d.className = "edge";
      if (e.v) Object.assign(d.style, { left: `${e.x * Arr.f + Arr.ox - 2}px`, top: `${e.y1 * Arr.f + Arr.oy + 10}px`, width: "4px", height: `${Math.max(0, (e.y2 - e.y1) * Arr.f - 20)}px` });
      else Object.assign(d.style, { top: `${e.y * Arr.f + Arr.oy - 2}px`, left: `${e.x1 * Arr.f + Arr.ox + 10}px`, height: "4px", width: `${Math.max(0, (e.x2 - e.x1) * Arr.f - 20)}px` });
      cv.appendChild(d);
    }
  }
  function bindArrange() {
    const cv = $("#arrange");
    if (!cv) return;
    layoutArrange();
    let drag = null;
    let suppress = false;
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
      drag.want = { x: drag.pos0.x + dx / Arr.f, y: drag.pos0.y + dy / Arr.f };
      drag.drop = dropOf(drag.s, drag.want);
      if (!drag.drop) return;
      // show where it will land: edge to edge, centred
      const r = { id: drag.s.id, ...drag.drop.spot, w: drag.s.position.w, h: drag.s.position.h };
      placeTile(cv, r);
      drawEdges(cv, conn().map((s) => (s.id === drag.s.id ? r : rectOf(s))));
    });
    const end = () => {
      if (!drag) return;
      const d = drag; drag = null;
      d.el.classList.remove("drag");
      if (!d.moved) return;
      suppress = true;
      setTimeout(() => (suppress = false), 0);
      UI.sel = d.s.id;
      if (!d.drop || d.drop.side === d.drop.target.side) { render(); return; }
      const target = d.drop.target, old = clone(target.settings.position);
      change(() => api.setScreenSetting(d.s.id, "position", { x: Math.round(d.want.x), y: Math.round(d.want.y) }),
        () => api.setScreenSetting(target.id, "position", old.value, old.value == null ? [] : old.when),
        { reload: ["screens"], confirm: (r) => r && r.applied && r.applied.length > 0 });
    };
    cv.addEventListener("pointerup", end);
    cv.addEventListener("pointercancel", end);
    cv.addEventListener("click", (e) => {
      const el = e.target.closest(".scr");
      if (!el || suppress) return;
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
      const target = s.laptop ? conn().find((x) => x.id !== s.id) : s;
      const want = s.laptop ? OPP[side] : side;
      if (target.side === want) { render(); return; }
      setScreen(target, "position", want);
    });
  }

  /* ================================================================ page: Screens */
  function setScreen(s, key, value, when = null) {
    const old = clone(s.settings[key]);
    return change(
      () => api.setScreenSetting(s.id, key, value, when),
      () => api.setScreenSetting(s.id, key, old.value, old.value == null ? [] : old.when),
      { reload: ["screens"], confirm: (r) => key !== "one_desktop" && r && r.applied && r.applied.length > 0 },
    );
  }

  /* "Always" / "Only with <screen>": one other screen at most. */
  function whenChip(s, key) {
    const st = s.settings[key];
    if (st.value == null) return "";
    const other = st.when.length ? scr(st.when[0]) : null;
    const label = !st.when.length ? t("Always") : t("Only with {name}", { name: other ? sname(other) : st.when[0] });
    const keyName = `when-${key}`;
    H[keyName] = {
      select: (el) => openListbox(el, {
        header: t("Applies"),
        value: st.when[0] || "",
        options: [
          { v: "", label: t("Always") },
          { head: t("Only while this one is connected:") },
          ...S.screens.filter((o) => o.id !== s.id).map((o) => ({ v: o.id, label: sname(o), sub: o.connected ? "" : t("not connected") })),
        ],
        onPick: (v) => { if (v !== (st.when[0] || "")) setScreen(s, key, st.value, v ? [v] : []); },
      }),
    };
    return `<button type="button" class="when${st.when.length ? " on" : ""}" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(t("Applies: {when}", { when: label }))}" title="${esc(t("When does this setting apply?"))}" ${k(keyName)}><span>${esc(label)}</span>${ic("chevD")}</button>`;
  }
  function settingHead(s, key, hyprText) {
    const st = s.settings[key];
    const resetKey = `reset-${key}`;
    H[resetKey] = { click: () => setScreen(s, key, null) };
    let left;
    if (st.value == null) left = `<span class="unset-note">${esc(hyprText ? t("Not set · Hyprland: {value}", { value: hyprText }) : t("Not set"))}</span>`;
    else left = `${st.active || !s.connected ? "" : `<span class="pill neutral" title="${esc(t("Its screen is not connected now"))}">${esc(t("Not in force now"))}</span>`}<button type="button" class="link" ${k(resetKey)}>${esc(t("Reset"))}</button>`;
    return `${left}${whenChip(s, key)}`;
  }

  function pageScreens() {
    if (!scr(UI.sel)) UI.sel = laptopId();
    const sel = scr(UI.sel);
    const cs = conn(), known = S.screens.filter((s) => !s.connected);
    const fx = S.fixed || {};
    const swap = fx.canSwap
      ? button("swap", `${ic("swap", "sm")}${esc(t("Swap the fixed screen"))}`, () =>
        change(() => api.swapFixed(), () => api.swapFixed(), { reload: ["screens"], msg: t("Swapped until the monitor is unplugged") }), { attrs: 'data-sid="screens.swap"' })
      : "";

    const tiles = cs.map((s) => {
      const isFixed = fx.fixed === s.id && cs.length > 1;
      const tip = !canDrag(s) ? (cs.length > 1 ? t("Drag one of the other screens: the laptop stays where it is") : "") : t("Drag to arrange · arrow keys put it next to the laptop");
      return `<button type="button" class="scr${s.id === UI.sel ? " sel" : ""}" data-scr="${esc(s.id)}" aria-pressed="${s.id === UI.sel}" aria-label="${esc(sname(s))}${isFixed ? `, ${esc(t("fixed"))}` : ""}"${tip ? ` title="${esc(tip)}"` : ""}>
        ${ic(s.laptop ? "laptop" : "monitor", "glyph-ic")}
        <span class="n">${esc(sname(s))}</span><span class="m">${res(s.position.w, s.position.h)}</span>
        ${isFixed ? `<span class="pill fixed-badge">${ic("pin")}${esc(t("Fixed"))}</span>` : ""}</button>`;
    }).join("");
    const knownStrip = known.length ? `<div class="known"><span class="known-h">${esc(t("Known screens"))}</span>${known.map((s) => {
      const m = s.modes.find((x) => x.preferred) || s.modes[0] || { w: 16, h: 9 };
      const w = 26, h = Math.round((26 * m.h) / m.w);
      const key = `known-${s.id}`;
      H[key] = { click: () => { UI.sel = s.id; render(); } };
      return `<button type="button" class="kscr${s.id === UI.sel ? " sel" : ""}" aria-pressed="${s.id === UI.sel}" ${k(key)}><span class="mini" style="width:${w}px;height:${h}px"></span><span><b>${esc(sname(s))}</b><small>${m.w ? res(m.w, m.h) : ""}</small></span>${s.favorite ? `<span title="${esc(t("Favorite"))}">${ic("star", "xs")}</span>` : ""}</button>`;
    }).join("")}</div>` : "";

    const arrange = `<div class="card arr-card" data-sid="screens.arrange">
      <div class="arr-bar"><span class="hint">${ic("drag", "sm")}${esc(cs.length > 1 ? t("Drag to arrange · click to select") : t("Only one screen is connected"))}</span>${fx.swapped ? `<span class="pill">${esc(t("Swapped"))}</span>` : ""}${swap}</div>
      <div class="arrange" id="arrange">${tiles}</div>${knownStrip}</div>`;

    /* the selected screen */
    const live = sel.hypr ? parseMode(sel.hypr.mode) : null;
    const pref = sel.modes.find((m) => m.preferred) || sel.modes[0];
    const curVal = sel.settings.mode.value;
    const cur = curVal && curVal !== "preferred" ? parseMode(curVal) : null;
    const shownSize = cur || (curVal === "preferred" ? pref : live);
    const grp = shownSize ? sel.modes.find((m) => m.w === shownSize.w && m.h === shownSize.h) : null;
    const modeOpts = [
      ...(pref ? [{ v: "preferred", label: t("What the screen prefers"), sub: res(pref.w, pref.h) }, { sep: true }] : []),
      ...sel.modes.map((m) => ({ v: `${m.w}x${m.h}`, label: res(m.w, m.h), badge: m.preferred ? t("Recommended") : "", sub: `${m.rates.map((r) => nf(r, 2)).join(" / ")}${NB}Hz` })),
    ];

    const pills = fx.fixed === sel.id && cs.length > 1 ? `<span class="pill">${ic("pin")}${esc(t("Fixed now"))}</span>` : "";
    const head = `<div class="scr-head">
      <span class="icon-tile">${ic(sel.laptop ? "laptop" : "monitor")}</span>
      <div><h2>${esc(sname(sel))}</h2><div class="meta"><span class="state-dot${sel.connected ? "" : " off"}"></span>${esc(sel.connected ? t("Connected") : t("Not connected"))}<span class="dotsep"></span><span class="mono">${esc(sel.connector)}</span>${pref ? `<span class="dotsep"></span><span class="num">${res(pref.w, pref.h)}</span>` : ""}${sel.description && !sel.laptop ? `<span class="dotsep"></span><span class="desc" title="${esc(sel.description)}">${esc(sel.description)}</span>` : ""}</div></div>
      <div class="end">${pills}</div>
    </div>`;
    const off = sel.connected ? "" : `<div style="margin-bottom:var(--s1)">${notice("info", esc(sel.lastSeen ? t("Not connected (last seen {date}). The settings apply as soon as it is back.", { date: new Date(sel.lastSeen).toLocaleDateString(loc()) }) : t("Not connected. The settings apply as soon as it is back.")))}</div>`;

    const rot = block({
      sid: "screens.rotation", icon: "rotate", title: esc(t("Rotation")),
      head: settingHead(sel, "rotation", sel.hypr ? rotLabel(sel.hypr.rotation) : ""),
      body: group("rot", ROT(), sel.settings.rotation.value, (v) => setScreen(sel, "rotation", v), {
        cls: "choices", itemCls: "choice", label: t("Rotation"),
        item: (o) => `<span class="tick">${ic("check")}</span>${monGlyph(o.v)}<span>${esc(o.label)}</span>`,
      }),
    });
    const scaleOpts = SCALES();
    const sv = sel.settings.scale.value;
    if (sv != null && !scaleOpts.some((o) => o.v === sv)) scaleOpts.push({ v: sv, label: scaleLabel(sv) });
    const scale = block({
      sid: "screens.scale", icon: "scale", title: esc(t("Scale")), desc: esc(t("Makes text and windows bigger or smaller")),
      head: settingHead(sel, "scale", sel.hypr ? scaleLabel(sel.hypr.scale) : ""),
      body: seg("scale", scaleOpts, sv, (v) => setScreen(sel, "scale", v), { label: t("Scale"), unset: true }),
    });
    const rates = grp ? grp.rates.map((r, i) => ({ v: grp.modes[i], label: hz(r) })) : [];
    const mode = block({
      sid: "screens.mode", icon: "resolution", title: esc(t("Resolution")),
      head: settingHead(sel, "mode", live ? `${res(live.w, live.h)} @ ${hz(live.rate)}` : ""),
      body: `<div class="mode-ctl">
        ${select("mode", {
          options: modeOpts, value: curVal === "preferred" ? "preferred" : cur ? `${cur.w}x${cur.h}` : null, label: t("Resolution"), width: 260,
          placeholder: live ? t("From Hyprland · {mode}", { mode: res(live.w, live.h) }) : t("Not set"),
          onChange: (v) => {
            if (v === "preferred") { setScreen(sel, "mode", "preferred"); return; }
            const m = sel.modes.find((x) => `${x.w}x${x.h}` === v);
            setScreen(sel, "mode", m.modes[m.rates.indexOf(Math.max(...m.rates))]);
          },
        })}
        ${rates.length > 1 || (rates.length && cur) ? group("rate", rates, cur && grp ? curVal : null, (m) => setScreen(sel, "mode", m), { cls: "chips", itemCls: "chip", label: t("Refresh rate"), item: (o) => `${ic("hz")}<span class="num">${esc(o.label)}</span>` }) : ""}
      </div>`,
    });
    const position = sel.laptop ? "" : block({
      sid: "screens.position", icon: "arrange", title: esc(t("Position")), desc: esc(sel.side ? sideText(sel.side) : t("Next to the laptop")),
      head: settingHead(sel, "position", ""),
      body: seg("side", SIDES(), sel.settings.position.value, (v) => setScreen(sel, "position", v), { label: t("Position"), unset: true }),
    });
    const od = sel.settings.one_desktop;
    const one = row({
      sid: "screens.one", icon: "pin", title: esc(t("Always shows the same desktop")),
      desc: esc(od.value == null ? t("Not set · follows “For new monitors”") : od.value ? t("Stays fixed; the other screen has the desktops 1–10") : t("Has its own desktops")),
      end: `${od.value != null ? `<button type="button" class="link" ${reg("reset-od", { click: () => setScreen(sel, "one_desktop", null) })}>${esc(t("Reset"))}</button>` : ""}${whenChip(sel, "one_desktop")}${toggle("od", !!od.value, (v) => setScreen(sel, "one_desktop", v), { label: t("Always shows the same desktop") })}`,
    });

    const adv = expander("scr-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("New monitors, favorite, forget")) }, [
      row({
        sid: "screens.newmon", cls: "sub", title: esc(t("For new monitors")), desc: esc(t("Which screen becomes fixed when an unknown monitor arrives")),
        end: seg("newmon", [{ v: "off", label: t("Off") }, { v: "external", label: t("External monitor") }, { v: "panel", label: t("Laptop") }], S.keys.options.default_fixed, (v) => {
          const old = S.keys.options.default_fixed;
          change(() => api.setOption("default_fixed", v), () => api.setOption("default_fixed", old), { reload: ["keys", "screens"] });
        }, { label: t("For new monitors") }),
      }),
      row({
        sid: "screens.fav", cls: "sub", title: esc(t("Favorite")), desc: esc(t("Comes first in the list and in the tray")),
        end: toggle("fav", sel.favorite, () => change(() => api.toggleFavorite(sel.id), () => api.toggleFavorite(sel.id), { reload: ["screens"] }), { label: t("Favorite") }),
      }),
      row({
        sid: "screens.forget", cls: "sub", title: esc(t("Forget this screen")),
        desc: esc(sel.laptop ? t("The laptop screen cannot be forgotten") : sel.connected ? t("Only possible while it is not connected") : t("Deletes all settings of this screen")),
        end: button("forget", `${ic("trash", "sm")}${esc(t("Forget"))}`, async () => {
          const ok = await confirmDialog({ title: t("Forget “{name}”?", { name: sname(sel) }), text: t("All settings of this screen are deleted. If you connect it again, it starts like new."), ok: t("Forget"), danger: true });
          if (!ok) return;
          const name = sname(sel);
          await change(() => api.forgetScreen(sel.id), null, { reload: ["screens"], msg: t("“{name}” forgotten", { name }) });
          if (!scr(UI.sel)) { UI.sel = laptopId(); render(); }
        }, { cls: "btn danger", attrs: sel.connected || sel.laptop ? "disabled" : "" }),
      }),
    ].join(""));

    after.push(bindArrange);
    return `${ph(esc(t("Screens")), esc(t("Drag the screens to where they stand on your desk.")))}
      ${arrange}
      ${head}${off}
      <div class="stack">${position}${rot}${scale}${mode}${one}</div>
      <div class="stack" style="margin-top:var(--s1)">${adv}</div>`;
  }

  /* ================================================================ page: Keyboard */
  const KEY_ICON = { stash: "minimize", stash_others: "minOthers", pop: "restore", pop_all: "restoreAll", undo: "undo", minimizer_menu: "list" };
  const keyName = (p) => ({ SUPER: "Super", SHIFT: "Shift", CTRL: t("Ctrl"), CONTROL: t("Ctrl"), ALT: "Alt", PERIOD: ".", COMMA: ",", SLASH: "/", MINUS: "-", RETURN: "Enter", SPACE: t("Space"), TAB: "Tab", LEFT: "←", RIGHT: "→", UP: "↑", DOWN: "↓", BACKSPACE: "⌫", DELETE: t("Del"), ESCAPE: "Esc" })[p] || p;
  const caps = (combo) => `<span class="keys">${combo.split(/\s*\+\s*/).map((p) => `<kbd>${esc(keyName(p))}</kbd>`).join('<span class="plus">+</span>')}</span>`;
  const comboText = (combo) => combo.split(/\s*\+\s*/).map(keyName).join(" + ");

  function comboFrom(e) {
    const mods = [];
    if (e.metaKey || e.getModifierState("OS") || e.getModifierState("Super") || e.getModifierState("Meta")) mods.push("SUPER");
    if (e.ctrlKey) mods.push("CTRL");
    if (e.altKey) mods.push("ALT");
    if (e.shiftKey) mods.push("SHIFT");
    const c = e.code;
    let key = null;
    if (/^Key[A-Z]$/.test(c)) key = c.slice(3);
    else if (/^Digit\d$/.test(c)) key = c.slice(5);
    else if (/^F\d{1,2}$/.test(c)) key = c;
    else key = ({ Period: "PERIOD", Comma: "COMMA", Slash: "SLASH", Minus: "MINUS", Space: "SPACE", Enter: "RETURN", Tab: "TAB", ArrowLeft: "LEFT", ArrowRight: "RIGHT", ArrowUp: "UP", ArrowDown: "DOWN", Delete: "DELETE", Backspace: "BACKSPACE", Home: "HOME", End: "END", PageUp: "PAGEUP", PageDown: "PAGEDOWN" })[c] || null;
    return { mods, key, combo: key ? [...mods, key].join(" + ") : null };
  }

  function captureDialog(action, slot) {
    const a = S.keys.actions.find((x) => x.id === action);
    const old = a.slots[slot];
    let combo = null, held = [];
    /* Hyprland gets an empty keymap while the dialog records (Super+Q must reach us). */
    api.beginKeyCapture().catch(() => {});
    const conflict = () => {
      if (!combo) return "";
      const other = S.keys.actions.find((x) => x.id !== action && x.slots.includes(combo)) || (a.slots[1 - slot] === combo ? a : null);
      if (other) return notice("alert", `${esc(t("Already used by “{action}”.", { action: t(other.title) }))}<small>${esc(t("Taking it over removes it there."))}</small>`, "warn");
      const h = S.keys.hyprBinds[combo];
      if (h) return notice("alert", `${esc(t("Hyprland uses it for “{action}”.", { action: t(h) }))}<small>${esc(t("Taking it over replaces that while hypr-screens runs."))}</small>`, "warn");
      return "";
    };
    const capInner = () => combo ? caps(combo)
      : held.length ? `<span class="keys">${held.map((m) => `<kbd>${esc(keyName(m))}</kbd>`).join('<span class="plus">+</span>')}<span class="plus">+ …</span></span>`
      : `<span class="wait"><span class="blink"></span>${esc(t("Waiting for keys …"))}</span>`;
    const draw = () => {
      const cap = $("#cap", dlg);
      cap.innerHTML = capInner();
      cap.classList.toggle("live", !!(combo || held.length));
      $("#cap-conf", dlg).innerHTML = conflict();
      $('[data-d="ok"]', dlg).disabled = !combo || combo === old;
    };
    const apply = async () => {
      const before = clone(S.keys.actions);
      const chosen = combo;
      closeDialog();
      await change(() => api.setKey(action, slot, chosen), async () => {
        for (const b of before) for (let i = 0; i < b.slots.length; i++) await api.setKey(b.id, i, b.slots[i]);
      }, { reload: ["keys"], msg: (r) => (r && r.conflicts && r.conflicts.length ? t("Saved · replaces Hyprland’s {keys} while hypr-screens runs", { keys: r.conflicts.map(comboText).join(", ") }) : t("Saved")) });
    };
    const remove = async () => {
      closeDialog();
      await change(() => api.setKey(action, slot, ""), () => api.setKey(action, slot, old), { reload: ["keys"], msg: t("Key removed") });
    };
    openDialog(`
      <div class="dlg-body">
        <h2>${esc(t(a.title))}</h2>
        <p>${esc(old ? t("Press the new key combination … Esc cancels, Backspace removes it.") : t("Press the new key combination … Esc cancels."))}</p>
        <div class="capture" id="cap" tabindex="0" aria-live="polite" aria-label="${esc(t("Record a key combination"))}">${capInner()}</div>
        <div id="cap-conf"></div>
      </div>
      <div class="dlg-foot">
        ${old ? `<button type="button" class="btn danger" data-d="remove">${ic("trash", "sm")}${esc(t("Remove"))}</button><span class="spacer"></span>` : ""}
        <button type="button" class="btn" data-d="cancel">${esc(t("Cancel"))}</button>
        <button type="button" class="btn primary" data-d="ok" disabled>${esc(t("Apply"))}</button>
      </div>`, {
      cancel: () => closeDialog(),
      ok: apply,
      remove,
    }, {
      focus: "#cap",
      onKey: (e) => {
        if (e.target.id !== "cap") return;
        if (e.key === "Escape") return; // the dialog's cancel
        const plain = !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey;
        if (plain && e.key === "Tab") return;
        if (plain && e.key === "Enter" && combo) { e.preventDefault(); if (combo !== old) apply(); return; }
        if (plain && e.key === "Backspace") { e.preventDefault(); if (old) remove(); return; }
        e.preventDefault();
        const r = comboFrom(e);
        if (r.key) { combo = r.combo; held = []; }
        else { held = r.mods; combo = null; }
        draw();
      },
    });
    dlg.onkeyup = (e) => {
      if (e.target.id !== "cap" || combo) return;
      held = comboFrom(e).mods; draw();
    };
    /* always back to the normal keymap: OK, cancel, Esc, remove, errors */
    dlgCleanup = () => { api.endKeyCapture().catch(() => {}); };
  }

  function pageKeys() {
    const acts = S.keys.actions.map((a) => {
      const title = t(a.title);
      const slots = a.slots.map((c, i) => {
        const key = `slot-${a.id}-${i}`;
        H[key] = { click: () => captureDialog(a.id, i) };
        if (c) return `<button type="button" class="keyslot" aria-label="${esc(t("{action}, key {n}: {keys}. Change", { action: title, n: i + 1, keys: comboText(c) }))}" ${k(key)}>${caps(c)}</button>`;
        if (i === 1 && !a.slots[0]) return "";
        return `<button type="button" class="keyslot empty" aria-label="${esc(i ? t("{action}: add a second key", { action: title }) : t("{action}: set a key", { action: title }))}" ${k(key)}>${ic("plus")}${esc(i ? t("Second key") : t("Set a key"))}</button>`;
      }).join("");
      return row({ sid: `keys.${a.id}`, icon: KEY_ICON[a.id] || "keyboard", title: esc(title), desc: esc(t(a.desc || "")), end: slots });
    }).join("");
    const dk = S.keys.options.desktop_keys;
    const desk = row({
      sid: "keys.desktop", icon: "desktops", title: esc(t("Desktop keys")),
      desc: esc(t("Takes over Super + 1 … 0 and Super + Tab so they only switch the desktops 1–10")),
      end: toggle("dk", dk, (v) => change(() => api.setOption("desktop_keys", v), () => api.setOption("desktop_keys", !v), { reload: ["keys"] }), { label: t("Desktop keys") }),
    });
    return `${ph(esc(t("Keyboard")), esc(t("Click a key to change it. Every action has two places.")))}
      ${sec(esc(t("Minimize keys")), `<div class="stack">${acts}</div>`)}
      ${sec(esc(t("Desktops")), `<div class="stack">${desk}</div>`)}`;
  }

  /* ================================================================ page: Windows (look) */
  /* While editing, the look is shown live in Hyprland (previewLook); "Discard" ends
   * the preview (revertLook), "Apply" keeps it (saveLook) with a 15 s "keep it?". */
  const PRESET_KEYS = ["gapsIn", "gapsOut", "rounding", "border", "blur", "blurSize", "blurPasses", "activeOpacity", "inactiveOpacity"];
  const PRESET_SUB = { Clean: () => t("Tight, square, no blur"), Soft: () => t("Airy and round"), Glass: () => t("See-through and blurred") };
  const presetOf = (v) => ((S.look.presets || []).find((p) => PRESET_KEYS.every((key) => p.values[key] === v[key])) || {}).name || null;
  const lookDirty = () => !!(S.look && S.lookDraft && (S.look.previewing || !eq(S.lookDraft, S.lookBase)));
  const opacityPct = (x) => pct(Math.round(x * 100));
  const solidHex = (c) => String(c || "").slice(0, 7);

  function lpVars(v) {
    const seeThrough = v.activeOpacity < 1 || v.inactiveOpacity < 1 || (v.apps || []).length;
    const bl = v.blur && seeThrough ? v.blurSize * 0.8 : 0;
    const theme = (S.look && S.look.themeBorder && S.look.themeBorder.colors) || [];
    const [c1, c2] = v.borderColors || [theme[0] || "var(--c-accent)", theme[1] || theme[0] || "var(--c-accent)"];
    return `--gi:${v.gapsIn};--go:${v.gapsOut};--rd:${v.rounding};--bw:${v.border};--tr:${Math.round((1 - v.inactiveOpacity) * 100)};--tr-act:${Math.round((1 - v.activeOpacity) * 100)};--bl:${bl};--bc1:${c1};--bc2:${c2};--ba:${v.borderColors ? v.borderAngle : 0};--bc-in:var(--c-selection)`;
  }
  function lookPreview(v, mini = false) {
    const term = `<div class="term"><div><span class="p">~/dev</span> <span class="d">❯</span> hypr-screens status</div><div><span class="g">●</span> ${esc(t("Laptop"))} <span class="d">· ${esc(t("fixed"))}</span></div><div><span class="g">●</span> HP 32f <span class="d">· ${esc(t("Desktops 1–10"))}</span></div><div><span class="p">~/dev</span> <span class="d">❯</span> <span class="y">▍</span></div></div>`;
    const doc = `<div class="doc"><i class="h"></i><i></i><i style="width:85%"></i><i style="width:70%"></i><i class="acc"></i><i style="width:90%"></i></div>`;
    const media = `<div class="media"><span class="art"></span><span class="lines"><i></i><i style="width:45%"></i><i style="width:100%;height:3px;margin-top:4px"></i></span></div>`;
    return `<div class="lp${mini ? " mini" : ""}" style="${lpVars(v)}" aria-hidden="true"><div class="lp-bar"><i class="on"></i><i></i><i></i><i></i><span>14:32</span></div><div class="lp-area"><div class="lp-win a active">${term}</div><div class="lp-win">${doc}</div><div class="lp-win">${media}</div></div></div>`;
  }

  /* One preview call at a time; the newest draft wins. */
  const Preview = { timer: 0, running: null, again: false };
  function queuePreview(delay = 120) {
    clearTimeout(Preview.timer);
    Preview.timer = setTimeout(runPreview, delay);
  }
  async function runPreview() {
    if (Preview.running) { Preview.again = true; return; }
    const draft = clone(S.lookDraft);
    Preview.running = (async () => {
      try {
        if (eq(draft, S.lookBase) && !S.look.previewing) await api.revertLook();
        else await api.previewLook(draft);
      } catch (err) { showError(err); }
    })();
    await Preview.running;
    Preview.running = null;
    if (Preview.again) { Preview.again = false; runPreview(); }
  }
  async function previewSettled() {
    clearTimeout(Preview.timer);
    Preview.again = false;
    if (Preview.running) await Preview.running;
  }
  function setDraft(changes, { full = true, preview = true } = {}) {
    Object.assign(S.lookDraft, changes);
    if (preview) queuePreview();
    if (full) render();
    else {
      const lp = $("#lp .lp"); if (lp) lp.setAttribute("style", lpVars(S.lookDraft));
      renderApplyBar(route());
    }
  }

  function pageLook() {
    const v = S.lookDraft;
    const R = S.look.ranges || {};
    const range = (key, min, max, step = 1) => ({ min, max, step, ...(R[key] || {}) });
    const sl = (key, title, icon, unit, desc) => {
      const r = range(key, 0, 30);
      return row({
        sid: `look.${key}`, icon, title: esc(title), desc: esc(desc),
        end: slider(`lk-${key}`, {
          min: r.min, max: r.max, step: r.step, value: v[key], label: title, fmt: (x) => `${nf(x)}${NB}${unit}`,
          onInput: (x) => setDraft({ [key]: x }, { full: false }),
          onChange: (x) => setDraft({ [key]: x }),
        }),
      });
    };
    const op = (key, title, icon, desc) => row({
      sid: `look.${key}`, icon, title: esc(title), desc: esc(desc),
      end: slider(`lk-${key}`, {
        min: 30, max: 100, step: 1, value: Math.round(v[key] * 100), label: title, fmt: (x) => pct(x),
        onInput: (x) => setDraft({ [key]: x / 100 }, { full: false }),
        onChange: (x) => setDraft({ [key]: x / 100 }),
      }),
    });
    const current = presetOf(v);
    const presets = tcards("preset", (S.look.presets || []).map((p) => ({
      v: p.name, label: t(p.name), sub: PRESET_SUB[p.name] ? PRESET_SUB[p.name]() : "",
      thumb: lookPreview({ ...v, ...Object.fromEntries(PRESET_KEYS.map((key) => [key, p.values[key]])) }, true),
    })), current, (name) => {
      const p = S.look.presets.find((x) => x.name === name);
      setDraft(Object.fromEntries(PRESET_KEYS.map((key) => [key, p.values[key]])));
    }, { label: t("Style") });

    /* see-through apps: own opacity per window class */
    const apps = (v.apps || []).map((a, i) => {
      const setApp = (ch) => setDraft({ apps: v.apps.map((x, j) => (j === i ? { ...x, ...ch } : x)) });
      return `<div class="app-row">${appIcon(a.class)}<b title="${esc(a.class)}">${esc(a.class)}</b>
        <span class="app-sl"><small>${esc(t("Active"))}</small>${slider(`app-a-${i}`, { min: 30, max: 100, value: Math.round(a.active * 100), label: t("{app}: active", { app: a.class }), fmt: pct, onChange: (x) => setApp({ active: x / 100 }) })}</span>
        <span class="app-sl"><small>${esc(t("Others"))}</small>${slider(`app-i-${i}`, { min: 30, max: 100, value: Math.round(a.inactive * 100), label: t("{app}: not active", { app: a.class }), fmt: pct, onChange: (x) => setApp({ inactive: x / 100 }) })}</span>
        <button type="button" class="btn ghost icon" aria-label="${esc(t("Remove {app}", { app: a.class }))}" title="${esc(t("Remove"))}" ${reg(`rmapp-${i}`, { click: () => setDraft({ apps: v.apps.filter((_, j) => j !== i) }) })}>${ic("x", "sm")}</button></div>`;
    }).join("");
    const addable = (S.look.apps || []).filter((a) => !(v.apps || []).some((x) => x.class === a.id));
    H.addapp = {
      select: (el) => openListbox(el, {
        header: t("Open apps"),
        options: addable.map((a) => ({ v: a.id, label: a.name, icon: appIcon(a.id) })),
        value: null,
        onPick: (id) => setDraft({ apps: [...(v.apps || []), { class: id, active: 0.9, inactive: 0.8 }] }),
      }),
    };

    const own = !!v.borderColors;
    const colors = own ? `<label class="swatch" title="${esc(t("Gradient start"))}"><i style="background:${esc(v.borderColors[0])}"></i><span>1</span><input type="color" value="${esc(solidHex(v.borderColors[0]))}" aria-label="${esc(t("Border color 1"))}" ${reg("col-1", { color: (c) => setDraft({ borderColors: [c, v.borderColors[1]] }, { full: false }), colorDone: (c) => setDraft({ borderColors: [c, S.lookDraft.borderColors[1]] }) })}></label>
      <label class="swatch" title="${esc(t("Gradient end"))}"><i style="background:${esc(v.borderColors[1])}"></i><span>2</span><input type="color" value="${esc(solidHex(v.borderColors[1]))}" aria-label="${esc(t("Border color 2"))}" ${reg("col-2", { color: (c) => setDraft({ borderColors: [S.lookDraft.borderColors[0], c] }, { full: false }), colorDone: (c) => setDraft({ borderColors: [S.lookDraft.borderColors[0], c] }) })}></label>` : "";
    const themeColors = (S.look.themeBorder && S.look.themeBorder.colors) || ["#89b4fa", "#89b4fa"];
    const anim = range("animSpeed", 0.25, 3, 0.05);
    const adv = expander("look-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("Blur, animations, border colors, see-through apps")) }, [
      row({ sid: "look.blur", cls: "sub", title: esc(t("Blur")), desc: esc(t("Blurs what is behind see-through windows")),
        end: toggle("lk-blur", v.blur, (x) => setDraft({ blur: x }), { label: t("Blur") }) }),
      row({ sid: "look.blurSize", cls: "sub", title: esc(t("Blur strength")),
        end: slider("lk-blurSize", { ...range("blurSize", 1, 20), value: v.blurSize, label: t("Blur strength"), disabled: !v.blur, fmt: (x) => `${nf(x)}${NB}px`, onInput: (x) => setDraft({ blurSize: x }, { full: false }), onChange: (x) => setDraft({ blurSize: x }) }) }),
      row({ sid: "look.blurPasses", cls: "sub", title: esc(t("Blur quality")),
        end: seg("passes", [{ v: 1, label: t("Fast") }, { v: 2, label: t("Balanced") }, { v: 3, label: t("Fine") }, { v: 4, label: t("Finest") }], v.blurPasses, (x) => setDraft({ blurPasses: x }), { label: t("Blur quality"), disabled: !v.blur }) }),
      row({ sid: "look.anim", cls: "sub", title: esc(t("Animation speed")), desc: esc(t("1× is Omarchy’s speed, 2× twice as fast")),
        end: slider("lk-anim", { min: anim.min, max: anim.max, step: anim.step, value: v.animSpeed, label: t("Animation speed"), fmt: (x) => `${nf(x, 2)}×`, onInput: (x) => setDraft({ animSpeed: x }, { full: false, preview: false }), onChange: (x) => setDraft({ animSpeed: x }) }) }),
      row({ sid: "look.colors", cls: "sub", title: esc(t("Own border colors")), desc: esc(own ? t("A gradient around the active window") : t("Off: the colors come from the Omarchy theme")),
        end: `${colors}${toggle("custcol", own, (x) => setDraft(x ? { borderColors: [solidHex(themeColors[0]), solidHex(themeColors[1] || themeColors[0])], borderAngle: S.look.themeBorder ? S.look.themeBorder.angle || 0 : 0 } : { borderColors: null, borderAngle: 0 }), { label: t("Own border colors") })}` }),
      own ? row({ sid: "look.angle", cls: "sub", title: esc(t("Gradient angle")),
        end: slider("lk-angle", { ...range("borderAngle", 0, 355, 5), value: v.borderAngle, label: t("Gradient angle"), fmt: (x) => `${nf(x)}°`, onInput: (x) => setDraft({ borderAngle: x }, { full: false }), onChange: (x) => setDraft({ borderAngle: x }) }) }) : "",
      `<div class="row sub block" data-sid="look.apps"><div class="row-head"><div class="row-text"><div class="row-title"><span class="t">${esc(t("See-through apps"))}</span></div><div class="row-desc">${esc(t("These apps get their own opacity"))}</div></div><div class="row-end">${addable.length ? `<button type="button" class="btn" aria-haspopup="listbox" aria-expanded="false" ${k("addapp")}>${ic("plus", "sm")}${esc(t("Add an app"))}</button>` : `<span class="muted" style="font-size:12.5px">${esc(t("No other app is open"))}</span>`}</div></div>${apps ? `<div class="body app-list">${apps}</div>` : ""}</div>`,
    ].join(""));

    const custom = Object.keys(S.look.saved || {}).length > 0;
    const resetBtn = custom ? button("lookreset", `${ic("undo", "sm")}${esc(t("Omarchy’s look"))}`, async () => {
      const ok = await confirmDialog({ title: t("Back to Omarchy’s look?"), text: t("Forgets your own window look; the Omarchy theme decides again."), ok: t("Reset") });
      if (!ok) return;
      await previewSettled();
      UI.busy += 1;
      try { S.look = await api.resetLook(); S.lookBase = clone(S.look.values); S.lookDraft = clone(S.look.values); toast(t("Back to Omarchy’s look")); }
      catch (err) { showError(err); }
      UI.busy -= 1;
      render();
    }, { cls: "btn", attrs: 'data-sid="look.reset"' }) : "";

    return `${ph(esc(t("Windows")), esc(t("How windows look. While you change something, Hyprland shows it right away.")), resetBtn)}
      <div class="card lp-card" id="lp">${lookPreview(v)}</div>
      ${sec(esc(t("Style")), `<div data-sid="look.presets">${presets}</div>`, { sub: current ? "" : esc(t("Own settings")) })}
      ${sec(esc(t("Gaps and borders")), `<div class="stack">
        ${sl("gapsIn", t("Inner gaps"), "gapIn", "px", t("Between the windows"))}
        ${sl("gapsOut", t("Outer gaps"), "gapOut", "px", t("To the edge of the screen"))}
        ${sl("rounding", t("Corners"), "corner", "px", t("Rounding of the window corners"))}
        ${sl("border", t("Border"), "border", "px", t("Width of the window border"))}
      </div>`)}
      ${sec(esc(t("Opacity")), `<div class="stack">
        ${op("activeOpacity", t("Active window"), "opacity", t("100 % = solid"))}
        ${op("inactiveOpacity", t("Other windows"), "opacity", t("100 % = solid"))}
      </div>`)}
      <div class="stack" style="margin-top:var(--s1)">${adv}</div>`;
  }

  async function discardLook() {
    await previewSettled();
    UI.busy += 1;
    try { S.look = await api.revertLook(); S.lookBase = clone(S.look.values); S.lookDraft = clone(S.look.values); toast(t("Discarded")); }
    catch (err) { showError(err); }
    UI.busy -= 1;
    render();
  }
  async function applyLook() {
    await previewSettled();
    const before = { values: clone(S.lookBase), saved: clone(S.look.saved || {}) };
    UI.busy += 1;
    try { S.look = await api.saveLook(clone(S.lookDraft)); }
    catch (err) { UI.busy -= 1; showError(err); render(); return; }
    S.lookBase = clone(S.look.values); S.lookDraft = clone(S.look.values);
    UI.busy -= 1;
    render();
    keepDialog(async () => {
      try {
        S.look = Object.keys(before.saved).length
          ? await api.saveLook({ ...before.values, borderColors: before.saved.borderColors ?? null })
          : await api.resetLook();
      } catch (err) { showError(err); await reload("look"); }
      S.lookBase = clone(S.look.values); S.lookDraft = clone(S.look.values);
      render();
    }, t("Keep this look?"));
  }
  function renderApplyBar(r) {
    const bar = $("#applybar");
    const show = r.page === "look" && !S.err.look && lookDirty();
    document.body.classList.toggle("has-bar", show);
    if (!show) { bar.hidden = true; bar.innerHTML = ""; return; }
    bar.innerHTML = `${ic("eye")}<p><b>${esc(t("Preview"))}</b><small>${esc(t("Hyprland shows the changes, but they are not kept yet."))}</small></p>
      <button type="button" class="btn" ${reg("discard", { click: discardLook })}>${esc(t("Discard"))}</button>
      <button type="button" class="btn primary" ${reg("applylook", { click: applyLook })}>${ic("check", "sm")}${esc(t("Apply"))}</button>`;
    bar.hidden = false;
  }

  /* ================================================================ widgets: previews */
  const W_ICON = { clock: "clock", calendar: "calendar", weather: "cloud", battery: "battery", system: "cpu", network: "wifi", disk: "disk", nowplaying: "play", lyrics: "lyrics", visualizer: "wave" };
  const wid = (kind) => (S.widgets || []).find((w) => w.kind === kind);
  const p2 = (n) => String(n).padStart(2, "0");
  const dtf = (o, d = new Date()) => { try { return new Intl.DateTimeFormat(loc(), o).format(d); } catch { return ""; } };
  /* Qt's date pattern (as the widget uses it): d dd ddd dddd M MM MMM MMMM yy yyyy, 'text'. */
  const qtDate = (p, d = new Date()) => String(p || "").replace(/'([^']*)'|dddd|ddd|dd|d|MMMM|MMM|MM|M|yyyy|yy/g, (tok, quoted) => {
    if (quoted !== undefined) return quoted;
    return ({
      dddd: dtf({ weekday: "long" }, d), ddd: dtf({ weekday: "short" }, d), dd: p2(d.getDate()), d: d.getDate(),
      MMMM: dtf({ month: "long" }, d), MMM: dtf({ month: "short" }, d), MM: p2(d.getMonth() + 1), M: d.getMonth() + 1,
      yyyy: d.getFullYear(), yy: String(d.getFullYear()).slice(2),
    })[tok];
  });
  function fmtDate(fmt, d = new Date(), pattern = "") {
    switch (fmt) {
      case "long": return dtf({ day: "numeric", month: "long" }, d);
      case "medium": return dtf({ day: "numeric", month: "short", year: "numeric" }, d);
      case "short": return dtf({ dateStyle: "short" }, d);
      case "iso": return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
      case "custom": return qtDate(pattern || "dddd d MMMM", d);
      default: return "";
    }
  }
  const clockDate = (c, d = new Date()) => {
    const date = fmtDate(c.date_format, d, c.date_pattern);
    return c.weekday && c.date_format !== "custom" ? `${dtf({ weekday: "long" }, d)}, ${date}` : date;
  };
  const fmtTime = (c, d = new Date(), zone) => dtf({ hour: "2-digit", minute: "2-digit", ...(c.seconds ? { second: "2-digit" } : {}), hour12: c.hours === "12", ...(zone ? { timeZone: zone } : {}) }, d);
  function wordClock(d = new Date()) {
    let h = d.getHours() % 12, m = Math.round(d.getMinutes() / 5) * 5;
    if (m === 60) { m = 0; h = (h + 1) % 12; }
    if (loc().startsWith("de")) {
      const HN = ["zwölf", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf"];
      const cur = HN[h], nxt = HN[(h + 1) % 12];
      const P = { 0: [cur === "eins" ? "ein" : cur, " Uhr"], 5: ["fünf nach ", cur], 10: ["zehn nach ", cur], 15: ["viertel nach ", cur], 20: ["zwanzig nach ", cur], 25: ["fünf vor halb ", nxt], 30: ["halb ", nxt], 35: ["fünf nach halb ", nxt], 40: ["zwanzig vor ", nxt], 45: ["viertel vor ", nxt], 50: ["zehn vor ", nxt], 55: ["fünf vor ", nxt] }[m];
      return m === 0 ? `ES IST <b>${P[0].toUpperCase()}</b>${P[1].toUpperCase()}` : `ES IST ${P[0].toUpperCase()}<b>${P[1].toUpperCase()}</b>`;
    }
    const HN = ["twelve", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven"];
    const cur = HN[h], nxt = HN[(h + 1) % 12];
    const P = { 0: ["", cur, " o’clock"], 5: ["five past ", cur], 10: ["ten past ", cur], 15: ["quarter past ", cur], 20: ["twenty past ", cur], 25: ["twenty-five past ", cur], 30: ["half past ", cur], 35: ["twenty-five to ", nxt], 40: ["twenty to ", nxt], 45: ["quarter to ", nxt], 50: ["ten to ", nxt], 55: ["five to ", nxt] }[m];
    return `IT IS ${P[0].toUpperCase()}<b>${P[1].toUpperCase()}</b>${(P[2] || "").toUpperCase()}`;
  }
  function analogSvg(d = new Date(), seconds = false) {
    const hA = ((d.getHours() % 12) + d.getMinutes() / 60) * 30, mA = d.getMinutes() * 6, sA = d.getSeconds() * 6;
    const ticks = Array.from({ length: 12 }, (_, i) => `<line x1="32" y1="5" x2="32" y2="${i % 3 ? 8 : 10}" transform="rotate(${i * 30} 32 32)" stroke="currentColor" stroke-opacity="${i % 3 ? 0.4 : 0.8}" stroke-width="${i % 3 ? 1.5 : 2.2}" stroke-linecap="round"/>`).join("");
    return `<svg class="wv-analog" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="rgb(17 17 27 / .55)" stroke="rgb(255 255 255 / .12)"/>${ticks}<line x1="32" y1="32" x2="32" y2="17" transform="rotate(${hA} 32 32)" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><line x1="32" y1="32" x2="32" y2="10" transform="rotate(${mA} 32 32)" stroke="var(--c-accent)" stroke-width="2" stroke-linecap="round"/>${seconds ? `<line x1="32" y1="36" x2="32" y2="8" transform="rotate(${sA} 32 32)" stroke="var(--c-red)" stroke-width="1" stroke-linecap="round"/>` : ""}<circle cx="32" cy="32" r="2.5" fill="var(--c-accent)"/></svg>`;
  }
  const isoWeek = (d) => { const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); const day = x.getUTCDay() || 7; x.setUTCDate(x.getUTCDate() + 4 - day); return Math.ceil(((x - new Date(Date.UTC(x.getUTCFullYear(), 0, 1))) / 864e5 + 1) / 7); };
  function calGrid(c) {
    const d = new Date(), y = d.getFullYear(), m = d.getMonth();
    const mon = c.week_start !== "sunday";
    const first = new Date(y, m, 1).getDay();
    const off = mon ? (first + 6) % 7 : first;
    const days = new Date(y, m + 1, 0).getDate();
    const heads = Array.from({ length: 7 }, (_, i) => `<b>${esc(dtf({ weekday: "narrow" }, new Date(2024, 0, (mon ? 1 : 7) + i)))}</b>`).join("");
    const cells = [];
    for (let i = 0; i < off + days; i++) {
      if (c.show_weeks && i % 7 === 0) cells.push(`<b class="wk">${isoWeek(new Date(y, m, Math.max(1, i - off + 1)))}</b>`);
      cells.push(i < off ? "<span></span>" : `<span${i - off + 1 === d.getDate() ? ' class="t"' : ""}>${i - off + 1}</span>`);
    }
    return `<div class="w box cal">${c.show_month ? `<div class="wv-s" style="margin-bottom:4px;font-weight:600;opacity:.9">${esc(dtf({ month: "long", year: "numeric" }, d))}</div>` : ""}<div class="wv-cal${c.show_weeks ? " wk" : ""}">${c.show_weeks ? "<b></b>" : ""}${heads}${cells.join("")}</div></div>`;
  }
  const VIS_H = [14, 26, 38, 30, 44, 22, 34, 18, 40, 28, 16, 32, 24, 12, 36, 20];
  function visPreview(c) {
    const n = Math.max(8, Math.min(16, Math.round((c.bars || 32) / 3)));
    const hs = Array.from({ length: n }, (_, i) => VIS_H[i % VIS_H.length]);
    switch (c.style) {
      case "wave": return `<div class="w"><svg viewBox="0 0 120 50" width="130" height="50"><path d="M0 25 C10 5 20 45 30 25 S50 2 60 25 80 48 90 25 110 8 120 25" fill="none" stroke="var(--c-accent)" stroke-width="2.2" stroke-linecap="round"/><path d="M0 25 C12 15 22 35 34 25 S56 12 66 25 86 38 98 25 114 18 120 25" fill="none" stroke="var(--c-red)" stroke-width="1.4" opacity=".7"/></svg></div>`;
      case "dots": return `<div class="w"><div class="wv-dots">${hs.map((h) => `<i>${"<b></b>".repeat(Math.max(1, Math.round(h / 9)))}</i>`).join("")}</div></div>`;
      case "circle": return `<div class="w"><svg viewBox="0 0 64 64" width="64" height="64">${hs.concat(hs).map((h, i, all) => `<line x1="32" y1="17" x2="32" y2="${17 - h / 5}" transform="rotate(${(i * 360) / all.length} 32 32)" stroke="var(--c-accent)" stroke-width="2.4" stroke-linecap="round"/>`).join("")}<circle cx="32" cy="32" r="13" fill="none" stroke="rgb(255 255 255 / .18)"/></svg></div>`;
      case "mirrored": return `<div class="w"><div class="wv-vis mirror">${hs.map((h) => `<i style="height:${h * 1.1}px"></i>`).join("")}</div></div>`;
      default: return `<div class="w"><div class="wv-vis">${hs.map((h) => `<i style="height:${h}px"></i>`).join("")}</div></div>`;
    }
  }
  function npPreview(c) {
    const text = `<div class="np-t">${c.show_title ? `<div style="font-weight:600;font-size:12px">Nachtfahrt</div>` : ""}${c.show_artist ? `<div class="wv-s">Kollektiv Ost</div>` : ""}${c.show_album ? `<div class="wv-s" style="opacity:.5">Stadtlichter</div>` : ""}${c.show_progress ? `<div class="wv-bar" style="width:84px;height:3px;margin-top:6px"><i style="width:40%"></i></div>` : ""}${c.show_time ? `<div class="wv-s mono" style="font-size:8.5px;margin-top:2px">1:24 / 3:41</div>` : ""}${c.show_controls ? `<div class="np-ctl"><svg viewBox="0 0 24 24"><path d="M7 6v12M18 6l-8 6 8 6z"/></svg><svg viewBox="0 0 24 24"><path d="M8 6v12M16 6v12"/></svg><svg viewBox="0 0 24 24"><path d="M17 6v12M6 6l8 6-8 6z"/></svg></div>` : ""}</div>`;
    return `<div class="w box"><div class="np ${c.np_layout === "column" ? "col" : ""}">${c.show_cover ? '<span class="wv-art"></span>' : ""}${text}</div></div>`;
  }
  function wPreview(w) {
    const c = w.content;
    const level = (S.samsung && S.samsung.level) ?? 76;
    switch (w.kind) {
      case "clock": {
        if (c.clock_style === "analog") return `<div class="w">${analogSvg(new Date(), c.seconds)}</div>`;
        if (c.clock_style === "words") return `<div class="w box"><div class="wv-words">${wordClock()}</div></div>`;
        const time = fmtTime(c);
        const zone = c.zone2 ? `<div class="wv-s" style="margin-top:3px">${esc(tzName(c.zone2))} ${esc(fmtTime({ ...c, seconds: false }, new Date(), c.zone2))}</div>` : "";
        const date = c.date ? `<div class="wv-date">${esc(clockDate(c))}</div>` : "";
        if (c.clock_style === "flip") {
          const parts = time.split(/[:.\s]/).filter((x) => /\d/.test(x)).slice(0, c.seconds ? 3 : 2);
          return `<div class="w"><div class="wv-flip">${parts.map((x) => `<span>${esc(x)}</span>`).join("")}</div>${date}${zone}</div>`;
        }
        return `<div class="w"><div class="wv-time">${esc(time)}</div>${date}${zone}</div>`;
      }
      case "calendar": return calGrid(c);
      case "weather": {
        const deg = (n) => `${c.units === "f" ? Math.round(n * 1.8 + 32) : n}°`;
        const days = [1, 2, 3].map((i) => dtf({ weekday: "short" }, new Date(Date.now() + i * 864e5)));
        return `<div class="w box">${c.show_place ? `<div class="wv-s" style="margin-bottom:2px">Berlin</div>` : ""}<div class="wv-row"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke-width="1.6" stroke-linecap="round"><circle cx="9" cy="9" r="3.5" stroke="var(--c-yellow)"/><path d="M9 2.5v1.5M2.5 9H4M4.4 4.4l1 1M13.6 4.4l-1 1" stroke="var(--c-yellow)"/><path d="M8 19a3.5 3.5 0 0 1-.4-7 4.7 4.7 0 0 1 9-.1A3.5 3.5 0 0 1 17 19z" fill="rgb(205 214 244 / .9)" stroke="none"/></svg><span class="wv-big">${deg(12)}</span></div>${c.show_details ? `<div class="wv-s">${esc(t("Partly cloudy"))} · ${esc(pct(64))}</div>` : ""}${c.show_forecast ? `<div class="wv-s" style="display:flex;gap:8px;margin-top:4px;font-family:var(--mono)"><span>${esc(days[0])} ${deg(14)}</span><span>${esc(days[1])} ${deg(11)}</span><span>${esc(days[2])} ${deg(10)}</span></div>` : ""}</div>`;
      }
      case "battery": {
        const low = level <= (c.low || 20);
        return `<div class="w box"><div class="wv-row">${ic("battery")}<span class="wv-big">${c.show_percent ? esc(pct(level)) : ""}</span></div><div class="wv-bar" style="margin-top:6px"><i style="width:${level}%;background:${low ? "var(--c-red)" : "var(--c-green)"}"></i></div>${c.show_remaining ? `<div class="wv-s" style="margin-top:4px">${esc(t("{time} left", { time: minutes((S.samsung && S.samsung.remainingMinutes) || 320) }))}</div>` : ""}</div>`;
      }
      case "system": {
        const parts = [c.cpu && ["CPU", 23], c.memory && ["RAM", 41], c.temperature && ["°C", 52]].filter(Boolean);
        return `<div class="w box wv-bars">${(parts.length ? parts : [["CPU", 23]]).map(([n, v]) => `<div class="wv-row"><span>${n}</span>${c.curves ? `<svg viewBox="0 0 80 14" width="80" height="14"><path d="M0 12 10 9 20 10 30 6 40 8 50 3 60 6 70 4 80 7" fill="none" stroke="var(--c-accent)" stroke-width="1.4"/></svg>` : `<div class="wv-bar"><i style="width:${v}%"></i></div>`}</div>`).join("")}</div>`;
      }
      case "network": return `<div class="w box">${c.curves ? `<svg viewBox="0 0 110 34" width="110" height="34"><path d="M0 28 10 24 20 26 30 18 40 21 50 10 60 15 70 8 80 16 90 12 100 19 110 14" fill="none" stroke="var(--c-accent)" stroke-width="1.8" stroke-linejoin="round"/><path d="M0 31 15 30 30 28 45 30 60 26 75 29 90 27 110 29" fill="none" stroke="var(--c-green)" stroke-width="1.4" opacity=".8"/></svg>` : ""}<div class="wv-s mono" style="display:flex;gap:10px;margin-top:2px"><span>↓ 2.4 MB/s</span><span>↑ 180 kB/s</span></div></div>`;
      case "disk": return `<div class="w box"><div class="wv-row"><svg class="wv-ring" viewBox="0 0 44 44"><circle cx="22" cy="22" r="17" stroke="rgb(255 255 255 / .12)"/><circle cx="22" cy="22" r="17" stroke="var(--c-accent)" stroke-dasharray="${(c.show_free ? 0.38 : 0.62) * 107} 107" stroke-linecap="round" transform="rotate(-90 22 22)"/></svg><div><div style="font-weight:600;font-size:13px">${c.show_free ? "312 GB" : esc(pct(62))}</div><div class="wv-s">${esc(c.show_free ? t("free") : t("used"))}</div></div></div></div>`;
      case "nowplaying": return npPreview(c);
      case "lyrics": {
        const lines = [t("and the lights pass by"), t("we drive through the night"), t("until the morning comes"), t("and the city is asleep")];
        const n = Math.max(1, Math.min(4, c.lines || 3));
        const shown = n === 1 ? [1] : n === 2 ? [0, 1] : n === 3 ? [0, 1, 2] : [0, 1, 2, 3];
        const hl = (i) => i === 1 ? (c.highlight === "word" ? `<span style="font-weight:700;font-size:12px">${esc(lines[1]).replace(/^(\S+\s+\S+)/, '<span style="color:var(--c-accent)">$1</span>')}</span>` : `<span class="${c.highlight === "off" ? "" : "hl"}" style="${c.highlight === "off" ? "font-size:12px;font-weight:600" : ""}">${esc(lines[1])}</span>`) : `<span class="dim">${esc(lines[i])}</span>`;
        return `<div class="w"><div class="wv-lines">${shown.map(hl).join("")}</div></div>`;
      }
      case "visualizer": return visPreview(c);
      default: return "";
    }
  }
  const wpBox = (w, big = false) => `<div class="wp${big ? " big" : ""}" aria-hidden="true">${wPreview(w)}</div>`;
  const thumb = (w, content) => `<div class="wp" style="height:100%;border:0">${wPreview({ ...w, content: { ...w.content, ...content } })}</div>`;

  /* ================================================================ widgets: changes */
  async function setEnabled(w, on) {
    const r = await change(() => api.updateWidget(w.kind, { enabled: on }), () => api.updateWidget(w.kind, { enabled: !on }), {
      reload: ["widgets"], msg: (x) => (on && x && !x.placed ? false : on ? t("{name} is on", { name: t(w.name) }) : t("{name} is off", { name: t(w.name) })),
    });
    if (r && on && !r.placed) toast(t("{name} is on – it starts in the middle of the screen", { name: t(w.name) }), null, { action: { label: t("Arrange"), run: arrange } });
  }
  function setField(w, f, value) {
    const old = clone(w[f.group][f.key]);
    return change(() => api.updateWidget(w.kind, { [f.group]: { [f.key]: value } }), () => api.updateWidget(w.kind, { [f.group]: { [f.key]: old } }), { reload: ["widgets"] });
  }
  const arrange = () => change(() => api.arrangeWidgets(), null, { msg: t("Arranging is open on the desktop") });

  /* ================================================================ widgets: fields from the schema */
  const FIELD_ICON = {
    player: "music", bars: "wave", style: "wave", sensitivity: "gauge", smoothing: "sliders", peaks: "sparkle",
    highlight: "lyrics", lines: "lyrics", hide_paused: "eye", clock_style: "clock", hours: "clock", seconds: "clock",
    date: "calendar", weekday: "calendar", date_format: "calendar", date_pattern: "lyrics", zone2: "globe",
    cpu: "cpu", memory: "cpu", temperature: "temp", curves: "hz", units: "temp", show_place: "globe", show_details: "info",
    show_forecast: "calendar", week_start: "calendar", show_month: "calendar", show_weeks: "lyrics", show_percent: "battery",
    show_remaining: "clock", low: "alert", show_free: "disk", np_layout: "widgets", hide_idle: "eye",
    screens: "monitor", desktops: "desktops", same_place: "arrange", only_empty: "desktops", hide_on_battery: "battery",
    above: "window", where: "widgets",
  };
  const valueOf = (w, key) => (key in w.content ? w.content[key] : w.where[key]);
  const shownField = (w, f) => !f.showIf || Object.entries(f.showIf).every(([key, v]) => valueOf(w, key) === v);
  const choiceLabel = (f, v) => { const c = (f.choices || []).find((x) => eq(x.value, v)); return c ? t(c.label) : String(v); };
  const CARD_FIELDS = {
    "clock.clock_style": (w, v) => thumb(w, { clock_style: v, zone2: "" }),
    "visualizer.style": (w, v) => thumb(w, { style: v }),
    "nowplaying.np_layout": (w, v) => thumb(w, { np_layout: v }),
  };
  const SCREEN_ICON = { laptop: "laptop", external: "monitor", all: "desktops" };

  /* One field as a row/block; card fields return {section} to stand on their own. */
  function fieldHtml(w, f) {
    const sid = `w.${w.kind}.${f.key}`;
    const key = `f-${w.kind}-${f.key}`;
    const val = valueOf(w, f.key);
    const off = f.enabledBy && !valueOf(w, f.enabledBy);
    const title = esc(t(f.label));
    const desc = f.hint ? esc(t(f.hint)) : "";
    const set = (v) => setField(w, f, v);
    const icon = FIELD_ICON[f.key] || "sliders";
    const cls = off ? "dim" : "";
    const card = CARD_FIELDS[`${w.kind}.${f.key}`];
    if (card) {
      return { section: sec(title, `<div data-sid="${esc(sid)}">${tcards(key, f.choices.map((c) => ({ v: c.value, label: t(c.label), thumb: card(w, c.value) })), val, set, { label: t(f.label) })}</div>`) };
    }
    if (f.key === "date_format") {
      const now = new Date();
      const opts = f.choices.map((c) => {
        const full = t(c.label);
        const name = full.replace(/\s*\(.*\)\s*$/, "") || full;
        return { v: c.value, label: name, ex: c.value === "custom" ? (val === "custom" ? fmtDate("custom", now, w.content.date_pattern) : "") : fmtDate(c.value, now) };
      });
      return { html: block({ sid, icon, title, desc, cls, body: radios(key, opts, val, set, { label: t(f.label), disabled: off }) }) };
    }
    if (f.key === "zone2") return { html: row({ sid, icon, title, cls, desc: desc || esc(t("Shows a second time below")), end: tzField(w, f, off) }) };
    if (f.key === "player") {
      const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label), ...(c.value ? { app: c.value } : { icon: "speaker" }) }));
      if (val != null && !opts.some((o) => o.v === val)) opts.push({ v: val, label: val, app: val });
      return { html: block({ sid, icon, title, desc, cls, body: chipsOne(key, opts, val, set, { label: t(f.label), disabled: off }) }) };
    }
    if (f.key === "screens" && f.group === "where") {
      const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label), icon: SCREEN_ICON[c.value] || "monitor" }));
      return { html: block({ sid: `w.where.screens`, icon, title, desc, cls, body: chipsOne(key, opts, val, set, { label: t(f.label), disabled: off }) }) };
    }
    if (f.key === "desktops" && f.type === "multi") {
      const all = val.includes("all");
      const opts = [...f.choices.map((c) => (c.value === "fixed" ? { v: c.value, label: t(c.label), icon: "pin" } : { v: c.value, label: t(c.label), square: /^\d+$/.test(c.value) })), { v: "all", label: t("All") }];
      const pick = (v, on) => {
        let d = val.filter((x) => x !== "all");
        if (v === "all") d = ["all"];
        else d = on ? [...d, v] : d.filter((x) => x !== v);
        set(d.length ? d : ["all"]);
      };
      return { html: block({ sid: "w.where.desktops", icon, title, desc: desc || esc(t("On which desktops the widget shows")), cls, body: chipsMulti(key, opts, all ? ["all"] : val, pick, { label: t(f.label), disabled: off }) }) };
    }
    switch (f.type) {
      case "toggle":
        return { html: row({ sid, icon, title, desc, cls, end: toggle(key, !!val, set, { label: t(f.label), disabled: off }) }) };
      case "choice": {
        const opts = f.choices.map((c) => ({ v: c.value, label: t(c.label) }));
        const short = opts.length <= 5 && opts.every((o) => o.label.length <= 16) && opts.reduce((n, o) => n + o.label.length, 0) <= 46;
        const ctl = short ? seg(key, opts, val, set, { label: t(f.label), disabled: off })
          : select(key, { options: opts, value: val, onChange: set, label: t(f.label), width: 220, disabled: off });
        return { html: row({ sid, icon, title, desc, cls, end: ctl }) };
      }
      case "number": {
        const unit = f.unit === "%" ? (x) => pct(x) : f.unit ? (x) => `${nf(x)}${NB}${f.unit}` : (x) => nf(x);
        const steps = (f.max - f.min) / (f.step || 1);
        const ctl = steps <= 10 && !f.unit
          ? stepper(key, { min: f.min, max: f.max, step: f.step || 1, value: val, fmt: unit, onChange: set, label: t(f.label), disabled: off })
          : slider(key, { min: f.min, max: f.max, step: f.step || 1, value: val, fmt: unit, onChange: set, label: t(f.label), disabled: off });
        return { html: row({ sid, icon, title, desc, cls, end: ctl }) };
      }
      case "text": {
        const isPattern = f.key === "date_pattern";
        const body = `${textField(key, { value: val || "", label: t(f.label), maxLength: f.maxLength, disabled: off, mono: isPattern, onChange: set,
          onInput: isPattern ? (v) => { const ex = $('[data-ex="custom"]'); if (ex) ex.textContent = fmtDate("custom", new Date(), v); } : null })}${isPattern ? `<div class="row-desc" style="margin-top:6px">${esc(t("d = day · dddd = weekday · MMMM = month · yyyy = year · 'text' as it is"))}</div>` : ""}`;
        return { html: block({ sid, icon, title, desc, cls, body }) };
      }
      case "multi": {
        const opts = (f.choices || []).map((c) => ({ v: c.value, label: t(c.label) }));
        return { html: block({ sid, icon, title, desc, cls, body: chipsMulti(key, opts, val || [], (v, on) => set(on ? [...val, v] : val.filter((x) => x !== v)), { label: t(f.label), disabled: off }) }) };
      }
      default: return { html: "" };
    }
  }
  /* All fields of one group: loose ones in a stack, `section` ones under their heading,
   * card fields (styles) as their own section. Order as in the schema. */
  function renderFields(w, groupName) {
    const out = [];
    let stack = [], stackTitle = null;
    const flush = () => {
      if (!stack.length) return;
      const body = `<div class="stack">${stack.join("")}</div>`;
      out.push(stackTitle ? sec(esc(t(stackTitle)), body) : `<div class="sec">${body}</div>`);
      stack = []; stackTitle = null;
    };
    for (const f of w.schema.filter((x) => x.group === groupName && shownField(w, x))) {
      const r = fieldHtml(w, f);
      if (r.section) { flush(); out.push(r.section); continue; }
      const title = f.section || null;
      if (title !== stackTitle) flush();
      stackTitle = title;
      stack.push(r.html);
    }
    flush();
    return out.join("");
  }

  /* ================================================================ time zones */
  const TZ = () => [
    ["America/New_York", t("New York")], ["Europe/London", t("London")], ["Asia/Tokyo", t("Tokyo")], ["America/Los_Angeles", t("Los Angeles")],
    ["Australia/Sydney", t("Sydney")], ["Asia/Dubai", t("Dubai")], ["Asia/Singapore", t("Singapore")], ["America/Sao_Paulo", t("São Paulo")],
    ["Europe/Moscow", t("Moscow")], ["Europe/Istanbul", t("Istanbul")], ["Asia/Kolkata", t("Mumbai")], ["Asia/Hong_Kong", t("Hong Kong")],
    ["Africa/Johannesburg", t("Johannesburg")], ["America/Mexico_City", t("Mexico City")], ["Atlantic/Reykjavik", t("Reykjavík")],
    ["Europe/Lisbon", t("Lisbon")], ["Europe/Madrid", t("Madrid")], ["Europe/Rome", t("Rome")], ["Europe/Paris", t("Paris")], ["Europe/Berlin", t("Berlin")],
    ["America/Toronto", t("Toronto")], ["America/Chicago", t("Chicago")], ["Pacific/Honolulu", t("Honolulu")], ["Pacific/Auckland", t("Auckland")],
    ["Asia/Shanghai", t("Shanghai")], ["Asia/Seoul", t("Seoul")], ["America/Denver", t("Denver")], ["Asia/Bangkok", t("Bangkok")], ["Africa/Cairo", t("Cairo")],
  ];
  const tzName = (zone) => { const x = TZ().find((z) => z[0] === zone); return x ? x[1] : String(zone).split("/").pop().replace(/_/g, " "); };
  const tzTime = (zone) => dtf({ hour: "2-digit", minute: "2-digit", timeZone: zone });
  const validZone = (z) => { try { new Intl.DateTimeFormat("en", { timeZone: z }); return true; } catch { return false; } };
  const norm = (s) => String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ß/g, "ss");

  let tzCtx = null;
  function tzField(w, f, off) {
    const cur = w.content.zone2;
    tzCtx = { w, f };
    if (cur) {
      return `<span class="chip" aria-pressed="true">${ic("globe")}${esc(tzName(cur))}<span class="num" style="opacity:.75">${esc(tzTime(cur))}</span><button type="button" class="btn ghost icon" style="width:22px;height:22px;margin-right:-6px" aria-label="${esc(t("Remove the second time zone"))}"${off ? " disabled" : ""} ${reg("tz-rm", { click: () => setField(w, f, "") })}>${ic("x", "xs")}</button></span>`;
    }
    H.tz = { combo: true };
    return `<label class="field" style="min-width:260px">${ic("search")}<input type="text" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="popover" aria-label="${esc(t("Search a second time zone"))}" placeholder="${esc(t("Search a city, e.g. Tokyo"))}" autocomplete="off" spellcheck="false"${off ? " disabled" : ""} ${k("tz")}></label>`;
  }
  function tzInput(el) {
    const raw = el.value.trim(), q = norm(raw);
    const hits = TZ().filter(([z, n]) => !q || norm(n).includes(q) || norm(z).includes(q)).slice(0, 7);
    const exact = raw.includes("/") && validZone(raw) && !hits.some(([z]) => z === raw) ? [[raw, t("Use “{zone}”", { zone: raw })]] : [];
    const list = [...exact, ...hits];
    if (!list.length) {
      Pop.open(el.closest(".field"), `<div class="sr-empty">${esc(t("No city found"))}</div>`, { keepFocus: true });
      el.setAttribute("aria-expanded", "true");
      return;
    }
    openListbox(el.closest(".field"), {
      keepFocus: true,
      options: list.map(([z, n]) => ({ v: z, label: n, sub: tzTime(z), icon: ic("globe", "sm") })),
      value: null,
      onPick: (z) => { if (tzCtx) setField(tzCtx.w, tzCtx.f, z); },
    });
    el.setAttribute("aria-expanded", "true");
  }

  /* ================================================================ layouts */
  function layoutBar() {
    const L = S.layouts;
    const chips = group("layout", L.items.map((n) => {
      const l = (L.layouts || []).find((x) => x.name === n) || {};
      return { v: n, label: n, title: l.auto ? t("Loads by itself with: {screens}", { screens: (l.screenNames || []).join(", ") }) : "" , auto: l.auto };
    }), L.current, (n) => {
      const old = L.current;
      change(() => api.loadLayout(n), old ? () => api.loadLayout(old) : null, { reload: ["widgets"], msg: t("Layout “{name}” loaded", { name: n }) });
    }, { cls: "chips", itemCls: "chip", label: t("Layout"), item: (o) => `${o.auto ? ic("plug") : ""}${esc(o.label)}` });
    H.savelayout = {
      click: (e, el) => {
        Pop.open(el, `<div class="pop-h">${esc(t("Save layout"))}</div><div class="pop-field"><label class="field" style="min-width:240px">${ic("widgets")}<input id="layout-name" maxlength="40" placeholder="${esc(t("Name, e.g. Presentation"))}" aria-label="${esc(t("Name of the layout"))}"></label></div><div class="pop-foot"><button type="button" class="btn" data-pf="cancel">${esc(t("Cancel"))}</button><button type="button" class="btn primary" data-pf="save">${esc(t("Save"))}</button></div>`, {
          minWidth: false, label: t("Save layout"),
          onClick: (ev) => {
            const b = ev.target.closest("[data-pf]");
            if (!b) return;
            if (b.dataset.pf === "cancel") { Pop.close(); return; }
            save();
          },
          onKey: (ev) => { if (ev.key === "Enter") { ev.preventDefault(); save(); return true; } return false; },
        });
        const save = () => {
          const n = $("#layout-name").value.trim();
          if (!n) { $("#layout-name").focus(); return; }
          Pop.close();
          change(() => api.saveLayout(n), null, { reload: ["widgets"], msg: t("Layout “{name}” saved", { name: n }) });
        };
      },
    };
    H.managelayouts = { click: () => layoutsDialog() };
    return `<div class="layouts" data-sid="widgets.layouts"><span class="lbl">${esc(t("Layout:"))}</span>${L.items.length ? chips : `<span class="muted" style="font-size:13px">${esc(t("none saved yet"))}</span>`}<button type="button" class="chip dashed" aria-haspopup="dialog" ${k("savelayout")}>${ic("plus")}${esc(t("Save"))}</button>${L.items.length ? `<button type="button" class="chip ghost" aria-haspopup="dialog" ${k("managelayouts")}>${ic("sliders")}${esc(t("Manage"))}</button>` : ""}</div>`;
  }
  function layoutsDialog() {
    const draw = () => {
      const L = S.layouts;
      const names = (L.connected || []).map((id) => sname(scr(id))).join(", ");
      return `<div class="dlg-body wide">
        <h2>${esc(t("Widget layouts"))}</h2>
        <p>${esc(t("A layout keeps where every widget is. “Automatic” loads it whenever exactly the screens connected now are connected."))}</p>
        <div class="stack lay-list">${L.layouts.length ? L.layouts.map((l, i) => `<div class="row lay-row" data-i="${i}">
          ${ic(l.auto ? "plug" : "widgets")}
          <div class="row-text"><div class="row-title"><span class="t">${esc(l.name)}</span>${L.current === l.name ? `<span class="pill">${esc(t("Shown now"))}</span>` : ""}</div>
            <div class="row-desc">${esc(l.auto ? t("Automatic with: {screens}", { screens: (l.screenNames || []).join(", ") || "–" }) : t("Only by hand"))}</div></div>
          <div class="row-end">
            <button type="button" class="sw" role="switch" aria-checked="${!!l.auto}" aria-label="${esc(t("Load “{name}” automatically with {screens}", { name: l.name, screens: names }))}" title="${esc(t("Automatic with the screens connected now"))}" data-d="auto" data-i="${i}"><span class="sw-label">${esc(t("Automatic"))}</span><span class="sw-track"></span></button>
            <button type="button" class="btn ghost icon" aria-label="${esc(t("Rename “{name}”", { name: l.name }))}" title="${esc(t("Rename"))}" data-d="rename" data-i="${i}">${ic("edit", "sm")}</button>
            <button type="button" class="btn ghost icon danger" aria-label="${esc(t("Delete “{name}”", { name: l.name }))}" title="${esc(t("Delete"))}" data-d="delete" data-i="${i}">${ic("trash", "sm")}</button>
          </div></div>`).join("") : `<div class="card empty-state">${ic("widgets")}<b>${esc(t("No layout saved yet"))}</b></div>`}</div>
      </div>
      <div class="dlg-foot"><button type="button" class="btn primary" data-d="close" autofocus>${esc(t("Done"))}</button></div>`;
    };
    const redraw = (focusSel) => {
      dlg.innerHTML = draw();
      const f = focusSel && $(focusSel, dlg);
      (f || $('[data-d="close"]', dlg)).focus();
    };
    const run = async (fn, focusSel) => {
      UI.busy += 1;
      try { S.layouts = await fn(); } catch (err) { showError(err); }
      UI.busy -= 1;
      render();
      if (dlg.open) redraw(focusSel);
    };
    const nameAt = (b) => S.layouts.layouts[+b.dataset.i].name;
    openDialog(draw(), {
      close: () => closeDialog(),
      auto: (b) => { const l = S.layouts.layouts[+b.dataset.i]; run(() => api.setLayoutAuto(l.name, !l.auto), `[data-d="auto"][data-i="${b.dataset.i}"]`); },
      delete: (b) => {
        const name = nameAt(b);
        run(() => api.deleteLayout(name)).then(() => toast(t("Layout “{name}” deleted", { name })));
      },
      rename: (b) => {
        const i = b.dataset.i, name = nameAt(b);
        const r = $(`.lay-row[data-i="${i}"] .row-text`, dlg);
        r.innerHTML = `<label class="field">${ic("edit")}<input id="lay-rename" maxlength="40" value="${esc(name)}" aria-label="${esc(t("New name for “{name}”", { name }))}"></label>`;
        const inp = $("#lay-rename", dlg);
        inp.focus(); inp.select();
        let done = false;
        const finish = (ok) => {
          if (done) return; done = true;
          const n = inp.value.trim();
          if (ok && n && n !== name) run(() => api.renameLayout(name, n), `[data-d="rename"][data-i="${i}"]`);
          else redraw(`[data-d="rename"][data-i="${i}"]`);
        };
        inp.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { e.preventDefault(); finish(true); }
          if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(false); }
        });
        inp.addEventListener("blur", () => finish(true));
      },
    }, { label: t("Widget layouts") });
  }

  /* ================================================================ page: Widgets */
  const arrangeBtn = () => button("arrange", `${ic("arrange", "sm")}${esc(t("Arrange on the desktop"))}`, arrange, { cls: "btn primary lg", attrs: 'data-sid="widgets.arrange"' });
  function widgetState(w) {
    if (w.missing && w.missing.length) return { cls: "warn", text: t("Not installed: {what} is missing", { what: w.missing.join(", ") }) };
    if (w.enabled && !w.placed) return { cls: "", text: t("Not arranged yet") };
    if (w.enabled && !w.onDesktop) return { cls: "neutral", text: t("Only in the bar") };
    return null;
  }

  function pageWidgets(r) {
    if (r.sub && wid(r.sub)) return pageWidget(wid(r.sub));
    const cards = S.widgets.map((w) => {
      const key = `w-${w.kind}`;
      const st = widgetState(w);
      H[key] = { click: () => { UI.wtab = "content"; go(`#/widgets/${w.kind}`); } };
      return `<div class="wcard${w.enabled ? "" : " off"}" data-sid="widgets.${w.kind}">
        <button type="button" class="wcard-open" aria-label="${esc(t("Open {name}", { name: t(w.name) }))}" title="${esc(t(w.description || ""))}" ${k(key)}>${wpBox(w)}</button>
        ${st ? `<span class="pill wcard-badge ${st.cls}">${esc(st.text)}</span>` : ""}
        <div class="wcard-foot">${ic(W_ICON[w.kind] || "widgets", "sm")}<b>${esc(t(w.name))}</b>${toggle(`wt-${w.kind}`, w.enabled, (v) => setEnabled(w, v), { label: t(w.name), text: false })}</div></div>`;
    }).join("");
    const on = S.widgets.filter((w) => w.enabled).length;
    return `${ph(esc(t("Widgets")), esc(t("{on} of {all} are on. Click a widget to set it up.", { on, all: S.widgets.length })), arrangeBtn())}
      <div style="margin:-8px 0 var(--s4)">${layoutBar()}</div>
      <div class="wgrid">${cards}</div>`;
  }

  function whereSummary(w) {
    const wh = w.where;
    const f = (key) => w.schema.find((x) => x.group === "where" && x.key === key);
    const parts = [];
    if (wh.where === "bar") return t("In the bar");
    if (wh.screens != null) parts.push(f("screens") ? choiceLabel(f("screens"), wh.screens) : wh.screens);
    if (wh.desktops) parts.push(wh.desktops.includes("all") ? t("all desktops") : (wh.desktops.length > 1 ? t("desktops {list}", { list: wh.desktops.map((x) => (x === "fixed" ? t("fixed") : x)).join(", ") }) : t("desktop {list}", { list: wh.desktops.map((x) => (x === "fixed" ? t("fixed") : x)).join("") })));
    if (wh.only_empty) parts.push(t("only on empty desktops"));
    if (wh.hide_on_battery) parts.push(t("hidden on battery"));
    if (wh.above) parts.push(t("above the windows"));
    if (wh.where === "both") parts.push(t("also in the bar"));
    return parts.join(" · ");
  }

  function pageWidget(w) {
    const tab = UI.wtab;
    H["tab-content"] = { click: () => { UI.wtab = "content"; render(); } };
    H["tab-where"] = { click: () => { UI.wtab = "where"; render(); } };
    H["tab-where2"] = { click: () => { UI.wtab = "where"; render(); const x = $('[data-k="tab-where"]'); if (x) x.focus(); } };
    H.crumb = { click: (e) => { e.preventDefault(); go("#/widgets"); } };
    const name = t(w.name);
    const missing = w.missing && w.missing.length ? `<div class="sec">${notice("alert", `${esc(t("Not installed: {what} is missing. The visualizer needs this program to hear the sound.", { what: w.missing.join(", ") }))}`, "warn")}
      <div style="margin-top:var(--s2)">${button("installcava", UI.cavaBusy ? `${spinner()}${esc(t("Installing …"))}` : `${ic("plus", "sm")}${esc(t("Install cava"))}`, async () => {
        UI.cavaBusy = true; render();
        await change(() => api.installCava(), null, { reload: ["widgets"], msg: t("cava is installed") });
        UI.cavaBusy = false; render();
      }, { cls: "btn primary", attrs: UI.cavaBusy ? "disabled" : "" })}</div></div>` : "";
    const unplaced = w.enabled && !w.placed && !missing ? `<div class="sec">${notice("info", esc(t("It starts in the middle of the screen. Put it where you want it on the desktop.")))}</div>` : "";
    const hint = `<div class="row hint-card" style="margin-top:var(--s5)">${ic("palette")}<div class="row-text"><div class="row-title"><span class="t">${esc(t("Colors, font and effects are set right on the desktop"))}</span></div></div>${button("arrange2", `${esc(t("Arrange"))}${ic("chevR", "sm")}`, arrange)}</div>`;
    return `<header class="ph"><div class="ph-text"><nav class="crumbs" aria-label="${esc(t("Path"))}"><a href="#/widgets" ${k("crumb")}>${esc(t("Widgets"))}</a>${ic("chevR")}<span aria-current="page">${esc(name)}</span></nav>${w.description ? `<p>${esc(t(w.description))}</p>` : ""}</div><div class="ph-actions">${arrangeBtn()}</div></header>
      <div class="wd-head">${wpBox(w, true)}
        <div class="stack">
          ${row({ sid: `widgets.${w.kind}.on`, icon: W_ICON[w.kind], title: esc(t("On the desktop")), desc: esc(w.enabled ? (w.onDesktop ? t("Shown") : t("Only in the bar")) : t("Hidden")), end: toggle(`wt-${w.kind}`, w.enabled, (v) => setEnabled(w, v), { label: t("{name} on the desktop", { name }) }) })}
          <button type="button" class="row" style="flex:1" ${k("tab-where2")}>${ic("desktops")}<div class="row-text"><div class="row-title"><span class="t">${esc(t("Where & when"))}</span></div><div class="row-desc">${esc(whereSummary(w))}</div></div>${ic("chevR", "chev")}</button>
        </div>
      </div>
      ${missing}${unplaced}
      <div class="tabs" role="tablist" aria-label="${esc(t("Sections"))}">
        <button type="button" class="tab" role="tab" id="tab-c" aria-controls="tabpanel" aria-selected="${tab === "content"}" tabindex="${tab === "content" ? 0 : -1}" ${k("tab-content")}>${esc(t("Content"))}</button>
        <button type="button" class="tab" role="tab" id="tab-w" aria-controls="tabpanel" aria-selected="${tab === "where"}" tabindex="${tab === "where" ? 0 : -1}" ${k("tab-where")}>${esc(t("Where & when"))}</button>
      </div>
      <div role="tabpanel" id="tabpanel" aria-labelledby="${tab === "content" ? "tab-c" : "tab-w"}">${tab === "content" ? renderFields(w, "content") + hint : renderFields(w, "where")}</div>`;
  }

  /* ================================================================ page: Sound */
  const DEV_ICON = { speaker: "speaker", headphones: "headphones", tv: "tv", mic: "mic" };
  const sndReload = { reload: ["sound"] };
  function devCard(d) {
    const input = d.kind === "source";
    const locked = d.forceMute;
    const usable = d.active && d.connected;
    const muteIc = input ? (d.muted ? "micX" : "mic") : (d.muted ? "volX" : "speaker");
    const name = t(d.name);
    const setV = (v) => change(() => api.setVolume(d.key, v), () => api.setVolume(d.key, d.volume), sndReload);
    const pills = `${d.isDefault ? `<span class="pill">${ic("check")}${esc(t("Default"))}</span>` : ""}${locked ? `<span class="pill danger">${ic("lock")}${esc(t("Stays muted"))}</span>` : ""}${!d.connected ? `<span class="pill neutral">${esc(t("Not connected"))}</span>` : !d.active ? `<span class="pill neutral">${esc(t("Switched off"))}</span>` : ""}`;
    const end = [
      d.connected && !d.active ? button(`on-${d.key}`, `${ic("power", "sm")}${esc(t("Switch on"))}`, () =>
        change(() => api.switchOnDevice(d.key), null, { ...sndReload, msg: t("{name} is on", { name }) }), { attrs: `title="${esc(t("Switches the sound card to the profile that drives this device"))}"` }) : "",
      d.isDefault || locked || !usable ? "" : button(`def-${d.key}`, esc(t("Make default")), () => {
        const prev = (input ? S.sound.inputs : S.sound.outputs).find((x) => x.isDefault);
        change(() => api.setDefault(d.key), prev ? () => api.setDefault(prev.key) : null, { ...sndReload, msg: t("{name} is the default", { name }) });
      }),
      button(`fm-${d.key}`, locked ? `${ic("lock", "sm")}${esc(t("Force muted"))}` : ic("lock", "sm"), () =>
        change(() => api.setForceMute(d.key, !locked), d.connected ? () => api.setForceMute(d.key, locked) : null, { ...sndReload, msg: locked ? t("Free again") : t("Stays muted") }),
      { cls: `btn lockbtn${locked ? "" : " icon ghost"}`, attrs: `aria-pressed="${locked}" aria-label="${esc(t("Force mute"))}" title="${esc(t("Force mute: keeps the device muted at 0 %, even when an app turns it up"))}"` }),
    ].join("");
    return `<div class="card dev${locked ? " locked" : ""}${usable ? "" : " inactive"}">
      <div class="dev-top">
        <span class="icon-tile">${ic(locked ? "lock" : DEV_ICON[d.icon] || "speaker")}</span>
        <div class="row-text"><div class="row-title"><b>${esc(name)}</b>${pills}</div><div class="row-desc">${esc(d.sub || "")}</div></div>
        <div class="row-end">${end}</div>
      </div>
      ${d.connected ? `<div class="dev-vol">
        ${button(`mute-${d.key}`, ic(muteIc), () => change(() => api.setMute(d.key, !d.muted), () => api.setMute(d.key, d.muted), { ...sndReload, msg: d.muted ? t("Sound on") : t("Sound off") }), { cls: "btn icon ghost mute", attrs: `aria-pressed="${d.muted}"${locked || !usable ? " disabled" : ""}`, label: d.muted ? t("Unmute {name}", { name }) : t("Mute {name}", { name }) })}
        ${slider(`vol-${d.key}`, { min: 0, max: 100, value: d.volume, label: t("Volume {name}", { name }), fmt: pct, onChange: setV, disabled: locked || !usable })}
      </div>` : ""}
    </div>`;
  }
  function appCard(a) {
    const outs = S.sound.outputs.filter((o) => o.active && o.connected && (!o.forceMute || o.key === a.output));
    const out = S.sound.outputs.find((o) => o.key === a.output);
    const setOut = (v) => change(() => api.setAppOutput(a.key, v), a.output ? () => api.setAppOutput(a.key, a.output) : null, sndReload);
    const label = t("Output for {app}", { app: a.name });
    const outCtl = outs.length <= 3
      ? chipsOne(`aout-${a.key}`, outs.map((o) => ({ v: o.key, label: t(o.name), icon: DEV_ICON[o.icon] || "speaker" })), a.output, setOut, { label })
      : select(`aout-${a.key}`, { options: outs.map((o) => ({ v: o.key, label: t(o.name) })), value: a.output, onChange: setOut, label });
    return `<div class="card dev">
      <div class="dev-top"><span class="icon-tile" style="background:transparent;border:0">${appIcon([...(a.icons || []), a.name], "app-ic")}</span>
        <div class="row-text"><div class="row-title"><b>${esc(a.name)}</b>${a.paused ? `<span class="pill neutral">${esc(t("Paused"))}</span>` : ""}</div><div class="row-desc">${esc([a.sub, out ? t("Plays on {device}", { device: t(out.name) }) : ""].filter(Boolean).join(" · "))}</div></div></div>
      <div class="dev-vol">
        ${button(`mute-${a.key}`, ic(a.muted ? "volX" : "speaker"), () => change(() => api.setMute(a.key, !a.muted), () => api.setMute(a.key, a.muted), { ...sndReload, msg: a.muted ? t("Sound on") : t("Sound off") }), { cls: "btn icon ghost mute", attrs: `aria-pressed="${a.muted}"`, label: a.muted ? t("Unmute {name}", { name: a.name }) : t("Mute {name}", { name: a.name }) })}
        ${slider(`vol-${a.key}`, { min: 0, max: 100, value: a.volume, label: t("Volume {name}", { name: a.name }), fmt: pct, onChange: (v) => change(() => api.setVolume(a.key, v), () => api.setVolume(a.key, a.volume), sndReload) })}
      </div>
      ${outs.length ? `<div class="dev-vol" style="margin-top:2px"><span class="row-desc" style="margin:0 4px 0 0">${esc(t("Output"))}</span>${outCtl}</div>` : ""}
    </div>`;
  }
  function pageSound() {
    const s = S.sound;
    const none = (text) => `<div class="card empty-state">${ic("speaker")}<b>${esc(text)}</b></div>`;
    const apps = s.apps.length ? s.apps.map(appCard).join("")
      : `<div class="card empty-state">${ic("music")}<b>${esc(t("No app is playing right now"))}</b><span style="font-size:12px">${esc(t("As soon as an app plays sound, it shows up here."))}</span></div>`;
    return `${ph(esc(t("Sound")), esc(t("Volume and devices. For every device, not only the default one.")))}
      ${sec(esc(t("Output")), `<div class="stack" data-sid="sound.out">${s.outputs.map(devCard).join("") || none(t("No output device"))}</div>`)}
      ${sec(esc(t("Input")), `<div class="stack" data-sid="sound.in">${s.inputs.map(devCard).join("") || none(t("No input device"))}</div>`)}
      ${sec(esc(t("Apps")), `<div class="stack" data-sid="sound.apps">${apps}</div>`)}`;
  }

  /* ================================================================ page: Camera */
  /* The preview image: asked for about twice a second while this page shows and the camera is on. */
  const Cam = { timer: 0, on: false };
  function camWanted() { return route().page === "camera" && S.camera && S.camera.installed && S.camera.enabled && !document.hidden && !S.err.camera; }
  function camLoop() {
    if (Cam.on) return;
    Cam.on = true;
    const step = async () => {
      if (!camWanted()) { Cam.on = false; return; }
      let p = null;
      try { p = await api.cameraPreview(); } catch { p = null; }
      const img = $("#cam-img"), msg = $("#cam-msg");
      if (img && p && p.image) { img.src = p.image; img.hidden = false; if (msg) msg.hidden = true; }
      else if (msg && p) {
        msg.hidden = false; if (img) img.hidden = true;
        $(".cam-msg-t", msg).textContent = p.reason === "off" ? t("The camera is off") : p.reason === "not_set_up" ? t("Not set up") : t("Starting the camera …");
      }
      Cam.timer = setTimeout(step, 500);
    };
    step();
  }
  function camState(c) {
    if (c.state == null) return { text: t("The background service is not running"), cls: "warn" };
    return ({
      off: { text: t("Off"), cls: "neutral" },
      idle: { text: t("Ready · no app uses it"), cls: "neutral" },
      live: { text: c.users === 1 ? t("1 app uses it") : t("{n} apps use it", { n: c.users }), cls: "ok" },
      busy: { text: t("The camera is busy (another app holds it)"), cls: "warn" },
    })[c.state] || { text: String(c.state), cls: "neutral" };
  }
  function pageCamera() {
    const c = S.camera;
    const intro = esc(t("Turns the camera picture for every app, like a monitor."));
    if (!c.hasCamera) {
      return `${ph(esc(t("Camera")), intro)}<div class="stack">${row({ lead: `<span class="icon-tile">${ic("camera")}</span>`, title: esc(t("No camera found")), desc: esc(t("Connect a camera; it shows up here.")) })}</div>`;
    }
    if (!c.installed) {
      const busy = UI.camBusy;
      return `${ph(esc(t("Camera")), intro)}
        <div class="stack">${row({
          sid: "camera.setup", lead: `<span class="icon-tile">${ic("camera")}</span>`, title: esc(t("Not set up")),
          desc: esc(t("Once: needs your password and about a minute. After that there is the “{name}”.", { name: c.virtualName })),
          end: button("camsetup", busy ? `${spinner()}${esc(t("Setting up …"))}` : `${esc(t("Set it up"))}${ic("chevR", "sm")}`, async () => {
            UI.camBusy = true; render();
            await change(() => api.setupCamera(), null, { reload: ["camera"], msg: t("The camera is set up") });
            UI.camBusy = false; render();
          }, { cls: "btn primary", attrs: busy ? "disabled" : "" }),
        })}</div>`;
    }
    const rotOpts = (c.rotations || [0, 90, 180, 270]).map((v) => ({ v, label: `${v}°` }));
    const setC = (en, rot) => change(() => api.setCamera(en, rot), () => api.setCamera(c.enabled, c.rotation), { reload: ["camera"] });
    const st = camState(c);
    after.push(() => camLoop());
    return `${ph(esc(t("Camera")), intro)}
      <div class="stack">
        ${row({ sid: "camera.toggle", icon: "camera", title: esc(c.virtualName), desc: esc(t("In Discord, the browser or Zoom pick “{name}”", { name: c.virtualName })), end: toggle("camon", c.enabled, (v) => setC(v, c.rotation), { label: c.virtualName }) })}
        <div class="card" style="padding:var(--s3)">
          <div class="cam${c.enabled ? "" : " off"}">
            ${c.enabled ? `<img id="cam-img" alt="${esc(t("Camera preview"))}" hidden><span class="cam-msg" id="cam-msg" role="status">${spinner()}<span class="cam-msg-t">${esc(t("Starting the camera …"))}</span></span>` : `<span class="cam-msg">${ic("camera", "lg")}<span>${esc(t("The camera is off"))}</span></span>`}
            <span class="label"><span class="rec"></span>${esc(c.enabled ? t("Preview · {device}", { device: c.device || t("Camera") }) : t("Apps do not see the camera"))}</span>
          </div>
        </div>
        ${row({ sid: "camera.rotation", icon: "rotate", title: esc(t("Rotation")), end: seg("camrot", rotOpts, c.rotation, (v) => setC(c.enabled, v), { label: t("Rotation") }) })}
        ${row({ icon: "info", title: esc(t("Camera light")), desc: esc(t("The real camera only runs while an app uses it")), end: `<span class="pill ${st.cls}">${esc(st.text)}</span>` })}
      </div>`;
  }

  /* ================================================================ page: Battery & power */
  const MODE_INFO = {
    "low-power": { icon: "leaf", desc: () => t("Longest battery life, slowed down") },
    quiet: { icon: "moon", desc: () => t("The fan stays almost silent") },
    balanced: { icon: "balance", desc: () => t("For every day") },
    performance: { icon: "bolt", desc: () => t("Full power, the fan can be heard") },
  };
  const modeLabel = (s, v) => { const m = (s.modes || []).find((x) => x.value === v); return m ? t(m.label) : v || "–"; };
  function setSam(field, value, msg) {
    const old = S.samsung[field];
    return change(() => api.setSamsung(field, value), field === "active" ? null : () => api.setSamsung(field, old), { reload: ["samsung"], msg });
  }
  function battState(s) {
    if (s.charging) return s.fullInMinutes != null ? t("Charging · full in {time}", { time: minutes(s.fullInMinutes) }) : t("Charging");
    if (s.plugged) return t("Plugged in, not charging");
    return s.remainingMinutes != null ? t("On battery · {time} left", { time: minutes(s.remainingMinutes) }) : t("On battery");
  }
  function pagePower() {
    const s = S.samsung;
    const intro = "Samsung Galaxy Book";
    if (!s.active) {
      const busy = UI.samBusy;
      return `${ph(esc(t("Battery & power")), intro)}
        <div class="stack">${row({ sid: "power.setup", lead: `<span class="icon-tile">${ic("battery")}</span>`, title: esc(t("The Samsung control is off")), desc: esc(t("Set it up once: needs your password. Then hypr-screens takes over the charge limit and the modes.")),
          end: button("samon", busy ? `${spinner()}${esc(t("Setting up …"))}` : esc(t("Set it up")), async () => {
            UI.samBusy = true; render();
            await setSam("active", true, t("The Samsung control is set up"));
            UI.samBusy = false; render();
          }, { cls: "btn primary", attrs: busy ? "disabled" : "" }) })}</div>`;
    }
    const level = s.level ?? 0;
    const ro = s.writable === false ? `<div class="sec">${notice("alert", esc(t("Some values cannot be changed right now. Run the setup again if this stays.")), "warn")}</div>` : "";
    const stats = [
      s.health != null ? `<div class="stat"><small>${esc(t("Health"))}</small><b>${esc(pct(s.health))}</b></div>` : "",
      s.cycles != null ? `<div class="stat"><small>${esc(t("Charge cycles"))}</small><b>${nf(s.cycles)}</b></div>` : "",
      s.power != null ? `<div class="stat"><small>${esc(t("Power draw"))}</small><b>${nf(s.power, 1)}${NB}W</b></div>` : "",
      `<div class="stat"><small>${esc(t("Charge limit"))}</small><b>${s.fullOnce ? esc(t("once 100 %")) : esc(pct(s.chargeLimit))}</b></div>`,
    ].join("");
    const hero = `<div class="card hero" data-sid="power.battery">
      <div class="batt" aria-hidden="true"><div class="shell"><i style="width:${level}%"></i></div><span class="cap"></span><span class="limit" style="left:calc(6.5px + (100% - 21px) * ${s.chargeLimit / 100} - 1px)"></span></div>
      <div>
        <div class="hero-big"><span class="num">${s.level == null ? "–" : nf(level)}<small>%</small></span><span class="st">${esc(battState(s))}</span></div>
        <div class="stats">${stats}</div>
      </div>
    </div>`;
    const limits = [60, 80, 90, 100];
    if (s.wantedLimit != null && !limits.includes(s.wantedLimit)) limits.push(s.wantedLimit);
    const limit = block({
      sid: "power.limit", icon: "heart", title: esc(t("Charge limit")), desc: esc(t("A limit below 100 % is easier on the battery")),
      head: s.fullOnce
        ? `<span class="pill">${ic("bolt")}${esc(t("Charges once to 100 %"))}</span>${button("fullstop", esc(t("Cancel")), () => setSam("fullOnce", false))}`
        : button("full", `${ic("bolt", "sm")}${esc(t("Charge fully once"))}`, () => setSam("fullOnce", true, t("Charges once to 100 %")), { attrs: `data-sid="power.full"${s.plugged ? "" : ` disabled title="${esc(t("Plug in the charger first."))}"`}` }),
      body: seg("limit", limits.sort((a, b) => a - b).map((v) => ({ v, label: pct(v) })), s.wantedLimit, (v) => setSam("chargeLimit", v), { label: t("Charge limit") }),
    });
    const modes = group("pmode", (s.modes || []).map((m) => ({ v: m.value, label: t(m.label), ...(MODE_INFO[m.value] || { icon: "gauge", desc: () => "" }) })), s.mode, (v) => setSam("mode", v, modeLabel(s, v)), {
      cls: "mcards", itemCls: "mcard", label: t("Performance mode"),
      item: (m) => `${ic(m.icon)}<b>${esc(m.label)}</b><small>${esc(m.desc())}</small>`,
    });
    const attrOff = s.attributesWritable === false;
    const adv = expander("pow-adv", { icon: "sliders", title: esc(t("Advanced")), desc: esc(t("USB charging, opening the lid, Samsung control")) }, [
      s.usbCharging == null ? "" : row({ sid: "power.usb", cls: "sub", title: esc(t("USB charging while the laptop is off")), desc: esc(t("Charges the phone even when the laptop is off")), end: toggle("usb", s.usbCharging, (v) => setSam("usbCharging", v), { label: t("USB charging while the laptop is off"), disabled: attrOff }) }),
      s.lidPower == null ? "" : row({ sid: "power.lid", cls: "sub", title: esc(t("Switch on when the lid opens")), end: toggle("lid", s.lidPower, (v) => setSam("lidPower", v), { label: t("Switch on when the lid opens"), disabled: attrOff }) }),
      row({ sid: "power.off", cls: "sub", title: esc(t("Switch off the Samsung control")), desc: esc(t("Gives Omarchy its battery menu and the modes back")),
        end: button("samoff", esc(t("Switch off")), async () => {
          const ok = await confirmDialog({ title: t("Switch off the Samsung control?"), text: t("Charge limit and the four modes go back to Omarchy. You can set them up again later."), ok: t("Switch off"), danger: true });
          if (ok) setSam("active", false, t("Switched off"));
        }, { cls: "btn danger" }) }),
    ].join(""));
    const fan = s.fanRpm ? t("The fan runs at {rpm} rpm", { rpm: nf(s.fanRpm) }) : s.fanRunning ? t("The fan is running") : t("The fan is still");
    return `${ph(esc(t("Battery & power")), intro)}
      ${ro}${hero}
      ${sec(esc(t("Charging")), `<div class="stack">${limit}</div>`)}
      ${s.modes && s.modes.length ? sec(esc(t("Performance mode")), `<div data-sid="power.mode">${modes}</div>`) : ""}
      <div class="stack" style="margin-top:var(--s2)">
        ${row({ sid: "power.fan", icon: "fan", title: esc(t("Fan and temperature")), desc: esc(fan),
          end: s.cpuTemp != null ? `<span class="pill ${s.cpuTemp > 80 ? "warn" : "neutral"}">${ic("temp")}CPU <span class="num">${nf(s.cpuTemp)}${NB}°C</span></span>` : "" })}
        ${s.kbdLight == null ? "" : row({ sid: "power.kbd", icon: "sun", title: esc(t("Keyboard light")),
          end: slider("kbd", { min: 0, max: s.kbdMax || 3, value: s.kbdLight, label: t("Keyboard light"), fmt: (v) => (v ? t("Level {n}", { n: v }) : t("Off")), onChange: (v) => setSam("kbdLight", v) }) })}
        ${adv}
      </div>`;
  }

  /* ================================================================ page: General */
  function pageGeneral() {
    const L = S.lang, A = S.about;
    return `${ph(esc(t("General")))}
      ${sec(esc(t("Language")), `<div data-sid="general.lang">${radios("lang", L.items.map((x) => ({ v: x.code, label: x.name })), L.code, async (v) => {
        const old = L.code;
        const r = await change(() => api.setLanguage(v), () => api.setLanguage(old), { reload: ["general"], msg: false });
        if (r && !(BOOT && BOOT.strings)) await useLanguage();  // in the app's window the page reloads by itself
        if (r) toast(t("Saved"));
      }, { label: t("Language") })}</div>`)}
      ${sec(esc(t("Help")), `<div class="stack">
        <button type="button" class="row" data-sid="general.guide" ${k("guide")}>${ic("book")}<div class="row-text"><div class="row-title"><span class="t">${esc(t("Open the guide"))}</span></div><div class="row-desc">${esc(t("All about screens, keys and widgets, on GitHub"))}</div></div>${ic("external", "chev")}</button>
        <button type="button" class="row" data-sid="general.folder" ${k("folder")}>${ic("folder")}<div class="row-text"><div class="row-title"><span class="t">${esc(t("Open the settings folder"))}</span></div><div class="row-desc mono" title="${esc(A.configFile || "")}">${esc(A.configPath || A.configDir)}</div></div>${ic("external", "chev")}</button>
      </div>`)}
      ${sec(esc(t("About")), `<div class="stack">${row({ sid: "general.version", icon: "info", title: "hypr-screens", desc: esc(t("For Hyprland and Omarchy")), end: `<span class="num muted">${esc(t("Version {version}", { version: A.version }))}</span>` })}</div>`)}`;
  }
  const GLOBAL = {
    guide: { click: () => api.openGuide().then(() => toast(t("The guide opens in the browser")), showError) },
    folder: { click: () => api.openConfigFolder().then(() => toast(t("Folder opened")), showError) },
  };

  /* ================================================================ page: Home */
  function pageHome() {
    const cs = conn(), fx = S.fixed || {};
    const rects = cs.map(rectOf);
    let mm = "";
    if (rects.length) {
      const minX = Math.min(...rects.map((r) => r.x)), minY = Math.min(...rects.map((r) => r.y));
      const bw = Math.max(...rects.map((r) => r.x + r.w)) - minX, bh = Math.max(...rects.map((r) => r.y + r.h)) - minY;
      const f = Math.min(220 / bw, 72 / bh);
      mm = rects.map((r) => {
        const s = scr(r.id);
        return `<span class="mm${fx.fixed === r.id && cs.length > 1 ? " fixed" : ""}" style="left:calc(50% + ${(r.x - minX - bw / 2) * f + 2}px);top:calc(50% + ${(r.y - minY - bh / 2) * f + 2}px);width:${r.w * f - 4}px;height:${r.h * f - 4}px">${esc(sname(s))}</span>`;
      }).join("");
    }
    const snd = S.sound || { outputs: [], inputs: [], apps: [] };
    const devs = [snd.outputs.find((o) => o.isDefault), snd.inputs.find((o) => o.isDefault)];
    const sm = S.samsung || {};
    const W = S.widgets || [];
    const on = W.filter((w) => w.enabled).length;
    const tileH = (icon, title, href) => `<div class="tile-h">${ic(icon)}<b>${esc(title)}</b><a href="${href}" aria-label="${esc(t("Open {name}", { name: title }))}" title="${esc(t("Open"))}">${ic("chevR", "sm")}</a></div>`;
    const fixedName = fx.fixed && scr(fx.fixed) ? sname(scr(fx.fixed)) : null;
    const modes = (sm.modes || []).map((m) => ({ v: m.value, label: "", title: t(m.label), aria: t(m.label), icon: (MODE_INFO[m.value] || { icon: "gauge" }).icon }));
    return `${ph(esc(t("Home")), esc(t("The most important things at a glance.")))}
      <div class="tiles">
        ${S.screens ? `<div class="card tile">${tileH("monitor", t("Screens"), "#/screens")}
          <div class="minimap" aria-hidden="true">${mm}</div>
          <div class="tile-foot"><span class="muted">${esc(fixedName && cs.length > 1 ? t("Fixed: {name}", { name: fixedName }) : t("{n} connected", { n: cs.length }))}</span>${fx.canSwap ? button("hswap", `${ic("swap", "sm")}${esc(t("Swap"))}`, () => change(() => api.swapFixed(), () => api.swapFixed(), { reload: ["screens"], msg: t("Swapped until the monitor is unplugged") })) : ""}</div>
        </div>` : ""}
        ${S.sound ? `<div class="card tile">${tileH("speaker", t("Sound"), "#/sound")}
          ${devs.map((d, i) => d ? `<div class="mini-vol">
            ${button(`hmute${i}`, ic(i ? (d.muted ? "micX" : "mic") : (d.muted ? "volX" : "speaker")), () => change(() => api.setMute(d.key, !d.muted), () => api.setMute(d.key, d.muted), { ...sndReload, msg: d.muted ? t("Sound on") : t("Sound off") }), { cls: "btn icon ghost mute", attrs: `aria-pressed="${d.muted}"${d.forceMute ? " disabled" : ""}`, label: d.muted ? t("Unmute {name}", { name: t(d.name) }) : t("Mute {name}", { name: t(d.name) }) })}
            <div class="mini-vol-b"><span class="t">${esc(t(d.name))}</span>${slider(`hvol${i}`, { min: 0, max: 100, value: d.volume, label: t("Volume {name}", { name: t(d.name) }), fmt: pct, disabled: d.forceMute || !d.active, onChange: (v) => change(() => api.setVolume(d.key, v), () => api.setVolume(d.key, d.volume), sndReload) })}</div>
          </div>` : "").join("")}
          <div class="tile-foot"><span class="muted">${esc(snd.apps.length ? t("Playing: {apps}", { apps: snd.apps.map((a) => a.name).join(", ") }) : t("No app is playing right now"))}</span></div>
        </div>` : ""}
        ${sm.available && sm.active ? `<div class="card tile">${tileH("battery", t("Battery & mode"), "#/power")}
          <div class="hero-big sm"><span class="num">${sm.level == null ? "–" : nf(sm.level)}<small>%</small></span><span class="st">${esc(battState(sm))}</span></div>
          <div class="meter" aria-hidden="true"><i style="width:${sm.level || 0}%"></i><b style="left:${sm.chargeLimit}%"></b></div>
          <div class="muted" style="font-size:12.5px">${esc(modeLabel(sm, sm.mode))} · ${esc(t("Charge limit"))} <span class="num">${esc(pct(sm.chargeLimit))}</span></div>
          ${modes.length ? `<div class="tile-foot">${seg("hmode", modes, sm.mode, (v) => setSam("mode", v, modeLabel(sm, v)), { cls: "seg wide", label: t("Performance mode"), item: (m) => ic(m.icon, "sm") })}</div>` : ""}
        </div>` : ""}
        ${S.widgets ? `<div class="card tile">${tileH("widgets", t("Widgets"), "#/widgets")}
          <div class="wmini">${chipsMulti("hwid", W.map((w) => ({ v: w.kind, label: t(w.name), icon: W_ICON[w.kind] })), W.filter((w) => w.enabled).map((w) => w.kind), (v, en) => setEnabled(wid(v), en), { label: t("Widgets on and off") })}</div>
          <div class="tile-foot"><span class="muted">${esc(t("{on} of {all} on", { on, all: W.length }))}</span>${button("harr", `${ic("arrange", "sm")}${esc(t("Arrange"))}`, arrange)}</div>
        </div>` : ""}
      </div>`;
  }

  /* ================================================================ search */
  function searchIndex() {
    const list = [
      { id: "screens.arrange", r: "screens", t: t("Arrange screens"), syn: t("position left right above below beside drag layout monitor") },
      { id: "screens.swap", r: "screens", t: t("Swap the fixed screen"), syn: t("fixed swap one desktop") },
      { id: "screens.position", r: "screens", t: t("Position"), syn: t("left right above below beside laptop") },
      { id: "screens.rotation", r: "screens", t: t("Rotation"), d: t("Turn the screen"), syn: t("rotate portrait upside down landscape") },
      { id: "screens.scale", r: "screens", t: t("Scale"), d: t("Makes text and windows bigger or smaller"), syn: t("size zoom dpi big small") },
      { id: "screens.mode", r: "screens", t: t("Resolution"), d: t("Resolution and refresh rate"), syn: t("hz hertz frequency pixels refresh rate") },
      { id: "screens.one", r: "screens", t: t("Always shows the same desktop"), syn: t("one desktop fixed workspace") },
      { id: "screens.newmon", r: "screens", t: t("For new monitors"), exp: "scr-adv", syn: t("new unknown default fixed") },
      { id: "screens.fav", r: "screens", t: t("Favorite"), exp: "scr-adv", syn: t("star top") },
      { id: "screens.forget", r: "screens", t: t("Forget this screen"), exp: "scr-adv", syn: t("delete remove forget") },
      ...((S.keys && S.keys.actions) || []).map((a) => ({ id: `keys.${a.id}`, r: "keys", t: t(a.title), d: t(a.desc || ""), syn: t("key shortcut minimize") })),
      { id: "keys.desktop", r: "keys", t: t("Desktop keys"), syn: t("super 1 tab workspace switch") },
      { id: "look.presets", r: "look", t: t("Window style"), d: ((S.look && S.look.presets) || []).map((p) => t(p.name)).join(", "), syn: t("preset template look theme") },
      { id: "look.gapsIn", r: "look", t: t("Inner gaps"), syn: t("gaps space between windows") },
      { id: "look.gapsOut", r: "look", t: t("Outer gaps"), syn: t("gaps edge of the screen") },
      { id: "look.rounding", r: "look", t: t("Corners"), syn: t("rounding round radius") },
      { id: "look.border", r: "look", t: t("Border"), syn: t("border width") },
      { id: "look.activeOpacity", r: "look", t: t("Opacity"), syn: t("transparent see-through opacity") },
      { id: "look.blur", r: "look", t: t("Blur"), exp: "look-adv", syn: t("blur frosted") },
      { id: "look.anim", r: "look", t: t("Animation speed"), exp: "look-adv", syn: t("animation fast slow") },
      { id: "look.colors", r: "look", t: t("Own border colors"), exp: "look-adv", syn: t("color border active gradient") },
      { id: "look.apps", r: "look", t: t("See-through apps"), exp: "look-adv", syn: t("transparent app opacity") },
      { id: "widgets.arrange", r: "widgets", t: t("Arrange widgets"), syn: t("desktop move colors font effects") },
      { id: "widgets.layouts", r: "widgets", t: t("Widget layouts"), syn: t("layout save load") },
      { id: "sound.out", r: "sound", t: t("Output"), d: t("Speakers, headphones, HDMI"), syn: t("speakers headphones hdmi volume default") },
      { id: "sound.in", r: "sound", t: t("Input"), d: t("Microphone"), syn: t("microphone mic recording") },
      { id: "sound.out", r: "sound", t: t("Force mute"), syn: t("force mute silent lock") },
      { id: "sound.apps", r: "sound", t: t("App volume"), syn: t("spotify firefox app volume output") },
      { id: "camera.toggle", r: "camera", t: t("Rotated camera"), syn: t("webcam camera on off") },
      { id: "camera.rotation", r: "camera", t: t("Turn the camera"), syn: t("webcam rotation turn") },
      { id: "camera.setup", r: "camera", t: t("Set up the camera"), syn: t("webcam setup v4l2loopback") },
      { id: "power.battery", r: "power", t: t("Battery level"), syn: t("battery health charge cycles") },
      { id: "power.limit", r: "power", t: t("Charge limit"), syn: t("charging 80 limit protect battery") },
      { id: "power.full", r: "power", t: t("Charge fully once"), syn: t("100 full charge") },
      { id: "power.mode", r: "power", t: t("Performance mode"), syn: t("saver quiet balanced performance fan") },
      { id: "power.fan", r: "power", t: t("Fan and temperature"), syn: t("cpu temperature fan") },
      { id: "power.kbd", r: "power", t: t("Keyboard light"), syn: t("backlight light keyboard") },
      { id: "power.usb", r: "power", t: t("USB charging while the laptop is off"), exp: "pow-adv", syn: t("usb charge phone") },
      { id: "power.lid", r: "power", t: t("Switch on when the lid opens"), exp: "pow-adv", syn: t("lid open switch on") },
      { id: "power.off", r: "power", t: t("Switch off the Samsung control"), exp: "pow-adv", syn: t("samsung off disable") },
      { id: "general.lang", r: "general", t: t("Language"), syn: "language english deutsch español français italiano" },
      { id: "general.guide", r: "general", t: t("Open the guide"), syn: t("help docs manual") },
      { id: "general.folder", r: "general", t: t("Open the settings folder"), syn: t("config folder file") },
      { id: "general.version", r: "general", t: t("Version"), syn: t("info about") },
    ];
    const W = S.widgets || [];
    for (const w of W) {
      list.push({ id: `widgets.${w.kind}`, r: `widgets/${w.kind}`, t: t(w.name), d: t(w.description || ""), syn: "widget", top: true });
      for (const f of w.schema.filter((x) => x.group === "content")) list.push({ id: `w.${w.kind}.${f.key}`, r: `widgets/${w.kind}`, t: `${t(w.name)}: ${t(f.label)}`, syn: f.section ? t(f.section) : "" });
    }
    const first = W.find((w) => w.enabled) || W[0];
    if (first) {
      for (const f of first.schema.filter((x) => x.group === "where")) {
        const sid = f.key === "screens" || f.key === "desktops" ? `w.where.${f.key}` : `w.${first.kind}.${f.key}`;
        list.push({ id: sid, r: `widgets/${first.kind}`, tab: "where", t: t(f.label), d: t("Widgets · where & when"), syn: "widget" });
      }
    }
    return list;
  }
  const pageName = (r) => {
    const [p, sub] = r.split("/");
    const name = pageOf(p).label();
    return sub && wid(sub) ? `${name} › ${t(wid(sub).name)}` : name;
  };
  function searchHits(q) {
    const n = norm(q.trim());
    if (!n) return [];
    const words = n.split(/\s+/);
    const pages = PAGES.filter((p) => !p.when || p.when()).map((p) => ({ id: `page.${p.id}`, r: p.id, t: p.label(), page: true }));
    const power = S.samsung && S.samsung.available;
    return [...pages, ...searchIndex().filter((e) => !e.r.startsWith("power") || power)].map((e) => {
      const tn = norm(e.t), hay = `${tn} ${norm(e.d || "")} ${norm(e.syn || "")}`;
      if (!words.every((w) => hay.includes(w))) return null;
      const score = (tn.startsWith(n) ? 0 : tn.includes(n) ? 1 : 2) - (e.page ? 0.5 : 0) - (e.top ? 0.2 : 0);
      return { e, score };
    }).filter(Boolean).sort((a, b) => a.score - b.score).slice(0, 8).map((x) => x.e);
  }
  const mark = (text, q) => {
    const i = norm(text).indexOf(norm(q.trim()));
    if (i < 0 || !q.trim()) return esc(text);
    const L = q.trim().length;
    return `${esc(text.slice(0, i))}<mark>${esc(text.slice(i, i + L))}</mark>${esc(text.slice(i + L))}`;
  };
  const Search = { hits: [], active: 0 };
  const sIn = $("#search-input"), sRes = $("#search-results");
  function drawSearch() {
    const q = sIn.value;
    if (!q.trim()) { sRes.hidden = true; sIn.setAttribute("aria-expanded", "false"); sIn.removeAttribute("aria-activedescendant"); return; }
    Search.hits = searchHits(q);
    Search.active = Math.min(Search.active, Math.max(0, Search.hits.length - 1));
    sRes.innerHTML = Search.hits.length ? Search.hits.map((e, i) => {
      const p = e.r.split("/")[0];
      const icn = e.r.includes("/") ? W_ICON[e.r.split("/")[1]] : pageOf(p).icon;
      return `<div class="sr-item" role="option" id="sr-${i}" data-i="${i}" aria-selected="${i === Search.active}">${ic(icn)}<span><b>${mark(e.t, q)}</b><small>${e.page ? esc(t("Page")) : esc(pageName(e.r))}</small></span></div>`;
    }).join("") : `<div class="sr-empty">${esc(t("Nothing found for “{query}”", { query: q.trim() }))}</div>`;
    sRes.hidden = false;
    sIn.setAttribute("aria-expanded", "true");
    if (Search.hits.length) sIn.setAttribute("aria-activedescendant", `sr-${Search.active}`); else sIn.removeAttribute("aria-activedescendant");
  }
  let pendingJump = null;
  function jump(e) {
    sIn.value = ""; drawSearch(); sIn.blur();
    if (e.exp) UI.open[e.exp] = true;
    if (e.r.startsWith("widgets/")) { UI.wtab = e.tab || "content"; UI.wtabNext = UI.wtab; }
    const target = `#/${e.r}`;
    const finish = () => {
      if (e.page) { $("#main").focus({ preventScroll: true }); return; }
      const el = $(`[data-sid="${CSS.escape(e.id)}"]`);
      if (!el) return;
      el.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      const box = el.classList.contains("row") || el.classList.contains("card") ? el : el.closest(".row, .card") || el;
      box.classList.remove("flash"); void box.offsetWidth; box.classList.add("flash");
      const f = el.matches("button, [tabindex]") ? el : ['[role="radio"][tabindex="0"]', '[role="switch"]', "input", "button", "[tabindex='0']"].map((q) => $(q, el)).find(Boolean);
      if (f) f.focus({ preventScroll: true });
    };
    if (location.hash === target) { render(); finish(); }
    else { pendingJump = finish; location.hash = target; }
  }
  sIn.addEventListener("input", () => { Search.active = 0; drawSearch(); });
  sIn.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!Search.hits.length) return;
      Search.active = (Search.active + (e.key === "ArrowDown" ? 1 : -1) + Search.hits.length) % Search.hits.length;
      drawSearch();
      const a = $(`#sr-${Search.active}`); if (a) a.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (Search.hits[Search.active]) jump(Search.hits[Search.active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (sIn.value) { sIn.value = ""; drawSearch(); } else sIn.blur();
    }
  });
  sIn.addEventListener("blur", () => setTimeout(() => { if (document.activeElement !== sIn) { sRes.hidden = true; sIn.setAttribute("aria-expanded", "false"); } }, 120));
  sIn.addEventListener("focus", () => { if (sIn.value) drawSearch(); });
  sRes.addEventListener("mousedown", (e) => e.preventDefault());
  sRes.addEventListener("click", (e) => { const it = e.target.closest(".sr-item"); if (it) jump(Search.hits[+it.dataset.i]); });

  /* ================================================================ render */
  const RENDER = { home: pageHome, screens: pageScreens, keys: pageKeys, look: pageLook, widgets: pageWidgets, sound: pageSound, camera: pageCamera, power: pagePower, general: pageGeneral };
  const main = $("#main"), page = $("#page");
  let lastRoute = "";

  function renderNav(r) {
    $("#nav-list").innerHTML = PAGES.filter((p) => !p.when || p.when()).map((p) => {
      const label = p.label();
      const dot = p.id === "look" && lookDirty() && r.page !== "look";
      return `<li><a class="nav-item" href="#/${p.id}"${p.id === r.page ? ' aria-current="page"' : ""} title="${esc(label)}">${ic(p.icon)}<span>${esc(label)}</span>${dot ? `<i class="dot" role="img" aria-label="${esc(t("Preview active"))}"></i>` : ""}</a></li>`;
    }).join("");
  }
  /* A page whose data did not load: the reason and "try again". */
  function pageMissing(p) {
    const names = p.needs.filter((n) => S.err[n]);
    if (!names.length) return `${ph(esc(p.label()))}<div class="card empty-state">${spinner()}<b>${esc(t("Loading …"))}</b></div>`;
    H.retry = { click: async () => { await reload(...p.needs); render(); } };
    return `${ph(esc(p.label()))}<div class="card empty-state">${ic("alert")}<b>${esc(t("This page could not be loaded"))}</b><span style="font-size:12.5px;max-width:520px">${esc(errText(S.err[names[0]]))}</span><button type="button" class="btn" ${k("retry")}>${ic("cycle", "sm")}${esc(t("Try again"))}</button></div>`;
  }
  const NEEDS_ALL = { home: ["screens"], widgets: ["widgets"] };  // pages that can do without the rest

  function render(enter = false) {
    const r = route();
    const key = `${r.page}/${r.sub || ""}`;
    if (key !== lastRoute) { enter = true; lastRoute = key; UI.wtab = UI.wtabNext || "content"; UI.wtabNext = null; }
    const act = document.activeElement;
    const focusK = act && act.closest && act.closest("#page, #applybar") && act.closest("[data-k]") ? act.closest("[data-k]").dataset.k : null;
    const top = main.scrollTop;
    Pop.close(false);
    H = Object.assign({}, GLOBAL);
    after = [];
    const p = pageOf(r.page);
    const needs = NEEDS_ALL[r.page] || p.needs;
    const ready = needs.every((n) => !S.err[n] && S[{ screens: "screens", keys: "keys", look: "look", sound: "sound", camera: "camera", samsung: "samsung", widgets: "widgets", general: "lang" }[n]]);
    if (r.page === "power" && S.samsung && !S.samsung.available) { location.replace("#/home"); return; }
    page.innerHTML = ready ? RENDER[r.page](r) : pageMissing(p);
    renderNav(r);
    renderApplyBar(r);
    document.title = `${p.label()} – ${t("Settings")}`;
    if (enter) {
      page.classList.remove("enter"); void page.offsetWidth; page.classList.add("enter");
      main.scrollTop = 0;
    } else main.scrollTop = top;
    after.forEach((f) => f());
    if (focusK && !enter) {
      const el = $(`[data-k="${CSS.escape(focusK)}"]`);
      if (el && !el.disabled) el.focus({ preventScroll: true });
    }
    if (pendingJump) { const f = pendingJump; pendingJump = null; requestAnimationFrame(f); }
  }

  /* ================================================================ delegated events */
  const handlerFor = (el) => el && el.dataset && H[el.dataset.on];
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-on]");
    if (!el || el.disabled || el.closest("#dialog")) return;
    const h = handlerFor(el);
    if (!h) return;
    if (h.pick && el.dataset.i != null) { h.pick(+el.dataset.i); return; }
    if (h.select) { if (Pop.isOpen && Pop.anchor === el) Pop.close(); else h.select(el); return; }
    if (h.click) h.click(e, el);
  });
  document.addEventListener("input", (e) => {
    const el = e.target;
    const h = handlerFor(el);
    if (!h) return;
    if (el.type === "range") {
      const v = Number(el.value);
      el.style.setProperty("--p", `${((v - h.min) / (h.max - h.min)) * 100}%`);
      const lab = $(`[data-val="${CSS.escape(el.dataset.on)}"]`);
      if (lab) lab.textContent = h.fmt(v);
      el.setAttribute("aria-valuetext", h.fmt(v));
      if (h.input) h.input(v);
    } else if (el.type === "color" && h.color) {
      el.parentElement.querySelector("i").style.background = el.value;
      h.color(el.value);
    } else if (h.combo) tzInput(el);
    else if (h.typing) h.typing(el.value);
  });
  document.addEventListener("change", (e) => {
    const el = e.target;
    const h = handlerFor(el);
    if (!h) return;
    if (el.type === "range") h.change(Number(el.value));
    else if (el.type === "color" && h.colorDone) h.colorDone(el.value);
    else if (h.text) h.text(el.value);
  });
  document.addEventListener("focusin", (e) => {
    const h = handlerFor(e.target);
    if (h && h.combo && !e.target.value) tzInput(e.target);
  });
  document.addEventListener("keydown", (e) => {
    if (dlg.open) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
      e.preventDefault(); Pop.close(false); sIn.focus(); sIn.select(); return;
    }
    if (Pop.isOpen) {
      if (e.key === "Escape") { e.preventDefault(); Pop.close(); return; }
      if (Pop.onKey && (pop.contains(e.target) || e.target === Pop.anchor || (Pop.anchor && Pop.anchor.contains(e.target)))) {
        if (Pop.onKey(e)) return;
      }
    }
    const tg = e.target;
    const hc = handlerFor(tg);
    if (hc && hc.combo && e.key === "ArrowDown" && !Pop.isOpen) { e.preventDefault(); tzInput(tg); return; }
    if (hc && hc.select && ["ArrowDown", "ArrowUp"].includes(e.key)) { e.preventDefault(); hc.select(tg); return; }
    if (hc && hc.stepKey && tg.getAttribute("aria-disabled") !== "true" && hc.stepKey(e)) return;
    if (tg.getAttribute && tg.getAttribute("role") === "radio") {
      const keys = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 };
      if (e.key in keys || e.key === "Home" || e.key === "End") {
        const g = tg.closest('[role="radiogroup"]');
        const items = $$('[role="radio"]:not(:disabled)', g);
        let i = items.indexOf(tg);
        i = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (i + keys[e.key] + items.length) % items.length;
        e.preventDefault();
        items[i].focus();
        items[i].click();
        return;
      }
    }
    if (tg.getAttribute && tg.getAttribute("role") === "tab" && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      const tabs = $$('[role="tab"]', tg.parentElement);
      const n = tabs[(tabs.indexOf(tg) + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
      e.preventDefault(); n.focus(); n.click(); return;
    }
    if (tg.getAttribute && tg.getAttribute("role") === "button" && tg.tagName !== "BUTTON" && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault(); tg.click(); return;
    }
    if (e.key === "Escape" && document.activeElement === sIn) sIn.blur();
  });
  document.addEventListener("pointerdown", (e) => {
    UI.pressed = true;
    if (Pop.isOpen && !pop.contains(e.target) && !(Pop.anchor && Pop.anchor.contains(e.target))) Pop.close(false);
  });
  const released = () => { UI.pressed = false; };
  document.addEventListener("pointerup", released);
  document.addEventListener("pointercancel", released);
  main.addEventListener("scroll", () => { if (Pop.isOpen) Pop.place(false); }, { passive: true });
  addEventListener("resize", () => { Pop.close(false); layoutArrange(); });
  addEventListener("hashchange", () => render());
  document.addEventListener("visibilitychange", () => { if (!document.hidden && route().page === "camera") camLoop(); });
  addEventListener("pagehide", () => {
    if (dlgCleanup) { const c = dlgCleanup; dlgCleanup = null; c(); }   // e.g. the key capture's keymap
    if (lookDirty()) api.revertLook().catch(() => {});
  });

  /* Live values change from outside (keys, apps, the charger): poll what the page shows. */
  let tickN = 0, polling = false;
  const quiet = () => document.hidden || dlg.open || Pop.isOpen || UI.pressed || UI.busy > 0 || polling;
  setInterval(async () => {
    tickN += 1;
    if (quiet()) return;
    const r = route().page;
    const want = [];
    if (r === "sound" || r === "home") want.push("sound");
    if ((r === "power" || r === "home") && tickN % 10 === 0 && S.samsung && S.samsung.available) want.push("samsung");
    if (r === "camera" && tickN % 3 === 0) want.push("camera");
    if (!want.length) return;
    polling = true;
    const before = want.map((n) => JSON.stringify(S[n] || null));
    await reload(...want);
    polling = false;
    if (want.some((n, i) => JSON.stringify(S[n] || null) !== before[i]) && !quiet()) {
      const el = document.activeElement;
      if (el && el.matches && el.matches("input[type=text], input[type=search]")) return;
      render();
    }
  }, 1000);

  /* ================================================================ texts of index.html */
  function applyStatic() {
    document.documentElement.lang = LANG || "en";
    $(".nav").setAttribute("aria-label", t("Sections"));
    $(".nav-head-text small").textContent = t("Settings");
    sIn.placeholder = t("Search a setting");
    sIn.setAttribute("aria-label", t("Search a setting"));
    $(".search-hint").textContent = t("Ctrl F");
    sRes.setAttribute("aria-label", t("Search results"));
    $("#applybar").setAttribute("aria-label", t("Changes not applied yet"));
  }
  /* Without the app's boot data (browser preview): the table from the backend. */
  async function useLanguage() {
    try { const tr = await api.translations(); STR = (tr && tr.texts) || {}; LANG = (tr && tr.code) || LANG; } catch { /* English then */ }
    applyStatic();
    render();
  }

  /* ================================================================ bridge hooks */
  /* Python calls refresh() when config.json changed from outside or the window is shown again. */
  window.hyprScreens = {
    setTheme(colors) {
      const map = { lighter_background: "lighter-background", dark_background: "dark-background", darker_background: "darker-background", dark_foreground: "dark-foreground", light_foreground: "light-foreground" };
      for (const [name, val] of Object.entries(colors || {})) document.documentElement.style.setProperty(`--c-${map[name] || name}`, val);
    },
    setMode(m) { document.documentElement.dataset.mode = m === "light" ? "light" : "dark"; },
    async refresh() {
      if (UI.busy || dlg.open) return;
      await reload(...Object.keys(loaders));
      render();
    },
  };

  /* ================================================================ start */
  (async function start() {
    const qs = new URLSearchParams(location.search);
    if (qs.get("mode")) window.hyprScreens.setMode(qs.get("mode"));
    if (!(BOOT && BOOT.strings)) {
      try { const tr = await api.translations(); STR = (tr && tr.texts) || {}; LANG = (tr && tr.code) || "en"; } catch { /* English */ }
    }
    applyStatic();
    await reload(...Object.keys(loaders));
    UI.sel = laptopId();
    if (!location.hash) history.replaceState(null, "", "#/home");
    render(true);
  })();
})();
