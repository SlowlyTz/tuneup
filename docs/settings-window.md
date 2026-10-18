# The settings window

Opens from the tray icon (or `hypr-screens settings`). Already open on another desktop – or minimized – it comes to the desktop you are on, like hypr-minimizer brings a window back. Closing it ends the window completely; the tray icon stays.

The window is a web page (`hypr_screens/web/`) in a WebKit view: it takes the colors of the Omarchy theme and the language chosen under General. Every change is saved and applied at once, with **Undo** in the message at the bottom. Two kinds of change ask again after 15 seconds, because a wrong one can leave you without a usable screen: a screen's rotation, scaling, resolution or position, and the window look after **Apply**.

| Page | What is there |
|---|---|
| **Home** | the screens in small with **Swap**, volume, battery and performance mode, the widgets on and off |
| **Screens** | the screens as they stand on the desk – drag one to another edge of the laptop, the mouse then crosses there. Below, for the screen you clicked: rotation, scaling, resolution and refresh rate, "Always shows the same desktop". Each setting can apply always or only while a certain other screen is connected (the chip "Always ▾"); a setting that is not set shows dashed what Hyprland does now. Right below the picture: which screen is fixed for new monitors (for all screens). Under **Advanced**: favorite, forget. Screens known from before but not connected are in a row below the picture. |
| **Keyboard** | the keys that hide and bring back windows, two per action; click one and press the new keys. The desktop keys (Super + 1…0 through hypr-screens). |
| **Windows** | a live preview, presets, gaps, corners, border, transparency; under **Advanced** blur, animation speed, own border colors and see-through apps. Changes show in Hyprland while you edit; **Apply** keeps them, **Discard** brings the old look back. |
| **Widgets** | every widget with a small preview and a switch, the layouts as chips, **Arrange on the desktop**. A widget's page has the tabs *Content* and *Where & when*. Colors, font, effect and card are set on the desktop while arranging (see [Personalization](personalization.md)). |
| **Sound** | volume per device and app, the default device, Force Mute, the output of each app |
| **Camera** | the turned virtual camera ("Rotated Camera") with a preview, and the one-time setup |
| **Battery & power** | charge limit, performance mode, keyboard light and device settings (only on a Galaxy Book) |
| **General** | language, **Keep my settings** (another app changes a setting made here – hypr-screens sets it back; with the last corrections), the full guide, the settings folder, the version |

Narrower than 900 pixels, the sidebar shrinks to its icons.

## Search

The field at the top of the sidebar, or Ctrl+F. It finds pages and single settings by their names and by other words for them ("volume" finds Sound, "monitor" finds Screens). Pick a result and the page opens, scrolls to the setting – unfolding **Advanced** if it is in there – and marks it for a moment.

## Keys

| Key | Does |
|---|---|
| Ctrl+F | search |
| ↑/↓, Enter | choose and open a result |
| ←/→ | move within a row of buttons (rotation, scaling, …) |
| Esc | close a menu or dialog, empty the search |
| Ctrl+Q, Ctrl+W | close the window |

## Opened in a browser

The page also runs in a plain browser: without the app around it, `mock.js` fills it with made-up screens, devices and widgets, so it can be worked on without touching anything. It is made of ES modules, which browsers only load over http (not from `file://`), so serve the package folder (the mock reads the translations from `../locales.json`):

```bash
python -m http.server 8765 -d hypr_screens
# then open http://127.0.0.1:8765/web/index.html?lang=de
```

`?lang=de` picks the language, `?mode=light` the light colors. What the page can ask the app is in [`hypr_screens/web/API.md`](../hypr_screens/web/API.md).

## How the page is built

`index.html` loads `bridge.js` (the line to Python, and the theme's colors), `mock.js` when there is no app, then the module `app.js`:

| Folder | What is in it |
|---|---|
| `core/` | the state and its loaders, the API, the texts (`t()`), numbers and errors, the pages and the route, the render and its handlers, one change with Undo |
| `ui/` | icons, the building blocks of a page (row, block, section), the controls, the popover with its list, the dialog, the toast |
| `pages/` | one module per page; Screens, Keyboard, Windows and Widgets have a folder (the arrangement, the key recording, the look's preview, the schema-driven settings, layouts, previews) |
| `shell/` | the navigation and the render of the page, the delegated events, the search, the live updates |
| `css/` | tokens, base, components, pages, and the narrow window last |

Every page is a function that returns HTML; its controls register their handlers under a stable key, and after each change the page is rendered again with the focus kept.
