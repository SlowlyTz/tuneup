# Screens

Every monitor you ever plug in is remembered, and each one keeps its own settings. Screens are recognised by make, model and serial number, not by the port, so a monitor keeps its settings on any cable or dock.

![The Screens page](images/screens.png)

## The Screens page

At the top the connected screens stand as they do on your desk.

- **Drag a screen** to another edge of the laptop, and the mouse crosses there. Arrow keys work too: select a screen, then press an arrow.
- **Click a screen** to see its settings below the picture.
- **Known screens:** monitors you used before but that are not connected now are in the row below the picture. Their settings apply as soon as they come back.
- **Swap the fixed screen** at the top right: see [one-desktop.md](one-desktop.md).
- **For new monitors**, below the picture: which screen gets the fixed desktop when an unknown monitor is plugged in (for all screens).

The settings of the screen you clicked:

| Setting | Choices |
|---|---|
| Mirror the laptop screen | on or off (external screens), see below |
| Position | left, above, below or right of the laptop (external screens; also by dragging) |
| Rotation | Normal · Portrait, right · Upside down · Portrait, left |
| Scaling | Auto · 100 % · 125 % · 150 % · 200 % |
| Resolution | every mode the screen offers, the recommended one first, each with its refresh rates |

A setting you never touched shows **Not set**, with what Hyprland does now. **Reset** takes your value back, and Hyprland's own config decides again.

Under **Advanced**:
- **Favorite:** favorites are listed first.
- **Forget:** only while the screen is unplugged, and it asks first.

### Safety net

When a change gives a screen new values (rotation, scaling, resolution, place), Tuneup asks whether to keep it. Without a click on **Keep** it goes back after 15 seconds, like the display settings of other desktops.

## Mirror the laptop screen

For a projector or a TV: switch on **Mirror the laptop screen** for that monitor, and it shows the same picture as the laptop. Tuneup remembers it, so the projector mirrors again the next time it is plugged in, while your desk monitor keeps its own desktops.

- A mirroring screen has no place, rotation or scaling of its own. Its resolution can still be set; if it is not the laptop's shape, the picture gets black bars.
- In the picture at the top it stands under **Mirrors the laptop**; click it there to change its settings.
- It is no screen of its own for [one desktop](one-desktop.md): nothing is fixed while it is plugged in.
- With the lid closed there is nothing to mirror: the monitor shows its own picture until the lid opens again.
- Like every setting, it can apply **Always** or only while a certain other screen is connected.

## Settings tied to a monitor

Every setting can apply **Always** or only while a certain other screen is connected. Use the chip **Always ▾** next to the setting.

Example: turn the laptop upside down only at the desk with the HP monitor. Click Laptop, choose Rotation → *Upside down*, then the chip → *Only with HP 32f*.

Unplug the HP and the laptop goes back to normal. Plug it in, and it turns again.

## From the terminal

A screen can be named by its name, its connector or its id:

```bash
tuneup list                                  # ● connected, ★ favorite
tuneup set "HP 32f" scale 1.25
tuneup set DP-3 position left
tuneup set Laptop rotation 180
tuneup set Laptop rotation unset             # back to Hyprland's own config
tuneup set "LG TV" mirror on                 # show the laptop's picture
tuneup when Laptop rotation "HP 32f"         # only while HP 32f is connected
tuneup when Laptop rotation always
tuneup favorite "HP 32f"
tuneup forget "Fujitsu B27-9 TS QHD"
```

## How it works

- `tuneup watch`, the background service, applies the settings when a screen is plugged in or out, and after a Hyprland reload. It starts with Hyprland.
- Settings are applied with `hl.monitor`, edge to edge with the laptop. If a setting stops applying, Hyprland's config is reloaded once to get your normal values back.
- If another app changes a screen, Tuneup puts it back: see [keep-settings.md](keep-settings.md).

| What | Where |
|---|---|
| settings and known screens | `~/.config/tuneup/config.json` |
| what is applied right now | `$XDG_RUNTIME_DIR/tuneup/applied.json` |
