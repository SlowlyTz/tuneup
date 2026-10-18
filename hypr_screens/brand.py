"""Who the app is: its name, ids, links and the names of its files.

The app is Tuneup; it was called hypr-screens before (the Python package keeps
that name, it is internal). OLD_* are the names of the files hypr-screens
made, so migrate.py can move them and uninstalling finds them.
"""
import shutil
from pathlib import Path

NAME = "Tuneup"
COMMAND = "tuneup"
ALIASES = ("hypr-screens",)  # old command, kept as a symlink
TAGLINE = "The settings app Omarchy is missing"
APP_ID = "io.github.slowlytz.Tuneup"
OLD_APP_ID = "io.github.slowlytz.HyprScreens"
REPO_URL = "https://github.com/SlowlyTz/tuneup"
RELEASES_URL = f"{REPO_URL}/releases"
DOCS_URL = f"{REPO_URL}/tree/master/docs"
CLONE_URL = f"{REPO_URL}.git"

# Folders below ~/.config and $XDG_RUNTIME_DIR, and the Hyprland Lua module.
DIR = "tuneup"
OLD_DIR = "hypr-screens"
LUA_MODULE = "tuneup"
OLD_LUA_MODULE = "hypr_screens"

ROOT = Path(__file__).resolve().parent.parent  # the checkout (or the clone in ~/.local/share/tuneup)


def command() -> str:
    """The command the generated Lua runs: tuneup, or hypr-screens on a system
    that has only the old one on $PATH (not updated yet)."""
    return next((name for name in (COMMAND, *ALIASES) if shutil.which(name)), COMMAND)
