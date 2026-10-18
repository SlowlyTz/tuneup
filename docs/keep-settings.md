# Keeps your settings in force

What you set in Tuneup stays set. When another app, a script or a Hyprland reload changes something Tuneup manages, the background service puts it back.

It is on by default. Switch it in Tuneup under **General → Keep my settings**, which also lists the latest corrections, or in a terminal:

```bash
tuneup enforce        # status: recent corrections, what it leaves alone for now
tuneup enforce on
tuneup enforce off    # leave it to the other apps
```

## What it keeps

| Area | What |
|---|---|
| Screens | resolution, scaling, rotation and place of each monitor |
| Desktops | the fixed desktop on its screen, desktops 1–10 on the other one |
| Windows | gaps, corners, border, blur, transparency, border colors |
| Keyboard | Tuneup's shortcuts and the desktop keys stay bound to Tuneup |
| Sound | Force Mute (checked every second) |
| Battery & power | charge limit and performance mode on a Galaxy Book (checked every second) |

It also notices a screen that Hyprland drives but that shows no picture, a known problem after unplugging a dock. It switches that screen off and on once (see [troubleshooting.md](troubleshooting.md)).

## How it works

- Every 5 seconds, and right after a reload or a monitor change, the service compares what Hyprland shows with your settings. It puts back only what drifted, in one go.
- **No endless fights.** If another app changes the same thing more than 3 times within a minute, Tuneup leaves it alone for a while: 30 seconds at first, then twice as long each time, up to 30 minutes. It forgets the trouble after 10 quiet minutes. The General page shows what it leaves alone and until when.
- Force Mute never backs off: a muted device stays muted.
- The service has to run for any of this. General shows **Watching** while it does, and a warning when it does not (see [troubleshooting.md](troubleshooting.md)).
