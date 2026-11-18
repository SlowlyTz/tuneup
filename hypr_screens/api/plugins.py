"""The "Plugins" page: Tuneup's own plugins (plugins.py), to install, remove
and set up. A PluginError (unknown plugin or setting, a value its schema does
not allow) is a ValueError, so the page gets bad_value."""
from hypr_screens import config
from hypr_screens import plugins as plugins_mod
from hypr_screens.api.core import endpoint


def view(cfg: dict, plugin: dict, checks: list[dict] | None = None) -> dict:
    """One plugin for the page, its texts in the chosen language."""
    language = cfg["language"]
    tr = lambda english: plugins_mod.text(plugin, english, language)  # noqa: E731
    settings = []
    for spec in plugin["settings"]:
        item = {"key": spec["key"], "type": spec["type"], "label": tr(str(spec.get("label") or spec["key"])),
                "description": tr(str(spec.get("description") or "")), "default": spec.get("default")}
        if spec["type"] == "enum":
            item["options"] = [{"value": o["value"], "label": tr(str(o.get("label") or o["value"]))} for o in spec["options"]]
        if spec["type"] == "int":
            item.update({"min": spec.get("min"), "max": spec.get("max")})
        settings.append(item)
    if checks is None:
        checks = plugins_mod.run_checks(plugin)
    return {
        "id": plugin["id"], "name": tr(plugin["name"]), "description": tr(plugin["description"]),
        "icon": plugin["icon"], "version": plugin["version"],
        "installed": bool(plugins_mod.state(cfg, plugin["id"]).get("installed")),
        "settings": settings, "values": plugins_mod.settings_of(cfg, plugin),
        "checks": [{**c, "label": tr(c["label"]), "text": tr(c["text"])} for c in checks],
    }



@endpoint
def plugins() -> list:
    cfg = config.load()
    return [view(cfg, plugin) for plugin in plugins_mod.catalog()]


@endpoint
def install_plugin(plugin_id: str) -> dict:
    _done, checks = plugins_mod.install_plugin(plugin_id)
    return view(config.load(), plugins_mod.manifest(plugin_id), checks)


@endpoint
def remove_plugin(plugin_id: str) -> dict:
    plugins_mod.remove_plugin(plugin_id)
    return view(config.load(), plugins_mod.manifest(plugin_id))


@endpoint
def set_plugin_setting(plugin_id: str, key: str, value: object) -> dict:
    cfg = plugins_mod.set_setting(plugin_id, key, value)
    return view(cfg, plugins_mod.manifest(plugin_id))
