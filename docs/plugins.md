# Plugins

Plugins are extras that go into the Omarchy bar. They come with Tuneup in the `plugins/` folder of the checkout. You install the ones you want.

## Install one

1. Tray icon → Tuneup → **Plugins**.
2. **Install**. The plugin shows up in the bar at once, where it belongs (the music plugin to the left of the AI icon).
3. Its settings appear below it. **Remove** takes it out of the bar again and keeps the settings for later.

In the terminal:

```bash
tuneup plugin list
tuneup plugin install music
tuneup plugin remove music
```

Updates keep installed plugins in the bar. `tuneup uninstall` removes them.

## Music

A note in the bar, always there, bright while music plays. A click opens the panel:

- cover, title, artist, album
- the progress: click or drag to jump
- previous, play/pause, next; shuffle and repeat when the player has them
- where it plays: the app, or for a browser the site (SoundCloud as a web app or a tab shows "SoundCloud", not the browser's name)
- with several players (SlowTunes, Spotify, a browser tab): a button for each, to pick the one shown

In the bar: middle click plays or pauses, the wheel skips.

It works with every player that speaks MPRIS. **SlowTunes** (the desktop app) gives more: a heart to like the song and the queue ("Up next"; a click plays that song). Installing the plugin checks whether your SlowTunes can do that.

Settings: **Preferred player** (shown first when several play) and **Show the time left**.

## Display

Takes the place of Omarchy's display icon (the monitor) in the bar; removing the plugin puts Omarchy's back on the same spot. The panel is Omarchy's: brightness, text size and scale work as before, and the shortcut for the display panel opens this one. Instead of Omarchy's list of displays it shows your **screens**:

- every connected screen: laptop or monitor, the name Tuneup knows it by, the connector and resolution
- how they are used, at a glance: extended, mirrored, laptop only
- for each external screen a switch **Extend | Mirror** (mirror shows the laptop's picture); Tuneup keeps the choice for that screen, like `tuneup set "HP 32f" mirror on`
- **Screen settings in Tuneup** opens the settings window

The keys work as everywhere in the panel: j/k from row to row, h/l picks Extend or Mirror, Enter applies it.

## Write a plugin

A folder `plugins/<id>/`:

- `plugin.json`: name, description, icon, version, where it goes in the bar, its settings and checks (see the top of `hypr_screens/plugins.py` for every field)
- optional `"replaces": ["omarchy.monitor"]`: built-in widgets the plugin stands in for. Installing puts it exactly where the first of them sits and takes that one out of the bar; removing the plugin (or Tuneup) puts it back on that spot
- `shell/`: an Omarchy shell plugin (`manifest.json` and its QML). Installing links this folder to `~/.config/omarchy/plugins/<its id>`.

The settings are written onto the widget's entry in `shell.json`; the widget reads them with `setting("key", default)`. Tuneup also writes `language` there, so the widget can speak the language set in the app.
