import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.Commons

// The dock itself: one icon per app with open windows, in the order of their
// desktops, the minimized ones (hypr-minimizer) after a line and paler. An app
// with a window on this desktop has a dot beside it; one with several windows
// shows how many and lists them, with their whole titles, as soon as the
// pointer rests on it. Clicking a window brings it onto the desktop this
// screen shows now (`hypr-minimizer fetch`).
//
// Clicking does not close it: it goes only when the pointer leaves it.
//
// The layer stays mapped and only fades: mapping it each time would play
// Hyprland's layer animation instead of the fade. Hidden, it takes no input.
PanelWindow {
  id: dock

  property bool wanted: false
  readonly property bool showing: wanted && dock.groups.length + dock.minimized.length > 0
  readonly property bool hovered: showing && (cardHover.hovered || listHover.hovered || hintHover.hovered)

  // hypr_screens: the external screen's own desktops (shown as 1, 2, ...) and
  // the scratch desktops (201 and up while open, parked as special workspaces while closed).
  readonly property int fixedFirst: 99
  readonly property int fixedLast: 108
  readonly property int scratchFirst: 201
  readonly property string scratchParked: "special:tuneup-scratch-"
  readonly property string minimizedName: "special:minimized"

  readonly property int iconSize: Math.round(Style.font.iconLarge * 1.6)
  readonly property int tileSize: iconSize + Style.space(12)
  readonly property int pad: Style.space(6)
  readonly property int radius: Style.space(14)
  readonly property int gap: Style.space(8)
  readonly property int minListWidth: Style.space(220)
  // Titles are shown whole: the list grows up to the screen's edge and only then wraps.
  readonly property int maxListWidth: {
    var room = dock.screen ? dock.screen.width - Style.gapsOut * 2 - card.width - dock.gap : Style.space(900)
    return Math.max(dock.minListWidth, room)
  }
  readonly property color surface: Qt.rgba(Color.menu.background.r, Color.menu.background.g, Color.menu.background.b, 0.92)
  readonly property color edge: Qt.rgba(Color.menu.text.r, Color.menu.text.g, Color.menu.text.b, 0.08)
  readonly property color lit: Qt.rgba(Color.menu.text.r, Color.menu.text.g, Color.menu.text.b, 0.1)

  // The app whose window list is open, by its key: the last one with several
  // windows the pointer rested on.
  property string openKey: ""
  // The app under the pointer: a lone window shows its title beside it.
  property string hoverKey: ""

  color: "transparent"
  anchors { top: true; left: true }
  margins { top: Style.gapsOut; left: Style.gapsOut }
  // Below the bar (its exclusive zone), over the windows.
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "tuneup-dock"
  WlrLayershell.layer: WlrLayer.Top
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
  implicitWidth: card.width + dock.gap + dock.maxListWidth
  implicitHeight: Math.max(card.height, list.y + list.height, hint.y + hint.height, 1)

  mask: Region {
    item: dock.showing ? card : null
    Region { item: dock.showing && list.visible ? list : null }
    Region { item: dock.showing && hint.visible ? hint : null }
  }

  // Kept a moment after it is no longer wanted, for the fade-out.
  property bool live: false
  Timer {
    id: rest
    interval: 200
    onTriggered: {
      dock.live = false
      dock.frozen = null
    }
  }

  // While it shows, apps and windows keep their places, whatever happens to
  // them; they are sorted anew only the next time it opens. Maps each app's
  // and each window's key to its place; new ones go after these.
  property var frozen: null

  onWantedChanged: {
    if (wanted) {
      rest.stop()
      Hyprland.refreshToplevels()
      if (!dock.frozen) {
        var now = dock.collect(Hyprland.toplevels.values, dock.here, null)
        var places = {}
        now.open.concat(now.hidden).forEach(function(group, i) {
          places[group.key] = i
          group.windows.forEach(function(window, j) { places[window.address] = j })
        })
        dock.frozen = places
      }
      dock.live = true
    } else {
      dock.openKey = ""
      dock.hoverKey = ""
      rest.restart()
    }
  }

  // --- what it shows ---

  readonly property int here: {
    var monitor = dock.screen ? Hyprland.monitorFor(dock.screen) : Hyprland.focusedMonitor
    return monitor && monitor.activeWorkspace ? monitor.activeWorkspace.id : 0
  }

  // Worked out only while it shows (or fades), and again whenever a window comes, goes or moves.
  readonly property var all: dock.live ? dock.collect(Hyprland.toplevels.values, dock.here, dock.frozen) : ({ open: [], hidden: [] })
  readonly property var groups: all.open
  readonly property var minimized: all.hidden

  function appId(toplevel) {
    if (toplevel.wayland && toplevel.wayland.appId) return String(toplevel.wayland.appId)
    var ipc = toplevel.lastIpcObject
    return ipc && ipc["class"] ? String(ipc["class"]) : ""
  }

  // Its desktop entry: by file name first (web apps are named after their
  // window class), the fuzzy lookup would find the browser that runs them.
  function entryFor(id) {
    if (!id) return null
    return DesktopEntries.byId(id) || DesktopEntries.byId(id.toLowerCase()) || DesktopEntries.heuristicLookup(id)
  }

  // The desktop's number as the bar shows it; "" for a special one.
  function label(workspace) {
    var id = workspace ? workspace.id : 0
    var name = workspace ? String(workspace.name || "") : ""
    if (name.indexOf(dock.scratchParked) === 0) return "S" + (Number(name.slice(dock.scratchParked.length)) - dock.scratchFirst + 1)
    if (id >= dock.scratchFirst) return "S" + (id - dock.scratchFirst + 1)
    if (id >= dock.fixedFirst && id <= dock.fixedLast) return String(id - dock.fixedFirst + 1)
    return id > 0 ? String(id) : ""
  }

  function order(workspace) {
    var id = workspace ? workspace.id : 0
    var name = workspace ? String(workspace.name || "") : ""
    if (name.indexOf(dock.scratchParked) === 0) return Number(name.slice(dock.scratchParked.length)) || 100000
    return id > 0 ? id : 100000
  }

  function collect(toplevels, here, frozen) {
    var open = {}, hidden = {}
    for (var i = 0; i < toplevels.length; i++) {
      var toplevel = toplevels[i]
      var workspace = toplevel.workspace
      if (!workspace || !toplevel.address) continue
      var id = dock.appId(toplevel)
      var isHidden = String(workspace.name || "") === dock.minimizedName
      var into = isHidden ? hidden : open
      var key = (isHidden ? "min:" : "") + id.toLowerCase()
      if (!into[key]) {
        var entry = dock.entryFor(id)
        into[key] = { key: key, name: entry && entry.name ? String(entry.name) : (id || String(toplevel.title || "")),
                      icon: dock.iconFor(entry), windows: [], here: false, order: 100000, hidden: isHidden }
      }
      var group = into[key]
      var isHere = !isHidden && workspace.id === here
      group.windows.push({ address: "0x" + String(toplevel.address).replace(/^0x/, ""), title: String(toplevel.title || group.name),
                           desktop: isHidden ? "" : dock.label(workspace), here: isHere, order: dock.order(workspace) })
      group.here = group.here || isHere
      group.order = Math.min(group.order, isHidden ? 0 : dock.order(workspace))
    }
    // Kept places first (frozen), then the natural order: by desktop, then by name.
    function place(key) {
      return frozen && frozen[key] !== undefined ? frozen[key] : 100000
    }
    function sorted(map) {
      var list = Object.keys(map).map(function(k) { return map[k] })
      list.forEach(function(g) {
        g.windows.sort(function(a, b) {
          return place(a.address) - place(b.address) || a.order - b.order || a.title.localeCompare(b.title)
        })
      })
      return list.sort(function(a, b) { return place(a.key) - place(b.key) || a.order - b.order || a.name.localeCompare(b.name) })
    }
    return { open: sorted(open), hidden: sorted(hidden) }
  }

  function iconFor(entry) {
    var icon = entry ? String(entry.icon || "") : ""
    if (icon.charAt(0) === "/") return Util.fileUrl(icon)
    var themed = icon ? Quickshell.iconPath(icon, true) : ""
    return themed || Quickshell.iconPath("application-x-executable", true)
  }

  function groupByKey(key) {
    if (!key) return null
    var every = dock.groups.concat(dock.minimized)
    for (var i = 0; i < every.length; i++) if (every[i].key === key) return every[i]
    return null
  }

  function tileFor(key) {
    var tiles = column.children
    for (var i = 0; i < tiles.length; i++) if (tiles[i].group && tiles[i].group.key === key) return tiles[i]
    return null
  }

  // A window here that nothing covers is minimized; any other comes here, to
  // the front. The focus does not matter (hypr-minimizer toggle).
  function fetch(address) {
    if (dock.here <= 0) return
    Quickshell.execDetached(["hypr-minimizer", "toggle", address, String(dock.here)])
  }

  function clicked(group) {
    if (group.windows.length === 1) dock.fetch(group.windows[0].address)
    else dock.openKey = group.key
  }

  // --- how it looks ---

  component Tile: Item {
    id: tile
    required property var group
    width: dock.tileSize
    height: dock.tileSize
    readonly property bool hot: dock.openKey === tile.group.key || tileArea.containsMouse

    Rectangle {
      anchors.fill: parent
      radius: dock.radius - dock.pad
      color: dock.lit
      opacity: tile.hot ? 1 : 0
      Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    // A window of it on this desktop.
    Rectangle {
      visible: tile.group.here
      width: Style.space(4)
      height: width
      radius: width / 2
      anchors { left: parent.left; leftMargin: -Style.space(4); verticalCenter: parent.verticalCenter }
      color: Color.menu.text
      opacity: 0.85
    }

    Image {
      anchors.centerIn: parent
      width: dock.iconSize
      height: dock.iconSize
      fillMode: Image.PreserveAspectFit
      sourceSize.width: width * 1.2 * Screen.devicePixelRatio
      sourceSize.height: height * 1.2 * Screen.devicePixelRatio
      source: tile.group.icon
      asynchronous: true
      smooth: true
      mipmap: true
      opacity: tile.group.hidden ? 0.45 : 1
      scale: tileArea.pressed ? 0.94 : (tile.hot ? 1.08 : 1)
      Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    }

    // How many windows, when more than one.
    Rectangle {
      visible: tile.group.windows.length > 1
      anchors { bottom: parent.bottom; right: parent.right; margins: Style.space(1) }
      width: Math.max(height, count.implicitWidth + Style.space(8))
      height: count.implicitHeight + Style.space(2)
      radius: height / 2
      color: Color.menu.text
      Text {
        id: count
        anchors.centerIn: parent
        text: tile.group.windows.length
        color: Color.menu.background
        font.family: Style.font.menuFamily
        font.pixelSize: Math.round(Style.font.caption * 0.9)
        font.weight: Font.Bold
      }
    }

    MouseArea {
      id: tileArea
      anchors.fill: parent
      acceptedButtons: Qt.LeftButton
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onContainsMouseChanged: {
        if (containsMouse) {
          dock.hoverKey = tile.group.key
          // Several windows: list them right away. The list stays while the
          // pointer crosses over to it, until it rests on another app.
          dock.openKey = tile.group.windows.length > 1 ? tile.group.key : ""
        } else if (dock.hoverKey === tile.group.key) dock.hoverKey = ""
      }
      onClicked: dock.clicked(tile.group)
    }
  }

  component Surface: Rectangle {
    radius: dock.radius
    color: dock.surface
    border.width: 1
    border.color: dock.edge
    opacity: card.opacity
  }

  Surface {
    id: card
    width: column.width + dock.pad * 2
    height: column.height + dock.pad * 2
    opacity: dock.showing ? 1 : 0
    x: dock.showing ? 0 : -Style.space(10)
    Behavior on opacity { NumberAnimation { duration: dock.showing ? 160 : 120; easing.type: Easing.OutCubic } }
    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    HoverHandler { id: cardHover }

    Column {
      id: column
      x: dock.pad
      y: dock.pad
      spacing: Style.space(2)

      Repeater {
        model: dock.groups
        delegate: Tile { required property var modelData; group: modelData }
      }

      Item {
        visible: dock.groups.length > 0 && dock.minimized.length > 0
        width: dock.tileSize
        height: Style.space(9)
        Rectangle {
          anchors.centerIn: parent
          width: parent.width - Style.space(12)
          height: 1
          color: dock.edge
        }
      }

      Repeater {
        model: dock.minimized
        delegate: Tile { required property var modelData; group: modelData }
      }
    }
  }

  // The title of the lone window under the pointer, and where it is.
  readonly property var hintGroup: dock.openKey ? null : dock.groupByKey(dock.hoverKey)
  readonly property Item hintTile: dock.hintGroup ? dock.tileFor(dock.hintGroup.key) : null

  Surface {
    id: hint
    visible: dock.showing && dock.hintTile !== null
    x: card.x + card.width + dock.gap
    y: dock.hintTile ? Math.max(0, card.y + column.y + dock.hintTile.y + (dock.hintTile.height - height) / 2) : 0
    width: Math.min(dock.maxListWidth, hintText.implicitWidth + Style.space(24))
    height: hintText.height + Style.space(14)
    radius: Math.min(height / 2, dock.radius)

    HoverHandler { id: hintHover }

    Text {
      id: hintText
      anchors.centerIn: parent
      width: Math.min(implicitWidth, dock.maxListWidth - Style.space(24))
      text: {
        var group = dock.hintGroup
        if (!group) return ""
        var lone = group.windows[0]
        if (group.windows.length > 1) return group.name
        return lone.desktop && !lone.here ? lone.title + "  ·  " + lone.desktop : lone.title
      }
      textFormat: Text.PlainText
      wrapMode: Text.WrapAtWordBoundaryOrAnywhere
      color: Color.menu.text
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.body
    }
  }

  // The windows of the app under the pointer (or clicked).
  readonly property var listGroup: dock.groupByKey(dock.openKey)
  readonly property Item listTile: dock.listGroup ? dock.tileFor(dock.listGroup.key) : null

  Surface {
    id: list
    visible: dock.showing && dock.listTile !== null
    x: card.x + card.width + dock.gap
    y: dock.listTile ? Math.max(0, card.y + column.y + dock.listTile.y + (dock.listTile.height - height) / 2) : 0
    width: Math.min(dock.maxListWidth, Math.max(dock.minListWidth, measure.width + dock.pad * 2))
    height: rows.height + dock.pad * 2

    HoverHandler { id: listHover }

    // The widest row as it would be unwrapped: title, desktop and their margins.
    Column {
      id: measure
      visible: false
      Repeater {
        model: dock.listGroup ? dock.listGroup.windows : []
        delegate: Item {
          required property var modelData
          implicitWidth: Style.space(16) + measureTitle.implicitWidth + Style.space(10) + measureDesk.implicitWidth + Style.space(10)
          implicitHeight: 1
          Text {
            id: measureTitle
            text: parent.modelData.title
            textFormat: Text.PlainText
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
          Text {
            id: measureDesk
            text: parent.modelData.desktop
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.caption
          }
        }
      }
    }

    Column {
      id: rows
      x: dock.pad
      y: dock.pad
      width: list.width - dock.pad * 2
      spacing: Style.space(2)

      Repeater {
        model: dock.listGroup ? dock.listGroup.windows : []
        delegate: Rectangle {
          id: row
          required property var modelData
          width: rows.width
          height: rowText.implicitHeight + Style.space(16)
          radius: dock.radius - dock.pad
          color: rowArea.containsMouse ? dock.lit : "transparent"

          Rectangle {
            visible: row.modelData.here
            width: Style.space(4)
            height: width
            radius: width / 2
            anchors { left: parent.left; leftMargin: Style.space(6); verticalCenter: parent.verticalCenter }
            color: Color.menu.text
            opacity: 0.85
          }
          Text {
            id: rowText
            anchors { left: parent.left; leftMargin: Style.space(16); right: desk.left; rightMargin: Style.space(10); verticalCenter: parent.verticalCenter }
            text: row.modelData.title
            textFormat: Text.PlainText
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            color: Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
          Text {
            id: desk
            anchors { right: parent.right; rightMargin: Style.space(10); verticalCenter: parent.verticalCenter }
            text: row.modelData.desktop
            color: Color.menu.text
            opacity: 0.5
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.caption
          }
          MouseArea {
            id: rowArea
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: dock.fetch(row.modelData.address)
          }
        }
      }
    }
  }
}
