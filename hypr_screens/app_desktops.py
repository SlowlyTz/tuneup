"""App to desktop: chosen apps always start on their own desktop.

Each scratch desktop (1-10) and each of the desktops 1-10 (Tuneup's normal
desktops, wherever they are -- on the laptop with the external screen fixed)
can have up to MAX_APPS apps. A new window of such an app goes to that desktop
in silence (the focus stays), tiled or floating as chosen, and is kept there
for GUARD_TICKS * TICK_MS (5 s) after it opened; after that it may be moved
like any other window. A window that lands where nobody looks -- a closed
scratch row, a desktop not shown -- is announced by Omarchy's own OSD (the
rocket of its app launch).

The apps are desktop entries; their windows are found by class: the entry's
StartupWMClass, a Chromium/Helium web app's chrome-<app id>-<profile> (the class
such a window really gets, a moment after it opened), and the entry's own name.

All of it runs in Hyprland's Lua (module_lua(), part of the generated file,
safe to evaluate again: the rules and handlers are replaced).
"""
import base64
import functools
import os
import re
import shlex
import subprocess
from pathlib import Path

from hypr_screens import blocks, desktops, hypr, scratch

MAX_APPS = 5
DESKTOPS = 10
GROUPS = ("scratch", "desk")
MODES = ("tile", "float")
GUARD_TICKS, TICK_MS = 25, 200  # kept on its desktop for 5 s
OPEN_MS = GUARD_TICKS * TICK_MS
FLOAT_SIZE = (1100, 820)  # as the web app flyouts
ROCKET = "\U000f14de"  # the icon of Omarchy's app launch OSD
OSD_MS = 2000
ICON_MAX_BYTES = 96 * 1024
ICON_SIZES = ("scalable", "128x128", "96x96", "64x64", "48x48", "256x256", "512x512", "32x32")
CHROMIUM_APP = re.compile(r"--app-id=([a-p]{32})")
PROFILE = re.compile(r"--profile-directory=(\S+)")
# Programs that only start another one: their name is not the window's class.
LAUNCHERS = {"env", "sh", "bash", "flatpak", "uwsm", "uwsm-app", "gtk-launch", "omarchy-launch-webapp"}


def desktop_keys() -> list[str]:
    return [f"{group}:{n}" for group in GROUPS for n in range(1, DESKTOPS + 1)]


def parse_key(key: str) -> tuple[str, int] | None:
    group, _, number = str(key).partition(":")
    if group in GROUPS and number.isdigit() and 1 <= int(number) <= DESKTOPS:
        return group, int(number)
    return None


def normalize(raw: object) -> dict:
    """{desktop key: [{id, name, classes, mode}]}: valid desktops, at most
    MAX_APPS each, every app on one desktop only (the first one keeps it)."""
    found: dict[str, list[dict]] = {}
    if not isinstance(raw, dict):
        return found
    seen: set[str] = set()
    for key in desktop_keys():
        apps = []
        for app in raw.get(key) if isinstance(raw.get(key), list) else []:
            if not isinstance(app, dict):
                continue
            app_id = str(app.get("id") or "").strip()[:200]
            classes = [str(c).strip().lower()[:200] for c in app.get("classes") or [] if str(c).strip()]
            if not app_id or not classes or app_id in seen or len(apps) >= MAX_APPS:
                continue
            seen.add(app_id)
            apps.append({"id": app_id, "name": str(app.get("name") or app_id)[:120],
                         "classes": list(dict.fromkeys(classes))[:6],
                         "mode": app.get("mode") if app.get("mode") in MODES else "tile"})
        if apps:
            found[key] = apps
    return found


# --- desktop entries ---------------------------------------------------------------------


def data_dirs() -> list[Path]:
    home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    dirs = [home, *(os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")]
    return [Path(d) for d in dict.fromkeys(dirs) if d]


def read_entry(path: Path) -> dict[str, str]:
    entry: dict[str, str] = {}
    inside = False
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return entry
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            inside = line == "[Desktop Entry]"
        elif inside and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            entry.setdefault(key.strip(), value.strip())
    return entry


def classes_of(app_id: str, entry: dict[str, str]) -> list[str]:
    """The window classes this entry's windows (may) have, lower case."""
    found = []
    wm_class = entry.get("StartupWMClass", "")
    exec_line = entry.get("Exec", "")
    web_app = CHROMIUM_APP.search(exec_line)
    if web_app:
        profile = PROFILE.search(exec_line)
        found.append(f"chrome-{web_app.group(1)}-{profile.group(1) if profile else 'Default'}")
    if wm_class:
        found.append(wm_class)
    found.append(app_id)
    try:
        program = shlex.split(exec_line)[0] if exec_line else ""
    except ValueError:
        program = exec_line.split(" ")[0]
    if program and not web_app and os.path.basename(program) not in LAUNCHERS:
        found.append(os.path.basename(program))
    return list(dict.fromkeys(c.lower() for c in found if c))


def entries(language: str = "en") -> dict[str, dict]:
    """Every app of the launcher: {desktop id: {id, name, icon, classes}};
    a user's entry hides the system's of the same id."""
    apps: dict[str, dict] = {}
    for base in data_dirs():
        folder = base / "applications"
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.desktop")):
            app_id = str(path.relative_to(folder))[:-len(".desktop")].replace("/", "-")
            if app_id in apps:
                continue
            entry = read_entry(path)
            apps[app_id] = {}
            if (entry.get("Type", "Application") != "Application" or entry.get("NoDisplay") == "true"
                    or entry.get("Hidden") == "true" or entry.get("Terminal") == "true" or not entry.get("Name")):
                continue
            apps[app_id] = {"id": app_id, "name": entry.get(f"Name[{language}]") or entry["Name"],
                            "iconName": entry.get("Icon", ""), "classes": classes_of(app_id, entry)}
    return {key: app for key, app in apps.items() if app}


@functools.lru_cache(maxsize=1)
def icon_theme() -> str:
    try:
        done = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"],
                              capture_output=True, text=True, timeout=2)
        return done.stdout.strip().strip("'\"")
    except (OSError, subprocess.SubprocessError):
        return ""


@functools.lru_cache(maxsize=512)
def icon_path(name: str) -> str | None:
    if not name:
        return None
    if name.startswith("/"):
        return name if Path(name).is_file() else None
    themes = [t for t in (icon_theme(), "hicolor") if t]
    for base in [Path.home() / ".icons", *(d / "icons" for d in data_dirs())]:
        for theme in themes:
            for size in ICON_SIZES:
                for ext in ("svg", "png"):
                    path = base / theme / size / "apps" / f"{name}.{ext}"
                    if path.is_file():
                        return str(path)
    for ext in ("svg", "png", "xpm"):
        path = Path("/usr/share/pixmaps") / f"{name}.{ext}"
        if path.is_file() and ext != "xpm":
            return str(path)
    return None


@functools.lru_cache(maxsize=512)
def icon_data(name: str) -> str | None:
    """The app's icon as a data: URL (the page cannot read files), small ones only."""
    path = icon_path(name)
    if not path:
        return None
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if len(data) > ICON_MAX_BYTES:
        return None
    kind = "image/svg+xml" if path.endswith(".svg") else "image/png"
    return f"data:{kind};base64," + base64.b64encode(data).decode("ascii")


def view_app(app: dict, icon_name: str = "") -> dict:
    return {**{k: app[k] for k in ("id", "name", "classes") if k in app},
            **({"mode": app["mode"]} if "mode" in app else {}), "icon": icon_data(icon_name)}


# --- Hyprland ---------------------------------------------------------------------------


def osd_command(name: str) -> str:
    osd = blocks.omarchy_path() / "bin" / "omarchy-osd"
    program = str(osd) if osd.is_file() else "omarchy-osd"
    return " ".join(shlex.quote(part) for part in (program, "-i", ROCKET, "-m", name, "-d", str(OSD_MS)))


def rules(cfg: dict) -> list[dict]:
    """The apps that go somewhere now (scratch ones only with the scratch desktops on)."""
    found = []
    for key, apps in normalize(cfg.get("app_desktops")).items():
        group, number = parse_key(key)
        if group == "scratch" and not scratch.enabled(cfg):
            continue
        found += [{**app, "group": group, "n": number} for app in apps]
    return found


def lua_rule(rule: dict) -> str:
    classes = ", ".join(hypr.lua_string(c) for c in rule["classes"])
    return (f"    {{ key = {hypr.lua_string(rule['id'])}, classes = {{ {classes} }}, "
            f"scratch = {'true' if rule['group'] == 'scratch' else 'false'}, n = {rule['n']}, "
            f"float = {'true' if rule['mode'] == 'float' else 'false'}, "
            f"osd = {hypr.lua_string(osd_command(rule['name']))} }},")


def module_lua(cfg: dict) -> str:
    lines = [
        "-- App to desktop (see hypr_screens/app_desktops.py): these apps start on their",
        "-- own desktop, in silence, and are kept there for 5 s after they opened.",
        "do",
        "  local RULES = {",
        *[lua_rule(rule) for rule in rules(cfg)],
        "  }",
        f"  local layout_file = {hypr.lua_string(str(desktops.layout_file()))}",
        f"  local first_scratch, park_from = {scratch.FIRST}, {desktops.PARK_FROM}",
        f"  local TICKS, TICK_MS, OPEN_MS = {GUARD_TICKS}, {TICK_MS}, {OPEN_MS}",
        f"  local WIDTH, HEIGHT = {FLOAT_SIZE[0]}, {FLOAT_SIZE[1]}",
        "  local A = _G.tuneup_apps_state or {}",
        "  _G.tuneup_apps_state = A",
        "  A.fresh, A.done, A.told = A.fresh or {}, A.done or {}, A.told or {}",
        "  local function after(ms, fn) hl.timer(fn, { timeout = ms, type = \"oneshot\" }) end",
        "",
        "  local function rule_of(window)",
        "    local class = string.lower(window.class or \"\")",
        "    if class == \"\" then return nil end",
        "    for _, rule in ipairs(RULES) do",
        "      for _, c in ipairs(rule.classes) do if c == class then return rule end end",
        "    end",
        "  end",
        "  -- Desktop n: its id now (the ids follow the screens, see desktops.py).",
        "  local function desk_first()",
        "    local file = io.open(layout_file, \"r\")",
        "    if not file then return 1 end",
        "    local text = file:read(\"a\") or \"\"",
        "    file:close()",
        "    return tonumber(text:match('\"desk_first\": *(%d+)')) or 1",
        "  end",
        "  local function is_scratch(ws) return ws ~= nil and not ws.special and ws.id >= first_scratch and ws.id < park_from end",
        "  local function row_open()",
        "    for _, monitor in ipairs(hl.get_monitors()) do",
        "      if is_scratch(monitor.active_workspace) then return true end",
        "    end",
        "    return false",
        "  end",
        "  -- A closed scratch row's desktops wait as special workspaces (scratch.py).",
        "  local function target_of(rule)",
        "    if rule.scratch then",
        "      local id = first_scratch + rule.n - 1",
        "      return row_open() and tostring(id) or \"special:tuneup-scratch-\" .. id",
        "    end",
        "    return tostring(desk_first() + rule.n - 1)",
        "  end",
        "  local function is_on(ws, name)",
        "    return ws ~= nil and (ws.name == name or (not ws.special and tostring(ws.id) == name))",
        "  end",
        "  local function shown(name)",
        "    for _, monitor in ipairs(hl.get_monitors()) do",
        "      if is_on(monitor.active_workspace, name) then return true end",
        "    end",
        "    return false",
        "  end",
        "  local function find(address)",
        "    for _, w in ipairs(hl.get_windows() or {}) do if w.address == address then return w end end",
        "  end",
        "  -- Floating: the size of the web app flyouts (smaller on a small screen), centred.",
        "  local function fit(target)",
        "    local width, height = WIDTH, HEIGHT",
        "    local monitor = hl.get_active_monitor()",
        "    if monitor and monitor.width and monitor.scale then",
        "      width = math.min(WIDTH, math.floor(monitor.width / monitor.scale * 0.9))",
        "      height = math.min(HEIGHT, math.floor(monitor.height / monitor.scale * 0.85))",
        "    end",
        "    hl.dispatch(hl.dsp.window.resize({ x = width, y = height, relative = false, window = target }))",
        "    hl.dispatch(hl.dsp.window.center({ window = target }))",
        "  end",
        "  -- Tiled or floating first: a change of that under a move loses the move.",
        "  -- A floating one is sized when it is placed first (it may float already)",
        "  -- and when it is floated again later.",
        "  local function place(window, rule, first)",
        "    local target = \"address:\" .. window.address",
        "    local size = first and rule.float",
        "    if (window.floating == true) ~= rule.float then",
        "      hl.dispatch(hl.dsp.window.float({ action = rule.float and \"on\" or \"off\", window = target }))",
        "      size = rule.float",
        "    end",
        "    local name = target_of(rule)",
        "    if not is_on(window.workspace, name) then",
        "      hl.dispatch(hl.dsp.window.move({ workspace = name, follow = false, window = target }))",
        "    end",
        "    if size then after(1, function() fit(target) end) end",
        "    return name",
        "  end",
        "  -- For 5 s the window is put back whenever it left its desktop.",
        "  local function guard(address, rule, left)",
        "    after(TICK_MS, function()",
        "      local window = find(address)",
        "      if not window then return end",
        "      place(window, rule)",
        "      if left > 1 then guard(address, rule, left - 1) end",
        "    end)",
        "  end",
        "  -- Chromium and Electron windows get their class a moment after they",
        "  -- opened: a window counts until OPEN_MS after it opened, once.",
        "  local function handle(window)",
        "    if not (window and window.address and A.fresh[window.address]) or A.done[window.address] then return end",
        "    local rule = rule_of(window)",
        "    if not rule then return end",
        "    A.done[window.address] = true",
        "    local name = place(window, rule, true)",
        "    if not shown(name) and not A.told[rule.key] then",
        "      A.told[rule.key] = true  -- one OSD per launch, not one per window",
        "      after(OPEN_MS, function() A.told[rule.key] = nil end)",
        "      hl.exec_cmd(rule.osd)",
        "    end",
        "    guard(window.address, rule, TICKS)",
        "  end",
        "  local function opened(window)",
        "    if not (window and window.address) then return end",
        "    local address = window.address",
        "    A.fresh[address] = true",
        "    after(OPEN_MS, function() A.fresh[address] = nil; A.done[address] = nil end)",
        "    handle(window)",
        "  end",
        "",
        "  for _, subscription in ipairs(_G.tuneup_apps_events or {}) do subscription:remove() end",
        "  _G.tuneup_apps_events = {}",
        "  if #RULES > 0 then",
        "    _G.tuneup_apps_events = { hl.on(\"window.open\", opened), hl.on(\"window.class\", handle) }",
        "  end",
        "end",
    ]
    return "\n".join(lines)
