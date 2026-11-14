"""Audit fixes for the keys: the Lua file is written once, atomically and without
a reload (BUG-02, DAT-04), the recorder ends safely (BUG-01, BUG-24), keys alone
and invalid key names are refused (BUG-06, BUG-07), Lua text is escaped (SEC-01)."""
import pytest

from hypr_screens import api, apply, config, drift, hypr, keybinds, look, scratch, setup
from hypr_screens.api import shortcuts
from test_api import FakeHyprland, error_of, hp, isolated, laptop  # noqa: F401 - fixtures


@pytest.fixture()
def desk(monkeypatch):
    hyprland = FakeHyprland([laptop(), hp()])
    monkeypatch.setattr(hypr, "hyprctl", hyprland)
    api.screens()
    hyprland.calls.clear()
    return hyprland


def evals(desk):
    return [call[1] for call in desk.calls if call[0] == "eval"]


def test_lua_text_cannot_leave_its_string():
    assert hypr.lua_string('a"b\\c\nd\x00e') == '"a\\"b\\\\c\\010d\\000e"'
    assert keybinds.parse("SUPER + A\nB") is None
    assert keybinds.parse('SUPER + A"') is None
    rule = look.normalize({"apps": [{"class": "ki\ntty", "active": 0.9, "inactive": 0.8}]})["apps"]
    assert rule[0]["class"] == "kitty"


def test_page_keys_use_xkb_names_and_old_spellings_are_migrated():
    assert keybinds.normalize("super + pageup") == "SUPER + PRIOR"
    assert keybinds.normalize("SUPER + PAGEDOWN") == "SUPER + NEXT"
    assert keybinds.known_key("PRIOR") and not keybinds.known_key("PAGEUP")
    cfg = config.default_config()
    cfg["keybinds"]["pop"] = ["SUPER + PAGEUP", ""]
    assert 'hl.bind("SUPER + PRIOR"' in keybinds.render(cfg)


def test_a_key_alone_or_an_unknown_key_is_refused(desk):
    assert error_of(api.set_key, "pop", 0, "Q").code == "bad_value"
    assert error_of(api.set_key, "pop", 0, "SPACE").code == "bad_value"
    assert error_of(api.set_key, "pop", 0, "SUPER + NOSUCHKEY").code == "bad_value"
    assert api.set_key("pop", 0, "F5")["slots"][0] == "F5"
    assert api.set_key("pop", 1, "ctrl+q")["slots"][1] == "CTRL + Q"
    assert config.load()["keybinds"]["pop"] == ["F5", "CTRL + Q"]


def test_an_unchanged_file_is_not_written_and_a_change_holds_the_autoreload_back(desk):
    cfg = config.default_config()
    keybinds.write(cfg)
    first = evals(desk)
    assert len(first) == 1 and "disable_autoreload = true" in first[0] and "tuneup_autoreload_was" in first[0]
    stamp = keybinds.lua_file().stat().st_mtime_ns
    keybinds.write(cfg)
    assert len(evals(desk)) == 1 and keybinds.lua_file().stat().st_mtime_ns == stamp
    cfg["no_warps"] = True
    keybinds.write(cfg)
    assert len(evals(desk)) == 2
    assert [p.name for p in keybinds.hypr_dir().iterdir()] == ["tuneup.lua"]  # no temporary left


def test_saving_a_key_writes_once_and_never_reloads(desk):
    api.set_key("pop", 1, "SUPER + J")
    assert desk.reloads == 0
    assert 'hl.bind("SUPER + J"' in keybinds.lua_file().read_text()
    api.set_key("pop", 1, "SUPER + J")  # the same again: nothing to write
    assert sum('disable_autoreload = true' in code for code in evals(desk)) == 1


def test_go_live_defines_the_recorder_once(desk):
    cfg = config.default_config()
    keybinds.go_live(None, cfg)
    assert "define_submap" in evals(desk)[-1]
    desk.binds = [{"modmask": 0, "key": "escape", "submap": keybinds.RECORD_SUBMAP, "description": ""}]
    keybinds.go_live(None, cfg, settled=True)
    code = evals(desk)[-1]
    assert "define_submap" not in code and "blur = true" not in code and "hl.gesture" not in code


def test_escape_in_the_recorder_reaches_the_page_too():
    lua = keybinds.render(config.default_config())
    assert 'hl.bind("escape", hl.dsp.submap("reset"), { non_consuming = true })' in lua


def test_a_minimized_window_asked_for_comes_back_through_the_minimizer():
    lua = keybinds.render(config.default_config())
    assert 'there.name == "special:minimized"' in lua and "hypr-minimizer fetch" in lua


def test_a_recording_that_cannot_start_fails_and_one_that_ended_is_seen(desk, monkeypatch):
    monkeypatch.setattr(hypr, "dispatch", lambda expression: "error: no such dispatcher")
    assert error_of(api.begin_key_capture).code == "capture_failed"
    assert shortcuts._capturing is False
    monkeypatch.undo()
    monkeypatch.setattr(hypr, "hyprctl", desk)
    answers = iter([keybinds.RECORD_SUBMAP, "default"])
    monkeypatch.setattr(hypr, "hyprctl", lambda *args: next(answers) if args == ("submap",) else "ok")
    shortcuts._capturing = True
    assert api.key_capture_active() == {"active": True}
    assert api.key_capture_active() == {"active": False}  # Esc left the keymap
    assert shortcuts._capturing is False


def test_a_capture_nobody_asks_about_ends_by_itself(desk, monkeypatch):
    """The window closed while begin_key_capture was still running (BUG-24)."""
    ticks = iter([0.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(shortcuts.time, "monotonic", lambda: next(ticks, 100.0))
    monkeypatch.setattr(shortcuts.time, "sleep", lambda seconds: None)
    api.begin_key_capture()
    shortcuts._watch_capture()
    assert shortcuts._capturing is False and desk.dispatched[-1] == 'hl.dsp.submap("reset")'


def test_switching_the_scratch_desktops_off_reloads_before_it_unparks(desk, monkeypatch):
    order = []
    monkeypatch.setattr(scratch, "unpark_all", lambda: order.append("unpark") or [])
    monkeypatch.setattr(keybinds.hypr, "hyprctl", lambda *args: order.append(args[0]) or "")
    before = config.default_config()
    after = {**before, "scratch": False}
    keybinds.option_changed(before, after, "scratch")
    assert order.index("reload") < order.index("unpark")


def test_an_option_that_does_not_move_desktops_does_not_sync(desk, monkeypatch):
    synced = []
    monkeypatch.setattr(shortcuts, "run_sync", lambda: synced.append(1))
    api.set_option("no_warps", True)
    assert synced == []
    api.set_option("fixed_desktops", 3)
    assert synced == [1]
    api.set_option("no_warps", False)  # switched off by a reload: the screens' settings again
    assert synced == [1, 1]


def test_a_broken_settings_file_binds_no_default_keys(desk):
    config.config_file().parent.mkdir(parents=True, exist_ok=True)
    config.config_file().write_text("{ not json")
    assert drift.run() == []
    assert evals(desk) == []


def test_setup_marks_its_reload_as_ours(desk):
    keybinds.hyprland_file().parent.mkdir(parents=True, exist_ok=True)
    keybinds.hyprland_file().write_text("-- config\n")
    setup.lua(config.default_config(), moved=False)
    assert desk.reloads == 1 and apply.reloaded_by_us(5.0)


def test_setup_reloads_once_when_an_update_changed_the_file(desk):
    keybinds.hyprland_file().parent.mkdir(parents=True, exist_ok=True)
    keybinds.hyprland_file().write_text(f"-- config\n{keybinds.REQUIRE_LINE}\n")
    cfg = config.default_config()
    keybinds.lua_file().parent.mkdir(parents=True, exist_ok=True)
    keybinds.lua_file().write_text("-- an older Tuneup\n")
    setup.lua(cfg, moved=False)
    assert desk.reloads == 1
    setup.lua(cfg, moved=False)
    assert desk.reloads == 1  # unchanged now: the keys go live by eval
