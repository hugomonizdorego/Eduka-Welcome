import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from edukasaun_welcome import eduka_desktop as eduka


class EdukaDesktopSettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.home = Path(self.folder.name)
        self.runtime = patch.dict("os.environ", {"XDG_RUNTIME_DIR": str(self.home / "run")})
        self.runtime.start()

    def tearDown(self):
        self.runtime.stop()
        self.folder.cleanup()

    def test_defaults_when_missing(self):
        settings = eduka.read_settings(self.home)
        self.assertEqual(settings["panel"]["transparency"], 0.54)
        self.assertEqual(settings["desktop"]["layout"], "Grid")
        self.assertEqual(settings["menu"]["mode"], "Eduka-Desktop")

    def test_merge_preserves_unknown_keys_and_signals_reload(self):
        path = self.home / ".config/eduka-desktop/panel/settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"future_option": 7, "height": 40}))
        eduka.save_settings({"height": 50}, {"layout": "List"}, {}, self.home)
        panel = json.loads(path.read_text())
        self.assertEqual(panel["future_option"], 7)
        self.assertEqual(panel["height"], 50)
        self.assertEqual(panel["_settings_revision"], eduka.SETTINGS_REVISION)
        command = json.loads((self.home / "run/eduka-desktop/menu-command.json").read_text())
        self.assertEqual(command["action"], "reload-style")
        self.assertTrue((self.home / "run/eduka-desktop/reload").is_file())

    def test_values_are_clamped_and_validated(self):
        eduka.save_settings({"height": 999, "transparency": 0.1, "theme_style": "old glass",
                             "menu_label": "  "}, {"width_percent": 10}, {}, self.home)
        settings = eduka.read_settings(self.home)
        self.assertEqual(settings["panel"]["height"], 58)
        self.assertEqual(settings["panel"]["transparency"], 0.45)
        self.assertEqual(settings["panel"]["theme_style"], eduka.THEME_DEFAULT)
        self.assertEqual(settings["panel"]["menu_label"], "Edukasaun")
        self.assertEqual(settings["desktop"]["width_percent"], 92)
        for panel, desktop, menu in (({"taskbar_style": "Huge"}, {}, {}), ({}, {"layout": "Tiles"}, {}),
                                     ({}, {"last_category": "Nope"}, {}), ({}, {}, {"language": "xx"})):
            with self.assertRaises(ValueError):
                eduka.save_settings(panel, desktop, menu, self.home)

    def test_liquid_glass_capability(self):
        meminfo = self.home / "meminfo"
        meminfo.write_text("MemTotal:        2000000 kB\n")
        self.assertFalse(eduka.liquid_glass_capability(meminfo)[2])
        meminfo.write_text("MemTotal:        8000000 kB\n")
        with patch("os.cpu_count", return_value=4):
            self.assertTrue(eduka.liquid_glass_capability(meminfo)[2])

    def test_orca_uses_eduka_desktop_in_separate_process(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="Orca enabled\n", stderr="")
        with patch.object(eduka, "installed", return_value=True):
            self.assertEqual(eduka.configure_orca(True, runner), (True, "Orca enabled"))
        self.assertEqual(calls[0][0], "python3")
        self.assertEqual(calls[0][-1], "1")
        with patch.object(eduka, "installed", return_value=False):
            self.assertFalse(eduka.configure_orca(True, runner)[0])


if __name__ == "__main__":
    unittest.main()
