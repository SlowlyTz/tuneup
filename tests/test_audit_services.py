"""Audit fixes in the background services: the watcher (reconnecting, restarting
on new code, closing windows only after a second look), the guards (camera,
sound, Samsung, enforcement status) and the scratch desktops' Lua."""
import json
import os
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from hypr_screens import camera, config, desktops, engine, enforce, hypr, samsung, scratch, sound, watch
from test_hotplug import Clock, five, isolated, on, plug, run, unplug, unplug_windows, watched, window, world  # noqa: F401
from test_samsung import ppd, put, sysfs  # noqa: F401

LUA = next((shutil.which(name) for name in ("lua5.5", "lua5.4", "lua") if shutil.which(name)), None)
HERE = Path(__file__).resolve().parent


# --- DAT-09: the lid closed -------------------------------------------------------------


def test_a_closed_lid_leaves_the_fixed_desktops_alone(five):
    """With the laptop screen off, the external one is all there is: its
    desktops must not be folded onto desktop 1 (they would not come back)."""
    model = five
    window(model, "0x1", desktops.FIXED_WS)
    window(model, "0x2", desktops.FIXED_WS + 2)
    model.close_lid()
    run(model, "removed")
    assert (on(model, "0x1"), on(model, "0x2")) == (desktops.FIXED_WS, desktops.FIXED_WS + 2)
    model.close_lid(closed=False)
    run(model, "added")
    assert (on(model, "0x1"), on(model, "0x2")) == (desktops.FIXED_WS, desktops.FIXED_WS + 2)


# --- DAT-02: closing windows needs a second look ----------------------------------------


def test_close_waits_for_a_second_look(five):
    model = five
    unplug_windows("close")
    window(model, "0x1", desktops.FIXED_WS + 1)
    window(model, "0x2", 2)
    assert engine.CLOSE_PENDING in unplug(model, "DP-3")
    assert on(model, "0x1") == desktops.FIXED_WS + 1         # nothing closed yet
    assert engine.CLOSE_PENDING not in engine.sync("removed", close_ok=True)
    assert on(model, "0x1") is None and on(model, "0x2") == 2


def test_a_dock_that_comes_back_closes_nothing(five, monkeypatch):
    model = five
    unplug_windows("close")
    window(model, "0x1", desktops.FIXED_WS)
    clock = Clock()
    watcher = watch.Watcher(clock.now)
    monkeypatch.setattr(watch.widgets, "auto_layout", lambda: "")
    model.unplug("DP-3")
    watcher.feed([line.encode() for line in model.events], clock.now)
    model.events.clear()
    clock.now += watch.SETTLE_SECONDS + 0.1
    said = watcher.tick(clock.now)
    assert any("not closed yet" in line for line in said)
    assert on(model, "0x1") == desktops.FIXED_WS
    model.plug(__import__("hyprland_model").hp_output("DP-3"))   # the dock wakes up again
    watcher.feed([line.encode() for line in model.events], clock.now + 1)
    model.events.clear()
    clock.now += 1 + watch.SETTLE_SECONDS + 0.1
    watcher.tick(clock.now)
    clock.now += watch.CLOSE_SETTLE_SECONDS + 1
    watcher.tick(clock.now)
    assert on(model, "0x1") is not None


def test_a_screen_that_stays_away_is_closed_after_the_longer_wait(five, monkeypatch):
    model = five
    unplug_windows("close")
    window(model, "0x1", desktops.FIXED_WS)
    clock = Clock()
    watcher = watch.Watcher(clock.now)
    monkeypatch.setattr(watch.widgets, "auto_layout", lambda: "")
    model.unplug("DP-3")
    watcher.feed([line.encode() for line in model.events], clock.now)
    model.events.clear()
    clock.now += watch.SETTLE_SECONDS + 0.1
    watcher.tick(clock.now)
    assert watcher.wait(clock.now) > watch.SETTLE_SECONDS    # the longer pause
    clock.now += watch.CLOSE_SETTLE_SECONDS + 0.1
    assert any(line.startswith("closing") for line in watcher.tick(clock.now))
    assert on(model, "0x1") is None


def test_a_mirrored_or_sleeping_screen_is_not_closed_for(five, monkeypatch):
    model = five
    unplug_windows("close")
    window(model, "0x1", desktops.FIXED_WS)
    model.unplug("DP-3")
    monkeypatch.setattr(desktops, "external_listed", lambda: True)
    assert engine.CLOSE_PENDING not in engine.sync("removed", close_ok=True)
    assert on(model, "0x1") == desktops.FIXED_WS


def test_the_other_options_still_act_at_once(five):
    model = five
    unplug_windows("fold")
    window(model, "0x1", desktops.FIXED_WS)
    unplug(model, "DP-3")
    assert on(model, "0x1") in desktops.DESKTOPS


# --- BUG-22: the watcher connects again ---------------------------------------------------


class FakeEvents:
    """A socket that is closed at once."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def settimeout(self, seconds):
        pass

    def recv(self, size):
        return b""


@pytest.fixture()
def quiet_watcher(monkeypatch):
    monkeypatch.setattr(watch, "start_guards", lambda: None)
    monkeypatch.setattr(watch.widgets, "export", lambda cfg: "")
    monkeypatch.setattr(watch, "safe_sync", lambda kind: kind)
    monkeypatch.setattr(watch, "try_restart", lambda watcher: None)


def test_the_watcher_connects_again_with_a_growing_pause(quiet_watcher, monkeypatch, tmp_path):
    socket_file = tmp_path / "events"
    socket_file.touch()
    monkeypatch.setattr(watch, "event_socket", lambda: socket_file)
    attempts, pauses = [], []

    def connect(path):
        attempts.append(path)
        if len(attempts) in (2, 3):
            raise ConnectionRefusedError("no")
        if len(attempts) == 5:
            socket_file.unlink()          # Hyprland is gone
        return FakeEvents()

    monkeypatch.setattr(watch, "connect", connect)
    assert watch.watch(sleep=pauses.append) == 0
    assert len(attempts) == 5
    # a good connection starts the pause over; refused ones double it
    assert pauses == [1.0, 2.0, 4.0, 1.0]


def test_the_pause_never_grows_past_the_maximum(quiet_watcher, monkeypatch, tmp_path):
    socket_file = tmp_path / "events"
    socket_file.touch()
    monkeypatch.setattr(watch, "event_socket", lambda: socket_file)
    pauses = []
    monkeypatch.setattr(watch, "connect", lambda path: (_ for _ in ()).throw(OSError("down")))

    def sleep(seconds):
        pauses.append(seconds)
        if len(pauses) == 9:
            socket_file.unlink()

    assert watch.watch(sleep=sleep) == 0
    assert max(pauses) == watch.RECONNECT_MAX and pauses[:3] == [1.0, 2.0, 4.0]


def test_without_a_socket_the_watcher_gives_up(quiet_watcher, monkeypatch):
    monkeypatch.setattr(watch, "event_socket", lambda: None)
    assert watch.watch() == 1


# --- OPS-01: new code means a new watcher -------------------------------------------------


def test_changed_files_restart_the_watcher_once_they_hold_still(monkeypatch):
    stamps = [("a",), ("a",), ("b",), ("c",), ("c",), ("c",)]
    monkeypatch.setattr(watch, "STARTED_WITH", ("a",))
    monkeypatch.setattr(watch, "code_stamp", lambda: stamps.pop(0))
    watcher = watch.Watcher(0.0)
    seen = []
    for step in range(1, 6):
        watcher.check_code(step * watch.CODE_CHECK_SECONDS)
        seen.append(watcher.restart)
    # unchanged, then changed (still being written), changed again, then still: restart
    assert seen == [False, False, False, False, True]


def test_between_the_looks_nothing_is_stat_ed(monkeypatch):
    monkeypatch.setattr(watch, "code_stamp", lambda: pytest.fail("looked too soon"))
    watcher = watch.Watcher.__new__(watch.Watcher)
    watcher.next_code_check, watcher.restart = 100.0, False
    watcher.check_code(50.0)
    assert not watcher.restart


def test_code_that_does_not_load_is_not_started(monkeypatch):
    executed = []
    monkeypatch.setattr(os, "execv", lambda *args: executed.append(args))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, b"", b"boom"))
    monkeypatch.setattr(watch, "REFUSED", set())
    watch.restart_self()
    assert executed == [] and watch.REFUSED


def test_code_that_loads_replaces_the_process(monkeypatch):
    executed = []
    monkeypatch.setattr(os, "execv", lambda *args: executed.append(args))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, b"", b""))
    watch.restart_self()
    assert len(executed) == 1 and executed[0][0] == watch.sys.executable


def test_the_real_stamp_sees_the_package_files():
    count, newest, size = watch.code_stamp()
    assert count > 10 and newest > 0 and size > 0


# --- BUG-20 / BUG-31: the camera ----------------------------------------------------------


class FakeProcess:
    def __init__(self):
        self.stopped = False
        self.code = None
        self.stdin = open(os.devnull, "wb")

    def terminate(self):
        self.stopped = True

    def kill(self):
        self.stopped = True

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return self.code


def test_an_error_in_the_feeder_leaves_no_ffmpeg_behind(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    virtual = tmp_path / "video42"
    virtual.write_text("")
    feeder = camera.Feeder(virtual, tmp_path / "video0")
    reader, writer = FakeProcess(), FakeProcess()
    feeder.reader, feeder.writer = reader, writer

    def boom():
        raise RuntimeError("config exploded")

    monkeypatch.setattr(camera.enforce, "cached_config", boom)
    with pytest.raises(RuntimeError):
        feeder.run()
    assert reader.stopped and writer.stopped
    assert feeder.reader is None and feeder.writer is None


def test_a_writer_that_keeps_ending_is_started_with_growing_pauses(tmp_path, monkeypatch):
    feeder = camera.Feeder(tmp_path / "video42", tmp_path / "video0")
    clock = {"now": 100.0}
    monkeypatch.setattr(camera.time, "monotonic", lambda: clock["now"])
    started = []

    def start():
        started.append(clock["now"])
        feeder.writer_started = clock["now"]
        feeder.writer = FakeProcess()
        feeder.writer.stdin = open(os.devnull, "wb")
        feeder.writer.code = 1                   # ffmpeg ends at once

    monkeypatch.setattr(feeder, "start_writer", start)
    for _ in range(40):
        feeder.keep_writer()
        clock["now"] += 0.25
    gaps = [b - a for a, b in zip(started, started[1:])]
    assert len(started) <= 10
    assert [round(g) for g in gaps[:3]] == [1, 1, 2] and gaps[0] < gaps[1] < gaps[2]


def test_a_healthy_writer_resets_the_pause(tmp_path, monkeypatch):
    feeder = camera.Feeder(tmp_path / "video42", tmp_path / "video0")
    clock = {"now": 100.0}
    monkeypatch.setattr(camera.time, "monotonic", lambda: clock["now"])
    feeder.writer_failures = 4
    feeder.writer = FakeProcess()
    feeder.writer.stdin = open(os.devnull, "wb")
    feeder.writer_started = clock["now"] - 60
    feeder.writer.code = 1
    monkeypatch.setattr(feeder, "start_writer", lambda: None)
    feeder.keep_writer()
    assert feeder.writer_retry_at == clock["now"] + camera.WRITER_RETRY_FIRST


def test_writing_without_a_writer_is_no_crash(tmp_path):
    assert not camera.Feeder(tmp_path / "video42", tmp_path / "video0").write(b"frame")


def test_a_preview_request_in_an_unwritable_place_is_no_error(monkeypatch, tmp_path):
    monkeypatch.setattr(camera, "preview_request_file", lambda: tmp_path / "missing" / "wanted")
    camera.request_preview()


# --- BUG-21 / BUG-32: sound guard and the status file --------------------------------------


class Stop(BaseException):
    pass


def test_events_do_not_start_a_check_storm(monkeypatch):
    """100 device events a second -- an app fighting the mute -- bring a few checks, not hundreds."""
    read, write = os.pipe()
    checks = []

    class Pactl:
        stdout = os.fdopen(read, "rb", buffering=0)

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def terminate(self):
            pass

    def check():
        checks.append(time.monotonic())
        if len(checks) > 60:
            raise Stop

    monkeypatch.setattr(sound.subprocess, "Popen", Pactl)
    monkeypatch.setattr(sound, "check", check)
    stop = threading.Event()

    def feed():
        while not stop.is_set():
            os.write(write, b"Event 'change' on sink #1\n")
            time.sleep(0.01)

    thread = threading.Thread(target=feed, daemon=True)
    thread.start()
    result = []

    def guard():
        try:
            sound.guard()
        except Stop:
            result.append("stopped")

    runner = threading.Thread(target=guard, daemon=True)
    runner.start()
    time.sleep(1.5)
    stop.set()
    assert len(checks) <= 9, checks      # one at the start, then about one per gap


def test_a_failing_check_does_not_restart_pactl(monkeypatch, capsys):
    monkeypatch.setattr(sound, "enforce", lambda report=None: (_ for _ in ()).throw(KeyError("boom")))
    sound.check()
    assert "boom" in capsys.readouterr().err


def test_a_status_file_that_cannot_be_written_does_not_stop_the_mute(monkeypatch, capsys):
    monkeypatch.setattr(sound.enforcement, "record", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    sound.report_silenced(["Speaker"])
    assert "cannot record" in capsys.readouterr().err


def test_broken_entries_in_the_status_file_are_dropped(tmp_path):
    enforce.status_file().write_text(json.dumps({
        "heartbeat": 5.0, "pid": "x",
        "fixes": [{"time": 1.0, "area": "keys", "what": "Shortcuts", "detail": ""}, "junk", {"area": "keys"}],
        "history": {"keys:keys": [1.0, "x", None], "a": "junk"},
        "backoff": {"keys:keys": "junk", "screens:layout": {"until": 5.0, "level": 1}, "b": {"until": "x"}},
    }))
    status = enforce.load_status()
    assert len(status["fixes"]) == 1 and status["history"] == {"keys:keys": [1.0]}
    assert list(status["backoff"]) == ["screens:layout"] and status["pid"] == 0
    assert enforce.record("sound", "force_mute", "Speaker") is False       # no exception
    assert enforce.view(config.default_config())["fixes"][0]["detail"] == "Speaker"
    assert enforce.backed_off("keys", "keys") is False


# --- OPS-02 / ARC-04: less load, no slow calls under the lock -----------------------------


def test_the_config_is_read_again_only_when_the_file_changed(monkeypatch):
    config.update(lambda cfg: None)
    loads = []
    real = config.load
    monkeypatch.setattr(config, "load", lambda: loads.append(1) or real())
    first = enforce.cached_config()
    assert enforce.cached_config() is first and len(loads) == 1
    config.update(lambda cfg: cfg.__setitem__("enforce", False))
    changed = enforce.cached_config()
    assert changed["enforce"] is False and len(loads) == 2


def test_the_samsung_guard_calls_busctl_outside_the_settings_lock(sysfs, ppd, monkeypatch):
    config.update(lambda cfg: cfg.__setitem__("samsung", {"limit": 70, "mode": "quiet", "full_once": False}))
    monkeypatch.setattr(samsung, "writable", lambda: True)
    held = []

    @contextmanager
    def locked():
        held.append(True)
        try:
            yield
        finally:
            held.pop()

    monkeypatch.setattr(config, "locked", locked)
    seen = []
    real = samsung.ppd_profile
    monkeypatch.setattr(samsung, "ppd_profile", lambda: seen.append(bool(held)) or real())
    samsung.guard_once(enforce)
    assert seen == [False]
    assert samsung.number(sysfs / "class/power_supply/BAT1/charge_control_end_threshold") == 70


def test_the_keyboard_mode_key_is_still_taken_over(sysfs, ppd, monkeypatch):
    config.update(lambda cfg: cfg.__setitem__("samsung", {"limit": 80, "mode": "quiet", "full_once": False}))
    monkeypatch.setattr(samsung, "writable", lambda: True)
    put(sysfs / "class/platform-profile/platform-profile-0/profile", "performance")
    samsung.guard_once(enforce)
    assert config.load()["samsung"]["mode"] == "performance"


def test_the_daemon_is_asked_only_every_few_seconds(sysfs, ppd, monkeypatch):
    config.update(lambda cfg: cfg.__setitem__("samsung", {"limit": 80, "mode": "balanced", "full_once": False}))
    monkeypatch.setattr(samsung, "writable", lambda: True)
    asked = []
    monkeypatch.setattr(samsung, "ppd_profile", lambda: asked.append(1) or "")
    for tick in range(10):
        samsung.guard_once(enforce, check_ppd=tick % samsung.PPD_SECONDS == 0)
    assert len(asked) == 2


# --- BUG-14 / BUG-15: scratch desktops ----------------------------------------------------

LUA_TEST = r'''
package.path = arg[0]:match("(.*/)") .. "?.lua;" .. package.path
local fake = require("fake_hl")
local function check(cond, message)
  if not cond then io.stderr:write("FAILED: " .. message .. "\n") os.exit(1) end
end
local laptop = fake.add_monitor("eDP-1", 3)
local hp = fake.add_monitor("DP-3", 99)
assert(loadfile(arg[1]))()
fake.open_window("terminal")
tuneup_scratch.toggle()
fake.run_timers()
local notes = fake.open_window("notes")
check(notes.workspace.id == 201, "a window on scratch desktop 1")

-- A screen that does not say what it shows must not make the row look closed.
local before, before_hp = laptop.active_workspace, hp.active_workspace
laptop.active_workspace = nil
hp.active_workspace = nil
fake.fire("monitor.focused", laptop)
fake.run_timers()
check(not notes.workspace.special, "windows stay while the screens are in between")
laptop.active_workspace, hp.active_workspace = before, before_hp

-- Our own switch under way: the focus event in the middle of it puts nothing away.
local mail = fake.open_window("mail")
fake.fire("monitor.focused", laptop)
check(not mail.workspace.special, "a monitor.focused during a switch parks nothing at once")
fake.run_timers()
check(not mail.workspace.special and not notes.workspace.special, "the row is open: nothing put away")

-- A row that really is closed is put away -- but only after a second look.
tuneup_scratch.toggle()
fake.run_timers()
check(notes.workspace.special, "closed row: put away")

-- A row that opens again before the look is not put away.
tuneup_scratch.toggle()
fake.run_timers()
check(not notes.workspace.special, "row open again: windows are back")
fake.fire("monitor.focused", laptop)
tuneup_scratch.toggle()                 -- closing: parks later ...
tuneup_scratch.toggle()                 -- ... but it is open again before that
fake.run_timers()
check(not notes.workspace.special, "reopened in time: nothing put away")

-- stop(): no handler puts anything away any more.
tuneup_scratch.stop()
tuneup_scratch.toggle()
fake.run_timers()
tuneup_scratch.toggle()
fake.run_timers()
fake.fire("monitor.focused", laptop)
fake.run_timers()
check(not notes.workspace.special, "after stop() nothing is put away")
print("ok")
'''


@pytest.mark.skipif(LUA is None, reason="no Lua interpreter")
def test_the_scratch_row_is_not_put_away_by_mistake(tmp_path):
    module = tmp_path / "module.lua"
    module.write_text(scratch.module_lua({"enabled": False}))
    script = tmp_path / "check.lua"
    script.write_text(LUA_TEST)
    for name in ("fake_hl.lua",):
        shutil.copy(HERE / "lua" / name, tmp_path / name)
    done = subprocess.run([LUA, str(script), str(module)], capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout.strip() == "ok", done.stderr


def test_switching_the_scratch_desktops_off_stops_the_lua_before_it_unparks(world):
    model = world
    calls = []
    model.on_eval = calls.append
    model.clients = [{"address": "0xa", "class": "notes", "workspace": {"id": -101, "name": scratch.PARKED + "202"}}]
    assert scratch.unpark_all() == ["notes"]
    assert "tuneup_scratch.stop()" in calls[0]
