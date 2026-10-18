# Keys

Only **window keys** live on the keyboard: minimize, bring back, the window menu, and the desktops. Everything else is in the app. Every action has **two** key slots.

| Action | Default |
|---|---|
| Open window list (the window menu) | `SUPER + .` |
| Hide window | `SUPER + M` |
| Hide all others | – |
| Bring back last | `SUPER + I` |
| Bring back all | `SUPER + SHIFT + I` |
| Undo | `SUPER + U` |

## Change a key in the app

1. Tray icon → Tuneup → **Keyboard**.
2. Click the key you want to change, or **+ Second key**.
3. Press the new combination. `Backspace` removes the key, `Esc` cancels.
4. If the key is already used by something else, Tuneup tells you what it does now and asks before replacing it.

While you press the new keys, Hyprland's own shortcuts are paused, so even taken combinations get recorded.

**Desktop keys** (same page): `SUPER + 1…0` and `SUPER + TAB` go through Tuneup, so the desktops 1–10 land on the right screen. Needed for [one desktop](one-desktop.md).

## Change a key in the terminal

```bash
tuneup bind minimizer_menu 1 "SUPER + PERIOD"
tuneup bind minimizer_menu 2 "SUPER + SHIFT + F23"   # Copilot key
tuneup bind stash_others 1 ""                         # clear
tuneup option desktop_keys on
```

Actions: `minimizer_menu` `stash` `stash_others` `pop` `pop_all` `undo`

## Where they live

- Tuneup generates its Hyprland file `~/.config/hypr/tuneup.lua`. Don't edit it; change keys as above.
- It unbinds whatever else sits on your keys first, so nothing fires twice.
- New keys work at once. A key you gave up gets its old meaning back after the next `hyprctl reload`.

See what is bound:

```bash
hyprctl binds -j | jq -r '.[] | "\(.modmask) \(.key) \(.keycode) \(.description)"' | sort
```
