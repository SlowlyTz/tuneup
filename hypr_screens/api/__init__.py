"""The backend of the HTML settings window (hypr_screens/web/).

The page calls `window.api.someMethod(a, b)`; the WebKit bridge turns that
into `some_method(a, b)` here (camelCase -> snake_case, positional JSON
arguments, the return value as JSON). `call(name, args)` does exactly that,
for the bridge. An ApiError rejects the page's promise with {code, message};
every endpoint turns any other exception into ApiError("internal", ...).

Each change goes the way the old GTK window did it: the settings through
config.update() (locked, atomic, never over an unreadable file), then what
makes it live -- engine.sync() for screens, the Lua file and go_live for
keys, widgets.apply() for widgets, look.apply() for the window look.

One module per page: displays, shortcuts, appearance, audio, webcam,
galaxy_book, desktop_widgets, enforcing, general; what they share is in core.
Every endpoint is also `api.<name>`. The shapes, the error codes and where
they differ from the old mock are in hypr_screens/web/API.md; web/mock.js
returns the same shapes.
"""
from hypr_screens.api import (appearance, audio, desktop_widgets, displays, enforcing, galaxy_book,  # noqa: F401
                              general, shortcuts, webcam)
from hypr_screens.api.core import METHODS, ApiError, call, endpoint  # noqa: F401

globals().update(METHODS)
