-- The scratch desktops' Lua against fake_hl.lua: lua scratch_test.lua <module.lua>
package.path = arg[0]:match("(.*/)") .. "?.lua;" .. package.path
local fake = require("fake_hl")

local function load_module()
  local chunk = assert(loadfile(arg[1]))
  chunk()
end

local function check(cond, message)
  if not cond then
    io.stderr:write("FAILED: " .. message .. "\n  log: " .. table.concat(fake.log, " | ") .. "\n")
    os.exit(1)
  end
end

local function shows(monitor) return monitor.active_workspace.id end

local laptop = fake.add_monitor("eDP-1", 3)
local hp = fake.add_monitor("DP-3", 99)
load_module()
check(fake.style() == "instant", "outside the row the user's (Omarchy's: off) animation")
fake.open_window("terminal")

-- In: the last scratch desktop (201 at first) flies in from below.
tuneup_scratch.toggle()
check(shows(laptop) == 201, "SUPER+S shows scratch desktop 1")
check(fake.log[#fake.log] == "eDP-1 201 slidevert", "it flies in vertically")
check(fake.style() == "slidevert", "the flight keeps its animation until it has settled")
fake.run_timers()
check(fake.style() == "instant", "inside the row switches like outside it: no animation")

-- Inside: SUPER+3 goes to scratch desktop 3; SUPER+SHIFT+2 takes the window to 2.
fake.open_window("notes")
tuneup_scratch.digit("switch", 3, hl.dsp.exec_cmd("tuneup switch 3"))
check(shows(laptop) == 203, "SUPER+3 in the row: scratch desktop 3")
check(fake.workspaces[201] ~= nil, "201 keeps its window")
tuneup_scratch.digit("move", 2, hl.dsp.exec_cmd("tuneup move 2"))
check(shows(laptop) == 202 and fake.active_window.workspace.id == 202, "SUPER+SHIFT+2: window and focus to 2")
fake.run_timers()

-- Out: back to the desktop it showed, flying down; the user's animation again.
tuneup_scratch.toggle()
check(shows(laptop) == 3, "SUPER+S again: back to desktop 3")
check(fake.log[#fake.log] == "eDP-1 3 slidevert", "it flies out vertically")
check(fake.style() == "slidevert", "flying out is not cut short by the user's (off) animation")
fake.run_timers()
check(fake.style() == "instant", "the user's animation is back after the flight")

-- Outside the row the desktop keys do what they did.
tuneup_scratch.digit("switch", 4, hl.dsp.exec_cmd("tuneup switch 4"))
check(fake.log[#fake.log] == "exec tuneup switch 4", "SUPER+4 outside the row: the desktop keys")

-- Back in: the last used scratch desktop (2), with its window.
tuneup_scratch.toggle()
fake.run_timers()
check(shows(laptop) == 202, "SUPER+S opens the last used scratch desktop")

-- Scratch desktops 1 to 5 are always there while the row is open, empty or
-- not: SUPER + 1 is scratch desktop 1 (seen live: the bar's "1" was another).
for id = 201, 205 do check(fake.workspaces[id] ~= nil, "scratch desktop " .. (id - 200) .. " is there") end

-- Swipes: sideways in the row, and a bounce at the left end.
fake.swipe("right")
check(shows(laptop) == 203, "swipe right: scratch desktop 3")
fake.swipe("left")
check(shows(laptop) == 202, "swipe left: back")
fake.swipe("left")
check(shows(laptop) == 201, "swipe left: scratch desktop 1, empty but kept")
fake.swipe("left")    -- next on this screen is desktop 3: out of the row ...
fake.run_timers()
check(shows(laptop) == 201, "... bounces back into the row")
check(fake.style() == "instant", "still the user's animation in the row")

-- Leaving by key is no bounce.
tuneup_scratch.toggle()
fake.run_timers()
check(shows(laptop) == 3, "SUPER+S leaves the row for good")

-- Closed, the row's desktops are put away: a swipe on a normal desktop never
-- reaches them (seen live: two swipes right from a normal desktop landed in it).
check(fake.workspaces[202] == nil and fake.specials["special:tuneup-scratch-202"] ~= nil,
      "scratch desktop 2 waits hidden while the row is closed")
check(fake.workspaces[201] == nil and fake.workspaces[205] == nil, "the kept ones leave with the row")
fake.swipe("right")
fake.run_timers()
check(shows(laptop) == 4, "a swipe right from the last normal desktop opens a new normal one")
fake.swipe("left")
fake.run_timers()
check(shows(laptop) == 3, "and back")

-- Shared by all screens: SUPER+S on the HP brings the scratch desktop there.
fake.focus_monitor(hp)
check(fake.style() == "instant", "the HP is not in the row: the user's animation")
tuneup_scratch.toggle()
fake.run_timers()
check(shows(hp) == 201 and fake.workspaces[202].monitor == hp and fake.workspaces[205].monitor == hp,
      "SUPER+S on the HP: the row (last used: 1) comes over, with its window on 2")
tuneup_scratch.toggle()
fake.run_timers()
check(shows(hp) == 99, "and back to the HP's own desktop 99")

-- SUPER+ALT+S: the active window to the last used scratch desktop, nothing follows.
fake.focus_monitor(laptop)
local mail = fake.open_window("mail")
tuneup_scratch.move_window()
check(mail.workspace.name == "special:tuneup-scratch-201" and shows(laptop) == 3,
      "SUPER+ALT+S sends the window to the (put away) last scratch desktop, the screen stays")

-- Evaluating the module again (a key changed) keeps the state, no double handlers.
load_module()
local count = #fake.handlers["workspace.active"]
check(count == 1, "one workspace.active handler after a second load, not " .. count)
tuneup_scratch.toggle()
check(shows(laptop) == 201, "the last scratch desktop survives a second load")

-- The whole row comes along to the screen that opens it, so a swipe there
-- reaches every scratch desktop (seen live: from 1 straight to a new 3).
tuneup_scratch.digit("switch", 1, hl.dsp.exec_cmd("tuneup switch 1"))
fake.open_window("one")
tuneup_scratch.digit("switch", 2, hl.dsp.exec_cmd("tuneup switch 2"))
fake.open_window("two")
tuneup_scratch.digit("switch", 1, hl.dsp.exec_cmd("tuneup switch 1"))
tuneup_scratch.toggle()                     -- leave on 1: it is the last one
fake.run_timers()
check(fake.workspaces[201] == nil and fake.workspaces[202] == nil, "both wait hidden while the row is closed")
fake.focus_monitor(hp)
tuneup_scratch.toggle()
fake.run_timers()
check(shows(hp) == 201 and fake.workspaces[202].monitor == hp, "the HP gets the whole row")
fake.swipe("right")
fake.run_timers()
check(shows(hp) == 202, "swipe right from scratch desktop 1: 2, not a new 3")

print("ok")
