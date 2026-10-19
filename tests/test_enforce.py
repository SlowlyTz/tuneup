"""Enforcement: drift found and put back, the back-off against fights, the status
for the settings window, and the watcher's timing -- against the Hyprland model."""
import os

import pytest

from hypr_screens import api, apply, config, desktops, drift, drm, engine, enforce, hypr, keybinds, look, sound, watch
from hyprland_model import HyprlandModel, hp_output, laptop_output, tv_output
from test_hotplug import HP_ID, run


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(apply.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(drm, "SYSFS", tmp_path / "sys")
    monkeypatch.setattr(drift, "_dark_before", set())
    monkeypatch.setattr(drift, "_handled", set())
    monkeypatch.setattr(look, "ANIMATION_FILES", [])


@pytest.fixture()
def docked(monkeypatch):
    """Laptop and HP (above, one desktop), the look and desktop keys set, all applied."""
    model = HyprlandModel(laptop_output())
    model.static_options = model.options = {"general:gaps_in": 5}
    monkeypatch.setattr(hypr, "hyprctl", model)

    def settings(cfg):
        cfg["screens"].setdefault(HP_ID, {"favorite": False, "settings": {}})
        config.set_setting(cfg, HP_ID, "position", "above")
        config.set_setting(cfg, HP_ID, "one_desktop", True)
        cfg["look"] = {"gaps_in": 5}
        cfg["desktop_keys"] = True
    cfg = config.update(settings)
    model.plug(hp_output())
    run(model, "added")
    keybinds.go_live(None, cfg)
    assert drift.run() == []          # all in place
    return model


# --- the checks put back what drifted ---------------------------------------------------


def test_a_screen_moved_by_another_app_is_put_back(docked):
    model = docked
    spot = model.box("DP-3")
    model.runtime_rules["DP-3"] = {**model.runtime_rules["DP-3"], "position": "1920x0"}
    model.arrange()
    assert drift.run() == ["screens: DP-3 moved or changed"]
    assert model.box("DP-3") == spot and model.touching("eDP-1", "DP-3")
    assert enforce.view(config.load())["fixes"][0]["what"] == "Screen arrangement"
    assert drift.run() == []


def test_the_fixed_desktop_comes_back_to_its_screen(docked):
    model = docked
    model.move_workspace(desktops.FIXED_WS, model.monitor("eDP-1"))
    fixed = drift.run()
    assert fixed and fixed[0].startswith("desktops:")
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    assert drift.run() == []


def test_window_look_and_keys_come_back(docked):
    model = docked
    model.options["general:gaps_in"] = 0
    model.binds = [b for b in model.binds if b["description"] != "Minimize window"]
    model.binds.append(model.bind("SUPER + M", "Something else"))
    fixed = drift.run()
    assert [f.split(":")[0] for f in fixed] == ["look", "keys"]
    assert model.options["general:gaps_in"] == 5
    assert [b["description"] for b in model.binds if b["combo"] == "SUPER + M"] == ["Minimize window"]
    assert drift.run() == []


def test_a_look_preview_is_left_alone(docked):
    model = docked
    drift.mark_preview(True)
    model.options["general:gaps_in"] = 20
    assert drift.run() == []
    drift.mark_preview(False)
    assert drift.run()[0].startswith("look:")


def test_nothing_is_put_back_while_switched_off_or_while_a_sync_runs(docked):
    model = docked
    model.move_workspace(desktops.FIXED_WS, model.monitor("eDP-1"))
    with apply.locked("sync"):
        assert drift.run() == []
    api.set_enforcement(False)
    calls = len(model.calls)
    assert drift.run() == []
    assert not [c for c in model.calls[calls:] if c[0] in ("eval", "dispatch")]
    assert api.enforcement()["enabled"] is False


# --- fights --------------------------------------------------------------------------------


def test_a_fight_backs_off_and_gets_longer_each_time(docked):
    model = docked

    def other_app():
        model.options["general:gaps_in"] = 0
    now = 1000.0
    for _ in range(enforce.MAX_FIXES + 1):
        other_app()
        assert not enforce.backed_off("look", "look", now)
        drift.run()
    assert enforce.backed_off("look", "look")
    other_app()
    assert drift.run() == []                       # left alone now
    status = enforce.view(config.load())
    assert [b["what"] for b in status["backedOff"]] == ["Window look"]

    entry = enforce.load_status()["backoff"]["look:look"]
    first = entry["until"]
    for _ in range(enforce.MAX_FIXES + 1):
        enforce.record("look", "look", "x", now=first + 1)
    second = enforce.load_status()["backoff"]["look:look"]
    assert second["level"] == 2 and second["until"] - (first + 1) == 2 * enforce.BACKOFF_FIRST


def test_force_mute_never_backs_off():
    for _ in range(10):
        enforce.record("sound", "force_mute", "Laptop speakers")
    assert not enforce.backed_off("sound", "force_mute")
    fixes = enforce.load_status()["fixes"]
    assert len(fixes) == 1 and fixes[0]["what"] == "Force mute"   # repeats are folded


def test_force_mute_reports_the_devices_it_silenced(monkeypatch):
    node = {"name": "alsa_output.speaker", "description": "Speaker", "mute": False,
            "volume": {"front-left": {"value_percent": "40%"}}, "properties": {}, "ports": []}
    monkeypatch.setattr(sound, "pactl_list", lambda what: [node] if what == "sinks" else [])
    monkeypatch.setattr(sound, "pactl", lambda *args: "")
    cfg = config.default_config()
    cfg["sound"]["force_mute"] = {"alsa_output.speaker": {"kind": "sink", "label": "Laptop speakers",
                                                          "volume": 40, "mute": False}}
    heard = []
    assert sound.enforce(cfg, report=heard.append) == 2
    assert heard == [["Laptop speakers"]]


def test_status_shape_and_heartbeat():
    status = enforce.view(config.default_config(), now=100.0)
    assert status == {"enabled": True, "running": False, "fixes": [], "backedOff": []}
    enforce.heartbeat()
    assert api.enforcement()["running"] is True
    assert api.set_enforcement(True)["enabled"] is True
    with pytest.raises(api.ApiError) as error:
        api.set_enforcement("yes")
    assert error.value.code == "bad_value"


# --- a screen without a picture ----------------------------------------------------------


def drm_connector(root, name, status, enabled):
    folder = root / "class/drm" / f"card1-{name}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "status").write_text(status + "\n")
    (folder / "enabled").write_text(enabled + "\n")


def test_a_dark_screen_after_an_mst_dock_is_switched_off_and_on(tmp_path, monkeypatch):
    model = HyprlandModel(laptop_output())
    monkeypatch.setattr(hypr, "hyprctl", model)
    told = []
    monkeypatch.setattr(drm, "tell_user", told.append)
    model.plug(tv_output())
    run(model, "added")
    keybinds.go_live(None, config.load())
    drm_connector(tmp_path / "sys", "eDP-1", "connected", "enabled")
    drm_connector(tmp_path / "sys", "DP-5", "disconnected", "enabled")    # the dock's, gone, still holding a CRTC
    drm_connector(tmp_path / "sys", "HDMI-A-1", "connected", "disabled")  # got that CRTC: dark
    assert drm.stale(drm.connectors()) == ["DP-5"]

    assert drift.run() == []                       # seen once: maybe still being set up
    evals = len(model.calls)
    assert drift.run() == ["screens: HDMI-A-1 without a picture"]
    sent = [c[1] for c in model.calls[evals:] if c[0] == "eval"]
    assert 'disabled = true' in sent[0] and 'output = "HDMI-A-1"' in sent[1] and "disabled" not in sent[1]
    assert told == ["HDMI-A-1"]                    # still dark in this fake: the user is told what helps
    assert drift.run() == []                       # once per time it goes dark
    drm_connector(tmp_path / "sys", "HDMI-A-1", "connected", "enabled")
    assert drift.run() == []


def test_screens_switched_off_while_idle_are_left_alone(tmp_path, monkeypatch):
    """Seen live: with the session idle, Hyprland turns the screens off by DPMS
    (no CRTC in the kernel either); taking that for the dock bug switched both
    screens off and on -- Hyprland ended up with no output, the lock screen had
    nowhere to show, and only a hard reset brought the picture back."""
    model = HyprlandModel(laptop_output())
    monkeypatch.setattr(hypr, "hyprctl", model)
    told = []
    monkeypatch.setattr(drm, "tell_user", told.append)
    model.plug(hp_output())
    run(model, "added")
    keybinds.go_live(None, config.load())
    for monitor in model.monitors:
        monitor["dpmsStatus"] = False
    drm_connector(tmp_path / "sys", "eDP-1", "connected", "disabled")
    drm_connector(tmp_path / "sys", "DP-3", "connected", "disabled")

    evals = len(model.calls)
    assert drift.run() == [] and drift.run() == []
    assert not [c for c in model.calls[evals:] if c[0] == "eval" and "disabled = true" in c[1]]
    assert told == []


def test_the_laptop_panel_never_counts_as_dark():
    found = {"eDP-1": {"status": "connected", "enabled": "disabled"},
             "HDMI-A-1": {"status": "connected", "enabled": "disabled"}}
    panel = {"name": "eDP-1", "disabled": False, "dpmsStatus": True}
    tv = {"name": "HDMI-A-1", "disabled": False, "dpmsStatus": True}
    assert drm.dark([panel, tv], found) == ["HDMI-A-1"]
    assert drm.dark([panel, {**tv, "dpmsStatus": False}], found) == []


# --- the watcher's timing ---------------------------------------------------------------------


def test_watcher_settles_bursts_skips_its_own_reload_and_audits(monkeypatch):
    synced, audited = [], []
    monkeypatch.setattr(engine, "sync", lambda kind="": synced.append(kind) or [])
    monkeypatch.setattr(drift, "run", lambda cfg=None: audited.append(1) or [])
    monkeypatch.setattr(watch.widgets, "auto_layout", lambda: "")
    watcher = watch.Watcher(now=0.0)
    watcher.feed([b"monitorremovedv2>>1,DP-3,HP", b"activewindow>>x"], now=0.0)
    watcher.feed([b"monitoraddedv2>>2,DP-5,HP"], now=0.5)
    assert watcher.tick(1.0) == [] and synced == []          # the burst is not over
    watcher.feed([b"activewindow>>y"], now=1.2)               # other events do not hold it up
    watcher.tick(1.6)
    assert synced == ["added"]

    apply.reload_mark().write_text(f"{apply.time.time()}\n")  # we just reloaded
    watcher.feed([b"configreloaded>>"], now=2.0)
    assert watcher.pending == set()

    watcher.tick(2.0 + enforce.AUDIT_SECONDS + 1)
    assert audited == [1]
    watcher.feed([b"moveworkspacev2>>99,99,eDP-1"], now=10.0)
    assert watcher.wait(10.0) <= watch.AUDIT_SOON_SECONDS
    assert os.path.exists(enforce.status_file())               # the heartbeat went out


def test_the_cli_switches_it(capsys):
    from hypr_screens import cli

    assert cli.run(cli.build_parser().parse_args(["enforce", "off"])) == 0
    assert config.load()["enforce"] is False
    assert '"enabled": false' in capsys.readouterr().out
    cli.run(cli.build_parser().parse_args(["enforce"]))
    assert '"running"' in capsys.readouterr().out
