"""Per-user preferences; the session gate reads them instead of hiding autostart."""
import json
import os
from pathlib import Path


def config_home():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def load_preferences():
    try:
        return json.loads((config_home() / "edukasaun-welcome/preferences.json").read_text())
    except (OSError, ValueError):
        return {}


def save_preferences(values, root=None):
    root = config_home() if root is None else Path(root)
    path = root / "edukasaun-welcome/preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    # Earlier development builds hid the autostart entry per user. The autostart entry
    # now also starts Eduka-Desktop, so it must never be hidden.
    legacy = root / "autostart/edukasaun-welcome.desktop"
    try:
        if "edukasaun-welcome --autostart" in legacy.read_text(encoding="utf-8"):
            legacy.unlink()
    except OSError:
        pass
