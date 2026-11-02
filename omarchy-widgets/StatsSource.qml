import QtQuick
import Quickshell.Io

// What the system, network and disk widgets show: CPU, memory and
// temperature, the network's speed (with the last two minutes as curves) and
// how full the disks are. Read straight from /proc every two seconds (no
// processes started); the disks from `df` once a minute.
Item {
  id: stats

  required property var service
  property string temperatureFile: ""

  readonly property int historyLength: 60
  readonly property bool systemWanted: service.enabled("system")
  readonly property bool networkWanted: service.enabled("network")

  property real cpu: 0
  property real memory: 0
  property real temperature: 0
  property var cpuHistory: []
  property var memoryHistory: []
  property var temperatureHistory: []
  property var lastCpu: null

  property real netDown: 0       // bytes a second
  property real netUp: 0
  property var netDownHistory: []
  property var netUpHistory: []
  property var lastNet: null

  property var disks: []         // [{mount, size, used}]

  function pushHistory(list, value) {
    var next = list.slice(Math.max(0, list.length - (stats.historyLength - 1)))
    next.push(value)
    return next
  }

  // Back on after a while: the first sample must not average over the whole gap.
  onSystemWantedChanged: if (!systemWanted) lastCpu = null
  onNetworkWantedChanged: if (!networkWanted) lastNet = null

  // --- system ---

  FileView { id: procStat; path: stats.systemWanted ? "/proc/stat" : ""; blockLoading: true; printErrors: false }
  FileView { id: procMemory; path: stats.systemWanted ? "/proc/meminfo" : ""; blockLoading: true; printErrors: false }
  FileView { id: temperatureSource; path: stats.systemWanted ? stats.temperatureFile : ""; blockLoading: true; printErrors: false }
  Timer {
    interval: 2000
    repeat: true
    running: stats.systemWanted
    triggeredOnStart: true
    onTriggered: {
      procStat.reload()
      procMemory.reload()
      if (stats.temperatureFile) temperatureSource.reload()
      stats.takeSystem(procStat.text(), procMemory.text(), stats.temperatureFile ? temperatureSource.text() : "0")
    }
  }

  function takeSystem(stat, memory, temperature) {
    var fields = (String(stat || "").split("\n")[0] || "").trim().split(/\s+/).slice(1).map(Number)
    if (fields.length >= 4) {
      var idle = fields[3] + (fields[4] || 0)
      var total = 0
      // user ... steal: guest and guest_nice are counted in user and nice already
      for (var i = 0; i < Math.min(8, fields.length); i++) total += fields[i]
      if (stats.lastCpu) {
        var dt = total - stats.lastCpu.total
        stats.cpu = dt > 0 ? Math.max(0, Math.min(1, 1 - (idle - stats.lastCpu.idle) / dt)) : 0
      }
      stats.lastCpu = { total: total, idle: idle }
    }
    var memTotal = String(memory || "").match(/^MemTotal:\s+(\d+)/m)
    var memAvailable = String(memory || "").match(/^MemAvailable:\s+(\d+)/m)
    if (memTotal && memAvailable && Number(memTotal[1]) > 0) stats.memory = 1 - Number(memAvailable[1]) / Number(memTotal[1])
    var degrees = Number(String(temperature || "0").trim()) || 0
    stats.temperature = degrees > 1000 ? degrees / 1000 : degrees
    stats.cpuHistory = stats.pushHistory(stats.cpuHistory, stats.cpu)
    stats.memoryHistory = stats.pushHistory(stats.memoryHistory, stats.memory)
    stats.temperatureHistory = stats.pushHistory(stats.temperatureHistory, Math.min(1, stats.temperature / 100))
  }

  // --- network: /proc/net/dev ---

  FileView { id: procNet; path: stats.networkWanted ? "/proc/net/dev" : ""; blockLoading: true; printErrors: false }
  Timer {
    interval: 2000
    repeat: true
    running: stats.networkWanted
    triggeredOnStart: true
    onTriggered: {
      procNet.reload()
      stats.takeNet(procNet.text())
    }
  }
  function takeNet(text) {
    var rx = 0, tx = 0
    var rows = String(text).split("\n")
    for (var i = 2; i < rows.length; i++) {
      var match = rows[i].match(/^\s*([^:]+):\s*(.*)$/)
      // Only real interfaces: a VPN tunnel or a container bridge would count the same traffic twice.
      if (!match || /^(lo|veth|docker|br-|virbr|vnet|tun|tap|wg|tailscale|zt)/.test(match[1].trim())) continue
      var fields = match[2].trim().split(/\s+/).map(Number)
      rx += fields[0] || 0
      tx += fields[8] || 0
    }
    var now = Date.now()
    if (stats.lastNet) {
      var seconds = Math.max(0.5, (now - stats.lastNet.at) / 1000)
      stats.netDown = Math.max(0, (rx - stats.lastNet.rx) / seconds)
      stats.netUp = Math.max(0, (tx - stats.lastNet.tx) / seconds)
      stats.netDownHistory = stats.pushHistory(stats.netDownHistory, stats.netDown)
      stats.netUpHistory = stats.pushHistory(stats.netUpHistory, stats.netUp)
    }
    stats.lastNet = { rx: rx, tx: tx, at: now }
  }

  // --- disks: df ---

  Process {
    id: diskStats
    // timeout: a hung network mount must not keep df (and so the list) stuck for good
    command: ["timeout", "10", "df", "-B1", "--output=source,size,used,avail,target", "-x", "tmpfs", "-x", "devtmpfs",
              "-x", "efivarfs", "-x", "squashfs", "-x", "overlay"]
    stdout: StdioCollector { onStreamFinished: stats.takeDisks(text) }
  }
  Timer {
    interval: 60000
    repeat: true
    running: stats.service.enabled("disk")
    triggeredOnStart: true
    onTriggered: if (!diskStats.running) diskStats.running = true
  }
  // One row per device (btrfs mounts the same one many times: the shortest
  // mount point stands for it); small boot partitions are left out.
  function takeDisks(text) {
    var bySource = {}
    var order = []
    var rows = String(text).split("\n")
    for (var i = 1; i < rows.length; i++) {
      // source size used avail target -- the mount point last, it may hold spaces
      var m = rows[i].trim().match(/^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)$/)
      if (!m || !(Number(m[2]) > 0)) continue
      if (/^\/(boot|efi)/.test(m[5]) && Number(m[2]) < 4e9) continue
      var known = bySource[m[1]]
      if (!known) { order.push(m[1]); bySource[m[1]] = { mount: m[5], size: Number(m[2]), used: Number(m[3]), avail: Number(m[4]) } }
      else if (m[5].length < known.mount.length) known.mount = m[5]
    }
    stats.disks = order.map(function(source) { return bySource[source] })
  }
}
