"""LXQt configuration using Qt's own INI serializer and native wallpaper CLI."""
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PyQt6.QtCore import QSettings
from .preferences import config_home


def theme_choices(kind, home=None):
    home = Path.home() if home is None else Path(home)
    if kind == "theme":
        roots = [home / ".local/share/lxqt/themes", Path("/usr/local/share/lxqt/themes"),
                 Path("/usr/share/lxqt/themes")]
        valid = lambda path: (path / "lxqt-panel.qss").is_file()
    else:
        roots = [home / ".icons", home / ".local/share/icons", Path("/usr/local/share/icons"),
                 Path("/usr/share/icons")]
        valid = (lambda path: (path / "cursors").is_dir()) if kind == "cursor" else (
            lambda path: (path / "index.theme").is_file() and
            any(child.is_dir() and child.name != "cursors" for child in path.iterdir()))
    result = set()
    for root in roots:
        if root.is_dir():
            result.update(path.name for path in root.iterdir() if path.is_dir() and valid(path))
    return sorted(result, key=str.casefold)


def current_settings(root=None):
    root = config_home() if root is None else Path(root)
    settings = QSettings(str(root / "lxqt/lxqt.conf"), QSettings.Format.IniFormat)
    return {"icons": settings.value("icon_theme", ""), "theme": settings.value("theme", ""),
            "accent": settings.value("Palette/highlight_color", "#00a887")}


def apply_desktop(values, root=None, runner=subprocess.run):
    """Back up existing settings; restore the file if the operation fails."""
    if "LXQt" not in os.environ.get("XDG_CURRENT_DESKTOP", "").split(":"):
        raise RuntimeError("Desktop apply is supported in an LXQt session only.")
    root = config_home() if root is None else Path(root)
    wallpaper = values.get("wallpaper", "")
    if wallpaper and (not Path(wallpaper).is_file() or not shutil.which("pcmanfm-qt")):
        raise RuntimeError("Wallpaper or PCManFM-Qt is unavailable.")
    for field, kind in (("icons", "icons"), ("theme", "theme")):
        if values.get(field) and values[field] not in theme_choices(kind):
            raise ValueError("Choose an installed theme.")
    accent = values.get("accent", "")
    if accent and (len(accent) != 7 or accent[0] != "#" or
                   any(c not in "0123456789abcdefABCDEF" for c in accent[1:])):
        raise ValueError("Invalid accent color.")
    target = root / "lxqt/lxqt.conf"
    target.parent.mkdir(parents=True, exist_ok=True)
    original = target.read_bytes() if target.exists() else None
    if original is not None:
        folder = root / "edukasaun-welcome/backups"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        (folder / ("lxqt-" + stamp + ".conf")).write_bytes(original)
    try:
        settings = QSettings(str(target), QSettings.Format.IniFormat)
        if values.get("icons"):
            settings.setValue("icon_theme", values["icons"])
        if values.get("theme"):
            settings.setValue("theme", values["theme"])
        if accent:
            settings.setValue("Palette/highlight_color", accent)
        settings.sync()
        if settings.status() != QSettings.Status.NoError:
            raise OSError("Unable to save LXQt configuration.")
        # Release the serializer before restoring on failure.
        del settings
        if wallpaper:
            result = runner(["pcmanfm-qt", "--set-wallpaper", str(Path(wallpaper).resolve()),
                             "--wallpaper-mode", "zoom"], capture_output=True, text=True,
                            timeout=15, check=False)
            if result.returncode:
                raise RuntimeError(result.stderr or "Wallpaper command failed.")
    except Exception:
        if original is not None:
            target.write_bytes(original)
        else:
            target.unlink(missing_ok=True)
        raise


def open_tool(arguments):
    if not arguments or not shutil.which(arguments[0]):
        return False
    subprocess.Popen(arguments, start_new_session=True)
    return True
