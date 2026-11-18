// Tuneup's part of the display panel: the "Screens" section's texts (Tuneup
// writes its language onto the bar entry) and what the screens are, from
// `tuneup state` and `hyprctl monitors all -j`.
.pragma library

var TABLE = {
  de: {
    "Screens": "Bildschirme",
    "Extended": "Erweitert",
    "Mirrored": "Gespiegelt",
    "Partly mirrored": "Teils gespiegelt",
    "Laptop only": "Nur Laptop",
    "External only": "Nur extern",
    "One screen": "Ein Bildschirm",
    "Extend": "Erweitern",
    "Mirror": "Spiegeln",
    "Mirrors %1": "Spiegelt %1",
    "Own desktop": "Eigener Desktop",
    "Off": "Aus",
    "Laptop": "Laptop",
    "Switching…": "Wird umgestellt …",
    "Screen settings in Tuneup": "Bildschirm-Einstellungen in Tuneup",
  },
  es: {
    "Screens": "Pantallas",
    "Extended": "Extendido",
    "Mirrored": "Duplicado",
    "Partly mirrored": "Duplicado en parte",
    "Laptop only": "Solo portátil",
    "External only": "Solo externa",
    "One screen": "Una pantalla",
    "Extend": "Extender",
    "Mirror": "Duplicar",
    "Mirrors %1": "Duplica %1",
    "Own desktop": "Escritorio propio",
    "Off": "Apagada",
    "Laptop": "Portátil",
    "Switching…": "Cambiando…",
    "Screen settings in Tuneup": "Ajustes de pantalla en Tuneup",
  },
  fr: {
    "Screens": "Écrans",
    "Extended": "Étendu",
    "Mirrored": "Dupliqué",
    "Partly mirrored": "En partie dupliqué",
    "Laptop only": "Portable seul",
    "External only": "Externe seul",
    "One screen": "Un écran",
    "Extend": "Étendre",
    "Mirror": "Dupliquer",
    "Mirrors %1": "Duplique %1",
    "Own desktop": "Bureau à part",
    "Off": "Éteint",
    "Laptop": "Portable",
    "Switching…": "Changement…",
    "Screen settings in Tuneup": "Réglages des écrans dans Tuneup",
  },
  it: {
    "Screens": "Schermi",
    "Extended": "Esteso",
    "Mirrored": "Duplicato",
    "Partly mirrored": "In parte duplicato",
    "Laptop only": "Solo portatile",
    "External only": "Solo esterno",
    "One screen": "Uno schermo",
    "Extend": "Estendi",
    "Mirror": "Duplica",
    "Mirrors %1": "Duplica %1",
    "Own desktop": "Desktop proprio",
    "Off": "Spento",
    "Laptop": "Portatile",
    "Switching…": "Cambio in corso…",
    "Screen settings in Tuneup": "Impostazioni schermi in Tuneup",
  },
}

function t(language, english) {
  var table = TABLE[language]
  return table && table[english] ? table[english] : english
}

var INTERNAL = ["eDP", "LVDS", "DSI"]

function isInternalConnector(name) {
  name = String(name || "")
  for (var i = 0; i < INTERNAL.length; i++) if (name.indexOf(INTERNAL[i]) === 0) return true
  return false
}

function parseJson(raw, fallback) {
  try {
    var value = JSON.parse(String(raw || ""))
    return value === null || value === undefined ? fallback : value
  } catch (e) {
    return fallback
  }
}

// The connected screens, laptop first: {id, name, connector, internal, active,
// width, height, refresh, mirrorOf}. id is what `tuneup set` takes (Tuneup's
// screen id; the connector when Tuneup does not know the screen). The live
// truth (on, resolution, mirroring) is Hyprland's; names come from Tuneup.
function screens(stateRaw, monitorsRaw) {
  var state = parseJson(stateRaw, {})
  var monitors = parseJson(monitorsRaw, [])
  if (!Array.isArray(monitors)) monitors = []
  var known = state && Array.isArray(state.screens) ? state.screens : []
  var list = []
  for (var i = 0; i < monitors.length; i++) {
    var m = monitors[i]
    if (!m || !m.name || m.name === "FALLBACK" || String(m.name).indexOf("HEADLESS") === 0) continue
    var tuned = null
    for (var j = 0; j < known.length; j++) {
      if (known[j] && known[j].connected && known[j].connector === m.name) { tuned = known[j]; break }
    }
    var mirrorOf = String(m.mirrorOf || "none")
    list.push({
      id: tuned ? String(tuned.id) : String(m.name),
      name: tuned ? String(tuned.name) : String(m.description || m.model || m.name),
      connector: String(m.name),
      internal: tuned ? tuned.internal === true : isInternalConnector(m.name),
      active: m.disabled !== true,
      width: Number(m.width || 0),
      height: Number(m.height || 0),
      refresh: Number(m.refreshRate || 0),
      mirrorOf: mirrorOf === "none" ? "" : mirrorOf
    })
  }
  list.sort(function(a, b) {
    if (a.internal !== b.internal) return a.internal ? -1 : 1
    return a.connector < b.connector ? -1 : a.connector > b.connector ? 1 : 0
  })
  return list
}

// How the screens are used, as one word: "single", "laptop" (externals off),
// "external" (laptop off), "mirrored", "extended" or "mixed".
function mode(list) {
  var laptopOn = false, externals = 0, mirrored = 0, hasLaptop = false
  for (var i = 0; i < list.length; i++) {
    var s = list[i]
    if (s.internal) { hasLaptop = true; if (s.active) laptopOn = true; continue }
    if (!s.active) continue
    externals++
    if (s.mirrorOf) mirrored++
  }
  if (externals === 0) return list.length > 1 && hasLaptop ? "laptop" : "single"
  if (hasLaptop && !laptopOn) return "external"
  if (mirrored === 0) return "extended"
  return mirrored === externals ? "mirrored" : "mixed"
}

function modeText(language, word) {
  var english = {
    single: "One screen", laptop: "Laptop only", external: "External only",
    mirrored: "Mirrored", extended: "Extended", mixed: "Partly mirrored"
  }[word] || ""
  return english ? t(language, english) : ""
}

// "DP-4 · 1920×1080 · 60 Hz"
function details(screen) {
  var parts = [screen.connector]
  if (screen.active && screen.width > 0 && screen.height > 0) {
    parts.push(screen.width + "×" + screen.height)
    if (screen.refresh > 0) parts.push(Math.round(screen.refresh) + " Hz")
  }
  return parts.join(" · ")
}

// What a screen does now: "Mirrors Laptop", "Own desktop", "Off".
function status(language, screen, list) {
  if (!screen.active) return t(language, "Off")
  if (screen.mirrorOf) {
    var source = screen.mirrorOf
    for (var i = 0; i < list.length; i++)
      if (list[i].connector === screen.mirrorOf) source = list[i].internal ? t(language, "Laptop") : list[i].name
    return t(language, "Mirrors %1").replace("%1", source)
  }
  return t(language, "Own desktop")
}

if (typeof module !== "undefined") {
  module.exports = { t: t, screens: screens, mode: mode, modeText: modeText, details: details, status: status }
}
