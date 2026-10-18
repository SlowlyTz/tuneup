"""Enforcement: what the watcher had to put back, and switching it on or off."""
from hypr_screens import config, enforce
from hypr_screens.api.core import endpoint, need


@endpoint
def enforcement() -> dict:
    """{enabled, running (the watcher is alive), fixes (newest first), backedOff}."""
    return enforce.view(config.read())


@endpoint
def set_enforcement(enabled: bool) -> dict:
    need(isinstance(enabled, bool), "bad_value", "enabled must be true or false")
    return enforce.view(config.update(lambda cfg: cfg.__setitem__("enforce", enabled)))
