"""Background watcher: re-sync on monitor hotplug and config reloads, audit
what Tuneup set (drift.py, when enforcement is on), keep force-muted
sound devices silent (sound.guard), hold the Samsung charge limit and
performance mode (samsung.guard) and feed the virtual camera (camera.guard),
each guard in its own thread.

A hotplug arrives as a burst of events and settles over a moment -- a dock
unplugs and plugs its screens in waves -- so events are collected until
SETTLE_SECONDS pass quietly, then one sync runs. The reload our own sync
caused (apply.reset) is not a reason for another one. Events that can mean a
desktop was moved elsewhere bring the next audit forward.

Closing windows when the external screen goes (option "close") cannot be
undone: that sync waits CLOSE_SETTLE_SECONDS more and looks again first.

The watcher outlives updates and Hyprland hiccups: a lost event socket is
connected again (with a growing pause; it gives up when Hyprland is gone), and
when Tuneup's own files change under it, it starts itself again -- old code
must not keep writing the settings of new code.
"""
import fcntl
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from hypr_screens import apply, camera, config, desktops, drift, engine, enforce, install, samsung, sound, widgets

SETTLE_SECONDS = 1.0
# A screen that is gone for good, before windows are closed for it (a dock
# reconnects in waves, a screen in standby comes back).
CLOSE_SETTLE_SECONDS = 10.0
# Pause before the event socket is connected again: doubling up to the maximum.
RECONNECT_FIRST, RECONNECT_MAX = 1.0, 30.0
# How often the package's files are looked at (an update replaces them).
CODE_CHECK_SECONDS = 20.0
# An own reload's event comes within this time.
ECHO_SECONDS = 5.0
EVENTS = {
    "monitoradded": "added",
    "monitoraddedv2": "added",
    "monitorremoved": "removed",
    "monitorremovedv2": "removed",
    "configreloaded": "reload",
}
# Events after which a desktop may sit on the wrong screen: audit soon.
DRIFT_EVENTS = {"moveworkspace", "moveworkspacev2", "createworkspace", "createworkspacev2"}
AUDIT_SOON_SECONDS = 1.5


def event_socket() -> Path | None:
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not signature:
        return None
    for base in (os.environ.get("XDG_RUNTIME_DIR"), "/tmp"):
        if base:
            path = Path(base) / "hypr" / signature / ".socket2.sock"
            if path.exists():
                return path
    return None


def names(lines: list[bytes]) -> set[str]:
    return {line.partition(b">>")[0].decode(errors="replace") for line in lines}


def kinds(lines: list[bytes]) -> set[str]:
    return {EVENTS[name] for name in names(lines) if name in EVENTS}


def strongest(found: set[str]) -> str:
    """One sync per burst: plugging in wins over unplugging over a reload; a
    pending close (the second look) comes last."""
    for kind in ("added", "removed", "reload", "closing"):
        if kind in found:
            return kind
    return ""


def log(message: str) -> None:
    print(f"tuneup watch: {message}", file=sys.stderr, flush=True)


def safe(work, what: str) -> str:
    """One job, logged; an error must not end the watcher -- its threads keep
    force-muted devices silent, and nothing would start it again before the
    next login."""
    try:
        return work() or ""
    except Exception as error:
        return f"{what} failed: {error!r}"


def safe_list(work) -> list[str]:
    """safe() for a job that returns lines."""
    try:
        return work()
    except Exception as error:
        return [f"audit failed: {error!r}"]


def safe_sync(kind: str) -> str:
    return safe(lambda: ", ".join(engine.sync(kind)), "sync") or "nothing to change"


def run_sync(kind: str, close_ok: bool = False) -> list[str]:
    """One sync; what it did, or one line saying it failed."""
    try:
        return engine.sync(kind, close_ok=True) if close_ok else engine.sync(kind)
    except Exception as error:
        return [f"sync failed: {error!r}"]


# --- changed code ------------------------------------------------------------------------


def code_stamp() -> tuple:
    """What the package's files look like now (count, newest change, total size)."""
    newest, size, count = 0, 0, 0
    for path in Path(__file__).resolve().parent.rglob("*.py"):
        try:
            info = path.stat()
        except OSError:
            continue
        newest, size, count = max(newest, info.st_mtime_ns), size + info.st_size, count + 1
    return count, newest, size


STARTED_WITH = code_stamp()
# File states that were tried and do not load: not tried again until they change.
REFUSED: set[tuple] = set()


class Watcher:
    """What to do when, from the events and the clock (the socket loop only
    reads and waits; tests drive this directly)."""

    def __init__(self, now: float):
        self.pending: set[str] = set()
        self.quiet_at = 0.0
        self.next_audit = now + enforce.AUDIT_SECONDS
        self.next_beat = now
        self.code = STARTED_WITH  # what the files looked like when this process began
        self.code_seen = self.code  # the last look, to tell an update that is still being written
        self.next_code_check = now + CODE_CHECK_SECONDS
        self.restart = False

    def check_code(self, now: float) -> None:
        """Sets `restart` when the files changed since the start and stay
        changed over two looks (an update is not written in one moment)."""
        if now < self.next_code_check:
            return
        self.next_code_check = now + CODE_CHECK_SECONDS
        stamp = code_stamp()
        if stamp != self.code and stamp == self.code_seen and stamp not in REFUSED:
            self.restart = True
        self.code_seen = stamp

    def feed(self, lines: list[bytes], now: float) -> None:
        found = kinds(lines)
        if found == {"reload"} and apply.reloaded_by_us(ECHO_SECONDS):
            found = set()  # our own reload: that sync is done already
        if found:
            self.pending |= found
            self.quiet_at = now + SETTLE_SECONDS
        if "changeworkspaceid" in names(lines):
            if message := safe(lambda: desktops.renumbered(lines), "renumbered desktops"):
                log(message)
        if names(lines) & DRIFT_EVENTS:
            self.next_audit = min(self.next_audit, now + AUDIT_SOON_SECONDS)

    def wait(self, now: float) -> float:
        """Seconds until there is something to do."""
        due = [self.next_audit, self.next_beat] + ([self.quiet_at] if self.pending else [])
        return max(0.05, min(due) - now)

    def tick(self, now: float) -> list[str]:
        """Does what is due; returns what to log."""
        said = []
        if self.pending and now >= self.quiet_at:
            kind = strongest(self.pending)
            self.pending.clear()
            done = run_sync("removed" if kind == "closing" else kind, close_ok=kind == "closing")
            said.append(f"{kind}: {', '.join(done) or 'nothing to change'}")
            if engine.CLOSE_PENDING in done:
                self.pending.add("closing")
                self.quiet_at = now + CLOSE_SETTLE_SECONDS
                said.append(f"windows are not closed yet: looking again in {CLOSE_SETTLE_SECONDS:g} s")
            if kind in ("added", "removed"):
                if message := safe(widgets.auto_layout, "widget layout"):
                    said.append(message)
            self.next_audit = now + enforce.AUDIT_SECONDS  # let the new state settle first
        elif not self.pending and now >= self.next_audit:
            self.next_audit = now + enforce.AUDIT_SECONDS
            said += [f"put back {fix}" for fix in safe_list(drift.run)]
        if now >= self.next_beat:
            self.next_beat = now + enforce.AUDIT_SECONDS
            safe(enforce.heartbeat, "heartbeat")
        self.check_code(now)
        return said


def start_guards() -> None:
    threading.Thread(target=sound.guard, daemon=True).start()
    threading.Thread(target=samsung.guard, daemon=True).start()
    threading.Thread(target=camera.guard, daemon=True).start()
    log(f"battery panel: {safe(lambda: install.sync_power_panel(samsung.active()), 'battery panel')}")


def connect(path: Path) -> socket.socket:
    events = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        events.connect(str(path))
    except OSError:
        events.close()
        raise
    return events


def listen(events, watcher: Watcher) -> None:
    """Reads events until the socket ends (or the code changed); errors of the socket go up."""
    buffer = b""
    while not watcher.restart:
        events.settimeout(watcher.wait(time.monotonic()))
        try:
            chunk = events.recv(4096)
        except TimeoutError:
            for message in watcher.tick(time.monotonic()):
                log(message)
            continue
        if not chunk:
            return
        buffer += chunk
        *lines, buffer = buffer.split(b"\n")
        watcher.feed(lines, time.monotonic())
        # Busy desktops send events all the time: what is due must not wait for a pause.
        for message in watcher.tick(time.monotonic()):
            log(message)


def restart_self() -> None:
    """Start this watcher again with the new files (the lock goes with the old
    process image). Not when the new code does not even import: it would end
    the watcher for good. Returns when it did not."""
    probe = subprocess.run([sys.executable, "-c", "import hypr_screens.watch"], check=False,
                           capture_output=True, timeout=60, cwd=str(Path(__file__).resolve().parent.parent))
    if probe.returncode != 0:
        REFUSED.add(code_stamp())
        log("the files changed but do not load; keeping the running code")
        return
    log("the files changed: starting again")
    os.execv(sys.executable, [sys.executable, *sys.orig_argv[1:]])


def try_restart(watcher: Watcher) -> None:
    if not watcher.restart:
        return
    watcher.restart = False
    try:
        restart_self()
    except (OSError, subprocess.SubprocessError) as error:
        log(f"cannot start again: {error!r}")


def watch(sleep=time.sleep) -> int:
    lock = open(config.runtime_dir() / "watch.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("already running")
        return 0

    start_guards()
    # hwmon numbers change between boots: point the widgets at this boot's CPU sensor.
    if message := safe(lambda: widgets.export(config.load()), "widget export"):
        log(message)
    delay, first = RECONNECT_FIRST, True
    while True:
        path = event_socket()
        if path is None:
            log("no Hyprland event socket" if first else "Hyprland is gone: stopping")
            return 1 if first else 0
        watcher = Watcher(time.monotonic())
        try:
            with connect(path) as events:
                log(f"{'started' if first else 'connected again'}, "
                    f"{safe_sync('added' if first else 'reload')}")
                first, delay = False, RECONNECT_FIRST
                listen(events, watcher)
            log("the event socket ended")
        except OSError as error:
            log(f"event socket: {error!r}")
        try_restart(watcher)
        if not path.exists():
            log("Hyprland is gone: stopping")
            return 0
        sleep(delay)
        delay = min(RECONNECT_MAX, delay * 2)
