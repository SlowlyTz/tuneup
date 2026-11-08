# Minimize windows

Part of Tuneup, as the command `hypr-minimizer` that the minimize keys call. It hides windows in a hidden workspace (`special:minimized`) and brings them back, last in first out, **per desktop**.

The keys (`SUPER + M` hide, `SUPER + I` bring back, `SUPER + .` window menu, …) are set in Tuneup under **Keyboard**: see [keys.md](keys.md).

## Commands

```bash
hypr-minimizer stash          # minimize the active window
hypr-minimizer minimize 0xabc # minimize a window by address
hypr-minimizer stash_others   # minimize everything else on this desktop
hypr-minimizer pop            # bring back the last one (this desktop)
hypr-minimizer pop_all        # bring back all (this desktop)
hypr-minimizer undo           # undo last stash/pop/restore (5 steps)
hypr-minimizer menu           # window menu
hypr-minimizer list           # print minimized windows (--json)
hypr-minimizer restore 0xabc  # restore by address (--here: onto this desktop)
hypr-minimizer peek 0xabc     # peek by address
hypr-minimizer fetch 0xabc 3  # bring a window onto desktop 3 (restores a minimized one)
```

## Window menu

Keyboard only (the mouse does nothing inside it; clicking outside closes it).

| Key | Does |
|---|---|
| `Enter` | bring it to this desktop |
| `Shift+Enter` | back to the desktop it was minimized on |
| `-` | **peek** |
| typing | filter; the first match is always selected |
| `Esc` | clear filter, then close |

## Peek

- The window slides in from the bottom, over everything, in the space a single tiled window would take (bar and gaps stay free).
- Your tiled windows underneath don't move.
- `SUPER + M` slides it out again. Switching desktop hides it too.
- It goes back to its old place in the list.

## Dock

Rest the pointer on the Omarchy logo in the bar for a moment and a dock fades in on the left: one icon per app with open windows, in the order of their desktops (the small number shows where), minimized ones paler below a line. A dot marks an app with a window on this desktop.

- Click an icon to bring the window to this desktop. An app with several windows shows how many; a click lists them, and a click on one brings it.
- A window brought this way always lands in front. Where other windows float, a tiled one would end up behind them, so it floats too, in the middle of the screen.
- The dock stays while the pointer is on the logo or the dock, and goes a moment after it left.
- Left click on the logo still opens the Omarchy menu, right click a terminal.
- A full-screen window hides the bar, and with it the dock.

## Taskbar

Right of the desktops in the bar sit the windows of the desktop on that screen, in the order they lie on it from left to right. A short line marks the focused one. A window minimized from this desktop keeps its place and turns grey.

- Click a window to minimize it, click a grey one to bring it back.
- Middle click closes a window. Resting on an icon shows its title.
- Windows come and go with a slide; another desktop fades the row over.

## Scratch desktops and the scratchpad

On a [scratch desktop](scratch.md) (`SUPER + S`, the default) minimizing works as on any desktop; the menu shows these windows with the scratch desktop's number (`ws 201` and up).

With the scratch desktops off (`tuneup option scratch off`), `SUPER + S` opens Omarchy's scratchpad. While it is open, it counts as the current desktop: `SUPER + M` there minimizes into its own list, `SUPER + I` puts the window back into the scratchpad, and `Enter` in the window menu brings any window into it. Opened from a desktop, `Enter` brings a scratchpad window to that desktop; `Shift+Enter` sends it back to the scratchpad. If minimizing empties the scratchpad, Hyprland closes it — open it again with `SUPER + S` and press `SUPER + I`. The menu shows these windows as `ws scratchpad`.

## Apps that ask to be shown

Starting an app again from the launcher (`SUPER + SPACE`) when it already runs brings its window **to this desktop** — also when it is minimized or on another desktop. Hyprland would otherwise switch to its desktop, or open `special:minimized` and show every minimized window. Same for notifications and links that bring an app forward. Tuneup sets this up in its generated Hyprland file.

## Bar counter (optional)

Shows `-3` when 3 windows are minimized.

**Omarchy bar**: add this to a workspaces widget (e.g. `omarchy-workspaces/Workspaces.qml`), inside its `GridLayout` (give `columns` one more slot while it is visible):

```qml
readonly property int minimizedCount: {
  var values = Hyprland.workspaces.values
  for (var i = 0; i < values.length; i++)
    if (String(values[i].name || "") === "special:minimized") return values[i].toplevels.values.length
  return 0
}

WidgetButton {
  visible: root.minimizedCount > 0
  bar: root.bar
  text: "-" + root.minimizedCount
  opacity: 0.5
  horizontalMargin: 4
  fixedHeight: root.barSize
  onPressed: function() { if (root.bar) root.bar.run("hypr-minimizer menu") }
}
```

**Waybar**:

```jsonc
"custom/minimized": {
  "exec": "n=$(hypr-minimizer list --json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'); [ \"$n\" -gt 0 ] && echo \"-$n\" || echo",
  "interval": 2,
  "on-click": "hypr-minimizer menu"
}
```

## Where things live

| What | Where |
|---|---|
| minimized windows + undo | `$XDG_RUNTIME_DIR/hypr-minimizer/state.json` |
| menu plugin | `~/.config/omarchy/plugins/hypr-minimizer.picker` |
| dock (the bar's logo) | `~/.config/omarchy/plugins/hypr-screens.dock` |
| taskbar (beside the desktops) | `~/.config/omarchy/plugins/hypr-screens.taskbar` |

Without Omarchy the menu falls back to `walker`, `wofi` or `rofi` (only `Enter`: brings it here).
