# Sound

The **Sound** page controls every output, input and app, not only the default device.

![The Sound page](images/sound.png)

| Part | Shows | You can |
|---|---|---|
| **Output** | speakers, headphones, Bluetooth, HDMI and monitors | volume, mute, make it the default, **Force Mute** |
| **Input** | microphones | the same |
| **Apps** | apps playing sound right now, with icon and name | volume, mute, pick the output it plays on |

Outputs on an unplugged jack (headphones not plugged in, HDMI without a screen) are left out.

## Switched-off speakers

On some laptops the sound card drives *either* the speakers *or* the headphone jack, with one profile for each. While the headphone profile is active, the speakers show **Switched off** with a **Switch on** button, which switches the card to the speaker profile. The default output stays where it was, so Bluetooth keeps playing, and you can set the speaker volume for later.

## Force Mute

The lock button on a device keeps it silent for good: muted and at 0 %.

- Anything that turns it back up is undone right away: a volume key, an app, a profile switch, reconnecting.
- The background service checks it on every PipeWire change and once a second, so it also works with the app closed.
- A force-muted device that is not there right now stays listed and is silenced the moment it shows up.
- Switching it off brings back the volume and mute from before.

It is saved in `~/.config/tuneup/config.json` under `sound.force_mute`, by sound card and port, so it survives profile switches and restarts.

## Needs

`pactl` (PipeWire's `pipewire-pulse`, standard on Omarchy).
