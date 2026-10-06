"""Per-user preferences and freedesktop autostart opt-out."""
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
    autostart = root / "autostart/edukasaun-welcome.desktop"
    autostart.parent.mkdir(parents=True, exist_ok=True)
    autostart.write_text("[Desktop Entry]\nType=Application\nName=Edukasaun Welcome\n"
                         "Exec=edukasaun-welcome --autostart\nIcon=edukasaun-welcome\n"
                         "OnlyShowIn=LXQt;\nHidden=" +
                         ("false" if values.get("always_show", True) else "true") + "\n", encoding="utf-8")
