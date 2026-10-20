import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import qs.Commons
import qs.Ui

// Workspace indicator for the fixed screen of hypr-screens.
//
// With an external monitor attached, one screen -- laptop or external, see
// `hypr-screens menu` -- keeps its own desktops (workspace 99 and up, shown as
// 1, 2, ...; a single "1" by default); desktops 1-10 live on the other one. Without one, it behaves like the stock
// widget. Each bar highlights the workspace active on *its own* screen, not the
// globally focused one.
BarWidget {
  id: root
  moduleName: "hypr-screens.workspaces"

  readonly property string panelName: "eDP-1"
  readonly property int fixedWorkspace: 99
  // ids of the fixed screen's desktops: 99 up to 108 (Tuneup's fixed_desktops option)
  readonly property int fixedLast: 108

  function isFixed(id) { return id >= root.fixedWorkspace && id <= root.fixedLast }

  // The output this particular bar instance lives on.
  readonly property string screenName: {
    var window = root.QsWindow ? root.QsWindow.window : null
    return window && window.screen ? String(window.screen.name || "") : ""
  }

  readonly property bool docked: {
    var monitors = Hyprland.monitors.values
    for (var i = 0; i < monitors.length; i++) {
      if (monitors[i] && String(monitors[i].name || "") !== root.panelName) return true
    }
    return false
  }

  // The fixed screen is whichever one shows one of the fixed desktops.
  readonly property bool pinned: root.docked && root.isFixed(root.activeWorkspace)

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

  function workspaceIds() {
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

    var ids = [1, 2, 3, 4, 5]
    var values = Hyprland.workspaces.values

    for (var i = 0; i < values.length; i++) {
      var id = values[i].id
      if (id > 0 && id <= 10 && ids.indexOf(id) === -1) ids.push(id)
    }

    ids.sort(function(left, right) { return left - right })
    return ids
  }

  function label(id) {
    if (root.isFixed(id)) return String(id - root.fixedWorkspace + 1)
    return id === 10 ? "0" : String(id)
  }

  // Go through hypr-screens so desktops stay on the right screen.
  function focusWorkspace(id) {
    if (!root.bar) return
    if (root.isFixed(id)) {
      root.bar.run("hypr-screens switch --fixed " + Util.shellQuote(String(id - root.fixedWorkspace + 1)))
      return
    }
    root.bar.run("hypr-screens switch --desk " + Util.shellQuote(String(id)))
  }

  readonly property real trailingGap: root.vertical ? 0 : Style.spaceReal(1.5)

  implicitWidth: grid.implicitWidth + trailingGap
  implicitHeight: grid.implicitHeight

  GridLayout {
    id: grid
    anchors.fill: parent
    anchors.rightMargin: root.trailingGap
    columns: root.vertical ? 1 : root.workspaceIds().length
    columnSpacing: root.vertical ? 0 : Style.space(1)
    rowSpacing: root.vertical ? Style.space(2) : 0

    Repeater {
      model: root.workspaceIds()

      WidgetButton {
        required property int modelData

        readonly property bool occupied: root.hasWindows(modelData)
        readonly property bool focused: root.activeWorkspace === modelData

        bar: root.bar
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
