"""App to desktop: the settings, the apps of the launcher, the Lua module and
the endpoint (hypr_screens/app_desktops.py, api/apps.py)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hypr_screens import app_desktops, config, desktops, keybinds

HERE = Path(__file__).resolve().parent
LUA = next((shutil.which(name) for name in ("lua5.5", "lua5.4", "lua") if shutil.which(name)), None)


def entry(folder: Path, name: str, text: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.desktop").write_text("[Desktop Entry]\nType=Application\n" + text)


@pytest.fixture
def apps(tmp_path, monkeypatch):
    home, system = tmp_path / "home", tmp_path / "system"
    monkeypatch.setenv("XDG_DATA_HOME", str(home))
    monkeypatch.setenv("XDG_DATA_DIRS", str(system))
    entry(system / "applications", "discord", "Name=Discord\nExec=/usr/bin/discord --url -- %u\nStartupWMClass=discord\nIcon=discord\n")
    entry(home / "applications", "chrome-hnpfjngllnobngcgfapefoaidbinmjnm-Default",
          "Name=WhatsApp Web\nExec=/opt/helium/helium-wrapper --profile-directory=Default "
          "--app-id=hnpfjngllnobngcgfapefoaidbinmjnm\nStartupWMClass=crx_hnpfjngllnobngcgfapefoaidbinmjnm\n")
    entry(system / "applications", "org.gnome.Nautilus", "Name=Files\nName[de]=Dateien\nExec=env GTK_X=1 nautilus\n")
    entry(system / "applications", "hidden", "Name=Hidden\nNoDisplay=true\nExec=hidden\n")
    entry(system / "applications", "btop", "Name=btop\nTerminal=true\nExec=btop\n")
    entry(home / "applications", "discord", "Name=My Discord\nExec=discord\n")  # the user's own wins
    icons = system / "icons" / "hicolor" / "48x48" / "apps"
    icons.mkdir(parents=True)
    (icons / "discord.png").write_bytes(b"\x89PNG fake")
    app_desktops.icon_path.cache_clear()
    app_desktops.icon_data.cache_clear()
    monkeypatch.setattr(app_desktops, "icon_theme", lambda: "")
    yield
    app_desktops.icon_path.cache_clear()
    app_desktops.icon_data.cache_clear()


def test_the_apps_of_the_launcher_and_their_classes(apps):
    found = app_desktops.entries("de")
    assert set(found) == {"discord", "chrome-hnpfjngllnobngcgfapefoaidbinmjnm-Default", "org.gnome.Nautilus"}
    assert found["discord"]["name"] == "My Discord" and found["discord"]["classes"] == ["discord"]
    # a web app's window is chrome-<id>-<profile>, a moment after it opened
    assert found["chrome-hnpfjngllnobngcgfapefoaidbinmjnm-Default"]["classes"] == [
        "chrome-hnpfjngllnobngcgfapefoaidbinmjnm-default", "crx_hnpfjngllnobngcgfapefoaidbinmjnm"]
    assert found["org.gnome.Nautilus"]["name"] == "Dateien"
    assert found["org.gnome.Nautilus"]["classes"] == ["org.gnome.nautilus"]  # not "env"


def test_icons_are_data_urls(apps):
    assert app_desktops.icon_data("discord").startswith("data:image/png;base64,")
    assert app_desktops.icon_data("nothing-here") is None


def test_the_setting_is_checked():
    app = lambda i, **more: {"id": i, "name": i, "classes": [i], **more}  # noqa: E731
    raw = {"scratch:1": [app(f"a{i}") for i in range(7)],
           "desk:3": [app("a1"), app("b", mode="float"), {"id": "c", "classes": []}, "x"],
           "desk:11": [app("z")], "fixed:1": [app("y")]}
    found = app_desktops.normalize(raw)
    assert [a["id"] for a in found["scratch:1"]] == ["a0", "a1", "a2", "a3", "a4"]  # at most 5
    assert found["desk:3"] == [{"id": "b", "name": "b", "classes": ["b"], "mode": "float"}]  # each app once
    assert set(found) == {"scratch:1", "desk:3"}
    assert config.normalize({"app_desktops": raw})["app_desktops"] == found


def test_scratch_apps_wait_while_the_scratch_desktops_are_off():
    cfg = config.default_config()
    cfg["app_desktops"] = {"scratch:2": [{"id": "d", "classes": ["d"]}], "desk:1": [{"id": "e", "classes": ["e"]}]}
    assert [r["id"] for r in app_desktops.rules(cfg)] == ["d", "e"]
    cfg["scratch"] = False
    assert [r["id"] for r in app_desktops.rules(cfg)] == ["e"]


@pytest.mark.skipif(LUA is None, reason="no lua interpreter")
def test_the_lua_module_places_and_guards(tmp_path, monkeypatch):
    layout = tmp_path / "desktops.json"
    monkeypatch.setattr(desktops, "layout_file", lambda: layout)
    monkeypatch.setattr(app_desktops, "osd_command",
                        lambda name: app_desktops.shlex.join(["/fake/omarchy-osd", "-i", app_desktops.ROCKET,
                                                              "-m", name, "-d", str(app_desktops.OSD_MS)]))
    cfg = config.default_config()
    cfg["app_desktops"] = {
        "scratch:1": [{"id": "discord", "name": "Discord", "classes": ["discord"], "mode": "tile"}],
        "desk:3": [{"id": "wa", "name": "WhatsApp", "classes": ["chrome-abc-default"], "mode": "float"}],
    }
    module = tmp_path / "module.lua"
    module.write_text(app_desktops.module_lua(cfg))
    done = subprocess.run([LUA, str(HERE / "lua" / "apps_test.lua"), str(module), str(layout)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr + done.stdout


def test_the_generated_file_has_the_module():
    cfg = config.default_config()
    cfg["app_desktops"] = {"desk:2": [{"id": "x", "name": "X", "classes": ["x"]}]}
    lua = keybinds.render(cfg)
    assert '{ key = "x", classes = { "x" }, scratch = false, n = 2, float = false' in lua
    assert 'hl.on("window.open", opened)' in lua


def test_the_endpoint_moves_an_app_between_desktops(apps, monkeypatch):
    from hypr_screens import api
    written = []
    monkeypatch.setattr(keybinds, "write", lambda cfg: written.append(json.dumps(cfg["app_desktops"])))
    monkeypatch.setattr(keybinds, "go_live", lambda old, new, settled=False: True)
    state = api.set_app_desktop("scratch:1", [{"id": "discord", "mode": "tile"}])
    assert [a["id"] for a in state["desktops"]["scratch:1"]] == ["discord"]
    assert state["desktops"]["scratch:1"][0]["icon"] is None or state["desktops"]["scratch:1"][0]["icon"].startswith("data:")
    state = api.set_app_desktop("desk:4", [{"id": "discord", "mode": "float"}])
    assert "scratch:1" not in state["desktops"]
    assert state["desktops"]["desk:4"][0]["mode"] == "float" and state["desktops"]["desk:4"][0]["installed"]
    assert config.read()["app_desktops"]["desk:4"][0]["classes"] == ["discord"]
    assert len(written) == 2
    for bad in (("desk:11", []), ("desk:1", [{"id": "nope"}]), ("desk:1", [{"id": "discord", "mode": "x"}]),
                ("desk:1", [{"id": "discord"}] * 2)):
        with pytest.raises(api.ApiError):
            api.set_app_desktop(*bad)
