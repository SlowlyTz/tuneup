"""Scratch desktops: Tuneup's stand-in for Omarchy's scratchpad.

A row of normal workspaces from FIRST (201) upward, shared by all screens.
SUPER + S on a screen flies the last used scratch desktop in from below (and
remembers what that screen showed); on a scratch desktop it flies back out.
Inside the row, SUPER + 1…0 / SHIFT + 1…0 go to / move the window to scratch
desktop 1…10, swiping moves sideways between them, and a swipe that would
leave the row (or enter it from a normal desktop) bounces back.
SUPER + ALT + S (and SUPER + SHIFT + S if it is free) moves the active window
to the last used scratch desktop.

All of it runs in Hyprland's Lua (module_lua(), part of the generated Lua
file, safe to evaluate again: event handlers are replaced, the state is
kept), so a key press costs no process. The animation is switched on the fly:
"slidevert" for flying in and out, the user's own workspace animation (read
from Hyprland when the file is written) at all other times -- also inside the
row, so SUPER+1…0 switch there just as they do outside it (Omarchy's: no
animation), while a swipe still follows the finger.
"""
import json

from hypr_screens import hypr, look

FIRST = 201
TOGGLE_LABEL = "Scratch desktops"
MOVE_LABEL = "Move window to scratch desktop"
TOGGLE_KEYS = ["SUPER + S"]
MOVE_KEYS = ["SUPER + ALT + S"]
SHIFT_S = "SUPER + SHIFT + S"
# What Omarchy itself puts on SUPER + SHIFT + S: taking it over loses nothing of the user's.
OMARCHY_SHIFT_S = {"Google Maps"}
# Omarchy's special workspace animation, the flight of the old scratchpad.
FLY = {"enabled": True, "speed": 3, "bezier": "easeOutQuint", "style": "slidevert"}
SLIDE = {**FLY, "style": "slide"}  # set inside the row by earlier versions
SETTLE_MS = 400
BOUNCE_MS = 60  # after a swipe has set its workspace
KEPT = 5  # scratch desktops that exist while the row is open, empty or not (config scratch_kept)  # a bit longer than the flight (speed 3 = 300 ms)
OMARCHY_SCRATCHPAD = "special:scratchpad"
# Closed, a scratch desktop's windows wait here, so a swipe on a normal
# desktop never reaches them (it walks the workspaces of its screen).
PARKED = "special:tuneup-scratch-"


def enabled(cfg: dict) -> bool:
    return bool(cfg.get("scratch", True))


def binds(cfg: dict) -> list[tuple[str, str, str]]:
    """(combo, Lua call, description) of the scratch keys (not the desktop keys)."""
    if not enabled(cfg):
        return []
    move = MOVE_KEYS + ([SHIFT_S] if cfg.get("scratch_shift_s") else [])
    return [(combo, "toggle()", TOGGLE_LABEL) for combo in TOGGLE_KEYS] + \
        [(combo, "move_window()", MOVE_LABEL) for combo in move]


def may_take_shift_s(others: list[str]) -> bool:
    """SUPER + SHIFT + S is free, or only Omarchy's own default sits there."""
    return set(others) <= OMARCHY_SHIFT_S


# --- the workspace animation to give back --------------------------------------------------


def lua_table(spec: dict) -> str:
    fields = ['leaf = "workspaces"', f"enabled = {'true' if spec.get('enabled') else 'false'}"]
    if spec.get("speed"):
        fields.append(f"speed = {spec['speed']:g}")
    for key in ("bezier", "style"):
        if spec.get(key):
            fields.append(f"{key} = {hypr.lua_string(spec[key])}")
    return "{ " + ", ".join(fields) + " }"


def ours(spec: dict) -> bool:
    """One of the animations the scratch desktops set themselves."""
    return {k: spec.get(k) for k in FLY} in (FLY, SLIDE)


def effective(animations: list[dict], name: str) -> dict | None:
    """An animation as Hyprland plays it: a leaf that is not set inherits from
    its parents (workspaces -> global)."""
    by_name = {a.get("name"): a for a in animations if isinstance(a, dict)}
    for candidate in (name, "global"):
        entry = by_name.get(candidate)
        if entry and entry.get("overridden"):
            return {"enabled": bool(entry.get("enabled")), "speed": float(entry.get("speed") or 0),
                    "bezier": str(entry.get("bezier") or ""), "style": str(entry.get("style") or "")}
    return None


def from_files() -> dict:
    """The workspaces animation as Omarchy's (and the user's) looknfeel.lua set it."""
    fields = next((f for f in look.animations() if f.get("leaf", "").strip('"') == "workspaces"), {})
    spec = {"enabled": fields.get("enabled", "false") == "true"}
    if "speed" in fields:
        try:
            spec["speed"] = float(fields["speed"])
        except ValueError:
            pass
    for key in ("bezier", "style"):
        if key in fields:
            spec[key] = fields[key].strip('"')
    return spec


def user_animation() -> dict:
    """What workspace switches look like outside the row: Hyprland's live value
    -- unless it is one of ours (the file is written while a screen is in the
    row), then the looknfeel files'."""
    try:
        live = json.loads(hypr.hyprctl("-j", "animations") or "null")
        spec = effective(live[0], "workspaces") if isinstance(live, list) and live else None
    except (json.JSONDecodeError, TypeError, IndexError):
        spec = None
    return spec if spec is not None and not ours(spec) else from_files()


# --- the Lua module -------------------------------------------------------------------------


MODULE = """\
-- Scratch desktops: workspaces {first} and up, shared by all screens (see
-- hypr_screens/scratch.py). Evaluating this again keeps the state and
-- replaces the event handlers.
do
  local first = {first}
  local S = _G.tuneup_scratch_state or {{ last = first, normal = {{}}, shown = {{}}, busy = 0, anim = "" }}
  _G.tuneup_scratch_state = S
  local animations = {{
    user = {user},
    fly = {fly},
  }}
  local M = {{}}

  local function is_scratch(ws) return ws ~= nil and not ws.special and ws.id >= first end
  local function after(ms, fn) hl.timer(fn, {{ timeout = ms, type = "oneshot" }}) end
  local function animate(name)
    if S.anim == name then return end
    S.anim = name
    hl.animation(animations[name])
  end
  -- Our own switch is under way (until it has settled): no bounce for it.
  local function ours()
    S.busy = S.busy + 1
    local mine = S.busy
    after({settle}, function() if S.busy == mine then S.busy = 0 end end)
  end
  -- After a flight: the user's own animation again, in the row too; a closed
  -- row's desktops are put away.
  local park
  local function settle()
    animate("user")
    park()
  end
  local function show(id)
    hl.dispatch(hl.dsp.focus({{ workspace = tostring(id), on_current_monitor = true }}))
  end
  local function workspaces_on(monitor)
    local found = {{}}
    for _, ws in ipairs(hl.get_workspaces()) do
      if not ws.special and ws.monitor and ws.monitor.name == monitor.name then table.insert(found, ws.id) end
    end
    return found
  end
  -- What a swipe does: to the next workspace of that screen, nothing in between.
  local function next_to(monitor, a, b)
    local low, high = math.min(a, b), math.max(a, b)
    for _, id in ipairs(workspaces_on(monitor)) do
      if id > low and id < high then return false end
    end
    return true
  end
  -- The row is one: all scratch desktops go to the screen that opens it, so a
  -- swipe there reaches each of them (a swipe only knows its own screen's).
  local function gather(monitor)
    for _, ws in ipairs(hl.get_workspaces()) do
      if is_scratch(ws) and ws.monitor and ws.monitor.name ~= monitor.name then
        hl.dispatch(hl.dsp.workspace.move({{ workspace = tostring(ws.id), monitor = monitor.name }}))
      end
    end
  end
  -- While no screen shows the row, its desktops wait in hidden special
  -- workspaces; opening it brings them back first.
  local function move_window(window, target)
    hl.dispatch(hl.dsp.window.move({{ workspace = target, follow = false, window = "address:" .. window.address }}))
  end
  -- Scratch desktops 1 to {kept} are always there while the row is open (never
  -- dropped when empty, so SUPER + 1…0 and the bar's numbers always match);
  -- the rule is lifted when the row closes, so they leave with it.
  local function keep(monitor)
    local on = monitor ~= nil
    local state = on and (monitor.name .. ":" .. {kept}) or false
    if S.kept == state then return end
    S.kept = state
    for i = 0, 9 do  -- all ten: a smaller count lifts the rule from the rest
      local rule = {{ workspace = tostring(first + i), persistent = on and i < {kept} }}
      if rule.persistent then rule.monitor = monitor.name end
      hl.workspace_rule(rule)
    end
  end
  local function row_open()
    for _, monitor in ipairs(hl.get_monitors()) do
      if is_scratch(monitor.active_workspace) then return true end
    end
    return false
  end
  park = function()
    if row_open() then return end
    keep(nil)
    for _, ws in ipairs(hl.get_workspaces()) do
      if is_scratch(ws) then
        for _, window in ipairs(hl.get_workspace_windows(ws) or {{}}) do move_window(window, "{parked}" .. ws.id) end
      end
    end
  end
  local function unpark()
    for _, ws in ipairs(hl.get_workspaces()) do
      local id = ws.special and tonumber((ws.name or ""):match("^{parked_pattern}(%d+)$"))
      if id then
        for _, window in ipairs(hl.get_workspace_windows(ws) or {{}}) do move_window(window, tostring(id)) end
      end
    end
  end
  local function normal_of(monitor)
    if S.normal[monitor.name] then return S.normal[monitor.name] end
    local lowest
    for _, id in ipairs(workspaces_on(monitor)) do
      if id < first and (lowest == nil or id < lowest) then lowest = id end
    end
    return lowest or 1
  end

  function M.toggle()
    local monitor = hl.get_active_monitor()
    if not monitor then return end
    local ws = monitor.active_workspace
    ours()
    animate("fly")
    if is_scratch(ws) then
      S.last = ws.id
      show(normal_of(monitor))
    else
      if ws and not ws.special then S.normal[monitor.name] = ws.id end
      keep(monitor)
      unpark()
      gather(monitor)
      show(S.last)
    end
    after({settle}, settle)
  end

  -- SUPER (+ SHIFT / + SHIFT + ALT) + digit: scratch desktop n inside the row,
  -- `otherwise` (a dispatcher) outside it.
  function M.digit(action, n, otherwise)
    local monitor = hl.get_active_monitor()
    if not (monitor and is_scratch(monitor.active_workspace)) then
      hl.dispatch(otherwise)
      return
    end
    local id = tostring(first + n - 1)
    if action ~= "switch" then
      hl.dispatch(hl.dsp.window.move({{ workspace = id, follow = false }}))
    end
    if action ~= "move-silent" then
      ours()
      show(id)
    end
  end

  function M.move_window()
    local window = hl.get_active_window()
    if not window or (window.workspace and window.workspace.id == S.last) then return end
    -- A closed row's desktops are put away: the window waits with them.
    local target = row_open() and tostring(S.last) or "{parked}" .. S.last
    hl.dispatch(hl.dsp.window.move({{ workspace = target, follow = false }}))
  end

  -- A swipe that leaves the row (or enters it from a normal desktop) bounces back.
  local function on_active(ws)
    if not ws or ws.special then return end
    local monitor = ws.monitor or hl.get_active_monitor()
    if not monitor then return end
    local before = S.shown[monitor.name]
    S.shown[monitor.name] = ws.id
    if is_scratch(ws) then S.last = ws.id end
    if S.busy == 0 and before ~= nil and (before >= first) ~= is_scratch(ws)
        and next_to(monitor, before, ws.id) then
      -- Not right away: a swipe that just ended sets its workspace after this
      -- event, and would undo a switch made from inside it.
      ours()
      after({bounce}, function()
        local now = hl.get_active_monitor()
        if now and now.name == monitor.name and now.active_workspace and now.active_workspace.id == ws.id then
          ours()  -- this switch is ours too: no bounce of the bounce
          show(before)
        end
      end)
      after({settle}, settle)
      return
    end
    -- During our own switch the flight is still running: switching to the
    -- user's animation now (Omarchy's is off) would end it at once, so the
    -- timer of that switch settles it.
    if S.busy == 0 then settle() end
  end

  for _, subscription in ipairs(_G.tuneup_scratch_events or {{}}) do subscription:remove() end
  _G.tuneup_scratch_events = {{
    hl.on("workspace.active", on_active),
    hl.on("monitor.focused", function() settle() end),
  }}
  S.anim = ""
  settle()
  tuneup_scratch = M
end"""


def module_lua(user: dict | None = None, kept: int = KEPT) -> str:
    """kept: scratch desktops that are always there while the row is open."""
    user = user_animation() if user is None else user
    return MODULE.format(first=FIRST, settle=SETTLE_MS, user=lua_table(user), fly=lua_table(FLY),
                         parked=PARKED, parked_pattern=PARKED.replace("-", "%-"), kept=kept, bounce=BOUNCE_MS)


def call(body: str, otherwise: str = "") -> str:
    """A bind's function. The module may not be loaded yet (a file written
    before Hyprland reloaded it): then `otherwise` (a dispatcher), or nothing."""
    fallback = f" else hl.dispatch({otherwise})" if otherwise else ""
    return f"function() if tuneup_scratch then tuneup_scratch.{body}{fallback} end end"


def digit_call(action: str, index: int, otherwise: str) -> str:
    return call(f"digit({hypr.lua_string(action)}, {index}, {otherwise})", otherwise)


# --- setup -----------------------------------------------------------------------------------


def unpark_all() -> list[str]:
    """Scratch desktops put away while the row was closed come back as normal
    workspaces (switching the feature off, uninstalling): nothing stays hidden."""
    moved = []
    for client in hypr.query_list("clients"):
        name = str((client.get("workspace") or {}).get("name") or "")
        if name.startswith(PARKED) and name[len(PARKED):].isdigit():
            hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{name[len(PARKED):]}", follow = false, '
                          f'window = "address:{client["address"]}" }})')
            moved.append(str(client.get("class") or client["address"]))
    return moved


def rescue_scratchpad() -> list[str]:
    """Windows left in Omarchy's scratchpad go to the first scratch desktop (the
    scratchpad has no key any more)."""
    moved = []
    for client in hypr.query_list("clients"):
        if (client.get("workspace") or {}).get("name") == OMARCHY_SCRATCHPAD:
            hypr.dispatch(f'hl.dsp.window.move({{ workspace = "{FIRST}", follow = false, '
                          f'window = "address:{client["address"]}" }})')
            moved.append(str(client.get("class") or client["address"]))
    return moved
