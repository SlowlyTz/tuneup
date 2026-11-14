"""Fixes from the audit: aborts, rejected hyprctl replies, undo, peeks, escaping."""
import fcntl
import json
import subprocess
from unittest.mock import Mock

import pytest

import minimizer
from hypr_screens.gui import placement


@pytest.fixture(autouse=True)
def quiet(monkeypatch, tmp_path):
    monkeypatch.setattr(minimizer, "_LUA_DISPATCH", False)
    monkeypatch.setattr(minimizer.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(minimizer, "STATE_FILE", tmp_path / "hm" / "state.json")


def window(address, workspace=1, minimized=False, **extra):
    where = {"id": -98, "name": "special:minimized"} if minimized else {"id": workspace, "name": str(workspace)}
    return {"address": address, "workspace": where, "floating": False, **extra}


def stacks():
    return minimizer.load_state()


def test_lua_text_cannot_leave_the_string():
    assert minimizer.lua_text("a'b\\c\nd\re\x00") == "a\\'b\\\\c\\nd\\re\\x00"
    assert minimizer.lua_text("0xabc") == "0xabc"


def test_lua_commands_escape_the_address(monkeypatch):
    monkeypatch.setattr(minimizer, "_LUA_DISPATCH", True)
    sent = []
    monkeypatch.setattr(minimizer, "run_hyprctl", lambda *args: sent.append(args))
    minimizer.move_window("0x1'); os.exit() --", "2")
    assert "address:0x1\\'); os.exit() --" in sent[0][1]


def test_run_hyprctl_times_out_as_runtime_error(monkeypatch):
    def hang(*args, **kwargs):
        assert kwargs["timeout"] == minimizer.HYPRCTL_SECONDS
        raise subprocess.TimeoutExpired("hyprctl", 5)

    monkeypatch.setattr(minimizer.subprocess, "run", hang)
    with pytest.raises(RuntimeError):
        minimizer.run_hyprctl("-j", "clients")


@pytest.mark.parametrize("reply", ["error: no such window", "Invalid dispatcher", "Lua error: boom"])
def test_rejected_dispatch_is_an_error(monkeypatch, reply):
    monkeypatch.setattr(minimizer.subprocess, "run", lambda *a, **k: Mock(stdout=reply))
    with pytest.raises(RuntimeError):
        minimizer.run_hyprctl("dispatch", "x")
    with pytest.raises(RuntimeError):
        minimizer.run_hyprctl("eval", "x")
    assert minimizer.run_hyprctl("-j", "clients").stdout == reply  # queries are not judged


def test_ok_and_empty_replies_pass(monkeypatch):
    for reply in ("ok", "", "ok\n"):
        monkeypatch.setattr(minimizer.subprocess, "run", lambda *a, reply=reply, **k: Mock(stdout=reply))
        minimizer.run_hyprctl("dispatch", "x")


def test_lua_probe_follows_the_reply(monkeypatch):
    monkeypatch.setattr(minimizer, "_LUA_DISPATCH", None)
    monkeypatch.setattr(minimizer.subprocess, "run", lambda *a, **k: Mock(stdout="Invalid dispatcher"))
    assert minimizer._lua_dispatch_supported() is False
    monkeypatch.setattr(minimizer, "_LUA_DISPATCH", None)
    monkeypatch.setattr(minimizer.subprocess, "run", lambda *a, **k: Mock(stdout="ok"))
    assert minimizer._lua_dispatch_supported() is True


def test_state_lock_gives_up(monkeypatch):
    monkeypatch.setattr(minimizer, "LOCK_WAIT_SECONDS", 0)
    minimizer.STATE_FILE.parent.mkdir(parents=True)
    with open(minimizer.STATE_FILE.with_name("state.json.lock"), "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError):
            with minimizer.state_lock():
                pass


def stash_others_setup(monkeypatch, clients):
    monkeypatch.setattr(minimizer, "end_peek", lambda: None)
    monkeypatch.setattr(minimizer, "get_active_window", lambda: ("0xa", "1"))
    monkeypatch.setattr(minimizer, "get_clients", lambda: clients)
    monkeypatch.setattr(minimizer, "focus_window", lambda address: None)


def test_stash_others_saves_each_window_before_hiding_it(monkeypatch):
    clients = [window("0xa"), window("0xb"), window("0xc")]
    stash_others_setup(monkeypatch, clients)
    seen = []

    def hide(address, client=None):
        seen.append((address, list(stacks().get("1", []))))
        if address == "0xc":
            raise RuntimeError("hyprctl did not answer")

    monkeypatch.setattr(minimizer, "hide_window", hide)
    with pytest.raises(RuntimeError):
        minimizer.stash_others()
    assert seen == [("0xb", ["0xb"]), ("0xc", ["0xb", "0xc"])]
    assert stacks() == {"1": ["0xb", "0xc"]}


def test_stash_others_leaves_pinned_and_unmapped_alone(monkeypatch):
    clients = [window("0xa"), window("0xb", pinned=True), window("0xc", mapped=False), window("0xd", mapped=True)]
    stash_others_setup(monkeypatch, clients)
    hidden = []
    monkeypatch.setattr(minimizer, "hide_window", lambda address, client=None: hidden.append(address))
    minimizer.stash_others()
    assert hidden == ["0xd"]


def test_stash_in_the_minimized_workspace_makes_no_stack(monkeypatch):
    monkeypatch.setattr(minimizer, "end_peek", lambda: None)
    monkeypatch.setattr(minimizer, "get_active_window", lambda: ("0xa", "special:minimized"))
    monkeypatch.setattr(minimizer, "hide_window", lambda *a: pytest.fail("hid a hidden window"))
    minimizer.stash()
    minimizer.minimize_from("0xa", "special:minimized")
    assert stacks() == {}


def test_pop_adopts_orphans(monkeypatch):
    clients = {"0xo": window("0xo", minimized=True)}
    monkeypatch.setattr(minimizer, "end_peek", lambda: None)
    monkeypatch.setattr(minimizer, "get_active_workspace_id", lambda: "1")
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: clients)
    shown = []
    monkeypatch.setattr(minimizer, "show_window", lambda address, ws, **k: shown.append((address, ws)))
    monkeypatch.setattr(minimizer, "focus_window", lambda address: None)
    minimizer.pop()
    assert shown == [("0xo", "1")]
    assert stacks() == {}


def test_pop_all_adopts_orphans(monkeypatch):
    clients = {"0xo": window("0xo", minimized=True), "0xp": window("0xp", minimized=True)}
    monkeypatch.setattr(minimizer, "end_peek", lambda: None)
    monkeypatch.setattr(minimizer, "get_active_workspace_id", lambda: "1")
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: clients)
    shown = []
    monkeypatch.setattr(minimizer, "show_window", lambda address, ws, **k: shown.append(address))
    minimizer.pop_all()
    assert sorted(shown) == ["0xo", "0xp"]


def test_undo_hides_only_windows_still_here(monkeypatch):
    minimizer.save_storage({"stacks": {}, "peek": None, "history": [
        {"workspace_id": "1", "stacks": {"1": ["0xhere", "0xaway", "0xgone", "0xalready"]}}]})
    clients = {
        "0xhere": window("0xhere", 1),
        "0xaway": window("0xaway", 2),
        "0xalready": window("0xalready", minimized=True),
    }
    monkeypatch.setattr(minimizer, "end_peek", lambda: None)
    monkeypatch.setattr(minimizer, "get_active_workspace_id", lambda: "1")
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: clients)
    hidden = []
    monkeypatch.setattr(minimizer, "hide_window", lambda address, client=None: hidden.append(address))
    minimizer.undo()
    assert hidden == ["0xhere"]
    assert stacks() == {"1": ["0xhere"]}


def test_end_peek_keeps_a_window_moved_by_hand(monkeypatch):
    minimizer.save_storage({"stacks": {}, "history": [], "peek": {
        "address": "0xp", "origin": "1", "workspace": "2", "index": 0, "floating": True,
        "geometry": [1, 2, 3, 4]}})
    moved = window("0xp", 5, floating=True, tags=[])
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: {"0xp": moved})
    monkeypatch.setattr(minimizer, "place_window", lambda *a: pytest.fail("reset the geometry"))
    monkeypatch.setattr(minimizer, "move_window", lambda *a, **k: pytest.fail("moved it"))
    assert minimizer.end_peek() is None
    assert stacks() == {}
    assert minimizer.load_storage()["peek"] is None


def test_end_peek_still_restores_a_minimized_peek(monkeypatch):
    minimizer.save_storage({"stacks": {}, "history": [], "peek": {
        "address": "0xp", "origin": "1", "workspace": "2", "index": 0, "floating": True,
        "geometry": [1, 2, 3, 4]}})
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: {"0xp": window("0xp", 2, floating=True)})
    placed = []
    monkeypatch.setattr(minimizer, "place_window", lambda address, geometry: placed.append(geometry))
    monkeypatch.setattr(minimizer, "move_window", lambda *a, **k: None)
    assert minimizer.end_peek() == "0xp"
    assert placed == [[1, 2, 3, 4]]
    assert stacks() == {"1": ["0xp"]}


def full(address, fullscreen, **extra):
    return {**window(address, **extra), "at": [0, 0], "size": [100, 100], "fullscreen": fullscreen}


def test_a_fullscreen_window_lies_on_top():
    clients = [full("0xa", 1), {**window("0xb", floating=True), "at": [0, 0], "size": [10, 10], "fullscreen": 0}]
    assert minimizer.lies_on_top("0xa", clients) is True


def test_a_window_under_a_fullscreen_one_does_not():
    clients = [{**window("0xa"), "at": [0, 0], "size": [10, 10], "fullscreen": 0}, full("0xb", 2)]
    assert minimizer.lies_on_top("0xa", clients) is False


def test_named_workspace_is_selected_by_name():
    assert minimizer.workspace_key({"id": -1337, "name": "web"}) == "name:web"
    assert minimizer.workspace_key({"id": 3, "name": "3"}) == "3"
    assert minimizer.workspace_key({"id": -98, "name": "special:minimized"}) == "special:minimized"
    assert minimizer.workspace_label("name:web") == "web"


def test_the_docks_negative_id_becomes_the_name(monkeypatch):
    reply = Mock(stdout=json.dumps([{"id": -1337, "name": "web"}, {"id": 2, "name": "2"}]))
    monkeypatch.setattr(minimizer, "run_hyprctl", lambda *args: reply)
    assert minimizer.workspace_arg("-1337") == "name:web"
    assert minimizer.workspace_arg("2") == "2"
    assert minimizer.workspace_arg("-5") == "-5"


def test_fetch_of_a_hidden_window_without_stack_undoes_its_tags(monkeypatch):
    clients = {"0xh": {**window("0xh", minimized=True), "tags": ["tuneup-tiled"]}}
    monkeypatch.setattr(minimizer, "clients_by_address", lambda: clients)
    monkeypatch.setattr(minimizer, "restore_address", lambda *a, **k: False)
    monkeypatch.setattr(minimizer, "focus_window", lambda address: None)
    monkeypatch.setattr(minimizer, "move_window", lambda *a, **k: pytest.fail("plain move"))
    shown = []
    monkeypatch.setattr(minimizer, "show_window", lambda address, ws, **k: shown.append((address, ws)))
    assert minimizer.fetch_address("0xh", "2") is True
    assert shown == [("0xh", "2")]


def test_a_restored_window_is_clamped_onto_its_screen(monkeypatch):
    monkeypatch.setattr(minimizer, "get_monitors", lambda: [{"name": "A", "x": 0, "y": 0, "width": 1920, "height": 1080}])
    assert minimizer.clamp_to_monitor(2500, 900, 800, 600, "A") == (1120, 480)
    assert minimizer.clamp_to_monitor(100, 100, 800, 600, "A") == (100, 100)
    assert minimizer.clamp_to_monitor(-50, 5, 800, 600, "A") == (0, 5)
    assert minimizer.clamp_to_monitor(2500, 900, 800, 600, "unknown") == (2500, 900)


def test_main_reports_a_broken_reply_instead_of_a_traceback(monkeypatch, capsys):
    monkeypatch.setattr(minimizer.sys, "argv", ["hypr-minimizer", "pop"])

    def boom(args):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(minimizer, "run_command", boom)
    with pytest.raises(SystemExit) as stopped:
        minimizer.main()
    assert stopped.value.code == 1
    assert "hypr-minimizer:" in capsys.readouterr().err


def test_bring_here_survives_a_stuck_minimizer(monkeypatch):
    monkeypatch.setattr(placement, "own_client", lambda: {
        "address": "0xs", "workspace": {"id": -98, "name": "special:minimized"}})
    monkeypatch.setattr(placement.shutil, "which", lambda name: "/bin/hypr-minimizer")

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("hypr-minimizer", 10)

    monkeypatch.setattr(placement.subprocess, "run", hang)
    assert placement.bring_here(1) is False
