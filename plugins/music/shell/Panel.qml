// Tuneup's music widget: a note in the bar, always there (bright while music
// plays); a click opens what plays -- cover, title, artist, album, the
// progress (click or drag to seek), previous / play-pause / next, shuffle and
// repeat where the player has them, and a choice between players. For
// SlowTunes also "like" and the queue, through the desktop app's local control
// interface ($XDG_RUNTIME_DIR/slowtunes/control.json).
//
// Settings on its bar entry (Tuneup's Plugins page writes them):
//   player         "auto" | "slowtunes" | "spotify" -- which player to show first
//   timeRemaining  true: the time left instead of the length
//   language       the language Tuneup is set to
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Services.Mpris
import qs.Ui
import qs.Commons
import qs.Commons as Commons
import "Texts.js" as Texts

BarWidget {
  id: root
  moduleName: "tuneup.music"

  readonly property string language: String(setting("language", "en"))
  readonly property string preferredApp: String(setting("player", "auto"))
  readonly property bool timeRemaining: setting("timeRemaining", false) === true
  function tr(english) { return Texts.t(language, english) }

  // --- which player ---------------------------------------------------------

  readonly property var mediaService: bar?.shell?.firstPartyServiceFor("omarchy.media")
  readonly property var players: Mpris.players ? Mpris.players.values : []
  readonly property var shownPlayers: players.filter(function(p) { return p && (p.trackTitle || p.trackArtist) })
  // A player picked in the panel; cleared when it goes away.
  property var chosen: null

  function preferred() {
    if (preferredApp === "auto") return null
    for (var i = 0; i < shownPlayers.length; i++)
      if (Texts.appOf(shownPlayers[i]) === preferredApp) return shownPlayers[i]
    return null
  }

  readonly property var player: {
    if (chosen && shownPlayers.indexOf(chosen) >= 0) return chosen
    var pick = preferred()
    if (pick) return pick
    if (mediaService && mediaService.activePlayer) return mediaService.activePlayer
    for (var i = 0; i < shownPlayers.length; i++) if (shownPlayers[i].isPlaying) return shownPlayers[i]
    return shownPlayers.length ? shownPlayers[0] : null
  }

  readonly property bool hasMedia: !!player && !!(player.trackTitle || player.trackArtist)
  readonly property bool playing: !!player && !!player.isPlaying
  readonly property bool isSlowtunes: Texts.appOf(player) === "slowtunes"

  // The windows (pid, title) for naming what plays: a browser player is named
  // after its site ("SoundCloud", not "Helium"). Read again when the panel opens.
  readonly property var windows: Hyprland.toplevels.values.map(function(t) {
    var ipc = t.lastIpcObject || {}
    return { pid: Number(ipc.pid || 0), title: String(t.title || ipc.title || "") }
  })
  function nameOf(p) { return Texts.sourceName(p, root.windows) }
  onPopupOpenChanged: if (popupOpen) Hyprland.refreshToplevels()

  // --- the bar --------------------------------------------------------------

  property bool popupOpen: false
  function close() { popupOpen = false }

  // The bar lays its own pointer area over every widget (for dragging) and
  // shows the hand cursor only over widgets that answer triggerPress; a left
  // click then arrives here instead of at the MouseArea below.
  function triggerPress(button) {
    if (root.bar) root.bar.hideTooltip(root)
    root.popupOpen = !root.popupOpen
  }

  implicitWidth: barSize
  implicitHeight: barSize

  Text {
    anchors.centerIn: parent
    textFormat: Text.PlainText
    text: "󰝚"
    color: root.playing ? root.bar.barForeground : Qt.darker(root.bar.barForeground, 1.6)
    font.family: root.bar.fontFamily
    font.pixelSize: Style.font.body
    Behavior on color {
      enabled: !root.bar || root.bar.foregroundAnimationEnabled
      ColorAnimation { duration: Style.duration(160) }
    }
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
    onClicked: function(mouse) {
      if (mouse.button === Qt.MiddleButton) {
        if (root.player && root.player.canTogglePlaying) root.player.togglePlaying()
      } else {
        root.popupOpen = !root.popupOpen
      }
    }
    onWheel: function(wheel) {
      if (!root.player) return
      if (wheel.angleDelta.y > 0 && root.player.canGoPrevious) root.player.previous()
      else if (wheel.angleDelta.y < 0 && root.player.canGoNext) root.player.next()
    }
    onEntered: if (root.bar) root.bar.showTooltip(root, root.hasMedia
      ? (root.player.trackTitle + (root.player.trackArtist ? " — " + root.player.trackArtist : ""))
      : root.tr("Nothing playing"))
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }

  // --- progress -------------------------------------------------------------

  // MPRIS does not announce the position as it moves; ask while it is shown.
  Timer {
    running: root.popupOpen && root.playing
    interval: 1000
    repeat: true
    triggeredOnStart: true
    onTriggered: if (root.player) root.player.positionChanged()
  }

  readonly property real length: player && player.lengthSupported ? player.length : 0
  readonly property real position: player && player.positionSupported ? player.position : 0

  // --- SlowTunes: likes and the queue ----------------------------------------

  readonly property string runtimeDir: Quickshell.env("XDG_RUNTIME_DIR") || ""
  property var control: null   // {port, token} from the app's control.json
  property var tunes: null      // the app's /v1/state
  property bool likeBusy: false

  FileView {
    id: controlFile
    path: root.runtimeDir ? root.runtimeDir + "/slowtunes/control.json" : ""
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      try {
        var data = JSON.parse(text())
        root.control = data && data.version === 1 && data.port && data.token ? data : null
      } catch (e) {
        root.control = null
      }
      if (root.control) root.refreshTunes()
    }
    onLoadFailed: { root.control = null; root.tunes = null }
    // A file left by a SlowTunes that was killed points nowhere: its requests
    // fail and the extras stay hidden (tunes null), MPRIS works as for any player.
  }

  function request(method, path, body, done) {
    if (!control) return
    var xhr = new XMLHttpRequest()
    xhr.onreadystatechange = function() {
      if (xhr.readyState !== XMLHttpRequest.DONE) return
      if (xhr.status === 200) {
        try { done(JSON.parse(xhr.responseText)) } catch (e) { done(null) }
      } else {
        done(null)
      }
    }
    xhr.open(method, "http://127.0.0.1:" + control.port + path)
    xhr.setRequestHeader("Authorization", "Bearer " + control.token)
    if (body !== null) xhr.setRequestHeader("Content-Type", "application/json")
    xhr.send(body === null ? null : JSON.stringify(body))
  }

  function refreshTunes() {
    if (!control || !isSlowtunes) return
    request("GET", "/v1/state", null, function(state) { root.tunes = state })
  }

  function toggleLike() {
    if (!tunes || !tunes.track || likeBusy) return
    likeBusy = true
    request("POST", "/v1/like", { liked: !tunes.liked }, function(state) {
      root.likeBusy = false
      if (state) root.tunes = state
    })
  }

  // With the song's id: a queue that changed meanwhile answers 409 instead of
  // playing another song; the next refresh shows the new one.
  function playFromQueue(entry) {
    request("POST", "/v1/queue/play", { index: entry.index, id: entry.id }, function(state) {
      if (state) root.tunes = state
      else root.refreshTunes()
    })
  }

  Timer {
    running: root.popupOpen && root.isSlowtunes && !!root.control
    interval: 2000
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refreshTunes()
  }

  Connections {
    target: root.player
    ignoreUnknownSignals: true
    function onTrackTitleChanged() { if (root.popupOpen) root.refreshTunes() }
  }

  readonly property bool showLike: isSlowtunes && !!tunes && !!tunes.track
  readonly property var queue: isSlowtunes && tunes && tunes.queue ? tunes.queue.slice(0, 10) : []

  // --- the panel ------------------------------------------------------------

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(340))
    contentHeight: popup.fittedContentHeight(column.implicitHeight)

    Column {
      id: column
      anchors.fill: parent
      spacing: Style.space(10)

      // More than one player: pick the one shown, at the top.
      Flow {
        visible: root.shownPlayers.length > 1
        width: parent.width
        spacing: Style.space(4)

        Repeater {
          model: root.shownPlayers

          Button {
            required property var modelData
            text: root.nameOf(modelData) || "?"
            iconText: modelData.isPlaying ? "󰏤" : "󰐊"
            foreground: root.bar.foreground
            bordered: true
            selected: modelData === root.player
            onClicked: root.chosen = modelData
          }
        }
      }
      PanelSeparator {
        visible: root.shownPlayers.length > 1
        foreground: root.bar.foreground
      }

      // Nothing plays.
      Column {
        visible: !root.hasMedia
        width: parent.width
        spacing: Style.space(4)
        Text {
          textFormat: Text.PlainText
          text: root.tr("Nothing playing")
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.subtitle
          font.bold: true
        }
        Text {
          textFormat: Text.PlainText
          text: root.tr("Start music in SlowTunes, Spotify or the browser.")
          color: Qt.darker(root.bar.foreground, 1.4)
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
          width: parent.width
        }
      }

      // Cover and what plays.
      Row {
        visible: root.hasMedia
        width: parent.width
        spacing: Style.space(12)

        BorderSurface {
          id: cover
          width: Style.space(96)
          height: Style.space(96)
          radius: Style.spacing.labelGap
          color: Style.normalFillFor(root.bar.foreground, Commons.Color.accent)
          borderSpec: Border.controlSpec("normal", root.bar.foreground, Commons.Color.accent)

          SizedImage {
            anchors.fill: parent
            anchors.margins: Style.space(2)
            crop: true
            url: root.player && root.player.trackArtUrl ? root.player.trackArtUrl : ""
            visible: url != ""
          }
          Text {
            anchors.centerIn: parent
            visible: !root.player || !root.player.trackArtUrl
            text: "󰝚"
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.displayLarge
          }
        }

        Column {
          width: parent.width - cover.width - Style.space(12)
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(4)

          Text {
            textFormat: Text.PlainText
            text: root.player ? (root.player.trackTitle || "") : ""
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.subtitle
            font.bold: true
            elide: Text.ElideRight
            width: parent.width
          }
          Text {
            textFormat: Text.PlainText
            text: root.player ? (root.player.trackArtist || "") : ""
            color: Qt.darker(root.bar.foreground, 1.25)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
          }
          Text {
            textFormat: Text.PlainText
            text: root.player && root.player.trackAlbum ? root.player.trackAlbum : ""
            color: Qt.darker(root.bar.foreground, 1.6)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
          }
          Text {
            textFormat: Text.PlainText
            text: root.player ? root.nameOf(root.player) : ""
            color: Qt.darker(root.bar.foreground, 1.9)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
          }
        }
      }

      // Progress: click or drag to seek.
      Column {
        visible: root.hasMedia && root.length > 0
        width: parent.width
        spacing: Style.space(2)

        PanelSlider {
          width: parent.width
          bar: root.bar
          minimum: 0
          maximum: Math.max(1, root.length)
          step: 1
          value: root.position
          enabled: !!root.player && root.player.canSeek
          onReleased: function(value) { if (root.player && root.player.canSeek) root.player.position = value }
        }
        Item {
          width: parent.width
          height: elapsed.implicitHeight
          Text {
            id: elapsed
            anchors.left: parent.left
            textFormat: Text.PlainText
            text: Texts.clock(root.position)
            color: Qt.darker(root.bar.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
          }
          Text {
            anchors.right: parent.right
            textFormat: Text.PlainText
            text: root.timeRemaining ? "-" + Texts.clock(root.length - root.position) : Texts.clock(root.length)
            color: Qt.darker(root.bar.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
          }
        }
      }

      // Shuffle, previous, play/pause, next, repeat (and the heart for SlowTunes).
      Row {
        visible: root.hasMedia
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Style.space(4)
        LayoutMirroring.enabled: false
        LayoutMirroring.childrenInherit: true

        Button {
          anchors.verticalCenter: parent.verticalCenter
          visible: !!root.player && root.player.shuffleSupported
          iconText: "󰒟"
          tooltipText: root.tr("Shuffle")
          foreground: root.bar.foreground
          selected: !!root.player && root.player.shuffle
          opacity: selected ? 1.0 : 0.55
          onClicked: root.player.shuffle = !root.player.shuffle
        }
        Button {
          anchors.verticalCenter: parent.verticalCenter
          iconText: "󰒮"
          tooltipText: root.tr("Previous")
          foreground: root.bar.foreground
          enabled: !!root.player && root.player.canGoPrevious
          opacity: enabled ? 1.0 : 0.4
          onClicked: root.player.previous()
        }
        Button {
          anchors.verticalCenter: parent.verticalCenter
          iconText: root.playing ? "󰏤" : "󰐊"
          tooltipText: root.playing ? root.tr("Pause") : root.tr("Play")
          foreground: root.bar.foreground
          horizontalPadding: Style.spacing.panelGap
          iconSize: Style.font.iconLarge
          enabled: !!root.player && root.player.canTogglePlaying
          opacity: enabled ? 1.0 : 0.4
          onClicked: root.player.togglePlaying()
        }
        Button {
          anchors.verticalCenter: parent.verticalCenter
          iconText: "󰒭"
          tooltipText: root.tr("Next")
          foreground: root.bar.foreground
          enabled: !!root.player && root.player.canGoNext
          opacity: enabled ? 1.0 : 0.4
          onClicked: root.player.next()
        }
        Button {
          anchors.verticalCenter: parent.verticalCenter
          visible: !!root.player && root.player.loopSupported
          iconText: root.player && root.player.loopState === MprisLoopState.Track ? "󰑘" : "󰑖"
          tooltipText: root.tr("Repeat")
          foreground: root.bar.foreground
          selected: !!root.player && root.player.loopState !== MprisLoopState.None
          opacity: selected ? 1.0 : 0.55
          onClicked: {
            var state = root.player.loopState
            root.player.loopState = state === MprisLoopState.None ? MprisLoopState.Playlist
              : state === MprisLoopState.Playlist ? MprisLoopState.Track : MprisLoopState.None
          }
        }
        Button {
          anchors.verticalCenter: parent.verticalCenter
          visible: root.showLike
          iconText: root.tunes && root.tunes.liked ? "󰋑" : "󰋕"
          tooltipText: root.tunes && root.tunes.liked ? root.tr("Liked") : root.tr("Like")
          foreground: root.bar.foreground
          selected: !!root.tunes && root.tunes.liked
          enabled: !root.likeBusy
          onClicked: root.toggleLike()
        }
      }

      // SlowTunes: up next.
      PanelSeparator {
        visible: root.queue.length > 0
        foreground: root.bar.foreground
      }
      Text {
        visible: root.queue.length > 0
        textFormat: Text.PlainText
        text: root.tr("Up next")
        color: Qt.darker(root.bar.foreground, 1.4)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        font.bold: true
      }
      Column {
        id: queueList
        visible: root.queue.length > 0
        width: parent.width
        spacing: Style.space(2)

        Repeater {
          model: root.queue

          CursorSurface {
            id: queueRow
            required property var modelData
            width: queueList.width
            height: Style.space(40)
            hasCursor: queueMouse.containsMouse
            foreground: root.bar.foreground

            Row {
              anchors.fill: parent
              anchors.leftMargin: Style.space(6)
              anchors.rightMargin: Style.space(6)
              spacing: Style.space(8)

              SizedImage {
                width: Style.space(32)
                height: Style.space(32)
                anchors.verticalCenter: parent.verticalCenter
                crop: true
                url: queueRow.modelData.coverUrl || ""
                visible: url != ""
              }
              Column {
                width: parent.width - Style.space(84)
                anchors.verticalCenter: parent.verticalCenter
                Text {
                  textFormat: Text.PlainText
                  text: queueRow.modelData.title || ""
                  color: root.bar.foreground
                  font.family: root.bar.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  elide: Text.ElideRight
                  width: parent.width
                }
                Text {
                  textFormat: Text.PlainText
                  text: queueRow.modelData.artist || ""
                  color: Qt.darker(root.bar.foreground, 1.5)
                  font.family: root.bar.fontFamily
                  font.pixelSize: Style.font.caption
                  elide: Text.ElideRight
                  width: parent.width
                }
              }
              Text {
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.PlainText
                text: Texts.clock(queueRow.modelData.duration)
                color: Qt.darker(root.bar.foreground, 1.6)
                font.family: root.bar.fontFamily
                font.pixelSize: Style.font.caption
              }
            }

            MouseArea {
              id: queueMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: root.playFromQueue(queueRow.modelData)
            }
          }
        }
      }
    }
  }
}
