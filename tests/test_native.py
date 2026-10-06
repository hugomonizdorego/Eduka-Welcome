import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font.db=false")
try:
    from PyQt6.QtCore import QSettings, Qt
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from edukasaun_welcome.desktop import apply_desktop, current_settings
    from edukasaun_welcome.gui import WelcomeWindow
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
from edukasaun_welcome.catalog import load_catalog
from edukasaun_welcome.inventory import Inventory


@unittest.skipUnless(QT_AVAILABLE, "Install python3-pyqt6 for native UI checks")
class DesktopTests(unittest.TestCase):
    def test_unrelated_settings_preserved_and_backed_up(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "LXQt"}):
            root = Path(folder)
            path = root / "lxqt/lxqt.conf"
            path.parent.mkdir()
            original = b"[General]\nunrelated=keep\n[Custom]\nvalue=42\n"
            path.write_bytes(original)
            apply_desktop({"accent": "#33aaff"}, root)
            settings = QSettings(str(path), QSettings.Format.IniFormat)
            self.assertEqual(settings.value("unrelated"), "keep")
            self.assertEqual(settings.value("Custom/value"), "42")
            self.assertEqual(settings.value("Palette/highlight_color"), "#33aaff")
            self.assertEqual(next((root / "edukasaun-welcome/backups").iterdir()).read_bytes(), original)

    def test_rollback_after_wallpaper_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "LXQt"}), patch("shutil.which", return_value="/usr/bin/pcmanfm-qt"):
            root = Path(folder)
            path = root / "lxqt/lxqt.conf"
            path.parent.mkdir()
            original = b"[General]\nkeep=me\n"
            path.write_bytes(original)
            wallpaper = root / "test.png"
            wallpaper.write_bytes(b"fixture")
            with self.assertRaises(RuntimeError):
                apply_desktop({"accent": "#123456", "wallpaper": str(wallpaper)}, root,
                              lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="failed"))
            self.assertEqual(path.read_bytes(), original)

    def test_no_uninstalled_theme_or_non_lxqt_write(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}):
            with self.assertRaises(RuntimeError):
                apply_desktop({}, folder)
            self.assertFalse((Path(folder) / "lxqt/lxqt.conf").exists())
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "LXQt"}), patch("edukasaun_welcome.desktop.theme_choices", return_value=[]):
            with self.assertRaises(ValueError):
                apply_desktop({"theme": "missing"}, folder)
            self.assertFalse((Path(folder) / "lxqt/lxqt.conf").exists())


@unittest.skipUnless(QT_AVAILABLE, "Install python3-pyqt6 for native UI checks")
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"XDG_CONFIG_HOME": self.folder.name})
        self.environment.start()
        self.window = WelcomeWindow("en", {}, auto_scan=False)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.application.processEvents()
        self.environment.stop()
        self.folder.cleanup()

    def fixture_apps(self):
        self.window.apps = load_catalog()["apps"]
        self.window.availability = {app["id"]: True for app in self.window.apps}
        self.window.scanned = True
        self.window.populate_apps()

    def test_six_pages_navigation_and_locale_switch(self):
        self.assertEqual(self.window.stack.count(), 6)
        self.assertTrue(self.window.always.isChecked())
        self.assertFalse(self.window.back_button.isEnabled())
        self.window.navigate(5)
        self.assertEqual(self.window.next_button.text(), "Close")
        self.window.locale_combo.setCurrentIndex(self.window.locale_combo.findData("tet"))
        self.assertEqual(self.window.stack.currentIndex(), 5)
        self.assertEqual(self.window.windowTitle(), "Edukasaun Benvindu")
        self.assertEqual(self.window.next_button.text(), "Taka")

    def test_selection_maps_to_catalog_and_clear_on_filter(self):
        self.fixture_apps()
        self.window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(self.window.selected_apps()[0]["id"], "chromium")
        self.window.category_combo.setCurrentIndex(self.window.category_combo.findData("educationGames"))
        self.assertEqual(self.window.selected_apps(), [])

    def test_inventory_error_disables_installation(self):
        self.fixture_apps()
        self.window.inventory.errors = ["fixture failure"]
        self.window.populate_apps()
        self.assertFalse(self.window.install_button.isEnabled())

    def test_unavailable_apt_item_is_disabled(self):
        self.fixture_apps()
        self.window.availability["chromium"] = False
        self.window.populate_apps()
        self.assertFalse(self.window.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEnabled)

    def test_qprocess_success_and_failure(self):
        outcome = []
        self.window.finish_install = lambda success: outcome.append(success)
        for command, expected in [(["/bin/true"], True), (["/bin/false"], False), (["/nonexistent/fixture-command"], False)]:
            self.window.commands = [command]
            self.window.run_next_command()
            deadline = time.monotonic() + 3
            while self.window.process and time.monotonic() < deadline:
                self.application.processEvents()
                time.sleep(0.005)
            self.assertEqual(outcome[-1], expected)
        self.assertIsNone(self.window.process)

    def test_live_process_output_is_read(self):
        self.window.finish_install = lambda success: None
        self.window.commands = [["/bin/echo", "fixture-output"]]
        self.window.run_next_command()
        deadline = time.monotonic() + 3
        while self.window.process and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(0.005)
        self.assertIn("fixture-output", self.window.log.toPlainText())

    def test_preflight_rejects_changed_inventory(self):
        self.fixture_apps()
        self.window.pending = (["chromium"], "apt")
        self.window.apps = [app for app in self.window.apps if app["id"] != "chromium"]
        worker = SimpleNamespace(deleteLater=lambda: None)
        self.window.worker = worker
        with patch.object(self.window, "begin_install") as install:
            self.window.worker_finished()
            install.assert_not_called()
        self.assertIn("inventory changed", self.window.message.text())

    def test_missing_english_message_keys(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "edukasaun_welcome/gui.py").read_text()
        keys = set(re.findall(r'self\.t\("([a-zA-Z]+)"', source))
        messages = json.loads((root / "edukasaun_welcome/locales/en.json").read_text())
        self.assertFalse(keys - set(messages))


if __name__ == "__main__":
    unittest.main()
