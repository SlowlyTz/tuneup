-- App to desktop's Lua against fake_hl.lua: lua apps_test.lua <module.lua> <desktops.json>
package.path = arg[0]:match("(.*/)") .. "?.lua;" .. package.path
local fake = require("fake_hl")

local function check(cond, message)
  if not cond then
    io.stderr:write("FAILED: " .. message .. "\n  log: " .. table.concat(fake.log, " | ") .. "\n")
    os.exit(1)
  end
end
local function logged(text)
  for _, line in ipairs(fake.log) do if line == text then return true end end
  return false
end
local function osd_count()
  local n = 0
  for _, line in ipairs(fake.log) do if line:find("^exec .*omarchy%-osd") then n = n + 1 end end
  return n
end
local function open(name, class)
  local window = fake.open_window(name, class)
  fake.fire("window.open", window)
  return window
end

local laptop = fake.add_monitor("eDP-1", 1)
fake.add_monitor("HDMI-A-1", 21)
assert(loadfile(arg[1]))()

-- Discord belongs on scratch desktop 1; the row is closed: it waits there unseen.
local discord = open("discord", "discord")
check(discord.workspace.name == "special:tuneup-scratch-201", "a closed row: the app waits with its desktop")
check(laptop.active_workspace.id == 1, "the screen stays where it was")
check(osd_count() == 1 and logged("exec /fake/omarchy-osd -i '\u{f14de}' -m Discord -d 2000"), "the rocket tells it started")

-- Within the 5 s it is put back when it leaves.
discord.workspace = fake.workspaces[1]
fake.run_round(200)
check(discord.workspace.name == "special:tuneup-scratch-201", "moved away in the first 5 s: back it goes")

-- A second window of it in the same launch: no second rocket.
open("discord2", "discord")
check(osd_count() == 1, "one rocket per launch")

-- After the 5 s it may go anywhere.
fake.run_timers()
discord.workspace = fake.workspaces[1]
fake.fire("window.class", discord)
fake.run_timers()
check(discord.workspace.id == 1, "after 5 s the window stays where it was moved")

-- A web app gets its class a moment after it opened: desktop 3, floating.
local whatsapp = open("whatsapp", "")
check(whatsapp.workspace.id == 1, "no class yet: left alone")
whatsapp.class = "chrome-abc-Default"
fake.fire("window.class", whatsapp)
check(whatsapp.workspace.id == 3, "with its class: desktop 3")
check(whatsapp.floating == true and logged("float whatsapp on"), "floating as chosen")
fake.run_round(1)
check(logged("resize whatsapp") and logged("center whatsapp"), "sized and centred after the move")
check(osd_count() == 2, "desktop 3 is not shown: the rocket again")
fake.run_timers()

-- One that floats by itself is sized and centred all the same.
local floating = fake.open_window("whatsapp3", "chrome-abc-default")
floating.floating = true
fake.fire("window.open", floating)
fake.run_round(1)
check(not logged("float whatsapp3 on") and logged("resize whatsapp3"), "floating already: only sized")
check(osd_count() == 3, "a new launch: a new rocket")
fake.run_timers()

-- Other apps are left alone.
local foot = open("foot", "foot")
fake.run_timers()
check(foot.workspace.id == 1, "an app without a desktop opens where it is")

-- The row open on the laptop: Discord goes to scratch desktop 1 itself, shown: no rocket.
fake.show(laptop, fake.workspace(201, laptop))
local again = open("discord3", "discord")
check(again.workspace.id == 201, "an open row: straight onto scratch desktop 1")
check(osd_count() == 3, "shown where it starts: no rocket")
fake.run_timers()

-- The desktops' ids follow the screens (desktops.json).
local file = assert(io.open(arg[2], "w"))
file:write('{"omarchy": true, "desk_first": 11}')
file:close()
local moved = open("whatsapp2", "chrome-abc-default")
check(moved.workspace.id == 13, "desktop 3 of block 1 is workspace 13")
fake.run_timers()

print("ok")
