"""What every endpoint shares: ApiError, @endpoint (and METHODS, the registry
the bridge calls through call()), and the helpers for reading and changing
the settings."""
import functools
import inspect
import re

from hypr_screens import config, engine, hypr
from hypr_screens import samsung as samsung_mod


class ApiError(Exception):
    """Rejects the page's promise with {code, message}. Codes are stable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_json(self) -> dict:
        return {"code": self.code, "message": self.message}


METHODS: dict = {}


def endpoint(function):
    """A method the page can call: wrong arguments and any failure become ApiError."""
    signature = inspect.signature(function)

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            signature.bind(*args, **kwargs)
        except TypeError as error:
            raise ApiError("bad_args", f"{function.__name__}: {error}") from None
        try:
            return function(*args, **kwargs)
        except ApiError:
            raise
        except config.ConfigError as error:
            raise ApiError("config_unreadable", f"{error}. Fix or remove the file; nothing was saved.") from error
        except samsung_mod.NotSetUp as error:
            raise ApiError("not_set_up", str(error)) from error
        except ValueError as error:
            raise ApiError("bad_value", str(error)) from error
        except Exception as error:  # never let a raw exception reach the page
            raise ApiError("internal", f"{type(error).__name__}: {error}") from error

    METHODS[function.__name__] = wrapper
    return wrapper


def snake_case(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def call(method: str, args: list | None = None) -> object:
    """For the bridge: `api.call("setScreenSetting", [...])`."""
    function = METHODS.get(snake_case(str(method)))
    if function is None:
        raise ApiError("unknown_method", f"no such method: {method}")
    return function(*(args or []))


# --- helpers ---------------------------------------------------------------------------


def settings() -> dict:
    """The settings, strictly (an unreadable file is an error, not the defaults)."""
    return config.read()


def recorded() -> tuple[dict, list[dict]]:
    """The settings with every connected monitor recorded, and all monitors."""
    monitors = hypr.monitors(include_disabled=True)
    return config.update(lambda cfg: config.record(cfg, monitors)), monitors


def changing(function, *args):
    """A config.update() mutation from a backend helper `function(cfg, *args)`."""
    def mutate(cfg: dict) -> None:
        function(cfg, *args)
    return mutate


def need(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ApiError(code, message)


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def run_sync() -> list[str]:
    try:
        return engine.sync()
    except Exception as error:
        raise ApiError("apply_failed", f"Saved, but applying it failed: {error}") from error
