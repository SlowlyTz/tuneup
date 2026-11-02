# Own desktops for one screen

With an external monitor connected:

- **One screen has desktops of its own** (here: the fixed screen): it always shows the same desktop (workspace `99`, shown as `1` in the bar). This is good for chat, music or a dashboard.
- **The other screen has desktops 1–10.** `SUPER + 1…0` only switch that one.

This is for **one** external monitor. Without one, everything is normal Hyprland.

## Which screen is fixed?

Tuneup decides in this order:

1. **Swap:** until you unplug the monitor. Swap from the tray menu (*Swap the own desktops*), the **Swap** button on Home and on Screens, or `tuneup swap`.
2. **Own desktops** (Screens page, below the picture): Off · External monitor · Laptop.

A monitor that [mirrors the laptop](screens.md#mirror-the-laptop-screen) is no screen of its own, so nothing is fixed while it is plugged in.

The canvas on the Screens page marks the fixed screen with a pin.

## More than one desktop on the fixed screen

**Number of own desktops** (Screens page, below the picture) gives it up to 10 desktops of its own
(workspaces `99`, `100`, … shown as `1`, `2`, … in its bar). The two screens stay apart: desktops 1–10 never
appear on the fixed screen, its own desktops never on the other one.

With more than one, `SUPER + 1…0` switch the desktops of the screen you are on (`SUPER + SHIFT + 1…0` move the
window there), swiping moves between them, and a click on a tile in either bar switches that screen.

```bash
tuneup option fixed_desktops 5
```

## What happens when you…

| …you | then |
|---|---|
| plug in (laptop fixed) | the windows you had on the laptop stay on the laptop |
| plug in (external fixed) | the external screen starts empty; move windows there with `SUPER + Y` |
| swap | the screens trade places; windows and layouts stay as they are |
| unplug, or mirror the laptop | windows of the fixed screen go where **When the external monitor goes** says (below) |

## When the external monitor goes

When the external screen is the fixed one and is unplugged or set to mirror the laptop, its windows:

- **Onto the laptop's current desktop** (the default): all together on the desktop the laptop shows.
- **Spread over desktops 6–10:** its desktop 1 onto desktop 6, 2 onto 7 and so on; from its sixth desktop on all onto 10.
  Windows already there stay. When the monitor is back (or stops mirroring), the windows still on those desktops go back.
- **Close them:** as `SUPER + W` would, so an app may still ask to save.

When the laptop is the fixed screen, its own windows always stay together on the desktop it shows.

```bash
tuneup option unplug_windows spread   # fold | spread | close
```

## What it needs

- **Desktop keys** on: Keyboard page, or `tuneup option desktop_keys on`. They make `SUPER + 1…0` and `SUPER + TAB` go through Tuneup.
- Omarchy bar: Tuneup's desktops widget, which knows the fixed screen. The installer sets it up.

```bash
tuneup status        # who is fixed right now
```
