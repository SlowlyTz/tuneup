# Scratch desktops

Tuneup replaces Omarchy's scratchpad with a row of scratch desktops: normal
desktops (workspaces 201 and up) that fly in from below like the scratchpad
did, but you can have several, swipe between them and move windows onto them.

| Key | Does |
|---|---|
| `SUPER + S` | show the scratch desktops (the last one you used) – press again to go back |
| `SUPER + 1…0` (in the row) | scratch desktop 1–10 |
| `SUPER + SHIFT + 1…0` (in the row) | move the window to scratch desktop 1–10, follow |
| `SUPER + SHIFT + ALT + 1…0` (in the row) | move the window there, stay |
| `SUPER + ALT + S` | move the window to the last scratch desktop, stay where you are |
| `SUPER + SHIFT + S` | the same – only if nothing of yours is on that key (see below) |
| 3-finger swipe (in the row) | next / previous scratch desktop; past the last one a new one opens |

- **One row for all screens.** `SUPER + S` on any screen brings the scratch
  desktop to that screen. Each screen remembers the desktop it showed and goes
  back to it.
- **It flies.** It comes in from below and leaves downward, like the old
  scratchpad. Switching inside the row with SUPER + 1…0 uses your own desktop
  animation, as outside it (Omarchy: none); a swipe follows the finger.
- **Swiping stays in the row.** Swiping left past the first scratch desktop
  bounces back.
- **Closed, the row is out of the way.** While no screen shows it, its desktops
  wait hidden, so swiping on your normal desktops never lands in them; `SUPER + S`
  brings them all back. Switching scratch desktops off (or uninstalling) turns
  them into normal desktops again, nothing stays hidden.
- **Scratch desktops 1 to 5 are always there** while the row is open, empty or
  not, so `SUPER + 1…5` and the numbers in the bar always mean the same desktop.
  Further ones (6 and up) disappear when they are empty.
- **Outside the row** `SUPER + 1…0` work as before (Omarchy's desktops, or
  Tuneup's desktop keys with "one desktop" on).
- **The bar** shows only the scratch desktops (numbered 1, 2, 3 …, in the accent
  color behind a marker) on a screen that is in the row, and never shows them
  elsewhere.
- Windows that were in Omarchy's scratchpad move to scratch desktop 1 when
  Tuneup is set up.

`SUPER + SHIFT + S` is taken only if it is free or holds Omarchy's own default
(Google Maps); if you put something of your own there (a screenshot, say),
Tuneup leaves it alone. Change your mind:

```bash
tuneup option scratch_shift_s on     # or off
tuneup option scratch off            # no scratch desktops: Omarchy's scratchpad keys come back
```
