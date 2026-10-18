"""Omarchy look for the settings window: colors, font and corners of the menu.

The active Omarchy theme (hypr_screens.theme) turned into GTK CSS that
recolors libadwaita through its named colors.
"""
# The theme itself is read by the backend (no GTK needed); re-exported here.
from hypr_screens.theme import FALLBACK, HEX, font, palette, read_toml, rounding, theme_dir  # noqa: F401


def css(colors: dict, radius: int = 0, family: str = "monospace") -> str:
    bg = colors["menu_background"]
    fg = colors["menu_text"]
    accent = colors["accent"]
    raised = colors["lighter_background"]
    muted = colors["dark_foreground"]
    return f"""
@define-color window_bg_color {bg};
@define-color window_fg_color {fg};
@define-color view_bg_color {bg};
@define-color view_fg_color {fg};
@define-color headerbar_bg_color {bg};
@define-color headerbar_fg_color {fg};
@define-color sidebar_bg_color {bg};
@define-color sidebar_fg_color {fg};
@define-color card_bg_color {raised};
@define-color card_fg_color {fg};
@define-color dialog_bg_color {bg};
@define-color dialog_fg_color {fg};
@define-color popover_bg_color {raised};
@define-color popover_fg_color {fg};
@define-color accent_bg_color {accent};
@define-color accent_fg_color {bg};
@define-color accent_color {accent};
@define-color destructive_bg_color {colors["red"]};
@define-color destructive_color {colors["red"]};
@define-color success_color {colors["green"]};

window, dialog, popover, .card, button, entry, row, list, .navigation-sidebar {{
  font-family: "{family}";
}}
.card, list.boxed-list, button, popover > contents, dialog .dialog-contents {{
  border-radius: {radius}px;
}}
list.boxed-list {{ border: 1px solid alpha({fg}, 0.15); }}
.navigation-sidebar row {{ border-radius: {radius}px; padding: 10px 12px; }}
.navigation-sidebar row:selected {{ background: alpha({fg}, 0.08); color: {accent}; }}
.page-title {{ font-size: 1.4em; font-weight: bold; }}
.hint {{ color: {muted}; }}
.page-footer {{ padding: 2px 0; }}
.sidebar-section {{ font-size: 0.8em; font-weight: bold; color: {muted}; padding: 16px 14px 4px 14px; }}
.sidebar-separator {{ margin: 10px 12px; background: alpha({fg}, 0.1); }}
.result-path {{ font-size: 0.82em; }}
.search-results row {{ padding: 8px 12px; }}
.search-hit {{ background: alpha({accent}, 0.18); box-shadow: inset 0 0 0 2px alpha({accent}, 0.7);
              transition: background 300ms, box-shadow 300ms; }}
.status-on {{ color: {colors["green"]}; }}
.status-off {{ color: {muted}; }}
.keycap {{ padding: 4px 10px; min-width: 150px; }}
.capture {{ font-size: 1.3em; padding: 18px; }}
"""
