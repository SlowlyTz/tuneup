"""Scratch desktops: the Lua module run by a real Lua (5.5, as Hyprland links)
against tests/lua/fake_hl.lua, the generated Lua file, the animation to give
back, setup's decisions, and the rest of Tuneup treating 201+ as valid."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hypr_screens import config, desktops, drift, hypr, keybinds, scratch, setup
from hyprland_model import HyprlandModel, hp_output, laptop_output

LUA = next((shutil.which(name) for name in ("lua5.5", "lua5.4", "lua") if shutil.which(name)), None)
LUAC = next((shutil.which(name) for name in ("luac5.5", "luac5.4", "luac") if shutil.which(name)), None)
HERE = Path(__file__).resolve().parent


@pytest.mark.skipif(LUA is None, reason="no Lua interpreter")
def test_the_lua_module_flies_bounces_and_remembers(tmp_path):
    module = tmp_path / "module.lua"
    module.write_text(scratch.module_lua({"enabled": False}))
    done = subprocess.run([LUA, str(HERE / "lua" / "scratch_test.lua"), str(module)], capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout.strip() == "ok", done.stderr


@pytest.mark.skipif(LUAC is None, reason="no Lua compiler")
@pytest.mark.parametrize("desktop_keys", [True, False])
def test_the_whole_generated_file_is_valid_lua(tmp_path, desktop_keys):
    cfg = config.default_config()
    cfg.update(desktop_keys=desktop_keys, scratch_shift_s=True)
    path = tmp_path / "tuneup.lua"
    path.write_text(keybinds.render(cfg))
    done = subprocess.run([LUAC, "-p", str(path)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_keys_it_takes_over():
    cfg = config.default_config()
    lua = keybinds.render(cfg)
    assert 'hl.unbind("SUPER + S")' in lua and 'hl.unbind("SUPER + ALT + S")' in lua
    assert 'hl.bind("SUPER + S", function() if tuneup_scratch then tuneup_scratch.toggle() end end' in lua
    assert "SUPER + SHIFT + S" not in lua                  # not decided yet: left alone
    # Desktop keys off: Omarchy's own actions outside the row.
    assert ('tuneup_scratch.digit("switch", 3, hl.dsp.focus({ workspace = "3" })) '
            'else hl.dispatch(hl.dsp.focus({ workspace = "3" })) end end') in lua
    cfg.update(desktop_keys=True, scratch_shift_s=True)
    lua = keybinds.render(cfg)
    assert 'tuneup_scratch.digit("move", 3, hl.dsp.exec_cmd("tuneup move 3"))' in lua
    assert 'hl.bind("SUPER + SHIFT + S", function() if tuneup_scratch then tuneup_scratch.move_window()' in lua
    assert "tuneup_scratch" not in keybinds.render({**cfg, "scratch": False, "desktop_keys": False})


def test_three_fingers_up_open_the_row_and_down_close_it(monkeypatch):
    cfg = config.default_config()
    lua = keybinds.render(cfg)
    assert ('hl.gesture({ fingers = 3, direction = "up", action = function() if tuneup_scratch then '
            'tuneup_scratch.open() end end })') in lua
    assert 'direction = "down", action = function() if tuneup_scratch then tuneup_scratch.close()' in lua
    # Hyprland cannot take a gesture back and would run a second one too:
    # never in what goes live on every change ...
    assert "hl.gesture" not in keybinds.render(cfg, runtime=True)
    assert "hl.gesture" not in keybinds.render({**cfg, "scratch_swipe": False})
    assert "hl.gesture" not in keybinds.render({**cfg, "scratch": False})
    sent = []
    monkeypatch.setattr(hypr, "eval_lua", sent.append)
    keybinds.go_live(cfg, cfg)
    keybinds.go_live({**cfg, "scratch_swipe": False}, cfg)       # ... only once, when switched on
    keybinds.go_live(None, cfg)                                  # ... and by setup (an update)
    assert "hl.gesture" not in sent[0] and sent[1].count("hl.gesture") == 2 and sent[2].count("hl.gesture") == 2


def test_switching_the_swipes_off_reloads(model):
    from hypr_screens import cli

    assert cli.run(cli.build_parser().parse_args(["option", "scratch_swipe", "off"])) == 0
    assert config.load()["scratch_swipe"] is False and model.reloads == 1
    assert "hl.gesture" not in keybinds.lua_file().read_text()


def test_our_scratch_keys_are_ours_for_the_enforcer():
    cfg = {**config.default_config(), "scratch_shift_s": True}
    combos = dict(keybinds.wanted(cfg))
    assert combos["SUPER + S"] == scratch.TOGGLE_LABEL and combos["SUPER + SHIFT + S"] == scratch.MOVE_LABEL
    assert combos["SUPER + code:10"] == "Show desktop"      # the digits too, desktop keys or not
    assert scratch.TOGGLE_LABEL in keybinds.own_descriptions()
    binds = [HyprlandModel.bind(combo, label) for combo, label in keybinds.wanted(cfg)]
    assert keybinds.missing(cfg, binds) == []


def test_the_animation_given_back_is_hyprlands_own():
    animations = [{"name": "global", "overridden": True, "bezier": "default", "enabled": True, "speed": 10.0,
                   "style": ""},
                  {"name": "workspaces", "overridden": True, "bezier": "default", "enabled": False, "speed": 1.0,
                   "style": ""}]
    assert scratch.effective(animations, "workspaces") == {"enabled": False, "speed": 1.0, "bezier": "default",
                                                          "style": ""}
    animations[1]["overridden"] = False                       # not set: inherits from global
    assert scratch.effective(animations, "workspaces")["speed"] == 10.0
    assert scratch.lua_table({"enabled": False, "speed": 1.0, "bezier": "default", "style": ""}) == \
        '{ leaf = "workspaces", enabled = false, speed = 1, bezier = "default" }'


def test_written_while_in_the_row_it_does_not_keep_our_own_animation(monkeypatch):
    live = [[{"name": "workspaces", "overridden": True, **scratch.SLIDE}], []]
    monkeypatch.setattr(hypr, "hyprctl", lambda *args: json.dumps(live))
    monkeypatch.setattr(scratch, "from_files", lambda: {"enabled": False})
    assert scratch.user_animation() == {"enabled": False}
    live[0][0].update(style="slidefade", speed=4)
    assert scratch.user_animation()["style"] == "slidefade"


@pytest.fixture()
def model(monkeypatch):
    world = HyprlandModel(laptop_output())
    monkeypatch.setattr(hypr, "hyprctl", world)
    return world


def test_setup_takes_shift_s_only_when_it_is_free(model):
    model.binds = [model.bind("SUPER + SHIFT + S", "Screenshot region")]
    cfg, notes = setup.scratch_desktops(config.update(lambda cfg: None))
    assert cfg["scratch_shift_s"] is False and "left to Screenshot region" in notes[0]
    config.update(lambda cfg: cfg.__setitem__("scratch_shift_s", None))
    model.binds = [model.bind("SUPER + SHIFT + S", "Google Maps")]   # Omarchy's own default
    cfg, _notes = setup.scratch_desktops(config.load())
    assert cfg["scratch_shift_s"] is True
    model.binds = []
    cfg, notes = setup.scratch_desktops(cfg)                         # decided once
    assert cfg["scratch_shift_s"] is True and notes == []


def test_windows_left_in_the_scratchpad_move_to_the_first_scratch_desktop(model):
    model.clients = [{"address": "0xa", "class": "notes", "workspace": {"id": -98, "name": "special:scratchpad"}},
                     {"address": "0xb", "class": "web", "workspace": {"id": 1, "name": "1"}}]
    assert scratch.rescue_scratchpad() == ["notes"]
    assert model.clients[0]["workspace"]["id"] == scratch.FIRST and model.clients[1]["workspace"]["id"] == 1


def test_put_away_scratch_desktops_come_back_when_switched_off(model):
    """Without the keys nothing could open them again: switching scratch
    desktops off (or uninstalling) gives their windows back as normal desktops."""
    model.clients = [{"address": "0xa", "class": "notes", "workspace": {"id": -101, "name": scratch.PARKED + "202"}},
                     {"address": "0xb", "class": "web", "workspace": {"id": -97, "name": "special:minimized"}}]
    assert scratch.unpark_all() == ["notes"]
    assert model.clients[0]["workspace"]["id"] == 202 and model.clients[1]["workspace"]["name"] == "special:minimized"


def test_a_scratch_desktop_on_the_fixed_screen_is_no_drift(model):
    def settings(cfg):
        cfg["default_fixed"] = "external"
    config.update(settings)
    from hypr_screens import engine

    model.plug(hp_output())
    engine.sync("added")
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    model.focus_monitor(model.monitor("DP-3"))
    model.focus_workspace(scratch.FIRST)                  # SUPER + S on the fixed screen
    assert model.visible()["DP-3"] == scratch.FIRST
    assert drift.placement(drift.Audit(config.load())) == []
    engine.sync("")                                       # a sync keeps it there too
    assert model.visible()["DP-3"] == scratch.FIRST


def test_the_scratch_option_switches_it_off_with_a_reload(model, capsys):
    from hypr_screens import cli

    assert cli.run(cli.build_parser().parse_args(["option", "scratch", "off"])) == 0
    assert config.load()["scratch"] is False and model.reloads == 1
    assert "tuneup_scratch" not in keybinds.lua_file().read_text()
