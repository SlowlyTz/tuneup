"""What the settings window shows of a desktop widget: its content and where
and when it shows -- as a schema the HTML settings window can draw and
api.update_widget() checks changes against.

Taken from the old GTK page (gui/widgets_tab.py: SECTIONS, CHOICE_LABELS,
SWITCH_TITLES, SLIDER_ROWS, EXPANDERS) and the ranges in widgets.py. The look
-- colors, accent, font, weight, effect, card, opacity, size, letter spacing,
the gap between bars and the lyrics' alignment, line size and scroll time --
is left out on purpose: it is set on the desktop in the arrange tool.

Labels are English i18n source texts (locales.json translates them).

A field: {"key", "type", "label", "group", "default", ...}
  type "toggle": a bool.
  type "choice": "choices": [{"value", "label"}]; "dynamic": True when the
      choices depend on the machine (media players, screens).
  type "number": "min", "max", "step", "unit"; whole numbers.
  type "text":   "maxLength"; "format": "timezone" for an IANA zone ("" = off).
  type "multi":  a list of "choices" values; for "desktops" ["all"] = every desktop.
  group: "content" or "where".
  "section": the title of the fold-out row it sits in (e.g. "Date").
  "enabledBy": a toggle key it only matters with (e.g. "date").
  "showIf": {key: value} -- only shown while that other field has that value.
  "hint": an explaining sentence.
"""
from hypr_screens import widgets

# Content per widget, in the order the old page had them. An entry is a key,
# or (section title, enabled-by toggle or None, [keys]) for a fold-out row.
CONTENT = {
    "visualizer": ["player", "bars", "style", ("Motion", None, ["sensitivity", "smoothing", "peaks"])],
    "lyrics": ["player", "highlight", "lines", "hide_paused"],
    "clock": ["clock_style", "hours", "seconds",
              ("Date", "date", ["date", "weekday", "date_format", "date_pattern"]), "zone2"],
    "system": ["cpu", "memory", "temperature", "curves"],
    "nowplaying": ["player", "np_layout",
                   ("Parts", None, ["show_cover", "show_title", "show_artist", "show_album", "show_progress",
                                    "show_time", "show_controls"]), "hide_idle"],
    "weather": ["units", "show_place", "show_details", "show_forecast"],
    "calendar": ["week_start", "show_month", "show_weeks"],
    "battery": ["show_percent", "show_remaining", "low"],
    "network": ["curves"],
    "disk": ["show_free"],
}
# Where and when, for every widget (the visualizer also has "where": bar/desktop).
WHERE = ["screens", "same_place", "desktops", "only_empty", "hide_on_battery", "above"]

CHOICE_TITLES = {"where": "Where", "style": "Style", "highlight": "Highlight", "hours": "Time format",
                 "clock_style": "Style", "date_format": "Date format", "np_layout": "Layout", "units": "Units",
                 "week_start": "Week starts on"}
CHOICE_LABELS = {
    "where": {"bar": "In the bar", "desktop": "On the desktop", "both": "Bar and desktop"},
    "style": {"bottom": "Bars from the bottom", "mirrored": "Mirrored from the middle", "wave": "Wave",
              "dots": "Dots", "circle": "Circle"},
    "highlight": {"line": "Current line", "word": "Word by word", "off": "Off"},
    "hours": {"24": "24-hour", "12": "12-hour"},
    "clock_style": {"digital": "Digital", "analog": "Analog", "flip": "Flip cards", "words": "In words"},
    "np_layout": {"row": "Cover beside the text", "column": "Cover above the text"},
    "units": {"c": "Celsius", "f": "Fahrenheit"},
    "week_start": {"monday": "Monday", "sunday": "Sunday"},
    "date_format": {"long": "Long (3 October)", "medium": "Medium (3 Oct 2026)",
                    "short": "Short (as the language writes it)", "iso": "ISO (2026-10-03)", "custom": "Own pattern"},
}
SWITCH_TITLES = {"hide_paused": "Hide while paused", "date": "Show the date", "seconds": "Show seconds",
                 "cpu": "CPU usage", "memory": "Memory", "temperature": "Temperature", "curves": "Show the curves",
                 "only_empty": "Only on an empty desktop", "hide_on_battery": "Hide on battery",
                 "above": "Above the windows", "same_place": "Same place on every screen",
                 "weekday": "Show the weekday", "peaks": "Peak marks", "show_cover": "Cover", "show_title": "Title",
                 "show_artist": "Artist", "show_album": "Album", "show_progress": "Progress bar", "show_time": "Time",
                 "show_controls": "Buttons", "hide_idle": "Hide while nothing plays", "show_place": "Place",
                 "show_details": "Details", "show_forecast": "Next days", "show_month": "Month name",
                 "show_weeks": "Week numbers", "show_percent": "Percent", "show_remaining": "Time left",
                 "show_free": "Free space instead of used"}
# key: (title, step, unit); the range is widgets.RANGES.
NUMBERS = {"bars": ("Bars", 1, ""), "lines": ("Lines", 1, ""), "sensitivity": ("Sensitivity", 10, " %"),
           "smoothing": ("Smoothing", 5, " %"), "low": ("Low at", 5, " %")}
HINTS = {
    "highlight": "Word by word follows the singing; most songs only have times per line, "
                 "then the words are spread over the line.",
    "same_place": "Off: arrange it on each screen on its own.",
    "player": "With an app picked, only its music counts – the visualizer then hears only that app.",
}
TITLES = widgets.TITLES
DESCRIPTIONS = {
    "visualizer": "Bars that move with the sound playing right now.",
    "lyrics": "The words of the song playing, in time with the music (from lrclib.net).",
    "clock": "A big clock with the date.",
    "system": "CPU, memory and temperature with a curve of the last two minutes.",
    "nowplaying": "The song playing with its cover, a progress bar and buttons.",
    "weather": "The weather at the place set in Omarchy's weather panel.",
    "calendar": "This month with today marked.",
    "battery": "The battery's charge as a ring, with the time left.",
    "network": "Download and upload right now, with curves.",
    "disk": "How full every disk is.",
}
DATE_PATTERN_MAX = 60
# The desktops a widget can be limited to, as the settings window names them.
DESKTOP_VALUES = [str(n) for n in range(1, 11)] + ["fixed"]
SCREEN_MODES = ["laptop", "external", "all"]


def content_keys(kind: str) -> list[str]:
    keys = []
    for entry in CONTENT[kind]:
        keys += entry[2] if isinstance(entry, tuple) else [entry]
    return keys


def where_keys(kind: str) -> list[str]:
    return (["where"] if kind == "visualizer" else []) + WHERE


def player_choices(current: str) -> list[dict]:
    values = ["", *widgets.players()]
    if current and current not in values:
        values.append(current)
    return [{"value": v, "label": "Whatever plays" if not v else v.replace("_", " ").title()} for v in values]


def screen_choices(cfg: dict) -> list[dict]:
    """Laptop, every external, all, then each known external screen by its id."""
    choices = [{"value": "laptop", "label": "Laptop screen"}, {"value": "external", "label": "All external screens"},
               {"value": "all", "label": "All screens"}]
    for sid, screen in sorted(cfg["screens"].items(), key=lambda item: item[1].get("name", "")):
        if not screen.get("internal"):
            choices.append({"value": sid, "label": screen.get("name", sid)})
    return choices


def field(kind: str, key: str, group: str, cfg: dict, widget: dict) -> dict:
    default = widgets.DEFAULTS[kind].get(key)
    out = {"key": key, "group": group}
    if key == "player":
        out.update(type="choice", label="React to", choices=player_choices(widget.get("player", "")),
                   dynamic=True, default="")
    elif key == "screens":
        out.update(type="choice", label="Screens", choices=screen_choices(cfg), dynamic=True, default="all")
    elif key == "desktops":
        out.update(type="multi", label="Desktops", default=["all"],
                   choices=[{"value": v, "label": "Fixed screen" if v == "fixed" else v} for v in DESKTOP_VALUES],
                   hint="None picked: on every desktop.")
    elif key == "zone2":
        out.update(type="text", format="timezone", label="Second time zone", default="")
    elif key == "date_pattern":
        out.update(type="text", label="Own pattern, e.g. dd.MM.yyyy or dddd d MMMM", maxLength=DATE_PATTERN_MAX,
                   default="", showIf={"date_format": "custom"})
    elif key in widgets.CHOICES[kind]:
        out.update(type="choice", label=CHOICE_TITLES[key], default=default,
                   choices=[{"value": v, "label": CHOICE_LABELS[key][v]} for v in widgets.CHOICES[kind][key]])
    elif key in NUMBERS:
        title, step, unit = NUMBERS[key]
        low, high = widgets.RANGES[key]
        out.update(type="number", label=title, min=low, max=high, step=step, unit=unit.strip(), default=default)
    else:
        out.update(type="toggle", label=SWITCH_TITLES[key], default=bool(default))
    if key in HINTS:
        out["hint"] = HINTS[key]
    return out


def schema(kind: str, cfg: dict, widget: dict) -> list[dict]:
    fields = []
    for entry in CONTENT[kind]:
        if isinstance(entry, tuple):
            section, switch, keys = entry
            for key in keys:
                item = field(kind, key, "content", cfg, widget)
                item["section"] = section
                if switch and key != switch:
                    item["enabledBy"] = switch
                fields.append(item)
        else:
            fields.append(field(kind, entry, "content", cfg, widget))
    return fields + [field(kind, key, "where", cfg, widget) for key in where_keys(kind)]


# --- the real config <-> what the window sees ----------------------------------------


def screens_value(widget: dict) -> str:
    monitors = widget.get("monitors") or {}
    if monitors.get("mode") == "screen" and monitors.get("screen"):
        return str(monitors["screen"])
    return monitors.get("mode") if monitors.get("mode") in SCREEN_MODES else "all"


def desktops_value(widget: dict) -> list[str]:
    chosen = widget.get("desktops") or []
    if not chosen:
        return ["all"]
    return ["fixed" if d == widgets.FIXED_DESKTOP else str(d) for d in chosen]


def view(kind: str, widget: dict, cfg: dict) -> dict:
    where = {}
    for key in where_keys(kind):
        if key == "screens":
            where[key] = screens_value(widget)
        elif key == "desktops":
            where[key] = desktops_value(widget)
        else:
            where[key] = widget[key]
    return {
        "kind": kind,
        "name": TITLES[kind],
        "description": DESCRIPTIONS[kind],
        "enabled": bool(widget["enabled"]),
        "placed": bool(widget.get("placed")),
        "onDesktop": widgets.on_desktop(widget, kind),
        "missing": ["cava"] if kind == "visualizer" and not widgets.has_cava() else [],
        "content": {key: widget[key] for key in content_keys(kind)},
        "where": where,
        "schema": schema(kind, cfg, widget),
    }


class Invalid(ValueError):
    pass


def check(kind: str, group: str, key: str, value: object, cfg: dict) -> tuple[str, object]:
    """(config key, config value) for one change, or Invalid."""
    allowed = content_keys(kind) if group == "content" else where_keys(kind)
    if key not in allowed:
        raise Invalid(f"{kind} has no {group} setting {key!r}")
    if key == "screens":
        if value in SCREEN_MODES:
            return "monitors", {"mode": value, "screen": ""}
        screen = cfg["screens"].get(value) if isinstance(value, str) else None
        if screen is None or screen.get("internal"):
            raise Invalid(f"screens must be laptop, external, all or a known external screen id, not {value!r}")
        return "monitors", {"mode": "screen", "screen": value}
    if key == "desktops":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise Invalid("desktops must be a list like [\"all\"] or [\"1\", \"fixed\"]")
        if not value or value == ["all"]:
            return "desktops", []
        if "all" in value or any(v not in DESKTOP_VALUES for v in value):
            raise Invalid(f"desktops must be [\"all\"] or a list of {DESKTOP_VALUES}")
        return "desktops", sorted({widgets.FIXED_DESKTOP if v == "fixed" else int(v) for v in value})
    if key == "player":
        if not isinstance(value, str) or (value and not widgets.PLAYER_KEY.match(value)):
            raise Invalid("player must be \"\" or a media player's name like \"spotify\"")
        return key, value
    if key == "zone2":
        if not isinstance(value, str) or (value and value not in widgets.time_zones()):
            raise Invalid(f"unknown time zone: {value!r}")
        return key, value
    if key == "date_pattern":
        if not isinstance(value, str) or len(value) > DATE_PATTERN_MAX:
            raise Invalid(f"date_pattern must be text of at most {DATE_PATTERN_MAX} characters")
        return key, value
    if key in widgets.CHOICES[kind]:
        if value not in widgets.CHOICES[kind][key]:
            raise Invalid(f"{key} must be one of {widgets.CHOICES[kind][key]}")
        return key, value
    if key in NUMBERS:
        low, high = widgets.RANGES[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise Invalid(f"{key} must be a number from {low} to {high}")
        return key, int(round(value))
    if not isinstance(value, bool):
        raise Invalid(f"{key} must be true or false")
    return key, value


def known_kind(kind: object) -> bool:
    return kind in widgets.KINDS

