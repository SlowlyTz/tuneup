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
"""
import fcntl
import os
import socket
import sys
import threading
import time
from pathlib import Path

from hypr_screens import apply, camera, config, drift, engine, enforce, install, samsung, sound, widgets

SETTLE_SECONDS = 1.0
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
    """One sync per burst: plugging in wins over unplugging over a reload."""
    for kind in ("added", "removed", "reload"):
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
    return safe(lambda: engine.sync(kind), "sync") or "nothing to change"


class Watcher:
    """What to do when, from the events and the clock (the socket loop only
    reads and waits; tests drive this directly)."""

    def __init__(self, now: float):
        self.pending: set[str] = set()
        self.quiet_at = 0.0
        self.next_audit = now + enforce.AUDIT_SECONDS
        self.next_beat = now

    def feed(self, lines: list[bytes], now: float) -> None:
        found = kinds(lines)
        if found == {"reload"} and apply.reloaded_by_us(ECHO_SECONDS):
            found = set()  # our own reload: that sync is done already
        if found:
            self.pending |= found
            self.quiet_at = now + SETTLE_SECONDS
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
            said.append(f"{kind}: {safe_sync(kind)}")
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
        return said


def start_guards() -> None:
    threading.Thread(target=sound.guard, daemon=True).start()
    threading.Thread(target=samsung.guard, daemon=True).start()
    threading.Thread(target=camera.guard, daemon=True).start()
    log(f"battery panel: {safe(lambda: install.sync_power_panel(samsung.active()), 'battery panel')}")


def watch() -> int:
    lock = open(config.runtime_dir() / "watch.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("already running")
        return 0

    start_guards()
    path = event_socket()
    if path is None:
        log("no Hyprland event socket")
        return 1

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as events:
        events.connect(str(path))
        log(f"started, {safe_sync('added')}")
        watcher = Watcher(time.monotonic())
        buffer = b""
        while True:
            events.settimeout(watcher.wait(time.monotonic()))
            try:
                chunk = events.recv(4096)
            except TimeoutError:
                for message in watcher.tick(time.monotonic()):
                    log(message)
                continue
            if not chunk:
                return 0
            buffer += chunk
            *lines, buffer = buffer.split(b"\n")
            watcher.feed(lines, time.monotonic())
            # Busy desktops send events all the time: what is due must not wait for a pause.
            for message in watcher.tick(time.monotonic()):
                log(message)
