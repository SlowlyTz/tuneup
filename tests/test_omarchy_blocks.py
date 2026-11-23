"""Omarchy's workspaces per monitor: every screen owns a block of ten ids and
Omarchy renumbers what lies outside it, on every reload and monitor change.
Tuneup's desktops take their ids from those blocks, so nothing of theirs is
renumbered and the windows stay where the bar and the keys find them."""
import os

import pytest

from hypr_screens import config, desktops, engine, hypr
from hyprland_model import HyprlandModel, hp_output, laptop_output

HP_ID = "HP Inc.|HP 32f|3CM1230QVW"
HP = 11      # the HP's block is 1 (the laptop has 0): its desktop 1 is workspace 11


@pytest.fixture()
def model(monkeypatch):
    model = HyprlandModel(laptop_output())
    monkeypatch.setattr(hypr, "hyprctl", model)
    model.with_omarchy(os.environ["OMARCHY_PATH"], os.environ["XDG_STATE_HOME"])
    config.update(lambda cfg: cfg.update(default_fixed="external", fixed_desktops=5, unplug_windows="spread"))
    engine.sync("added")
    return model


def run(model, kind):
    """A sync, and one more for the reload it caused (as the watcher sees it)."""
    model.events.clear()
    engine.sync(kind)
    if any(event.startswith("configreloaded") for event in model.events):
        model.events.clear()
        engine.sync("reload")


def window(model, address, workspace, monitor="DP-3"):
    model.clients.append({"address": address, "workspace": {"id": workspace, "name": str(workspace)},
                          "mapped": True, "at": [0, 0], "size": [100, 100], "monitor": 1})
    model.workspaces.setdefault(workspace, monitor)


def on(model, address):
    return next((c["workspace"]["id"] for c in model.clients if c["address"] == address), None)


def docked(model, **settings):
    if settings:
        config.update(lambda cfg: cfg.update(settings))
    model.plug(hp_output("DP-3"))
    run(model, "added")
    model.omarchy.renumbered.clear()


def test_the_fixed_screens_desktops_lie_in_its_block(model):
    docked(model)
    assert model.visible() == {"eDP-1": 1, "DP-3": HP}
    assert desktops.status(config.load())["fixed_workspaces"] == list(range(HP, HP + 5))


def test_a_reload_leaves_the_fixed_screens_windows_where_they_are(model):
    docked(model)
    window(model, "0xa", HP)
    desktops.switch(config.load(), "switch", 3, fixed=True)
    window(model, "0xc", HP + 2)
    for _ in range(3):
        model.reload()
        run(model, "reload")
    assert model.omarchy.renumbered == []
    assert (on(model, "0xa"), on(model, "0xc")) == (HP, HP + 2)
    assert model.visible()["DP-3"] == HP + 2
    desktops.switch(config.load(), "switch", 1, fixed=True)
    assert model.visible()["DP-3"] == HP


def test_desktops_1_to_10_stay_on_the_laptops_block(model):
    docked(model)
    model.focus_monitor(model.monitor("eDP-1"))
    desktops.switch(config.load(), "switch", 4)
    assert model.visible() == {"eDP-1": 4, "DP-3": HP}


def test_with_the_laptop_fixed_the_desktops_go_to_the_external_block(model):
    window(model, "0x1", 1, "eDP-1")
    docked(model, default_fixed="panel")
    # what the laptop showed stays on it, as its own desktop; desktops 1-10 are the HP's 11-20
    assert model.visible()["eDP-1"] == 1 and on(model, "0x1") == 1
    assert model.workspaces.get(1) == "eDP-1"
    model.focus_monitor(model.monitor("DP-3"))
    desktops.switch(config.load(), "switch", 2)
    window(model, "0x2", HP + 1)
    model.reload()
    run(model, "reload")
    assert model.omarchy.renumbered == []
    assert model.visible()["DP-3"] == HP + 1 and on(model, "0x2") == HP + 1


def test_a_swap_trades_the_blocks(model):
    docked(model)
    window(model, "0xf", HP)            # the HP's own desktop
    window(model, "0xd", 2, "eDP-1")    # desktop 2
    desktops.swap(config.load(), "panel")
    assert model.workspaces[on(model, "0xf")] == "eDP-1" and on(model, "0xf") == 1   # fixed now: the laptop's block
    assert model.workspaces[on(model, "0xd")] == "DP-3" and on(model, "0xd") == HP + 1
    model.reload()
    run(model, "reload")
    assert model.omarchy.renumbered == []


def test_unplugging_spreads_and_brings_back_as_before(model):
    docked(model)
    window(model, "0x1", HP)
    window(model, "0x3", HP + 2)
    window(model, "0x6", 6, "eDP-1")       # the laptop's own
    window(model, "0x5", 5, "eDP-1")
    model.unplug("DP-3")                   # Omarchy merges them into the laptop's block at once
    run(model, "removed")
    assert (on(model, "0x1"), on(model, "0x3"), on(model, "0x6")) == (6, 8, 6)
    model.clients.append({"address": "0x9", "workspace": {"id": 6, "name": "6"}, "mapped": True,
                          "at": [0, 0], "size": [1, 1], "monitor": 0})   # opened on desktop 6 meanwhile
    docked(model)
    assert (on(model, "0x1"), on(model, "0x3")) == (HP, HP + 2)
    assert (on(model, "0x6"), on(model, "0x9")) == (6, 6)   # the laptop's own stay


def test_unplugging_folds_onto_the_laptops_desktop(model):
    docked(model, unplug_windows="fold")
    window(model, "0x1", HP + 1)
    model.focus_monitor(model.monitor("eDP-1"))
    desktops.switch(config.load(), "switch", 3)
    model.unplug("DP-3")
    run(model, "removed")
    assert on(model, "0x1") == 3 and model.visible()["eDP-1"] == 3


def test_unplugging_with_the_laptop_fixed_gives_the_desktops_their_numbers_back(model):
    docked(model, default_fixed="panel")
    window(model, "0x2", HP + 1)    # desktop 2 on the HP
    window(model, "0x4", HP + 3)    # desktop 4
    window(model, "0xf", 1, "eDP-1")  # the laptop's own desktop
    model.unplug("DP-3")
    run(model, "removed")
    assert (on(model, "0x2"), on(model, "0x4")) == (2, 4)
    assert on(model, "0xf") == 1    # folded onto desktop 1, as before


def test_the_first_start_after_the_update_moves_the_old_ids(monkeypatch):
    """Tuneup's old ids (99 and up) and Omarchy's first reload, which renumbers
    them into the HP's block before Tuneup looks."""
    model = HyprlandModel(laptop_output(), hp_output("DP-3"))
    monkeypatch.setattr(hypr, "hyprctl", model)
    config.update(lambda cfg: cfg.update(default_fixed="external", fixed_desktops=5))
    engine.sync("added")
    desktops.layout_file().unlink()                 # as written by a Tuneup before this one
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    window(model, "0xa", 99)
    model.workspaces[101] = "DP-3"
    window(model, "0xc", 101)
    model.with_omarchy(os.environ["OMARCHY_PATH"], os.environ["XDG_STATE_HOME"])
    model.events.clear()
    model.reload()                                  # Omarchy renumbers 99 and 101 right away
    desktops.renumbered([event.encode() for event in model.events])
    run(model, "reload")
    assert (on(model, "0xa"), on(model, "0xc")) == (HP, HP + 2)
    assert model.visible()["DP-3"] == HP


def test_an_open_scratch_desktop_gets_its_id_back(model):
    docked(model)
    model.workspaces[201] = "DP-3"
    window(model, "0x5", 201)
    desktops.renumbered([b"changeworkspaceid>>201,12"])
    model.change_id(201, 12)
    model.events.clear()
    desktops.renumbered([b"changeworkspaceid>>201,12"])
    assert on(model, "0x5") == 201


def test_without_omarchys_blocks_the_ids_stay_tuneups(monkeypatch):
    model = HyprlandModel(laptop_output(), hp_output("DP-3"))
    monkeypatch.setattr(hypr, "hyprctl", model)
    config.update(lambda cfg: cfg.update(default_fixed="external"))
    engine.sync("added")
    assert model.visible()["DP-3"] == desktops.FIXED_WS
    assert desktops.load_layout()["omarchy"] is False
