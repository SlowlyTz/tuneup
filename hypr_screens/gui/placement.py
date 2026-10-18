"""Where the settings window sits: floating, sized and centred, and brought to
the desktop in front of you when it is shown again from somewhere else."""
import os
import shutil
import subprocess

from hypr_screens import hypr

WIDTH, HEIGHT = 1100, 760


def own_client() -> dict | None:
    return next((c for c in hypr.query_list("clients") if c.get("pid") == os.getpid()), None)


def float_centered() -> bool:
    """Fallback for a Lua file without the window rule (keybinds.render): float
    it, sized, centred on the focused screen. With the rule it already floats."""
    client = own_client()
    if client is None or client.get("floating"):
        return False
    center(client["address"])
    return False


def bring_here(workspace: int | None) -> bool:
    """Shown again while it is open on another desktop: it moves to the one in
    front of you (`workspace`, taken before showing it), like hypr-minimizer's
    restore, and is centred there. A minimized window comes back through
    hypr-minimizer, so its list stays right."""
    client = own_client()
    if client is None or workspace is None:
        return False
    address = client["address"]
    where = client.get("workspace") or {}
    if str(where.get("name", "")).startswith("special:minimized") and shutil.which("hypr-minimizer"):
        subprocess.run(["hypr-minimizer", "restore", address, "--here"], check=False, capture_output=True,
                       timeout=10)
    elif where.get("id") != workspace:
        hypr.eval_lua(f"hl.dispatch(hl.dsp.window.move({{ workspace = '{workspace}', follow = true, "
                      f"window = 'address:{address}' }}))")
    else:
        return float_centered()
    center(address, workspace)
    hypr.eval_lua(f"hl.dispatch(hl.dsp.focus({{ window = 'address:{address}' }}))")
    return False


def center(address: str, workspace: int | None = None) -> None:
    """Float it, sized and centred on the screen showing `workspace` (else
    the focused one)."""
    screens = hypr.monitors()
    monitor = next((m for m in screens if workspace is not None
                    and (m.get("activeWorkspace") or {}).get("id") == workspace), None)
    monitor = monitor or next((m for m in screens if m.get("focused")), None)
    if monitor is None:
        return
    scale = float(monitor.get("scale") or 1)
    width, height = int(monitor["width"] / scale), int(monitor["height"] / scale)
    if int(monitor.get("transform") or 0) % 2:
        width, height = height, width
    w, h = min(WIDTH, width - 80), min(HEIGHT, height - 80)
    x, y = monitor["x"] + (width - w) // 2, monitor["y"] + (height - h) // 2
    window = f"window = 'address:{address}'"
    hypr.eval_lua("; ".join([
        f"hl.dispatch(hl.dsp.window.float({{ action = 'enable', {window} }}))",
        f"hl.dispatch(hl.dsp.window.resize({{ x = {w}, y = {h}, {window} }}))",
        f"hl.dispatch(hl.dsp.window.move({{ x = {x}, y = {y}, {window} }}))",
    ]))
