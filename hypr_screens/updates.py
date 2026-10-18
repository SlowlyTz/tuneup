"""Updates: Tuneup is a git checkout (the installer's clone in
~/.local/share/tuneup, or the user's own); an update is `git pull --ff-only`
and `install.sh --update` (packages that are new, the integration, restarting
the watcher and the tray, the window again).

check() says whether there is one and whether it can be done; run() does it.
The settings window starts `tuneup update --report` detached (it restarts the
tray, which closes the window) and follows its status file.
"""
import json
import re
import subprocess

from hypr_screens import brand, config

GIT_SECONDS = 30
INSTALL_SECONDS = 1800
LOG_LINES = 40
REASONS = ("not_git", "local_changes", "diverged", "offline")


def git(*args: str, timeout: float = GIT_SECONDS) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(brand.ROOT), *args], capture_output=True, text=True, timeout=timeout,
                          check=False)


def version_of(pyproject: str) -> str | None:
    """The version line of pyproject.toml's [project] table."""
    project = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", pyproject, re.M | re.S)
    found = re.search(r'^version\s*=\s*"([^"]+)"', project.group(1), re.M) if project else None
    return found.group(1) if found else None


def current_version() -> str:
    try:
        return version_of((brand.ROOT / "pyproject.toml").read_text()) or "?"
    except OSError:
        return "?"


def version_key(version: str | None) -> tuple:
    """"1.10.0" > "1.9.2"; "v1.2" counts like "1.2"; anything else is lowest."""
    numbers = re.findall(r"\d+", str(version or ""))
    return tuple(int(n) for n in numbers) if numbers else (-1,)


def is_checkout() -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    except (OSError, subprocess.TimeoutExpired):
        return False


def upstream() -> str:
    """origin's branch this one follows (origin/master if none is set)."""
    found = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return found.stdout.strip() if found.returncode == 0 and found.stdout.strip() else "origin/master"


def counts(remote: str) -> tuple[int, int]:
    """(commits behind, commits ahead) of origin."""
    found = git("rev-list", "--left-right", "--count", f"{remote}...HEAD")
    try:
        behind, ahead = (int(n) for n in found.stdout.split())
    except ValueError:
        return 0, 0
    return behind, ahead


def latest_version(remote: str) -> str | None:
    """The version in origin's pyproject.toml, else origin's newest tag."""
    shown = git("show", f"{remote}:pyproject.toml")
    if shown.returncode == 0 and version_of(shown.stdout):
        return version_of(shown.stdout)
    tags = git("tag", "--list", "--sort=-v:refname").stdout.split()
    return tags[0].lstrip("v") if tags else None


def fetched(remote: str) -> bool:
    try:
        return git("fetch", "--quiet", "--tags", remote).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def check(fetch: bool = True) -> dict:
    """The settings window's checkUpdate() shape."""
    result = {"current": current_version(), "latest": None, "available": False, "commitsBehind": 0,
              "canUpdate": False, "reason": None}
    if not is_checkout():
        return {**result, "reason": "not_git"}
    remote = upstream()
    if fetch and not fetched(remote.split("/", 1)[0]):
        return {**result, "reason": "offline"}
    behind, ahead = counts(remote)
    result.update(latest=latest_version(remote), commitsBehind=behind, available=behind > 0)
    if behind and git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        result["reason"] = "local_changes"
    elif behind and ahead:
        result["reason"] = "diverged"
    result["canUpdate"] = result["available"] and result["reason"] is None
    return result


REASON_TEXTS = {
    "not_git": "Tuneup was not installed with git: run the installer again to update.",
    "local_changes": "the checkout has changes of its own: commit or stash them first.",
    "diverged": "the checkout has commits origin does not have: update it by hand (git pull).",
    "offline": "GitHub cannot be reached: try again later.",
}


# --- the status file the settings window follows ---------------------------------------------


def status_file():
    return config.runtime_dir() / "update.json"


def read_status() -> dict:
    """The settings window's updateStatus() shape."""
    try:
        status = json.loads(status_file().read_text())
    except (OSError, json.JSONDecodeError):
        status = {}
    idle = {"state": "idle", "from": None, "to": None, "log": [], "error": None}
    return {**idle, **{k: v for k, v in status.items() if k in idle}} if isinstance(status, dict) else idle


def write_status(**changes) -> None:
    status = {**read_status(), **changes}
    status["log"] = status["log"][-LOG_LINES:]
    temporary = status_file().with_suffix(".tmp")
    temporary.write_text(json.dumps(status) + "\n")
    temporary.replace(status_file())


def say(line: str, report: bool) -> None:
    print(line, flush=True)
    if report:
        write_status(log=[*read_status()["log"], line])


# --- doing it ------------------------------------------------------------------------------------


def remember_previous(version: str) -> None:
    """The welcome after the update says "updated from <version>" also for a
    user who never saw one (installed before welcomes existed)."""
    config.update(lambda cfg: False if cfg["seen_version"] else cfg.__setitem__("seen_version", version))


def run(report: bool = False, runner=subprocess.run) -> int:
    """Pull and run the installer in update mode; 0 when done. report: keep the
    status file up to date (for the settings window)."""
    before = current_version()
    if report:
        write_status(state="running", **{"from": before, "to": None}, log=[], error=None)
    state = check()
    if not state["canUpdate"]:
        why = REASON_TEXTS.get(state["reason"]) or "Tuneup is up to date."
        say(f"{brand.COMMAND} update: {why}", report)
        if report:
            write_status(state="done" if state["reason"] is None else "failed", to=before,
                         error=state["reason"])
        return 0 if state["reason"] is None else 1
    say(f"Updating Tuneup {before} -> {state['latest']} ({state['commitsBehind']} new commits)", report)
    pulled = git("pull", "--ff-only", "--quiet")
    if pulled.returncode != 0:
        return failed(pulled.stderr.strip() or "git pull failed", report)
    remember_previous(before)
    done = runner(["bash", str(brand.ROOT / "install.sh"), "--update"], capture_output=True, text=True,
                  timeout=INSTALL_SECONDS, check=False)
    for line in (done.stdout or "").splitlines()[-LOG_LINES:]:
        say(strip_colors(line), report)
    if done.returncode != 0:
        last = (done.stderr or "").strip().splitlines()
        return failed(strip_colors(last[-1]) if last else f"install.sh --update failed ({done.returncode})", report)
    if report:
        write_status(state="done", to=current_version(), error=None)
    return 0


def failed(error: str, report: bool) -> int:
    say(f"{brand.COMMAND} update failed: {error}", report)
    if report:
        write_status(state="failed", error=error)
    return 1


def strip_colors(line: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", line)
