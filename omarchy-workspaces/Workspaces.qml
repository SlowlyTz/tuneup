import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui

// Tuneup's workspace indicator.
//
// With an external monitor attached, one screen -- laptop or external -- keeps
// its own desktops (shown as 1, 2, ...; a single "1" by default); desktops
// 1-10 live on the other one. Without one, it behaves like the stock widget.
// Each bar highlights the workspace active on *its own* screen, not the
// globally focused one.
//
// The ids come from Tuneup (desktops.json in its runtime folder): with
// Omarchy's workspaces per monitor every screen's desktops are the ids of its
// block (block b: b*10+1 ... b*10+10); with an older Omarchy desktops 1-10
// are workspaces 1-10 and the fixed screen's are 99 and up.
//
// A screen showing a scratch desktop (workspace 201 and up, SUPER + S) shows
// only the scratch desktops -- those that exist (Tuneup keeps the first ones
// while the row is open), numbered as SUPER + 1…0 reach them -- in the accent
// color behind a scratch marker;
// elsewhere they never show.
BarWidget {
  id: root
  moduleName: "hypr-screens.workspaces"

  // The laptop's own panel (hypr_screens/config.py INTERNAL_PREFIXES).
  function isPanel(name) { return /^(eDP|LVDS|DSI)/.test(name) }
  // What Tuneup uses now (hypr_screens/desktops.py save_layout).
  readonly property string runtimeDir: Quickshell.env("XDG_RUNTIME_DIR") || ""
  property var layout: null
  FileView {
    path: root.runtimeDir ? root.runtimeDir + "/tuneup/desktops.json" : ""
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      try { root.layout = JSON.parse(text()) } catch (e) { root.layout = null }
    }
    onLoadFailed: root.layout = null
  }
  readonly property bool omarchy: !!(root.layout && root.layout.omarchy)

  // The fixed screen's desktops: its desktop 1 and the nine ids after it
  // (Tuneup's fixed_desktops option); 99 up to 108 without Omarchy's blocks.
  readonly property int fixedWorkspace: root.layout && root.layout.fixed_first ? root.layout.fixed_first
                                        : (root.omarchy ? -1000 : 99)
  readonly property int fixedLast: root.fixedWorkspace + 9

  // Tuneup's scratch desktops (hypr_screens/scratch.py FIRST), shared by all
  // screens; ids from 9001 are only on their way to another id.
  readonly property int scratchFirst: 201
  readonly property int scratchEnd: 9001

  function isFixed(id) { return id >= root.fixedWorkspace && id <= root.fixedLast }
  function isScratch(id) { return id >= root.scratchFirst && id < root.scratchEnd }

  // This screen's desktop 1: the first id of its block, or 1.
  readonly property int deskFirst: {
    var blocks = root.layout && root.layout.blocks
    var block = blocks ? blocks[root.screenName] : undefined
    return root.omarchy && block !== undefined ? block * 10 + 1 : 1
  }

  // The output this particular bar instance lives on.
  readonly property string screenName: {
    var window = root.QsWindow ? root.QsWindow.window : null
    return window && window.screen ? String(window.screen.name || "") : ""
  }

  readonly property bool docked: {
    var monitors = Hyprland.monitors.values
    for (var i = 0; i < monitors.length; i++) {
      if (monitors[i] && !root.isPanel(String(monitors[i].name || ""))) return true
    }
    return false
  }

  // The fixed screen is whichever one shows one of the fixed desktops.
  readonly property bool pinned: root.docked && root.isFixed(root.activeWorkspace)
                                 && (!root.omarchy || root.layout.fixed_monitor === root.screenName)
  // This screen shows a scratch desktop: the bar shows the scratch row.
  readonly property bool scratch: root.isScratch(root.activeWorkspace)

  readonly property int activeWorkspace: {
    var monitors = Hyprland.monitors.values
    var fallback = 0

    for (var i = 0; i < monitors.length; i++) {
      var monitor = monitors[i]
      if (!monitor || !monitor.activeWorkspace) continue
      if (String(monitor.name || "") === root.screenName) return monitor.activeWorkspace.id
      if (monitor.focused) fallback = monitor.activeWorkspace.id
    }

    return fallback
  }

  function workspaceById(id) {
    var values = Hyprland.workspaces.values
    for (var i = 0; i < values.length; i++) {
      if (values[i].id === id) return values[i]
    }
    return null
  }

  function hasWindows(id) {
    var workspace = root.workspaceById(id)
    return workspace !== null && workspace.toplevels.values.length > 0
  }

  function scratchIds() {
    var ids = []
    var all = Hyprland.workspaces.values
    for (var k = 0; k < all.length; k++) {
      var wid = all[k].id
      if (root.isScratch(wid) && ids.indexOf(wid) === -1) ids.push(wid)
    }
    if (ids.indexOf(root.activeWorkspace) === -1) ids.push(root.activeWorkspace)
    ids.sort(function(left, right) { return left - right })
    return ids
  }

  function workspaceIds() {
    if (root.scratch) return root.scratchIds()
    if (root.pinned) {
      // its desktops that exist (Tuneup keeps them all while there are several)
      var fixed = [root.fixedWorkspace]
      var all = Hyprland.workspaces.values
      for (var k = 0; k < all.length; k++) {
        var wid = all[k].id
        if (root.isFixed(wid) && fixed.indexOf(wid) === -1) fixed.push(wid)
      }
      if (fixed.indexOf(root.activeWorkspace) === -1) fixed.push(root.activeWorkspace)
      fixed.sort(function(left, right) { return left - right })
      return fixed
    }

    var first = root.deskFirst
    var ids = [first, first + 1, first + 2, first + 3, first + 4]
    var values = Hyprland.workspaces.values

    for (var i = 0; i < values.length; i++) {
      var id = values[i].id
      if (id >= first && id < first + 10 && ids.indexOf(id) === -1) ids.push(id)
    }

    ids.sort(function(left, right) { return left - right })
    return ids
  }

  function label(id) {
    if (root.isScratch(id)) {  // as SUPER + 1…0 reach it: 201 is 1, 210 is 0
      var n = id - root.scratchFirst + 1
      return n === 10 ? "0" : String(n)
    }
    if (root.isFixed(id)) return String(id - root.fixedWorkspace + 1)
    var slot = id - root.deskFirst + 1
    return slot === 10 ? "0" : String(slot)
  }

  // Go through Tuneup so desktops stay on the right screen; a scratch desktop
  // comes to the screen whose bar was clicked.
  function focusWorkspace(id) {
    if (!root.bar) return
    if (root.isScratch(id)) {
      root.bar.run("hyprctl dispatch " + Util.shellQuote(
        'hl.dsp.focus({ workspace = "' + id + '", on_current_monitor = true })'))
      return
    }
    if (root.isFixed(id)) {
      root.bar.run("tuneup switch --fixed " + Util.shellQuote(String(id - root.fixedWorkspace + 1)))
      return
    }
    var slot = String(id - root.deskFirst + 1)
    if (root.omarchy && !(root.layout && root.layout.role)) {
      // every screen has its own desktops (Omarchy's): this bar's screen
      root.bar.run("hyprctl dispatch " + Util.shellQuote(
        "o.workspaces.focus(" + slot + ", " + JSON.stringify(root.screenName) + ")"))
      return
    }
    root.bar.run("tuneup switch --desk " + Util.shellQuote(slot))
  }

  readonly property real trailingGap: root.vertical ? 0 : Style.spaceReal(1.5)

  implicitWidth: grid.implicitWidth + trailingGap
  implicitHeight: grid.implicitHeight

  GridLayout {
    id: grid
    anchors.fill: parent
    anchors.rightMargin: root.trailingGap
    columns: root.vertical ? 1 : root.workspaceIds().length + (root.scratch ? 1 : 0)
    columnSpacing: root.vertical ? 0 : Style.space(1)
    rowSpacing: root.vertical ? Style.space(2) : 0

    // The scratch marker: this screen shows the scratch row (SUPER + S leaves it).
    WidgetButton {
      visible: root.scratch
      bar: root.bar
      text: "\uf24d"
      foreground: Color.accent
      pressable: false
      horizontalMargin: 6
      verticalPadding: 6
      fixedWidth: root.vertical ? root.barSize : Style.space(20)
      fixedHeight: root.barSize
      tooltipText: "Scratch desktops"
    }

    Repeater {
      model: root.workspaceIds()

      WidgetButton {
        required property int modelData

        readonly property bool occupied: root.hasWindows(modelData)
        readonly property bool focused: root.activeWorkspace === modelData

        bar: root.bar
        foreground: root.isScratch(modelData) ? Color.accent : (root.bar ? root.bar.barForeground : Color.foreground)
        text: focused ? "󱓻" : root.label(modelData)
        opacity: occupied || focused ? 1 : 0.5
        horizontalMargin: 6
        verticalPadding: 6
        fixedWidth: root.vertical ? root.barSize : Style.space(20)
        fixedHeight: root.barSize
        onPressed: function() { root.focusWorkspace(modelData) }
      }
    }
  }
}
