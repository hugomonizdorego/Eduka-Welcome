"""Render native review images with fixture data; never scan or install packages."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font.db=false")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PyQt6.QtWidgets import QApplication
from edukasaun_welcome.catalog import load_catalog
from edukasaun_welcome.gui import WelcomeWindow

original_read = Path.read_text
# Previews must look the same on any machine: fixed system time zone.
import edukasaun_welcome.gui as gui
gui.current_timezone = lambda: "Etc/UTC"


def fixture_read(path, *args, **kwargs):
    if str(path) == "/etc/os-release":
        return 'PRETTY_NAME="Edukasaun OS 1.0 (Kameli)"\n'
    return original_read(path, *args, **kwargs)


with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_CONFIG_HOME": folder}), patch.object(Path, "read_text", fixture_read):
    application = QApplication([])
    window = WelcomeWindow("en", {}, auto_scan=False, session=True)
    window.apps = load_catalog()["apps"]
    window.scanned = True
    window.availability = {app["id"]: True for app in window.apps}
    window.populate_apps()
    window.show()
    application.processEvents()
    for page in range(6):
        window.navigate(page)
        application.processEvents()
        window.grab().save(str(ROOT / "docs" / f"page-{page + 1}.png"))
    window.navigate(0)
    application.processEvents()
    window.grab().save(str(ROOT / "docs/welcome-preview.png"))
    window.close()
