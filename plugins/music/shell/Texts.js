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
