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
    from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox
    from edukasaun_welcome.desktop import apply_desktop, current_settings
    from edukasaun_welcome.gui import WelcomeWindow
    from edukasaun_welcome.eduka_desktop import read_settings, save_settings
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

    def test_six_pages_navigation(self):
        self.assertEqual(self.window.stack.count(), 7)
        self.assertTrue(self.window.always.isChecked())
        self.assertFalse(self.window.back_button.isEnabled())
        self.assertEqual(self.window.counter.text(), "Step 1 of 7")
        self.window.navigate(4)
        self.assertEqual(self.window.next_button.text(), "Next")
        self.window.navigate(6)
        self.assertEqual(self.window.next_button.text(), "Finish")
        session = WelcomeWindow("en", {}, auto_scan=False, session=True)
        session.navigate(6)
        self.assertEqual(session.next_button.text(), "Start Eduka-Desktop")
        session.deleteLater()

    def test_no_version_number_in_interface(self):
        from edukasaun_welcome import __version__
        texts = [widget.text() for widget in self.window.findChildren(QLabel)]
        self.assertFalse([text for text in texts if __version__ in text])

    def test_timezone_starts_from_dili_and_filters(self):
        self.assertEqual(self.window.zone_combo.itemData(0), "Asia/Dili")
        self.assertEqual(self.window.selected_timezone(), "Asia/Dili")
        self.assertIn("Timor-Leste", self.window.zone_combo.itemText(0))
        self.window.zone_search.setText("lisbon")
        self.assertEqual(self.window.selected_timezone(), "Europe/Lisbon")
        self.window.zone_search.setText("")
        self.assertEqual(self.window.zone_combo.itemData(0), "Asia/Dili")
        self.window.zone_search.setText("no-such-zone")
        self.assertIsNone(self.window.selected_timezone())

    def test_github_link_and_sponsor_placeholders(self):
        self.assertEqual(self.window.project["github"], "https://github.com/hugomonizdorego")
        sponsors = self.window.stack.widget(5).widget()
        texts = [widget.text() for widget in sponsors.findChildren(QLabel)]
        self.assertIn("Your logo here", texts)

    def test_eduka_desktop_settings_saved_in_eduka_format(self):
        home = Path(self.folder.name)
        with patch("pathlib.Path.home", return_value=home), \
                patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(home / "run")}):
            self.window.panel_height.setValue(50)
            self.window.panel_transparency.setValue(80)
            self.window.menu_label.setText("Eskola")
            self.window.desktop_layout.setCurrentIndex(self.window.desktop_layout.findData("List"))
            self.window.vision.setChecked(True)
            panel, desktop, menu = self.window.eduka_values()
            save_settings(panel, desktop, menu)
            saved = read_settings()
            self.assertTrue((home / "run/eduka-desktop/reload").is_file())
        self.assertEqual(saved["panel"]["height"], 50)
        self.assertEqual(saved["panel"]["transparency"], 0.8)
        self.assertEqual(saved["panel"]["menu_label"], "Eskola")
        self.assertEqual(saved["desktop"]["layout"], "List")
        self.assertTrue(saved["desktop"]["visual_accessibility"])
        self.assertEqual(saved["panel"]["_settings_revision"], "0.9.6-transparency")

    def test_liquid_glass_refused_on_weak_hardware(self):
        index = self.window.visual_theme.findData("Liquid Glass")
        with patch("edukasaun_welcome.gui.liquid_glass_capability", return_value=(1.0, 1, False)), \
                patch.object(QMessageBox, "warning") as warning:
            self.window.visual_theme.setCurrentIndex(index)
            warning.assert_called_once()
        self.assertEqual(self.window.visual_theme.currentData(), "Eduka-Default-Theme")
        with patch("edukasaun_welcome.gui.liquid_glass_capability", return_value=(8.0, 4, True)), \
                patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.visual_theme.setCurrentIndex(index)
        self.assertEqual(self.window.visual_theme.currentData(), "Liquid Glass")
        self.assertFalse(self.window.low_resource.isEnabled())

    def test_sponsor_entries(self):
        from edukasaun_welcome.gui import sponsor_entry
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "logo.png").write_bytes(b"fixture")
            entry = sponsor_entry({"name": "Fixture", "logo": "../../logo.png", "url": "https://example.org"},
                                  [Path(folder)])
            self.assertEqual(entry["logo"], Path(folder) / "logo.png")
            self.assertEqual(sponsor_entry({"name": "X", "url": "http://insecure"})["url"], "")
            self.assertEqual(sponsor_entry("Plain name")["name"], "Plain name")
            self.assertIsNone(sponsor_entry({"logo": "a.png"}))
            self.assertIsNone(sponsor_entry({"name": "Y", "logo": "a.sh"}, [Path(folder)])["logo"])

    def test_clock_format_is_saved(self):
        self.window.clock_format.setCurrentIndex(1)
        self.assertFalse(self.window.preferences["clock_24h"])
        self.assertRegex(self.window.clock_label.text(), r"(AM|PM)$")

    def test_session_close_starts_desktop(self):
        session = WelcomeWindow("en", {}, auto_scan=False, session=True)
        with patch("edukasaun_welcome.gui.start_desktop") as start:
            session.close()
            start.assert_called_once_with(session.project["eduka_desktop"])
        with patch("edukasaun_welcome.gui.start_desktop") as start:
            self.window.close()
            start.assert_not_called()
        session.deleteLater()

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
        for command, expected in [(["/bin/true"], True), (["/bin/false"], False), (["/nonexistent/fixture-command"], False)]:
            self.window.run_commands([command], self.window.log, outcome.append)
            deadline = time.monotonic() + 3
            while self.window.process and time.monotonic() < deadline:
                self.application.processEvents()
                time.sleep(0.005)
            self.assertEqual(outcome[-1], expected)
        self.assertIsNone(self.window.process)

    def test_live_process_output_is_read(self):
        self.window.run_commands([["/bin/echo", "fixture-output"]], self.window.log, lambda success: None)
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
