# Troubleshooting

## Settings are not applied after plugging in

Check that the background service runs, then apply everything once:

```bash
pgrep -af "tuneup (watch|tray)"   # both should be listed
tuneup restart                    # restarts the background service and the tray
tuneup apply
```

To see what the service does, run it in a terminal:

```bash
pkill -f "tuneup watch"; tuneup watch
```

## "The background service is not running" (General page)

Nothing is kept in force and nothing is applied on plug or unplug while it does not run. Start it with `tuneup restart`. It starts with Hyprland by itself; if it does not, check that the line loading Tuneup is still in `~/.config/hypr/hyprland.lua` (next section).

## A key does nothing or fires twice

```bash
grep -n tuneup ~/.config/hypr/hyprland.lua   # must show require("hypr.tuneup")
hyprctl configerrors
tuneup setup                                  # writes Tuneup's Hyprland file again, keeps your settings
```

## No tray icon

```bash
pgrep -af "tuneup tray" || tuneup restart
```

On Omarchy the tray is folded behind the `<` in the bar. You can always open the app with `tuneup settings`.

## The app does not open

It needs WebKitGTK 6.0, GTK 4, libadwaita and PyGObject; the installer installs them. Check:

```bash
python3 -c 'import gi; gi.require_version("Gtk","4.0"); gi.require_version("Adw","1"); gi.require_version("WebKit","6.0")' && echo ok
```

If that fails, run the installer again (see [install.md](install.md)); `--dry-run` shows what it would change.

## The window menu opens with the old look

The shell caches the menus:

```bash
omarchy-restart-shell
```

## Desktops end up on the wrong screen

```bash
tuneup status
tuneup apply
```

To forget a swap, unplug and plug in again, or:

```bash
rm "$XDG_RUNTIME_DIR/tuneup/fixed.json" && tuneup apply
```

## Another app keeps changing a screen, the gaps or a key

Tuneup puts back what it sets. When another app keeps changing the same thing back, Tuneup gives up on it for a while instead of fighting (see [keep-settings.md](keep-settings.md)):

```bash
tuneup enforce        # recent corrections and what it leaves alone for now
tuneup enforce off    # leave it to the other app
```

## A screen stays dark after unplugging a dock

This is a known Hyprland (aquamarine) bug. The dock's screen is gone but still holds the graphics output, so the screen you plug in next gets nothing. Tuneup notices this, switches the screen off and on once, and tells you if it stays dark.

What helps then:
- unplug and plug in again,
- or switch to another console and back (`Ctrl+Alt+F2`, then `Ctrl+Alt+F1`),
- or log out and in.

## Stuck in "press the new shortcut"

Press `Esc`. If it is still stuck:

```bash
hyprctl dispatch 'hl.dsp.submap("reset")'
```

## A peeked window does not go away

```bash
hypr-minimizer stash   # or SUPER + M on it
```

## Start over

```bash
cp ~/.config/tuneup/config.json ~/tuneup-config.backup.json
rm ~/.config/tuneup/config.json && tuneup setup && tuneup restart
```
