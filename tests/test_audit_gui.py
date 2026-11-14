"""Audit fixes of the settings window: an unconfirmed screen setting goes back
when the window closes (DAT-08), undo of a layout load does not overwrite later
changes (DAT-06), the page's own writes are told from outside ones (BUG-17),
the close clean-up waits for a running call (BUG-24, BUG-19) and a tray with
old code restarts (OPS-01)."""
import json
import os

import pytest

from hypr_screens import config, widgets as widgets_mod
from hypr_screens.api import ApiError, call, displays


@pytest.fixture()
def cfg_home(tmp_path, monkeypatch):
    (tmp_path / "run").mkdir(exist_ok=True)
    monkeypatch.setattr(displays, "run_sync", lambda: ["applied"])
    monkeypatch.setattr(displays, "recorded", lambda: (config.read(), []))
    config.save(config.load())
    return tmp_path


def seed_screen(sid="S1"):
    def mutate(cfg):
        cfg["screens"][sid] = {"name": sid, "internal": False, "settings": {}}
    config.update(mutate)
    return sid


def test_unconfirmed_screen_setting_goes_back_on_close(cfg_home):
    sid = seed_screen()
    displays.set_screen_setting(sid, "scale", 2, None, True)
    assert config.get_setting(config.read(), sid, "scale")["value"] == 2
    displays.revert_pending_keep()
    assert config.get_setting(config.read(), sid, "scale") in (None, {"value": None, "when": None})\
        or config.get_setting(config.read(), sid, "scale").get("value") is None


def test_confirmed_screen_setting_stays(cfg_home):
    sid = seed_screen()
    displays.set_screen_setting(sid, "scale", 2, None, True)
    displays.clear_pending_keep()
    displays.revert_pending_keep()
    assert config.get_setting(config.read(), sid, "scale")["value"] == 2


def test_a_change_without_arm_is_never_reverted(cfg_home):
    sid = seed_screen()
    displays.set_screen_setting(sid, "scale", 2)
    displays.revert_pending_keep()
    assert config.get_setting(config.read(), sid, "scale")["value"] == 2


def test_restore_widgets_refuses_after_a_later_change(cfg_home):
    before = widgets_mod.normalize(config.read()["widgets"])
    changed = json.loads(json.dumps(before))
    kind = next(iter(changed))
    changed[kind]["x"] = 0.123
    config.update(lambda cfg: cfg.__setitem__("widgets", widgets_mod.normalize(changed)))
    loaded = widgets_mod.normalize(config.read()["widgets"])
    config.update(lambda cfg: cfg["widgets"][kind].__setitem__("x", 0.9))  # a later change
    with pytest.raises(ApiError) as error:
        call("restoreWidgets", [before, loaded])
    assert error.value.code == "conflict"
    assert config.read()["widgets"][kind]["x"] == 0.9


def test_code_stamp_changes_with_the_code(tmp_path, monkeypatch):
    pytest.importorskip("gi")
    from hypr_screens.gui import app

    monkeypatch.setattr(app, "PACKAGE", tmp_path)
    (tmp_path / "a.py").write_text("x = 1")
    first = app.code_stamp()
    os.utime(tmp_path / "a.py", ns=(first[0] + 10**9, first[0] + 10**9))
    assert app.code_stamp() != first
    (tmp_path / "b.py").write_text("y = 2")
    assert app.code_stamp()[1] == 2


def test_own_write_is_not_an_outside_change(cfg_home):
    pytest.importorskip("gi")
    from hypr_screens.gui import web_window

    own = web_window.config_stat()
    assert web_window.config_stat() == own
    config.update(lambda cfg: cfg.__setitem__("language", "de" if cfg.get("language") != "de" else "en"))
    assert web_window.config_stat() != own  # someone else wrote: refresh


def test_close_release_waits_for_a_running_call(monkeypatch):
    pytest.importorskip("gi")
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from hypr_screens.gui import web_window

    events, started, go = [], threading.Event(), threading.Event()
    monkeypatch.setattr(web_window, "release_key_capture", lambda: events.append("keys"))
    monkeypatch.setattr(web_window, "release_pending", lambda: events.append("pending"))
    worker = ThreadPoolExecutor(max_workers=1)

    def slow_call():
        started.set()
        go.wait(2)
        events.append("call-ended")
    worker.submit(slow_call)
    started.wait(2)
    worker.shutdown(wait=False, cancel_futures=True)
    thread = threading.Thread(target=web_window.release_after_close, args=(worker,))
    thread.start()
    go.set()
    thread.join(3)
    assert events == ["keys", "call-ended", "keys", "pending"]
