-- A Hyprland for the scratch desktops' Lua (tests/test_scratch.py): monitors,
-- workspaces that are created on demand and dropped when empty and out of
-- sight, the focus and window.move dispatchers, events, timers, animations
-- and a swipe like Hyprland's (to the next workspace of that screen, a new one
-- past the last). Nothing here is Hyprland's; it only behaves like it.
local fake = { monitors = {}, workspaces = {}, windows = {}, timers = {}, handlers = {}, log = {},
               specials = {}, specials_order = {}, persistent = {}, animation = nil, active_window = nil }

local function sorted_ids()
  local ids = {}
  for id in pairs(fake.workspaces) do table.insert(ids, id) end
  table.sort(ids)
  return ids
end

local function windows_on(id)
  local n = 0
  for _, w in ipairs(fake.windows) do if w.workspace.id == id then n = n + 1 end end
  return n
end

function fake.focused()
  for _, m in ipairs(fake.monitors) do if m.focused then return m end end
end

function fake.add_monitor(name, id)
  local m = { name = name, focused = #fake.monitors == 0 }
  table.insert(fake.monitors, m)
  local ws = fake.workspace(id, m)
  m.active_workspace = ws
  return m
end

function fake.workspace(id, monitor)
  local ws = fake.workspaces[id]
  if not ws then
    ws = { id = id, name = tostring(id), special = false, monitor = monitor }
    fake.workspaces[id] = ws
  end
  return ws
end

function fake.fire(event, ...)
  for _, sub in ipairs(fake.handlers[event] or {}) do sub.fn(...) end
end

-- What a switch on that monitor leaves behind: an empty workspace out of sight
-- is gone, unless a rule keeps it (persistent).
local function drop_if_empty(ws)
  if not ws or fake.persistent[ws.id] then return end
  for _, m in ipairs(fake.monitors) do if m.active_workspace == ws then return end end
  if windows_on(ws.id) == 0 then fake.workspaces[ws.id] = nil end
end

function fake.show(monitor, ws)
  local old = monitor.active_workspace
  ws.monitor = monitor
  monitor.active_workspace = ws
  table.insert(fake.log, monitor.name .. " " .. ws.id .. " " .. fake.style())
  if old ~= ws then drop_if_empty(old) end
  fake.fire("workspace.active", ws)
end

function fake.style()
  local a = fake.animation
  if not a or not a.enabled then return "instant" end
  return a.style or "?"
end

function fake.focus_monitor(monitor)
  for _, m in ipairs(fake.monitors) do m.focused = (m == monitor) end
  fake.fire("monitor.focused", monitor)
end

local function focus_on_current(id)
  local here = fake.focused()
  local ws = fake.workspaces[id]
  if ws and ws.monitor ~= here then
    for _, other in ipairs(fake.monitors) do
      if other.active_workspace == ws then  -- shown elsewhere: the two swap
        local mine = here.active_workspace
        mine.monitor = other
        other.active_workspace = mine
      end
    end
  end
  fake.show(here, ws or fake.workspace(id, here))
end

local function dispatch(d)
  if d.op == "focus" then
    local id = tonumber(d.args.workspace)
    if d.args.on_current_monitor then return focus_on_current(id) end
    local ws = fake.workspaces[id]
    if ws then fake.focus_monitor(ws.monitor) end
    fake.show(fake.focused(), ws or fake.workspace(id, fake.focused()))
  elseif d.op == "move" then
    local window = fake.active_window
    if d.args.window then
      window = nil
      for _, w in ipairs(fake.windows) do if "address:" .. w.address == d.args.window then window = w end end
    end
    if not window then return end
    local name = tostring(d.args.workspace)
    local id = tonumber(name)
    local target
    if id then
      target = fake.workspaces[id] or fake.workspace(id, fake.focused())
    else  -- a special workspace: hidden, out of every screen's list of workspaces
      target = fake.specials[name]
      if not target then
        target = { id = -100 - #fake.specials_order, name = name, special = true, monitor = fake.focused() }
        fake.specials[name] = target
        table.insert(fake.specials_order, name)
      end
    end
    local from = window.workspace
    window.workspace = target
    table.insert(fake.log, "window " .. window.name .. " -> " .. name)
    if d.args.follow ~= false and id then fake.show(target.monitor, target) end
    if not from.special then drop_if_empty(from) end
  elseif d.op == "wsmove" then
    local ws = fake.workspaces[tonumber(d.args.workspace)]
    for _, m in ipairs(fake.monitors) do
      if m.name == d.args.monitor and ws then
        table.insert(fake.log, "workspace " .. ws.id .. " -> " .. m.name)
        ws.monitor = m
      end
    end
  elseif d.op == "exec" then
    table.insert(fake.log, "exec " .. d.args)
  end
end

-- A three-finger swipe on the focused screen: to its next workspace that way,
-- a new one past the last (workspace_swipe_create_new).
function fake.swipe(direction)
  local here = fake.focused()
  local current = here.active_workspace.id
  local target
  local ids = sorted_ids()
  if direction == "right" then
    for _, id in ipairs(ids) do
      if id > current and fake.workspaces[id].monitor == here and not target then target = id end
    end
    if not target then  -- a new one: the next id no screen uses yet
      target = current + 1
      while fake.workspaces[target] do target = target + 1 end
    end
  else
    for i = #ids, 1, -1 do
      local id = ids[i]
      if id < current and fake.workspaces[id].monitor == here and not target then target = id end
    end
    if not target then return end  -- nothing that way: the swipe snaps back
  end
  local ws = fake.workspaces[target] or fake.workspace(target, here)
  fake.show(here, ws)
  -- Like Hyprland: the ending swipe sets its workspace after the event, so a
  -- switch made from inside the event is undone.
  if here.active_workspace ~= ws then
    table.insert(fake.log, "swipe ends on " .. ws.id)
    ws.monitor = here
    here.active_workspace = ws
  end
end

function fake.run_timers()
  while #fake.timers > 0 do
    local pending = fake.timers
    fake.timers = {}
    for _, fn in ipairs(pending) do fn() end
  end
end

function fake.open_window(name)
  local window = { name = name, address = "0x" .. name, workspace = fake.focused().active_workspace }
  table.insert(fake.windows, window)
  fake.active_window = window
  return window
end

hl = {
  dsp = {
    focus = function(args) return { op = "focus", args = args } end,
    exec_cmd = function(cmd) return { op = "exec", args = cmd } end,
    window = { move = function(args) return { op = "move", args = args } end },
    workspace = { move = function(args) return { op = "wsmove", args = args } end },
  },
  dispatch = dispatch,
  animation = function(spec) fake.animation = spec end,
  timer = function(fn, _) table.insert(fake.timers, fn) end,
  on = function(event, fn)
    fake.handlers[event] = fake.handlers[event] or {}
    local sub = { fn = fn }
    function sub.remove()
      for i, s in ipairs(fake.handlers[event]) do if s == sub then table.remove(fake.handlers[event], i) end end
    end
    table.insert(fake.handlers[event], sub)
    return sub
  end,
  get_active_monitor = function() return fake.focused() end,
  get_active_window = function() return fake.active_window end,
  get_workspaces = function()
    local list = {}
    for _, id in ipairs(sorted_ids()) do table.insert(list, fake.workspaces[id]) end
    for _, name in ipairs(fake.specials_order) do table.insert(list, fake.specials[name]) end
    return list
  end,
  get_monitors = function() return fake.monitors end,
  workspace_rule = function(rule)
    local id = tonumber(rule.workspace)
    fake.persistent[id] = rule.persistent or nil
    if rule.persistent then
      local monitor
      for _, m in ipairs(fake.monitors) do if m.name == rule.monitor then monitor = m end end
      fake.workspace(id, monitor or fake.focused())
    else
      drop_if_empty(fake.workspaces[id])
    end
  end,
  get_workspace_windows = function(ws)
    local list = {}
    for _, w in ipairs(fake.windows) do if w.workspace == ws then table.insert(list, w) end end
    return list
  end,
}

return fake
