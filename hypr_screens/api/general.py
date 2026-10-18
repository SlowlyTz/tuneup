"""Language, translations, about, links and the theme for the page."""
import subprocess
from pathlib import Path

from hypr_screens import brand, config, i18n, updates
from hypr_screens import theme as theme_mod
from hypr_screens import widgets as widgets_mod
from hypr_screens.api.core import ApiError, endpoint, need

DOCS_URL = brand.DOCS_URL


def open_uri(uri: str) -> None:
    try:
        subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as error:
        raise ApiError("unavailable", f"cannot open {uri}: {error}") from error


def language_view(code: str) -> dict:
    return {"code": code, "items": [{"code": c, "name": n} for c, n in i18n.LANGUAGES.items()]}


@endpoint
def language() -> dict:
    return language_view(config.load()["language"])


@endpoint
def set_language(code: str) -> dict:
    need(code in config.LANGUAGE_CODES, "bad_value", f"language must be one of {config.LANGUAGE_CODES}")
    cfg = config.update(lambda fresh: fresh.__setitem__("language", code))
    i18n.set_language(code)
    widgets_mod.export(cfg)  # the widgets' own texts and date format
    return language_view(code)


@endpoint
def translations() -> dict:
    """{english text: translation} for the chosen language ({} for English)."""
    code = config.load()["language"]
    return {"code": code, "texts": i18n.load_table(code)}


@endpoint
def about() -> dict:
    folder = config.config_file().parent
    home = Path.home()
    shown = f"~/{folder.relative_to(home)}" if folder.is_relative_to(home) else str(folder)
    return {"version": updates.current_version(), "configDir": shown, "configPath": str(folder),
            "configFile": str(config.config_file()), "guideUrl": DOCS_URL, "repoUrl": brand.REPO_URL,
            "releasesUrl": brand.RELEASES_URL}


@endpoint
def open_guide() -> dict:
    open_uri(DOCS_URL)
    return {"ok": True}


@endpoint
def open_config_folder() -> dict:
    folder = config.config_file().parent
    folder.mkdir(parents=True, exist_ok=True)
    open_uri(folder.as_uri())
    return {"ok": True}


@endpoint
def theme() -> dict:
    """The Omarchy theme for the page: its colors, light or dark, font, rounding."""
    colors = theme_mod.palette()
    mode = colors.pop("mode")
    return {"mode": mode, "colors": colors, "font": theme_mod.font(), "rounding": theme_mod.rounding()}
