"""Command line entry point of Tuneup (`tuneup`, also `hypr-screens`, its old name)."""
import argparse
import json
import sys


def print_state(cfg: dict | None = None, message: str = "") -> None:
    from hypr_screens import engine

    print(json.dumps(engine.state(cfg, message)))


def change(mutate) -> int:
    """Change the config under its lock, re-sync, print the new state."""
    from hypr_screens import config, engine

    notes = []

    def work(cfg):
        notes.append(mutate(cfg) or "")
    try:
        config.update(work)
    except config.ConfigError as error:
        print(f"tuneup: {error}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as error:
        print_state(config.load(), f"error: {error}")
        return 1
    engine.sync()
    print_state(None, notes[0] if notes else "")
    return 0


def gui(tray: bool) -> int:
    try:
        from hypr_screens.gui import app
    except (ImportError, ValueError) as error:
        print(f"tuneup: the settings window needs GTK 4, libadwaita, WebKitGTK 6.0 and PyGObject ({error})", file=sys.stderr)
        return 1
    return app.run(tray)


def parse_value(key: str, raw: str) -> object:
    from hypr_screens import config

    if raw in ("", "unset", "default", "none"):
        return None
    if key == "rotation":
        value = int(raw)
        if value not in config.ROTATIONS:
            raise ValueError(f"rotation must be one of {config.ROTATIONS}")
        return value
    if key == "scale":
        if raw == "auto":
            return raw
        value = float(raw)
        if not 0.25 <= value <= 4:
            raise ValueError("scale must be auto or between 0.25 and 4")
        return value
    if key == "position":
        if raw not in config.POSITIONS:
            raise ValueError(f"position must be one of {config.POSITIONS}")
        return raw
    if key == "mirror":
        if raw not in ("on", "off", "yes", "no", "true", "false"):
            raise ValueError("mirror must be on, off or unset")
        return raw in ("on", "yes", "true")
    return raw


def resolve_screen(cfg: dict, name: str) -> str:
    """Accept a screen id, a connector (DP-3) or a name (HP 32f, Laptop)."""
    if name in cfg["screens"]:
        return name
    for sid, screen in cfg["screens"].items():
        if name.lower() in (str(screen.get("connector", "")).lower(), str(screen.get("name", "")).lower()):
            return sid
    raise ValueError(f"unknown screen: {name}")


def power(args: argparse.Namespace) -> int:
    """The battery panel's profile buttons: Samsung's four modes when this is a
    Galaxy Book, otherwise Omarchy's power profiles unchanged."""
    from hypr_screens import config, samsung

    if not samsung.present():
        import subprocess

        command = (["omarchy-powerprofiles-list", "--active-state"] if args.action == "list"
                   else ["omarchy-powerprofiles-set", "autodetect", args.mode or ""])
        return subprocess.run(command, check=False).returncode
    if args.action == "list":
        current = samsung.current_mode()
        for mode, _label in samsung.modes():
            print(f"{mode}\t{1 if mode == current else 0}")
        return 0
    try:
        config.update(lambda cfg: samsung.set_mode(cfg, args.mode or ""))
    except (ValueError, RuntimeError) as error:
        print(f"tuneup: {error}", file=sys.stderr)
        return 1
    return 0


def camera_command(args: argparse.Namespace) -> int:
    from hypr_screens import camera, config

    if args.action == "status":
        print(json.dumps({"set_up": camera.is_set_up(), "virtual": str(camera.virtual_device() or ""),
                          "real": str(camera.real_device() or ""), "rotation": camera.rotation()}, indent=2))
        return 0
    if args.action in ("setup", "teardown"):
        work = camera.setup if args.action == "setup" else camera.teardown
        return 0 if work(graphical=not sys.stdin.isatty()) else 1
    if args.degrees not in camera.ROTATIONS:
        print(f"tuneup: rotation must be one of {camera.ROTATIONS}", file=sys.stderr)
        return 1
    try:
        config.update(lambda cfg: cfg["camera"].__setitem__("rotation", args.degrees))
    except config.ConfigError as error:
        print(f"tuneup: {error}", file=sys.stderr)
        return 1
    return 0


def samsung_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, samsung

    if not samsung.present():
        print("tuneup: not a Samsung Galaxy Book (or the samsung-galaxybook driver is not loaded)",
              file=sys.stderr)
        return 1
    if args.action == "status":
        print(json.dumps(samsung.status(), indent=2))
        return 0
    if args.action in ("setup", "teardown"):
        from hypr_screens import install

        work = samsung.setup if args.action == "setup" else samsung.teardown
        if not work(graphical=not sys.stdin.isatty()):
            return 1
        print(f"battery panel: {install.sync_power_panel(samsung.active())}")
        return 0
    def work(cfg):
        if args.action == "limit":
            samsung.set_limit(cfg, int(args.value or 100))
        else:
            samsung.full_once(cfg, (args.value or "on") in ("on", "1", "true", "yes"))
    try:
        config.update(work)
    except (ValueError, RuntimeError) as error:
        print(f"tuneup: {error}", file=sys.stderr)
        return 1
    return 0


def enforce_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, enforce

    try:
        cfg = config.read() if args.action == "status" else \
            config.update(lambda fresh: fresh.__setitem__("enforce", args.action == "on"))
    except config.ConfigError as error:
        print(f"tuneup: {error}", file=sys.stderr)
        return 1
    print(json.dumps(enforce.view(cfg), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tuneup",
        description="Tuneup – the settings app Omarchy is missing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("settings", help="open the settings window")
    sub.add_parser("tray", help="tray icon (started by the generated Lua file)")
    sub.add_parser("setup", help="wire Tuneup into Hyprland and Omarchy (the installer runs it; keeps your settings)")
    restart = sub.add_parser("restart", help="start the watcher and the tray anew")
    restart.add_argument("--open", action="store_true", help="open the window too")
    update = sub.add_parser("update", help="update Tuneup from GitHub (git pull + install.sh --update)")
    update.add_argument("--check", action="store_true", help="only say whether there is an update")
    update.add_argument("--report", action="store_true", help=argparse.SUPPRESS)  # for the settings window
    uninstall = sub.add_parser("uninstall", help="remove Tuneup (the system packages stay)")
    uninstall.add_argument("--keep-settings", action="store_true", help="keep ~/.config/tuneup")
    uninstall.add_argument("--yes", action="store_true", help="do not ask")
    helper = sub.add_parser("installer", help=argparse.SUPPRESS)  # for install.sh
    helper.add_argument("action", choices=["packages", "root-script", "choices", "remember", "galaxy-book",
                                           "set-up", "version"])
    helper.add_argument("values", nargs="*")
    sub.add_parser("watch", help="background watcher (started by the generated Lua file)")
    sub.add_parser("apply", help="apply all settings now")
    sub.add_parser("state", help="print everything as JSON")
    sub.add_parser("list", help="list known screens")

    setting = sub.add_parser("set", help="set a screen setting, e.g. `set Laptop rotation 180`")
    setting.add_argument("screen")
    setting.add_argument("key", choices=["rotation", "scale", "mode", "position", "mirror"])
    setting.add_argument("value", help="value, or `unset`")

    when = sub.add_parser("when", help="tie a setting to another screen: `when Laptop rotation \"HP 32f\"`")
    when.add_argument("screen")
    when.add_argument("key")
    when.add_argument("other", help="screen that must be connected, or `always`")

    favorite = sub.add_parser("favorite", help="toggle a favorite")
    favorite.add_argument("screen")
    forget = sub.add_parser("forget", help="forget a screen that is not connected")
    forget.add_argument("screen")

    swap = sub.add_parser("swap", help="swap the fixed screen until unplugged")
    swap.add_argument("role", nargs="?", choices=["panel", "external"])

    bind = sub.add_parser("bind", help="set a key: `bind stash 1 \"SUPER + M\"`")
    bind.add_argument("action")
    bind.add_argument("slot", type=int, choices=[1, 2])
    bind.add_argument("combo", nargs="?", default="", help="empty to clear")

    option = sub.add_parser("option", help="desktop_keys on|off, default_fixed off|external|panel, fixed_desktops 1-10, "
                                          "scratch on|off, scratch_shift_s on|off, scratch_swipe on|off")
    option.add_argument("name", choices=["desktop_keys", "default_fixed", "fixed_desktops", "scratch",
                                         "scratch_shift_s", "scratch_kept", "scratch_swipe"])
    option.add_argument("value", nargs="?", default="next")

    for name, text in (
        ("switch", "show desktop N (1-10)"),
        ("move", "move the active window to desktop N and follow"),
        ("move-silent", "move the active window to desktop N, stay"),
    ):
        desk = sub.add_parser(name, help=text)
        desk.add_argument("index", type=int)
        where = desk.add_mutually_exclusive_group()
        where.add_argument("--fixed", action="store_true", help="desktop N of the fixed screen (its bar)")
        where.add_argument("--desk", action="store_true", help="desktop N of the other screen, whatever has the focus")
    sub.add_parser("next", help="next used desktop")
    sub.add_parser("prev", help="previous used desktop")
    cycle = sub.add_parser("cycle", help="focus the next visible window")
    cycle.add_argument("direction", nargs="?", choices=["prev"])
    sub.add_parser("status", help="fixed screen status as JSON")
    enforce = sub.add_parser("enforce", help="keep what Tuneup sets: status | on | off")
    enforce.add_argument("action", nargs="?", default="status", choices=["status", "on", "off"])
    cam = sub.add_parser("camera", help="the turned virtual camera: status | setup | teardown | rotate 0|90|180|270")
    cam.add_argument("action", choices=["status", "setup", "teardown", "rotate"])
    cam.add_argument("degrees", nargs="?", type=int)
    wid = sub.add_parser("widgets", help="desktop widgets: save PLACEMENTS_JSON (used by the arranging overlay)")
    wid.add_argument("action", choices=["save"])
    wid.add_argument("placements")
    power = sub.add_parser("power", help="performance mode, used by the battery panel: list | set MODE")
    power.add_argument("action", choices=["list", "set"])
    power.add_argument("mode", nargs="?")
    samsung = sub.add_parser("samsung",
                             help="Samsung Galaxy Book: status | setup | teardown | limit N | full-once on|off")
    samsung.add_argument("action", choices=["status", "setup", "teardown", "limit", "full-once"])
    samsung.add_argument("value", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    raise SystemExit(run(args))


DESKTOP_COMMANDS = ("switch", "move", "move-silent", "next", "prev", "cycle")


def desktop_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, desktops

    if args.command == "cycle":
        desktops.cycle(-1 if args.direction == "prev" else 1)
    elif args.command in ("next", "prev"):
        desktops.step(config.load(), 1 if args.command == "next" else -1)
    else:
        desktops.switch(config.load(), args.command, args.index, fixed=True if args.fixed else False if args.desk else None)
    return 0


def unreadable(error: Exception) -> int:
    print(f"tuneup: {error}", file=sys.stderr)
    return 1


def watch_command(args: argparse.Namespace) -> int:
    from hypr_screens import watch

    return watch.watch()


def apply_command(args: argparse.Namespace) -> int:
    from hypr_screens import engine

    print(", ".join(engine.sync()) or "nothing to change")
    return 0


def state_command(args: argparse.Namespace) -> int:
    print_state()
    return 0


def status_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, desktops

    print(json.dumps(desktops.status(config.load())))
    return 0


def widgets_command(args: argparse.Namespace) -> int:
    """The arranging overlay saves the places and sizes it was given."""
    from hypr_screens import config, widgets

    try:
        placements = json.loads(args.placements)
    except json.JSONDecodeError:
        print("tuneup: placements must be JSON", file=sys.stderr)
        return 1
    try:
        cfg = config.update(lambda cfg: widgets.save_placements(cfg, placements if isinstance(placements, dict) else {}))
    except config.ConfigError as error:
        return unreadable(error)
    widgets.export(cfg)
    return 0


def list_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, engine, hypr

    cfg = config.load()
    for row in engine.screen_rows(cfg, set(config.connected(hypr.monitors(include_disabled=True)))):
        mark = "●" if row["connected"] else "○"
        star = "★" if row["favorite"] else " "
        print(f"{mark} {star} {row['name']:<24} {row['connector']:<10} {row['summary']}")
    return 0


def set_command(args: argparse.Namespace) -> int:
    from hypr_screens import config

    def mutate(cfg):
        sid = resolve_screen(cfg, args.screen)
        config.set_setting(cfg, sid, args.key, parse_value(args.key, args.value))
    return change(mutate)


def when_command(args: argparse.Namespace) -> int:
    from hypr_screens import config

    def mutate(cfg):
        sid = resolve_screen(cfg, args.screen)
        other = None if args.other == "always" else resolve_screen(cfg, args.other)
        config.set_condition(cfg, sid, args.key, other)
    return change(mutate)


def favorite_command(args: argparse.Namespace) -> int:
    def mutate(cfg):
        screen = cfg["screens"][resolve_screen(cfg, args.screen)]
        screen["favorite"] = not screen.get("favorite")
    return change(mutate)


def forget_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, hypr

    def mutate(cfg):
        sid = resolve_screen(cfg, args.screen)
        if cfg["screens"][sid].get("internal"):
            raise ValueError("the laptop screen cannot be forgotten")
        if sid in config.connected(hypr.monitors(include_disabled=True)):
            raise ValueError("unplug it first")
        del cfg["screens"][sid]
        for screen in cfg["screens"].values():
            for setting in screen.get("settings", {}).values():
                if setting.get("when") == sid:
                    setting["when"] = None
    return change(mutate)


def swap_command(args: argparse.Namespace) -> int:
    from hypr_screens import config, desktops

    cfg = config.load()
    try:
        desktops.swap(cfg, args.role)
    except RuntimeError as error:
        print_state(cfg, f"error: {error}")
        return 1
    print_state(cfg)
    return 0


def keys_change(work) -> tuple[dict, dict] | int:
    """config.update(work) for a key or an option: (before, after), or the exit code."""
    from hypr_screens import config

    before = []

    def mutate(cfg):
        before.append(config.normalize(json.loads(json.dumps(cfg))))
        work(cfg)
    try:
        cfg = config.update(mutate)
    except config.ConfigError as error:
        return unreadable(error)
    except ValueError as error:
        print_state(config.load(), f"error: {error}")
        return 1
    return before[0], cfg


def bind_command(args: argparse.Namespace) -> int:
    from hypr_screens import keybinds

    notes = []
    result = keys_change(lambda cfg: notes.append(keybinds.set_key(cfg, args.action, args.slot - 1, args.combo)))
    if isinstance(result, int):
        return result
    before, cfg = result
    keybinds.write(cfg)
    keybinds.go_live(before, cfg)
    print_state(cfg, notes[0])
    return 0


def option_value(cfg: dict, name: str, value: str) -> object:
    """desktop_keys: on/off or next/prev (toggle); default_fixed: a choice or next/prev;
    fixed_desktops: 1-10 or next/prev."""
    from hypr_screens import config

    if name in ("fixed_desktops", "scratch_kept"):
        if value in ("next", "prev"):
            return (cfg[name] + (0 if value == "next" else -2)) % 10 + 1
        if not value.isdigit() or not 1 <= int(value) <= 10:
            raise ValueError(f"{name} must be 1-10")
        return int(value)
    if name in ("desktop_keys", "scratch", "scratch_shift_s", "scratch_swipe"):
        return not cfg[name] if value in ("next", "prev") else value in ("on", "1", "true", "yes")
    choices = config.FIXED_DEFAULTS
    if value in ("next", "prev"):
        value = choices[(choices.index(cfg["default_fixed"]) + (1 if value == "next" else -1)) % len(choices)]
    if value not in choices:
        raise ValueError(f"default_fixed must be one of {choices}")
    return value


def option_command(args: argparse.Namespace) -> int:
    from hypr_screens import engine, keybinds

    result = keys_change(lambda cfg: cfg.__setitem__(args.name, option_value(cfg, args.name, args.value)))
    if isinstance(result, int):
        return result
    before, cfg = result
    keybinds.option_changed(before, cfg, args.name)
    engine.sync()
    print_state()
    return 0


HANDLERS = {
    "watch": watch_command, "apply": apply_command, "state": state_command, "status": status_command,
    "enforce": enforce_command, "camera": camera_command, "widgets": widgets_command, "power": power,
    "samsung": samsung_command, "list": list_command, "set": set_command, "when": when_command,
    "favorite": favorite_command, "forget": forget_command, "swap": swap_command, "bind": bind_command,
    "option": option_command,
}


def setup_command(args: argparse.Namespace) -> int:
    from hypr_screens import setup

    return setup.main()


def restart_command(args: argparse.Namespace) -> int:
    from hypr_screens import install

    for line in install.restart(open_window=args.open):
        print(f"  {line}")
    return 0


def update_command(args: argparse.Namespace) -> int:
    from hypr_screens import updates

    if not args.check:
        return updates.run(report=args.report)
    state = updates.check()
    print(json.dumps(state, indent=2))
    return 0 if state["reason"] in (None,) else 1


def uninstall_command(args: argparse.Namespace) -> int:
    from hypr_screens import uninstall

    return uninstall.main(keep_settings=args.keep_settings, yes=args.yes)


def installer_command(args: argparse.Namespace) -> int:
    from hypr_screens import installer

    return installer.main(args.action, args.values)


HANDLERS.update({"setup": setup_command, "restart": restart_command, "update": update_command,
                 "uninstall": uninstall_command, "installer": installer_command})


def run(args: argparse.Namespace) -> int:
    command = args.command
    if command in DESKTOP_COMMANDS:  # the hot path: desktop keys fire on every keypress
        return desktop_command(args)
    if command in ("settings", "tray"):
        return gui(tray=command == "tray")
    return HANDLERS[command](args) if command in HANDLERS else 1
