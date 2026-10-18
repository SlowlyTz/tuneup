import QtQuick

// The lyrics of the song playing (Mpris + lrclib.net): its lines with their
// times, the line being sung and, word by word, the time in the song.
Item {
  id: lyrics

  required property var service
  required property var requests

  property var player: null
  property string trackKey: ""
  property var lines: []           // [{t: seconds, text, words: [{t, text}] or null}]
  property int index: -1
  property bool playing: false
  // The player's position and when it was read; songTime runs on from it
  // smoothly while words are highlighted.
  property real positionAt: 0
  property double positionStamp: 0
  property real songTime: 0
  property string lyricsState: "none"  // none | loading | synced | missing
  property var cache: ({})
  readonly property bool wanted: service.enabled("lyrics")
  readonly property bool wordsWanted: wanted && service.widget("lyrics") && service.widget("lyrics").highlight === "word"
  readonly property var userAgent: ({ "User-Agent": "hypr-screens (https://github.com/SlowlyTz/hypr-minimizer)" })

  Timer {
    interval: 250
    repeat: true
    running: lyrics.wanted
    onTriggered: {
      var settings = lyrics.service.widget("lyrics")
      var next = lyrics.service.pickPlayer(settings ? settings.player : "", lyrics.player)
      if (next !== lyrics.player) lyrics.player = next
      var p = lyrics.player
      if (!p) { lyrics.trackKey = ""; lyrics.lines = []; lyrics.lyricsState = "none"; lyrics.playing = false; return }
      var key = String(p.trackArtist || "") + "\u0001" + String(p.trackTitle || "")
      if (key !== lyrics.trackKey) {
        lyrics.trackKey = key
        lyrics.index = -1
        lyrics.load(p)
      }
      if (p.isPlaying) p.positionChanged()
      lyrics.playing = !!p.isPlaying
      lyrics.positionAt = Number(p.position || 0)
      lyrics.positionStamp = Date.now()
      lyrics.songTime = lyrics.positionAt
      lyrics.index = lyrics.lineAt(lyrics.positionAt)
    }
  }
  Timer {
    interval: 40
    repeat: true
    running: lyrics.wordsWanted && lyrics.playing && lyrics.lines.length > 0
    onTriggered: lyrics.songTime = lyrics.positionAt + (Date.now() - lyrics.positionStamp) / 1000
  }

  function lineAt(seconds) {
    var found = -1
    for (var i = 0; i < lyrics.lines.length; i++) {
      if (lyrics.lines[i].t <= seconds + 0.25) found = i
      else break
    }
    return found
  }

  function parseSynced(text) {
    var out = []
    var rows = String(text || "").split("\n")
    for (var i = 0; i < rows.length; i++) {
      var match = rows[i].match(/^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$/)
      if (!match) continue
      var clean = match[3].replace(/<\d+:\d+(?:\.\d+)?>/g, " ").replace(/\s+/g, " ").trim()
      out.push({ t: Number(match[1]) * 60 + Number(match[2]), text: clean, words: lyrics.parseWords(match[3]) })
    }
    return out
  }

  // Enhanced LRC ("<00:12.34>word <00:12.80>word"): a time for each word.
  function parseWords(line) {
    if (!/<\d+:\d+(?:\.\d+)?>/.test(line)) return null
    var words = []
    var time = null
    var parts = String(line).split(/(<\d+:\d+(?:\.\d+)?>)/)
    for (var i = 0; i < parts.length; i++) {
      var tag = parts[i].match(/^<(\d+):(\d+(?:\.\d+)?)>$/)
      if (tag) { time = Number(tag[1]) * 60 + Number(tag[2]); continue }
      var pieces = parts[i].split(/\s+/)
      for (var j = 0; j < pieces.length; j++) {
        if (pieces[j] !== "" && time !== null) words.push({ t: time, text: pieces[j] })
      }
    }
    return words.length ? words : null
  }

  // The words of a line with the time each is sung: from the lyrics when they
  // have them, otherwise spread over the line by their length (the singing
  // takes about a tenth of a second a letter, at most most of the line).
  function wordsFor(index) {
    var line = lyrics.lines[index]
    if (!line) return []
    var lineEnd = index + 1 < lyrics.lines.length ? lyrics.lines[index + 1].t : line.t + 6
    if (line.words) {
      // Each word lasts until the next one (the last one up to a second).
      return line.words.map(function(w, i, all) {
        return { t: w.t, text: w.text, end: i + 1 < all.length ? all[i + 1].t : Math.min(lineEnd, w.t + 1) }
      })
    }
    var words = String(line.text).split(/\s+/).filter(function(w) { return w !== "" })
    var letters = 0
    for (var i = 0; i < words.length; i++) letters += words[i].length + 1
    var duration = Math.min((lineEnd - line.t) * 0.9, Math.max(1.2, letters * 0.1))
    var out = []
    var time = line.t
    for (var k = 0; k < words.length; k++) {
      var next = time + duration * (words[k].length + 1) / letters
      out.push({ t: time, text: words[k], end: next })
      time = next
    }
    return out
  }

  function load(p) {
    var title = String(p.trackTitle || "")
    var artist = String(p.trackArtist || "")
    if (!title) { lyrics.lines = []; lyrics.lyricsState = "none"; return }
    var key = lyrics.trackKey
    if (lyrics.cache[key] !== undefined) {
      lyrics.lines = lyrics.cache[key]
      lyrics.lyricsState = lyrics.lines.length ? "synced" : "missing"
      return
    }
    lyrics.lines = []
    lyrics.lyricsState = "loading"
    var query = "track_name=" + encodeURIComponent(title) + "&artist_name=" + encodeURIComponent(artist)
    if (p.trackAlbum) query += "&album_name=" + encodeURIComponent(String(p.trackAlbum))
    if (p.lengthSupported && p.length > 0) query += "&duration=" + Math.round(p.length)
    lyrics.ask("https://lrclib.net/api/get?" + query, key, function(data) {
      return data && data.syncedLyrics ? lyrics.parseSynced(data.syncedLyrics) : null
    }, function() {
      // No exact match (album or length differ): search by title and artist.
      lyrics.ask("https://lrclib.net/api/search?track_name=" + encodeURIComponent(title)
                 + "&artist_name=" + encodeURIComponent(artist), key, function(list) {
        for (var i = 0; list && i < list.length; i++) {
          if (list[i].syncedLyrics) return lyrics.parseSynced(list[i].syncedLyrics)
        }
        return []
      }, function() { lyrics.store(key, []) })
    })
  }

  // parse(answer) → lines, or null: otherwise() is asked next.
  function ask(url, key, parse, otherwise) {
    lyrics.requests.get(url, function(xhr) {
      if (key !== lyrics.trackKey) return
      // No answer (offline, given up) or a server error: not a song without
      // lyrics, so it is not remembered as one and asked again soon.
      if (xhr.status === 0 || xhr.status >= 500) { lyrics.failed(key); return }
      var data = lyrics.requests.json(xhr)
      var lines = null
      try { lines = data === null ? null : parse(data) } catch (e) { lines = null }
      if (lines === null) otherwise()
      else lyrics.store(key, lines)
    }, lyrics.userAgent)
  }

  function failed(key) {
    lyrics.lyricsState = "missing"
    retry.key = key
    retry.restart()
  }
  Timer {
    id: retry
    property string key: ""
    interval: 30000
    onTriggered: if (key === lyrics.trackKey && lyrics.player && lyrics.cache[key] === undefined) lyrics.load(lyrics.player)
  }

  function store(key, lines) {
    var cache = Object.assign({}, lyrics.cache)
    cache[key] = lines
    lyrics.cache = cache
    if (key !== lyrics.trackKey) return
    lyrics.lines = lines
    lyrics.lyricsState = lines.length ? "synced" : "missing"
  }
}
