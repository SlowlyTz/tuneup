"""Tuneup's own plugins (plugins.py, api/plugins.py): found in plugins/, put in
the bar where they ask, their settings checked and written onto the bar entry."""
import json

import pytest

from hypr_screens import api, config, install, plugins
from hypr_screens.api.core import ApiError


def make_plugin(root, plugin_id="music", **extra):
    folder = root / plugin_id
    (folder / "shell").mkdir(parents=True)
    (folder / "shell" / "manifest.json").write_text(json.dumps({"id": f"tuneup.{plugin_id}"}))
    manifest = {
        "id": plugin_id, "name": "Music", "description": "What plays", "icon": "music", "version": "1.0.0",
        "bar": {"section": "right", "before": ["slowly.agents"]},
        "settings": [
            {"key": "player", "type": "enum", "label": "Preferred player", "default": "auto",
             "options": [{"value": "auto", "label": "Automatic"}, {"value": "spotify", "label": "Spotify"}]},
            {"key": "timeRemaining", "type": "bool", "label": "Show the time left", "default": False},
        ],
        "translations": {"de": {"Preferred player": "Bevorzugter Player"}},
        **extra,
    }
    (folder / "plugin.json").write_text(json.dumps(manifest))
    return folder


@pytest.fixture()
def shell(tmp_path, monkeypatch):
    """A checkout with one plugin and a bar with the agents icon on the right."""
    monkeypatch.setattr(plugins, "FOLDER", tmp_path / "plugins")
    make_plugin(tmp_path / "plugins")
    monkeypatch.setattr(install, "has_omarchy_shell", lambda: True)
    monkeypatch.setattr(install, "run_quietly", lambda command: 0)
    install.shell_json().parent.mkdir(parents=True, exist_ok=True)
    install.shell_json().write_text(json.dumps({"bar": {"layout": {
        "right": [{"id": "omarchy.tray"}, {"id": "slowly.agents"}, {"id": "omarchy.audio"}]}}}))
    return tmp_path


def right_ids():
    return [w["id"] for w in json.loads(install.shell_json().read_text())["bar"]["layout"]["right"]]


def entry():
    return next(w for w in json.loads(install.shell_json().read_text())["bar"]["layout"]["right"]
                if w["id"] == "tuneup.music")


def test_a_folder_without_a_shell_manifest_is_not_a_plugin(shell):
    (shell / "plugins" / "broken").mkdir()
    (shell / "plugins" / "broken" / "plugin.json").write_text('{"id": "broken"}')
    assert [p["id"] for p in plugins.catalog()] == ["music"]


def test_installing_puts_it_in_front_of_the_agents_icon(shell):
    plugin = api.install_plugin("music")
    assert plugin["installed"] is True
    assert right_ids() == ["omarchy.tray", "tuneup.music", "slowly.agents", "omarchy.audio"]
    assert (install.plugins_dir() / "tuneup.music").resolve() == (shell / "plugins" / "music" / "shell").resolve()
    assert entry() == {"id": "tuneup.music", "player": "auto", "timeRemaining": False, "language": "en"}
    assert config.load()["plugins"]["music"]["installed"] is True


def test_installing_twice_keeps_one_entry(shell):
    api.install_plugin("music")
    api.install_plugin("music")
    assert right_ids().count("tuneup.music") == 1


def test_without_the_agents_icon_it_goes_first_on_the_right(shell):
    install.shell_json().write_text(json.dumps({"bar": {"layout": {"right": [{"id": "omarchy.audio"}]}}}))
    api.install_plugin("music")
    assert right_ids() == ["tuneup.music", "omarchy.audio"]


def test_a_setting_is_checked_and_lands_on_the_bar_entry(shell):
    api.install_plugin("music")
    plugin = api.set_plugin_setting("music", "player", "spotify")
    assert plugin["values"]["player"] == "spotify"
    assert entry()["player"] == "spotify"
    with pytest.raises(ApiError) as error:
        api.set_plugin_setting("music", "player", "winamp")
    assert error.value.code == "bad_value"
    with pytest.raises(ApiError):
        api.set_plugin_setting("music", "volume", 3)


def test_removing_keeps_the_settings_for_later(shell):
    api.install_plugin("music")
    api.set_plugin_setting("music", "timeRemaining", True)
    plugin = api.remove_plugin("music")
    assert plugin["installed"] is False
    assert "tuneup.music" not in right_ids()
    assert not (install.plugins_dir() / "tuneup.music").exists()
    api.install_plugin("music")
    assert entry()["timeRemaining"] is True


def test_texts_come_in_the_chosen_language(shell):
    config.update(lambda cfg: cfg.__setitem__("language", "de"))
    plugin = api.plugins()[0]
    assert plugin["settings"][0]["label"] == "Bevorzugter Player"
    assert plugin["settings"][1]["label"] == "Show the time left"  # not translated: English


def test_checks_report_what_they_find(shell, tmp_path):
    (shell / "plugins" / "music" / "plugin.json").unlink()
    import shutil
    shutil.rmtree(shell / "plugins" / "music")
    make_plugin(shell / "plugins", checks=[
        {"id": "yes", "label": "There", "command": ["true"], "ok": "fine", "missing": "gone"},
        {"id": "no", "label": "Missing", "command": ["no-such-command-here"], "ok": "fine", "missing": "gone"},
        {"id": "own", "label": "Own script", "command": ["./check"], "missing": "gone", "texts": {"old": "too old"}},
    ])
    script = shell / "plugins" / "music" / "check"
    script.write_text("#!/bin/sh\necho old\nexit 1\n")
    script.chmod(0o755)
    checks = {c["id"]: c for c in api.plugins()[0]["checks"]}
    assert not checks["own"]["ok"] and checks["own"]["text"] == "too old"
    assert checks["yes"]["ok"] and checks["yes"]["text"] == "fine"
    assert not checks["no"]["ok"] and checks["no"]["text"] == "gone"


def test_setup_wires_installed_plugins_again(shell):
    api.install_plugin("music")
    install.shell_json().write_text(json.dumps({"bar": {"layout": {"right": [{"id": "slowly.agents"}]}}}))
    plugins.sync(config.load())
    assert right_ids() == ["tuneup.music", "slowly.agents"]


def test_uninstalling_takes_every_plugin_out(shell):
    api.install_plugin("music")
    plugins.remove_all(config.load())
    assert right_ids() == ["omarchy.tray", "slowly.agents", "omarchy.audio"]
    assert not (install.plugins_dir() / "tuneup.music").is_symlink()


def test_the_settings_file_keeps_only_plain_plugin_values():
    cfg = config.normalize({"plugins": {"music": {"installed": True, "settings": {"a": 1, "b": {"x": 1}}},
                                        "Bad Id": {"installed": True}}})
    assert cfg["plugins"] == {"music": {"installed": True, "settings": {"a": 1}}}


@pytest.fixture()
def replacing(shell):
    """A second plugin that stands in for Omarchy's display panel."""
    folder = shell / "plugins" / "display"
    (folder / "shell").mkdir(parents=True)
    (folder / "shell" / "manifest.json").write_text(json.dumps({"id": "tuneup.display"}))
    (folder / "plugin.json").write_text(json.dumps({
        "id": "display", "name": "Display", "replaces": ["omarchy.monitor"],
        "bar": {"section": "right", "before": ["omarchy.power"]}}))
    install.shell_json().write_text(json.dumps({"bar": {"layout": {"right": [
        {"id": "omarchy.network"}, {"id": "omarchy.monitor"}, {"id": "omarchy.power", "showPercentage": True}]}}}))
    return shell


def test_a_replacing_plugin_takes_the_spot_of_the_widget_it_replaces(replacing):
    assert plugins.manifest("display")["replaces"] == ["omarchy.monitor"]
    api.install_plugin("display")
    assert right_ids() == ["omarchy.network", "tuneup.display", "omarchy.power"]
    api.install_plugin("display")  # again (as `tuneup setup` does): nothing moves, nothing comes back
    assert right_ids() == ["omarchy.network", "tuneup.display", "omarchy.power"]


def test_removing_a_replacing_plugin_puts_the_replaced_widget_back_on_its_spot(replacing):
    api.install_plugin("display")
    layout = json.loads(install.shell_json().read_text())
    layout["bar"]["layout"]["right"].append({"id": "omarchy.tray"})  # moved around meanwhile
    layout["bar"]["layout"]["right"].insert(0, layout["bar"]["layout"]["right"].pop(1))
    install.shell_json().write_text(json.dumps(layout))
    api.remove_plugin("display")
    assert right_ids() == ["omarchy.monitor", "omarchy.network", "omarchy.power", "omarchy.tray"]
    assert json.loads(install.shell_json().read_text())["bar"]["layout"]["right"][2] == {
        "id": "omarchy.power", "showPercentage": True}


def test_without_the_replaced_widget_it_goes_where_bar_before_says(replacing):
    install.shell_json().write_text(json.dumps({"bar": {"layout": {"right": [
        {"id": "omarchy.network"}, {"id": "omarchy.power"}]}}}))
    api.install_plugin("display")
    assert right_ids() == ["omarchy.network", "tuneup.display", "omarchy.power"]


def test_the_replaced_widget_is_not_put_back_twice(replacing):
    api.install_plugin("display")
    layout = json.loads(install.shell_json().read_text())
    layout["bar"]["layout"]["right"].append({"id": "omarchy.monitor"})  # the user put it back by hand
    install.shell_json().write_text(json.dumps(layout))
    api.remove_plugin("display")
    assert right_ids() == ["omarchy.network", "omarchy.power", "omarchy.monitor"]


def test_uninstalling_restores_the_replaced_widget(replacing):
    api.install_plugin("display")
    plugins.remove_all(config.load())
    assert right_ids() == ["omarchy.network", "omarchy.monitor", "omarchy.power"]


def test_a_plugin_that_replaces_nothing_restores_nothing(shell):
    api.install_plugin("music")
    api.remove_plugin("music")
    assert right_ids() == ["omarchy.tray", "slowly.agents", "omarchy.audio"]


def test_the_display_plugin_in_the_checkout_is_complete():
    plugin = next(p for p in plugins.catalog() if p["id"] == "display")
    assert plugin["shellId"] == "tuneup.display" and plugin["replaces"] == ["omarchy.monitor"]
    assert plugin["icon"] == "monitor"
    for language in ("de", "es", "fr", "it"):
        assert plugins.text(plugin, plugin["name"], language) != plugin["name"]
        assert plugins.text(plugin, plugin["description"], language) != plugin["description"]
    shell_dir = plugin["path"] / "shell"
    assert {"Panel.qml", "Model.js", "Texts.js", "manifest.json"} <= {p.name for p in shell_dir.iterdir()}
    assert json.loads((shell_dir / "manifest.json").read_text())["omarchy"]["clonedFrom"] == "omarchy.monitor"
