"""Read and write Eduka-Desktop Suite settings (Eduka-Desktop, Eduka-Panel, Eduka-Settings).

Mirrors the per-user JSON format of Eduka-Desktop 0.9.24 (`eduka_common.py`):
~/.config/eduka-desktop/{panel,desktop,menu}/settings.json. Saving merges into the
existing files. Afterwards `finish_in_eduka()` lets Eduka-Desktop's own code do what
Eduka-Settings does after saving (desktop theme, Qt palette, compositor, wallpaper,
Orca, reload signals). Eduka-Desktop uses PyQt5, so that code runs in a separate
process and is never imported here.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

EDUKA_VERSION = "0.9.24"
# Eduka-Desktop resets transparency once when this marker is missing, so keep it set.
SETTINGS_REVISION = "0.9.6-transparency"
EDUKA_LIBRARY = Path("/usr/lib/edukasaun-desktop")
START_ICON = "/usr/share/edukasaun-desktop/assets/StartMenu.png"
BACKGROUND_DIRS = [Path("/usr/share/Edukasaun/Backgrounds")]
LOGO_PATHS = [Path("/usr/share/Edukasaun/Logo/Edukasaun Logo.png")]

THEME_DEFAULT = "Eduka-Default-Theme"
THEME_LOW = "Eduka-Low-Theme"
THEME_LIQUID = "Liquid Glass"
THEME_DARK = "Edukasaun-Dark"
THEME_TRANSPARENT = "Eduka-Transparan"
THEME_MULTI = "Eduka-MultiColor"
THEMES = (THEME_DEFAULT, THEME_LOW, THEME_LIQUID, THEME_DARK, THEME_TRANSPARENT, THEME_MULTI)
GLASS_THEMES = (THEME_LIQUID, THEME_TRANSPARENT)
DARK_THEMES = (THEME_DARK, THEME_TRANSPARENT)
# (surface, panel, accent, text) as drawn by Eduka-Settings' theme previews.
THEME_SWATCHES = {
    THEME_DEFAULT: ("#f4faf7", "#ffffff", "#00a879", "#1f2d2a"),
    THEME_LOW: ("#f7f7f7", "#323030", "#315bef", "#3d3d3d"),
    THEME_LIQUID: ("#dcecf6", "#ffffff", "#1e9bd7", "#1c2b33"),
    THEME_DARK: ("#2c2c2c", "#212121", "#26a69a", "#ffffff"),
    THEME_TRANSPARENT: ("#1a1a1a", "#262626", "#d9d9d9", "#f2f2f2"),
    THEME_MULTI: ("#fafafa", "#ffffff", "#5b6ee1", "#212121"),
}
MULTI_COLORS = ("#ef5350", "#ff9800", "#f9a825", "#43a047", "#00acc1", "#1e88e5", "#5b6ee1", "#8e24aa",
                "#d81b60", "#00897b")
ACCENT_CHOICES = (
    ("", "Theme color"), ("#10b981", "Emerald"), ("#0d9488", "Teal"), ("#0891b2", "Cyan"),
    ("#0284c7", "Sky blue"), ("#2563eb", "Blue"), ("#4f46e5", "Indigo"), ("#7c3aed", "Violet"),
    ("#a21caf", "Purple"), ("#db2777", "Pink"), ("#e11d48", "Rose"), ("#dc2626", "Red"),
    ("#ea580c", "Orange"), ("#d97706", "Amber"), ("#65a30d", "Lime"), ("#92400e", "Brown"),
    ("#475569", "Slate"),
)
PANEL_STYLES = (("full", "Long"), ("floating", "Floating bar"), ("short", "Short"), ("dock", "Dock"))
PANEL_POSITIONS = ("Bottom", "Top", "Left", "Right")
CLOCK_STYLES = ("digital", "analog", "led")
SECTIONS = ("All", "Edukasaun", "Accessories", "Graphics", "Internet", "Office", "Programming",
            "Sound & Video", "System Tools", "Universal Access", "Preferences")
LAYOUTS = ("Grid", "List")
TASKBAR_STYLES = ("Icon and Text", "Icon only", "Text only")
EFFECT_HOVER = ("none", "wave", "glow", "slide", "pop", "bounce")
EFFECT_LAUNCH = ("none", "bubble", "zoom-in", "zoom-out", "ripple", "bounce", "confetti", "fade")
TILE_SIZES = (118, 132, 150)
COMPOSITORS = ("auto", "xrender", "glx", "wm", "off")
MENU_LANGUAGES = ("system", "tet")
WALLPAPER_MODES = ("zoom", "tile", "center", "fit", "stretch")

DEFAULT_PANEL = {
    "height": 42, "width_percent": 96, "position": "Bottom", "transparency": 0.54, "icon_size": 24,
    "menu_label": "Edukasaun", "menu_icon": START_ICON, "menu_icon_size": 26, "menu_icon_keep_aspect": True,
    "show_menu_text": True, "taskbar_style": "Icon and Text", "taskbar_icon_size": 22, "autohide": False,
    "locked": True, "enable_shadows": False, "low_resource_mode": True, "theme_style": THEME_DEFAULT,
    "clock_style": "digital", "clock_format": "24h", "clock_seconds": False, "clock_blink": False,
    "clock_color": "", "notify_seconds": 7, "notify_history": True, "reserve_workarea": True,
    "force_window_above_panel": True, "taskbar_max_button_width": 175, "taskbar_min_button_width": 46,
}
DEFAULT_MENU = {"mode": "Eduka-Desktop", "language": "system", "sddm_follow": True}
DEFAULT_DESKTOP = {
    "last_category": "Edukasaun", "layout": "Grid", "width_percent": 98, "height_percent": 92,
    "transparency": 0.51, "enable_shadows": False, "low_resource_mode": True, "theme_style": THEME_DEFAULT,
    "show_right_panel": True, "smooth_animations": False, "corner_radius": 24, "visual_accessibility": False,
    "hearing_accessibility": False, "orca_enabled": False, "glass_blur": False, "effects_enabled": False,
    "effect_hover": "wave", "effect_launch": "bubble", "effect_speed": 1.0, "effect_size": 1.0,
    "effect_random": False, "tile_size": 132, "accent_color": "", "compositor": "auto", "multicolor": False,
}
DEFAULT_WALLPAPER = {"images": [], "mode": "zoom", "color": "#1f6b45", "slideshow": False, "interval": 10,
                     "random": True, "transition": "normal", "extra": []}

# (key, minimum, maximum) as enforced by Eduka-Settings 0.9.24.
PANEL_RANGES = {"transparency": (0.50, 1.0), "height": (34, 58), "width_percent": (70, 100),
                "menu_icon_size": (16, 64)}
DESKTOP_RANGES = {"transparency": (0.45, 1.0), "width_percent": (94, 99), "height_percent": (78, 95)}
CHOICES = {
    "panel": {"taskbar_style": TASKBAR_STYLES, "position": PANEL_POSITIONS,
              "panel_style": tuple(k for k, _ in PANEL_STYLES), "clock_style": CLOCK_STYLES,
              "clock_format": ("24h", "12h")},
    "desktop": {"layout": LAYOUTS, "last_category": SECTIONS, "effect_hover": EFFECT_HOVER,
                "effect_launch": EFFECT_LAUNCH, "tile_size": TILE_SIZES, "compositor": COMPOSITORS},
    "menu": {"language": MENU_LANGUAGES},
}
COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def config_root(home=None):
    return (Path.home() if home is None else Path(home)) / ".config/eduka-desktop"


def runtime_dir():
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "eduka-desktop"


def installed():
    return (EDUKA_LIBRARY / "eduka_common.py").is_file()


def installed_version(library=EDUKA_LIBRARY):
    try:
        match = re.search(r'^VERSION\s*=\s*"([^"]+)"', (Path(library) / "eduka_common.py").read_text(), re.M)
        return match.group(1) if match else ""
    except OSError:
        return ""


def logo_path():
    return next((path for path in LOGO_PATHS if path.is_file()), None)


def normalize_theme(value):
    text = str(value or "").strip().casefold()
    return next((theme for theme in THEMES if theme.casefold() == text), THEME_DEFAULT)


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
    desktop = read_json(root / "desktop/settings.json", DEFAULT_DESKTOP)
    wallpaper = dict(DEFAULT_WALLPAPER)
    if isinstance(desktop.get("wallpaper"), dict):
        wallpaper.update({k: v for k, v in desktop["wallpaper"].items() if k in DEFAULT_WALLPAPER})
    desktop["wallpaper"] = wallpaper
    return {"panel": read_json(root / "panel/settings.json", DEFAULT_PANEL), "desktop": desktop,
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
    for name, values in (("panel", panel), ("desktop", desktop), ("menu", menu)):
        for key, allowed in CHOICES[name].items():
            if key in values and values[key] not in allowed:
                raise ValueError(f"Unknown value for {key}.")
    for key in ("accent_color",):
        if desktop.get(key) and not COLOR.fullmatch(str(desktop[key])):
            raise ValueError("Invalid accent color.")
    if panel.get("clock_color") and not COLOR.fullmatch(str(panel["clock_color"])):
        raise ValueError("Invalid clock color.")
    if "menu_label" in panel:
        panel["menu_label"] = str(panel["menu_label"]).strip()[:40] or "Edukasaun"
    if "menu_icon" in panel:
        panel["menu_icon"] = str(panel["menu_icon"]).strip() or START_ICON
    if desktop.get("theme_style") in GLASS_THEMES:
        desktop["low_resource_mode"] = False
    if desktop.get("theme_style") == THEME_LOW:
        desktop["low_resource_mode"] = True
    wallpaper = desktop.get("wallpaper")
    if wallpaper is not None:
        if not isinstance(wallpaper, dict) or wallpaper.get("mode", "zoom") not in WALLPAPER_MODES:
            raise ValueError("Invalid wallpaper settings.")
        if wallpaper.get("color") and not COLOR.fullmatch(str(wallpaper["color"])):
            raise ValueError("Invalid wallpaper color.")
        wallpaper["images"] = [str(path) for path in wallpaper.get("images", []) if Path(str(path)).is_file()]


def save_settings(panel, desktop, menu, home=None):
    """Merge into Eduka-Desktop's files and ask running components to reload."""
    panel, desktop, menu = dict(panel), dict(desktop), dict(menu)
    validate(panel, desktop, menu)
    root = config_root(home)
    current = read_settings(home)
    if "wallpaper" in desktop:
        merged_wallpaper = current["desktop"]["wallpaper"]
        merged_wallpaper.update(desktop["wallpaper"])
        desktop["wallpaper"] = merged_wallpaper
    for name, values in (("panel", panel), ("desktop", desktop), ("menu", menu)):
        merged = current[name]
        merged.update(values)
        if name in ("panel", "desktop"):
            merged["_settings_revision"] = SETTINGS_REVISION
        write_json(root / name / "settings.json", merged)
    signal_reload()


def signal_reload(folder=None):
    """Same signals as Eduka-Settings: touch `reload`, send `reload-style`."""
    folder = runtime_dir() if folder is None else Path(folder)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "reload").write_text(str(time.time()))
        write_json(folder / "menu-command.json",
                   {"action": "reload-style", "time": time.time(), "id": int(time.time() * 1000)})
    except OSError:
        pass  # Eduka-Desktop is not running yet; it reads the files at startup.


def memory_gib(meminfo="/proc/meminfo"):
    try:
        for line in Path(meminfo).read_text().splitlines():
            if line.startswith("MemTotal:"):
                return float(line.split()[1]) / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def glass_capability(meminfo="/proc/meminfo"):
    """Eduka-Settings 0.9.24: glass themes need about 2 GB RAM and two CPU threads."""
    memory, threads = memory_gib(meminfo), max(1, os.cpu_count() or 1)
    return memory, threads, memory >= 1.8 and threads >= 2


def effects_capability(meminfo="/proc/meminfo"):
    """Animated effects need 4 GB RAM (about 3.5 GiB usable) and four CPU threads."""
    memory, threads = memory_gib(meminfo), max(1, os.cpu_count() or 1)
    return memory, threads, memory >= 3.5 and threads >= 4


def background_images(folders=None):
    images = []
    for folder in folders or BACKGROUND_DIRS:
        if Path(folder).is_dir():
            images.extend(sorted(path for path in Path(folder).iterdir()
                                 if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg")))
    return images


# Runs inside Eduka-Desktop's own Python (PyQt5) with only whitelisted steps.
FINISH_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
steps = json.loads(sys.argv[2])
import eduka_common as ec
notes, ok = [], True
def run(name, call):
    global ok
    try:
        result = call()
        if isinstance(result, tuple):
            if not result[0]:
                ok = False
            if result[1]:
                notes.append(str(result[1]))
    except Exception as error:
        ok = False
        notes.append(name + ": " + str(error))
if steps.get("theme"):
    run("theme", lambda: ec.apply_desktop_theme(steps["theme"]))
run("palette", ec.repair_qt_palette)
if steps.get("orca") is not None:
    run("orca", lambda: ec.configure_orca(bool(steps["orca"])))
if steps.get("wallpaper"):
    def wallpaper():
        import eduka_wallpaper
        eduka_wallpaper.apply_wallpaper()
    run("wallpaper", wallpaper)
if hasattr(ec, "ensure_compositor"):
    run("compositor", ec.ensure_compositor)
run("reload", lambda: (ec.touch_reload(), ec.send_menu_command("reload-style")) and None)
print("\n".join(notes))
sys.stdout.flush()
ec.exit_now(0 if ok else 1) if hasattr(ec, "exit_now") else sys.exit(0 if ok else 1)
"""


def finish_in_eduka(theme=None, orca=None, wallpaper=False, runner=subprocess.run):
    """Let Eduka-Desktop apply the saved settings with its own functions."""
    if not installed():
        return True, ""
    steps = {"theme": normalize_theme(theme) if theme else None, "orca": orca, "wallpaper": bool(wallpaper)}
    try:
        result = runner(["python3", "-c", FINISH_SCRIPT, str(EDUKA_LIBRARY), json.dumps(steps)],
                        capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    return result.returncode == 0, (result.stdout or result.stderr).strip()
