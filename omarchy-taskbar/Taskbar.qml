import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui

// The windows of the desktop this screen shows, as icons in the order they sit
// on it (left to right). A window minimized from it (hypr-minimizer keeps which
// desktop that was) stays where it was and turns grey. A click brings a window
// to the front, or minimizes one nothing covers; a middle click closes it.
//
// Icons come and go with their width, so their neighbours slide aside; a
// change of desktop fades the whole row instead of animating every icon.
BarWidget {
  id: root
  moduleName: "hypr-screens.taskbar"

  readonly property string minimizedName: "special:minimized"
  readonly property int tileWidth: Math.round(root.barSize * 1.15)
  readonly property int iconSize: Math.round(root.barSize * 0.62)
  readonly property color ink: root.bar ? root.bar.barForeground : Color.foreground

  readonly property var monitor: {
    var window = root.QsWindow ? root.QsWindow.window : null
    return window && window.screen ? Hyprland.monitorFor(window.screen) : Hyprland.focusedMonitor
  }
  readonly property int here: root.monitor && root.monitor.activeWorkspace ? root.monitor.activeWorkspace.id : 0
  readonly property string focusedAddress: Hyprland.activeToplevel ? root.norm(Hyprland.activeToplevel.address) : ""

  // hypr-minimizer's stacks: desktop id -> the windows minimized from it.
  property var stacks: ({})
  // The window behind each address, for its title.
  property var windows: ({})
  // Each desktop's row as last shown, so a minimized window keeps its place.
  property var orders: ({})
  // A window changed places: the icons glide to their new spots.
  property bool reordering: false

  implicitWidth: row.implicitWidth
  implicitHeight: root.barSize

  function norm(address) { return "0x" + String(address || "").replace(/^0x/, "") }

  function appId(toplevel) {
    if (toplevel.wayland && toplevel.wayland.appId) return String(toplevel.wayland.appId)
    var ipc = toplevel.lastIpcObject
    return ipc && ipc["class"] ? String(ipc["class"]) : ""
  }

  // As the dock finds it: by file name first (web apps are named after their
  // window class), the fuzzy lookup would find the browser that runs them.
  property var iconCache: ({})
  function iconOf(toplevel) {
    var id = root.appId(toplevel)
    if (id in root.iconCache) return root.iconCache[id]
    var entry = id ? (DesktopEntries.byId(id) || DesktopEntries.byId(id.toLowerCase()) || DesktopEntries.heuristicLookup(id)) : null
    var icon = entry ? String(entry.icon || "") : ""
    var path = icon.charAt(0) === "/" ? Util.fileUrl(icon) : (icon ? Quickshell.iconPath(icon, true) : "")
    path = path || Quickshell.iconPath("application-x-executable", true)
    if (id) root.iconCache[id] = path
    return path
  }

  function position(toplevel, axis) {
    var ipc = toplevel.lastIpcObject
    return ipc && ipc.at ? Number(ipc.at[axis]) || 0 : 0
  }

  // What the row shows: the open windows in their order on the screen, the
  // minimized ones where they were; new open ones after the last open one,
  // minimized ones never seen here at the end.
  function collect() {
    var open = [], byAddress = {}, minimized = {}, stacked = {}
    var all = Hyprland.toplevels.values
    for (var i = 0; i < all.length; i++) {
      var toplevel = all[i]
      if (!toplevel.address) continue
      var address = root.norm(toplevel.address)
      byAddress[address] = toplevel
      if (toplevel.workspace && toplevel.workspace.id === root.here && root.here > 0)
        open.push({ address: address, x: root.position(toplevel, 0), y: root.position(toplevel, 1) })
    }
    open.sort(function(a, b) { return a.x - b.x || a.y - b.y || a.address.localeCompare(b.address) })
    root.windows = byAddress

    function hidden(address) {
      var toplevel = byAddress[address]
      return !!toplevel && !!toplevel.workspace && String(toplevel.workspace.name || "") === root.minimizedName
    }
    for (var key in root.stacks) {
      var stack = root.stacks[key] || []
      for (var s = 0; s < stack.length; s++) {
        var stackAddress = root.norm(stack[s])
        stacked[stackAddress] = true
        if (key === String(root.here) && hidden(stackAddress)) minimized[stackAddress] = true
      }
    }

    var previous = root.orders[root.here] || []
    var openSet = {}
    for (var o = 0; o < open.length; o++) openSet[open[o].address] = true
    // Just minimized, its stack not written yet: it stays, grey.
    for (var p = 0; p < previous.length; p++)
      if (!openSet[previous[p]] && !stacked[previous[p]] && hidden(previous[p])) minimized[previous[p]] = true

    var slots = previous.filter(function(a) { return openSet[a] || minimized[a] })
                        .map(function(a) { return minimized[a] ? a : null })
    var next = 0, lastOpen = -1, order = []
    for (var k = 0; k < slots.length; k++) {
      if (slots[k] === null) { order.push(open[next++].address); lastOpen = order.length - 1 }
      else order.push(slots[k])
    }
    var fresh = open.slice(next).map(function(w) { return w.address })
    order.splice.apply(order, [lastOpen + 1, 0].concat(fresh))
    for (var m in minimized) if (order.indexOf(m) === -1) order.push(m)

    var orders = root.orders
    orders[root.here] = order
    root.orders = orders
    return order.map(function(a) { return { address: a, icon: root.iconOf(byAddress[a]), minimized: !!minimized[a] } })
  }

  function indexIn(model, address) {
    for (var i = 0; i < model.count; i++) if (model.get(i).address === address) return i
    return -1
  }

  // The model becomes `wanted`, in its order, touching only what changed so
  // the icons that stay keep their delegates. Gone ones fade out first.
  function sync(model, wanted, animate) {
    var keep = {}
    for (var k = 0; k < wanted.length; k++) keep[wanted[k].address] = true
    for (var i = model.count - 1; i >= 0; i--) {
      var item = model.get(i)
      if (keep[item.address]) continue
      if (!animate) model.remove(i)
      else if (!item.leaving) model.setProperty(i, "leaving", true)
    }
    var pos = 0, moved = false
    for (var j = 0; j < wanted.length; j++) {
      var want = wanted[j]
      while (pos < model.count && model.get(pos).leaving && !keep[model.get(pos).address]) pos++
      var at = root.indexIn(model, want.address)
      if (at === -1) {
        model.insert(pos, { address: want.address, icon: want.icon, minimized: want.minimized, leaving: false, fresh: animate })
        at = pos
      } else {
        if (at !== pos) { model.move(at, pos, 1); at = pos; moved = true }
        var current = model.get(at)
        if (current.leaving) model.setProperty(at, "leaving", false)
        if (current.icon !== want.icon) model.setProperty(at, "icon", want.icon)
        if (current.minimized !== want.minimized) model.setProperty(at, "minimized", want.minimized)
      }
      pos = at + 1
    }
    if (moved && animate) { root.reordering = true; reorderTimer.restart() }
  }

  function rebuild(animate) {
    if (animate && switcher.running) return  // the fade rebuilds when it is dark
    root.sync(tiles, root.collect(), animate)
  }

  function drop(address) {
    var at = root.indexIn(tiles, address)
    if (at !== -1 && tiles.get(at).leaving) tiles.remove(at)
  }

  // A window nothing covers is minimized; any other, grey or hidden behind
  // others, comes to the front. The focus does not matter (hypr-minimizer toggle).
  function activate(address) {
    if (root.here > 0)
      Quickshell.execDetached(["hypr-minimizer", "toggle", address, String(root.here)])
  }

  function closeWindow(address) {
    Quickshell.execDetached(["hyprctl", "dispatch", "hl.dsp.window.close({ window = 'address:" + address + "' })"])
  }

  function titleOf(address) {
    var toplevel = root.windows[address]
    return toplevel ? String(toplevel.title || "") : ""
  }

  ListModel { id: tiles }

  Timer { id: rebuildTimer; interval: 40; onTriggered: root.rebuild(true) }
  // Tiling places a new window a moment after it opened: its spot, read again.
  Timer {
    id: settleTimer
    interval: 350
    onTriggered: { Hyprland.refreshToplevels(); rebuildTimer.restart() }
  }
  Timer { id: reorderTimer; interval: 320; onTriggered: root.reordering = false }

  readonly property var watchedEvents: ["openwindow", "closewindow", "movewindowv2", "activewindowv2",
                                       "changefloatingmode", "fullscreen", "workspacev2", "moveworkspacev2"]
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event || root.watchedEvents.indexOf(String(event.name)) === -1) return
      Hyprland.refreshToplevels()
      rebuildTimer.restart()
      settleTimer.restart()
    }
  }
  Connections {
    target: Hyprland.toplevels
    function onValuesChanged() { rebuildTimer.restart() }
  }

  onStacksChanged: rebuildTimer.restart()
  onHereChanged: switcher.restart()
  Component.onCompleted: { Hyprland.refreshToplevels(); root.rebuild(false) }

  FileView {
    path: Quickshell.env("XDG_RUNTIME_DIR") + "/hypr-minimizer/state.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.readStacks(text())
    onLoadFailed: root.readStacks("")
  }

  function readStacks(raw) {
    var parsed = {}
    try { parsed = raw ? JSON.parse(raw) : {} } catch (error) { parsed = {} }
    var stacks = parsed && parsed.stacks ? parsed.stacks : parsed
    root.stacks = stacks && typeof stacks === "object" ? stacks : {}
  }

  // Another desktop: the row fades out, changes while unseen, and fades in.
  SequentialAnimation {
    id: switcher
    NumberAnimation { target: row; property: "opacity"; to: 0; duration: 90; easing.type: Easing.OutCubic }
    ScriptAction { script: root.rebuild(false) }
    NumberAnimation { target: row; property: "opacity"; to: 1; duration: 200; easing.type: Easing.OutCubic }
  }

  component Tile: Item {
    id: tile
    required property int index
    required property string address
    required property string icon
    required property bool minimized
    required property bool leaving
    required property bool fresh

    readonly property bool focused: !tile.minimized && root.focusedAddress === tile.address
    // The bar shows its tooltip only while this is true.
    readonly property bool tooltipHovered: area.containsMouse
    property real presence: tile.fresh ? 0 : 1
    property real grey: tile.minimized ? 1 : 0
    Behavior on grey { NumberAnimation { duration: 360; easing.type: Easing.OutCubic } }

    width: root.tileWidth * tile.presence
    height: root.barSize

    Behavior on x {
      enabled: root.reordering
      NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }

    Component.onCompleted: if (tile.fresh) appear.start()
    onLeavingChanged: {
      if (tile.leaving) { appear.stop(); vanish.start() }
      else { vanish.stop(); appear.start() }
    }

    NumberAnimation { id: appear; target: tile; property: "presence"; to: 1; duration: 340; easing.type: Easing.OutQuart }
    NumberAnimation {
      id: vanish
      target: tile; property: "presence"; to: 0; duration: 260; easing.type: Easing.InOutCubic
      onFinished: { var address = tile.address; Qt.callLater(function() { root.drop(address) }) }
    }

    Rectangle {
      anchors.centerIn: parent
      width: root.tileWidth - Style.space(4)
      height: root.barSize - Style.space(6)
      radius: Style.space(6)
      color: root.ink
      opacity: area.containsMouse ? 0.1 : 0
      scale: tile.presence
      Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    Item {
      anchors.centerIn: parent
      anchors.verticalCenterOffset: -Style.space(1)
      width: root.iconSize
      height: root.iconSize
      scale: area.pressed ? 0.9 : (area.containsMouse ? 1.08 : 1)
      Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

      Image {
        anchors.fill: parent
        source: tile.icon
        fillMode: Image.PreserveAspectFit
        sourceSize.width: root.iconSize * 1.5 * Screen.devicePixelRatio
        sourceSize.height: root.iconSize * 1.5 * Screen.devicePixelRatio
        asynchronous: true
        smooth: true
        mipmap: true
        opacity: tile.presence * tile.presence * (1 - 0.55 * tile.grey)
        scale: 0.55 + 0.45 * tile.presence
        layer.enabled: tile.grey > 0
        layer.effect: MultiEffect { saturation: -tile.grey }
      }
    }

    // The focused window: a short line that grows out under it.
    Rectangle {
      anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: Style.space(2) }
      height: Math.max(2, Style.space(2))
      radius: height / 2
      width: tile.focused ? Style.space(12) : Style.space(3)
      color: root.ink
      opacity: tile.focused ? 0.9 * tile.presence : 0
      Behavior on width { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
      Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }

    MouseArea {
      id: area
      anchors.fill: parent
      enabled: !tile.leaving
      acceptedButtons: Qt.LeftButton | Qt.MiddleButton
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onEntered: if (root.bar) root.bar.showTooltip(tile, root.titleOf(tile.address))
      onExited: if (root.bar) root.bar.hideTooltip(tile)
      onClicked: function(mouse) {
        if (root.bar) root.bar.hideTooltip(tile)
        if (mouse.button === Qt.MiddleButton) root.closeWindow(tile.address)
        else root.activate(tile.address)
      }
    }
  }

  Row {
    id: row
    anchors.verticalCenter: parent.verticalCenter

    Repeater {
      model: tiles
      delegate: Tile {}
    }
  }
}
