"""Thin hyprctl wrappers. Tuneup needs Hyprland >= 0.56 (Lua dispatchers)."""
import json
import subprocess

HYPRCTL_SECONDS = 5


def hyprctl(*args: str) -> str:
    """hyprctl's reply; an error text when it hangs or is missing, so a stuck
    compositor cannot hang the watcher or the settings window."""
    try:
        return subprocess.run(
            ["hyprctl", *args], check=False, text=True, capture_output=True, timeout=HYPRCTL_SECONDS
        ).stdout
    except subprocess.TimeoutExpired:
        return "error: hyprctl timed out"
    except OSError as error:
        return f"error: {error}"


def rejected(reply: str) -> bool:
    """Whether Hyprland refused a command: an error text instead of "ok" (an
    empty answer counts as taken, as before this check existed)."""
    text = str(reply or "").strip().lower()
    if not text or text == "ok":
        return False
    return text.startswith(("error", "err:", "invalid", "unknown", "failed", "couldn't", "could not")) \
        or "error:" in text or "lua error" in text


def query(what: str, *args: str) -> object:
    try:
        return json.loads(hyprctl("-j", what, *args) or "null")
    except json.JSONDecodeError:
        return None


def query_list(what: str, *args: str) -> list[dict]:
    result = query(what, *args)
    if not isinstance(result, list):
        return []
    return [item for item in result if isinstance(item, dict)]


def monitors(include_disabled: bool = False) -> list[dict]:
    return query_list("monitors", "all") if include_disabled else query_list("monitors")


def dispatch(expression: str) -> str:
    return hyprctl("dispatch", expression)


def eval_lua(code: str) -> str:
    return hyprctl("eval", code)


def lua_string(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'
