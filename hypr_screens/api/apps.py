"""App to desktop: which apps always start on which desktop (app_desktops.py)."""
import copy

from hypr_screens import app_desktops, config, keybinds, scratch
from hypr_screens.api.core import endpoint, need, settings


def view(cfg: dict) -> dict:
    """{scratch (the scratch desktops are on), max, desktops: {key: [{id, name, icon, mode}]}}."""
    installed = app_desktops.entries(cfg.get("language", "en"))
    shown = {}
    for key, apps in app_desktops.normalize(cfg.get("app_desktops")).items():
        shown[key] = [{**app_desktops.view_app(app, (installed.get(app["id"]) or {}).get("iconName", "")),
                       "installed": app["id"] in installed} for app in apps]
    return {"scratch": scratch.enabled(cfg), "max": app_desktops.MAX_APPS, "desktops": shown}


@endpoint
def app_desktops_state() -> dict:
    return view(settings())


@endpoint
def installed_apps() -> list:
    """Every app of the launcher: [{id, name, icon}], by name."""
    apps = app_desktops.entries(settings().get("language", "en")).values()
    return sorted((app_desktops.view_app(app, app["iconName"]) for app in apps),
                  key=lambda app: (app["name"].casefold(), app["id"]))


@endpoint
def set_app_desktop(desktop: str, apps: list) -> dict:
    """The apps of one desktop ("scratch:1".."scratch:10", "desk:1".."desk:10"):
    [{id, mode: "tile" | "float"}], at most 5. An app given here leaves any other desktop."""
    need(app_desktops.parse_key(desktop) is not None, "bad_value", f"unknown desktop: {desktop!r}")
    need(isinstance(apps, list) and len(apps) <= app_desktops.MAX_APPS, "bad_value",
         f"apps must be a list of at most {app_desktops.MAX_APPS}")
    need(all(isinstance(a, dict) and isinstance(a.get("id"), str) and a.get("mode", "tile") in app_desktops.MODES
             for a in apps), "bad_value", "each app must be {id, mode: tile | float}")
    ids = [a["id"] for a in apps]
    need(len(set(ids)) == len(ids), "bad_value", "an app can be on a desktop once")
    installed = app_desktops.entries(settings().get("language", "en"))
    before = []

    def mutate(cfg):
        before.append(copy.deepcopy(cfg))
        current = app_desktops.normalize(cfg.get("app_desktops"))
        known = {app["id"]: app for listed in current.values() for app in listed}
        chosen = []
        for wanted in apps:
            source = installed.get(wanted["id"]) or known.get(wanted["id"])
            need(source is not None, "bad_value", f"no such app: {wanted['id']!r}")
            chosen.append({"id": source["id"], "name": source["name"], "classes": source["classes"],
                           "mode": wanted.get("mode", "tile")})
        for key in list(current):
            current[key] = [app for app in current[key] if app["id"] not in ids]
        current[desktop] = chosen
        cfg["app_desktops"] = {key: listed for key, listed in current.items() if listed}
        return cfg["app_desktops"] != before[0].get("app_desktops")
    with config.locked():  # the Lua file follows the settings, whoever else writes
        cfg = config.update(mutate)
        changed = cfg["app_desktops"] != before[0].get("app_desktops")
        if changed:
            keybinds.write(cfg)
    if changed:
        keybinds.go_live(before[0], cfg)
    return view(cfg)
