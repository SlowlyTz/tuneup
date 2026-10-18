# Troubleshooting

## Settings are not applied after plugging in

```bash
pgrep -af "hypr-screens watch" || (hypr-screens watch &)   # watcher running?
hypr-screens apply
```

Watcher log: run it in a terminal to see what it does:

```bash
pkill -f "hypr-screens watch"; hypr-screens watch
```

## A key does nothing / fires twice

```bash
grep -n hypr_screens ~/.config/hypr/hyprland.lua   # must show the require line
hyprctl configerrors
hypr-screens setup                                  # rewrites the Lua file
```

## No tray icon

```bash
pgrep -af "hypr-screens tray" || (hypr-screens tray &)
```

Omarchy: the tray is folded behind the `<` in the bar. The window needs GTK 4 + libadwaita + PyGObject:

```bash
python3 -c 'import gi; gi.require_version("Gtk","4.0"); gi.require_version("Adw","1")' && echo ok
```

## The window menu opens with the old look

The shell caches the menus:

```bash
omarchy-restart-shell
```

## Desktops end up on the wrong screen

```bash
hypr-screens status
hypr-screens apply
```

Forget a swap: unplug and plug in again, or

```bash
rm "$XDG_RUNTIME_DIR/hypr-screens/fixed.json" && hypr-screens apply
```

## Another app keeps changing a screen, gaps or a key

The watcher puts back what hypr-screens sets (every 5 s, and right after a
reload or a hotplug). When another app keeps changing the same thing back, it
gives up on it for a while (30 s, then longer) instead of fighting:

```bash
hypr-screens enforce        # recent fixes and what it gave up on for now
hypr-screens enforce off    # leave it to the other app
```

## A screen stays dark after unplugging a dock

A known Hyprland (aquamarine) bug: the dock's screen is gone but still holds
the graphics output, and the screen plugged in next gets nothing. The watcher
notices it, switches the screen off and on once and, if it stays dark, says
so. What helps then: unplug and plug in again; or switch to another console
and back (`Ctrl+Alt+F2`, then `Ctrl+Alt+F1`); or log out and in.

## Stuck in "press the new shortcut"

Press `Esc`. Still stuck:

```bash
hyprctl dispatch 'hl.dsp.submap("reset")'
```

## A peeked window does not go away

```bash
hypr-minimizer stash   # or SUPER + M on it
```

## Start over

```bash
cp ~/.config/hypr-screens/config.json ~/hypr-screens-config.backup.json
rm ~/.config/hypr-screens/config.json && hypr-screens setup
```
