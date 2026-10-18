import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Services.Mpris
import Quickshell.Services.UPower
import qs.Commons
import "ColorTools.js" as ColorTools

// Desktop widgets of Tuneup, drawn behind (or above) the windows on
// every chosen screen; the bar visualizer (BarWidget.qml) reads its levels
// from here too.
//
// This file holds the widgets' settings and look, where they are, and
// arranging them. The rest lives next to it:
//   *Source.qml     the data the widgets show (cava, lyrics, clock, system
//                   stats, now playing, weather; Requests.qml for the web)
//   WidgetLayer     one screen's layer (Variants below: five per screen)
//   Placed, *View   one widget on a layer, and what it draws
//   StylePanel      styling a widget while arranging
//
// Settings come from ~/.config/tuneup/widgets.json (hypr-screens/ before the
// rename), written by Tuneup (hypr_screens/widgets.py). While arranging,
// every screen with a widget gets an extra layer above the windows that shows
// the wallpaper -- an empty desktop -- where the widgets can be dragged,
// resized by their edges and corners and turned with the wheel. Its own
// Save/Cancel (and Esc) end it, so nothing behind it is needed; Save hands
// places and sizes to `tuneup widgets save`.
Item {
  id: root

  property var shell: null
  property var manifest: null

  readonly property string configBase: Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")
  // Tuneup's settings; before the rename they were in hypr-screens/ (read
  // only while Tuneup's own file is not there).
  property bool tuneupSettings: false
  readonly property string wallpaper: Quickshell.env("HOME") + "/.local/state/omarchy/current/background"
  property var widgets: ({})
  property string cavaConfig: ""
  property string cavaKey: ""
  property string cpuTemperatureFile: ""
  property string fontFamily: ""
  // Texts in the settings window's language, and its locale for the date.
  property var texts: ({})
  property string locale: ""
  // kind -> {size: [min, max], width: [min, max] or null}, from widgets.py.
  property var ranges: ({})
  property bool editing: false
  // kind -> {x, y, rotation, size, width, colors}: the centre as fractions of
  // the screen, degrees, the size (width 0: it follows the size) and the
  // colors of its parts (only the ones set).
  property var draft: ({})
  // The widgets there are, and each one's parts with a color: part -> default.
  property var kinds: ["visualizer", "lyrics", "clock", "system"]
  property var parts: ({})
  // part -> its name in the settings window's language, per widget.
  property var partTitles: ({})
  // kind -> the look settings it has (widgets.look_keys: font, effect, card
  // ...), set in the style panel; and the ranges of its sliders.
  property var lookKeys: ({})
  property var lookRanges: ({})
  // The theme's colors by name, from its colors.toml (follows a theme change).
  property var palette: ({})

  // --- settings ------------------------------------------------------------------

  FileView {
    id: settingsFile
    path: root.configBase + "/tuneup/widgets.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: { root.tuneupSettings = true; root.parseSettings(text()) }
    onLoadFailed: root.tuneupSettings = false
  }
  FileView {
    id: legacySettingsFile
    path: root.configBase + "/hypr-screens/widgets.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: if (!root.tuneupSettings) root.parseSettings(text())
  }
  function reloadSettings() {
    settingsFile.reload()
    legacySettingsFile.reload()
  }

  function parseSettings(text) {
    var data
    try { data = JSON.parse(String(text)) } catch (e) { return }
    var key = root.cavaKey
    root.widgets = data.widgets || {}
    root.cavaConfig = String(data.cava || "")
    root.cavaKey = String(data.cavaKey || "")
    root.cpuTemperatureFile = String(data.cpuTemperature || "")
    root.fontFamily = String(data.font || "")
    root.texts = data.texts || {}
    root.locale = String(data.locale || "")
    root.ranges = data.ranges || {}
    if (data.kinds) root.kinds = data.kinds
    root.parts = data.parts || {}
    root.partTitles = data.partTitles || {}
    root.lookKeys = data.lookKeys || root.lookKeysFallback()
    root.lookRanges = data.lookRanges || { letter_spacing: [-2, 20], effect_strength: [0, 100], opacity: [20, 100],
                                           card_opacity: [5, 100], card_radius: [0, 60], card_padding: [0, 80],
                                           current_size: [100, 170], scroll_ms: [150, 1500] }
    if (!root.editing) root.draft = root.placementsFromSettings()
    if (root.widget("visualizer") && root.cavaKey !== key && key !== "") cava.restart()
  }

  FileView {
    id: themeFile
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      var found = {}
      var rows = String(text()).split("\n")
      for (var i = 0; i < rows.length; i++) {
        var match = rows[i].match(/^\s*([a-z_]+)\s*=\s*"(#[0-9a-fA-F]{6})"/)
        if (match) found[match[1]] = match[2]
      }
      root.palette = found
    }
  }
  // A theme switch replaces the file; the shell's colors change with it.
  Connections {
    target: Color
    function onAccentChanged() { themeFile.reload() }
  }

  function themeColor(name) {
    if (root.palette[name]) return root.hexColor(root.palette[name])
    if (name === "foreground") return Color.foreground
    if (name === "background") return Color.background
    if (name === "muted") return Color.muted
    if (name === "red") return Color.urgent
    return Color.accent
  }
  // "#rrggbb" or "#rrggbbaa" (CSS order; Qt reads #aarrggbb).
  function hexColor(value) {
    var hex = String(value).slice(1)
    var alpha = hex.length === 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1
    return Qt.rgba(parseInt(hex.slice(0, 2), 16) / 255, parseInt(hex.slice(2, 4), 16) / 255,
                   parseInt(hex.slice(4, 6), 16) / 255, alpha)
  }
  function colorValue(kind, value) {
    if (value === "accent") return root.tint(kind)
    if (String(value).indexOf("theme:") === 0) return root.themeColor(String(value).slice(6))
    if (/^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(String(value))) return root.hexColor(value)
    return null
  }
  // A widget's own colors: part -> value, and its base color ("base"). While
  // arranging they come from the draft, or from the style panel's preview while
  // the pointer is on a color there.
  function colorsOf(kind) {
    if (root.preview && root.preview.kind === kind && root.preview.colors) return root.preview.colors
    var spot = root.draft[kind]
    return spot && spot.colors ? spot.colors : {}
  }
  // A part's color: set by the user (in the draft while arranging), else its
  // default; `fallback` where the default is "auto".
  function colorOf(kind, part, fallback) {
    var set = root.colorsOf(kind)[part]
    var value = set || (root.parts[kind] ? root.parts[kind][part] : undefined) || "accent"
    var color = value === "auto" ? null : root.colorValue(kind, value)
    return color === null ? (fallback !== undefined ? fallback : root.tint(kind)) : color
  }
  function hasColor(kind, part) {
    return !!root.colorsOf(kind)[part]
  }

  // widgets.look_keys, for a settings file written before it had them.
  function lookKeysFallback() {
    var out = {}
    var look = ["effect", "effect_strength", "opacity", "card", "card_opacity", "card_radius", "card_padding", "card_blur"]
    for (var kind in root.widgets) {
      out[kind] = (kind === "visualizer" ? [] : ["font_family", "font_weight", "letter_spacing"]).concat(look)
                  .concat(kind === "lyrics" ? ["align", "current_size", "scroll_ms"] : [])
    }
    return out
  }

  // A widget's settings with its look (lookKeys) as arranged: from the draft,
  // or from the style panel's preview while the pointer rests on a choice.
  function style(kind) {
    var w = root.widget(kind)
    if (!w) return null
    var out = Object.assign({}, w)
    var spot = root.draft[kind]
    var keys = root.lookKeys[kind] || []
    for (var i = 0; spot && i < keys.length; i++) {
      if (spot[keys[i]] !== undefined) out[keys[i]] = spot[keys[i]]
    }
    if (root.preview && root.preview.kind === kind && root.preview.look) Object.assign(out, root.preview.look)
    return out
  }

  readonly property var weights: ({ light: 300, regular: 400, medium: 500, bold: 700, black: 900 })
  // A widget's text: font, weight, spacing and the outline (its effect).
  function textLook(kind) {
    var w = root.style(kind)
    var weight = w ? (root.weights[w.font_weight] || 700) : 700
    var strength = w ? w.effect_strength / 100 : 0.35
    return {
      family: w && w.font_family ? w.font_family : root.fontFamily,
      weight: weight,
      lighter: Math.max(300, weight - 300),
      spacing: w ? w.letter_spacing : 0,
      outline: !!(w && w.effect === "outline" && strength > 0),
      outlineColor: root.colorOf(kind, "effect", Qt.rgba(0, 0, 0, strength))
    }
  }
  // Which layer a widget sits on: below or above the windows, with blur
  // behind its card or without.
  function groupOf(kind) {
    var w = root.style(kind)
    if (!w) return "bottom"
    return (w.above ? "top" : "bottom") + (w.card && w.card_blur ? "-blur" : "")
  }

  function widget(kind) { return root.widgets ? (root.widgets[kind] || null) : null }
  function enabled(kind) { var w = root.widget(kind); return !!(w && w.enabled) }
  function onDesktop(kind) {
    var w = root.widget(kind)
    return !!(w && w.enabled && (kind !== "visualizer" || w.where !== "bar"))
  }
  // A widget's accent color: its base color, else its "color" setting (the
  // gradient starts from the accent).
  function tint(kind) {
    var base = root.colorsOf(kind).base
    var own = base && base !== "accent" ? root.colorValue(kind, base) : null
    if (own !== null) return own
    var w = root.widget(kind)
    var name = w ? w.color : "accent"
    if (name === "foreground") return Color.foreground
    if (name === "white") return Qt.rgba(1, 1, 1, 1)
    return Color.accent
  }
  function inBar() {
    var w = root.widget("visualizer")
    return !!(w && w.enabled && w.where !== "desktop")
  }
  function placementsFromSettings() {
    var out = {}
    for (var kind in root.widgets) {
      var w = root.widgets[kind]
      var spot = { x: Number(w.x), y: Number(w.y), rotation: Number(w.rotation),
                   size: Number(w.size), width: Number(w.width || 0), colors: Object.assign({}, w.colors || {}),
                   same_place: w.same_place !== false, spots: JSON.parse(JSON.stringify(w.spots || {})) }
      var keys = root.lookKeys[kind] || []
      for (var i = 0; i < keys.length; i++) spot[keys[i]] = w[keys[i]]
      out[kind] = spot
    }
    return out
  }
  // The place on a screen (sid: its id): the widget's own, or with
  // same_place off the screen's own spot once it has one.
  function placement(kind, sid) {
    var base = root.draft[kind] || { x: 0.5, y: 0.5, rotation: 0, size: { visualizer: 160, lyrics: 200 }[kind] || 100,
                                     width: 0, colors: {}, same_place: true, spots: {} }
    if (sid && base.same_place === false && base.spots && base.spots[sid]) return Object.assign({}, base, base.spots[sid])
    return base
  }
  function changePlacement(kind, changes, sid) {
    var next = Object.assign({}, root.draft)
    var base = Object.assign({}, root.placement(kind))
    if (sid && base.same_place === false) {
      var here = root.placement(kind, sid)
      var spots = Object.assign({}, base.spots || {})
      spots[sid] = Object.assign({ x: here.x, y: here.y, rotation: here.rotation, size: here.size, width: here.width }, changes)
      base.spots = spots
    } else {
      Object.assign(base, changes)
    }
    next[kind] = base
    root.draft = next
  }
  function setPlacement(kind, x, y, rotation, sid) {
    root.changePlacement(kind, { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)), rotation: rotation }, sid)
  }
  function hasWidth(kind) { return !!(root.ranges[kind] && root.ranges[kind].width) }
  function clamp(value, range) { return range ? Math.max(range[0], Math.min(range[1], value)) : value }
  function setSize(kind, size, width, sid) {
    var range = root.ranges[kind] || {}
    root.changePlacement(kind, { size: Math.round(root.clamp(size, range.size)),
                                 width: width > 0 ? Math.round(root.clamp(width, range.width)) : 0 }, sid)
  }

  // Tuneup's screen id: "make|model|serial", like config.screen_id().
  function screenId(screen) {
    var monitor = screen ? Hyprland.monitorFor(screen) : null
    var o = monitor ? monitor.lastIpcObject : null
    if (!o) return ""
    var parts = [String(o.make || "").trim(), String(o.model || "").trim(), String(o.serial || "").trim()]
    if (!parts[0] && !parts[1] && !parts[2]) parts = [String(o.description || o.name || "").trim()]
    return parts.join("|")
  }
  function screenMatches(kind, screen) {
    var w = root.widget(kind)
    if (!w || !screen) return false
    var mode = (w.monitors && w.monitors.mode) || "all"
    var internal = /^(eDP|LVDS|DSI)/.test(String(screen.name || ""))
    if (mode === "all") return true
    if (mode === "laptop") return internal
    if (mode === "external") return !internal
    return root.screenId(screen) === String(w.monitors.screen || "")
  }

  Component.onCompleted: Hyprland.refreshMonitors()

  // --- screens coming and going ------------------------------------------------------
  // A screen plugged in while the shell runs gets its layers at once
  // (Variants over Quickshell.screens), but Hyprland's data about it (make,
  // model and serial: the screen id that picks widgets and their places) only
  // after asking again. A screen that went away takes the style panel's
  // selection with it.
  Connections {
    target: Quickshell
    function onScreensChanged() { monitorRefresh.restart() }
  }
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (/^monitor(added|removed)/.test(event.name)) monitorRefresh.restart()
    }
  }
  Timer {
    id: monitorRefresh
    interval: 250
    onTriggered: {
      Hyprland.refreshMonitors()
      root.dropGoneSelection()
    }
  }
  function screenIds() {
    var ids = []
    for (var i = 0; i < Quickshell.screens.length; i++) ids.push(root.screenId(Quickshell.screens[i]))
    return ids
  }
  function dropGoneSelection() {
    if (root.selection && root.screenIds().indexOf(root.selection.screen) < 0) {
      root.selection = null
      root.preview = null
    }
  }

  // --- the data the widgets show (one source each) --------------------------------

  Requests { id: requests }
  CavaSource { id: cava; service: root; config: root.cavaConfig }
  LyricsSource { id: lyrics; service: root; requests: requests }
  ClockSource { id: clock; service: root }
  StatsSource { id: stats; service: root; temperatureFile: root.cpuTemperatureFile }
  NowPlayingSource { id: media; service: root }
  WeatherSource { id: weatherSource; service: root; requests: requests }

  // What the views read (service.levels, service.now, …).
  property alias levels: cava.levels
  property alias quiet: cava.quiet
  function useLevels(user, on) { cava.use(user, on) }
  property alias lyricLines: lyrics.lines
  property alias lyricIndex: lyrics.index
  property alias playing: lyrics.playing
  property alias songTime: lyrics.songTime
  function wordsFor(index) { return lyrics.wordsFor(index) }
  property alias now: clock.now
  property alias zoneKnown: clock.zoneKnown
  function zoneTime(date) { return clock.zoneTime(date) }
  property alias cpu: stats.cpu
  property alias memory: stats.memory
  property alias temperature: stats.temperature
  property alias cpuHistory: stats.cpuHistory
  property alias memoryHistory: stats.memoryHistory
  property alias temperatureHistory: stats.temperatureHistory
  property alias netDown: stats.netDown
  property alias netUp: stats.netUp
  property alias netDownHistory: stats.netDownHistory
  property alias netUpHistory: stats.netUpHistory
  property alias disks: stats.disks
  property alias npPlayer: media.player
  property alias npPosition: media.position
  property alias weather: weatherSource.weather
  property alias weatherPlace: weatherSource.place

  // A player's key: the first part of its MPRIS name ("spotify").
  function playerKey(p) {
    var name = String(p && p.dbusName ? p.dbusName : "").replace("org.mpris.MediaPlayer2.", "")
    return name.split(".")[0].toLowerCase()
  }
  // The player that plays (only `key`'s, when one is chosen); while none
  // does, `previous`, else one that looks like music (a track with an album)
  // rather than a video.
  function pickPlayer(key, previous) {
    var all = Mpris.players ? Mpris.players.values : []
    var players = all.filter(function(p) { return !key || root.playerKey(p) === key })
    for (var i = 0; i < players.length; i++) {
      if (players[i].isPlaying) return players[i]
    }
    var music = null
    var any = null
    for (var j = 0; j < players.length; j++) {
      var p = players[j]
      if (p === previous && p.trackTitle) return p
      if (!music && p.trackTitle && p.trackAlbum) music = p
      if (!any && p.trackTitle) any = p
    }
    return music || any
  }

  // Bytes as text ("2.4 MB"), and a speed ("180 KB/s").
  function bytes(n) { return root.scaled(n, ["B", "KB", "MB", "GB", "TB"]) }
  function rate(n) { return root.scaled(n, ["B/s", "KB/s", "MB/s", "GB/s"]) }
  function scaled(n, units) {
    var i = 0
    while (n >= 1000 && i < units.length - 1) { n /= 1000; i++ }
    return (n >= 100 || i === 0 ? Math.round(n) : n.toFixed(1)) + " " + units[i]
  }
  // A WMO weather code as a Nerd Font icon.
  function weatherIcon(code, day) {
    if (code === 0) return day === false ? String.fromCodePoint(0xf0594) : String.fromCodePoint(0xf0599)
    if (code <= 2) return day === false ? String.fromCodePoint(0xf0f31) : String.fromCodePoint(0xf0595)
    if (code === 3) return String.fromCodePoint(0xf0590)
    if (code <= 48) return String.fromCodePoint(0xf0591)
    if (code <= 57) return String.fromCodePoint(0xf0597)
    if (code <= 67) return String.fromCodePoint(0xf0596)
    if (code <= 77) return String.fromCodePoint(0xf0598)
    if (code <= 82) return String.fromCodePoint(0xf0596)
    if (code <= 86) return String.fromCodePoint(0xf0598)
    return String.fromCodePoint(0xf0593)
  }

  // --- the layers -----------------------------------------------------------------------

  // Is the widget on this screen, and (without a group: on any layer, as while
  // arranging) in this group and allowed by its rules right now?
  function shows(kind, screen, group) {
    return root.onDesktop(kind) && root.screenMatches(kind, screen)
           && (!group || (root.groupOf(kind) === group && root.allowedNow(kind, screen)))
  }
  // Its rules: only on some desktops (workspace ids, 99 the fixed screen),
  // only while the desktop has no window, not on battery.
  function allowedNow(kind, screen) {
    var w = root.widget(kind)
    if (!w) return false
    if (w.hide_on_battery && UPower.onBattery) return false
    var monitor = screen ? Hyprland.monitorFor(screen) : null
    var workspace = monitor ? monitor.activeWorkspace : null
    if (w.desktops && w.desktops.length && (!workspace || w.desktops.indexOf(workspace.id) < 0)) return false
    if (w.only_empty && workspace && workspace.toplevels && workspace.toplevels.values.length > 0) return false
    return true
  }
  function anyOn(screen, group) {
    for (var i = 0; i < root.kinds.length; i++) {
      if (root.shows(root.kinds[i], screen, group)) return true
    }
    return false
  }

  // Each widget's view; a view has `service` and `editing`.
  Component { id: visualizerView; VisualizerView { service: root } }
  Component { id: lyricsView; LyricsView { service: root } }
  Component { id: clockView; ClockView { service: root } }
  Component { id: systemView; SystemView { service: root } }
  Component { id: nowplayingView; NowPlayingView { service: root } }
  Component { id: weatherView; WeatherView { service: root } }
  Component { id: calendarView; CalendarView { service: root } }
  Component { id: batteryView; BatteryView { service: root } }
  Component { id: networkView; NetworkView { service: root } }
  Component { id: diskView; DiskView { service: root } }
  readonly property var views: ({ visualizer: visualizerView, lyrics: lyricsView, clock: clockView, system: systemView,
                                  nowplaying: nowplayingView, weather: weatherView, calendar: calendarView,
                                  battery: batteryView, network: networkView, disk: diskView })

  // --- arranging ------------------------------------------------------------------------

  // The style mode (colorMode): a click on a widget picks it (`selection`:
  // {kind, part, screen, x, y, rect}; rect: the widget's frame on the screen)
  // and the style panel (StylePanel.qml) sets its colors and look in the
  // draft. `part` is "base" (the whole widget) until fine-tuning is open, then
  // the part clicked.
  property bool colorMode: false
  property var selection: null
  property bool fineTune: false
  // The panel's open section: "color", "font", "effect" or "card".
  property string styleSection: "color"
  // While the pointer rests on a choice in the panel: {kind, colors} or
  // {kind, look: {key: value}}.
  property var preview: null
  // Own colors used last ("#rrggbb[aa]"), newest first.
  property var recentColors: []
  // The wallpaper's main colors (the style panel works them out when it opens).
  property var wallpaperColors: []
  // Where the style panel was dragged to, per screen: {screen: {x, y}}.
  property var palettePlaces: ({})
  // Every widget's colors and look before each change, for undo (newest last).
  property var styleHistory: []
  function selectPart(kind, part, screen, point, rect) {
    root.preview = null
    // A single part picked while fine-tuning: its color is what is wanted.
    if (root.fineTune && part) root.styleSection = "color"
    root.selection = { kind: kind, part: root.fineTune ? part : "base", clicked: part, screen: screen,
                       x: point.x, y: point.y, rect: rect || null }
  }
  function remember() {
    var all = {}
    for (var kind in root.draft) {
      var spot = root.draft[kind]
      var look = {}
      var keys = root.lookKeys[kind] || []
      for (var i = 0; i < keys.length; i++) look[keys[i]] = spot[keys[i]]
      all[kind] = { colors: Object.assign({}, spot.colors || {}), look: look }
    }
    root.styleHistory = root.styleHistory.concat([all]).slice(-50)
  }
  function undoStyle() {
    if (!root.styleHistory.length) return
    var last = root.styleHistory[root.styleHistory.length - 1]
    root.styleHistory = root.styleHistory.slice(0, -1)
    root.preview = null
    var next = Object.assign({}, root.draft)
    for (var kind in last) {
      if (next[kind]) next[kind] = Object.assign({}, next[kind], last[kind].look, { colors: last[kind].colors })
    }
    root.draft = next
  }
  // One look setting (lookKeys) into the draft; step: a new step for undo
  // (not for each move of a slider).
  function setLook(kind, key, value, step) {
    if (!root.draft[kind]) return
    if (step) root.remember()
    root.preview = null
    var next = Object.assign({}, root.draft)
    var changes = {}
    changes[key] = value
    next[kind] = Object.assign({}, next[kind], changes)
    root.draft = next
  }
  // Shows `value` on the widget while the pointer rests on it in the panel.
  function previewLook(kind, key, value) {
    var look = {}
    look[key] = value
    root.preview = { kind: kind, look: look }
  }

  // The installed font families for the panel's font list: asked from
  // fontconfig once, the first time the list opens.
  property var fontFamilies: []
  property bool fontsAsked: false
  function loadFonts() {
    if (root.fontsAsked) return
    root.fontsAsked = true
    fontList.running = true
  }
  Process {
    id: fontList
    command: ["fc-list", ":", "family"]
    stdout: StdioCollector { onStreamFinished: root.fontFamilies = root.parseFonts(text) }
  }
  // One family a line, with its other names after commas: the first name.
  function parseFonts(text) {
    var seen = {}
    var out = []
    var rows = String(text).split("\n")
    for (var i = 0; i < rows.length; i++) {
      var name = rows[i].split(",")[0].replace(/\\(.)/g, "$1").trim()
      if (!name || seen[name.toLowerCase()]) continue
      seen[name.toLowerCase()] = true
      out.push(name)
    }
    out.sort(function(a, b) { return a.toLowerCase().localeCompare(b.toLowerCase()) })
    return out
  }
  // step: a new step for undo (not for each move while dragging);
  // keep: among the colors used last.
  function setPartColor(kind, part, value, step, keep) {
    if (step) root.remember()
    var colors = Object.assign({}, root.placement(kind).colors || {})
    if (value) colors[part] = value
    else delete colors[part]
    root.changePlacement(kind, { colors: colors })
    if (keep && value && value.charAt(0) === "#") {
      var recent = root.recentColors.filter(function(c) { return c !== value })
      recent.unshift(value)
      root.recentColors = recent.slice(0, 8)
    }
  }
  function setColors(kind, colors) {
    root.remember()
    root.preview = null
    root.changePlacement(kind, { colors: colors })
  }
  // A scheme's colors for a widget, made from its base color as it is now.
  function schemeColors(kind, id) {
    var base = (root.placement(kind).colors || {}).base || ""
    var shown = root.tint(kind)
    return ColorTools.scheme(id, base, { r: shown.r, g: shown.g, b: shown.b, a: shown.a }, root.parts[kind] || {})
  }
  // This widget's colors on every other widget that is on.
  function applyToAll(kind) {
    root.remember()
    var from = root.placement(kind).colors || {}
    for (var i = 0; i < root.kinds.length; i++) {
      var other = root.kinds[i]
      if (other === kind || !root.enabled(other)) continue
      root.changePlacement(other, { colors: ColorTools.carry(from, root.parts[kind] || {}, root.parts[other] || {}) })
    }
  }

  // The style panel's place: `kept` (where it was dragged) unless that covers the
  // widget's frame `rect`; else right of the widget, left, below or above,
  // whichever fits first (or has the most room), inside `area` and below
  // its `top` (the toolbar).
  function placePalette(rect, kept, width, height, area) {
    var margin = 12, gap = 28
    var top = (area.top || 0) + margin
    function fit(x, y) {
      return { x: Math.max(margin, Math.min(area.width - width - margin, x)),
               y: Math.max(top, Math.min(area.height - height - margin, y)) }
    }
    function covers(p) {
      return !!rect && p.x < rect.x + rect.width && p.x + width > rect.x && p.y < rect.y + rect.height && p.y + height > rect.y
    }
    if (kept) {
      var there = fit(kept.x, kept.y)
      if (!covers(there)) return there
    }
    if (!rect) return fit((area.width - width) / 2, (area.height - height) / 2)
    var middleY = rect.y + rect.height / 2 - height / 2
    var middleX = rect.x + rect.width / 2 - width / 2
    var sides = [
      { room: area.width - rect.x - rect.width, need: width, at: fit(rect.x + rect.width + gap, middleY) },
      { room: rect.x, need: width, at: fit(rect.x - width - gap, middleY) },
      { room: area.height - rect.y - rect.height, need: height, at: fit(middleX, rect.y + rect.height + gap) },
      { room: rect.y - top, need: height, at: fit(middleX, rect.y - height - gap) }
    ]
    for (var i = 0; i < sides.length; i++) {
      if (sides[i].room >= sides[i].need + gap + margin && !covers(sides[i].at)) return sides[i].at
    }
    sides.sort(function(a, b) { return (b.room - b.need) - (a.room - a.need) })
    return sides[0].at
  }
  function startEditing() {
    Hyprland.refreshMonitors()
    root.draft = root.placementsFromSettings()
    root.colorMode = false
    root.selection = null
    root.preview = null
    root.styleHistory = []
    // Worked out again: the wallpaper may have changed.
    root.wallpaperColors = []
    root.editing = true
  }
  function cancelEditing() {
    root.draft = root.placementsFromSettings()
    root.selection = null
    root.preview = null
    root.editing = false
  }
  function saveEditing() {
    if (saver.running) return
    root.selection = null
    root.preview = null
    // `tuneup`, or `hypr-screens` before the rename.
    saver.command = ["sh", "-c", "if command -v tuneup >/dev/null; then exec tuneup widgets save \"$1\"; "
                     + "else exec hypr-screens widgets save \"$1\"; fi", "sh", JSON.stringify(root.draft)]
    saver.running = true
  }
  Process {
    id: saver
    // Saved: the settings file changes with it and brings the places back in.
    // Not saved: arranging stays open (nothing is lost), with a note.
    onExited: function(code) {
      root.saveFailed = code !== 0
      if (code === 0) root.editing = false
    }
  }
  property bool saveFailed: false
  onEditingChanged: if (editing) saveFailed = false

  // Each screen has five layers: behind the windows, above them (each with
  // and without blur behind the cards) and, while arranging, the edit layer.
  Variants {
    model: Quickshell.screens
    WidgetLayer { service: root; group: "bottom" }
  }
  Variants {
    model: Quickshell.screens
    WidgetLayer { service: root; group: "bottom-blur" }
  }
  Variants {
    model: Quickshell.screens
    WidgetLayer { service: root; group: "top" }
  }
  Variants {
    model: Quickshell.screens
    WidgetLayer { service: root; group: "top-blur" }
  }
  Variants {
    model: Quickshell.screens
    WidgetLayer { service: root; editLayer: true }
  }

  // --- IPC: omarchy-shell hypr-screens.widgets <function> ------------------------------

  IpcHandler {
    target: "hypr-screens.widgets"

    function edit(): string {
      root.startEditing()
      return "ok"
    }
    function editing(): string { return root.editing ? "yes" : "no" }
    function placements(): string { return JSON.stringify(root.draft) }
    function done(): void { root.editing = false }
    function cancel(): void { root.cancelEditing() }
    function reload(): void { root.reloadSettings() }
  }
}
