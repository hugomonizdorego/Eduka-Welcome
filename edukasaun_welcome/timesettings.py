"""Time zone and clock settings through systemd-timedated (timedatectl)."""
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

# Edukasaun OS is made in Timor-Leste: the time zone list always starts from Dili.
DEFAULT_TIMEZONE = "Asia/Dili"


def timezone_choices():
    zones = {zone for zone in available_timezones()
             if "/" in zone and not zone.startswith(("Etc/", "SystemV/", "posix/", "right/"))}
    zones.discard(DEFAULT_TIMEZONE)
    return [DEFAULT_TIMEZONE, *sorted(zones, key=str.casefold), "UTC"]


def valid_timezone(zone):
    if zone not in timezone_choices():
        return False
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def current_timezone(runner=subprocess.run):
    try:
        result = runner(["timedatectl", "show", "--property=Timezone", "--value"],
                        capture_output=True, text=True, timeout=5, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        return Path("/etc/timezone").read_text().strip()
    except OSError:
        return ""


def utc_offset(zone, moment=None):
    moment = moment or datetime.now(ZoneInfo(zone))
    offset = moment.astimezone(ZoneInfo(zone)).strftime("%z")
    return "UTC" + offset[:3] + ":" + offset[3:]


def format_clock(zone, use_24_hour=True, moment=None):
    local = (moment or datetime.now(ZoneInfo(zone))).astimezone(ZoneInfo(zone))
    clock = local.strftime("%H:%M:%S" if use_24_hour else "%I:%M:%S %p")
    return local.strftime("%A, %d %B %Y") + " · " + clock


def time_commands(zone, automatic=True, manual=None):
    """Return argument vectors; timedatectl asks PolicyKit for authentication."""
    if not valid_timezone(zone):
        raise ValueError("Choose a valid time zone.")
    commands = [["timedatectl", "set-timezone", zone],
                ["timedatectl", "set-ntp", "true" if automatic else "false"]]
    if not automatic:
        if not isinstance(manual, datetime):
            raise ValueError("Enter the date and time.")
        commands.append(["timedatectl", "set-time", manual.strftime("%Y-%m-%d %H:%M:%S")])
    return commands
