"""Read and write Eduka-Desktop Suite settings (Eduka-Desktop, Eduka-Panel, Eduka-Menu).

Mirrors the per-user JSON format of Eduka-Desktop 0.9.10 (`eduka_common.py`):
~/.config/eduka-desktop/{panel,desktop,menu}/settings.json. Saving merges into the
existing files, then signals running Eduka-Panel and Eduka-Desktop to reload, exactly
like Eduka-Menu-Settings. Eduka-Desktop itself uses PyQt5, so it is never imported here.
"""
import json
import os
import subprocess
import time
from pathlib import Path

# Eduka-Desktop resets transparency once when this marker is missing, so keep it set.
SETTINGS_REVISION = "0.9.6-transparency"
THEME_DEFAULT = "Eduka-Default-Theme"
THEME_LIQUID = "Liquid Glass"
THEMES = (THEME_DEFAULT, THEME_LIQUID)
START_ICON = "/usr/share/edukasaun-desktop/assets/StartMenu.png"
EDUKA_LIBRARY = Path("/usr/lib/edukasaun-desktop")
SECTIONS = ("All", "Edukasaun", "Accessories", "Graphics", "Internet", "Office", "Programming",
            "Sound & Video", "System Tools", "Universal Access", "Preferences")
LAYOUTS = ("Grid", "List")
TASKBAR_STYLES = ("Icon and Text", "Icon only", "Text only")

DEFAULT_PANEL = {
    "height": 42, "width_percent": 96, "position": "Bottom", "transparency": 0.54, "icon_size": 24,
    "menu_label": "Edukasaun", "menu_icon": START_ICON, "menu_icon_size": 26, "show_menu_text": True,
    "taskbar_style": "Icon and Text", "taskbar_icon_size": 22, "autohide": False, "locked": True,
    "enable_shadows": False, "low_resource_mode": True, "theme_style": THEME_DEFAULT,
    "reserve_workarea": True, "force_window_above_panel": True,
    "taskbar_max_button_width": 175, "taskbar_min_button_width": 46,
}
DEFAULT_MENU = {"mode": "Eduka-Desktop", "language": "system"}
DEFAULT_DESKTOP = {
    "last_category": "Edukasaun", "layout": "Grid", "width_percent": 98, "height_percent": 92,
    "transparency": 0.51, "enable_shadows": False, "low_resource_mode": True,
    "theme_style": THEME_DEFAULT, "show_right_panel": True, "smooth_animations": False,
    "corner_radius": 24, "visual_accessibility": False, "hearing_accessibility": False,
    "orca_enabled": False,
}

# (key, minimum, maximum) as enforced by Eduka-Menu-Settings.
PANEL_RANGES = {"transparency": (0.45, 1.0), "height": (34, 58), "width_percent": (70, 100),
                "menu_icon_size": (18, 48)}
DESKTOP_RANGES = {"transparency": (0.45, 1.0), "width_percent": (92, 99), "height_percent": (78, 95)}


def config_root(home=None):
    return (Path.home() if home is None else Path(home)) / ".config/eduka-desktop"


def runtime_dir():
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "eduka-desktop"


def installed():
    return (EDUKA_LIBRARY / "eduka_common.py").is_file()


def normalize_theme(value):
    return THEME_LIQUID if str(value or "").strip().casefold() == THEME_LIQUID.casefold() else THEME_DEFAULT


def read_json(path, default):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Not a settings object")
    except (OSError, ValueError):
        data = {}
    merged = dict(default)
    merged.update(data)
    return merged


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def read_settings(home=None):
    root = config_root(home)
    return {"panel": read_json(root / "panel/settings.json", DEFAULT_PANEL),
            "desktop": read_json(root / "desktop/settings.json", DEFAULT_DESKTOP),
            "menu": read_json(root / "menu/settings.json", DEFAULT_MENU)}


def clamp(values, ranges):
    for key, (low, high) in ranges.items():
        if key in values:
            kind = float if isinstance(low, float) else int
            values[key] = kind(min(high, max(low, kind(values[key]))))


def validate(panel, desktop, menu):
    for values in (panel, desktop):
        if "theme_style" in values:
            values["theme_style"] = normalize_theme(values["theme_style"])
    clamp(panel, PANEL_RANGES)
    clamp(desktop, DESKTOP_RANGES)
    if panel.get("taskbar_style", TASKBAR_STYLES[0]) not in TASKBAR_STYLES:
        raise ValueError("Unknown taskbar style.")
    if desktop.get("layout", LAYOUTS[0]) not in LAYOUTS:
        raise ValueError("Unknown layout.")
    if desktop.get("last_category", SECTIONS[1]) not in SECTIONS:
        raise ValueError("Unknown default section.")
    if menu.get("language", "system") not in ("system", "en"):
        raise ValueError("Unknown menu language.")
    if "menu_label" in panel:
        panel["menu_label"] = str(panel["menu_label"]).strip()[:40] or "Edukasaun"
    if "menu_icon" in panel:
        panel["menu_icon"] = str(panel["menu_icon"]).strip() or START_ICON


def save_settings(panel, desktop, menu, home=None):
    """Merge into Eduka-Desktop's files and ask running components to reload."""
    panel, desktop, menu = dict(panel), dict(desktop), dict(menu)
    validate(panel, desktop, menu)
    root = config_root(home)
    current = read_settings(home)
    for name, values in (("panel", panel), ("desktop", desktop), ("menu", menu)):
        merged = current[name]
        merged.update(values)
        if name in ("panel", "desktop"):
            merged["_settings_revision"] = SETTINGS_REVISION
        write_json(root / name / "settings.json", merged)
    signal_reload()


def signal_reload(folder=None):
    """Same signals as Eduka-Menu-Settings: touch `reload`, send `reload-style`."""
    folder = runtime_dir() if folder is None else Path(folder)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "reload").write_text(str(time.time()))
        write_json(folder / "menu-command.json",
                   {"action": "reload-style", "time": time.time(), "id": int(time.time() * 1000)})
    except OSError:
        pass  # Eduka-Desktop is not running yet; it reads the files at startup.


def liquid_glass_capability(meminfo="/proc/meminfo"):
    """Eduka-Menu-Settings requires about 4 GB RAM and two CPU threads for Liquid Glass."""
    memory = 0.0
    try:
        for line in Path(meminfo).read_text().splitlines():
            if line.startswith("MemTotal:"):
                memory = float(line.split()[1]) / (1024 * 1024)
                break
    except (OSError, ValueError, IndexError):
        pass
    threads = max(1, os.cpu_count() or 1)
    return memory, threads, memory >= 3.7 and threads >= 2


def configure_orca(enabled, runner=subprocess.run):
    """Use Eduka-Desktop's own Orca integration in a separate (PyQt5) process."""
    if not installed():
        return False, "Eduka-Desktop is not installed."
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from eduka_common import configure_orca; "
            "ok, message = configure_orca(sys.argv[2] == '1'); print(message); sys.exit(0 if ok else 1)")
    try:
        result = runner(["python3", "-c", code, str(EDUKA_LIBRARY), "1" if enabled else "0"],
                        capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    return result.returncode == 0, (result.stdout or result.stderr).strip()
