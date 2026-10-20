"""Plugging screens in and out without a restart, against a Hyprland model that
places, reloads and moves workspaces like the real one."""
import pytest

from hypr_screens import apply, config, desktops, engine, hypr
from hyprland_model import HyprlandModel, Output, fujitsu_output, hp_output, laptop_output, tv_output

LAPTOP_ID = "Samsung Display Corp.|0x4159|"
HP_ID = "HP Inc.|HP 32f|3CM1230QVW"
TV_ID = "LG Electronics|LG TV SSCR2|0x01010101"
FUJITSU_ID = "Fujitsu Siemens Computers GmbH|B27-9 TS QHD|YVEB021757"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(apply.time, "sleep", lambda seconds: None)


@pytest.fixture()
def world(monkeypatch):
    """The laptop alone, and the user's settings: the HP above with one desktop,
    the TV at 200 %."""
    model = HyprlandModel(laptop_output())
    monkeypatch.setattr(hypr, "hyprctl", model)

    def settings(cfg):
        for sid in (HP_ID, TV_ID, FUJITSU_ID):
            cfg["screens"].setdefault(sid, {"favorite": False, "settings": {}})
        config.set_setting(cfg, HP_ID, "position", "above")
        config.set_setting(cfg, HP_ID, "one_desktop", True)
        config.set_setting(cfg, TV_ID, "scale", 2)
    config.update(settings)
    run(model, "added")
    return model


def run(model: HyprlandModel, kind: str) -> list[str]:
    """What the watcher does with one burst: a sync, then one more for the
    reload event our own reload caused (as the socket would deliver it)."""
    model.events.clear()
    done = engine.sync(kind)
    if any(event.startswith("configreloaded") for event in model.events):
        model.events.clear()
        done += engine.sync("reload")
    return done


def plug(model, output, kind="added"):
    model.plug(output)
    return run(model, kind)


def unplug(model, name):
    model.unplug(name)
    return run(model, "removed")


def assert_settled(model):
    """Nothing left to do: a further sync changes nothing and reloads nothing."""
    reloads, calls = model.reloads, len(model.calls)
    assert engine.sync("") == []
    assert model.reloads == reloads
    assert not [c for c in model.calls[calls:] if c[0] == "eval" and "hl.monitor" in c[1]]
    assert not model.overlapping()


def test_desk_meeting_and_back(world):
    model = world
    plug(model, hp_output("DP-3"))
    assert model.touching("eDP-1", "DP-3")
    assert model.box("DP-3")[3] == model.box("eDP-1")[1]          # the HP above
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    assert_settled(model)

    unplug(model, "DP-3")
    assert desktops.FIXED_WS not in model.visible().values()
    assert_settled(model)

    plug(model, tv_output("HDMI-A-1"))
    tv = model.monitor("HDMI-A-1")
    assert tv["scale"] == 2.0 and model.touching("eDP-1", "HDMI-A-1")
    assert_settled(model)

    unplug(model, "HDMI-A-1")
    assert_settled(model)

    plug(model, hp_output("DP-5"))        # the dock enumerated the HP under another name
    assert model.touching("eDP-1", "DP-5") and model.box("DP-5")[3] == model.box("eDP-1")[1]
    assert model.visible()["DP-5"] == desktops.FIXED_WS
    assert_settled(model)


def test_unplugging_does_not_reload(world):
    model = world
    plug(model, hp_output())
    before = model.reloads
    unplug(model, "DP-3")
    assert model.reloads == before


def test_quick_replug_comes_back_in_place(world):
    model = world
    plug(model, hp_output())
    before = (model.box("DP-3"), model.box("eDP-1"), model.reloads)
    model.unplug("DP-3")
    model.plug(hp_output())
    run(model, "added")                    # one burst: removed + added
    assert (model.box("DP-3"), model.box("eDP-1"), model.reloads) == before
    assert_settled(model)


def test_a_screen_without_a_place_after_one_with(world):
    """The laptop keeps the spot it had under the HP; a TV without a side
    must not end up touching it at a corner only."""
    model = world
    plug(model, hp_output())
    unplug(model, "DP-3")
    plug(model, tv_output())
    assert model.touching("eDP-1", "HDMI-A-1")
    assert_settled(model)


def test_two_external_screens(world):
    model = world
    plug(model, hp_output("DP-3"))
    plug(model, fujitsu_output("DP-5"))
    assert not model.overlapping()
    for ws, name in model.workspaces.items():
        if ws in desktops.DESKTOPS:
            assert name == "eDP-1"
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    assert model.visible()["DP-5"] not in desktops.DESKTOPS
    assert_settled(model)
    unplug(model, "DP-5")
    unplug(model, "DP-3")
    assert_settled(model)


def test_unplug_during_a_sync(world, monkeypatch):
    model = world
    model.plug(hp_output())

    def pull_the_cable(code):
        if "DP-3" in code and model.monitor("DP-3"):
            model.unplug("DP-3")
    model.on_eval = pull_the_cable
    run(model, "added")
    model.on_eval = None
    run(model, "removed")
    assert [m["name"] for m in model.monitors] == ["eDP-1"]
    assert_settled(model)


def test_a_different_screen_on_the_same_connector_gets_its_own_settings(world):
    model = world
    plug(model, tv_output("HDMI-A-1"))
    assert model.monitor("HDMI-A-1")["scale"] == 2.0
    unplug(model, "HDMI-A-1")
    projector = Output("HDMI-A-1", "Epson", "EB-X41", "", [(1920, 1080, 60.0)])
    plug(model, projector)
    assert model.monitor("HDMI-A-1")["scale"] == 1.0   # not the TV's 200 %
    assert model.touching("eDP-1", "HDMI-A-1")
    assert_settled(model)


def test_windows_on_the_fixed_desktop_come_back_on_unplug(world):
    model = world
    plug(model, hp_output())
    model.clients.append({"address": "0xa", "workspace": {"id": desktops.FIXED_WS, "name": "99"},
                          "mapped": True, "at": [0, 0], "size": [10, 10]})
    unplug(model, "DP-3")
    assert model.clients[0]["workspace"]["id"] in desktops.DESKTOPS


# --- through the watcher: the model's events, the watcher's timing --------------------------


class Clock:
    def __init__(self):
        self.now = 0.0


def through_watcher(model, watcher, clock, seconds=1.5):
    """Hand the model's events to the watcher as the socket would, then let time pass."""
    from hypr_screens import watch

    said = []
    for _ in range(4):  # our own work causes events too; they must die down
        lines = [line.encode() for line in model.events]
        model.events.clear()
        watcher.feed(lines, clock.now)
        clock.now += seconds
        said += watcher.tick(clock.now)
        if not model.events:
            break
    assert not model.events, f"events keep coming: {model.events}"
    assert not [line for line in said if "failed" in line], said
    return said


@pytest.fixture()
def watched(world, monkeypatch):
    from hypr_screens import watch, widgets

    monkeypatch.setattr(widgets, "auto_layout", lambda: "")
    clock = Clock()
    return world, watch.Watcher(clock.now), clock


def test_a_dock_unplugging_in_waves_settles_with_one_sync(watched, monkeypatch):
    model, watcher, clock = watched
    model.plug(hp_output("DP-3"))
    through_watcher(model, watcher, clock)
    syncs = []
    real = engine.sync
    monkeypatch.setattr(engine, "sync", lambda kind="": syncs.append(kind) or real(kind))
    model.unplug("DP-3")
    watcher.feed([line.encode() for line in model.events], clock.now)
    model.events.clear()
    model.plug(hp_output("DP-3"))                # the dock wakes up once more ...
    watcher.feed([line.encode() for line in model.events], clock.now + 0.4)
    model.events.clear()
    model.unplug("DP-3")                         # ... and is gone for good
    watcher.feed([line.encode() for line in model.events], clock.now + 0.8)
    model.events.clear()
    clock.now += 0.9
    assert watcher.tick(clock.now) == []         # not quiet yet
    clock.now += 1.0
    watcher.tick(clock.now)
    assert syncs == ["added"]
    assert [m["name"] for m in model.monitors] == ["eDP-1"]
    assert_settled(model)


def test_desk_meeting_desk_through_the_watcher(watched):
    """Unplugging never reloads. Plugging in the TV reloads once: the desk's
    rules pinning desktops to the laptop must go, the TV has no fixed desktop."""
    model, watcher, clock = watched
    reloads = []
    for _ in range(3):
        before = model.reloads
        model.plug(hp_output("DP-3"))
        through_watcher(model, watcher, clock)
        assert model.touching("eDP-1", "DP-3")
        model.unplug("DP-3")
        through_watcher(model, watcher, clock)
        model.plug(tv_output("HDMI-A-1"))
        through_watcher(model, watcher, clock)
        assert model.monitor("HDMI-A-1")["scale"] == 2.0 and model.touching("eDP-1", "HDMI-A-1")
        assert model.workspace_rules == {}
        model.unplug("HDMI-A-1")
        through_watcher(model, watcher, clock)
        reloads.append(model.reloads - before)
    assert reloads == [1, 1, 1]
    assert_settled(model)


def test_with_a_fixed_desktop_on_every_external_screen_nothing_reloads(watched):
    model, watcher, clock = watched
    config.update(lambda cfg: cfg.__setitem__("default_fixed", "external"))
    for _ in range(2):
        for output in (hp_output("DP-3"), tv_output("HDMI-A-1")):
            model.plug(output)
            through_watcher(model, watcher, clock)
            assert model.visible()[output.name] == desktops.FIXED_WS
            model.unplug(output.name)
            through_watcher(model, watcher, clock)
    assert model.reloads == 0
    assert_settled(model)


def test_booting_docked_with_two_screens(monkeypatch):
    model = HyprlandModel(laptop_output(), hp_output("DP-3"), fujitsu_output("DP-5"))
    monkeypatch.setattr(hypr, "hyprctl", model)

    def settings(cfg):
        cfg["screens"].setdefault(HP_ID, {"favorite": False, "settings": {}})
        config.set_setting(cfg, HP_ID, "position", "above")
        config.set_setting(cfg, HP_ID, "one_desktop", True)
    config.update(settings)
    run(model, "added")                           # the watcher's first sync
    assert model.touching("eDP-1", "DP-3") and not model.overlapping()
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    assert all(name == "eDP-1" for ws, name in model.workspaces.items() if ws in desktops.DESKTOPS)
    assert_settled(model)


def test_the_laptop_as_fixed_screen_gives_its_windows_back_on_unplug(world):
    model = world
    config.update(lambda cfg: (config.set_setting(cfg, HP_ID, "one_desktop", None),
                               config.set_setting(cfg, LAPTOP_ID, "one_desktop", True)))
    model.clients.append({"address": "0xa", "workspace": {"id": 1, "name": "1"}, "mapped": True,
                          "at": [0, 0], "size": [10, 10]})
    plug(model, hp_output())
    assert model.visible()["eDP-1"] == desktops.FIXED_WS
    assert model.clients[0]["workspace"]["id"] == desktops.FIXED_WS   # stayed on the laptop
    unplug(model, "DP-3")
    assert model.clients[0]["workspace"]["id"] in desktops.DESKTOPS
    assert model.visible()["eDP-1"] in desktops.DESKTOPS


def test_a_swap_ends_with_the_unplug(world):
    model = world
    plug(model, hp_output())
    desktops.swap(config.load())
    assert desktops.load_override()["role"] == "panel"
    unplug(model, "DP-3")
    assert desktops.load_override() == {}
    plug(model, hp_output())
    assert model.visible()["DP-3"] == desktops.FIXED_WS     # the settings decide again


def test_a_reload_by_someone_else_puts_the_screens_back(watched):
    model, watcher, clock = watched
    model.plug(hp_output())
    through_watcher(model, watcher, clock)
    spot = (model.box("DP-3"), model.box("eDP-1"))
    model.reload()                                 # e.g. Omarchy switching the theme
    assert (model.box("DP-3"), model.box("eDP-1")) != spot
    through_watcher(model, watcher, clock)
    assert (model.box("DP-3"), model.box("eDP-1")) == spot
    assert model.visible()["DP-3"] == desktops.FIXED_WS and model.workspace_rules


def test_closing_the_lid_while_docked_does_not_reload(world):
    model = world
    plug(model, hp_output())
    before = model.reloads
    model.close_lid()
    run(model, "removed")
    assert model.reloads == before
    assert [m["name"] for m in model.monitors if not m["disabled"]] == ["DP-3"]
    model.close_lid(closed=False)
    run(model, "added")
    assert model.visible()["DP-3"] == desktops.FIXED_WS and model.touching("eDP-1", "DP-3")
    assert model.reloads == before
    assert_settled(model)


def test_hyprland_not_answering_is_not_everything_unplugged(world, monkeypatch):
    model = world
    plug(model, hp_output())
    desktops.swap(config.load())
    model.clients.append({"address": "0xa", "workspace": {"id": desktops.FIXED_WS, "name": "99"},
                          "mapped": True, "at": [0, 0], "size": [10, 10]})
    monkeypatch.setattr(hypr, "hyprctl", lambda *args: "error: hyprctl timed out")
    engine.sync("removed")
    monkeypatch.setattr(hypr, "hyprctl", model)
    assert desktops.load_override()["role"] == "panel"            # the swap is kept
    assert model.clients[0]["workspace"]["id"] == desktops.FIXED_WS


# --- several desktops on the fixed screen ------------------------------------------


@pytest.fixture()
def five(world):
    """The HP plugged in as the fixed screen, with five desktops of its own."""
    config.update(lambda cfg: cfg.__setitem__("fixed_desktops", 5))
    plug(world, hp_output("DP-3"))
    return world


def test_desktop_keys_follow_the_focused_screen(five):
    model = five
    laptop_shows = model.visible()["eDP-1"]
    model.focus_monitor(model.monitor("DP-3"))
    desktops.switch(config.load(), "switch", 3)
    assert model.visible()["DP-3"] == desktops.FIXED_WS + 2          # its desktop 3
    assert model.visible()["eDP-1"] == laptop_shows                  # the laptop stays
    desktops.switch(config.load(), "switch", 7)                      # it has only five
    assert model.visible()["DP-3"] == desktops.FIXED_WS + 2
    model.focus_monitor(model.monitor("eDP-1"))
    desktops.switch(config.load(), "switch", 3)
    assert model.visible()["eDP-1"] == 3 and model.visible()["DP-3"] == desktops.FIXED_WS + 2
    assert_settled(model)


def test_the_bar_switches_either_screen_whatever_has_the_focus(five):
    model = five
    model.focus_monitor(model.monitor("DP-3"))
    desktops.switch(config.load(), "switch", 4, fixed=False)         # a laptop tile clicked
    assert model.visible()["eDP-1"] == 4 and model.visible()["DP-3"] == desktops.FIXED_WS
    desktops.switch(config.load(), "switch", 2, fixed=True)          # a tile of the fixed screen
    assert model.visible()["DP-3"] == desktops.FIXED_WS + 1


def test_one_fixed_desktop_keeps_the_keys_on_the_laptop(world):
    model = world
    plug(model, hp_output("DP-3"))
    model.focus_monitor(model.monitor("DP-3"))
    desktops.switch(config.load(), "switch", 3)
    assert model.visible()["eDP-1"] == 3 and model.visible()["DP-3"] == desktops.FIXED_WS


def test_windows_on_the_fixed_desktops_come_back_when_unplugged(five):
    model = five
    model.focus_monitor(model.monitor("DP-3"))
    desktops.switch(config.load(), "switch", 2)
    model.clients.append({"address": "0xb", "workspace": {"id": desktops.FIXED_WS + 1, "name": "100"},
                          "mapped": True, "at": [0, 0], "size": [100, 100], "monitor": 1})
    unplug(model, "DP-3")
    assert model.clients[-1]["workspace"]["id"] in desktops.DESKTOPS
