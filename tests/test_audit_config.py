"""Audit fixes: settings that survive an older writer (DAT-01), symlinks and
temporaries (DAT-05, OPS-04), shell.json writes, stale update status (BUG-33),
the pending setup of a failed update (BUG-04) and the uninstall (DAT-03, BUG-27)."""
import json
import os
import time

import pytest

from hypr_screens import config, install, uninstall, updates


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    (tmp_path / "run").mkdir()
    return tmp_path


def test_save_keeps_what_this_version_does_not_know(home):
    path = config.config_file()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"future_switch": True, "look": {"future_look": 3, "gap": 5},
                                "camera": {"future_cam": "x"}, "widgets": {"clock": {"future_key": 1},
                                                                          "newkind": {"a": 1}}}))
    cfg = config.read()
    cfg["language"] = "de"
    config.save(cfg)
    saved = json.loads(path.read_text())
    assert saved["language"] == "de"
    assert saved["future_switch"] is True
    assert saved["look"]["future_look"] == 3
    assert saved["camera"]["future_cam"] == "x"
    assert saved["widgets"]["clock"]["future_key"] == 1 and saved["widgets"]["newkind"] == {"a": 1}


def test_a_known_setting_can_still_be_removed(home):
    path = config.config_file()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"look": {"anim_speed": 2.0}}))
    config.update(lambda cfg: cfg["look"].pop("anim_speed"))
    assert "anim_speed" not in json.loads(path.read_text())["look"]


def test_save_keeps_a_symlinked_file_and_leaves_no_temporaries(home):
    target = home / "dotfiles" / "config.json"
    target.parent.mkdir()
    target.write_text("{}")
    link = config.config_file()
    link.parent.mkdir(parents=True)
    link.symlink_to(target)
    config.update(lambda cfg: cfg.__setitem__("language", "fr"))
    assert link.is_symlink() and json.loads(target.read_text())["language"] == "fr"
    assert not list(link.parent.glob(".config-*")) and not list(target.parent.glob(".config-*"))


def test_old_temporaries_of_a_killed_writer_are_cleaned_up(home):
    config.save(config.default_config())
    old = config.config_dir() / ".config-dead.tmp"
    old.write_text("half")
    os.utime(old, (time.time() - 3600,) * 2)
    fresh = config.config_dir() / ".config-live.tmp"
    fresh.write_text("busy")
    config.save(config.default_config())
    assert not old.exists() and fresh.exists()


def test_shell_json_write_keeps_symlink_and_mode(home):
    target = home / "dotfiles" / "shell.json"
    target.parent.mkdir()
    target.write_text("{}")
    target.chmod(0o640)
    link = home / "shell.json"
    link.symlink_to(target)
    install.write_json(link, {"bar": {}})
    assert link.is_symlink() and json.loads(target.read_text()) == {"bar": {}}
    assert target.stat().st_mode & 0o777 == 0o640
    assert [p.name for p in target.parent.iterdir()] == ["shell.json"]


def test_a_running_status_without_a_process_is_stale(home):
    updates.write_status(state="running", pid=2 ** 22 + 12345, log=["x"])
    assert updates.read_status()["state"] == "failed"
    updates.write_status(state="running", pid=os.getpid())
    assert updates.read_status()["state"] == "running"
    updates.write_status(state="running", pid=None)
    assert updates.read_status()["state"] == "running"
    old = time.time() - updates.START_SECONDS - 5
    os.utime(updates.status_file(), (old, old))
    assert updates.read_status()["state"] == "failed"


def test_pending_setup_is_offered_again(home, monkeypatch):
    monkeypatch.setattr(updates, "is_checkout", lambda: True)
    monkeypatch.setattr(updates, "upstream", lambda: "origin/master")
    monkeypatch.setattr(updates, "fetched", lambda remote: True)
    monkeypatch.setattr(updates, "counts", lambda remote: (0, 0))
    monkeypatch.setattr(updates, "latest_version", lambda remote: "1.0.0")
    assert updates.check()["canUpdate"] is False
    updates.mark_setup(True)
    assert updates.check()["canUpdate"] is True
    updates.mark_setup(False)
    assert updates.check()["canUpdate"] is False


def test_install_script_restarts_even_when_a_step_fails():
    text = (install.REPO / "install.sh").read_text()
    assert "trap finish EXIT" in text and 'restart --open >/dev/null' in text
    assert text.index("trap finish EXIT") < text.index("Packages and system setup")


def test_uninstall_stops_when_the_root_teardown_fails(home, monkeypatch):
    calls = []
    monkeypatch.setattr(uninstall.install, "stop", lambda: [])
    monkeypatch.setattr(uninstall, "bring_back_windows", lambda: [])
    monkeypatch.setattr(uninstall.samsung, "end_full_charge", lambda cfg: None)
    monkeypatch.setattr(uninstall, "root_files", lambda graphical: (["kept x"], False))
    for name in ("lua_files", "folders"):
        monkeypatch.setattr(uninstall, name, lambda *a, _n=name: calls.append(_n) or [])
    monkeypatch.setattr(uninstall.install, "remove_launchers", lambda: calls.append("launchers") or {})
    with pytest.raises(uninstall.Incomplete) as stopped:
        uninstall.run()
    assert stopped.value.done == ["kept x"] and calls == []
    assert uninstall.main(False, True) == 1


def test_uninstall_gives_tags_and_size_back(monkeypatch):
    sent = []
    monkeypatch.setattr(uninstall.hypr, "dispatch", sent.append)
    tiled = {"tags": [uninstall.TILED_TAG]}
    uninstall.restore_state(tiled, 'window = "address:0x1"')
    assert any('action = "disable"' in line for line in sent) and any(f'-{uninstall.TILED_TAG}' in l for l in sent)
    sent.clear()
    shrunk = {"tags": [uninstall.SHRUNK_TAG], "at": [100, 100], "size": [850, 850]}
    uninstall.restore_state(shrunk, 'window = "address:0x2"')
    assert "x = 1000, y = 1000" in sent[0] and f"-{uninstall.SHRUNK_TAG}" in sent[-1]
