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


def shown_marker():
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "edukasaun-welcome/shown-before-session"


def mark_shown():
    """Remember for this login that the Welcome Screen already ran before the session."""
    try:
        marker = shown_marker()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(os.getpid()))
    except OSError:
        pass


def process_running(name, proc_root="/proc"):
    """Find a process of the current user whose command line runs `name`.

    Eduka-Desktop components are Python scripts started through `env`, so the
    process name is often `python3`; compare command line arguments instead.
    """
    if not name:
        return False
    uid = os.getuid()
    try:
        entries = list(Path(proc_root).iterdir())
    except OSError:
        return False
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            arguments = (entry / "cmdline").read_bytes().split(b"\0")[:4]
        except OSError:
            continue
        if any(Path(argument.decode(errors="replace")).name == name for argument in arguments if argument):
            return True
    return False


def start_desktop(settings, popen=subprocess.Popen):
    """Start each Eduka-Desktop component detached, unless running or not installed."""
    environment = {**os.environ, **{str(k): str(v) for k, v in settings.get("environment", {}).items()}}
    started = False
    for component in settings.get("components", []):
        command = list(component.get("command", []))
        if not command or not shutil.which(command[0]):
            continue
        started = True
        if not process_running(component.get("process") or Path(command[0]).name):
            popen(command, start_new_session=True, env=environment)
    return started
