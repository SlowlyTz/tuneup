"""Tuneup's own plugins: folders under plugins/ in the checkout, listed on the
"Plugins" page, installed into the Omarchy shell on request.

A plugin folder holds
  plugin.json   what the page shows and what installing does (see below)
  shell/        the Omarchy shell plugin itself (its manifest.json and QML)

plugin.json:
  id, name, description, icon (one of the page's icon names), version
  bar:       {"section": "right", "before": ["slowly.agents", ...]} -- the bar
             widget goes in front of the first of these found in that section,
             else at the start of it
  replaces:  ["omarchy.monitor", ...] (optional) -- built-in widgets the plugin
             stands in for: installing puts it exactly where the first of these
             sits in the bar and takes that one out (bar.before is then only
             the fallback); removing the plugin puts the first one back on the
             plugin's spot, unless one of them is in the bar again by then
  settings:  [{"key", "type": "bool" | "enum" | "int", "label", "default",
               "options": [{"value", "label"}] (enum), "min", "max" (int)}]
             -- kept in the settings and written onto the widget's entry in
             shell.json, where the widget reads them with setting(key, default);
             "language" (Tuneup's) is written there too
  checks:    [{"id", "label", "command": [...], "ok", "missing", "texts": {word: text}}]
             -- run on install and on the page: exit code 0 means "ok" (an
             optional extra, such as an app the plugin talks to; never a reason
             to refuse). "./script" is in the plugin's folder; the first word it
             prints picks one of "texts"
  translations: {"de": {"English text": "Übersetzung"}, ...} for the texts above

Installing links shell/ to ~/.config/omarchy/plugins/<the shell id> and puts
the widget in the bar; the settings file keeps {"installed", "settings"} per
plugin, so `tuneup setup` (every update) wires installed ones again.
"""
import json
import shutil
import subprocess
from pathlib import Path

from hypr_screens import brand, config, install

FOLDER = brand.ROOT / "plugins"
TYPES = ("bool", "enum", "int")
CHECK_SECONDS = 3


class PluginError(ValueError):
    """An unknown plugin or setting, or a value its schema does not allow."""


def folder() -> Path:
    return FOLDER


def read_manifest(path: Path) -> dict | None:
    """The plugin.json of one folder, checked; None when it is not a usable plugin."""
    try:
        data = json.loads((path / "plugin.json").read_text())
        shell = json.loads((path / "shell" / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(shell, dict) or data.get("id") != path.name:
        return None
    shell_id = shell.get("id")
    if not isinstance(shell_id, str) or not shell_id:
        return None
    settings = [s for s in data.get("settings") or [] if valid_setting(s)]
    checks = [c for c in data.get("checks") or [] if isinstance(c, dict) and isinstance(c.get("id"), str)
              and isinstance(c.get("command"), list) and c["command"] and all(isinstance(a, str) for a in c["command"])]
    bar = data.get("bar") if isinstance(data.get("bar"), dict) else {}
    return {
        "id": path.name, "shellId": shell_id, "path": path,
        "name": str(data.get("name") or path.name), "description": str(data.get("description") or ""),
        "icon": str(data.get("icon") or "plugin"), "version": str(data.get("version") or ""),
        "bar": {"section": str(bar.get("section") or "right"),
                "before": [str(b) for b in bar.get("before") or [] if isinstance(b, str)]},
        "replaces": [str(r) for r in data.get("replaces") or [] if isinstance(r, str) and r],
        "settings": settings, "checks": checks,
        "translations": data.get("translations") if isinstance(data.get("translations"), dict) else {},
    }


def valid_setting(spec: object) -> bool:
    if not isinstance(spec, dict) or not isinstance(spec.get("key"), str) or spec.get("type") not in TYPES:
        return False
    if spec["type"] == "enum":
        options = spec.get("options")
        return isinstance(options, list) and bool(options) and all(isinstance(o, dict) and "value" in o for o in options)
    return True


def catalog() -> list[dict]:
    """Every usable plugin in the checkout, by name."""
    try:
        paths = sorted(p for p in folder().iterdir() if p.is_dir())
    except OSError:
        return []
    found = [m for m in (read_manifest(p) for p in paths) if m]
    return sorted(found, key=lambda m: m["name"].lower())


def manifest(plugin_id: str) -> dict:
    found = next((m for m in catalog() if m["id"] == plugin_id), None)
    if found is None:
        raise PluginError(f"unknown plugin: {plugin_id}")
    return found


def state(cfg: dict, plugin_id: str) -> dict:
    entry = cfg.get("plugins", {}).get(plugin_id)
    return entry if isinstance(entry, dict) else {"installed": False, "settings": {}}


def settings_of(cfg: dict, plugin: dict) -> dict:
    """Every setting of the plugin: the saved value where it is valid, else its default."""
    saved = state(cfg, plugin["id"]).get("settings") or {}
    values = {}
    for spec in plugin["settings"]:
        try:
            values[spec["key"]] = checked(spec, saved[spec["key"]])
        except (KeyError, PluginError):
            values[spec["key"]] = spec.get("default")
    return values


def entry_values(cfg: dict, plugin: dict) -> dict:
    """What goes onto the widget's bar entry: its settings and Tuneup's language."""
    return {**settings_of(cfg, plugin), "language": cfg.get("language", "en")}


def checked(spec: dict, value: object) -> object:
    kind = spec["type"]
    if kind == "bool" and isinstance(value, bool):
        return value
    if kind == "int" and isinstance(value, int) and not isinstance(value, bool):
        if spec.get("min") is not None and value < spec["min"] or spec.get("max") is not None and value > spec["max"]:
            raise PluginError(f"{spec['key']} must be between {spec.get('min')} and {spec.get('max')}")
        return value
    if kind == "enum" and any(o["value"] == value for o in spec["options"]):
        return value
    raise PluginError(f"bad value for {spec['key']}: {value!r}")


def run_checks(plugin: dict) -> list[dict]:
    """{id, label, ok, text} per check; a command that is missing or hangs is not
    ok. A command starting with "./" is the plugin's own script. Its first line
    of output may name one of the check's "texts" (a finer answer than ok/missing)."""
    results = []
    for check in plugin["checks"]:
        command = list(check["command"])
        if command[0].startswith("./"):
            command[0] = str(plugin["path"] / command[0][2:])
        ok, said = False, ""
        if shutil.which(command[0]) or (command[0].startswith("/") and Path(command[0]).is_file()):
            try:
                done = subprocess.run(command, capture_output=True, text=True, timeout=CHECK_SECONDS)
                ok, said = done.returncode == 0, (done.stdout.strip().splitlines() or [""])[0]
            except (OSError, subprocess.SubprocessError):
                ok = False
        texts = check.get("texts") if isinstance(check.get("texts"), dict) else {}
        text = texts.get(said) or check.get("ok" if ok else "missing") or ""
        results.append({"id": check["id"], "label": str(check.get("label") or check["id"]), "ok": ok, "text": str(text)})
    return results


# --- shell.json -----------------------------------------------------------


def link_path(plugin: dict) -> Path:
    return install.plugins_dir() / plugin["shellId"]


@install.shell_edit
def put_in_bar(plugin: dict, values: dict) -> str:
    """The widget's entry in the bar, with the settings on it: on the spot of
    the first widget it replaces that is in the bar (which goes), else in front
    of the first of bar.before in its section, else at the start of that section."""
    path = install.shell_json()
    try:
        cfg = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "no shell.json"
    layout = cfg.setdefault("bar", {}).setdefault("layout", {})
    wanted = {"id": plugin["shellId"], **values}
    for section in (s for s in layout.values() if isinstance(s, list)):
        at = next((i for i, w in enumerate(section) if install.widget_id(w) == plugin["shellId"]), None)
        if at is not None:
            if section[at] == wanted:
                return "ok"
            section[at] = {**(section[at] if isinstance(section[at], dict) else {}), **wanted}
            install.write_json(path, cfg)
            return "updated"
    for replaced in plugin.get("replaces") or []:
        for section in (s for s in layout.values() if isinstance(s, list)):
            at = next((i for i, w in enumerate(section) if install.widget_id(w) == replaced), None)
            if at is not None:
                section[at] = wanted
                section[:] = [w for i, w in enumerate(section) if i == at or install.widget_id(w) != replaced]
                install.write_json(path, cfg)
                return f"added in place of {replaced}"
    section = layout.setdefault(plugin["bar"]["section"], [])
    ids = [install.widget_id(w) for w in section]
    at = next((ids.index(b) for b in plugin["bar"]["before"] if b in ids), 0)
    section.insert(at, wanted)
    install.write_json(path, cfg)
    return "added"


@install.shell_edit
def take_from_bar(shell_id: str, restore: list[str] | tuple = ()) -> str:
    """The widget out of the bar; with restore (the plugin's "replaces"), the
    first of those back on its spot unless one of them is in the bar already."""
    path = install.shell_json()
    try:
        cfg = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "no shell.json"
    layout = (cfg.get("bar") or {}).get("layout") or {}
    sections = [s for s in layout.values() if isinstance(s, list)]
    present = {install.widget_id(w) for s in sections for w in s}
    back = restore[0] if restore and not present.intersection(restore) else ""
    found = False
    for section in sections:
        at = next((i for i, w in enumerate(section) if install.widget_id(w) == shell_id), None)
        if at is None:
            continue
        if back and not found:
            section[at] = {"id": back}
        else:
            section.pop(at)
        section[:] = [w for w in section if install.widget_id(w) != shell_id]
        found = True
    if not found:
        return "ok"
    install.write_json(path, cfg)
    return f"removed, {back} back" if back else "removed"


def wire(plugin: dict, values: dict) -> list[str]:
    done = [f"{plugin['shellId']}: {install.link(plugin['path'] / 'shell', link_path(plugin))}"]
    install.run_quietly(["omarchy-shell", "shell", "rescanPlugins"])
    done.append(f"bar: {put_in_bar(plugin, values)}")
    return done


def unwire(plugin_id: str, shell_id: str, restore: list[str] | tuple = ()) -> list[str]:
    done = [f"bar: {take_from_bar(shell_id, restore)}"]
    path = install.plugins_dir() / shell_id
    if path.is_symlink() and (path.resolve().is_relative_to(folder().resolve()) or install.ours(path)):
        path.unlink()
        done.append(f"{shell_id}: removed")
    install.run_quietly(["omarchy-shell", "shell", "rescanPlugins"])
    return done


# --- what the page and the CLI call ------------------------------------------


def set_state(plugin_id: str, **changes) -> dict:
    def mutate(fresh: dict) -> None:
        entry = dict(state(fresh, plugin_id))
        entry.setdefault("settings", {})
        entry.update(changes)
        fresh.setdefault("plugins", {})[plugin_id] = entry
    return config.update(mutate)


def install_plugin(plugin_id: str) -> tuple[list[str], list[dict]]:
    """(what was done, the checks)."""
    plugin = manifest(plugin_id)
    checks = run_checks(plugin)
    if not install.has_omarchy_shell():
        raise PluginError("the Omarchy shell is not installed")
    cfg = set_state(plugin_id, installed=True)
    return wire(plugin, entry_values(cfg, plugin)), checks


def remove_plugin(plugin_id: str) -> list[str]:
    """Out of the bar and the shell; its settings are kept for a later install."""
    plugin = manifest(plugin_id)
    set_state(plugin_id, installed=False)
    return unwire(plugin_id, plugin["shellId"], plugin["replaces"])


def set_setting(plugin_id: str, key: str, value: object) -> dict:
    plugin = manifest(plugin_id)
    spec = next((s for s in plugin["settings"] if s["key"] == key), None)
    if spec is None:
        raise PluginError(f"{plugin_id} has no setting {key}")
    value = checked(spec, value)

    def mutate(fresh: dict) -> None:
        entry = dict(state(fresh, plugin_id))
        entry["settings"] = {**(entry.get("settings") or {}), key: value}
        fresh.setdefault("plugins", {})[plugin_id] = entry
    cfg = config.update(mutate)
    if state(cfg, plugin_id).get("installed"):
        put_in_bar(plugin, entry_values(cfg, plugin))
    return cfg


def sync(cfg: dict) -> list[str]:
    """`tuneup setup` (every update): installed plugins linked and in the bar again."""
    done = []
    for plugin in catalog():
        if state(cfg, plugin["id"]).get("installed"):
            done += [f"{plugin['id']}: {line}" for line in wire(plugin, entry_values(cfg, plugin))]
    return done


def refresh_bar(cfg: dict) -> None:
    """The installed widgets' bar entries again (after the language changed)."""
    for plugin in catalog():
        if state(cfg, plugin["id"]).get("installed"):
            put_in_bar(plugin, entry_values(cfg, plugin))


def remove_all(cfg: dict) -> list[str]:
    """Uninstalling: every plugin out of the shell (the settings go with the folder)."""
    done = []
    for plugin in catalog():
        if state(cfg, plugin["id"]).get("installed") or link_path(plugin).is_symlink():
            done += [f"{plugin['id']}: {line}" for line in unwire(plugin["id"], plugin["shellId"], plugin["replaces"])]
    return done


def text(plugin: dict, english: str, language: str) -> str:
    table = plugin["translations"].get(language)
    return table.get(english, english) if isinstance(table, dict) else english
