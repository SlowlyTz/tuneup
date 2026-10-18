# Camera

The **Camera** page turns the camera picture for every app, by 0°, 90°, 180° or 270°, like a monitor. It is useful when the laptop stands upside down on a dock or the webcam is mounted turned.

## Set it up once

**Set it up** (password, about a minute) installs `v4l2loopback-dkms` and the headers of your kernel from the Arch repositories. It also creates a virtual camera called **Rotated Camera** on every start. The installer offers this too.

Then pick **Rotated Camera** as the camera in Discord, the browser, Zoom and other apps.

## How it works

- **The switch** next to "Rotated Camera" turns it off and on. Off, nothing feeds the virtual camera, so apps no longer list it.
- While no app uses it, the real camera is **off** (its light is off) and the virtual camera shows black.
- As soon as an app opens it, the background service starts the real camera and passes its picture through, turned. Two seconds after the last app lets go, the camera is off again.
- The picture is always 1280 × 720, so turning it never breaks a running call. At 90° and 270° the upright picture sits between black bars.

**The preview** shows what apps get. It is a small picture the camera service writes next to the one for the apps, so the page never opens a camera itself, and the preview and an app (say a Discord call) work at the same time.

**One app at a time:** v4l2loopback lets one app read the virtual camera at a time, and the real camera only serves one program. Pick **Rotated Camera** in the app. If an app uses the real camera directly, the page says so, and the virtual camera stays black until that app lets go.

## Commands

```bash
tuneup camera status      # set up? which devices, which rotation
tuneup camera rotate 180  # 0 | 90 | 180 | 270
tuneup camera setup       # one-time, asks for your password
tuneup camera teardown    # remove the virtual camera again (the package stays)
```

The setup writes `/etc/modprobe.d/tuneup-camera.conf` and `/etc/modules-load.d/tuneup-camera.conf`. It also installs the headers of the running kernel, which `v4l2loopback-dkms` needs. The rotation is saved in `~/.config/tuneup/config.json` under `camera`.
