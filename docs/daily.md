# Daily cheat sheet

Default keys. Yours may differ: see them in Tuneup under **Keyboard**, or with `tuneup state | jq .keybinds`.

## Windows

| Key | Does |
|---|---|
| `SUPER + M` | minimize this window |
| `SUPER + I` | bring back the last minimized one |
| `SUPER + SHIFT + I` | bring back all |
| `SUPER + U` | undo |
| `SUPER + .` | window menu |

In the window menu: `Enter` here · `Shift+Enter` back to its desktop · `-` peek · type to filter · `Esc` close.

## Screens

| Key | Does |
|---|---|
| tray icon (click) | open Tuneup |
| tray icon (right-click) | open Tuneup, swap the fixed screen, arrange widgets, quit |
| `SUPER + Y` | move window to the other screen (Hyprland, not Tuneup) |

## Scratch desktops

| Key | Does |
|---|---|
| `SUPER + S` | scratch desktops in / out |
| `SUPER + 1…0`, `+ SHIFT`, `+ SHIFT + ALT` (in the row) | scratch desktop 1–10 / move window there |
| `SUPER + ALT + S` | move window to the last scratch desktop |
| swipe (in the row) | next / previous scratch desktop |

More: [scratch.md](scratch.md).

## Desktops (with "one desktop" on)

| Key | Does |
|---|---|
| `SUPER + 1…0` | show desktop 1–10 |
| `SUPER + SHIFT + 1…0` | move window there, follow |
| `SUPER + SHIFT + ALT + 1…0` | move window there, stay |
| `SUPER + TAB` / `+ SHIFT` | next / previous visible window |

## Commands

```bash
tuneup settings                          # open Tuneup
tuneup list                              # screens, ● connected, ★ favorite
tuneup set Laptop rotation 180           # set a value (unset = remove)
tuneup when Laptop rotation "HP 32f"     # only while HP 32f is connected
tuneup when Laptop rotation always
tuneup swap                              # swap the fixed screen until unplugged
tuneup apply                             # apply everything now
tuneup enforce [on|off]                  # keep your settings in force (status without on/off)
tuneup option scratch on|off             # scratch desktops on SUPER + S (off: Omarchy's scratchpad)
tuneup restart                           # restart the background service and the tray
tuneup update --check                    # is there a new version?
tuneup update                            # update Tuneup
tuneup uninstall [--keep-settings]       # remove Tuneup
hypr-minimizer list                      # minimized windows
```

`hypr-screens` still works in place of `tuneup`.
