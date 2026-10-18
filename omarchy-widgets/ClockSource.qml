import QtQuick
import Quickshell.Io

// The time, every second while the clock or the calendar is on, and the
// second time zone's offset (from `date`, so summer time is right; asked
// again every ten minutes).
Item {
  id: clock

  required property var service

  property date now: new Date()
  readonly property string zone: service.widget("clock") ? String(service.widget("clock").zone2 || "") : ""
  property int zoneOffset: 0
  property bool zoneKnown: false

  Timer {
    interval: 1000
    repeat: true
    running: clock.service.enabled("clock") || clock.service.enabled("calendar")
    triggeredOnStart: true
    onTriggered: clock.now = new Date()
  }

  onZoneChanged: { clock.zoneKnown = false; clock.askZone() }
  // The command is set here: a binding on `zone` could still hold the old one.
  function askZone() {
    if (!clock.zone || zoneProcess.running) return
    zoneProcess.command = ["sh", "-c", "TZ=\"$1\" date +%z", "sh", clock.zone]
    zoneProcess.running = true
  }
  Process {
    id: zoneProcess
    stdout: StdioCollector {
      onStreamFinished: {
        var match = String(text).trim().match(/^([+-])(\d\d)(\d\d)$/)
        if (!match) return
        clock.zoneOffset = (match[1] === "-" ? -1 : 1) * (Number(match[2]) * 60 + Number(match[3]))
        clock.zoneKnown = true
      }
    }
  }
  Timer {
    interval: 600000
    repeat: true
    running: clock.zone !== "" && clock.service.enabled("clock")
    onTriggered: clock.askZone()
  }

  function zoneTime(date) {
    return new Date(date.getTime() + (clock.zoneOffset + date.getTimezoneOffset()) * 60000)
  }
}
