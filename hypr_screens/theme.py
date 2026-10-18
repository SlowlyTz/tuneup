"""The active Omarchy theme: its colors, light or dark, the monospace font and
the window rounding -- for the settings window and the desktop widgets.

Reads $XDG_STATE_HOME/omarchy/current/theme (colors.toml, shell.toml). Falls
back to a neutral dark palette without Omarchy. Needs no GTK.
"""
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

FALLBACK = {
    "background": "#1e1e2e",
    "foreground": "#cdd6f4",
    "accent": "#89b4fa",
    "selection": "#45475a",
    "lighter_background": "#313244",
    "dark_foreground": "#6c7086",
    "red": "#f38ba8",
    "green": "#a6e3a1",
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
COMMAND_SECONDS = 3


def theme_dir() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "omarchy" / "current" / "theme"


def read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def palette(directory: Path | None = None) -> dict:
    """Theme colors plus "mode" ("dark"/"light"); the [menu] section of
    shell.toml wins where it has plain hex values."""
    directory = directory or theme_dir()
    colors = dict(FALLBACK)
    toml = read_toml(directory / "colors.toml")
    colors.update({k: v for k, v in toml.items() if isinstance(v, str) and HEX.match(v)})
    colors["mode"] = "light" if toml.get("mode") == "light" else "dark"
    menu = read_toml(directory / "shell.toml").get("menu", {})
    menu = menu if isinstance(menu, dict) else {}
    colors["menu_background"] = menu.get("background") if HEX.match(str(menu.get("background", ""))) else colors["background"]
    colors["menu_text"] = menu.get("text") if HEX.match(str(menu.get("text", ""))) else colors["foreground"]
    return colors


def rounding() -> int:
    """Hyprland's window rounding in pixels (0 when it cannot be asked)."""
    try:
        option = json.loads(subprocess.run(
            ["hyprctl", "-j", "getoption", "decoration:rounding"], capture_output=True, text=True, check=False,
            timeout=COMMAND_SECONDS,
        ).stdout)
        return int(option.get("int", 0))
    except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError, AttributeError):
        return 0


def font() -> str:
    """The monospace font fontconfig picks (Omarchy sets it)."""
    try:
        family = subprocess.run(
            ["fc-match", "-f", "%{family[0]}", "monospace"], capture_output=True, text=True, check=False,
            timeout=COMMAND_SECONDS,
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        family = ""
    return family or "monospace"
