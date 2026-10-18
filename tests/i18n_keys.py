"""Every text the settings window passes through i18n.t(), found in the code."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "hypr_screens"


def literal_keys() -> set[str]:
    """First arguments of t("...") calls that are plain strings."""
    keys = set()
    for path in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(), str(path))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t"
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                keys.add(node.args[0].value)
    return keys


# t("...") in the HTML settings window (hypr_screens/web/app.js): a double-quoted
# string literal as the first argument. Anything else passed to t() is a text
# the backend sends (already an English source text, translated elsewhere).
WEB_APP = ROOT / "web" / "app.js"
WEB_CALL = re.compile(r'(?<![\w.$])t\(\s*"((?:[^"\\\n]|\\.)*)"')


def web_keys() -> set[str]:
    """Texts of the HTML settings window."""
    if not WEB_APP.exists():
        return set()
    return {json.loads(f'"{text}"') for text in WEB_CALL.findall(WEB_APP.read_text(encoding="utf-8"))}


def table_keys() -> set[str]:
    """Texts kept in tables: the backend sends them to the page (or the widgets),
    which translates them through t(variable)."""
    from hypr_screens import api, look, samsung, sound, widget_schema, widgets

    keys = set(api.ACTION_TITLES.values()) | set(api.ACTION_HELP.values()) | set(api.DEFAULT_FIXED_LABELS.values())
    keys |= set(sound.PORT_LABELS.values())
    keys |= {label for _mode, label, _cpu in samsung.MODES} | set(samsung.ATTRIBUTES.values())
    keys |= set(look.PRESETS)
    keys |= set(widgets.TITLES.values())
    for group, parts in [*(g for groups in widgets.PARTS.values() for g in groups), widgets.LOOK_PARTS]:
        keys |= {group} | {title for _part, title, _default in parts}
    for name in ("CHOICE_TITLES", "SWITCH_TITLES", "HINTS", "DESCRIPTIONS"):
        keys |= set(getattr(widget_schema, name).values())
    keys |= {text for labels in widget_schema.CHOICE_LABELS.values() for text in labels.values()}
    keys |= {title for title, _step, _unit in widget_schema.NUMBERS.values()}
    keys |= {entry[0] for entries in widget_schema.CONTENT.values() for entry in entries if isinstance(entry, tuple)}
    return keys | schema_inline_keys()


def schema_inline_keys() -> set[str]:
    """Labels and hints written inline in widget_schema.py (label=..., "label": ...)."""
    keys = set()
    for node in ast.walk(ast.parse((ROOT / "widget_schema.py").read_text())):
        values = []
        if isinstance(node, ast.keyword) and node.arg in ("label", "hint"):
            values.append(node.value)
        if isinstance(node, ast.Dict):
            values += [v for k, v in zip(node.keys, node.values)
                       if isinstance(k, ast.Constant) and k.value in ("label", "hint")]
        for value in values:
            choices = [value.body, value.orelse] if isinstance(value, ast.IfExp) else [value]
            keys |= {c.value for c in choices if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return keys


def all_keys() -> set[str]:
    return literal_keys() | table_keys() | web_keys()
