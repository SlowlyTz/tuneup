# The settings window

Opens from the tray icon (or `hypr-screens settings`). Already open on another desktop – or minimized – it comes to the desktop you are on, like hypr-minimizer brings a window back. Closing it ends the window completely; the tray icon stays.

The window is a web page (`hypr_screens/web/`) in a WebKit view: it takes the colors of the Omarchy theme and the language chosen under General. Every change is saved and applied at once, with **Undo** in the message at the bottom. Two kinds of change ask again after 15 seconds, because a wrong one can leave you without a usable screen: a screen's rotation, scaling, resolution or position, and the window look after **Apply**.

| Page | What is there |
|---|---|
| **Home** | the screens in small with **Swap**, volume, battery and performance mode, the widgets on and off |
| **Screens** | the screens as they stand on the desk – drag one to another edge of the laptop, the mouse then crosses there. Below, for the screen you clicked: rotation, scaling, resolution and refresh rate, "Always shows the same desktop". Each setting can apply always or only while a certain other screen is connected (the chip "Always ▾"). Under **More**: which screen is fixed for new monitors, favorite, forget. Screens known from before but not connected are in a row below the picture. |
| **Keyboard** | the keys that hide and bring back windows, two per action; click one and press the new keys. The desktop keys (Super + 1…0 through hypr-screens). |
| **Windows** | a live preview, presets, gaps, corners, border, transparency; under **More** blur, animation speed, own border colors and see-through apps. Changes show in Hyprland while you edit; **Apply** keeps them, **Discard** brings the old look back. |
| **Widgets** | every widget with a small preview and a switch, the layouts as chips, **Arrange on the desktop**. A widget's page has the tabs *Content* and *Where & when*. Colors, font, effect and card are set on the desktop while arranging (see [Personalization](personalization.md)). |
| **Sound** | volume per device and app, the default device, Force Mute, the output of each app |
| **Camera** | the turned virtual camera with a preview |
| **Battery & power** | charge limit, performance mode, keyboard light and device settings (only on a Galaxy Book) |
| **General** | language, the full guide, the settings folder, the version |

Narrower than 900 pixels, the sidebar shrinks to its icons.

## Search

The field at the top of the sidebar, or Ctrl+F. It finds pages and single settings by their names and by other words for them ("volume" finds Sound, "monitor" finds Screens). Pick a result and the page opens, scrolls to the setting – unfolding **More** if it is in there – and marks it for a moment.

## Keys

| Key | Does |
|---|---|
| Ctrl+F | search |
| ↑/↓, Enter | choose and open a result |
| ←/→ | move within a row of buttons (rotation, scaling, …) |
| Esc | close a menu or dialog, empty the search |
| Ctrl+Q, Ctrl+W | close the window |

## Opened in a browser

`hypr_screens/web/index.html` also opens in a plain browser: without the app around it, `mock.js` fills it with made-up screens, devices and widgets, so the page can be worked on without touching anything. `?lang=de` picks the language, `?mode=light` the light colors. What the page can ask the app is in [`hypr_screens/web/API.md`](../hypr_screens/web/API.md).
