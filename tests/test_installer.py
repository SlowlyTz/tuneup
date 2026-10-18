"""install.sh, `tuneup setup`, the migration and `tuneup uninstall`, run for real
in a sandbox: a temporary HOME and XDG folders, and stubs on $PATH for sudo,
pkexec, pacman, hyprctl, omarchy and the rest that only write down how they
were called. Nothing runs as root, nothing reaches Hyprland, no process of
this machine's session is stopped (those have another HOME)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hypr_screens import camera, samsung

REPO = Path(__file__).resolve().parent.parent
STUBS = {
    # Never runs what it is given: writes the command and the script down.
    "sudo": 'echo "sudo $*" >> "$STUB_LOG"; [ -f "${2:-}" ] && cat "$2" >> "$STUB_LOG"; exit 0',
    "pkexec": 'echo "pkexec $*" >> "$STUB_LOG"; [ -f "${2:-}" ] && cat "$2" >> "$STUB_LOG"; exit 0',
    "pacman": 'echo "pacman $*" >> "$STUB_LOG"\n'
              'if [ "$1" = -T ]; then shift; for p in "$@"; do grep -qx "$p" "$STUB_INSTALLED" || echo "$p"; done; exit 0; fi\n'
              'exit 1',
    "hyprctl": 'echo "hyprctl $*" >> "$STUB_LOG"\n'
               'case "$1 $2" in "version -j") echo \'{"version": "0.56.2", "tag": "v0.56.2"}\';;\n'
               '"-j "*) echo "[]";; *) echo ok;; esac',
    "omarchy": 'echo "omarchy $*" >> "$STUB_LOG"',
    "omarchy-shell": 'echo "omarchy-shell $*" >> "$STUB_LOG"',
    "notify-send": 'echo "notify-send $*" >> "$STUB_LOG"',
    "xdg-open": 'echo "xdg-open $*" >> "$STUB_LOG"',
    "systemctl": 'echo "systemctl $*" >> "$STUB_LOG"',
}


@pytest.fixture()
def sandbox(tmp_path):
    home = tmp_path / "home"
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in STUBS.items():
        (stubs / name).write_text(f"#!/bin/sh\n{body}\n")
        (stubs / name).chmod(0o755)
    (home / ".config/hypr").mkdir(parents=True)
    (home / ".config/hypr/hyprland.lua").write_text('require("hypr.bindings")\n')
    (tmp_path / "installed").write_text("python-gobject\nlibadwaita\nffmpeg\ngit\n")
    env = {
        "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"), "XDG_RUNTIME_DIR": str(tmp_path / "run"),
        "PATH": f"{stubs}:{Path(sys.executable).parent}:/usr/bin:/bin",
        "HYPRLAND_INSTANCE_SIGNATURE": "sandbox", "STUB_LOG": str(tmp_path / "log"),
        "STUB_INSTALLED": str(tmp_path / "installed"), "LANG": "C.UTF-8",
    }
    (tmp_path / "run").mkdir()
    (tmp_path / "log").write_text("")

    class Box:
        root, path = tmp_path, home

        def run(self, *args, script=REPO / "install.sh"):
            return subprocess.run(["bash", str(script), *args], env=env, capture_output=True, text=True,
                                  timeout=120, stdin=subprocess.DEVNULL)

        def tuneup(self, *args):
            return subprocess.run([sys.executable, str(REPO / "tuneup"), *args], env=env, capture_output=True,
                                  text=True, timeout=120, stdin=subprocess.DEVNULL)

        @property
        def log(self) -> str:
            return (tmp_path / "log").read_text()
    return Box()


def test_the_installer_installs_into_the_sandbox(sandbox):
    done = sandbox.run("--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    home = sandbox.path
    for name in ("tuneup", "hypr-screens", "hypr-minimizer"):
        assert (home / ".local/bin" / name).is_symlink()
    assert (home / ".local/bin/tuneup").resolve() == REPO / "tuneup"
    lua = (home / ".config/hypr/tuneup.lua").read_text()
    assert 'hl.exec_cmd("tuneup watch")' in lua and "io\\\\.github\\\\.slowlytz\\\\.Tuneup" in lua
    assert 'require("hypr.tuneup")' in (home / ".config/hypr/hyprland.lua").read_text()
    entry = (home / ".local/share/applications/io.github.slowlytz.Tuneup.desktop").read_text()
    assert "Name=Tuneup" in entry and "Categories=Settings;" in entry and "Comment=The settings app Omarchy" in entry
    # --yes keeps what is there already (this machine's camera setup and cava), else "no".
    assert json.loads((home / ".config/tuneup/config.json").read_text())["install"] == \
        {"camera": camera.is_set_up(), "cava": shutil.which("cava") is not None, "galaxy_book": samsung.present()}
    log = sandbox.log
    # One sudo for the packages that are missing; nothing that is there already.
    assert log.count("sudo /bin/sh") == 1
    assert "pacman -S --needed --noconfirm libadwaita" not in log
    assert "pacman -S --needed --noconfirm webkitgtk-6.0 inter-font brightnessctl" in log
    assert "hyprctl dispatch hl.dsp.exec_cmd" in log and "tray" in log and "settings" in log
    assert "It lives in the tray now" in done.stdout


def test_dry_run_changes_nothing(sandbox):
    done = sandbox.run("--yes", "--dry-run")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "[dry-run] sudo /bin/sh" in done.stdout and "[dry-run] python3" in done.stdout
    assert "pacman -S --needed --noconfirm" in done.stdout     # the root script is shown
    assert not (sandbox.path / ".local/bin").exists() and not (sandbox.path / ".config/tuneup").exists()
    assert "sudo" not in sandbox.log and "dispatch" not in sandbox.log


def test_piped_from_curl_it_clones_first(sandbox):
    copy = sandbox.root / "downloaded" / "install.sh"
    copy.parent.mkdir()
    shutil.copy(REPO / "install.sh", copy)
    done = sandbox.run("--dry-run", script=copy)
    assert done.returncode == 0, done.stderr
    assert f"git clone --quiet https://github.com/SlowlyTz/tuneup.git {sandbox.path}/.local/share/tuneup" in done.stdout


def test_update_mode_asks_nothing_and_uses_pkexec(sandbox):
    assert sandbox.run("--yes").returncode == 0
    (sandbox.root / "installed").write_text("\n".join(["python-gobject", "libadwaita", "webkitgtk-6.0", "inter-font",
                                                         "ffmpeg", "brightnessctl"]) + "\n")
    (sandbox.root / "log").write_text("")
    done = sandbox.run("--update")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "pkexec /bin/sh" in sandbox.log and "sudo" not in sandbox.log    # git is missing now
    assert "pacman -S --needed --noconfirm git" in sandbox.log
    assert "is up to date" in done.stdout


def test_checks_stop_on_an_old_hyprland(sandbox):
    stub = sandbox.root / "stubs" / "hyprctl"
    stub.write_text('#!/bin/sh\necho \'{"version": "0.54.0"}\'\n')
    done = sandbox.run("--yes")
    assert done.returncode == 1 and "needs Hyprland 0.56 or newer" in done.stderr


def test_setup_moves_hypr_screens_files_once(sandbox):
    home = sandbox.path
    old = home / ".config/hypr-screens"
    old.mkdir(parents=True)
    (old / "config.json").write_text(json.dumps({"language": "de", "desktop_keys": True}))
    (old / "widgets.json").write_text("{}")
    (home / ".config/hypr/hypr_screens.lua").write_text("-- old\n")
    (home / ".config/hypr/hyprland.lua").write_text(
        'require("hypr.bindings")\n\n-- hypr-screens: keys, desktop keys, monitor watcher\nrequire("hypr.hypr_screens")\n')
    (home / ".config/hypr/autostart.lua").write_text(
        '-- hypr-screens watch is started here\no.launch_on_start("hypr-screens watch")\n')
    runtime = sandbox.root / "run" / "hypr-screens"
    runtime.mkdir()
    (runtime / "fixed.json").write_text("{}")

    done = sandbox.tuneup("setup")
    assert done.returncode == 0, done.stdout + done.stderr
    new = home / ".config/tuneup"
    assert json.loads((new / "config.json").read_text())["language"] == "de"
    assert (new / "widgets.json").exists() and old.is_symlink() and old.resolve() == new
    assert (sandbox.root / "run/tuneup/fixed.json").exists() and runtime.is_symlink()
    hyprland = (home / ".config/hypr/hyprland.lua").read_text()
    assert 'require("hypr.tuneup")' in hyprland and "hypr_screens" not in hyprland
    assert "-- Tuneup: keys" in hyprland
    assert not (home / ".config/hypr/hypr_screens.lua").exists()
    assert "tuneup switch 1" in (home / ".config/hypr/tuneup.lua").read_text()   # the desktop keys came along
    autostart = (home / ".config/hypr/autostart.lua").read_text()
    assert 'o.launch_on_start("tuneup watch")' in autostart and "-- hypr-screens watch" in autostart

    again = sandbox.tuneup("setup")
    assert again.returncode == 0 and "moved" not in again.stdout


def test_both_folders_there_nothing_is_lost(sandbox):
    home = sandbox.path
    (home / ".config/hypr-screens").mkdir(parents=True)
    (home / ".config/hypr-screens/config.json").write_text('{"language": "fr"}')
    (home / ".config/hypr-screens/notes.txt").write_text("mine")
    (home / ".config/tuneup").mkdir()
    (home / ".config/tuneup/config.json").write_text('{"language": "it"}')
    assert sandbox.tuneup("setup").returncode == 0
    assert json.loads((home / ".config/tuneup/config.json").read_text())["language"] == "it"
    assert (home / ".config/tuneup/notes.txt").read_text() == "mine"
    assert json.loads((home / ".config/hypr-screens.old/config.json").read_text())["language"] == "fr"


def test_uninstall_removes_everything_it_brought(sandbox):
    assert sandbox.run("--yes").returncode == 0
    home = sandbox.path
    hyprland_before = (home / ".config/hypr/hyprland.lua.bak-tuneup").read_text()
    (sandbox.root / "log").write_text("")
    done = sandbox.tuneup("uninstall", "--yes")
    assert done.returncode == 0, done.stdout + done.stderr
    assert (home / ".config/hypr/hyprland.lua").read_text() == hyprland_before
    left = sorted(str(p.relative_to(home)) for p in home.rglob("*") if p.is_file() or p.is_symlink())
    assert left == [".config/hypr/hyprland.lua"]
    assert not (sandbox.root / "run/tuneup").exists()
    assert "hyprctl reload" in sandbox.log
    assert "system packages stay" in done.stdout and "webkitgtk-6.0" in done.stdout
    if samsung.root_files() or camera.root_files():          # this machine has them: removed by one pkexec
        assert sandbox.log.count("pkexec /bin/sh") == 1 and "rm -f" in sandbox.log
    else:
        assert "pkexec" not in sandbox.log


def test_uninstall_can_keep_the_settings(sandbox):
    assert sandbox.run("--yes").returncode == 0
    assert sandbox.tuneup("uninstall", "--yes", "--keep-settings").returncode == 0
    assert (sandbox.path / ".config/tuneup/config.json").exists()
    assert not (sandbox.path / ".local/bin/tuneup").exists()


def test_uninstall_asks_first(sandbox):
    assert sandbox.run("--yes").returncode == 0
    done = sandbox.tuneup("uninstall")
    assert done.returncode == 1 and "Nothing removed" in done.stdout
    assert (sandbox.path / ".local/bin/tuneup").exists()


def test_restart_only_sees_processes_of_this_session(sandbox):
    done = sandbox.tuneup("restart")
    assert done.returncode == 0 and "stopped" not in done.stdout


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_shellcheck():
    assert subprocess.run(["shellcheck", str(REPO / "install.sh")]).returncode == 0


def test_the_installer_is_valid_bash():
    assert subprocess.run(["bash", "-n", str(REPO / "install.sh")]).returncode == 0
    assert os.access(REPO / "install.sh", os.X_OK) and os.access(REPO / "tuneup", os.X_OK)


def test_a_symlinked_hyprland_lua_stays_a_symlink(sandbox):
    hypr = sandbox.path / ".config/hypr"
    real = sandbox.root / "dotfiles-hyprland.lua"
    real.write_text('require("hypr.bindings")\n')
    (hypr / "hyprland.lua").unlink()
    (hypr / "hyprland.lua").symlink_to(real)
    assert sandbox.tuneup("setup").returncode == 0
    assert (hypr / "hyprland.lua").is_symlink() and 'require("hypr.tuneup")' in real.read_text()
