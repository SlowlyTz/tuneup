/* hypr-screens – fake backend for opening index.html in a plain browser.
 *
 * The UI talks only to `window.api`. In the real window the WebKit bridge
 * puts the Python backend (hypr_screens/api/) there: every method is async,
 * takes JSON arguments and returns plain JSON; a failure rejects with an
 * error that has {code, message}. This file returns exactly the same shapes
 * (the data below was produced by hypr_screens.api against a fake Hyprland) and keeps
 * all state in memory. Nothing here touches the system.
 *
 * Shapes, error codes and every method: hypr_screens/web/API.md.
 */
(function () {
  "use strict";

  const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
  const wait = (ms = 30) => new Promise((r) => setTimeout(r, ms));
  const reply = async (v) => { await wait(); return clone(v); };
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  /* What the bridge rejects with: err.code (stable) and err.message (English). */
  class ApiError extends Error {
    constructor(code, message) { super(message); this.name = "ApiError"; this.code = code; }
  }
  const fail = (code, message) => { throw new ApiError(code, message); };
  const need = (ok, code, message) => { if (!ok) fail(code, message); };
  const isNum = (v) => typeof v === "number" && Number.isFinite(v);

  /* ---------- data: hypr_screens.api's answers against a fake Hyprland ---------- */
  const FIXTURE = {
    "screens": [
      {"id": "Samsung Display Corp.|0x4159|", "name": "Laptop", "description": "Samsung Display Corp. 0x4159", "connector": "eDP-1", "laptop": true, "connected": true, "favorite": false, "lastSeen": "2026-10-18", "modes": [{"w": 1920, "h": 1080, "rates": [144.0, 60.0], "modes": ["1920x1080@144.00", "1920x1080@60.00"], "preferred": true}, {"w": 1680, "h": 1050, "rates": [60.0], "modes": ["1680x1050@60.00"], "preferred": false}, {"w": 1280, "h": 720, "rates": [60.0], "modes": ["1280x720@60.00"], "preferred": false}], "hypr": {"rotation": 0, "flipped": false, "scale": 1.25, "mode": "1920x1080@144.00", "one_desktop": true}, "settings": {"rotation": {"value": null, "when": [], "active": false}, "scale": {"value": 1.25, "when": [], "active": true}, "mode": {"value": "1920x1080@144.00", "when": [], "active": true}, "one_desktop": {"value": true, "when": ["HP Inc.|HP 32f|3CM1230QVW"], "active": true}}, "position": {"x": 192, "y": 1080, "w": 1536, "h": 864}, "side": null, "summary": "1920x1080@144.00 · one desktop if HP 32f · 1.25×"},
      {"id": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "name": "Fujitsu B27-9 TS QHD", "description": "Fujitsu Siemens Computers GmbH B27-9 TS QHD YVEB021757", "connector": "DP-2", "laptop": false, "connected": false, "favorite": true, "lastSeen": "2026-10-18", "modes": [{"w": 2560, "h": 1440, "rates": [59.95], "modes": ["2560x1440@59.95"], "preferred": true}, {"w": 1920, "h": 1080, "rates": [60.0], "modes": ["1920x1080@60.00"], "preferred": false}, {"w": 1280, "h": 720, "rates": [60.0], "modes": ["1280x720@60.00"], "preferred": false}], "hypr": null, "settings": {"rotation": {"value": null, "when": [], "active": false}, "scale": {"value": 1.25, "when": [], "active": true}, "mode": {"value": null, "when": [], "active": false}, "position": {"value": null, "when": [], "active": false}, "one_desktop": {"value": null, "when": [], "active": false}}, "position": null, "side": null, "summary": "1.25×"},
      {"id": "HP Inc.|HP 32f|3CM1230QVW", "name": "HP 32f", "description": "HP Inc. HP 32f 3CM1230QVW", "connector": "DP-3", "laptop": false, "connected": true, "favorite": false, "lastSeen": "2026-10-18", "modes": [{"w": 1920, "h": 1080, "rates": [75.0, 60.0], "modes": ["1920x1080@75.00", "1920x1080@60.00"], "preferred": true}, {"w": 1680, "h": 1050, "rates": [59.95], "modes": ["1680x1050@59.95"], "preferred": false}, {"w": 1280, "h": 1024, "rates": [75.03, 60.02], "modes": ["1280x1024@75.03", "1280x1024@60.02"], "preferred": false}, {"w": 1280, "h": 720, "rates": [60.0], "modes": ["1280x720@60.00"], "preferred": false}], "hypr": {"rotation": 0, "flipped": false, "scale": 1.0, "mode": "1920x1080@60.00", "one_desktop": false}, "settings": {"rotation": {"value": null, "when": [], "active": false}, "scale": {"value": null, "when": [], "active": false}, "mode": {"value": null, "when": [], "active": false}, "position": {"value": "above", "when": [], "active": true}, "one_desktop": {"value": null, "when": [], "active": false}}, "position": {"x": 0, "y": 0, "w": 1920, "h": 1080}, "side": "above", "summary": "above laptop"},
      {"id": "LG Electronics|LG TV|0x01010101", "name": "LG TV", "description": "LG Electronics LG TV 0x01010101", "connector": "HDMI-A-1", "laptop": false, "connected": false, "favorite": false, "lastSeen": "2026-10-18", "modes": [{"w": 3840, "h": 2160, "rates": [60.0, 30.0], "modes": ["3840x2160@60.00", "3840x2160@30.00"], "preferred": true}, {"w": 2560, "h": 1440, "rates": [59.95], "modes": ["2560x1440@59.95"], "preferred": false}, {"w": 1920, "h": 1080, "rates": [120.0, 60.0], "modes": ["1920x1080@120.00", "1920x1080@60.00"], "preferred": false}], "hypr": null, "settings": {"rotation": {"value": null, "when": [], "active": false}, "scale": {"value": 2, "when": [], "active": true}, "mode": {"value": null, "when": [], "active": false}, "position": {"value": null, "when": [], "active": false}, "one_desktop": {"value": null, "when": [], "active": false}}, "position": null, "side": null, "summary": "2×"}
    ],
    "fixed": {"fixed": "Samsung Display Corp.|0x4159|", "desk": "HP Inc.|HP 32f|3CM1230QVW", "role": "panel", "swapped": false, "panel": "Samsung Display Corp.|0x4159|", "external": "HP Inc.|HP 32f|3CM1230QVW", "canSwap": true, "fixedWorkspace": 99},
    "keys": {
      "actions": [
        {"id": "minimizer_menu", "title": "Open window list", "desc": "Opens the list of minimized windows (there: Enter, Shift+Enter, “-” to peek).", "slots": ["SUPER + PERIOD", "SUPER + SHIFT + F23"]},
        {"id": "stash", "title": "Hide window", "desc": "Hides the active window.", "slots": ["SUPER + M", null]},
        {"id": "stash_others", "title": "Hide all others", "desc": "Hides all other windows on this desktop.", "slots": [null, null]},
        {"id": "pop", "title": "Bring back last", "desc": "Brings back the window hidden last.", "slots": ["SUPER + I", null]},
        {"id": "pop_all", "title": "Bring back all", "desc": "Brings back all hidden windows of this desktop.", "slots": ["SUPER + SHIFT + I", null]},
        {"id": "undo", "title": "Undo", "desc": "Undoes the last hiding or bringing back.", "slots": ["SUPER + U", null]}
      ],
      "hyprBinds": {"SUPER + Q": "Close window", "SUPER + W": "Close window", "SUPER + RETURN": "Terminal", "SUPER + SPACE": "Launch apps", "SUPER + F": "Full screen", "SUPER + B": "Browser", "SUPER + T": "Toggle floating", "SUPER + L": "Lock screen", "SUPER + K": "Show key bindings", "SUPER + E": "File manager", "SUPER + ESCAPE": "System menu"},
      "options": {"desktop_keys": false, "default_fixed": "external"},
      "defaultFixedChoices": [
        {"value": "off", "label": "Off – both screens have desktops"},
        {"value": "external", "label": "The external monitor"},
        {"value": "panel", "label": "The laptop"}
      ]
    },
    "look": {
      "values": {"gapsIn": 5, "gapsOut": 10, "rounding": 10, "border": 2, "blur": true, "blurSize": 6, "blurPasses": 2, "activeOpacity": 1.0, "inactiveOpacity": 1.0, "apps": [{"class": "Alacritty", "active": 0.9, "inactive": 0.8}], "animSpeed": 1.0, "borderColors": null, "borderAngle": 0},
      "saved": {"activeOpacity": 1.0, "blur": true, "blurPasses": 2, "blurSize": 6, "border": 2, "gapsIn": 5, "gapsOut": 10, "inactiveOpacity": 1.0, "rounding": 10, "apps": [{"class": "Alacritty", "active": 0.9, "inactive": 0.8}]},
      "previewing": false,
      "apps": [
        {"id": "Alacritty", "name": "Alacritty"},
        {"id": "code", "name": "code"},
        {"id": "firefox", "name": "firefox"},
        {"id": "obsidian", "name": "obsidian"},
        {"id": "org.gnome.Nautilus", "name": "org.gnome.Nautilus"},
        {"id": "spotify", "name": "spotify"}
      ],
      "presets": [
        {"name": "Clean", "values": {"gapsIn": 0, "gapsOut": 0, "rounding": 0, "border": 1, "blur": false, "blurSize": 8, "blurPasses": 1, "activeOpacity": 1.0, "inactiveOpacity": 1.0, "animSpeed": 1.0, "borderColors": null, "borderAngle": 0, "apps": []}},
        {"name": "Soft", "values": {"gapsIn": 5, "gapsOut": 12, "rounding": 12, "border": 2, "blur": true, "blurSize": 6, "blurPasses": 2, "activeOpacity": 1.0, "inactiveOpacity": 0.95, "animSpeed": 1.0, "borderColors": null, "borderAngle": 0, "apps": []}},
        {"name": "Glass", "values": {"gapsIn": 6, "gapsOut": 14, "rounding": 14, "border": 1, "blur": true, "blurSize": 10, "blurPasses": 3, "activeOpacity": 0.9, "inactiveOpacity": 0.8, "animSpeed": 1.0, "borderColors": null, "borderAngle": 0, "apps": []}}
      ],
      "ranges": {"gapsIn": {"min": 0, "max": 30, "step": 1}, "gapsOut": {"min": 0, "max": 60, "step": 1}, "rounding": {"min": 0, "max": 30, "step": 1}, "border": {"min": 0, "max": 8, "step": 1}, "blurSize": {"min": 1, "max": 20, "step": 1}, "blurPasses": {"min": 1, "max": 4, "step": 1}, "activeOpacity": {"min": 0.3, "max": 1.0, "step": 0.01}, "inactiveOpacity": {"min": 0.3, "max": 1.0, "step": 0.01}, "animSpeed": {"min": 0.25, "max": 3.0, "step": 0.05}, "borderAngle": {"min": 0, "max": 355, "step": 5}, "appOpacity": {"min": 0.3, "max": 1.0, "step": 0.01}},
      "themeBorder": {"colors": ["#89b4faff", "#89b4faff"], "angle": 0}
    },
    "sound": {
      "outputs": [
        {"key": "alsa_card.pci-0000_00_1f.3:[Out] Speaker", "kind": "sink", "name": "Laptop speakers", "sub": "HD Audio", "icon": "speaker", "volume": 42, "muted": false, "isDefault": true, "forceMute": false, "active": true, "connected": true, "node": "alsa_output.pci-0000_00_1f.3.speaker"},
        {"key": "alsa_card.pci-0000_00_1f.3:[Out] Headphones", "kind": "sink", "name": "Headphones (jack)", "sub": "HD Audio", "icon": "headphones", "volume": 0, "muted": false, "isDefault": false, "forceMute": false, "active": false, "connected": true, "node": null},
        {"key": "alsa_card.pci-0000_00_1f.3:[Out] HDMI1", "kind": "sink", "name": "Screen HP 32f", "sub": "HD Audio", "icon": "tv", "volume": 0, "muted": true, "isDefault": false, "forceMute": true, "active": true, "connected": true, "node": "alsa_output.pci-0000_00_1f.3.hdmi"}
      ],
      "inputs": [
        {"key": "alsa_card.pci-0000_00_1f.3:[In] Mic1", "kind": "source", "name": "Laptop microphone", "sub": "HD Audio", "icon": "mic", "volume": 68, "muted": false, "isDefault": true, "forceMute": false, "active": true, "connected": true, "node": "alsa_input.pci-0000_00_1f.3.mic"}
      ],
      "apps": [
        {"key": "app:51", "index": 51, "name": "Spotify", "sub": "", "icons": ["spotify-client", "spotify"], "volume": 80, "muted": false, "paused": false, "output": "alsa_card.pci-0000_00_1f.3:[Out] Speaker"},
        {"key": "app:63", "index": 63, "name": "Firefox", "sub": "YouTube", "icons": ["firefox"], "volume": 100, "muted": false, "paused": true, "output": "alsa_card.pci-0000_00_1f.3:[Out] Speaker"}
      ]
    },
    "camera": {"installed": false, "enabled": true, "rotation": 0, "rotations": [0, 90, 180, 270], "state": null, "inUse": false, "users": 0, "device": "Integrated Camera", "hasCamera": true, "virtualName": "Rotated Camera"},
    "samsung": {"available": true, "active": true, "writable": true, "level": 76, "status": "Discharging", "charging": false, "plugged": false, "health": 94, "cycles": 212, "power": 8.4, "remainingMinutes": 320, "fullInMinutes": null, "chargeLimit": 80, "wantedLimit": 80, "fullOnce": false, "mode": "balanced", "modes": [{"value": "low-power", "label": "Saver"}, {"value": "quiet", "label": "Quiet"}, {"value": "balanced", "label": "Balanced"}, {"value": "performance", "label": "Performance"}], "fanRpm": null, "fanRunning": false, "cpuTemp": 52, "kbdLight": 2, "kbdMax": 3, "usbCharging": false, "lidPower": true, "attributesWritable": true},
    "widgets": [
      {"kind": "visualizer", "name": "Visualizer", "description": "Bars that move with the sound playing right now.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"player": "", "bars": 32, "style": "bottom", "sensitivity": 100, "smoothing": 77, "peaks": false}, "where": {"where": "desktop", "screens": "laptop", "same_place": true, "desktops": ["1"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "player", "group": "content", "type": "choice", "label": "React to", "choices": [{"value": "", "label": "Whatever plays"}, {"value": "spotify", "label": "Spotify"}, {"value": "firefox", "label": "Firefox"}], "dynamic": true, "default": "", "hint": "With an app picked, only its music counts – the visualizer then hears only that app."}, {"key": "bars", "group": "content", "type": "number", "label": "Bars", "min": 8, "max": 64, "step": 1, "unit": "", "default": 32}, {"key": "style", "group": "content", "type": "choice", "label": "Style", "default": "bottom", "choices": [{"value": "bottom", "label": "Bars from the bottom"}, {"value": "mirrored", "label": "Mirrored from the middle"}, {"value": "wave", "label": "Wave"}, {"value": "dots", "label": "Dots"}, {"value": "circle", "label": "Circle"}]}, {"key": "sensitivity", "group": "content", "type": "number", "label": "Sensitivity", "min": 20, "max": 300, "step": 10, "unit": "%", "default": 100, "section": "Motion"}, {"key": "smoothing", "group": "content", "type": "number", "label": "Smoothing", "min": 0, "max": 100, "step": 5, "unit": "%", "default": 77, "section": "Motion"}, {"key": "peaks", "group": "content", "type": "toggle", "label": "Peak marks", "default": false, "section": "Motion"}, {"key": "where", "group": "where", "type": "choice", "label": "Where", "default": "both", "choices": [{"value": "bar", "label": "In the bar"}, {"value": "desktop", "label": "On the desktop"}, {"value": "both", "label": "Bar and desktop"}]}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "lyrics", "name": "Lyrics", "description": "The words of the song playing, in time with the music (from lrclib.net).", "enabled": false, "placed": false, "onDesktop": false, "missing": [], "content": {"player": "", "highlight": "line", "lines": 3, "hide_paused": false}, "where": {"screens": "all", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "player", "group": "content", "type": "choice", "label": "React to", "choices": [{"value": "", "label": "Whatever plays"}, {"value": "spotify", "label": "Spotify"}, {"value": "firefox", "label": "Firefox"}], "dynamic": true, "default": "", "hint": "With an app picked, only its music counts – the visualizer then hears only that app."}, {"key": "highlight", "group": "content", "type": "choice", "label": "Highlight", "default": "line", "choices": [{"value": "line", "label": "Current line"}, {"value": "word", "label": "Word by word"}, {"value": "off", "label": "Off"}], "hint": "Word by word follows the singing; most songs only have times per line, then the words are spread over the line."}, {"key": "lines", "group": "content", "type": "number", "label": "Lines", "min": 1, "max": 10, "step": 1, "unit": "", "default": 3}, {"key": "hide_paused", "group": "content", "type": "toggle", "label": "Hide while paused", "default": false}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "clock", "name": "Clock", "description": "A big clock with the date.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"clock_style": "digital", "hours": "24", "seconds": false, "date": true, "weekday": true, "date_format": "long", "date_pattern": "", "zone2": ""}, "where": {"screens": "laptop", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "clock_style", "group": "content", "type": "choice", "label": "Style", "default": "digital", "choices": [{"value": "digital", "label": "Digital"}, {"value": "analog", "label": "Analog"}, {"value": "flip", "label": "Flip cards"}, {"value": "words", "label": "In words"}]}, {"key": "hours", "group": "content", "type": "choice", "label": "Time format", "default": "24", "choices": [{"value": "24", "label": "24-hour"}, {"value": "12", "label": "12-hour"}]}, {"key": "seconds", "group": "content", "type": "toggle", "label": "Show seconds", "default": false}, {"key": "date", "group": "content", "type": "toggle", "label": "Show the date", "default": true, "section": "Date"}, {"key": "weekday", "group": "content", "type": "toggle", "label": "Show the weekday", "default": true, "section": "Date", "enabledBy": "date"}, {"key": "date_format", "group": "content", "type": "choice", "label": "Date format", "default": "long", "choices": [{"value": "long", "label": "Long (3 October)"}, {"value": "medium", "label": "Medium (3 Oct 2026)"}, {"value": "short", "label": "Short (as the language writes it)"}, {"value": "iso", "label": "ISO (2026-10-03)"}, {"value": "custom", "label": "Own pattern"}], "section": "Date", "enabledBy": "date"}, {"key": "date_pattern", "group": "content", "type": "text", "label": "Own pattern, e.g. dd.MM.yyyy or dddd d MMMM", "maxLength": 60, "default": "", "showIf": {"date_format": "custom"}, "section": "Date", "enabledBy": "date"}, {"key": "zone2", "group": "content", "type": "text", "format": "timezone", "label": "Second time zone", "default": ""}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "system", "name": "System", "description": "CPU, memory and temperature with a curve of the last two minutes.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"cpu": true, "memory": true, "temperature": true, "curves": true}, "where": {"screens": "external", "same_place": true, "desktops": ["fixed"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "cpu", "group": "content", "type": "toggle", "label": "CPU usage", "default": true}, {"key": "memory", "group": "content", "type": "toggle", "label": "Memory", "default": true}, {"key": "temperature", "group": "content", "type": "toggle", "label": "Temperature", "default": true}, {"key": "curves", "group": "content", "type": "toggle", "label": "Show the curves", "default": true}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "nowplaying", "name": "Now Playing", "description": "The song playing with its cover, a progress bar and buttons.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"player": "spotify", "np_layout": "row", "show_cover": true, "show_title": true, "show_artist": true, "show_album": false, "show_progress": true, "show_time": true, "show_controls": true, "hide_idle": true}, "where": {"screens": "all", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "player", "group": "content", "type": "choice", "label": "React to", "choices": [{"value": "", "label": "Whatever plays"}, {"value": "spotify", "label": "Spotify"}, {"value": "firefox", "label": "Firefox"}], "dynamic": true, "default": "", "hint": "With an app picked, only its music counts – the visualizer then hears only that app."}, {"key": "np_layout", "group": "content", "type": "choice", "label": "Layout", "default": "row", "choices": [{"value": "row", "label": "Cover beside the text"}, {"value": "column", "label": "Cover above the text"}]}, {"key": "show_cover", "group": "content", "type": "toggle", "label": "Cover", "default": true, "section": "Parts"}, {"key": "show_title", "group": "content", "type": "toggle", "label": "Title", "default": true, "section": "Parts"}, {"key": "show_artist", "group": "content", "type": "toggle", "label": "Artist", "default": true, "section": "Parts"}, {"key": "show_album", "group": "content", "type": "toggle", "label": "Album", "default": false, "section": "Parts"}, {"key": "show_progress", "group": "content", "type": "toggle", "label": "Progress bar", "default": true, "section": "Parts"}, {"key": "show_time", "group": "content", "type": "toggle", "label": "Time", "default": true, "section": "Parts"}, {"key": "show_controls", "group": "content", "type": "toggle", "label": "Buttons", "default": true, "section": "Parts"}, {"key": "hide_idle", "group": "content", "type": "toggle", "label": "Hide while nothing plays", "default": true}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "weather", "name": "Weather", "description": "The weather at the place set in Omarchy's weather panel.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"units": "c", "show_place": true, "show_details": true, "show_forecast": true}, "where": {"screens": "all", "same_place": true, "desktops": ["1", "2"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "units", "group": "content", "type": "choice", "label": "Units", "default": "c", "choices": [{"value": "c", "label": "Celsius"}, {"value": "f", "label": "Fahrenheit"}]}, {"key": "show_place", "group": "content", "type": "toggle", "label": "Place", "default": true}, {"key": "show_details", "group": "content", "type": "toggle", "label": "Details", "default": true}, {"key": "show_forecast", "group": "content", "type": "toggle", "label": "Next days", "default": true}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "calendar", "name": "Calendar", "description": "This month with today marked.", "enabled": true, "placed": true, "onDesktop": true, "missing": [], "content": {"week_start": "monday", "show_month": true, "show_weeks": false}, "where": {"screens": "laptop", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "week_start", "group": "content", "type": "choice", "label": "Week starts on", "default": "monday", "choices": [{"value": "monday", "label": "Monday"}, {"value": "sunday", "label": "Sunday"}]}, {"key": "show_month", "group": "content", "type": "toggle", "label": "Month name", "default": true}, {"key": "show_weeks", "group": "content", "type": "toggle", "label": "Week numbers", "default": false}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "battery", "name": "Battery", "description": "The battery's charge as a ring, with the time left.", "enabled": false, "placed": false, "onDesktop": false, "missing": [], "content": {"show_percent": true, "show_remaining": true, "low": 20}, "where": {"screens": "all", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "show_percent", "group": "content", "type": "toggle", "label": "Percent", "default": true}, {"key": "show_remaining", "group": "content", "type": "toggle", "label": "Time left", "default": true}, {"key": "low", "group": "content", "type": "number", "label": "Low at", "min": 5, "max": 50, "step": 5, "unit": "%", "default": 20}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "network", "name": "Network", "description": "Download and upload right now, with curves.", "enabled": false, "placed": false, "onDesktop": false, "missing": [], "content": {"curves": true}, "where": {"screens": "all", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "curves", "group": "content", "type": "toggle", "label": "Show the curves", "default": true}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]},
      {"kind": "disk", "name": "Disks", "description": "How full every disk is.", "enabled": false, "placed": false, "onDesktop": false, "missing": [], "content": {"show_free": false}, "where": {"screens": "all", "same_place": true, "desktops": ["all"], "only_empty": false, "hide_on_battery": false, "above": false}, "schema": [{"key": "show_free", "group": "content", "type": "toggle", "label": "Free space instead of used", "default": false}, {"key": "screens", "group": "where", "type": "choice", "label": "Screens", "choices": [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"}, {"value": "all", "label": "All screens"}, {"value": "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757", "label": "Fujitsu B27-9 TS QHD"}, {"value": "HP Inc.|HP 32f|3CM1230QVW", "label": "HP 32f"}, {"value": "LG Electronics|LG TV|0x01010101", "label": "LG TV"}], "dynamic": true, "default": "all"}, {"key": "same_place", "group": "where", "type": "toggle", "label": "Same place on every screen", "default": true, "hint": "Off: arrange it on each screen on its own."}, {"key": "desktops", "group": "where", "type": "multi", "label": "Desktops", "default": ["all"], "choices": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}, {"value": "6", "label": "6"}, {"value": "7", "label": "7"}, {"value": "8", "label": "8"}, {"value": "9", "label": "9"}, {"value": "10", "label": "10"}, {"value": "fixed", "label": "Fixed screen"}], "hint": "None picked: on every desktop."}, {"key": "only_empty", "group": "where", "type": "toggle", "label": "Only on an empty desktop", "default": false}, {"key": "hide_on_battery", "group": "where", "type": "toggle", "label": "Hide on battery", "default": false}, {"key": "above", "group": "where", "type": "toggle", "label": "Above the windows", "default": false}]}
    ],
    "layouts": {
      "current": "Desk",
      "items": ["Desk", "Away"],
      "layouts": [
        {"name": "Desk", "screens": [], "screenNames": [], "auto": false, "matchesNow": false},
        {"name": "Away", "screens": [], "screenNames": [], "auto": false, "matchesNow": false}
      ],
      "connected": ["HP Inc.|HP 32f|3CM1230QVW", "Samsung Display Corp.|0x4159|"]
    },
    "enforcement": {"enabled": true, "running": true, "fixes": [{"time": 1792310363.0, "area": "look", "what": "Window look", "detail": "gaps_in 0 instead of 5"}, {"time": 1792310280.0, "area": "sound", "what": "Force mute", "detail": "Laptop speakers"}, {"time": 1792309500.0, "area": "keys", "what": "Shortcuts", "detail": "SUPER + M also runs Emoji picker"}, {"time": 1792306800.0, "area": "screens", "what": "Screen arrangement", "detail": "DP-3 moved or changed"}], "backedOff": [{"area": "look", "what": "Window look", "until": 1792310393.0}]},
    "language": {"code": "de", "items": [{"code": "en", "name": "English"}, {"code": "de", "name": "Deutsch"}, {"code": "es", "name": "Español"}, {"code": "fr", "name": "Français"}, {"code": "it", "name": "Italiano"}]},
    "about": {"version": "1.0.0", "configDir": "~/.config/tuneup", "configPath": "/home/you/.config/tuneup", "configFile": "/home/you/.config/tuneup/config.json", "guideUrl": "https://github.com/SlowlyTz/tuneup/tree/master/docs", "repoUrl": "https://github.com/SlowlyTz/tuneup", "releasesUrl": "https://github.com/SlowlyTz/tuneup/releases"},
    "welcome": {"show": true, "kind": "installed", "from": null, "to": "1.0.0", "releasesUrl": "https://github.com/SlowlyTz/tuneup/releases"},
    "update": {"current": "1.0.0", "latest": "1.1.0", "available": true, "commitsBehind": 7, "canUpdate": true, "reason": null},
    "updateStatus": {"state": "idle", "from": null, "to": null, "log": [], "error": null},
    "theme": {"mode": "dark", "colors": {"background": "#1e1e2e", "foreground": "#cdd6f4", "accent": "#89b4fa", "selection": "#45475a", "lighter_background": "#313244", "dark_foreground": "#6c7086", "red": "#f38ba8", "green": "#a6e3a1", "menu_background": "#1e1e2e", "menu_text": "#cdd6f4"}, "font": "JetBrainsMono Nerd Font", "rounding": 10},
    "translations": {"code": "de", "texts": {"Screens": "Bildschirme"}}
  };

  const db = clone(FIXTURE);
  db.lookShown = null; /* a preview: the look on screen but not saved */
  db.forceBefore = {};
  db.layoutStore = {}; /* name -> widgets as saved */
  for (const name of db.layouts.items) db.layoutStore[name] = snapshot();
  /* The fixture saved "Away" with the weather off; keep that difference. */
  if (db.layoutStore.Away) db.layoutStore.Away.find((w) => w.kind === "weather").enabled = false;

  /* ---------- screens ---------- */
  const ROTATIONS = [0, 90, 180, 270];
  const SIDES = ["left", "right", "above", "below"];
  const OPPOSITE = { left: "right", right: "left", above: "below", below: "above" };
  const screen = (sid) => db.screens.find((s) => s.id === sid) || fail("unknown_screen", `unknown screen: ${sid}`);
  const connectedIds = () => db.screens.filter((s) => s.connected).map((s) => s.id);

  function parseMode(mode) {
    const [wh, rate] = String(mode).split("@");
    const [w, h] = wh.split("x").map(Number);
    return { w, h, rate: Number(rate) };
  }
  /* The value in force: the setting if its condition holds, else Hyprland's. */
  function effective(s, key) {
    const st = s.settings[key];
    if (st && st.value != null && (!st.when.length || st.when.every((id) => connectedIds().includes(id)))) return st.value;
    return null;
  }
  function refreshActive() {
    for (const s of db.screens) {
      for (const st of Object.values(s.settings)) {
        st.active = st.value != null && (!st.when.length || st.when.every((id) => connectedIds().includes(id)));
      }
      s.side = s.settings.position ? s.settings.position.value : null;
    }
  }
  /* Like apply.py: active settings go live, then sides become coordinates. */
  function applyAll() {
    const applied = [];
    for (const s of db.screens.filter((x) => x.connected)) {
      const before = clone(s.hypr);
      const rot = effective(s, "rotation"), sc = effective(s, "scale"), mode = effective(s, "mode");
      if (rot != null) s.hypr.rotation = rot;
      if (sc != null) s.hypr.scale = sc === "auto" ? (s.laptop ? 1.25 : 1) : sc;
      if (mode != null) {
        const m = mode === "preferred" ? s.modes.find((x) => x.preferred) : parseMode(mode);
        const rate = mode === "preferred" ? m.rates[0] : m.rate || 60;
        s.hypr.mode = `${m.w}x${m.h}@${Number(rate).toFixed(2)}`;
      }
      const m = parseMode(s.hypr.mode);
      let w = Math.round(m.w / s.hypr.scale), h = Math.round(m.h / s.hypr.scale);
      if (s.hypr.rotation % 180) [w, h] = [h, w];
      s.position = { ...(s.position || { x: 0, y: 0 }), w, h };
      if (!eq(before, s.hypr)) applied.push(s.connector);
    }
    layout();
    for (const s of db.screens) {
      s.hypr = s.connected ? { ...s.hypr, one_desktop: db.fixed.fixed === s.id } : null;
      if (!s.connected) s.position = null;
    }
    return applied;
  }
  /* apply.layout: every placed screen edge to edge with the laptop, centred. */
  function layout() {
    const conn = db.screens.filter((s) => s.connected);
    const anchor = conn.find((s) => s.laptop) || conn[0];
    if (!anchor) return;
    const placed = conn.filter((s) => s !== anchor && effective(s, "position"));
    if (!placed.length) return;
    const A = anchor.position;
    const spots = new Map([[anchor, { x: 0, y: 0 }]]);
    const reach = { left: 0, right: A.w, above: 0, below: A.h };
    for (const s of placed.sort((a, b) => a.connector.localeCompare(b.connector))) {
      const side = effective(s, "position"), { w, h } = s.position;
      if (side === "left") { reach.left -= w; spots.set(s, { x: reach.left, y: Math.floor((A.h - h) / 2) }); }
      if (side === "right") { spots.set(s, { x: reach.right, y: Math.floor((A.h - h) / 2) }); reach.right += w; }
      if (side === "above") { reach.above -= h; spots.set(s, { x: Math.floor((A.w - w) / 2), y: reach.above }); }
      if (side === "below") { spots.set(s, { x: Math.floor((A.w - w) / 2), y: reach.below }); reach.below += h; }
    }
    const left = Math.min(...[...spots.values()].map((p) => p.x)), top = Math.min(...[...spots.values()].map((p) => p.y));
    for (const [s, p] of spots) s.position = { ...s.position, x: p.x - left, y: p.y - top };
  }
  function sideOf(r, a) {
    const dx = (r.x + r.w / 2 - (a.x + a.w / 2)) / Math.max(1, (r.w + a.w) / 2);
    const dy = (r.y + r.h / 2 - (a.y + a.h / 2)) / Math.max(1, (r.h + a.h) / 2);
    return Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "below" : "above");
  }
  /* A drag's {x, y} -> [the screen whose side changes, the side] (api.side_from_point). */
  function sideFromPoint(s, p) {
    need(isNum(p.x) && isNum(p.y), "bad_value", "position needs numbers x and y");
    need(s.connected, "not_connected", "only a connected screen can be dragged; pick a side instead");
    const conn = db.screens.filter((x) => x.connected);
    const others = conn.filter((x) => x !== s);
    const anchor = conn.find((x) => x.laptop) || others[0];
    need(anchor, "bad_value", "there is no other screen to place it next to");
    const rect = { x: p.x, y: p.y, w: s.position.w, h: s.position.h };
    if (anchor !== s) return [s, sideOf(rect, anchor.position)];
    need(others.length === 1, "bad_value", "drag one of the other screens: the laptop stays where it is");
    return [others[0], OPPOSITE[sideOf(rect, others[0].position)]];
  }
  function cleanValue(s, key, value) {
    if (value == null) return null;
    if (key === "rotation") need(ROTATIONS.includes(value), "bad_value", "rotation must be one of 0, 90, 180, 270");
    if (key === "scale") need(value === "auto" || (isNum(value) && value >= 0.25 && value <= 4), "bad_value", "scale must be \"auto\" or a number from 0.25 to 4");
    if (key === "mode") need(value === "preferred" || /^\d{2,5}x\d{2,5}(@\d{1,3}(\.\d{1,3})?)?$/.test(value), "bad_value", "mode must be \"preferred\" or like \"2560x1440@59.95\"");
    if (key === "position") {
      need(!s.laptop, "bad_value", "the laptop stays where it is; place the other screen next to it");
      need(SIDES.includes(value), "bad_value", "position must be left, right, above, below or {x, y}");
    }
    if (key === "one_desktop") need(typeof value === "boolean", "bad_value", "one_desktop must be true, false or null");
    return value;
  }
  function condition(s, when) {
    if (when == null) return undefined; /* keep */
    need(Array.isArray(when) && when.length <= 1, "bad_value", "a setting can only depend on one other screen");
    if (when.length) need(when[0] !== s.id && db.screens.some((x) => x.id === when[0]), "bad_value", `when must name another known screen, not ${when[0]}`);
    return when;
  }
  /* In the fixture, the fixed screen follows the laptop's "one_desktop" (mock only). */
  function refreshFixed() {
    const conn = db.screens.filter((s) => s.connected);
    const panel = conn.find((s) => s.laptop), ext = conn.find((s) => !s.laptop);
    db.fixed.panel = panel ? panel.id : null;
    db.fixed.external = ext ? ext.id : null;
    db.fixed.canSwap = !!ext;
    if (!panel || !ext) Object.assign(db.fixed, { fixed: null, desk: null, role: null, swapped: false });
  }
  function summary(s) {
    const NAMES = { left: "left of laptop", right: "right of laptop", above: "above laptop", below: "below laptop" };
    return Object.entries(s.settings).filter(([, st]) => st.value != null).map(([key, st]) => {
      let text = key === "one_desktop" ? (st.value ? "one desktop" : "no fixed desktop")
        : key === "position" ? NAMES[st.value] : key === "rotation" ? `${st.value}°`
          : key === "scale" ? (st.value === "auto" ? "auto" : `${st.value}×`) : String(st.value);
      if (st.when.length) text += ` if ${(db.screens.find((x) => x.id === st.when[0]) || { name: "?" }).name}`;
      return text;
    }).join(" · ");
  }
  const changed = () => { refreshActive(); refreshFixed(); const applied = applyAll(); for (const s of db.screens) s.summary = summary(s); return applied; };

  /* ---------- keys ---------- */
  const MODS = ["SUPER", "CTRL", "ALT", "SHIFT"];
  function normalizeCombo(combo) {
    const parts = String(combo).split("+").map((p) => p.trim()).filter(Boolean);
    if (!parts.length) return "";
    const key = parts.pop();
    const mods = parts.map((m) => ({ CONTROL: "CTRL", WIN: "SUPER", LOGO: "SUPER", MOD4: "SUPER" }[m.toUpperCase()] || m.toUpperCase()));
    if (mods.some((m) => !MODS.includes(m))) return "";
    return [...MODS.filter((m) => mods.includes(m)), /^code:/i.test(key) ? key : key.toUpperCase()].join(" + ");
  }

  /* ---------- look ---------- */
  const LOOK_KEYS = ["gapsIn", "gapsOut", "rounding", "border", "blur", "blurSize", "blurPasses", "activeOpacity",
    "inactiveOpacity", "animSpeed", "borderColors", "borderAngle", "apps"];
  function cleanLook(values) {
    need(values && typeof values === "object", "bad_value", "the look must be an object");
    const unknown = Object.keys(values).filter((k) => !LOOK_KEYS.includes(k));
    need(!unknown.length, "bad_value", `unknown look settings: ${unknown}`);
    const c = values.borderColors;
    need(c == null || (Array.isArray(c) && c.length === 2 && c.every((x) => /^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(x))), "bad_value", "borderColors must be null or two colors like \"#89b4fa\"");
    const out = { ...db.look.values, ...clone(values) };
    for (const [k, r] of Object.entries(db.look.ranges)) if (k in out && isNum(out[k])) out[k] = Math.min(r.max, Math.max(r.min, out[k]));
    if (out.borderColors == null) { out.borderColors = null; out.borderAngle = 0; }
    return out;
  }

  /* ---------- sound ---------- */
  const allSound = () => [...db.sound.outputs, ...db.sound.inputs, ...db.sound.apps];
  const soundItem = (key) => allSound().find((x) => x.key === key) || fail("unknown_device", `unknown or unplugged device: ${key}`);
  function usable(d, volume = true) {
    need(d.active, "inactive", "the sound card uses another profile: switch the device on first");
    if (volume) need(!d.forceMute, "force_muted", "Force Mute keeps this device silent; switch it off first");
  }

  /* ---------- widgets ---------- */
  const widget = (kind) => db.widgets.find((w) => w.kind === kind) || fail("unknown_widget", `unknown widget: ${kind}`);
  function snapshot() { return db.widgets.map((w) => ({ kind: w.kind, enabled: w.enabled, content: clone(w.content), where: clone(w.where) })); }
  function restore(saved) {
    for (const s of saved) Object.assign(widget(s.kind), { enabled: s.enabled, content: clone(s.content), where: clone(s.where) });
    for (const w of db.widgets) refreshWidget(w);
  }
  function refreshWidget(w) { w.onDesktop = w.enabled && (w.kind !== "visualizer" || ["desktop", "both"].includes(w.where.where)); }
  function checkField(w, group, key, value) {
    const f = w.schema.find((x) => x.key === key && x.group === group);
    need(f, "bad_value", `${w.kind} has no ${group} setting '${key}'`);
    if (f.type === "toggle") need(typeof value === "boolean", "bad_value", `${key} must be true or false`);
    if (f.type === "choice") need(f.choices.some((c) => c.value === value), "bad_value", `${key} must be one of ${f.choices.map((c) => c.value)}`);
    if (f.type === "number") { need(isNum(value) && value >= f.min && value <= f.max, "bad_value", `${key} must be a number from ${f.min} to ${f.max}`); value = Math.round(value); }
    if (f.type === "text") {
      need(typeof value === "string" && (!f.maxLength || value.length <= f.maxLength), "bad_value", `${key} must be text`);
      if (f.format === "timezone" && value) { try { new Intl.DateTimeFormat("en", { timeZone: value }); } catch { fail("bad_value", `unknown time zone: ${value}`); } }
    }
    if (f.type === "multi") {
      need(Array.isArray(value), "bad_value", `${key} must be a list`);
      if (!value.length || eq(value, ["all"])) value = ["all"];
      else need(value.every((v) => f.choices.some((c) => c.value === v)), "bad_value", `${key} must be ["all"] or a list of ${f.choices.map((c) => c.value)}`);
      if (value[0] !== "all") value = f.choices.map((c) => c.value).filter((v) => value.includes(v));
    }
    return value;
  }
  function layoutsView() {
    const now = snapshot();
    const conn = connectedIds().slice().sort();
    db.layouts.current = db.layouts.items.find((n) => eq(db.layoutStore[n], now)) || null;
    db.layouts.connected = conn;
    for (const l of db.layouts.layouts) {
      l.auto = l.screens.length > 0;
      l.matchesNow = l.auto && eq(l.screens, conn);
      l.screenNames = l.screens.map((id) => (db.screens.find((s) => s.id === id) || { name: id }).name);
    }
    return db.layouts;
  }
  const knownLayout = (name) => need(db.layouts.items.includes(name), "unknown_layout", `no layout called '${name}'`);
  const layoutName = (name) => { need(typeof name === "string" && name.trim(), "bad_value", "a layout needs a name"); return name.trim().slice(0, 60); };

  const api = {
    /* Screens */
    screens: () => reply(db.screens),
    /** key: rotation | scale | mode | position | one_desktop; value null = unset.
     *  when: null/undefined keeps the condition, [] = always, [sid] = only with that one.
     *  position: "left" | "right" | "above" | "below", or {x, y} from a drag. */
    async setScreenSetting(sid, key, value, when) {
      let s = screen(sid);
      const target0 = s;
      need(["rotation", "scale", "mode", "position", "one_desktop"].includes(key), "bad_value", `unknown setting: ${key}`);
      if (key === "position" && value && typeof value === "object") [s, value] = sideFromPoint(s, value);
      value = cleanValue(s, key, value);
      const w = condition(s, when);
      const st = s.settings[key];
      if (value == null) Object.assign(st, { value: null, when: [] });
      else { st.value = value; if (w !== undefined) st.when = w; }
      const applied = changed();
      return reply({ ...target0, applied });
    },
    async forgetScreen(sid) {
      const s = screen(sid);
      need(!s.laptop, "internal_screen", "the laptop screen cannot be forgotten");
      need(!s.connected, "connected_screen", "unplug it first, then forget it");
      db.screens = db.screens.filter((x) => x.id !== sid);
      for (const o of db.screens) for (const st of Object.values(o.settings)) st.when = st.when.filter((id) => id !== sid);
      changed();
      return reply({ ok: true });
    },
    async toggleFavorite(sid) { const s = screen(sid); s.favorite = !s.favorite; return reply(s); },
    fixedStatus: () => reply(db.fixed),
    async swapFixed() {
      const f = db.fixed;
      need(f.canSwap, "no_external", "no external monitor connected");
      if (!f.role) Object.assign(f, { role: "external", fixed: f.external, desk: f.panel });
      else Object.assign(f, { role: f.role === "panel" ? "external" : "panel", fixed: f.desk, desk: f.fixed });
      f.swapped = !f.swapped;
      changed();
      return reply(f);
    },

    /* Keys */
    keys: () => reply(db.keys),
    async setKey(action, slot, combo) {
      const a = db.keys.actions.find((x) => x.id === action) || fail("bad_value", `unknown action: ${action}`);
      need(slot === 0 || slot === 1, "bad_value", "slot must be 0 or 1");
      const raw = (combo || "").trim();
      const c = raw ? normalizeCombo(raw) : "";
      need(!raw || c, "bad_value", `not a key combination: '${raw}'`);
      if (c) for (const o of db.keys.actions) o.slots = o.slots.map((x, i) => (x === c && !(o === a && i === slot) ? null : x));
      a.slots[slot] = c || null;
      return reply({ ...a, conflicts: c && db.keys.hyprBinds[c] ? [db.keys.hyprBinds[c]] : [] });
    },
    async setOption(name, value) {
      if (name === "desktop_keys") need(typeof value === "boolean", "bad_value", "desktop_keys must be true or false");
      else if (name === "default_fixed") need(["off", "external", "panel"].includes(value), "bad_value", "default_fixed must be one of off, external, panel");
      else fail("bad_value", `unknown option: ${name}`);
      db.keys.options[name] = value;
      return reply(db.keys.options);
    },
    async beginKeyCapture() { return reply({ ok: true }); },
    async endKeyCapture() { return reply({ ok: true }); },

    /* Window look */
    look: () => reply({ ...db.look, values: db.lookShown || db.look.values, previewing: !!db.lookShown }),
    async previewLook(values) {
      const v = cleanLook(values);
      const reloaded = !eq(v.apps, (db.lookShown || db.look.values).apps);
      db.lookShown = v;
      return reply({ ok: true, values: v, reloaded });
    },
    async revertLook() { db.lookShown = null; return api.look(); },
    async saveLook(values) {
      const v = cleanLook(values);
      db.look.values = v;
      db.look.saved = clone(v);
      db.lookShown = null;
      return api.look();
    },
    async resetLook() {
      db.look.values = clone(FIXTURE.look.presets.find((p) => p.name === "Soft").values);
      db.look.saved = {};
      db.lookShown = null;
      await wait(300);
      return api.look();
    },

    /* Sound */
    soundState: () => reply(db.sound),
    async setVolume(key, value) {
      need(isNum(value) && value >= 0 && value <= 100, "bad_value", "volume must be 0 to 100");
      const d = soundItem(key);
      if (!key.startsWith("app:")) usable(d);
      d.volume = Math.round(value);
      return reply(d);
    },
    async setMute(key, on) {
      need(typeof on === "boolean", "bad_value", "on must be true or false");
      const d = soundItem(key);
      if (!key.startsWith("app:")) usable(d, !on);
      d.muted = on;
      return reply(d);
    },
    async setDefault(key) {
      need(!String(key).startsWith("app:"), "bad_value", "an app cannot be the default device");
      const d = soundItem(key);
      usable(d, false);
      const list = db.sound.outputs.includes(d) ? db.sound.outputs : db.sound.inputs;
      list.forEach((x) => (x.isDefault = x === d));
      return reply(db.sound);
    },
    async switchOnDevice(key) {
      const d = soundItem(key);
      need(!d.active && !key.startsWith("app:"), "bad_value", "that device is on already");
      d.active = true;
      d.node = `alsa_output.${key.split(":").pop().replace(/\W+/g, "_").toLowerCase()}`;
      return reply(db.sound);
    },
    async setForceMute(key, on) {
      need(typeof on === "boolean", "bad_value", "on must be true or false");
      need(!String(key).startsWith("app:"), "bad_value", "only devices can be force muted");
      const d = soundItem(key);
      if (d.forceMute === on) return reply(d);
      d.forceMute = on;
      if (on) { db.forceBefore[key] = { volume: d.volume, muted: d.muted }; d.volume = 0; d.muted = true; }
      else {
        if (!d.connected) { for (const l of [db.sound.outputs, db.sound.inputs]) { const i = l.indexOf(d); if (i >= 0) l.splice(i, 1); } return reply(null); }
        Object.assign(d, db.forceBefore[key] || {}); delete db.forceBefore[key];
      }
      return reply(d);
    },
    async setAppOutput(app, dev) {
      const a = soundItem(app);
      need(String(app).startsWith("app:"), "bad_value", `not an app: ${app}`);
      const o = db.sound.outputs.find((x) => x.key === dev && x.active);
      need(o, "unknown_device", `not an output that is on: ${dev}`);
      a.output = dev;
      return reply(a);
    },

    /* Camera */
    camera: () => reply(db.camera),
    async setCamera(enabled, rotation) {
      need(typeof enabled === "boolean", "bad_value", "enabled must be true or false");
      need(ROTATIONS.includes(rotation), "bad_value", "rotation must be one of 0, 90, 180, 270");
      Object.assign(db.camera, { enabled, rotation, state: db.camera.installed ? (enabled ? "idle" : "off") : db.camera.state });
      return reply(db.camera);
    },
    async setupCamera() { await wait(900); Object.assign(db.camera, { installed: true, state: "idle" }); return reply(db.camera); },
    async cameraPreview() {
      const c = db.camera;
      return reply({ image: null, reason: !c.installed ? "not_set_up" : c.enabled ? "starting" : "off" });
    },

    /* Samsung Galaxy Book */
    samsung: () => reply(db.samsung),
    async setSamsung(field, value) {
      const s = db.samsung;
      need(s.available, "unavailable", "not a Samsung Galaxy Book");
      const bool = () => need(typeof value === "boolean", "bad_value", `${field} must be true or false`);
      if (field === "active") { bool(); await wait(600); s.active = value; s.writable = value; }
      else if (field === "chargeLimit") { need(isNum(value) && value >= 50 && value <= 100, "bad_value", "chargeLimit must be 50 to 100"); need(s.writable, "not_set_up", "needs a one-time setup first"); s.wantedLimit = Math.round(value); if (!s.fullOnce) s.chargeLimit = s.wantedLimit; }
      else if (field === "fullOnce") { bool(); need(s.writable, "not_set_up", "needs a one-time setup first"); need(!value || s.plugged, "not_plugged", "plug in the charger first"); s.fullOnce = value; s.chargeLimit = value ? 100 : s.wantedLimit; }
      else if (field === "mode") { need(s.modes.some((m) => m.value === value), "bad_value", `mode must be one of ${s.modes.map((m) => m.value)}`); need(s.writable, "not_set_up", "needs a one-time setup first"); s.mode = value; }
      else if (field === "usbCharging" || field === "lidPower") { bool(); need(s.attributesWritable, "not_set_up", "could not change it (is the one-time setup done?)"); s[field] = value; }
      else if (field === "kbdLight") { need(s.kbdMax != null, "unavailable", "this laptop has no keyboard backlight"); need(isNum(value) && value >= 0 && value <= s.kbdMax, "bad_value", `kbdLight must be 0 to ${s.kbdMax}`); s.kbdLight = Math.round(value); }
      else fail("bad_value", `unknown field: ${field}`);
      return reply(s);
    },

    /* Widgets */
    widgets: () => reply(db.widgets),
    /** changes: {enabled?, content?: {key: value}, where?: {key: value}} — checked against w.schema. */
    async updateWidget(kind, changes) {
      const w = widget(kind);
      need(changes && typeof changes === "object", "bad_value", "changes must be an object");
      const extra = Object.keys(changes).filter((k) => !["enabled", "content", "where"].includes(k));
      need(!extra.length, "bad_value", `only enabled, content and where can be changed here, not ${extra}`);
      need(changes.enabled == null || typeof changes.enabled === "boolean", "bad_value", "enabled must be true or false");
      const next = { content: {}, where: {} };
      for (const group of ["content", "where"]) for (const [k, v] of Object.entries(changes[group] || {})) next[group][k] = checkField(w, group, k, v);
      if (changes.enabled != null) w.enabled = changes.enabled;
      Object.assign(w.content, next.content);
      Object.assign(w.where, next.where);
      refreshWidget(w);
      return reply(w);
    },
    async installCava() { await wait(600); widget("visualizer").missing = []; return reply(widget("visualizer")); },
    layouts: () => reply(layoutsView()),
    async saveLayout(name) {
      name = layoutName(name);
      if (!db.layouts.items.includes(name)) {
        need(db.layouts.items.length < 30, "bad_value", "there are 30 layouts already; delete one first");
        db.layouts.items.push(name);
        db.layouts.layouts.push({ name, screens: [], screenNames: [], auto: false, matchesNow: false });
      }
      db.layoutStore[name] = snapshot();
      return reply(layoutsView());
    },
    async loadLayout(name) {
      knownLayout(name);
      const previous = snapshot();
      restore(db.layoutStore[name]);
      return reply({ ...layoutsView(), previous });
    },
    async restoreWidgets(previous) {
      need(previous && typeof previous === "object", "bad_value", "previous must be the widgets from loadLayout");
      restore(previous);
      return reply(layoutsView());
    },
    async deleteLayout(name) {
      knownLayout(name);
      db.layouts.items = db.layouts.items.filter((n) => n !== name);
      db.layouts.layouts = db.layouts.layouts.filter((l) => l.name !== name);
      delete db.layoutStore[name];
      return reply(layoutsView());
    },
    async renameLayout(name, newName) {
      knownLayout(name);
      newName = layoutName(newName);
      if (newName !== name) {
        need(!db.layouts.items.includes(newName), "conflict", `there is a layout called '${newName}' already`);
        db.layouts.items = db.layouts.items.map((n) => (n === name ? newName : n));
        db.layouts.layouts.find((l) => l.name === name).name = newName;
        db.layoutStore[newName] = db.layoutStore[name];
        delete db.layoutStore[name];
      }
      return reply(layoutsView());
    },
    async setLayoutAuto(name, on) {
      knownLayout(name);
      need(typeof on === "boolean", "bad_value", "on must be true or false");
      const conn = connectedIds().slice().sort();
      for (const l of db.layouts.layouts) {
        if (l.name === name) l.screens = on ? conn : [];
        else if (on && eq(l.screens, conn)) l.screens = [];
      }
      return reply(layoutsView());
    },
    async arrangeWidgets() {
      need(db.widgets.some((w) => w.onDesktop), "nothing_to_arrange", "switch a widget on first");
      return reply({ ok: true });
    },

    /* Enforcement */
    enforcement: () => reply(db.enforcement),
    async setEnforcement(enabled) {
      need(typeof enabled === "boolean", "bad_value", "enabled must be true or false");
      db.enforcement.enabled = enabled;
      return reply(db.enforcement);
    },

    /* Welcome, update, uninstall */
    welcome: () => reply(db.welcome),
    async dismissWelcome() {
      Object.assign(db.welcome, { show: false, kind: null, from: null });
      return reply(db.welcome);
    },
    checkUpdate: () => reply(db.update),
    async runUpdate() {
      need(db.updateStatus.state !== "running", "busy", "an update is running already");
      const { current, latest } = db.update;
      Object.assign(db.updateStatus, { state: "running", from: current, to: null, error: null,
        log: [`Updating Tuneup ${current} -> ${latest} (${db.update.commitsBehind} new commits)`] });
      setTimeout(() => {
        db.updateStatus.log.push("Tuneup is up to date.");
        Object.assign(db.updateStatus, { state: "done", to: latest });
        Object.assign(db.update, { current: latest, available: false, commitsBehind: 0, canUpdate: false });
        Object.assign(db.welcome, { show: true, kind: "updated", from: current, to: latest });
        db.about.version = latest;
      }, 2500);
      return reply({ started: true });
    },
    updateStatus: () => reply(db.updateStatus),
    async uninstall(keepSettings) {
      need(typeof keepSettings === "boolean", "bad_value", "keepSettings must be true or false");
      return reply({ started: true });
    },

    /* General */
    language: () => reply(db.language),
    async setLanguage(code) {
      need(db.language.items.some((x) => x.code === code), "bad_value", "language must be one of en, de, es, fr, it");
      db.language.code = code;
      db.translations.code = code;
      return reply(db.language);
    },
    translations: () => reply(translationTable(db.language.code)),
    about: () => reply(db.about),
    async openGuide() { return reply({ ok: true }); },
    async openConfigFolder() { return reply({ ok: true }); },
    theme: () => reply(db.theme),
  };

  /* The real tables (../locales.json) when the page is served from the repo, so the
   * preview shows every language; ?lang=xx picks one. Falls back to the sample above. */
  let locales;
  function translationTable(code) {
    if (code === "en") return { code, texts: {} };
    if (locales === undefined) {
      locales = null;
      try {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", new URL("../locales.json", document.baseURI).href, false);
        xhr.send();
        if (xhr.status === 200 || (xhr.status === 0 && xhr.responseText)) locales = JSON.parse(xhr.responseText);
      } catch { locales = null; }
    }
    return locales && locales[code] ? { code, texts: locales[code] } : { ...db.translations, code };
  }
  const wanted = typeof location !== "undefined" && new URLSearchParams(location.search).get("lang");
  if (wanted && db.language.items.some((x) => x.code === wanted)) db.language.code = wanted;

  refreshActive();
  for (const w of db.widgets) refreshWidget(w);
  window.api = api;
  window.ApiError = ApiError;
})();
