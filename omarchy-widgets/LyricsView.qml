import QtQuick
import qs.Commons

// The song's lines, synced to the player and scrolling like a teleprompter.
//
// The widget's box is the text: its height (`size`, in pixels) is split into
// one slot per visible line and the font fills the slot; a line too long for
// the width first gets smaller, then takes two rows in its slot. All lines sit
// in one column that slides up, so the line being sung stays in the middle
// slot: the next one comes up from below, the last one moves on up and fades.
// At the start and end of a song the lines fill the box from the top or to
// the bottom instead of leaving slots empty.
// Shown while there are synced lyrics (or while arranging).
//
// Highlight "line" colors the line being sung, "word" each word as it is sung
// (from the word times of the lyrics, or spread over the line), "off" none.
Item {
  id: view

  property var service: null
  property bool editing: false

  readonly property var settings: service ? service.widget("lyrics") : null
  // Alignment, sizes and motion are its look: as arranged (Service.style).
  readonly property var looks: service ? service.style("lyrics") : null
  // Its place and size on this screen (set by Placed).
  property var spot: null
  readonly property int shownLines: settings ? settings.lines : 3
  readonly property string highlight: settings ? settings.highlight : "line"
  readonly property string align: looks ? looks.align : "center"
  readonly property color tint: service ? service.tint("lyrics") : Color.accent
  readonly property var look: service ? service.textLook("lyrics") : ({ family: "", weight: 700, lighter: 400, spacing: 0, outline: false })
  function paint(part, fallback) { return view.service ? view.service.colorOf("lyrics", part, fallback) : fallback }
  readonly property bool hidePaused: !!(settings && settings.hide_paused)
  readonly property var lines: service ? service.lyricLines : []
  readonly property bool hasLyrics: lines.length > 0
  readonly property string sample: service && service.texts ? (service.texts.lyricsSample || "♪") : "♪"
  // What the column holds, and the line in the middle (-1: before the first).
  readonly property var shown: hasLyrics ? lines : (editing ? [{ t: 0, text: sample }] : [])
  readonly property int current: hasLyrics ? (service ? service.lyricIndex : -1) : 0

  readonly property real slot: height / Math.max(1, shownLines)
  // The font fills most of its slot; long lines go down to half of it.
  readonly property real fontSize: Math.max(8, Math.floor(slot * 0.6))
  // The other lines are smaller than the one being sung (current_size: how
  // much bigger it is, in percent).
  readonly property real restScale: 100 / (looks ? looks.current_size : 115)
  readonly property int scrollMs: looks ? looks.scroll_ms : 550

  implicitWidth: spot && spot.width > 0 ? spot.width : 720
  implicitHeight: spot ? spot.size : 200
  width: implicitWidth
  height: implicitHeight
  opacity: editing || (hasLyrics && (!hidePaused || (service && service.playing))) ? 1 : 0
  Behavior on opacity { NumberAnimation { duration: 500 } }

  // The line being sung, word by word (the Loader in each line): each word's place,
  // worked out once per line from the font size the line got (Text.Fit on
  // the plain line), so the highlight only moves a clip as the song plays.
  FontMetrics {
    id: wordMetrics
    font.family: view.look.family
    font.pixelSize: view.fontSize
    font.weight: view.look.weight
    font.letterSpacing: view.look.spacing * view.fontSize / 30
  }
  // {text, t, end, x, y, width} for each word in a box of width × height at
  // `pixels`, wrapped like the line and aligned like it; smaller while the
  // rows do not fit (down to half the size). Widths are measured once at the
  // full size and scaled.
  function placeWords(index, width, height, pixels) {
    var timed = view.service ? view.service.wordsFor(index) : []
    if (!timed.length || width <= 0 || pixels <= 0) return { size: pixels, words: [] }
    var widths = timed.map(function(w) { return wordMetrics.advanceWidth(w.text) })
    var space = wordMetrics.advanceWidth(" ")
    var size = pixels
    var rows = []
    for (var tries = 0; tries < 8; tries++) {
      var f = size / view.fontSize
      rows = [{ width: 0, words: [] }]
      for (var i = 0; i < timed.length; i++) {
        var row = rows[rows.length - 1]
        var w = widths[i] * f
        var gap = row.words.length ? space * f : 0
        if (row.words.length && row.width + gap + w > width) {
          row = { width: 0, words: [] }
          rows.push(row)
          gap = 0
        }
        row.words.push({ i: i, x: row.width + gap, width: w })
        row.width += gap + w
      }
      if (rows.length * wordMetrics.height * f * 0.95 <= height * 1.02 || size <= view.fontSize / 2) break
      size = Math.max(view.fontSize / 2, size * 0.92)
    }
    var lineHeight = wordMetrics.height * (size / view.fontSize) * 0.95
    var top = (height - rows.length * lineHeight) / 2
    var out = []
    for (var r = 0; r < rows.length; r++) {
      var left = view.align === "left" ? 0 : view.align === "right" ? width - rows[r].width : (width - rows[r].width) / 2
      for (var k = 0; k < rows[r].words.length; k++) {
        var placed = rows[r].words[k]
        var word = timed[placed.i]
        out.push({ text: word.text, t: word.t, end: word.end, x: left + placed.x, y: top + r * lineHeight,
                   width: placed.width, height: lineHeight })
      }
    }
    return { size: size, words: out }
  }

  // One word of the line being sung (its height: the row's).
  component LyricWord: Text {
    property real pixels: view.fontSize
    height: parent ? parent.height : 0
    verticalAlignment: Text.AlignVCenter
    textFormat: Text.PlainText
    font.family: view.look.family
    font.pixelSize: Math.max(6, Math.round(pixels))
    font.weight: view.look.weight
    font.letterSpacing: view.look.spacing * pixels / 30
    style: view.look.outline ? Text.Outline : Text.Normal
    styleColor: view.look.outline ? view.look.outlineColor : "transparent"
  }

  // Where the column goes: the current line in the middle slot (the upper of
  // the two with an even number of lines), but never past the first line at
  // the top or the last at the bottom; fewer lines than slots sit in the middle.
  readonly property real columnY: {
    var total = view.shown.length * view.slot
    if (total <= view.height) return (view.height - total) / 2
    var middle = (Math.floor((view.shownLines - 1) / 2) - view.current) * view.slot
    return Math.max(view.height - total, Math.min(0, middle))
  }

  // A new song (or lyrics) jumps into place; only the next line scrolls.
  property bool jumping: false
  onShownChanged: { jumping = true; Qt.callLater(function() { view.jumping = false }) }

  Column {
    id: column
    width: view.width
    y: view.columnY
    Behavior on y {
      enabled: !view.jumping
      NumberAnimation { duration: view.scrollMs; easing.type: Easing.OutCubic }
    }

    Repeater {
      model: view.shown
      Item {
        id: line
        required property var modelData
        required property int index
        readonly property int distance: index - view.current
        readonly property bool sung: distance === 0
        readonly property bool byWord: sung && view.highlight === "word" && view.hasLyrics
        width: column.width
        height: view.slot
        transformOrigin: view.align === "left" ? Item.Left : (view.align === "right" ? Item.Right : Item.Center)
        // Inside the box once the column has moved: the coming lines a bit
        // brighter than the ones sung; outside it, gone.
        readonly property real slotTop: view.columnY + index * view.slot
        readonly property bool inside: slotTop > -view.slot / 2 && slotTop + view.slot < view.height + view.slot / 2
        opacity: !inside ? 0 : (sung ? 1 : (distance > 0 ? 0.7 : 0.4))
        scale: sung ? 1 : view.restScale
        Behavior on opacity { NumberAnimation { duration: view.scrollMs * 0.8; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: view.scrollMs * 0.8; easing.type: Easing.OutCubic } }

        // The line as plain text: Text.Fit finds its size once (the text only
        // changes with the line). Word by word it only lends that size.
        Text {
          id: plain
          anchors.fill: parent
          opacity: line.byWord && words.status === Loader.Ready ? 0 : 1
          horizontalAlignment: view.align === "left" ? Text.AlignLeft : (view.align === "right" ? Text.AlignRight : Text.AlignHCenter)
          verticalAlignment: Text.AlignVCenter
          wrapMode: Text.WordWrap
          fontSizeMode: Text.Fit
          minimumPixelSize: Math.max(6, Math.floor(view.fontSize / 2))
          lineHeight: 0.95
          textFormat: Text.PlainText
          text: line.modelData.text || "♪"
          color: line.sung ? (view.highlight === "line" ? view.paint("current", view.tint) : view.paint("waiting", Color.foreground))
                           : view.paint(line.distance > 0 ? "upcoming" : "past", Color.foreground)
          font.family: view.look.family
          font.pixelSize: view.fontSize
          font.weight: view.look.weight
          font.letterSpacing: view.look.spacing * view.fontSize / 30
          style: view.look.outline ? Text.Outline : Text.Normal
          styleColor: view.look.outline ? view.look.outlineColor : "transparent"
          Behavior on color { ColorAnimation { duration: 350 } }
        }

        // Word by word: each word in the color still to sing, the sung part
        // of it covered by the same word in the sung color (a clip that
        // grows with the song: no text is laid out again while it plays).
        Loader {
          id: words
          anchors.fill: parent
          active: line.byWord
          sourceComponent: Item {
            id: wordBox
            readonly property var layout: view.placeWords(line.index, line.width, line.height,
                                                          plain.fontInfo.pixelSize || view.fontSize)
            readonly property color sungColor: view.paint("sung", view.tint)
            readonly property color waitingColor: view.paint("waiting", Color.foreground)
            Repeater {
              model: wordBox.layout.words
              Item {
                id: word
                required property var modelData
                readonly property real fill: {
                  var now = (view.service ? view.service.songTime : 0) + 0.1
                  if (now >= modelData.end) return 1
                  if (now <= modelData.t) return 0
                  return (now - modelData.t) / Math.max(0.05, modelData.end - modelData.t)
                }
                x: modelData.x
                y: modelData.y
                width: modelData.width
                height: modelData.height
                LyricWord { text: word.modelData.text; pixels: wordBox.layout.size; color: wordBox.waitingColor }
                Item {
                  visible: word.fill > 0
                  width: Math.round(word.fill * (word.width + 2))
                  height: word.height
                  clip: true
                  LyricWord { text: word.modelData.text; pixels: wordBox.layout.size; color: wordBox.sungColor }
                }
              }
            }
          }
        }

        PartHit { part: line.sung ? (view.highlight === "line" ? "current" : view.highlight === "word" ? "sung" : "waiting")
                                  : (line.distance > 0 ? "upcoming" : "past") }
      }
    }
  }
}
