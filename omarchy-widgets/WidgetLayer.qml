import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Commons
import qs.Ui

// One screen's layer. `group`: "bottom" (behind the windows) or "top"
// (above them), each with "-blur" for widgets with a blurred card (Hyprland
// blurs that layer, see the layer rule in hypr_screens.lua). The edit layer
// holds every widget.
PanelWindow {
  id: panel
  required property var service
  required property var modelData
  property bool editLayer: false
  property string group: "bottom"
  // A part that takes clicks (Now Playing's buttons); clicks go through
  // everywhere else.
  property Item clickable: null
  readonly property var hyprMonitor: Hyprland.monitorFor(modelData)
  readonly property bool fullscreen: !!(hyprMonitor && hyprMonitor.activeWorkspace && hyprMonitor.activeWorkspace.hasFullscreen)
  screen: modelData
  visible: panel.service.anyOn(modelData, editLayer ? "" : group) && (editLayer ? panel.service.editing : (!panel.service.editing && !fullscreen))
           && !remap.remapping
  anchors { top: true; bottom: true; left: true; right: true }
  color: "transparent"
  exclusionMode: ExclusionMode.Ignore
  WlrLayershell.namespace: editLayer ? "hypr-screens-widgets-edit"
                           : "hypr-screens-widgets" + (group === "bottom" ? "" : "-" + group)
  WlrLayershell.layer: editLayer ? WlrLayer.Overlay : (group.indexOf("top") === 0 ? WlrLayer.Top : WlrLayer.Bottom)
  // While arranging, Esc must reach it; otherwise it never takes the keyboard.
  WlrLayershell.keyboardFocus: editLayer ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
  // Clicks go through, except while arranging and on clickable parts.
  mask: editLayer ? allInput : (clickable ? clickRegion : noInput)
  onVisibleChanged: if (visible && editLayer) canvas.forceActiveFocus()
  Region { id: noInput }
  Region { id: allInput; item: canvas }
  Region { id: clickRegion; item: panel.clickable }
  ScreenMoveRemap { id: remap; window: panel }

  Item {
    id: canvas
    anchors.fill: parent
    focus: panel.editLayer
    // Esc closes the style panel first, then cancels; Ctrl+Z takes back a
    // color or look.
    Keys.onEscapePressed: panel.service.selection ? panel.service.selection = null : panel.service.cancelEditing()
    Keys.onReturnPressed: panel.service.saveEditing()
    Keys.onPressed: function(event) {
      if (event.key === Qt.Key_Z && (event.modifiers & Qt.ControlModifier)) {
        panel.service.undoStyle()
        event.accepted = true
      }
    }

    // An empty desktop to arrange on: the wallpaper, over all windows.
    Image {
      anchors.fill: parent
      visible: panel.editLayer
      source: panel.editLayer ? "file://" + panel.service.wallpaper : ""
      fillMode: Image.PreserveAspectCrop
      asynchronous: true
      cache: false
    }
    Rectangle {
      anchors.fill: parent
      visible: panel.editLayer
      color: Qt.rgba(0, 0, 0, 0.15)
    }

    Rectangle {
      id: toolbar
      visible: panel.editLayer
      z: 10
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      anchors.topMargin: Style.space(60)
      radius: Style.space(12)
      color: Qt.rgba(0, 0, 0, 0.7)
      border.color: Color.accent
      border.width: 1
      implicitWidth: bar.implicitWidth + Style.space(24)
      implicitHeight: bar.implicitHeight + Style.space(16)

      Row {
        id: bar
        anchors.centerIn: parent
        spacing: Style.space(16)

        ToolButton {
          family: panel.service.fontFamily
          label: panel.service.texts.move || "Move"
          primary: !panel.service.colorMode
          onClicked: { panel.service.colorMode = false; panel.service.selection = null }
        }
        ToolButton {
          family: panel.service.fontFamily
          label: panel.service.texts.style || "Style"
          primary: panel.service.colorMode
          onClicked: panel.service.colorMode = true
        }
        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: panel.service.saveFailed ? (panel.service.texts.saveFailed || "Could not save – try again or cancel")
                : panel.service.colorMode ? (panel.service.texts.hintStyle || "Click a widget to style it  ·  Ctrl+Z undoes")
                : (panel.service.texts.hint || "Drag the widgets  ·  scroll to turn (Shift: fine)")
          color: panel.service.saveFailed ? Color.urgent : "white"
          font.family: panel.service.fontFamily
          font.pixelSize: Style.font.body
        }
        ToolButton { family: panel.service.fontFamily; label: panel.service.texts.cancel || "Cancel"; onClicked: panel.service.cancelEditing() }
        ToolButton { family: panel.service.fontFamily; label: panel.service.texts.save || "Save"; primary: true; onClicked: panel.service.saveEditing() }
      }
    }

    // The style panel, only on the edit layer and only while arranging.
    Loader {
      z: 20
      active: panel.editLayer && panel.service.editing
      sourceComponent: StylePanel {
        id: stylePanel
        service: panel.service
        screenKey: panel.service.screenId(panel.modelData)
        focusBack: canvas
        visible: panel.service.colorMode && !!panel.service.selection && panel.service.selection.screen === screenKey
        // The room below the toolbar; a taller panel scrolls.
        maxHeight: canvas.height - (toolbar.y + toolbar.height) - Style.space(36)
        // Where it was dragged to, unless it would hide the widget; else
        // beside the widget. Never over the toolbar.
        readonly property var place: {
          var area = { width: canvas.width, height: canvas.height, top: toolbar.y + toolbar.height }
          var rect = panel.service.selection ? panel.service.selection.rect : null
          return panel.service.placePalette(rect, panel.service.palettePlaces[screenKey], width, height, area)
        }
        x: place.x
        y: place.y
        onMoved: function(x, y) {
          var places = Object.assign({}, panel.service.palettePlaces)
          places[screenKey] = { x: x, y: y }
          panel.service.palettePlaces = places
          stylePanel.x = Qt.binding(function() { return stylePanel.place.x })
          stylePanel.y = Qt.binding(function() { return stylePanel.place.y })
        }
      }
    }

    Repeater {
      model: panel.service.kinds
      Placed {
        id: placed
        required property string modelData
        service: panel.service
        kind: modelData
        screenKey: panel.service.screenId(panel.modelData)
        editable: panel.editLayer
        visible: panel.service.shows(kind, panel.modelData, panel.editLayer ? "" : panel.group)
        // Only while it shows: not behind a fullscreen window or while
        // arranging hides this layer (a visualizer then stops cava).
        Loader {
          id: view
          active: placed.visible && panel.visible
          sourceComponent: panel.service.views[placed.kind] || null
        }
        Binding { target: view.item; property: "editing"; value: panel.editLayer; when: view.item !== null }
        Binding { target: view.item; property: "spot"; value: placed.spot; when: view.item !== null }
        Binding {
          target: panel
          property: "clickable"
          value: view.item ? view.item.controls : null
          when: placed.kind === "nowplaying" && placed.visible && !panel.editLayer && view.item !== null
        }
      }
    }
  }

  // A button of the toolbar (an inline component: it cannot see `panel`,
  // so the font comes in as `family`).
  component ToolButton: Rectangle {
    id: button
    property string label: ""
    property string family: ""
    property bool primary: false
    signal clicked()
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    radius: Style.space(8)
    color: primary ? Color.accent : (area.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.08))
    implicitWidth: text.implicitWidth + Style.space(28)
    implicitHeight: text.implicitHeight + Style.space(14)
    Text {
      id: text
      anchors.centerIn: parent
      text: button.label
      color: button.primary ? Color.background : "white"
      font.family: button.family
      font.pixelSize: Style.font.body
      font.bold: true
    }
    MouseArea {
      id: area
      anchors.fill: parent
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onClicked: button.clicked()
    }
  }
}
