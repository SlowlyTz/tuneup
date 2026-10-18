import QtQuick

// The player the Now Playing widget shows, and its position (asked twice a second).
Item {
  id: media

  required property var service

  property var player: null
  property real position: 0

  Timer {
    interval: 500
    repeat: true
    running: media.service.enabled("nowplaying")
    triggeredOnStart: true
    onTriggered: {
      var settings = media.service.widget("nowplaying")
      var next = media.service.pickPlayer(settings ? settings.player : "", media.player)
      if (next !== media.player) media.player = next
      if (next && next.isPlaying) next.positionChanged()
      media.position = next ? Number(next.position || 0) : 0
    }
  }
}
