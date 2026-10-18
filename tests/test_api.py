"""The HTML settings window's backend (hypr_screens/api/) and config.update(),
against a fake Hyprland, fake pactl and a fake /sys -- nothing real is touched."""
import json
import os
from pathlib import Path
import threading
import time

import pytest

from hypr_screens import (api, apply, camera, config, desktops, engine, hypr, i18n, install, keybinds, look, samsung,
                          sound, theme, widgets)
from test_samsung import ppd, sysfs  # noqa: F401 - fixtures
from test_screens import HP_ID, LAPTOP_ID, FakeHyprland, hp, laptop

REAL_HYPRCTL = hypr.hyprctl
LOOK_KEYS = {"color", "colors", "font_family", "font_weight", "letter_spacing", "effect", "effect_strength", "card",
             "card_radius", "card_padding", "card_opacity", "card_blur", "opacity", "size", "width", "gap", "align",
             "current_size", "scroll_ms", "x", "y", "rotation", "spots"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    for name in ("XDG_CONFIG_HOME", "XDG_RUNTIME_DIR", "XDG_STATE_HOME"):
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(apply.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    # Nothing outside: no shell plugin wiring, no pw-dump/busctl, no real camera or /sys.
    monkeypatch.setattr(widgets, "apply", lambda cfg: calls.setdefault("widgets.apply", []).append(cfg))
    monkeypatch.setattr(widgets, "export", lambda cfg: calls.setdefault("widgets.export", []).append(cfg))
    monkeypatch.setattr(widgets, "players", lambda: ["spotify"])
    monkeypatch.setattr(widgets, "has_cava", lambda: True)
    monkeypatch.setattr(camera, "SYSFS", tmp_path / "sys")
    monkeypatch.setattr(camera, "MODPROBE", tmp_path / "modprobe.conf")
    monkeypatch.setattr(camera, "OLD_MODPROBE", tmp_path / "old-modprobe.conf")
    monkeypatch.setattr(samsung, "SYSFS", tmp_path / "no-sys")
    monkeypatch.setattr(sound, "pactl", lambda *args: calls.setdefault("pactl", []).append(args) or "")
    monkeypatch.setattr(api.general, "open_uri", lambda uri: calls.setdefault("open", []).append(uri))
    # Any hyprctl a test forgets to fake answers nothing instead of reaching Hyprland.
    monkeypatch.setattr(hypr, "hyprctl", lambda *args: "")
    monkeypatch.setattr(api.appearance, "_preview", None)
    calls.clear()
    yield
    i18n.set_language("en")


calls: dict[str, list] = {}


@pytest.fixture()
def desk(monkeypatch):
    """Laptop (1920x1080) with the HP (2560x1440) to its right, both recorded."""
    hyprland = FakeHyprland([laptop(), hp()])
    monkeypatch.setattr(hypr, "hyprctl", hyprland)
    api.screens()
    hyprland.calls.clear()
    return hyprland


def error_of(function, *args) -> api.ApiError:
    with pytest.raises(api.ApiError) as caught:
        function(*args)
    return caught.value


# --- config.update ---------------------------------------------------------------------


def test_update_saves_under_the_lock_and_skips_when_told():
    config.update(lambda cfg: cfg.__setitem__("language", "de"))
    assert config.load()["language"] == "de"
    stamp = config.config_file().stat().st_mtime_ns
    config.update(lambda cfg: False)
    assert config.config_file().stat().st_mtime_ns == stamp
    assert [p.name for p in config.config_file().parent.iterdir()] == ["config.json"]  # no temporary left


def test_update_never_writes_over_an_unreadable_file():
    path = config.config_file()
    path.parent.mkdir(parents=True)
    path.write_text('{"screens": {"x": ')
    with pytest.raises(config.ConfigError):
        config.update(lambda cfg: cfg.__setitem__("language", "de"))
    assert path.read_text() == '{"screens": {"x": '
    assert config.load() == config.default_config()  # readers still get something
    assert error_of(api.keys).code == "config_unreadable"


def test_updates_from_two_threads_both_land():
    def add(name):
        def mutate(cfg):
            seen = dict(cfg["screens"])
            time.sleep(0.05)  # both would read the same old file without the lock
            cfg["screens"] = {**seen, name: {"favorite": False, "settings": {}}}
        config.update(mutate)
    threads = [threading.Thread(target=add, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert set(config.load()["screens"]) == {"a", "b"}


def test_nested_update_does_not_deadlock():
    config.update(lambda cfg: config.update(lambda inner: inner.__setitem__("language", "it")) and False)
    assert config.load()["language"] == "it"


def test_sync_records_screens_through_update(desk):
    path = config.config_file()
    path.write_text("not json")
    with pytest.raises(config.ConfigError):
        engine.sync()
    assert path.read_text() == "not json"


def test_summary_wording():
    cfg = config.default_config()
    config.set_setting(cfg, HP_ID, "position", "above")
    assert config.summary(cfg, HP_ID) == "above laptop"


# --- the bridge's contract -------------------------------------------------------------


def test_call_maps_camel_case_and_rejects_unknown_methods(desk):
    assert api.call("fixedStatus", [])["canSwap"] is True
    assert error_of(api.call, "dropDatabase", []).code == "unknown_method"
    assert error_of(api.call, "setScreenSetting", ["only-one"]).code == "bad_args"
    assert api.ApiError("x", "y").to_json() == {"code": "x", "message": "y"}


def test_unexpected_errors_become_internal(desk, monkeypatch):
    monkeypatch.setattr(desktops, "status", lambda cfg: 1 / 0)
    error = error_of(api.fixed_status)
    assert error.code == "internal" and "ZeroDivisionError" in error.message


def test_the_mock_has_exactly_the_real_methods():
    import re

    script = (Path(api.__file__).parent.parent / "web" / "mock.js").read_text()
    block = script[script.index("const api = {"):script.index("window.api = api")]
    mock = set(re.findall(r"^    (?:async )?([a-zA-Z]+)(?:\(|: )", block, re.M))
    real = {re.sub(r"_([a-z])", lambda m: m.group(1).upper(), name) for name in api.METHODS}
    assert mock == real


def test_every_result_is_json(desk):
    for name in ("screens", "fixed_status", "keys", "look", "sound_state", "camera", "samsung", "widgets",
                 "layouts", "language", "about", "translations", "enforcement"):
        json.dumps(api.METHODS[name]())


# --- screens ---------------------------------------------------------------------------


def test_screens_show_live_values_modes_and_settings(desk):
    desk.monitors[1]["availableModes"] = ["2560x1440@59.95Hz", "2560x1440@30.00Hz", "1920x1080@60.00Hz"]
    screens = api.screens()
    assert [s["id"] for s in screens] == [LAPTOP_ID, HP_ID]
    laptop_view, hp_view = screens
    assert laptop_view["laptop"] and laptop_view["connected"] and "position" not in laptop_view["settings"]
    assert hp_view["modes"] == [
        {"w": 2560, "h": 1440, "rates": [59.95, 30.0], "modes": ["2560x1440@59.95", "2560x1440@30.00"],
         "preferred": True},
        {"w": 1920, "h": 1080, "rates": [60.0], "modes": ["1920x1080@60.00"], "preferred": False},
    ]
    assert hp_view["hypr"] == {"rotation": 0, "flipped": False, "scale": 1.0, "mode": "2560x1440@60.00",
                               "one_desktop": False}
    assert hp_view["position"] == {"x": 1920, "y": 0, "w": 2560, "h": 1440}
    assert hp_view["settings"]["rotation"] == {"value": None, "when": [], "active": False}
    assert hp_view["side"] is None


def test_a_setting_with_a_condition_is_saved_and_applied(desk):
    result = api.set_screen_setting(LAPTOP_ID, "rotation", 180, [HP_ID])
    assert config.get_setting(config.load(), LAPTOP_ID, "rotation") == {"value": 180, "when": HP_ID}
    assert result["settings"]["rotation"] == {"value": 180, "when": [HP_ID], "active": True}
    assert result["applied"] == ["eDP-1"] and result["hypr"]["rotation"] == 180

    api.set_screen_setting(LAPTOP_ID, "rotation", 90, None)  # None keeps the condition
    assert config.get_setting(config.load(), LAPTOP_ID, "rotation") == {"value": 90, "when": HP_ID}
    api.set_screen_setting(LAPTOP_ID, "rotation", 90, [])  # [] = always
    assert config.get_setting(config.load(), LAPTOP_ID, "rotation")["when"] is None
    api.set_screen_setting(LAPTOP_ID, "rotation", None)
    assert config.get_setting(config.load(), LAPTOP_ID, "rotation") is None


def test_bad_screen_values_are_refused(desk):
    assert error_of(api.set_screen_setting, LAPTOP_ID, "rotation", 45).code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "scale", 9).code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "mode", "huge").code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "position", "left").code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "one_desktop", 1).code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "rotation", 90, [HP_ID, "x"]).code == "bad_value"
    assert error_of(api.set_screen_setting, LAPTOP_ID, "rotation", 90, [LAPTOP_ID]).code == "bad_value"
    assert error_of(api.set_screen_setting, "nope", "rotation", 90).code == "unknown_screen"
    assert config.get_setting(config.load(), LAPTOP_ID, "rotation") is None


def test_a_dragged_screen_gets_the_nearest_side(desk):
    result = api.set_screen_setting(HP_ID, "position", {"x": -320, "y": -1440})
    assert result["side"] == "above" and config.get_setting(config.load(), HP_ID, "position")["value"] == "above"
    # apply.layout put it edge to edge above the laptop, centred.
    assert result["position"] == {"x": 0, "y": 0, "w": 2560, "h": 1440}
    assert api.screens()[0]["position"]["y"] == 1440

    api.set_screen_setting(HP_ID, "position", {"x": -2560, "y": 1440 - 180})
    assert config.get_setting(config.load(), HP_ID, "position")["value"] == "left"
    # Dragging the laptop sets the other screen's side: laptop below the HP = HP above.
    api.set_screen_setting(LAPTOP_ID, "position", {"x": 2560 // 2 - 960, "y": 1440 + 10_000})
    assert config.get_setting(config.load(), HP_ID, "position")["value"] == "above"
    assert api.set_screen_setting(HP_ID, "position", "right")["side"] == "right"


def test_forget_favorite_and_swap(desk):
    assert error_of(api.forget_screen, HP_ID).code == "connected_screen"
    assert error_of(api.forget_screen, LAPTOP_ID).code == "internal_screen"
    assert api.toggle_favorite(HP_ID)["favorite"] is True
    desk.monitors.pop()  # unplugged
    assert api.forget_screen(HP_ID) == {"ok": True}
    assert HP_ID not in config.load()["screens"]
    assert error_of(api.swap_fixed).code == "no_external"


def test_fixed_status_names_screen_ids(desk):
    api.set_option("default_fixed", "external")
    status = api.fixed_status()
    assert (status["fixed"], status["desk"], status["role"]) == (HP_ID, LAPTOP_ID, "external")
    assert api.screens()[1]["hypr"]["one_desktop"] is True
    swapped = api.swap_fixed()
    assert (swapped["fixed"], swapped["swapped"]) == (LAPTOP_ID, True)


# --- keys ------------------------------------------------------------------------------


def test_keys_list_actions_and_what_hyprland_has_bound(desk):
    desk.binds = [
        {"modmask": 64, "key": "Q", "description": "Close window"},
        {"modmask": 64, "key": "", "keycode": 10, "description": "Switch to workspace 1"},
        {"modmask": 64, "key": "M", "description": "Minimize window"},  # ours
        {"modmask": 0, "key": "escape", "submap": "hypr-screens-record", "description": ""},
    ]
    result = api.keys()
    stash = next(a for a in result["actions"] if a["id"] == "stash")
    assert stash == {"id": "stash", "title": "Hide window", "desc": "Hides the active window.",
                     "slots": ["SUPER + M", None]}
    assert result["hyprBinds"] == {"SUPER + Q": "Close window", "SUPER + 1": "Switch to workspace 1"}
    assert result["options"] == {"desktop_keys": False, "default_fixed": "off"}


def test_a_key_moves_from_another_action_and_goes_live(desk):
    result = api.set_key("pop", 1, "super+m")
    assert result["slots"] == ["SUPER + I", "SUPER + M"]
    assert config.load()["keybinds"]["stash"] == ["", ""]
    assert 'hl.bind("SUPER + M", hl.dsp.exec_cmd("hypr-minimizer pop")' in keybinds.lua_file().read_text()
    assert any("hypr-minimizer pop" in code for code in desk.evaluated)
    assert api.set_key("pop", 1, None)["slots"] == ["SUPER + I", None]
    assert error_of(api.set_key, "pop", 2, "SUPER + K").code == "bad_value"
    assert error_of(api.set_key, "pop", 0, "HYPER + K").code == "bad_value"
    assert error_of(api.set_key, "fly", 0, "SUPER + K").code == "bad_value"


def test_options_and_key_capture(desk):
    assert api.set_option("desktop_keys", True) == {"desktop_keys": True, "default_fixed": "off"}
    assert "tuneup switch 1" in keybinds.lua_file().read_text()
    assert error_of(api.set_option, "default_fixed", "laptop").code == "bad_value"
    assert error_of(api.set_option, "volume", 3).code == "bad_value"
    api.begin_key_capture()
    api.end_key_capture()
    assert desk.dispatched[-2:] == ['hl.dsp.submap("hypr-screens-record")', 'hl.dsp.submap("reset")']


# --- window look -----------------------------------------------------------------------


@pytest.fixture()
def shown(monkeypatch):
    """What look.apply/show_by_reload put on screen."""
    state = {"live": {"gaps_in": 5, "gaps_out": 10, "rounding": 8, "border_size": 2, "blur": True, "blur_size": 6,
                      "blur_passes": 2, "active_opacity": 1.0, "inactive_opacity": 1.0}, "applied": [], "reloads": []}
    monkeypatch.setattr(look, "current", lambda: dict(state["live"]))
    monkeypatch.setattr(look, "current_border", lambda: (["#89b4faff", "#89b4faff"], 0))
    monkeypatch.setattr(look, "apply", lambda values: state["applied"].append(values))
    monkeypatch.setattr(look, "show_by_reload", lambda cfg, values: state["reloads"].append(values))
    return state


def test_look_preview_revert_and_save(desk, shown):
    values = api.look()["values"]
    assert values["gapsIn"] == 5 and values["border"] == 2 and values["animSpeed"] == 1.0
    assert values["borderColors"] is None and values["apps"] == []

    draft = {**values, "gapsIn": 12}
    assert api.preview_look(draft)["reloaded"] is False
    assert shown["applied"][-1]["gaps_in"] == 12 and api.look()["previewing"] is True
    assert config.load()["look"] == {}

    api.revert_look()
    assert shown["applied"][-1]["gaps_in"] == 5 and api.look()["previewing"] is False

    saved = api.save_look({**values, "rounding": 0})
    assert config.load()["look"]["rounding"] == 0 and saved["saved"]["rounding"] == 0
    assert "rounding = 0" in keybinds.lua_file().read_text()


def test_see_through_apps_need_a_reload_and_bad_looks_are_refused(desk, shown):
    values = api.look()["values"]
    api.preview_look({**values, "apps": [{"class": "kitty", "active": 0.9, "inactive": 0.8}]})
    assert shown["reloads"][-1]["apps"][0]["class"] == "kitty"
    api.revert_look()
    assert shown["reloads"][-1] == {}  # the saved look (none) is shown again
    assert error_of(api.preview_look, {"transparency": 10}).code == "bad_value"
    assert error_of(api.preview_look, {"borderColors": ["red"]}).code == "bad_value"
    assert error_of(api.preview_look, {"gapsIn": "wide"}).code == "bad_value"
    api.preview_look({"rounding": 3})  # some values: the rest stays as shown
    assert shown["applied"][-1]["gaps_in"] == 5 and api.look()["values"]["rounding"] == 3
    api.save_look({"borderColors": ["#ff0000", "#00ff00"]})
    assert config.load()["look"]["border_colors"] == ["#ff0000", "#00ff00"]
    api.save_look({"borderColors": None})
    assert "border_colors" not in config.load()["look"]


# --- sound -----------------------------------------------------------------------------


SPEAKER = {"kind": "sink", "key": "card:[Out] Speaker", "name": "alsa_output.speaker", "label": "Laptop speakers",
           "detail": "HD Audio", "icon": "audio-speakers-symbolic", "volume": 40, "mute": False, "active": True,
           "default": True, "available": "", "card": "card", "profile": ""}
HEADPHONES = {**SPEAKER, "key": "card:[Out] Headphones", "name": "", "label": "Headphones (jack)",
              "icon": "audio-headphones-symbolic", "active": False, "default": False, "profile": "HiFi (Headphones)"}
MIC = {**SPEAKER, "kind": "source", "key": "card:[In] Mic1", "name": "alsa_input.mic", "label": "Laptop microphone",
       "icon": "audio-input-microphone-symbolic"}
APP = {"index": 7, "label": "Spotify", "detail": "", "icons": ["spotify"], "search": "Spotify", "volume": 80,
       "mute": False, "sink": "alsa_output.speaker", "paused": False}


@pytest.fixture()
def audio(monkeypatch):
    monkeypatch.setattr(sound, "snapshot", lambda: {"outputs": [dict(SPEAKER), dict(HEADPHONES)],
                                                    "inputs": [dict(MIC)], "apps": [dict(APP)]})
    monkeypatch.setattr(sound, "enforce", lambda cfg=None: calls.setdefault("enforce", []).append(cfg))
    monkeypatch.setattr(sound, "switch_on", lambda card, profile: calls.setdefault("switch_on", []).append(profile))


def test_sound_state_shapes(audio):
    state = api.sound_state()
    speaker = state["outputs"][0]
    assert speaker == {"key": "card:[Out] Speaker", "kind": "sink", "name": "Laptop speakers", "sub": "HD Audio",
                       "icon": "speaker", "volume": 40, "muted": False, "isDefault": True, "forceMute": False,
                       "active": True, "connected": True, "node": "alsa_output.speaker"}
    assert state["outputs"][1]["icon"] == "headphones" and state["outputs"][1]["active"] is False
    assert state["inputs"][0]["icon"] == "mic"
    assert state["apps"] == [{"key": "app:7", "index": 7, "name": "Spotify", "sub": "", "icons": ["spotify"],
                              "volume": 80, "muted": False, "paused": False, "output": "card:[Out] Speaker"}]


def test_volume_mute_default_and_app_output(audio):
    api.set_volume("card:[Out] Speaker", 55)
    api.set_mute("app:7", True)
    api.set_default("card:[In] Mic1")
    assert calls["pactl"] == [("set-sink-volume", "alsa_output.speaker", "55%"),
                              ("set-sink-input-mute", "7", "1"),
                              ("set-default-source", "alsa_input.mic")]
    assert error_of(api.set_volume, "card:[Out] Speaker", 101).code == "bad_value"
    assert error_of(api.set_volume, "card:[Out] Headphones", 10).code == "inactive"
    assert error_of(api.set_app_output, "app:7", "card:[Out] Headphones").code == "unknown_device"
    assert error_of(api.set_mute, "app:99", True).code == "unknown_device"
    api.switch_on_device("card:[Out] Headphones")
    assert calls["switch_on"] == ["HiFi (Headphones)"]


def test_force_mute_is_kept_and_locks_the_device(audio):
    api.set_force_mute("card:[Out] Speaker", True)
    assert sound.forced(config.load())["card:[Out] Speaker"]["volume"] == 40
    assert calls["enforce"]
    assert api.sound_state()["outputs"][0]["forceMute"] is True
    assert error_of(api.set_volume, "card:[Out] Speaker", 30).code == "force_muted"
    api.set_force_mute("card:[Out] Speaker", False)
    assert sound.forced(config.load()) == {}
    assert ("set-sink-volume", "alsa_output.speaker", "40%") in calls["pactl"]  # back where it was


def test_an_unplugged_force_muted_device_is_listed(audio):
    config.update(lambda cfg: cfg["sound"]["force_mute"].__setitem__(
        "bt:headset", {"kind": "sink", "label": "Headset", "volume": 20, "mute": False}))
    gone = api.sound_state()["outputs"][-1]
    assert (gone["key"], gone["connected"], gone["forceMute"]) == ("bt:headset", False, True)
    assert api.set_force_mute("bt:headset", False) is None
    assert sound.forced(config.load()) == {}


# --- camera, Samsung, general ----------------------------------------------------------


def test_camera_state_and_settings():
    state = api.camera()
    assert (state["installed"], state["enabled"], state["rotation"], state["state"]) == (False, True, 0, None)
    assert api.set_camera(False, 90)["rotation"] == 90
    assert config.load()["camera"] == {"rotation": 90, "enabled": False}
    assert error_of(api.set_camera, True, 45).code == "bad_value"
    assert api.camera_preview() == {"image": None, "reason": "not_set_up"}


def test_samsung_without_a_galaxy_book():
    assert api.samsung() == {"available": False, "active": False}
    assert error_of(api.set_samsung, "chargeLimit", 80).code == "unavailable"


def test_samsung_on_a_galaxy_book(sysfs, ppd, monkeypatch):  # noqa: F811
    monkeypatch.setattr(samsung, "writable", lambda: True)
    monkeypatch.setattr(samsung, "active", lambda: True)
    state = api.samsung()
    assert (state["available"], state["level"], state["chargeLimit"], state["health"]) == (True, 80, 80, 95)
    assert (state["mode"], state["fanRpm"], state["cpuTemp"], state["kbdMax"]) == ("balanced", 3100, 71, 3)
    assert state["modes"][0] == {"value": "low-power", "label": "Saver"}
    assert (state["usbCharging"], state["lidPower"]) == (True, False)
    assert api.set_samsung("chargeLimit", 60)["chargeLimit"] == 60
    assert config.load()["samsung"]["limit"] == 60
    assert api.set_samsung("mode", "quiet")["mode"] == "quiet"
    assert error_of(api.set_samsung, "mode", "turbo").code == "bad_value"
    assert error_of(api.set_samsung, "fanRpm", 1).code == "bad_value"


def test_samsung_writes_need_the_setup(sysfs, ppd, monkeypatch):  # noqa: F811
    monkeypatch.setattr(samsung, "writable", lambda: False)
    assert error_of(api.set_samsung, "chargeLimit", 70).code == "not_set_up"


def test_samsung_guard_change_writes_only_on_change(sysfs, ppd):  # noqa: F811
    cfg = config.default_config()
    assert samsung.guard_change(cfg) is False
    cfg["samsung"]["mode"] = "quiet"  # the keyboard's mode key set "balanced": taken over
    assert samsung.guard_change(cfg) is True and cfg["samsung"]["mode"] == "balanced"


def test_language_about_links_and_theme(monkeypatch, tmp_path):
    assert api.set_language("de")["code"] == "de" and config.load()["language"] == "de"
    assert calls["widgets.export"]
    assert api.translations()["texts"]["Screens"] == "Bildschirme"
    assert error_of(api.set_language, "xx").code == "bad_value"
    about = api.about()
    assert about["configDir"] == str(config.config_file().parent) and about["version"]
    api.open_guide()
    api.open_config_folder()
    assert calls["open"][0] == api.general.DOCS_URL and calls["open"][1].startswith("file://")
    folder = tmp_path / "xdg_state_home/omarchy/current/theme"
    folder.mkdir(parents=True)
    (folder / "colors.toml").write_text('mode = "light"\naccent = "#123456"\n')
    monkeypatch.setattr(theme, "font", lambda: "JetBrains Mono")
    monkeypatch.setattr(theme, "rounding", lambda: 6)
    result = api.theme()
    assert (result["mode"], result["colors"]["accent"], result["font"], result["rounding"]) == \
        ("light", "#123456", "JetBrains Mono", 6)


# --- widgets ---------------------------------------------------------------------------


def test_widgets_have_a_schema_without_the_look(desk):
    every = api.widgets()
    assert [w["kind"] for w in every] == widgets.KINDS
    for widget in every:
        keys = {f["key"] for f in widget["schema"]}
        assert not keys & LOOK_KEYS, (widget["kind"], keys & LOOK_KEYS)
        assert set(widget["content"]) | set(widget["where"]) == keys
        for f in widget["schema"]:
            assert f["type"] in ("toggle", "choice", "number", "text", "multi") and f["label"]
            if f["type"] == "choice":
                assert all({"value", "label"} <= set(c) for c in f["choices"])
            if f["type"] == "number":
                assert f["min"] <= f["default"] <= f["max"]
    clock = next(w for w in every if w["kind"] == "clock")
    assert clock["content"]["clock_style"] == "digital" and clock["where"]["desktops"] == ["all"]
    assert clock["where"]["screens"] == "all"
    screens = next(f for f in clock["schema"] if f["key"] == "screens")
    assert [c["value"] for c in screens["choices"]] == ["laptop", "external", "all", HP_ID]
    pattern = next(f for f in clock["schema"] if f["key"] == "date_pattern")
    assert pattern["showIf"] == {"date_format": "custom"} and pattern["enabledBy"] == "date"
    player = next(f for f in every[0]["schema"] if f["key"] == "player")
    assert [c["value"] for c in player["choices"]] == ["", "spotify"]


def test_update_widget_checks_and_applies(desk):
    clock = api.update_widget("clock", {"enabled": True, "content": {"clock_style": "analog", "hours": "12"},
                                        "where": {"screens": HP_ID, "desktops": ["1", "fixed"], "above": True}})
    assert clock["enabled"] and clock["content"]["clock_style"] == "analog"
    assert clock["where"]["screens"] == HP_ID and clock["where"]["desktops"] == ["1", "fixed"]
    saved = config.load()["widgets"]["clock"]
    assert saved["monitors"] == {"mode": "screen", "screen": HP_ID} and saved["desktops"] == [1, 99]
    assert (saved["x"], saved["y"]) == (0.5, 0.5) and calls["widgets.apply"]
    assert api.update_widget("clock", {"where": {"desktops": ["all"]}})["where"]["desktops"] == ["all"]

    for kind, changes in (("clock", {"content": {"color": "white"}}), ("clock", {"content": {"hours": "13"}}),
                          ("clock", {"where": {"screens": LAPTOP_ID}}), ("clock", {"where": {"desktops": ["11"]}}),
                          ("clock", {"content": {"zone2": "Mars/Base"}}), ("lyrics", {"content": {"lines": 99}}),
                          ("clock", {"size": 3}), ("clock", {"enabled": "yes"})):
        assert error_of(api.update_widget, kind, changes).code == "bad_value", changes
    assert error_of(api.update_widget, "aquarium", {}).code == "unknown_widget"
    assert api.update_widget("clock", {"content": {"zone2": "Asia/Tokyo"}})["content"]["zone2"] == "Asia/Tokyo"


def test_layouts_save_load_rename_delete(desk):
    api.update_widget("clock", {"enabled": True})
    assert api.save_layout("Desk") == {"current": "Desk", "items": ["Desk"], "connected": sorted([LAPTOP_ID, HP_ID]),
                                       "layouts": [{"name": "Desk", "screens": [], "screenNames": [], "auto": False,
                                                    "matchesNow": False}]}
    api.update_widget("clock", {"enabled": False})
    assert api.layouts()["current"] is None
    assert api.load_layout("Desk")["current"] == "Desk"
    assert config.load()["widgets"]["clock"]["enabled"] is True
    api.save_layout("Away")
    assert error_of(api.rename_layout, "Desk", "Away").code == "conflict"
    assert api.rename_layout("Desk", "Office")["items"] == ["Office", "Away"]
    assert api.set_layout_auto("Office", True)["layouts"][0]["matchesNow"] is True
    assert api.delete_layout("Away")["items"] == ["Office"]
    assert error_of(api.load_layout, "Away").code == "unknown_layout"
    assert error_of(api.save_layout, "  ").code == "bad_value"


def test_arranging_needs_a_widget_and_the_plugin(desk, monkeypatch):
    assert error_of(api.arrange_widgets).code == "nothing_to_arrange"
    api.update_widget("clock", {"enabled": True})
    monkeypatch.setattr(widgets, "start_editing", lambda: False)
    assert error_of(api.arrange_widgets).code == "not_ready"
    monkeypatch.setattr(widgets, "start_editing", lambda: True)
    assert api.arrange_widgets() == {"ok": True}


def test_wire_shell_survives_odd_plugins(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "has_omarchy_shell", lambda: True)
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / widgets.PLUGIN).symlink_to(install.PLUGINS[widgets.PLUGIN])
    monkeypatch.setattr(install, "plugins_dir", lambda: plugins)
    shell = tmp_path / "shell.json"
    shell.write_text(json.dumps({"plugins": {"not": "a list"}}))
    monkeypatch.setattr(install, "shell_json", lambda: shell)
    state = widgets.normalize({"clock": {"enabled": True}})
    assert widgets.wire_shell(state) == ["shell.json"]
    assert json.loads(shell.read_text())["plugins"] == [{"id": widgets.PLUGIN}]


# --- fixes around it -------------------------------------------------------------------


def test_a_rejected_monitor_rule_is_not_recorded(desk, monkeypatch):
    def refuse(*args):
        if args[0] == "eval":
            desk.calls.append(args)
            return "error: bad monitor rule"
        return desk(*args)
    monkeypatch.setattr(hypr, "hyprctl", refuse)
    cfg = config.load()
    config.set_setting(cfg, LAPTOP_ID, "rotation", 180)
    assert apply.apply(cfg) == []
    assert apply.load_applied() == {}
    assert hypr.rejected("error: nope") and not hypr.rejected("ok") and not hypr.rejected("")


def test_hyprctl_gives_up_after_a_timeout(monkeypatch):
    def hang(*args, **kwargs):
        raise hypr.subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))
    monkeypatch.setattr(hypr.subprocess, "run", hang)
    monkeypatch.setattr(hypr, "hyprctl", REAL_HYPRCTL)
    assert hypr.hyprctl("monitors") == "error: hyprctl timed out"
    assert hypr.monitors() == []


def test_cli_no_longer_has_the_menu_commands(desk):
    from hypr_screens import cli

    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["step", "Laptop", "rotation", "1"])
    assert not hasattr(engine, "step_value") and "command" not in engine.state(config.default_config())


def test_save_leaves_no_temporary_on_failure(monkeypatch):
    def broken(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(config.os, "replace", broken)
    with pytest.raises(OSError):
        config.save(config.default_config())
    assert [p for p in config.config_file().parent.iterdir()] == []
    assert os.environ["XDG_CONFIG_HOME"] in str(config.config_file())


def test_undoing_a_layout_load_brings_back_unsaved_widgets(desk):
    api.update_widget("clock", {"enabled": True})
    api.save_layout("Desk")
    api.update_widget("clock", {"enabled": False})  # not saved anywhere

    loaded = api.load_layout("Desk")
    assert config.load()["widgets"]["clock"]["enabled"] is True
    api.restore_widgets(loaded["previous"])
    assert config.load()["widgets"]["clock"]["enabled"] is False
    assert error_of(api.restore_widgets, "nothing").code == "bad_value"
