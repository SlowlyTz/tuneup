// The widget's own texts; Tuneup writes the chosen language onto its bar entry.
.pragma library

var TABLE = {
  de: {
    "Nothing playing": "Nichts läuft",
    "Start music in SlowTunes, Spotify or the browser.": "Starte Musik in SlowTunes, Spotify oder im Browser.",
    "Up next": "Als Nächstes",
    "Like": "Gefällt mir",
    "Liked": "Gefällt dir",
    "Shuffle": "Zufällig",
    "Repeat": "Wiederholen",
    "Previous": "Zurück",
    "Next": "Weiter",
    "Play": "Abspielen",
    "Pause": "Pause",
    "Players": "Player",
    "Music": "Musik",
  },
  es: {
    "Nothing playing": "No suena nada",
    "Start music in SlowTunes, Spotify or the browser.": "Pon música en SlowTunes, Spotify o el navegador.",
    "Up next": "A continuación",
    "Like": "Me gusta",
    "Liked": "Te gusta",
    "Shuffle": "Aleatorio",
    "Repeat": "Repetir",
    "Previous": "Anterior",
    "Next": "Siguiente",
    "Play": "Reproducir",
    "Pause": "Pausa",
    "Players": "Reproductores",
    "Music": "Música",
  },
  fr: {
    "Nothing playing": "Rien en lecture",
    "Start music in SlowTunes, Spotify or the browser.": "Lance de la musique dans SlowTunes, Spotify ou le navigateur.",
    "Up next": "À suivre",
    "Like": "J’aime",
    "Liked": "Aimé",
    "Shuffle": "Aléatoire",
    "Repeat": "Répéter",
    "Previous": "Précédent",
    "Next": "Suivant",
    "Play": "Lecture",
    "Pause": "Pause",
    "Players": "Lecteurs",
    "Music": "Musique",
  },
  it: {
    "Nothing playing": "Nessuna riproduzione",
    "Start music in SlowTunes, Spotify or the browser.": "Avvia la musica in SlowTunes, Spotify o nel browser.",
    "Up next": "Prossimi brani",
    "Like": "Mi piace",
    "Liked": "Ti piace",
    "Shuffle": "Casuale",
    "Repeat": "Ripeti",
    "Previous": "Precedente",
    "Next": "Successivo",
    "Play": "Riproduci",
    "Pause": "Pausa",
    "Players": "Lettori",
    "Music": "Musica",
  },
}

function t(language, english) {
  var table = TABLE[language]
  return table && table[english] ? table[english] : english
}

// 3:07, or 1:02:03 for an hour and more.
function clock(seconds) {
  var s = Math.max(0, Math.floor(seconds || 0))
  var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60
  var pad = function(n) { return n < 10 ? "0" + n : "" + n }
  return h > 0 ? h + ":" + pad(m) + ":" + pad(r) : m + ":" + pad(r)
}

// Which app a player is: "slowtunes", "spotify" or "" (anything else).
function appOf(player) {
  if (!player) return ""
  var name = ((player.identity || "") + " " + (player.desktopEntry || "") + " " + (player.dbusName || "")).toLowerCase()
  if (name.indexOf("slowtunes") >= 0) return "slowtunes"
  if (name.indexOf("spotify") >= 0) return "spotify"
  return ""
}

// Music services a browser player may be: found in a window's title.
var SERVICES = ["SoundCloud", "YouTube Music", "Spotify", "Deezer", "TIDAL", "Apple Music", "Amazon Music",
                "Bandcamp", "Mixcloud", "Audiomack", "Qobuz", "Napster", "Twitch", "YouTube"]

function serviceIn(title) {
  var lower = (title || "").toLowerCase()
  for (var i = 0; i < SERVICES.length; i++) if (lower.indexOf(SERVICES[i].toLowerCase()) >= 0) return SERVICES[i]
  return ""
}

// The browser process behind a player: Chromium-style players are named
// "...chromium.instance5637", Firefox "...firefox.instance_1_23" (the pid).
function playerPid(player) {
  var match = /\.instance_?(\d+)/.exec(player && player.dbusName ? player.dbusName : "")
  return match ? Number(match[1]) : 0
}

// What plays: for a browser (Helium, Chrome, Firefox …) the site, from the
// windows of the same process -- web apps (SoundCloud as a desktop app) and
// tabs. A window naming the song wins; else the one music service open there;
// else the player's own name.
function sourceName(player, windows) {
  var own = player ? (player.identity || player.desktopEntry || "") : ""
  var pid = playerPid(player)
  if (!pid) return own
  var mine = windows.filter(function(w) { return w.pid === pid })
  var song = (player.trackTitle || "").toLowerCase()
  if (song.length >= 3) {
    for (var i = 0; i < mine.length; i++) {
      if (mine[i].title.toLowerCase().indexOf(song) >= 0) {
        var named = serviceIn(mine[i].title)
        if (named) return named
      }
    }
  }
  var found = []
  for (var j = 0; j < mine.length; j++) {
    var service = serviceIn(mine[j].title)
    if (service && found.indexOf(service) < 0) found.push(service)
  }
  return found.length === 1 ? found[0] : own
}
