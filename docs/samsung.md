# Galaxy Book support

Samsung Settings, on Linux. On a Samsung Galaxy Book, Tuneup gets a **Battery & power** page with what Samsung Settings offers on Windows. It needs the `samsung-galaxybook` kernel driver (in Linux since 6.14).

Every other laptop (Intel, AMD, HP, Lenovo, Dell, …) works fully with Tuneup. Only this page does not show there.

![The Battery & power page](images/power.png)

## What it does

| Part | You can |
|---|---|
| **Battery** | set the charge limit (60 · 80 · 90 · 100 % in the app, 50–100 % in the terminal), **charge to 100 % once**, and see level, health, charge cycles and power draw |
| **Performance mode** | Saver · Quiet · Balanced · Performance: how fast and how loud (the fan). It also shows whether the fan runs and the CPU temperature. |
| **Keyboard light** | its level |
| **Advanced** | USB charging while the laptop is off, power on when the lid opens, turn Samsung control off |

**Charge to 100 % once** lifts the limit for one charge. The limit comes back when the battery is full or the charger is unplugged, also after a restart in between.

## Performance mode in one place

You can set the mode in the app, in the **battery panel** in the bar (four buttons instead of Omarchy's three), and with the keyboard's mode key. All three stay in sync.

- Linux has no free fan curve on these laptops. The four modes are what the firmware offers, the same as on Windows.
- `power-profiles-daemon` only knows three modes, and Omarchy switches it on boot and when the charger goes in or out.
  - So the setup keeps the daemon off the platform profile (it still tunes the CPU), and Tuneup's background service keeps the mode you chose.
  - Quiet runs the CPU on *balanced*.
- The battery panel is Omarchy's own, with the buttons going through Tuneup. It is in the bar only while Samsung control is active. Setting up puts it there; turning off puts Omarchy's back.

## One-time setup

Writing these settings needs root once. Set it up in the installer, on the page (**Set it up**, password dialog), or in a terminal:

```bash
tuneup samsung setup
```

It installs:

| File | Why |
|---|---|
| `/etc/udev/rules.d/90-tuneup-samsung.rules` | hands the charge limit, the platform profile and the firmware switches to your user |
| `/etc/systemd/system/power-profiles-daemon.service.d/tuneup.conf` | starts `power-profiles-daemon --block-driver platform_profile` |

**Turn off Samsung control** (under Advanced, or `tuneup samsung teardown`) undoes it:
- both files go, and the settings belong to root again,
- Omarchy gets its battery panel and the performance mode back,
- a running full charge ends at the old limit.

## Commands

```bash
tuneup samsung status        # everything as JSON
tuneup samsung setup         # turn Samsung control on (password once)
tuneup samsung teardown      # turn it off again
tuneup samsung limit 80      # charge limit
tuneup samsung full-once on  # charge to 100 % once
tuneup power list            # modes, the active one marked (used by the battery panel)
tuneup power set quiet       # low-power | quiet | balanced | performance
```

Settings are saved in `~/.config/tuneup/config.json` under `samsung`.
