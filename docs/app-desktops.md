# App to desktop

The page **App to desktop** in the app gives apps a desktop of their own: an app
put there always starts on that desktop and nowhere else, for example WhatsApp
and Discord on scratch desktop 1.

- **Which desktops.** Scratch desktops 1–10 (`SUPER + S`, see [scratch.md](scratch.md))
  and desktops 1–10. Desktops 1–10 are Tuneup's normal desktops: on the laptop
  while the external screen keeps its own (see [one-desktop.md](one-desktop.md)),
  on the external screen if the laptop keeps its own. The external screen's own
  desktops cannot be chosen.
- **Up to 5 apps per desktop**, each **tiled** or **floating** (centred, the size
  of a web app flyout, smaller on a small screen). An app is on one desktop only:
  adding it somewhere else takes it from where it was.
- **In the background.** The app opens on its desktop; you stay where you are.
  When it starts where you cannot see it – a closed scratch row, a desktop no
  screen shows – Omarchy's own launch message shows its name with a rocket.
- **A closed scratch row.** The app waits there unseen and is there when you
  press `SUPER + S`. With the scratch desktops switched off, their apps start
  wherever they open until the scratch desktops are on again.
- **Kept there for 5 seconds.** For 5 seconds after a window opened Tuneup puts it
  back on its desktop if it leaves (some apps move or float themselves while they
  start). After that you can move it wherever you like.
- **Every new window of the app** goes there (a second window, a dialog), windows
  that were open before you set it up stay where they are.

How it finds the app: by the window's class, taken from the app's desktop entry
(its `StartupWMClass`, its name; for a web app of Helium or Chromium the
`chrome-<app id>-<profile>` class its window gets a moment after it opens). An
app removed from the system stays in the list as "Not installed" until you
remove it.

The setting is `app_desktops` in `~/.config/tuneup/config.json`; it goes live at
once (Tuneup's Lua file, no reload).
