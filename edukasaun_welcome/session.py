"""Session gate: Welcome Screen first, Eduka-Desktop second, never on the live system."""
import os
import shutil
import subprocess
from pathlib import Path

# Debian live-boot / live-config and Ubuntu casper markers.
LIVE_BOOT_ARGUMENTS = ("boot=live", "boot=casper")
LIVE_PATHS = ("/run/live/medium", "/lib/live/mount/medium", "/run/casper", "/rofs")


def is_live_session(cmdline_path="/proc/cmdline", live_paths=LIVE_PATHS):
    """True when running from the live image, where no Welcome Screen is wanted."""
    try:
        arguments = Path(cmdline_path).read_text(encoding="utf-8", errors="replace").split()
    except OSError:
        arguments = []
    if any(argument in LIVE_BOOT_ARGUMENTS for argument in arguments):
        return True
    return any(Path(path).exists() for path in live_paths)


def should_show_welcome(preferences, live=None):
    """Show only on an installed system, and only while the user keeps it enabled."""
    live = is_live_session() if live is None else live
    return not live and preferences.get("always_show", True)


def process_running(name, proc_root="/proc"):
    """Look for a process of the current user by executable name, without psutil."""
    if not name:
        return False
    uid = os.getuid()
    root = Path(proc_root)
    try:
        entries = list(root.iterdir())
    except OSError:
        return False
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            if (entry / "comm").read_text().strip() == name[:15]:
                return True
        except OSError:
            continue
    return False


def start_desktop(settings, popen=subprocess.Popen):
    """Start Eduka-Desktop detached, unless it is already running or not installed."""
    command = list(settings.get("command", []))
    if not command or not shutil.which(command[0]):
        return False
    if process_running(settings.get("process") or Path(command[0]).name):
        return True
    popen(command, start_new_session=True)
    return True
