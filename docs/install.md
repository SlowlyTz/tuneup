# Install, update, uninstall

**Needs:** [Omarchy](https://omarchy.org/) on Arch Linux, with Hyprland ≥ 0.56 and its Lua config. Everything else is installed by the installer.

## Install

One line:

```bash
curl -fsSL https://raw.githubusercontent.com/SlowlyTz/tuneup/master/install.sh | bash
```

Or from a clone:

```bash
git clone https://github.com/SlowlyTz/tuneup.git && ./tuneup/install.sh
```

With `curl`, the installer clones Tuneup to `~/.local/share/tuneup` and runs from there. With `git clone`, Tuneup runs from your clone, so keep that folder.

| Flag | Does |
|---|---|
| `--yes` | take the defaults, ask nothing |
| `--no-deps` | skip the packages and the camera |
| `--update` | used by `tuneup update` |
| `--dry-run` | print every change and the root script, change nothing |
| `--help` | show the flags |

## What the installer does

### 1. It checks your system

It **stops** when:
- there is no `pacman`,
- Python is older than 3.10,
- there is no `hyprctl`,
- Hyprland is not running or is older than 0.56,
- there is no `~/.config/hypr/hyprland.lua`.

It only **warns** when:
- Omarchy is missing (then there is no window list and no bar widgets),
- git is missing.

### 2. It asks first

| Question | Default | |
|---|---|---|
| Camera | no | the turned camera for every app, see [camera.md](camera.md) |
| Visualizer (cava) | no | for the visualizer desktop widget |
| Galaxy Book | yes | only asked on a Galaxy Book, see [samsung.md](samsung.md) |

### 3. It runs one root script, once

It runs once with `sudo`, so your password is asked **once**. It installs only the packages that are missing (`pacman -S --needed`), from the official Arch repositories only, nothing from the AUR:

- **always:** `python-gobject` `libadwaita` `webkitgtk-6.0` `inter-font` `ffmpeg` `brightnessctl` `git`
- **visualizer:** `cava`
- **camera:** `v4l2loopback-dkms` and the headers of the running kernel (e.g. `linux-omarchy-headers`)

The same script does the camera and Galaxy Book setup, if you chose them.

### 4. It sets up Tuneup as you

The installer runs `tuneup setup`, which sets up:
- the commands,
- your settings,
- the Hyprland file,
- the Omarchy shell plugins and the desktop widgets,
- the app entry and its icon.

It also moves an old hypr-screens setup over (see below).

### 5. It starts Tuneup

`tuneup restart --open` starts the background service and the tray icon, and opens Tuneup. From then on Tuneup lives in the **tray** (Omarchy: the `<` in the bar). Both start with Hyprland.

The first time, Tuneup shows a short welcome. Monitor settings and shortcuts are not part of the installer; set them in the app.

## What goes where

| What | Where |
|---|---|
| the code | your clone, or `~/.local/share/tuneup` for the curl install |
| commands (symlinks) | `~/.local/bin/tuneup`, `~/.local/bin/hypr-screens` (old name), `~/.local/bin/hypr-minimizer` |
| your settings | `~/.config/tuneup/` (`config.json`, `widgets.json`, `cava.conf`) |
| Hyprland file (generated, do not edit) | `~/.config/hypr/tuneup.lua` |
| the line that loads it | `require("hypr.tuneup")` at the end of `~/.config/hypr/hyprland.lua` (backup: `hyprland.lua.bak-tuneup`) |
| Omarchy shell plugins | `~/.config/omarchy/plugins/` (`hypr-minimizer.picker`, `hypr-screens.workspaces`, `hypr-screens.power`, `hypr-screens.widgets`), plus their entries in `~/.config/omarchy/shell.json` |
| app entry and icon | `~/.local/share/applications/io.github.slowlytz.Tuneup.desktop`, `~/.local/share/icons/hicolor/scalable/apps/tuneup.svg` |
| what is applied right now, status | `$XDG_RUNTIME_DIR/tuneup/` |
| minimized windows | `$XDG_RUNTIME_DIR/hypr-minimizer/state.json` |
| camera (only if chosen) | `/etc/modprobe.d/tuneup-camera.conf`, `/etc/modules-load.d/tuneup-camera.conf` |
| Galaxy Book (only if chosen) | `/etc/udev/rules.d/90-tuneup-samsung.rules`, `/etc/systemd/system/power-profiles-daemon.service.d/tuneup.conf` |

The shell plugins keep their `hypr-screens.*` ids on purpose.

### Coming from hypr-screens

`tuneup setup` moves the old setup over on install and on every update. It is safe to run again.

- `~/.config/hypr-screens` becomes `~/.config/tuneup`, and the old name stays as a symlink.
  - If both folders exist, nothing in the new one is replaced, and the leftovers are kept as `hypr-screens.old`.
- The runtime folder moves from `hypr-screens` to `tuneup`.
- `hypr_screens.lua` becomes `tuneup.lua`, with its `require` line.
- Autostart lines that start `hypr-screens` now start `tuneup`.

## Check it

```bash
tuneup list                       # your screens
hyprctl configerrors              # should print nothing
pgrep -af "tuneup (watch|tray)"   # background service and tray
tuneup restart                    # restart both
```

## Update

In the app: **General → About → Check for updates**. Or in a terminal:

```bash
tuneup update --check   # is there a new version?
tuneup update
```

The update does three things:
- It fetches the new version (`git fetch`, then `git pull --ff-only`).
- It runs `install.sh --update`. A password dialog appears only if packages are missing.
- It restarts Tuneup.

Your settings stay. After the update, Tuneup shows the welcome screen with old → new version and **What's new?**.

It refuses, with the reason, when:
- the folder is not a git checkout,
- you are offline,
- the checkout has local changes,
- your copy has diverged from GitHub.

## Uninstall

In the app: **General → About → Uninstall**, with the checkbox **Keep the settings** (on by default). Or:

```bash
tuneup uninstall                   # asks y/N first
tuneup uninstall --keep-settings   # keep ~/.config/tuneup
tuneup uninstall --yes             # do not ask
```

In this order, it:

1. stops the background service, the tray and the window;
2. brings back minimized windows and the windows of the fixed desktop;
3. ends a running "charge to 100 % once";
4. removes its lines from `hyprland.lua` and `autostart.lua`, and the Tuneup Lua files with their backups;
5. gives Omarchy its own desktops and battery bar widgets back and removes Tuneup's plugins from `shell.json`;
6. removes the commands, the app entry and the icon;
7. removes the camera and Galaxy Book root files (old and new names), with one password prompt, if any exist;
8. removes the runtime folders and, unless you keep the settings, `~/.config/tuneup` (and old `hypr-screens` folders);
9. runs `hyprctl reload`, so Omarchy's keys, look and monitor settings are back;
10. removes the clone if it lives in `~/.local/share/tuneup`.

**System packages stay.** At the end it lists the packages the installer took from the Arch repositories (WebKitGTK, the Inter font, cava, v4l2loopback, …). They are not removed, since other programs may use them. Remove them with `pacman` if you want.
