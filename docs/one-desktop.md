# One desktop on one screen

With an external monitor connected:

- **One screen is fixed:** it always shows the same desktop (workspace `99`, shown as `1` in the bar). This is good for chat, music or a dashboard.
- **The other screen has desktops 1–10.** `SUPER + 1…0` only switch that one.

This is for **one** external monitor. Without one, everything is normal Hyprland.

## Which screen is fixed?

Tuneup decides in this order:

1. **Swap:** until you unplug the monitor. Swap from the tray menu (*Swap the fixed screen*), the **Swap** button on Home and on Screens, or `tuneup swap`.
2. The setting **Always shows the same desktop** of a screen (Screens page). If both screens say yes, the laptop wins.
3. **For new monitors** (Screens page, below the picture): Off · External monitor · Laptop.

The canvas on the Screens page marks the fixed screen with a pin.

## More than one desktop on the fixed screen

**Desktops on the fixed screen** (Screens page, below the picture) gives it up to 10 desktops of its own
(workspaces `99`, `100`, … shown as `1`, `2`, … in its bar). The two screens stay apart: desktops 1–10 never
appear on the fixed screen, its own desktops never on the other one.

With more than one, `SUPER + 1…0` switch the desktops of the screen you are on (`SUPER + SHIFT + 1…0` move the
window there), swiping moves between them, and a click on a tile in either bar switches that screen.

```bash
tuneup option fixed_desktops 5
```

Example: the laptop is fixed only at the desk; any other monitor is fixed itself:

```bash
tuneup set Laptop one_desktop yes
tuneup when Laptop one_desktop "HP 32f"
tuneup option default_fixed external
```

## What happens when you…

| …you | then |
|---|---|
| plug in (laptop fixed) | the windows you had on the laptop stay on the laptop |
| plug in (external fixed) | the external screen starts empty; move windows there with `SUPER + Y` |
| swap | the screens trade places; windows and layouts stay as they are |
| unplug | windows of the fixed screen go to the desktop the laptop shows |

## What it needs

- **Desktop keys** on: Keyboard page, or `tuneup option desktop_keys on`. They make `SUPER + 1…0` and `SUPER + TAB` go through Tuneup.
- Omarchy bar: Tuneup's desktops widget, which knows the fixed screen. The installer sets it up.

```bash
tuneup status        # who is fixed right now
```
