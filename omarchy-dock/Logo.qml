import QtQuick
import Quickshell
import qs.Ui

// The Omarchy logo, clicked as before (left: the Omarchy menu, right: a
// terminal); resting on it for a moment fades in the dock of all open windows
// on this screen. The dock stays while the pointer is on the logo or the dock
// and goes a moment after it left both. A full-screen window hides the bar,
// and so the way to the dock.
BarWidget {
  id: root
  moduleName: "hypr-screens.dock"

  readonly property int openDelay: 150
  readonly property int closeDelay: 300

  // Clicked (the menu took over): no dock again until the pointer left the logo.
  property bool spent: false
  readonly property bool logoHovered: hover.hovered

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    fontFamily: "omarchy"
    horizontalMargin: 7.5
    onPressed: function(button) {
      if (!root.bar) return
      if (button === Qt.MiddleButton) return
      root.dismiss()
      if (button === Qt.RightButton) root.bar.run("xdg-terminal-exec")
      else root.bar.run("omarchy-shell shell toggle omarchy.menu '{\"menu\":\"root\"}'")
    }
  }

  HoverHandler { id: hover }

  function dismiss() {
    root.spent = root.logoHovered
    openTimer.stop()
    dock.wanted = false
  }

  onLogoHoveredChanged: {
    if (logoHovered) {
      if (!root.spent && !dock.wanted) openTimer.restart()
      closeTimer.stop()
    } else {
      root.spent = false
      openTimer.stop()
      if (!dock.hovered) closeTimer.restart()
    }
  }

  Timer {
    id: openTimer
    interval: root.openDelay
    onTriggered: if (root.logoHovered && !root.spent) dock.wanted = true
  }
  Timer {
    id: closeTimer
    interval: root.closeDelay
    onTriggered: if (!root.logoHovered && !dock.hovered) dock.wanted = false
  }

  Dock {
    id: dock
    screen: root.QsWindow.window ? root.QsWindow.window.screen : null
    onHoveredChanged: {
      if (dock.hovered) closeTimer.stop()
      else if (!root.logoHovered) closeTimer.restart()
    }
  }
}
