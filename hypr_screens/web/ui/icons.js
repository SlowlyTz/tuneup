/* Line icons (24×24, stroked by CSS) and small colored app marks. */
import { esc } from "../core/dom.js";

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
  desktops: '<rect x="3" y="5" width="8" height="6" rx="1.2"/><rect x="13" y="5" width="8" height="6" rx="1.2"/><rect x="3" y="13" width="8" height="6" rx="1.2"/><rect x="13" y="13" width="8" height="6" rx="1.2"/>',
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

/* An icon by name; cls: "sm", "xs", "lg", … */
export const ic = (name, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ""}</svg>`;

/* Colored marks for a few common apps (others get their first letter). */
const APP_IC = {
  spotify: '<circle cx="12" cy="12" r="10" fill="#1ed760"/><path d="M7 9.5c3.6-1 7.3-.6 10.2 1M7.6 12.6c2.9-.8 5.9-.4 8.3.9M8.2 15.5c2.3-.6 4.5-.3 6.3.7" stroke="#0e0e0e" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
  firefox: '<circle cx="12" cy="12" r="10" fill="#6e3fd8"/><path d="M12 2a10 10 0 0 1 9.6 7.2c-1-1.6-2.4-2.3-3.4-2.3.9 1.4 1.3 2.9 1.2 4.4A7.5 7.5 0 0 1 5.6 16 7 7 0 0 0 16.3 12c0-2.2-1.4-3.6-2.8-4 .9 1.5.2 3.3-1.6 3.3-1.3 0-2.3-1-2.3-2.4 0-2.5 2.2-4 4.3-4.4A9.8 9.8 0 0 0 12 2z" fill="#ff8a24"/>',
  alacritty: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#2b2b36"/><path d="m7 9 3 3-3 3M12 15.5h5" stroke="#f5a742" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  nautilus: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#3b82f6"/><path d="M6.5 8.5h4l1.2 1.5h5.8v6.5h-11z" fill="#dbeafe"/>',
  code: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#1f6feb"/><path d="m9.5 8.5-3.5 3.5 3.5 3.5M14.5 8.5 18 12l-3.5 3.5" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  obsidian: '<rect x="2" y="2" width="20" height="20" rx="5" fill="#2a1f45"/><path d="m12 5 5 5-2 8.5H9L7 10z" fill="#a78bfa"/>',
  signal: '<circle cx="12" cy="12" r="10" fill="#3a76f0"/><path d="M12 6.5a5.5 5.5 0 0 0-4.8 8.2L6.5 17.5l2.8-.7A5.5 5.5 0 1 0 12 6.5z" fill="#fff"/>',
};

/* An app mark for a window class or icon names ("org.gnome.Nautilus", ["spotify-client", "spotify"]). */
export function appIcon(names, cls = "app-ic") {
  const list = (Array.isArray(names) ? names : [names]).map((n) => String(n || "").toLowerCase());
  const hit = Object.keys(APP_IC).find((id) => list.some((n) => n === id || n.split(/[.\-_ ]/).includes(id)));
  const first = (list.find(Boolean) || "?").split(".").pop();
  const body = hit ? APP_IC[hit]
    : `<rect x="2" y="2" width="20" height="20" rx="5" fill="var(--ctl-hover)"/><text x="12" y="16" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">${esc(first[0].toUpperCase())}</text>`;
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}

/* A monitor turned by `rot` degrees (the rotation choices). */
export const monGlyph = (rot) =>
  `<svg class="glyph rot${rot}" viewBox="0 0 40 40" aria-hidden="true"><rect x="6" y="8" width="28" height="18" rx="2.5"/><path d="M15 32.5h10M20 26v6.5"/><path d="M10.5 12.5h8" stroke-width="2.4"/></svg>`;
