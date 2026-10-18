# hypr-screens settings window: the `window.api` contract

The page (`index.html`, `app.js`) talks only to `window.api`. In the real
window the WebKit bridge puts the Python backend `hypr_screens/api/` there;
in a plain browser `mock.js` stands in with the **same shapes** (its data was
produced by `hypr_screens.api` against a fake Hyprland).

- `api.someMethod(a, b)` calls `hypr_screens.api.some_method(a, b)`
  (camelCase → snake_case, positional JSON arguments). `api.call(name, args)`
  does exactly this for the bridge; `api.METHODS` lists every method.
- Every method is async and resolves with plain JSON.
- A failure rejects with an error carrying `code` (stable, below) and
  `message` (English, fit for a toast). The mock throws `ApiError` (an
  `Error` with `.code`), so `err.message` works in both.
- Calls run one at a time on a worker thread. Some take long and hold the
  queue: `setupCamera`, `setSamsung("active", …)`, `installCava` (password
  dialogs), `arrangeWidgets` (up to 5 s), `resetLook` (~1 s), and any screen
  setting (it applies the monitors; a reload waits ½ s).
- Labels the backend sends (key titles, widget schema, choices) are the
  **English i18n source texts**; `translations()` gives the table for the
  chosen language.
- Arguments that JSON turns `undefined` into `null`: `null` always means
  "leave as is" where a method has an optional argument (`when`).

## Error codes

| code | when |
| --- | --- |
| `bad_args` | wrong number of arguments |
| `bad_value` | a value is not allowed (message says what is) |
| `unknown_method` | `call()` with a name that does not exist |
| `config_unreadable` | `~/.config/hypr-screens/config.json` exists but is not valid; nothing is written over it |
| `unknown_screen` / `unknown_device` / `unknown_widget` / `unknown_layout` | that id/key/name is not known (any more) |
| `connected_screen` | forgetting a screen that is plugged in |
| `internal_screen` | forgetting the laptop screen |
| `not_connected` | dragging a screen that is not connected |
| `no_external` | swapping without an external monitor |
| `conflict` | renaming a layout to a name that exists |
| `force_muted` | changing the volume of / unmuting a force-muted device |
| `inactive` | a sound device whose card profile is off (→ `switchOnDevice`) |
| `not_set_up` | Samsung writes before the one-time setup |
| `not_plugged` | Samsung "charge to 100 % once" without the charger |
| `unavailable` | not a Galaxy Book / no keyboard light / `xdg-open` missing |
| `cancelled` | a password dialog was cancelled or the setup failed |
| `nothing_to_arrange` | arranging with no widget on the desktop |
| `not_ready` | the widget plugin did not answer (just switched on) – try again |
| `apply_failed` | the setting was **saved**, but making it live failed |
| `internal` | anything unexpected (`"TypeError: …"`) |

---

## Screens

### `screens()` → `Screen[]`

Every screen ever connected: the laptop first, then favorites, then the
others; connected ones first within each group. Connected monitors are
recorded on every call.

```js
{
  id: "HP Inc.|HP 32f|3CM1230QVW",   // EDID make|model|serial – NOT "hp32f"/"laptop"
  name: "HP 32f",                     // the laptop is "Laptop"
  description: "HP Inc. HP 32f 3CM1230QVW",
  connector: "DP-3", laptop: false, connected: true, favorite: false,
  lastSeen: "2026-10-18",
  modes: [                            // grouped by resolution, as the screen offers them
    { w: 1920, h: 1080, rates: [75, 60], modes: ["1920x1080@75.00", "1920x1080@60.00"], preferred: true },
    { w: 1680, h: 1050, rates: [59.95], modes: ["1680x1050@59.95"], preferred: false }
  ],
  hypr: {                             // what Hyprland uses now; null while not connected
    rotation: 0, flipped: false, scale: 1, mode: "1920x1080@60.00",
    one_desktop: false                // true = this screen is the fixed one right now
  },
  settings: {                         // the laptop has no "position"
    rotation:    { value: null, when: [], active: false },   // null = not set ("Von Hyprland: …")
    scale:       { value: 1.25, when: [], active: true },
    mode:        { value: null, when: [], active: false },
    position:    { value: "above", when: [], active: true }, // "left" | "right" | "above" | "below"
    one_desktop: { value: true, when: ["Samsung Display Corp.|0x4159|"], active: true }
  },
  position: { x: 0, y: 0, w: 1920, h: 1080 },  // live, layout pixels (scaled, turned); null if not connected
  side: "above",                      // = settings.position.value
  summary: "above laptop · 1.25×"     // English one-liner of the settings
}
```

Values: `rotation` 0/90/180/270; `scale` `"auto"` or 0.25–4; `mode`
`"preferred"` or `"WxH@rate"` (best: one of `modes[].modes`); `one_desktop`
true/false.

`when` (the condition): `[]` = always, `[id]` = only while that other
screen is connected. **The real model has one screen at most**, not a list of
several. `active` = the value is set and its condition holds now.

### `setScreenSetting(sid, key, value, when?)` → `Screen & {applied: string[]}`

- `key`: `rotation | scale | mode | position | one_desktop`; `value: null` unsets
  (its condition goes with it).
- `when`: `null`/left out keeps the condition, `[]` = always, `[otherId]`.
- Saves, then applies everything (`engine.sync`: monitor rules, desktops).
  `applied` lists the connectors that got a new rule (empty when nothing
  changed on screen) – use it for "Keep this setting?".
- **Position from a drag**: `value` may be `{x, y}` – the dragged screen's
  top-left in the same coordinates as `position`. It is turned into the
  nearest side of the laptop (by the rectangles' middles); the backend then
  places it edge to edge with the laptop, centred along that edge
  (`apply.layout`), so the result may differ a little from the drop point –
  re-read `position`. Dragging the **laptop** sets the opposite side on the
  one other connected screen (with more than one: `bad_value`). Without a
  laptop the other screen (first by connector) is the anchor.
- Errors: `unknown_screen`, `bad_value`, `not_connected`, `apply_failed`.

### `forgetScreen(sid)` → `{ok: true}`
Removes a screen that is not connected, and every condition naming it.
Errors: `connected_screen`, `internal_screen`, `unknown_screen`.

### `toggleFavorite(sid)` → `Screen`

### `fixedStatus()` → `Fixed`
```js
{ fixed: "Samsung Display Corp.|0x4159|", desk: "HP Inc.|HP 32f|3CM1230QVW",
  role: "panel",            // "panel" (laptop fixed) | "external" | null (no fixed screen)
  swapped: false,           // a temporary swap is in force (until unplugged)
  panel: "<laptop id>", external: "<external id>", canSwap: true, fixedWorkspace: 99 }
```
`fixed`/`desk` are `null` while there is no fixed screen.

### `swapFixed()` → `Fixed`
Swaps which screen is fixed until the monitor is unplugged. Error `no_external`.

## Keys

### `keys()`
```js
{
  actions: [{ id: "stash", title: "Hide window", desc: "Hides the active window.",
              slots: ["SUPER + M", null] }, …],   // ids: minimizer_menu stash stash_others pop pop_all undo
  hyprBinds: { "SUPER + Q": "Close window", "SUPER + 1": "Switch to workspace 1", … },  // Hyprland's own, not ours
  options: { desktop_keys: false, default_fixed: "off" },   // "off" | "external" | "panel"
  defaultFixedChoices: [{ value: "off", label: "Off – both screens have desktops" }, …]
}
```

### `setKey(action, slot, combo)` → `Action & {conflicts: string[]}`
`slot` 0/1; `combo` like `"SUPER + SHIFT + PERIOD"` (normalized), `""`/`null`
removes. Another action of ours with the same key loses it. `conflicts` names
the Hyprland binds it now replaces (while hypr-screens runs). The Lua file is
rewritten and the keys go live at once.

### `beginKeyCapture()` / `endKeyCapture()` → `{ok: true}` (new)
Call around the "press the new keys" dialog: Hyprland switches to an empty
keymap, so combos it has bound (Super+Q closes the window!) reach the page.
Esc always drops back to the normal keymap.

### `setOption(name, value)` → `options`
`desktop_keys` true/false (rewrites and reloads the keys, then syncs) or
`default_fixed` `"off" | "external" | "panel"`.

## Window look

### `look()`
```js
{
  values: { gapsIn: 5, gapsOut: 10, rounding: 10, border: 2,
            blur: true, blurSize: 6, blurPasses: 2,          // blurSize 1–20, blurPasses 1–4
            activeOpacity: 1.0, inactiveOpacity: 1.0,         // 0.3–1.0 (not percent)
            animSpeed: 1.0,                                   // 0.25–3, 1 = Omarchy's speed
            borderColors: null,                               // null = the theme's; or ["#rrggbb[aa]", "#…"]
            borderAngle: 0,                                   // gradient angle of borderColors
            apps: [{ class: "Alacritty", active: 0.9, inactive: 0.8 }] },  // see-through apps
  saved: { … only what the user set (same keys) … },
  previewing: false,
  apps: [{ id: "Alacritty", name: "Alacritty" }, …],          // window classes open now
  presets: [{ name: "Clean" | "Soft" | "Glass", values: {…} }],
  ranges: { gapsIn: {min, max, step}, …, animSpeed, borderAngle, appOpacity },
  themeBorder: { colors: ["#89b4faff", "#89b4faff"], angle: 0 }   // to start own colors from
}
```
`values` = what Hyprland shows now with the saved values on top (during a
preview: the preview).

### `previewLook(values)` → `{ok, values, reloaded}`
Shows the look live without saving. `values` may be all or some keys; the
others stay as shown (`borderColors: null` goes back to the theme's). Adding or
removing see-through apps (or dropping own border colors) needs a Hyprland
reload (`reloaded: true`) – don't send those on every slider move.

### `revertLook()` → `look()` (new)
Ends a preview: the look from before it is shown again ("Verwerfen").

### `saveLook(values)` → `look()`
Shows (if needed) and keeps the look; it is written into the Lua file.

### `resetLook()` → `look()` (new)
Forgets the own look; Omarchy's theme decides again (Hyprland reloads).

## Sound

### `soundState()`
```js
{
  outputs: [{ key: "alsa_card.pci-0000_00_1f.3:[Out] Speaker",   // card:port, survives profile switches
              kind: "sink", name: "Laptop speakers", sub: "HD Audio",
              icon: "speaker",            // speaker | headphones | tv | mic
              volume: 42, muted: false, isDefault: true, forceMute: false,
              active: true,               // false: the card's profile does not drive it → switchOnDevice
              connected: true,            // false: force-muted device that is not there now
              node: "alsa_output.…" }],
  inputs: [ … same, kind: "source", icon: "mic" … ],
  apps: [{ key: "app:51", index: 51, name: "Spotify", sub: "", icons: ["spotify-client", "spotify"],
           volume: 80, muted: false, paused: false, output: "<output key>" | null }]
}
```
Volumes change from outside (keys, apps): poll about once a second while the
page shows. App keys change when an app restarts its stream.

- `setVolume(key, 0–100)` → the item (or `null` if it is gone). Errors
  `force_muted`, `inactive`, `unknown_device`. Raising the volume does **not**
  unmute (the mock did).
- `setMute(key, on)` → the item. Unmuting a force-muted device: `force_muted`.
- `setDefault(key)` → `soundState()`.
- `setForceMute(key, on)` → the item, or `null` when an unplugged device is
  switched off (it leaves the list). On: muted and 0 % for good (also after
  restarts). Off: back to the volume from before.
- `setAppOutput(appKey, outputKey)` → the app. The output must be `active`.
- `switchOnDevice(key)` → `soundState()` (new): switches the sound card to the
  profile that drives this device; the default devices stay.

## Camera

### `camera()`
```js
{ installed: false,        // the one-time setup (v4l2loopback) is done
  enabled: true, rotation: 0, rotations: [0, 90, 180, 270],
  state: null,             // "off" | "idle" | "live" | "busy" | null (watcher not running)
  inUse: false, users: 0,  // apps using the virtual camera
  device: "Integrated Camera", hasCamera: true, virtualName: "Rotated Camera" }
```
- `setCamera(enabled, rotation)` → `camera()`.
- `setupCamera()` → `camera()`; asks for the password (pkexec). Error `cancelled`.
- `cameraPreview()` → `{image: "data:image/jpeg;base64,…", time}` or
  `{image: null, reason: "not_set_up" | "off" | "starting"}` (new). Call it a
  few times a second while the preview shows; each call also asks the
  watcher's feeder to keep the camera running. Before the setup there is no
  preview (the old window ran its own ffmpeg; the API does not start processes).

## Samsung Galaxy Book

### `samsung()`
On other laptops: `{available: false, active: false}` only.
```js
{ available: true, active: true, writable: true,
  level: 76, status: "Discharging", charging: false, plugged: false,
  health: 94, cycles: 212, power: 8.4,            // power in W; any of these may be null
  remainingMinutes: 320, fullInMinutes: null,     // from the battery's own numbers; null if unknown
  chargeLimit: 80,          // the threshold in force (100 while fullOnce)
  wantedLimit: 80,          // the configured limit
  fullOnce: false,
  mode: "balanced", modes: [{ value: "low-power", label: "Saver" }, { value: "quiet", … }, …],
  fanRpm: null, fanRunning: false,   // Galaxy Books report only on/off, no speed
  cpuTemp: 52, kbdLight: 2, kbdMax: 3,                // null without a keyboard light
  usbCharging: false, lidPower: true, attributesWritable: true }   // null if the firmware lacks one
```

### `setSamsung(field, value)` → `samsung()`
| field | value |
| --- | --- |
| `active` | true: one-time setup, false: give everything back to Omarchy (password; `cancelled`) |
| `chargeLimit` | 50–100 |
| `fullOnce` | true/false (true needs the charger: `not_plugged`) |
| `mode` | one of `modes[].value`: `low-power`, `quiet`, `balanced`, `performance` |
| `usbCharging`, `lidPower` | true/false |
| `kbdLight` | 0…`kbdMax` |

Writes before the setup: `not_set_up`.

## Widgets

### `widgets()` → `Widget[]`
Kinds, in this order: `visualizer lyrics clock system nowplaying weather
calendar battery network disk`.
```js
{ kind: "clock", name: "Clock", description: "A big clock with the date.",
  enabled: true, placed: true,     // placed: arranged at least once (false: sits in the middle)
  onDesktop: true,                 // shows on the desktop (the visualizer may be in the bar only)
  missing: [],                     // ["cava"] for the visualizer without cava → installCava()
  content: { clock_style: "digital", hours: "24", seconds: false, date: true, weekday: true,
             date_format: "long", date_pattern: "", zone2: "" },
  where: { screens: "laptop", same_place: true, desktops: ["all"],
           only_empty: false, hide_on_battery: false, above: false },
  schema: [Field, …] }
```
`content`/`where` hold the **real config keys**. The look (colors, accent,
font, weight, letter spacing, effect, card, opacity, size, the gap between
bars, the lyrics' alignment/line size/scroll time) is **not** here – it is set
on the desktop while arranging.

`where`: `screens` = `"laptop" | "external" | "all" |` a known external
screen id; `desktops` = `["all"]` or a list of `"1"`…`"10"` and `"fixed"`
(the fixed screen); the visualizer also has `where: "bar" | "desktop" | "both"`.

**Field** (draw the settings from this):
```js
{ key: "date_format", group: "content",            // "content" | "where"
  type: "choice",                                  // toggle | choice | number | text | multi
  label: "Date format", default: "long",
  choices: [{ value: "long", label: "Long (3 October)" }, …],   // choice, multi
  min: 1, max: 10, step: 1, unit: "%",             // number (whole numbers)
  maxLength: 60, format: "timezone",               // text ("timezone": IANA name, "" = off)
  dynamic: true,                                   // choices depend on the machine (players, screens)
  section: "Date",                                 // fold-out row it belongs to
  enabledBy: "date",                               // only matters while that toggle is on
  showIf: { date_format: "custom" },               // only shown while that field has that value
  hint: "…" }
```
Content keys per kind:

| kind | content |
| --- | --- |
| visualizer | `player`, `bars`, `style` (bottom/mirrored/wave/dots/circle), `sensitivity`, `smoothing`, `peaks` |
| lyrics | `player`, `highlight` (line/word/off), `lines`, `hide_paused` |
| clock | `clock_style` (digital/analog/flip/words), `hours` ("24"/"12"), `seconds`, `date`, `weekday`, `date_format` (long/medium/short/iso/custom), `date_pattern`, `zone2` |
| system | `cpu`, `memory`, `temperature`, `curves` |
| nowplaying | `player`, `np_layout` (row/column), `show_cover`, `show_title`, `show_artist`, `show_album`, `show_progress`, `show_time`, `show_controls`, `hide_idle` |
| weather | `units` (c/f), `show_place`, `show_details`, `show_forecast` |
| calendar | `week_start` (monday/sunday), `show_month`, `show_weeks` |
| battery | `show_percent`, `show_remaining`, `low` |
| network | `curves` |
| disk | `show_free` |

`player`: `""` = whatever plays, else an MPRIS name like `"spotify"`
(choices: the players running now).

### `updateWidget(kind, changes)` → `Widget`
`changes = {enabled?, content?: {key: value}, where?: {key: value}}`, each
part optional and partial, checked against the schema (`bad_value` for an
unknown key or value, e.g. any look key). Saved, then live at once
(`widgets.json` export, shell plugin wiring). Switched on for the first time
it starts in the middle of the screen (`placed: false`) – offer
`arrangeWidgets()` then.

### Layouts
`layouts()` →
```js
{ current: "Desk",          // the layout the widgets match now, or null
  items: ["Desk", "Away"],
  layouts: [{ name: "Desk", screens: [], screenNames: [], auto: false, matchesNow: false }],
  connected: ["<id>", …] }  // screens connected now (for "load with these screens")
```
- `saveLayout(name)` – keeps all widgets as they are under this name (replaces one of that name).
- `loadLayout(name)` – the widgets as saved; live at once. Also returns
  `previous`: all widgets as they were before (saved or not).
- `restoreWidgets(previous)` (new) – undoes a load: the widgets back as in that
  `previous`. `bad_value` if it is not an object.
- `deleteLayout(name)` (new), `renameLayout(name, newName)` (new; `conflict`).
- `setLayoutAuto(name, on)` (new) – loads by itself whenever exactly the screens
  connected now are connected (another layout with the same screens gives them up).

All return `layouts()`; unknown names: `unknown_layout`.

### `arrangeWidgets()` → `{ok: true}`
Starts arranging on the desktop (move, resize, turn, colors, font, effects).
The overlay saves by itself. Errors `nothing_to_arrange`, `not_ready`.

### `installCava()` → the visualizer `Widget` (new)
Installs cava (password). Error `cancelled`.

## Enforcement (new)

hypr-screens keeps what it sets: the watcher (`hypr-screens watch`) audits every
5 s, and soon after events that can mean drift, and puts back only what
another app or a reload changed. An item that comes back more than 3 times in
60 s is left alone for 30 s, then 60 s, 120 s … (at most 30 min). Force mute is
never left alone. On by default.

### `enforcement()` → `Enforcement`

```js
{
  enabled: true,                 // the setting
  running: true,                 // the watcher is alive (heartbeat < 15 s old)
  fixes: [                       // newest first, at most 20; a fix repeating within 60 s shows once
    { time: 1792310400.5,        // epoch seconds
      area: "screens",           // "screens" | "desktops" | "look" | "keys" | "sound" | "samsung"
      what: "Screen arrangement",  // English source text (translate with translations())
      detail: "DP-3 moved or changed" }   // English, not translated (connector names, keys …)
  ],
  backedOff: [                   // items left alone right now, soonest end first
    { area: "look", what: "Window look", until: 1792310460.0 }
  ]
}
```

`what` is one of: `Screen arrangement`, `Screen without a picture`,
`Desktops on their screens`, `Window look`, `Shortcuts`, `Force mute`,
`Charge limit`, `Performance mode`.

### `setEnforcement(enabled)` → `Enforcement`
`enabled` must be a boolean (`bad_value`). Off: no audit (hotplug and reloads
still apply the settings; force mute and the Samsung charge limit / mode keep
working, as their own settings). A screen without a picture is still reported.

## General

- `language()` → `{code: "de", items: [{code: "en", name: "English"}, {code: "de", name: "Deutsch"}, …]}`
- `setLanguage(code)` → `language()`; also re-exports the widgets' own texts.
  The tray and the window keep their old texts until rebuilt.
- `translations()` → `{code, texts: {"English text": "translation", …}}` (new; `{}` for English).
- `about()` → `{version: "0.1.0", configDir: "~/.config/hypr-screens", configPath, configFile, guideUrl}`
- `openGuide()`, `openConfigFolder()` → `{ok: true}` (`xdg-open`; `unavailable`)
- `theme()` → `{mode: "dark" | "light", colors: {background, foreground, accent, selection,
  lighter_background, dark_foreground, red, green, menu_background, menu_text, …the theme's colors.toml},
  font: "JetBrainsMono Nerd Font", rounding: 10}` (new)

---

## What app.js expects today but the real API does differently

Screens
1. Screen ids are EDID strings (`"HP Inc.|HP 32f|3CM1230QVW"`), not `"laptop"`/`"hp32f"`.
   `UI.sel = "laptop"` (start, after forgetting) must pick the screen with `laptop: true`.
2. The laptop's name is `"Laptop"`.
3. `when` holds **one** screen at most: the "Gilt" popover must be single-choice
   (`[]` or `[id]`); sending two ids is `bad_value`. A condition holds while
   that screen is connected.
4. `hypr` is `null` for screens that are not connected (`sel.hypr.mode` crashes on
   a remembered screen) – there is no "Von Hyprland" value then.
5. `position` is `{x, y, w, h}` (live, scaled and turned) and `null` when not
   connected; drags may still send `{x, y}`. The stored setting is a side
   (`settings.position`, `side`); the drop point snaps to "edge to edge,
   centred" after the apply.
6. `settings.position` exists for external screens; every setting has `active`.
7. `modes[].rates` are real rates (59.95, 60.02 …) and `modes[].modes` the exact
   strings; `hypr.mode` is `"1920x1080@60.00"`. Sending `"WxH@<max rate>"` works.
8. `setScreenSetting` resolves with the screen plus `applied`.
9. `fixedStatus()` has `fixed`/`desk` `null` when no screen is fixed, plus
   `role`, `panel`, `external`, `canSwap`, `fixedWorkspace`.

Keys
10. `options.default_fixed` is `"off" | "external" | "panel"` – the UI sends `"laptop"`.
11. Titles/descriptions are English source texts (translate via `translations()`);
    `desc` is always a string; default keys differ from the mock (`stash` = `SUPER + M` …).
12. Call `beginKeyCapture()`/`endKeyCapture()` around the capture dialog.

Window look
13. `transparency` (0–60 %) is gone: `activeOpacity`/`inactiveOpacity` (0.3–1.0).
14. `anim` ("off"/"fast"/"normal"/"slow") is gone: `animSpeed` (0.25–3; there is no "off").
15. `customColors`/`activeColor`/`inactiveColor` are gone: `borderColors` (`null` =
    theme, or two colors of a gradient on the **active** border) + `borderAngle`.
    There is no own inactive color.
16. `transparentApps: [id]` is gone: `apps: [{class, active, inactive}]` (own
    opacity per app); `look().apps` are window classes (`{id, name}` = class).
17. `blurSize` is 1–20 and `blur` switches it (0 is not "off"); `blurPasses` 1–4.
18. Presets are `Clean`/`Soft`/`Glass` from `look().presets` (the UI's own preset values differ).
19. "Verwerfen" must call `revertLook()` (previewLook with the old values is not
    the same: it does not end the preview).

Sound
20. Keys are PipeWire keys (`"alsa_card…:[Out] Speaker"`, apps `"app:<index>"`).
21. `icon` is `speaker | headphones | tv | mic`; new `kind`, `active`, `connected`, `node`;
    apps have `index`, `icons`, `paused`, `sub`, `output` may be `null`.
22. Raising the volume does not unmute; `setForceMute(…, false)` on an unplugged
    device resolves `null` and the device leaves the list.
23. Devices with `active: false` need `switchOnDevice` before volume/default.

Camera
24. `device` may be `null`; new `state`, `users`, `hasCamera`, `virtualName`, `rotations`;
    the preview image comes from `cameraPreview()`.

Samsung
25. `mode` values are `low-power | quiet | balanced | performance` (the UI uses `"saver"`);
    take the list from `modes`.
26. `remaining` (text) is gone: `remainingMinutes` / `fullInMinutes` (numbers or `null`).
27. `fanRpm` is usually `null` (Galaxy Books report only `fanRunning`); `health`,
    `cycles`, `power`, `cpuTemp`, `kbdLight`, `kbdMax`, `usbCharging`, `lidPower` may be `null`.
28. New: `status`, `writable`, `wantedLimit`, `attributesWritable`, `modes`.

Widgets
29. Kinds are `visualizer lyrics clock system nowplaying weather calendar battery
    network disk` (`storage` is `disk`); `name` is English.
30. All `content` keys are the real ones (table above). Gone: clock `style`/`hour`/`date`
    (format)/`tz2`/`pattern` → `clock_style`/`hours`/`date_format`/`zone2`/`date_pattern`
    (`date` is now the on/off switch); calendar `weekStart: "mo"|"so"`/`weekNumbers` →
    `week_start: "monday"|"sunday"`/`show_weeks`; weather `forecast` → `show_forecast`;
    battery `percent` → `show_percent`; system/network/storage `show: [...]` → one toggle
    per part (`cpu`, `memory`, `temperature`, `curves`; network only `curves`; disk `show_free`);
    `source` (`"all"|"spotify"|"firefox"`) → `player` (`""` = whatever plays); lyrics
    `highlight` keeps `line|word|off`; visualizer `style` is
    `bottom|mirrored|wave|dots|circle` (not `bars|mirror|wave`).
31. `where.hideFullscreen` does not exist; real: `only_empty`, `hide_on_battery`, `above`,
    `same_place` (and the visualizer's `where`). `where.screens` may be a screen id.
32. Render the settings from `schema` instead of hard-coded rows.
33. New fields `description`, `placed`, `onDesktop`, `missing`; new methods
    `installCava`, `deleteLayout`, `renameLayout`, `setLayoutAuto`; `layouts()` has
    `layouts` and `connected`, and `current` may be `null`.

General
34. `about()` has `configPath`, `configFile`, `guideUrl`; the version is the package's (`0.1.0`).
35. New: `theme()`, `translations()`, `revertLook()`, `resetLook()`, `cameraPreview()`,
    `switchOnDevice()`, `beginKeyCapture()`, `endKeyCapture()`.
