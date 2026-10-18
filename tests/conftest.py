import sys
from pathlib import Path

# tests/i18n_keys.py is a helper, imported by name.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def private_runtime_dir(tmp_path, monkeypatch):
    """Locks and runtime files (config.lock, applied.json) never land in the real runtime dir."""
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
