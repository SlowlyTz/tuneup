"""A Hyprland that behaves like the real one where hypr-screens depends on it:
monitor rules (the config's catch-all plus rules set at runtime, which a
reload drops), the arrangement of src/state/MonitorPositionController.cpp,
workspaces that move off a removed monitor, workspace rules, binds, options
and the socket2 events. It answers `hypr.hyprctl(*args)`.

Outputs are plugged and unplugged with plug()/unplug(); `events` collects
the event lines a watcher would read.
"""
import json
import re
from dataclasses import dataclass, field

CATCH_ALL = {"mode": "preferred", "position": "auto", "scale": 1.0, "transform": 0}
AUTO_DIRS = {"auto": "right", "auto-right": "right", "auto-left": "left", "auto-up": "up", "auto-down": "down"}


@dataclass
class Output:
    """A screen that can be plugged in: its EDID and modes (preferred first)."""
    name: str
    make: str
    model: str
    serial: str = ""
    modes: list = field(default_factory=lambda: [(1920, 1080, 60.0)])
    auto_scale: float = 1.0

    def edid(self) -> dict:
        return {"make": self.make, "model": self.model, "serial": self.serial,
                "description": f"{self.make} {self.model} {self.serial}".strip()}


def laptop_output() -> Output:
    return Output("eDP-1", "Samsung Display Corp.", "0x4159", "", [(1920, 1080, 60.0), (1280, 720, 60.0)])


def hp_output(name: str = "DP-3") -> Output:
    return Output(name, "HP Inc.", "HP 32f", "3CM1230QVW", [(1920, 1080, 60.0), (1280, 720, 60.0)])


def tv_output(name: str = "HDMI-A-1") -> Output:
    return Output(name, "LG Electronics", "LG TV SSCR2", "0x01010101",
                  [(3840, 2160, 60.0), (1920, 1080, 60.0)], auto_scale=2.0)


def fujitsu_output(name: str = "DP-5") -> Output:
    return Output(name, "Fujitsu Siemens Computers GmbH", "B27-9 TS QHD", "YVEB021757",
                  [(2560, 1440, 59.95), (1920, 1080, 60.0)], auto_scale=1.25)


def lua_fields(table: str) -> dict:
    """{ a = "x", b = 1.5, c = true } -> {"a": "x", "b": 1.5, "c": True} (flat tables only)."""
    found = {}
    for key, value in re.findall(r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|[-\w.]+)', table):
        if value.startswith('"'):
            found[key] = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        elif value in ("true", "false"):
            found[key] = value == "true"
        else:
            try:
                found[key] = float(value) if "." in value else int(value)
            except ValueError:
                found[key] = value
    return found


class HyprlandModel:
    def __init__(self, *outputs: Output):
        self.monitors: list[dict] = []
        self.runtime_rules: dict[str, dict] = {}
        self.workspace_rules: dict[int, str] = {}
        self.workspaces: dict[int, str | None] = {}   # id -> monitor name
        self.clients: list[dict] = []
        self.static_binds: list[dict] = []
        self.binds: list[dict] = []
        self.static_options: dict[str, object] = {}
        self.options: dict[str, object] = {}
        self.events: list[str] = []
        self.calls: list[tuple] = []
        self.reloads = 0
        self.next_id = 0
        self.on_eval = None   # a test's hook: called with each eval, before it runs
        for output in outputs:
            self.plug(output)
        self.events.clear()

    # --- the screens --------------------------------------------------------------------

    def rule_for(self, name: str) -> dict:
        return {**CATCH_ALL, **self.runtime_rules.get(name, {})}

    def monitor(self, name: str) -> dict | None:
        return next((m for m in self.monitors if m["name"] == name), None)

    def plug(self, output: Output) -> dict:
        monitor = {"id": self.next_id, "name": output.name, **output.edid(), "output": output,
                   "focused": not self.monitors, "disabled": False, "x": 0, "y": 0,
                   "activeWorkspace": {"id": 0, "name": ""},
                   "specialWorkspace": {"id": 0, "name": ""}, "dpmsStatus": True, "reserved": [0, 0, 0, 0],
                   "availableModes": [f"{w}x{h}@{r:.2f}Hz" for w, h, r in output.modes]}
        self.next_id += 1
        self.monitors.append(monitor)
        self.take_rule(monitor)
        self.arrange()
        wanted = next((ws for ws, name in sorted(self.workspace_rules.items())
                       if name == output.name and self.workspaces.get(ws) is None), None)
        self.show(monitor, wanted if wanted is not None else self.free_workspace(output.name))
        self.events += [f"monitoradded>>{output.name}", f"monitoraddedv2>>{monitor['id']},{output.name},x"]
        return monitor

    def unplug(self, name: str) -> None:
        monitor = self.monitor(name)
        self.monitors.remove(monitor)
        backup = self.focused() or (self.monitors[0] if self.monitors else None)
        if backup is not None and not backup["focused"]:
            backup["focused"] = True
        for ws, owner in list(self.workspaces.items()):
            if owner == name:
                self.workspaces[ws] = backup["name"] if backup else None
        self.arrange()
        self.events += [f"monitorremoved>>{name}", f"monitorremovedv2>>{monitor['id']},{name},x"]

    def close_lid(self, name: str = "eDP-1", closed: bool = True) -> None:
        """What Omarchy does on the lid switch: a rule that disables (or enables) the panel."""
        monitor = self.monitor(name)
        self.runtime_rules[name] = {**self.runtime_rules.get(name, {}), "disabled": closed}
        self.take_rule(monitor)
        if closed:
            others = [m for m in self.monitors if not m["disabled"]]
            for ws, owner in list(self.workspaces.items()):
                if owner == name and others:
                    self.workspaces[ws] = others[0]["name"]
            if monitor["focused"] and others:
                self.focus_monitor(others[0])
            self.events += [f"monitorremoved>>{name}", f"monitorremovedv2>>{monitor['id']},{name},x"]
        else:
            self.show(monitor, self.free_workspace(name))
            self.events += [f"monitoradded>>{name}", f"monitoraddedv2>>{monitor['id']},{name},x"]
        self.arrange()

    def take_rule(self, monitor: dict) -> None:
        rule = self.rule_for(monitor["name"])
        if rule.get("disabled"):
            monitor["disabled"] = True
            return
        monitor["disabled"] = False
        output = monitor["output"]
        width, height, rate = self.pick_mode(output, str(rule["mode"]))
        monitor.update(width=width, height=height, refreshRate=rate,
                       scale=output.auto_scale if rule["scale"] == "auto" else float(rule["scale"]),
                       transform=int(rule["transform"]))

    @staticmethod
    def pick_mode(output: Output, mode: str) -> tuple:
        size = re.match(r"(\d+)x(\d+)(?:@([\d.]+))?$", mode)
        if size is None:
            return output.modes[0]
        width, height = int(size.group(1)), int(size.group(2))
        same = [m for m in output.modes if (m[0], m[1]) == (width, height)]
        if not same:
            return output.modes[0]
        rate = float(size.group(3) or same[0][2])
        return min(same, key=lambda m: abs(m[2] - rate))

    @staticmethod
    def logical(monitor: dict) -> tuple[int, int]:
        width, height = round(monitor["width"] / monitor["scale"]), round(monitor["height"] / monitor["scale"])
        return (height, width) if monitor["transform"] % 2 else (width, height)

    def arrange(self) -> None:
        """Hyprland's arrange(): explicit positions first, then the auto ones in order."""
        enabled = [m for m in self.monitors if not m["disabled"]]
        arranged, auto = [], []
        for monitor in enabled:
            position = str(self.rule_for(monitor["name"])["position"])
            place = re.match(r"(-?\d+)x(-?\d+)$", position)
            if place:
                monitor["x"], monitor["y"] = int(place.group(1)), int(place.group(2))
                arranged.append(monitor)
            else:
                auto.append((monitor, AUTO_DIRS.get(position, "right")))
        for monitor, direction in auto:
            right = max([m["x"] + self.logical(m)[0] for m in arranged] + [0])
            left = min([m["x"] for m in arranged] + [0])
            down = max([m["y"] + self.logical(m)[1] for m in arranged] + [0])
            up = min([m["y"] for m in arranged] + [0])
            width, height = self.logical(monitor)
            monitor["x"], monitor["y"] = {"right": (right, 0), "left": (left - width, 0),
                                          "up": (0, up - height), "down": (0, down)}[direction]
            arranged.append(monitor)

    # --- workspaces ---------------------------------------------------------------------

    def focused(self) -> dict | None:
        return next((m for m in self.monitors if m["focused"]), None)

    def free_workspace(self, monitor: str = "") -> int:
        """The lowest id that is not taken nor bound to another monitor by a rule."""
        ws = 1
        while ws in self.workspaces or self.workspace_rules.get(ws, monitor) != monitor:
            ws += 1
        return ws

    def windows_on(self, ws: int) -> int:
        return sum(1 for c in self.clients if c["workspace"]["id"] == ws)

    def show(self, monitor: dict, ws: int) -> None:
        old = monitor["activeWorkspace"]["id"]
        self.workspaces[ws] = monitor["name"]
        monitor["activeWorkspace"] = {"id": ws, "name": str(ws)}
        if old and old != ws and self.workspaces.get(old) == monitor["name"] and not self.windows_on(old):
            del self.workspaces[old]  # an empty workspace out of sight is gone

    def focus_monitor(self, monitor: dict) -> None:
        for other in self.monitors:
            other["focused"] = other is monitor

    def focus_workspace(self, ws: int) -> None:
        owner = self.monitor(self.workspaces.get(ws) or "")
        if owner is None:
            ruled = self.monitor(self.workspace_rules.get(ws, ""))
            owner = ruled or self.focused()
        if owner is None:
            return
        self.focus_monitor(owner)
        self.show(owner, ws)

    def move_workspace(self, ws: int, target: dict) -> None:
        """Like CCompositor::moveWorkspaceToMonitor: the old monitor gets another
        workspace if this was its active one; the target shows it only if it
        was active on the focused monitor."""
        source = self.monitor(self.workspaces.get(ws) or "")
        if ws not in self.workspaces or source is target:
            return
        was_active = source is not None and source["activeWorkspace"]["id"] == ws
        self.workspaces[ws] = target["name"]
        if was_active:
            rest = sorted(w for w, name in self.workspaces.items() if name == source["name"])
            replacement = rest[0] if rest else self.free_workspace(source["name"])
            self.workspaces[replacement] = source["name"]
            source["activeWorkspace"] = {"id": replacement, "name": str(replacement)}
        if was_active and source["focused"]:
            self.show(target, ws)
        elif not self.windows_on(ws):
            del self.workspaces[ws]  # hidden and empty: Hyprland drops it
        self.events.append(f"moveworkspacev2>>{ws},{ws},{target['name']}")

    def visible(self) -> dict[str, int]:
        return {m["name"]: m["activeWorkspace"]["id"] for m in self.monitors if not m["disabled"]}

    # --- hyprctl ------------------------------------------------------------------------

    def __call__(self, *args):
        self.calls.append(args)
        if args[:1] == ("-j",):
            return json.dumps(self.query(*args[1:]))
        if args == ("reload",):
            self.reload()
            return "ok"
        if args == ("cursorpos",):
            return "100, 200"
        if args[0] == "eval":
            if self.on_eval:
                self.on_eval(args[1])
            for line in args[1].splitlines():
                self.evaluate(line.strip())
            return "ok"
        if args[0] == "dispatch":
            self.dispatch(args[1])
            return "ok"
        return "ok"

    def query(self, what: str, *rest: str) -> object:
        if what == "monitors":
            shown = self.monitors if rest == ("all",) else [m for m in self.monitors if not m["disabled"]]
            return [{k: v for k, v in m.items() if k != "output"} for m in shown]
        if what == "workspaces":
            return [{"id": ws, "name": str(ws), "monitor": name or "", "windows": self.windows_on(ws)}
                    for ws, name in sorted(self.workspaces.items())]
        if what == "workspacerules":
            return [{"workspaceString": str(ws), "monitor": name} for ws, name in sorted(self.workspace_rules.items())]
        if what == "clients":
            return self.clients
        if what == "binds":
            return self.binds
        if what == "activewindow":
            return {}
        if what == "getoption":
            value = self.options.get(rest[0], 0)
            if isinstance(value, bool):
                return {"option": rest[0], "int": int(value)}
            if isinstance(value, float):
                return {"option": rest[0], "float": value}
            if isinstance(value, str):
                return {"option": rest[0], "custom": value}
            return {"option": rest[0], "int": value}
        return []

    def reload(self) -> None:
        self.reloads += 1
        self.runtime_rules.clear()
        self.workspace_rules.clear()
        self.binds = [dict(b) for b in self.static_binds]
        self.options = dict(self.static_options)
        for monitor in self.monitors:
            self.take_rule(monitor)
        self.arrange()
        self.events.append("configreloaded>>")

    def evaluate(self, line: str) -> None:
        if line.startswith("hl.monitor("):
            fields = lua_fields(line)
            name = fields.pop("output")
            self.runtime_rules[name] = fields
            monitor = self.monitor(name)
            if monitor is not None:
                self.take_rule(monitor)
                self.arrange()
        elif line.startswith("hl.workspace_rule("):
            fields = lua_fields(line)
            self.workspace_rules[int(fields["workspace"])] = fields["monitor"]
        elif line.startswith("hl.unbind("):
            combo = re.search(r'hl\.unbind\("([^"]+)"\)', line).group(1)
            self.binds = [b for b in self.binds if b.get("combo") != combo]
        elif line.startswith("hl.bind("):
            combo = re.search(r'hl\.bind\("([^"]+)"', line).group(1)
            description = re.search(r'description = "([^"]*)"', line)
            self.binds = [b for b in self.binds if b.get("combo") != combo]
            self.binds.append(self.bind(combo, description.group(1) if description else ""))
        elif line.startswith("hl.config("):
            self.set_options(line)

    def set_options(self, line: str) -> None:
        for path, value in (("general:gaps_in", r"gaps_in = (\d+)"), ("general:gaps_out", r"gaps_out = (\d+)"),
                            ("decoration:rounding", r"rounding = (\d+)"),
                            ("general:border_size", r"border_size = (\d+)")):
            found = re.search(value, line)
            if found:
                self.options[path] = int(found.group(1))

    @staticmethod
    def bind(combo: str, description: str) -> dict:
        from hypr_screens import keybinds

        mask, key = keybinds.parse(combo)
        # Like Hyprland 0.56: a `code:` bind is listed with neither key nor keycode.
        return {"combo": combo, "modmask": mask, "submap": "", "description": description,
                "key": "" if key.lower().startswith("code:") else key, "keycode": 0}

    def dispatch(self, expression: str) -> None:
        fields = lua_fields(expression)
        if expression.startswith("hl.dsp.workspace.move("):
            target = self.monitor(fields["monitor"])
            if target is not None:
                self.move_workspace(int(fields["workspace"]), target)
        elif expression.startswith("hl.dsp.focus("):
            if "monitor" in fields and self.monitor(fields["monitor"]):
                self.focus_monitor(self.monitor(fields["monitor"]))
            elif "workspace" in fields:
                self.focus_workspace(int(fields["workspace"]))
        elif expression.startswith("hl.dsp.window.move("):
            address = str(fields.get("window", "")).removeprefix("address:")
            for client in self.clients:
                if client["address"] == address and "workspace" in fields:
                    ws = int(fields["workspace"])
                    client["workspace"] = {"id": ws, "name": str(ws)}
                    if ws not in self.workspaces:
                        self.workspaces[ws] = (self.focused() or {}).get("name")
        elif expression.startswith("hl.dsp.workspace.swap_monitors("):
            first, second = self.monitor(fields["monitor1"]), self.monitor(fields["monitor2"])
            a, b = first["activeWorkspace"]["id"], second["activeWorkspace"]["id"]
            for ws, name in list(self.workspaces.items()):
                if name == first["name"]:
                    self.workspaces[ws] = second["name"]
                elif name == second["name"]:
                    self.workspaces[ws] = first["name"]
            first["activeWorkspace"], second["activeWorkspace"] = {"id": b, "name": str(b)}, {"id": a, "name": str(a)}

    # --- for the checks -----------------------------------------------------------------

    def box(self, name: str) -> tuple[int, int, int, int]:
        monitor = self.monitor(name)
        width, height = self.logical(monitor)
        return monitor["x"], monitor["y"], monitor["x"] + width, monitor["y"] + height

    def touching(self, first: str, second: str) -> bool:
        """Whether two monitors share a stretch of edge, not just a corner."""
        (ax, ay, ax2, ay2), (bx, by, bx2, by2) = self.box(first), self.box(second)
        side = (ax2 == bx or bx2 == ax) and min(ay2, by2) - max(ay, by) > 0
        top = (ay2 == by or by2 == ay) and min(ax2, bx2) - max(ax, bx) > 0
        return side or top

    def overlapping(self) -> bool:
        names = [m["name"] for m in self.monitors if not m["disabled"]]
        for index, first in enumerate(names):
            for second in names[index + 1:]:
                (ax, ay, ax2, ay2), (bx, by, bx2, by2) = self.box(first), self.box(second)
                if min(ax2, bx2) > max(ax, bx) and min(ay2, by2) > max(ay, by):
                    return True
        return False
