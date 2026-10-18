"""Samsung Galaxy Book: battery, charge limit, performance mode, firmware switches."""

from hypr_screens import config, install
from hypr_screens import samsung as samsung_mod
from hypr_screens.api.core import ApiError, endpoint, need, is_number, settings

SAMSUNG_ATTRIBUTES = {"usbCharging": "usb_charging", "lidPower": "power_on_lid_open"}


def battery_minutes() -> tuple[int | None, int | None]:
    """(minutes left on battery, minutes until full), from the battery's own numbers."""
    battery = samsung_mod.battery_dir()
    if battery is None:
        return None, None
    status = samsung_mod.read(battery / "status")
    now = samsung_mod.number(battery / "energy_now") or samsung_mod.number(battery / "charge_now")
    full = samsung_mod.number(battery / "energy_full") or samsung_mod.number(battery / "charge_full")
    rate = samsung_mod.number(battery / "power_now") if samsung_mod.number(battery / "energy_now") \
        else samsung_mod.number(battery / "current_now")
    if not now or not rate:
        return None, None
    if status == "Discharging":
        return round(60 * now / rate), None
    if status == "Charging" and full and full > now:
        return None, round(60 * (full - now) / rate)
    return None, None


def samsung_view() -> dict:
    if not samsung_mod.present():
        return {"available": False, "active": False}
    status = samsung_mod.status(settings())
    battery = status["battery"]
    left, full_in = battery_minutes()
    keyboard = status["keyboard"]
    return {
        "available": True,
        "active": samsung_mod.active(),
        "writable": status["writable"],
        "level": battery.get("percent"),
        "status": battery.get("status") or None,
        "charging": battery.get("status") == "Charging",
        "plugged": status["ac"],
        "health": battery.get("health"),
        "cycles": battery.get("cycles"),
        "power": battery.get("watts"),
        "remainingMinutes": left,
        "fullInMinutes": full_in,
        "chargeLimit": status["limit"],
        "wantedLimit": status["wanted_limit"],
        "fullOnce": status["full_once"],
        "mode": status["mode"] or None,
        "modes": [{"value": mode, "label": label} for mode, label in status["modes"]],
        "fanRpm": status["fan"]["rpm"],
        "fanRunning": status["fan"]["running"],
        "cpuTemp": status["cpu_temperature"],
        "kbdLight": keyboard[0] if keyboard else None,
        "kbdMax": keyboard[1] if keyboard else None,
        "usbCharging": status["attributes"].get("usb_charging"),
        "lidPower": status["attributes"].get("power_on_lid_open"),
        "attributesWritable": status["attributes_writable"],
    }


@endpoint
def samsung() -> dict:
    """Battery, charge limit, performance mode and the firmware switches of a
    Galaxy Book; {"available": False, "active": False} on other laptops."""
    return samsung_view()


@endpoint
def set_samsung(field: str, value: object) -> dict:
    """field: active | chargeLimit | fullOnce | mode | usbCharging | lidPower | kbdLight."""
    need(samsung_mod.present(), "unavailable", "not a Samsung Galaxy Book (or the samsung-galaxybook driver is not loaded)")
    if field == "active":
        need(isinstance(value, bool), "bad_value", "active must be true or false")
        if value != samsung_mod.active():
            done = samsung_mod.setup(graphical=True) if value else samsung_mod.teardown(graphical=True)
            need(done, "cancelled", "it was cancelled or failed")
            install.sync_power_panel(samsung_mod.active())
    elif field == "chargeLimit":
        need(is_number(value) and 50 <= value <= 100, "bad_value", "chargeLimit must be 50 to 100")
        config.update(lambda cfg: samsung_mod.set_limit(cfg, int(value)))
    elif field == "fullOnce":
        need(isinstance(value, bool), "bad_value", "fullOnce must be true or false")
        need(not value or samsung_mod.ac_online(), "not_plugged", "plug in the charger first")
        config.update(lambda cfg: samsung_mod.full_once(cfg, value))
    elif field == "mode":
        config.update(lambda cfg: samsung_mod.set_mode(cfg, value))
    elif field in SAMSUNG_ATTRIBUTES:
        need(isinstance(value, bool), "bad_value", f"{field} must be true or false")
        need(samsung_mod.set_attribute(SAMSUNG_ATTRIBUTES[field], value), "not_set_up",
             "could not change it (is the one-time setup done?)")
    elif field == "kbdLight":
        keyboard = samsung_mod.keyboard()
        need(keyboard is not None, "unavailable", "this laptop has no keyboard backlight")
        need(is_number(value) and 0 <= value <= keyboard[1], "bad_value", f"kbdLight must be 0 to {keyboard[1]}")
        samsung_mod.set_keyboard(int(value))
    else:
        raise ApiError("bad_value", f"unknown field: {field!r}")
    return samsung_view()
