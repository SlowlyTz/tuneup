import QtQuick
import qs.Commons
import "ColorTools.js" as ColorTools

// The arrange tool's style panel for the widget picked in the style mode, in
// folds (one open at a time):
// - Colors: the base color (every part on "accent" follows it) from the
//   theme's colors, the wallpaper's, the ones used last or an own one, color
//   schemes made from it, and with "Fine-tuning" the single parts.
// - Font (widgets with text): the family (the installed ones, searchable),
//   the weight and the letter spacing; for the lyrics also the alignment, the
//   size of the line being sung and the scroll time.
// - Effect: none, an outline on the text, a shadow or a glow, its strength,
//   and the widget's opacity.
// - Card: the card behind the widget, its opacity, corners, room around and
//   the blur behind it.
// A choice under the pointer shows on the widget at once (the service's
// preview); a click or a slider takes it into the draft, Ctrl+Z or ↶ takes it
// back, and the toolbar's Save keeps it. It sits beside the widget
// (Service.placePalette) and can be dragged by its title.
Rectangle {
  id: picker

  property var service: null
  property string screenKey: ""
  // The room it has; taller content scrolls.
  property real maxHeight: 100000
  // Where the keyboard goes back to after typing in the font search.
  property Item focusBack: null
  // Dragged by its title to (x, y).
  signal moved(real x, real y)

  readonly property var selection: service ? service.selection : null
  readonly property string kind: selection ? selection.kind : ""
  // "base": the whole widget, else one part.
  readonly property string part: selection ? selection.part : "base"
  readonly property bool whole: part === "base"
  readonly property var titles: service && service.partTitles && service.partTitles[kind] ? service.partTitles[kind] : ({})
  readonly property var texts: service && service.texts ? service.texts : ({})
  readonly property var words: texts.look || ({})
  readonly property var colors: service && kind ? (service.placement(kind).colors || {}) : ({})
  readonly property string value: colors[part] || ""
  readonly property color shown: !service || !kind ? "white"
                                 : whole ? service.tint(kind) : service.colorOf(kind, part, Color.foreground)
  readonly property real unit: Style.space(1)
  readonly property real pad: Math.round(12 * unit)
  property bool ownOpen: false
  property bool appliedAll: false

  // The widget as arranged (without the preview): its look settings.
  readonly property var spot: service && kind && service.draft[kind] ? service.draft[kind] : ({})
  readonly property var lookKeys: service && kind && service.lookKeys[kind] ? service.lookKeys[kind] : []
  function has(key) { return picker.lookKeys.indexOf(key) >= 0 }
  readonly property bool hasText: has("font_family")
  // The open fold: "color", "font", "effect", "card" or "" (all closed).
  readonly property string section: {
    var s = service ? service.styleSection : "color"
    return s === "font" && !hasText ? "" : s
  }
  function toggle(name) { picker.service.styleSection = picker.section === name ? "" : name }
  onSectionChanged: if (section === "font" && service) service.loadFonts()

  // The own color being picked.
  property real hue: 0
  property real sat: 0
  property real val: 1
  property real alpha: 1
  property bool syncing: false

  width: Math.round(340 * unit)
  height: Math.min(maxHeight, header.height + body.contentHeight + 2 * pad + Math.round(10 * unit))
  radius: Math.round(12 * unit)
  color: Qt.rgba(0.08, 0.08, 0.1, 0.97)
  border.color: Color.accent
  border.width: 1

  // Take the target's color into the own-color fields when the target changes.
  onPartChanged: Qt.callLater(takeShown)
  onKindChanged: { Qt.callLater(takeShown); picker.appliedAll = false; body.contentY = 0 }
  Component.onCompleted: {
    takeShown()
    if (section === "font" && service) service.loadFonts()
  }
  onVisibleChanged: {
    if (visible && service && !service.wallpaperColors.length) sampler.sample()
    if (!visible && search.activeFocus) picker.typed()
  }
  function takeShown() {
    picker.syncing = true
    var c = picker.shown
    picker.hue = c.hsvHue < 0 ? picker.hue : c.hsvHue
    picker.sat = c.hsvSaturation
    picker.val = c.hsvValue
    picker.alpha = c.a
    picker.syncing = false
  }
  function hexOf(c) { return ColorTools.hex({ r: c.r, g: c.g, b: c.b, a: c.a }) }

  // The target's colors with `value` in it ("" = its default).
  function withValue(value) {
    var next = Object.assign({}, picker.colors)
    if (value) next[picker.part] = value
    else delete next[picker.part]
    return next
  }
  function hover(value) { if (picker.kind) picker.service.preview = { kind: picker.kind, colors: picker.withValue(value) } }
  function hoverColors(colors) { if (picker.kind) picker.service.preview = { kind: picker.kind, colors: colors } }
  function hoverLook(key, value) { if (picker.kind) picker.service.previewLook(picker.kind, key, value) }
  function unhover() { if (picker.service) picker.service.preview = null }
  // step: a new step for undo; keep: among the colors used last.
  function pick(value, step, keep) {
    if (!picker.service || !picker.kind) return
    picker.service.preview = null
    picker.service.setPartColor(picker.kind, picker.part, value, step !== false, !!keep)
  }
  function pickOwn(step, keep) {
    if (picker.syncing) return
    picker.pick(picker.hexOf(Qt.hsva(picker.hue, picker.sat, picker.val, picker.alpha)), step, keep)
  }
  function setLook(key, value, step) { if (picker.kind) picker.service.setLook(picker.kind, key, value, step) }
  // Three colors that show what a scheme does: main, text and the quieter parts.
  function schemeDots(id) {
    var s = picker.service
    var c = s.schemeColors(picker.kind, id)
    var main = c.base ? s.colorValue(picker.kind, c.base) : id === "theme" ? s.themeColor("accent") : s.tint(picker.kind)
    var defaults = s.parts[picker.kind] || {}
    var text = null, quiet = null
    for (var p in defaults) {
      var r = ColorTools.role(defaults[p])
      var v = c[p] || defaults[p]
      var look = v === "accent" ? main : s.colorValue(picker.kind, v)
      if (r === "text" && text === null) text = look
      if (r === "quiet" && quiet === null) quiet = look
    }
    return [main, text || main, quiet || text || main]
  }
  function setFineTune(on) {
    picker.service.fineTune = on
    var sel = picker.selection
    picker.service.selection = Object.assign({}, sel, { part: on && sel.clicked ? sel.clicked : "base" })
  }

  // The font list: the Omarchy font first, then the installed families whose
  // name has what was typed.
  readonly property var fontChoices: {
    var query = search.text.trim().toLowerCase()
    var all = picker.service ? picker.service.fontFamilies : []
    var out = query ? [] : [""]
    for (var i = 0; i < all.length; i++) {
      if (!query || all[i].toLowerCase().indexOf(query) >= 0) out.push(all[i])
    }
    var own = picker.spot.font_family || ""
    if (!query && own && all.indexOf(own) < 0) out.splice(1, 0, own)
    return out
  }
  // Typing done: the keyboard back to the arrange tool (Esc, Return, Save).
  function typed() { if (picker.focusBack) picker.focusBack.forceActiveFocus() }
  function showChosenFont() {
    var at = picker.fontChoices.indexOf(picker.spot.font_family || "")
    if (at >= 0) fontView.positionViewAtIndex(at, ListView.Center)
  }

  // Swallow clicks, so they do not reach the widgets underneath.
  MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onWheel: function(w) { w.accepted = true } }

  // The wallpaper, small, to find its main colors.
  Canvas {
    id: sampler
    width: 64
    height: 36
    opacity: 0
    enabled: false
    readonly property string source: picker.service ? "file://" + picker.service.wallpaper : ""
    function sample() {
      if (!source) return
      unloadImage(source)
      loadImage(source)
    }
    onImageLoaded: requestPaint()
    onPaint: {
      if (!isImageLoaded(source)) return
      var ctx = getContext("2d")
      ctx.drawImage(source, 0, 0, width, height)
      var data = ctx.getImageData(0, 0, width, height).data
      var pixels = []
      for (var i = 0; i < data.length; i++) pixels.push(data[i])
      picker.service.wallpaperColors = ColorTools.mainColors(pixels, 7)
    }
  }

  component Label: Text {
    color: "white"
    font.family: picker.service ? picker.service.fontFamily : ""
    font.pixelSize: Style.font.bodySmall
  }
  component Caption: Label {
    color: Qt.rgba(1, 1, 1, 0.6)
    font.pixelSize: Style.font.bodySmall * 0.92
  }
  component Swatch: Rectangle {
    id: swatch
    property string value: ""
    property color fill: "transparent"
    property bool chosen: false
    width: Math.round(24 * picker.unit)
    height: width
    radius: width / 2
    color: fill
    border.width: chosen ? 3 : 1
    border.color: chosen ? "white" : Qt.rgba(1, 1, 1, 0.35)
    scale: swatchArea.containsMouse ? 1.15 : 1
    Behavior on scale { NumberAnimation { duration: 90 } }
    MouseArea {
      id: swatchArea
      anchors.fill: parent
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onEntered: picker.hover(swatch.value)
      onExited: picker.unhover()
      onClicked: { picker.pick(swatch.value, true, swatch.value.charAt(0) === "#"); picker.takeShown() }
    }
  }
  component Chip: Rectangle {
    id: chip
    property string label: ""
    property bool current: false
    property bool marked: false
    signal clicked()
    radius: height / 2
    color: current ? Color.accent : Qt.rgba(1, 1, 1, chipArea.containsMouse ? 0.16 : 0.08)
    implicitWidth: chipText.implicitWidth + Math.round(16 * picker.unit)
    implicitHeight: chipText.implicitHeight + Math.round(8 * picker.unit)
    Label {
      id: chipText
      anchors.centerIn: parent
      text: chip.label + (chip.marked ? " •" : "")
      color: chip.current ? Color.background : "white"
    }
    MouseArea { id: chipArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: chip.clicked() }
  }
  component Button: Rectangle {
    id: button
    property string label: ""
    signal clicked()
    radius: Math.round(6 * picker.unit)
    color: Qt.rgba(1, 1, 1, buttonArea.containsMouse && enabled ? 0.16 : 0.08)
    opacity: enabled ? 1 : 0.4
    implicitWidth: buttonText.implicitWidth + Math.round(20 * picker.unit)
    implicitHeight: buttonText.implicitHeight + Math.round(10 * picker.unit)
    Label { id: buttonText; anchors.centerIn: parent; text: button.label }
    MouseArea { id: buttonArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: button.clicked() }
  }
  // A fold inside a section (the own color, fine-tuning).
  component Fold: Item {
    id: fold
    property string label: ""
    property bool open: false
    signal toggled()
    width: parent ? parent.width : 0
    height: foldText.implicitHeight + Math.round(4 * picker.unit)
    Label {
      id: foldText
      anchors.verticalCenter: parent.verticalCenter
      text: (fold.open ? "▾  " : "▸  ") + fold.label
      font.bold: true
      opacity: foldArea.containsMouse ? 1 : 0.85
    }
    MouseArea { id: foldArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: fold.toggled() }
  }
  // A section's title: a line above it, the name and, on the right, what is
  // set now.
  component SectionTitle: Item {
    id: title
    property string name: ""
    property string label: ""
    property string summary: ""
    property color dot: "transparent"
    readonly property bool open: picker.section === name
    width: parent ? parent.width : 0
    height: titleText.implicitHeight + Math.round(16 * picker.unit)
    Rectangle { width: parent.width; height: 1; color: Qt.rgba(1, 1, 1, 0.1) }
    Label {
      id: titleText
      anchors.verticalCenter: parent.verticalCenter
      anchors.verticalCenterOffset: Math.round(2 * picker.unit)
      text: (title.open ? "▾  " : "▸  ") + title.label
      font.pixelSize: Style.font.body
      font.bold: true
      opacity: titleArea.containsMouse || title.open ? 1 : 0.85
    }
    Row {
      anchors.right: parent.right
      anchors.verticalCenter: titleText.verticalCenter
      spacing: Math.round(6 * picker.unit)
      Caption {
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(implicitWidth, title.width - titleText.implicitWidth - Math.round(40 * picker.unit))
        elide: Text.ElideRight
        text: title.summary
      }
      Rectangle {
        visible: title.dot.a > 0
        anchors.verticalCenter: parent.verticalCenter
        width: Math.round(12 * picker.unit)
        height: width
        radius: width / 2
        color: title.dot
        border.color: Qt.rgba(1, 1, 1, 0.35)
      }
    }
    MouseArea { id: titleArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: picker.toggle(title.name) }
  }
  // One of a few choices side by side; the one under the pointer shows on
  // the widget.
  component Segmented: Row {
    id: seg
    property string key: ""
    property var options: []
    property var labels: ({})
    property string current: ""
    width: parent ? parent.width : 0
    spacing: Math.round(3 * picker.unit)
    Repeater {
      model: seg.options
      Rectangle {
        id: segment
        required property string modelData
        readonly property bool chosen: modelData === seg.current
        width: (seg.width - (seg.options.length - 1) * seg.spacing) / Math.max(1, seg.options.length)
        height: segText.implicitHeight + Math.round(10 * picker.unit)
        radius: Math.round(6 * picker.unit)
        color: chosen ? Color.accent : Qt.rgba(1, 1, 1, segArea.containsMouse ? 0.16 : 0.08)
        Label {
          id: segText
          anchors.centerIn: parent
          width: parent.width - Math.round(6 * picker.unit)
          horizontalAlignment: Text.AlignHCenter
          // A long word ("Sehr fett") gets a little smaller rather than cut.
          fontSizeMode: Text.HorizontalFit
          minimumPixelSize: Math.round(Style.font.bodySmall * 0.75)
          elide: Text.ElideRight
          text: seg.labels[segment.modelData] || segment.modelData
          color: segment.chosen ? Color.background : "white"
          font.bold: segment.chosen
        }
        MouseArea {
          id: segArea
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onEntered: picker.hoverLook(seg.key, segment.modelData)
          onExited: picker.unhover()
          onClicked: picker.setLook(seg.key, segment.modelData, true)
        }
      }
    }
  }
  // A number in its range (service.lookRanges), with its value on the right.
  // Pressing starts a step for undo; dragging shows it on the widget at once.
  component LookSlider: Column {
    id: slider
    property string key: ""
    property string label: ""
    property string suffix: ""
    property real step: 1
    readonly property var range: picker.service && picker.service.lookRanges[key] ? picker.service.lookRanges[key] : [0, 100]
    readonly property real value: picker.spot[key] !== undefined ? Number(picker.spot[key]) : range[0]
    property bool fresh: false
    width: parent ? parent.width : 0
    spacing: Math.round(2 * picker.unit)
    opacity: enabled ? 1 : 0.4
    Item {
      width: parent.width
      height: sliderName.implicitHeight
      Label { id: sliderName; text: slider.label }
      Caption { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: Math.round(slider.value) + slider.suffix }
    }
    Item {
      id: track
      width: parent.width
      height: Math.round(18 * picker.unit)
      readonly property real share: (slider.value - slider.range[0]) / Math.max(1, slider.range[1] - slider.range[0])
      Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: Math.round(4 * picker.unit)
        radius: height / 2
        color: Qt.rgba(1, 1, 1, 0.15)
        Rectangle {
          width: handle.x + handle.width / 2
          height: parent.height
          radius: parent.radius
          color: Color.accent
        }
      }
      Rectangle {
        id: handle
        anchors.verticalCenter: parent.verticalCenter
        x: Math.max(0, Math.min(1, track.share)) * (track.width - width)
        width: Math.round(14 * picker.unit)
        height: width
        radius: width / 2
        color: sliderArea.pressed || sliderArea.containsMouse ? "white" : Qt.rgba(0.92, 0.92, 0.95, 1)
        border.color: Color.accent
        border.width: 2
      }
      MouseArea {
        id: sliderArea
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        enabled: slider.enabled
        cursorShape: Qt.PointingHandCursor
        function take(mouse) {
          var share = Math.max(0, Math.min(1, (mouse.x - handle.width / 2) / Math.max(1, track.width - handle.width)))
          var next = slider.range[0] + share * (slider.range[1] - slider.range[0])
          next = Math.max(slider.range[0], Math.min(slider.range[1], Math.round(next / slider.step) * slider.step))
          if (next === slider.value) return
          picker.setLook(slider.key, next, slider.fresh)
          slider.fresh = false
        }
        onPressed: function(mouse) { slider.fresh = true; take(mouse) }
        onPositionChanged: function(mouse) { if (pressed) take(mouse) }
      }
    }
  }
  // On or off.
  component Toggle: Item {
    id: toggle
    property string key: ""
    property string label: ""
    readonly property bool on: !!picker.spot[key]
    width: parent ? parent.width : 0
    height: Math.max(toggleText.implicitHeight, knob.height)
    opacity: enabled ? 1 : 0.4
    Label {
      id: toggleText
      anchors.verticalCenter: parent.verticalCenter
      width: parent.width - knob.width - Math.round(10 * picker.unit)
      wrapMode: Text.WordWrap
      text: toggle.label
    }
    Rectangle {
      id: knob
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      width: Math.round(34 * picker.unit)
      height: Math.round(20 * picker.unit)
      radius: height / 2
      color: toggle.on ? Color.accent : Qt.rgba(1, 1, 1, toggleArea.containsMouse ? 0.22 : 0.15)
      Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        x: toggle.on ? parent.width - width - 2 : 2
        width: parent.height - 4
        height: width
        radius: width / 2
        color: "white"
        Behavior on x { NumberAnimation { duration: 120 } }
      }
    }
    MouseArea {
      id: toggleArea
      anchors.fill: parent
      hoverEnabled: true
      enabled: toggle.enabled
      cursorShape: Qt.PointingHandCursor
      onClicked: picker.setLook(toggle.key, !toggle.on, true)
    }
  }

  // The title: drag it to move the panel.
  Item {
    id: header
    x: picker.pad
    y: picker.pad
    width: picker.width - 2 * picker.pad
    height: heading.implicitHeight + Math.round(4 * picker.unit)
    HoverHandler { cursorShape: Qt.SizeAllCursor }
    DragHandler {
      target: picker
      onActiveChanged: if (!active) picker.moved(picker.x, picker.y)
    }
    Label {
      id: heading
      anchors.verticalCenter: parent.verticalCenter
      text: "⠿  " + (picker.texts[picker.kind] || picker.kind)
            + (picker.section === "color" ? "  ·  " + (picker.whole ? (picker.texts.baseColor || "Base color")
                                                                     : (picker.titles[picker.part] || picker.part)) : "")
      font.bold: true
      width: parent.width - undo.width - close.width - Math.round(24 * picker.unit)
      elide: Text.ElideRight
    }
    Label {
      id: undo
      anchors.right: close.left
      anchors.rightMargin: Math.round(14 * picker.unit)
      anchors.verticalCenter: parent.verticalCenter
      text: "↶"
      font.pixelSize: Style.font.body
      opacity: picker.service && picker.service.styleHistory.length ? 1 : 0.3
      MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor
                  onClicked: { picker.service.undoStyle(); picker.takeShown() } }
    }
    Label {
      id: close
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      text: "✕"
      MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor
                  onClicked: { picker.unhover(); picker.service.selection = null } }
    }
  }

  Flickable {
    id: body
    x: picker.pad
    y: header.y + header.height + Math.round(10 * picker.unit)
    width: picker.width - 2 * picker.pad
    height: picker.height - y - picker.pad
    contentWidth: width
    contentHeight: sections.implicitHeight
    clip: contentHeight > height
    interactive: contentHeight > height
    boundsBehavior: Flickable.StopAtBounds

    Column {
      id: sections
      width: body.width
      spacing: 0

      // --- colors ---------------------------------------------------------------------

      SectionTitle {
        name: "color"
        label: picker.texts.colors || "Colors"
        dot: picker.service && picker.kind ? picker.service.tint(picker.kind) : "transparent"
      }
      Column {
        visible: picker.section === "color"
        width: parent.width
        spacing: Math.round(10 * picker.unit)
        bottomPadding: Math.round(12 * picker.unit)

        // The theme's colors (for a part also the base color, "accent").
        Caption { text: picker.texts.themeColors || "Theme" }
        Flow {
          width: parent.width
          spacing: Math.round(6 * picker.unit)
          Repeater {
            model: (picker.whole ? [] : ["accent"]).concat(["theme:accent", "theme:foreground", "theme:muted", "theme:background",
                    "theme:red", "theme:orange", "theme:yellow", "theme:green", "theme:cyan", "theme:blue", "theme:magenta"])
            Swatch {
              required property string modelData
              value: modelData
              fill: picker.service && picker.kind ? picker.service.colorValue(picker.kind, modelData) : "transparent"
              chosen: picker.value === modelData
            }
          }
        }

        // The wallpaper's colors, and the own ones used last.
        Caption { visible: wallpaperRow.count > 0; text: picker.texts.wallpaper || "Wallpaper" }
        Flow {
          visible: wallpaperRow.count > 0
          width: parent.width
          spacing: Math.round(6 * picker.unit)
          Repeater {
            id: wallpaperRow
            model: picker.service ? picker.service.wallpaperColors : []
            Swatch {
              required property string modelData
              value: modelData
              fill: picker.service ? picker.service.hexColor(modelData) : "transparent"
              chosen: picker.value === modelData
            }
          }
        }
        Caption { visible: recentRow.count > 0; text: picker.texts.recent || "Recent" }
        Flow {
          visible: recentRow.count > 0
          width: parent.width
          spacing: Math.round(6 * picker.unit)
          Repeater {
            id: recentRow
            model: picker.service ? picker.service.recentColors : []
            Swatch {
              required property string modelData
              value: modelData
              fill: picker.service ? picker.service.hexColor(modelData) : "transparent"
              chosen: picker.value === modelData
            }
          }
        }

        // An own color: saturation (across) and brightness (down) for the hue,
        // the hue, the opacity and #rrggbb[aa].
        Fold {
          label: picker.texts.ownColor || "Own color"
          open: picker.ownOpen
          onToggled: picker.ownOpen = !picker.ownOpen
        }
        Column {
          visible: picker.ownOpen
          width: parent.width
          spacing: Math.round(10 * picker.unit)

          Rectangle {
            id: field
            width: parent.width
            height: Math.round(110 * picker.unit)
            radius: Math.round(6 * picker.unit)
            color: Qt.hsva(picker.hue, 1, 1, 1)
            Rectangle {
              anchors.fill: parent
              radius: parent.radius
              gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "white" }
                GradientStop { position: 1; color: "transparent" }
              }
            }
            Rectangle {
              anchors.fill: parent
              radius: parent.radius
              gradient: Gradient {
                GradientStop { position: 0; color: "transparent" }
                GradientStop { position: 1; color: "black" }
              }
            }
            Rectangle {
              x: picker.sat * field.width - width / 2
              y: (1 - picker.val) * field.height - height / 2
              width: Math.round(14 * picker.unit)
              height: width
              radius: width / 2
              color: "transparent"
              border.color: "white"
              border.width: 2
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.CrossCursor
              preventStealing: true
              function take(mouse, step) {
                picker.sat = Math.max(0, Math.min(1, mouse.x / width))
                picker.val = Math.max(0, Math.min(1, 1 - mouse.y / height))
                picker.pickOwn(step, false)
              }
              onPressed: function(mouse) { take(mouse, true) }
              onPositionChanged: function(mouse) { if (pressed) take(mouse, false) }
              onReleased: picker.pickOwn(false, true)
            }
          }

          // The hue.
          Rectangle {
            width: parent.width
            height: Math.round(14 * picker.unit)
            radius: height / 2
            gradient: Gradient {
              orientation: Gradient.Horizontal
              GradientStop { position: 0.0; color: Qt.hsva(0.0, 1, 1, 1) }
              GradientStop { position: 0.17; color: Qt.hsva(0.17, 1, 1, 1) }
              GradientStop { position: 0.33; color: Qt.hsva(0.33, 1, 1, 1) }
              GradientStop { position: 0.5; color: Qt.hsva(0.5, 1, 1, 1) }
              GradientStop { position: 0.67; color: Qt.hsva(0.67, 1, 1, 1) }
              GradientStop { position: 0.83; color: Qt.hsva(0.83, 1, 1, 1) }
              GradientStop { position: 1.0; color: Qt.hsva(0.999, 1, 1, 1) }
            }
            Rectangle {
              x: picker.hue * parent.width - width / 2
              anchors.verticalCenter: parent.verticalCenter
              width: Math.round(6 * picker.unit)
              height: parent.height + 4
              radius: 3
              color: "white"
            }
            MouseArea {
              anchors.fill: parent
              anchors.margins: -4
              preventStealing: true
              function take(mouse, step) {
                picker.hue = Math.max(0, Math.min(0.999, (mouse.x - 4) / (width - 8)))
                picker.pickOwn(step, false)
              }
              onPressed: function(mouse) { take(mouse, true) }
              onPositionChanged: function(mouse) { if (pressed) take(mouse, false) }
              onReleased: picker.pickOwn(false, true)
            }
          }

          // The opacity.
          Rectangle {
            width: parent.width
            height: Math.round(14 * picker.unit)
            radius: height / 2
            gradient: Gradient {
              orientation: Gradient.Horizontal
              GradientStop { position: 0; color: Qt.hsva(picker.hue, picker.sat, picker.val, 0) }
              GradientStop { position: 1; color: Qt.hsva(picker.hue, picker.sat, picker.val, 1) }
            }
            border.color: Qt.rgba(1, 1, 1, 0.3)
            Rectangle {
              x: picker.alpha * parent.width - width / 2
              anchors.verticalCenter: parent.verticalCenter
              width: Math.round(6 * picker.unit)
              height: parent.height + 4
              radius: 3
              color: "white"
            }
            MouseArea {
              anchors.fill: parent
              anchors.margins: -4
              preventStealing: true
              function take(mouse, step) {
                picker.alpha = Math.max(0, Math.min(1, (mouse.x - 4) / (width - 8)))
                picker.pickOwn(step, false)
              }
              onPressed: function(mouse) { take(mouse, true) }
              onPositionChanged: function(mouse) { if (pressed) take(mouse, false) }
              onReleased: picker.pickOwn(false, true)
            }
          }

          Rectangle {
            width: Math.round(120 * picker.unit)
            height: hex.implicitHeight + Math.round(10 * picker.unit)
            radius: Math.round(6 * picker.unit)
            color: Qt.rgba(1, 1, 1, 0.08)
            border.color: hex.activeFocus ? Color.accent : Qt.rgba(1, 1, 1, 0.25)
            TextInput {
              id: hex
              anchors.fill: parent
              anchors.margins: Math.round(5 * picker.unit)
              verticalAlignment: TextInput.AlignVCenter
              color: "white"
              font.family: picker.service ? picker.service.fontFamily : ""
              font.pixelSize: Style.font.bodySmall
              selectByMouse: true
              text: picker.hexOf(picker.shown)
              validator: RegularExpressionValidator { regularExpression: /#?[0-9a-fA-F]{0,8}/ }
              Keys.onEscapePressed: picker.typed()
              onAccepted: {
                var v = text.charAt(0) === "#" ? text : "#" + text
                if (/^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(v)) { picker.pick(v.toLowerCase(), true, true); picker.takeShown() }
                picker.typed()
              }
            }
          }
        }

        // Schemes for the whole widget, made from its base color.
        Caption { text: picker.texts.scheme || "Color scheme" }
        Flow {
          width: parent.width
          spacing: Math.round(6 * picker.unit)
          Repeater {
            model: ColorTools.SCHEMES
            Rectangle {
              id: schemeChip
              required property string modelData
              readonly property var dots: picker.visible && picker.kind && picker.section === "color" ? picker.schemeDots(modelData) : []
              radius: height / 2
              color: Qt.rgba(1, 1, 1, schemeArea.containsMouse ? 0.16 : 0.08)
              implicitWidth: schemeRow.implicitWidth + Math.round(16 * picker.unit)
              implicitHeight: schemeRow.implicitHeight + Math.round(8 * picker.unit)
              Row {
                id: schemeRow
                anchors.centerIn: parent
                spacing: Math.round(3 * picker.unit)
                Repeater {
                  model: schemeChip.dots
                  Rectangle {
                    required property var modelData
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.round(10 * picker.unit)
                    height: width
                    radius: width / 2
                    color: modelData
                    border.color: Qt.rgba(1, 1, 1, 0.3)
                  }
                }
                Item { width: Math.round(3 * picker.unit); height: 1 }
                Label {
                  anchors.verticalCenter: parent.verticalCenter
                  text: (picker.texts.schemes || {})[schemeChip.modelData] || schemeChip.modelData
                }
              }
              MouseArea {
                id: schemeArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onEntered: picker.hoverColors(picker.service.schemeColors(picker.kind, schemeChip.modelData))
                onExited: picker.unhover()
                onClicked: {
                  picker.service.setColors(picker.kind, picker.service.schemeColors(picker.kind, schemeChip.modelData))
                  picker.takeShown()
                }
              }
            }
          }
        }

        Row {
          spacing: Math.round(8 * picker.unit)
          Button {
            label: picker.appliedAll ? "✓ " + (picker.texts.applied || "Applied to all widgets")
                                     : (picker.texts.applyAll || "Apply to all widgets")
            onClicked: { picker.service.applyToAll(picker.kind); picker.appliedAll = true }
          }
          Button {
            // The whole widget back to the theme, or this part to its default.
            label: picker.whole ? (picker.texts.reset || "Reset") : (picker.texts.byDefault || "Default")
            enabled: picker.whole ? Object.keys(picker.colors).length > 0 : picker.value !== ""
            onClicked: {
              if (picker.whole) picker.service.setColors(picker.kind, {})
              else picker.pick("", true, false)
              picker.takeShown()
            }
          }
        }

        // Single parts: the base color and each part (• has an own color).
        Fold {
          label: picker.texts.fineTune || "Fine-tuning"
          open: !!picker.service && picker.service.fineTune
          onToggled: picker.setFineTune(!picker.service.fineTune)
        }
        Flow {
          visible: !!picker.service && picker.service.fineTune
          width: parent.width
          spacing: Math.round(4 * picker.unit)
          Repeater {
            model: ["base"].concat(Object.keys(picker.titles))
            Chip {
              required property string modelData
              label: modelData === "base" ? (picker.texts.baseColor || "Base color") : picker.titles[modelData]
              current: modelData === picker.part
              marked: !!picker.colors[modelData]
              onClicked: picker.service.selection = Object.assign({}, picker.selection, { part: modelData })
            }
          }
        }
      }

      // --- font -----------------------------------------------------------------------

      SectionTitle {
        visible: picker.hasText
        name: "font"
        label: picker.words.font || "Font"
        summary: (picker.spot.font_family || picker.words.omarchyFont || "Omarchy")
                 + "  ·  " + ((picker.words.weights || {})[picker.spot.font_weight] || picker.spot.font_weight || "")
      }
      Column {
        visible: picker.section === "font"
        width: parent.width
        spacing: Math.round(10 * picker.unit)
        bottomPadding: Math.round(12 * picker.unit)
        onVisibleChanged: if (visible) Qt.callLater(picker.showChosenFont)

        Rectangle {
          width: parent.width
          height: search.implicitHeight + Math.round(12 * picker.unit)
          radius: Math.round(6 * picker.unit)
          color: Qt.rgba(1, 1, 1, 0.08)
          border.color: search.activeFocus ? Color.accent : Qt.rgba(1, 1, 1, 0.25)
          TextInput {
            id: search
            anchors.fill: parent
            anchors.leftMargin: Math.round(8 * picker.unit)
            anchors.rightMargin: Math.round(8 * picker.unit)
            verticalAlignment: TextInput.AlignVCenter
            color: "white"
            clip: true
            font.family: picker.service ? picker.service.fontFamily : ""
            font.pixelSize: Style.font.bodySmall
            selectByMouse: true
            onTextChanged: fontView.positionViewAtBeginning()
            Keys.onEscapePressed: { search.text = ""; picker.typed() }
            // Return takes the first family found.
            onAccepted: {
              var first = picker.fontChoices[0]
              if (first !== undefined && search.text) picker.setLook("font_family", first, true)
              picker.typed()
            }
          }
          Caption {
            anchors.left: parent.left
            anchors.leftMargin: Math.round(8 * picker.unit)
            anchors.verticalCenter: parent.verticalCenter
            visible: search.text === ""
            text: "⌕  " + (picker.words.searchFonts || "Search fonts")
          }
        }
        ListView {
          id: fontView
          width: parent.width
          height: Math.round(7 * 28 * picker.unit)
          clip: true
          boundsBehavior: Flickable.StopAtBounds
          model: picker.fontChoices
          delegate: Rectangle {
            id: fontRow
            required property string modelData
            readonly property bool chosen: modelData === (picker.spot.font_family || "")
            width: fontView.width
            height: Math.round(28 * picker.unit)
            radius: Math.round(5 * picker.unit)
            color: chosen ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.35)
                          : Qt.rgba(1, 1, 1, fontArea.containsMouse ? 0.12 : 0)
            Label {
              x: Math.round(8 * picker.unit)
              anchors.verticalCenter: parent.verticalCenter
              width: parent.width - sample.width - Math.round(24 * picker.unit)
              elide: Text.ElideRight
              text: fontRow.modelData || (picker.words.omarchyFont || "The Omarchy font")
              font.bold: fontRow.chosen
            }
            // A sample in the family itself.
            Text {
              id: sample
              anchors.right: parent.right
              anchors.rightMargin: Math.round(8 * picker.unit)
              anchors.verticalCenter: parent.verticalCenter
              text: "Aa 12:45"
              color: Qt.rgba(1, 1, 1, 0.85)
              font.family: fontRow.modelData || (picker.service ? picker.service.fontFamily : "")
              font.pixelSize: Style.font.body
            }
            MouseArea {
              id: fontArea
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onEntered: picker.hoverLook("font_family", fontRow.modelData)
              onExited: picker.unhover()
              onClicked: picker.setLook("font_family", fontRow.modelData, true)
            }
          }
          Caption {
            anchors.centerIn: parent
            visible: fontView.count === 0
            text: picker.words.noFonts || "No font found"
          }
        }

        Caption { text: picker.words.weight || "Weight" }
        Segmented {
          key: "font_weight"
          options: ["light", "regular", "medium", "bold", "black"]
          labels: picker.words.weights || ({})
          current: picker.spot.font_weight || "bold"
        }
        LookSlider { key: "letter_spacing"; label: picker.words.letterSpacing || "Letter spacing"; suffix: " px" }

        // The lyrics: how the lines sit and move.
        Caption { visible: picker.has("align"); text: picker.words.alignment || "Alignment" }
        Segmented {
          visible: picker.has("align")
          key: "align"
          options: ["left", "center", "right"]
          labels: picker.words.aligns || ({})
          current: picker.spot.align || "center"
        }
        LookSlider {
          visible: picker.has("current_size")
          key: "current_size"
          label: picker.words.currentSize || "Size of the line being sung"
          suffix: " %"
          step: 5
        }
        LookSlider {
          visible: picker.has("scroll_ms")
          key: "scroll_ms"
          label: picker.words.scrollTime || "Scroll time"
          suffix: " ms"
          step: 50
        }
      }

      // --- effect ---------------------------------------------------------------------

      SectionTitle {
        name: "effect"
        label: picker.words.effect || "Effect"
        // The visualizer has no text to outline: for it that is no effect.
        readonly property string current: !picker.hasText && picker.spot.effect === "outline" ? "none" : (picker.spot.effect || "none")
        summary: ((picker.words.effects || {})[current] || current)
                 + (current !== "none" ? "  ·  " + picker.spot.effect_strength + " %" : "")
      }
      Column {
        visible: picker.section === "effect"
        width: parent.width
        spacing: Math.round(10 * picker.unit)
        bottomPadding: Math.round(12 * picker.unit)
        readonly property string current: !picker.hasText && picker.spot.effect === "outline" ? "none" : (picker.spot.effect || "none")

        Segmented {
          key: "effect"
          options: picker.hasText ? ["none", "outline", "shadow", "glow"] : ["none", "shadow", "glow"]
          labels: picker.words.effects || ({})
          current: parent.current
        }
        LookSlider {
          enabled: parent.current !== "none"
          key: "effect_strength"
          label: picker.words.strength || "Strength"
          suffix: " %"
          step: 5
        }
        LookSlider { key: "opacity"; label: picker.words.opacity || "Opacity"; suffix: " %"; step: 5 }
      }

      // --- card -----------------------------------------------------------------------

      SectionTitle {
        name: "card"
        label: picker.words.card || "Card"
        summary: picker.spot.card ? (picker.spot.card_opacity + " %" + (picker.spot.card_blur ? "  ·  " + (picker.words.cardBlur || "Blur") : ""))
                                  : (picker.words.off || "Off")
        dot: picker.spot.card && picker.service && picker.kind ? picker.service.colorOf(picker.kind, "card", Color.background) : "transparent"
      }
      Column {
        visible: picker.section === "card"
        width: parent.width
        spacing: Math.round(10 * picker.unit)
        bottomPadding: Math.round(12 * picker.unit)

        Toggle { key: "card"; label: picker.words.showCard || "Show the card" }
        LookSlider {
          enabled: !!picker.spot.card
          key: "card_opacity"
          label: picker.words.cardOpacity || "Card opacity"
          suffix: " %"
          step: 5
        }
        LookSlider { enabled: !!picker.spot.card; key: "card_radius"; label: picker.words.corners || "Corners"; suffix: " px"; step: 2 }
        LookSlider { enabled: !!picker.spot.card; key: "card_padding"; label: picker.words.roomAround || "Room around"; suffix: " px"; step: 2 }
        Toggle { enabled: !!picker.spot.card; key: "card_blur"; label: picker.words.cardBlur || "Blur behind the card" }
        Caption {
          visible: !!picker.spot.card && !!picker.spot.card_blur
          width: parent.width
          wrapMode: Text.WordWrap
          text: picker.words.blurLater || "The blur shows on the desktop once saved"
        }
      }
    }
  }
}
