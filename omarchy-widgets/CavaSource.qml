import QtQuick
import Quickshell.Io

// The visualizer's levels from cava: one value 0..1 per bar, all zero while
// it is quiet. cava only runs while a visualizer is on screen (a desktop view
// not hidden by its rules or a fullscreen window, or the bar's): they say so
// through use(user, on).
Item {
  id: cava

  required property var service
  property string config: ""

  property var levels: []
  property double lastFrame: 0
  property bool quiet: true
  property double quietSince: 0
  property var users: []
  readonly property bool wanted: service.enabled("visualizer") && cava.config !== "" && cava.users.length > 0

  function use(user, on) {
    var rest = cava.users.filter(function(u) { return u !== user })
    if (on) rest.push(user)
    if (rest.length !== cava.users.length) cava.users = rest
  }
  // Its settings changed (bars, player, smoothing): start it again at once.
  function restart() {
    if (!cava.wanted) return
    slowRetry.stop()
    process.running = false
    quickRestart.restart()
  }

  Process {
    id: process
    command: ["setpriv", "--pdeathsig", "TERM", "cava", "-p", cava.config]
    // Only ever what plays here, never the microphone: without its player's
    // stream cava ends instead of falling back to the default input, and is
    // started again below until the player plays.
    environment: ({ PIPEWIRE_PROPS: "{ node.dont-fallback = true }" })
    running: false
    stdout: SplitParser { onRead: function(line) { cava.takeFrame(line) } }
    onExited: if (cava.wanted && !quickRestart.running) slowRetry.restart()
  }
  onWantedChanged: {
    if (wanted) {
      slowRetry.stop()
      process.running = true
    } else {
      process.running = false
      slowRetry.stop()
      quickRestart.stop()
      cava.levels = []
      cava.quiet = true
      cava.quietSince = 0
    }
  }
  // Without cava (not installed yet) this retries quietly every ten seconds.
  Timer { id: slowRetry; interval: 10000; onTriggered: if (cava.wanted) process.running = true }
  // A restart after new settings, on its own timer: changing a running
  // timer's interval restarts it, so the slow one cannot be reused.
  Timer { id: quickRestart; interval: 300; onTriggered: if (cava.wanted) process.running = true }

  // One frame: a value per bar. Bars rise at once and fall a little slower
  // (light smoothing, so they need no animation of their own).
  function takeFrame(line) {
    var parts = String(line).split(";")
    var before = cava.levels
    var next = []
    var loud = false
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] === "") continue
      var value = Number(parts[i]) / 1000
      value = value > 0 ? Math.min(1, value) : 0
      var last = before[next.length]
      if (last !== undefined && value < last) value = last + (value - last) * 0.6
      if (value > 0.02) loud = true
      next.push(value)
    }
    cava.levels = next
    cava.lastFrame = Date.now()
    if (loud) cava.quiet = false
  }

  // cava stops printing while it sleeps: let the bars fall and fade out.
  Timer {
    interval: 500
    repeat: true
    running: cava.wanted
    onTriggered: {
      var stale = Date.now() - cava.lastFrame > 1000
      var max = 0
      for (var i = 0; i < cava.levels.length; i++) max = Math.max(max, cava.levels[i])
      if (stale || max < 0.02) {
        if (stale && max > 0) cava.levels = cava.levels.map(function() { return 0 })
        cava.quietSince = cava.quietSince || Date.now()
        if (Date.now() - cava.quietSince > 2000) cava.quiet = true
      } else {
        cava.quietSince = 0
      }
    }
  }
}
