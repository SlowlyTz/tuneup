"""Updates against throwaway git repositories (a bare "origin" and a clone in
tmp_path; no network), the welcome after install and update, and the API's
update and uninstall endpoints (nothing is started for real)."""
import subprocess

import pytest

from hypr_screens import api, brand, config, updates
from hypr_screens.api import maintenance

PYPROJECT = '[build-system]\nrequires = []\n\n[project]\nname = "hypr-minimizer"\nversion = "{version}"\n'


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                   cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def checkout(tmp_path, monkeypatch):
    """origin at 1.0.0 and a clone of it as Tuneup's ROOT; install.sh only says it ran."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-b", "master", str(origin)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-b", "master")
    (seed / "pyproject.toml").write_text(PYPROJECT.format(version="1.0.0"))
    (seed / "install.sh").write_text('echo "install.sh $*"\necho "  ✓ done" >&1\n')
    git(seed, "add", ".")
    git(seed, "commit", "-m", "1.0.0")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "-u", "origin", "master")
    git(tmp_path, "clone", str(origin), str(work))
    monkeypatch.setattr(brand, "ROOT", work)

    def release(version):
        (seed / "pyproject.toml").write_text(PYPROJECT.format(version=version))
        git(seed, "commit", "-am", version)
        git(seed, "push", "origin", "master")
    return work, release


def test_up_to_date_then_an_update_is_found(checkout):
    work, release = checkout
    assert updates.check() == {"current": "1.0.0", "latest": "1.0.0", "available": False, "commitsBehind": 0,
                               "canUpdate": False, "reason": None}
    release("1.1.0")
    assert updates.check() == {"current": "1.0.0", "latest": "1.1.0", "available": True, "commitsBehind": 1,
                               "canUpdate": True, "reason": None}


def test_what_stands_in_the_way(checkout, tmp_path, monkeypatch):
    work, release = checkout
    release("1.1.0")
    (work / "pyproject.toml").write_text("changed")
    assert updates.check()["reason"] == "local_changes"
    git(work, "commit", "-am", "mine")
    assert updates.check()["reason"] == "diverged"
    git(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert updates.check()["reason"] == "offline"
    monkeypatch.setattr(brand, "ROOT", tmp_path / "not-a-checkout")
    (tmp_path / "not-a-checkout").mkdir()
    assert updates.check()["reason"] == "not_git"


def test_an_update_pulls_runs_the_installer_and_reports(checkout):
    work, release = checkout
    release("1.2.0")
    config.update(lambda cfg: cfg.__setitem__("seen_version", None))
    assert updates.run(report=True) == 0
    status = updates.read_status()
    assert status["state"] == "done" and (status["from"], status["to"]) == ("1.0.0", "1.2.0")
    assert "install.sh --update" in status["log"] and status["log"][0].startswith("Updating Tuneup 1.0.0 -> 1.2.0")
    assert updates.current_version() == "1.2.0"
    # Someone who never saw a welcome hears "updated from 1.0.0".
    assert api.welcome() == {"show": True, "kind": "updated", "from": "1.0.0", "to": "1.2.0",
                             "releasesUrl": "https://github.com/SlowlyTz/tuneup/releases"}


def test_a_failing_installer_is_reported(checkout):
    work, release = checkout
    release("1.3.0")

    def broken(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="✗ The system setup failed\n")
    assert updates.run(report=True, runner=broken) == 1
    assert updates.read_status()["state"] == "failed"
    assert updates.read_status()["error"] == "✗ The system setup failed"


def test_nothing_to_do_is_done(checkout):
    assert updates.run(report=True) == 0
    assert updates.read_status()["state"] == "done"


def test_versions_compare_by_number():
    assert updates.version_key("1.10.0") > updates.version_key("1.9.2") > updates.version_key("v1.2")
    assert updates.version_of(PYPROJECT.format(version="2.0.1")) == "2.0.1"
    assert updates.version_of("[tool.x]\nversion = \"9\"\n") is None


# --- the welcome and the endpoints ----------------------------------------------------------


def test_welcome_once_after_install_and_after_each_update(checkout, monkeypatch):
    assert api.welcome()["kind"] == "installed"
    assert api.dismiss_welcome() == {"show": False, "kind": None, "from": None, "to": "1.0.0",
                                     "releasesUrl": brand.RELEASES_URL}
    assert api.welcome()["show"] is False
    monkeypatch.setattr(updates, "current_version", lambda: "1.1.0")
    assert api.welcome() == {"show": True, "kind": "updated", "from": "1.0.0", "to": "1.1.0",
                             "releasesUrl": brand.RELEASES_URL}


def test_update_and_uninstall_start_detached(checkout, monkeypatch, tmp_path):
    started = []

    class Popen:
        def __init__(self, command, **kwargs):
            started.append((command[2:], kwargs["start_new_session"]))
    monkeypatch.setattr(maintenance.subprocess, "Popen", Popen)
    assert api.run_update() == {"started": True}
    assert started[-1] == (["update", "--report"], True)
    assert api.update_status()["state"] == "running"
    with pytest.raises(api.ApiError) as error:
        api.run_update()
    assert error.value.code == "busy"
    assert api.uninstall(True) == {"started": True}
    assert started[-1] == (["uninstall", "--yes", "--keep-settings"], True)
    with pytest.raises(api.ApiError):
        api.uninstall("yes")


def test_about_has_the_new_links(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    about = api.about()
    assert (about["repoUrl"], about["releasesUrl"]) == ("https://github.com/SlowlyTz/tuneup",
                                                        "https://github.com/SlowlyTz/tuneup/releases")
    assert about["guideUrl"] == "https://github.com/SlowlyTz/tuneup/tree/master/docs"
    assert about["configDir"].endswith("tuneup")


def test_installer_helper_remembers_the_answers(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from hypr_screens import installer

    installer.main("remember", ["camera=1", "cava=0", "galaxy_book=yes", "bogus=1"])
    assert config.load()["install"] == {"camera": True, "cava": False, "galaxy_book": True}
    installer.main("choices", [])
    assert capsys.readouterr().out.split() == ["camera=1", "cava=0", "galaxy_book=1"]
    installer.main("packages", ["camera", "cava"])
    names = capsys.readouterr().out.split()
    assert names[-2:] == ["v4l2loopback-dkms", "cava"] and "webkitgtk-6.0" in names
