import sys
from pathlib import Path

# tests/i18n_keys.py is a helper, imported by name.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def private_runtime_dir(tmp_path, monkeypatch):
    """Locks and runtime files (config.lock, applied.json) never land in the real
    runtime dir, settings and data never in the real home (a test may still
    point these somewhere else)."""
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for name, folder in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"),
                         ("XDG_STATE_HOME", ".local/state")):
        monkeypatch.setenv(name, str(tmp_path / "home" / folder))


@pytest.fixture(autouse=True)
def tuneup_command(monkeypatch):
    """The generated Lua runs `tuneup`, whatever this machine has on $PATH."""
    from hypr_screens import brand

    monkeypatch.setattr(brand, "command", lambda: brand.COMMAND)
