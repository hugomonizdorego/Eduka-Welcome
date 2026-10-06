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
        self.assertEqual(settings["panel"]["transparency"], 0.5)
        self.assertEqual(settings["panel"]["theme_style"], eduka.THEME_DEFAULT)
        self.assertEqual(settings["panel"]["menu_label"], "Edukasaun")
        self.assertEqual(settings["desktop"]["width_percent"], 94)
        for panel, desktop, menu in (({"taskbar_style": "Huge"}, {}, {}), ({}, {"layout": "Tiles"}, {}),
                                     ({}, {"last_category": "Nope"}, {}), ({}, {}, {"language": "xx"})):
            with self.assertRaises(ValueError):
                eduka.save_settings(panel, desktop, menu, self.home)

    def test_new_0924_options(self):
        eduka.save_settings({"panel_style": "dock", "position": "Left", "clock_style": "led", "clock_format": "12h"},
                            {"theme_style": "Eduka-Low-Theme", "accent_color": "#2563eb", "multicolor": True,
                             "low_resource_mode": False, "tile_size": 150}, {"language": "tet"}, self.home)
        settings = eduka.read_settings(self.home)
        self.assertEqual(settings["panel"]["panel_style"], "dock")
        self.assertEqual(settings["panel"]["clock_format"], "12h")
        self.assertTrue(settings["desktop"]["low_resource_mode"])  # Eduka-Low always runs light.
        self.assertEqual(settings["menu"]["language"], "tet")
        for panel, desktop in (({"panel_style": "round"}, {}), ({"clock_format": "25h"}, {}),
                               ({}, {"accent_color": "green"}), ({}, {"tile_size": 999}),
                               ({}, {"wallpaper": {"mode": "spin"}})):
            with self.assertRaises(ValueError):
                eduka.save_settings(panel, desktop, {}, self.home)

    def test_wallpaper_keeps_existing_images_only(self):
        picture = self.home / "picture.png"
        picture.write_bytes(b"fixture")
        eduka.save_settings({}, {"wallpaper": {"images": [str(picture), "/missing.png"], "mode": "fit"}}, {},
                            self.home)
        wallpaper = eduka.read_settings(self.home)["desktop"]["wallpaper"]
        self.assertEqual(wallpaper["images"], [str(picture)])
        self.assertEqual(wallpaper["mode"], "fit")
        self.assertEqual(wallpaper["color"], "#1f6b45")

    def test_capabilities(self):
        meminfo = self.home / "meminfo"
        meminfo.write_text("MemTotal:        1000000 kB\n")
        with patch("os.cpu_count", return_value=4):
            self.assertFalse(eduka.glass_capability(meminfo)[2])
            meminfo.write_text("MemTotal:        2000000 kB\n")
            self.assertTrue(eduka.glass_capability(meminfo)[2])
            self.assertFalse(eduka.effects_capability(meminfo)[2])
            meminfo.write_text("MemTotal:        8000000 kB\n")
            self.assertTrue(eduka.effects_capability(meminfo)[2])

    def test_finish_uses_eduka_desktop_in_separate_process(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="Orca enabled\n", stderr="")
        with patch.object(eduka, "installed", return_value=True):
            self.assertEqual(eduka.finish_in_eduka("edukasaun-dark", True, True, runner), (True, "Orca enabled"))
        steps = json.loads(calls[0][-1])
        self.assertEqual(steps, {"theme": "Edukasaun-Dark", "orca": True, "wallpaper": True})
        self.assertEqual(calls[0][0], "python3")
        with patch.object(eduka, "installed", return_value=False):
            self.assertEqual(eduka.finish_in_eduka(None, None, False, runner), (True, ""))
        self.assertEqual(len(calls), 1)

    def test_installed_version(self):
        library = self.home / "lib"
        library.mkdir()
        (library / "eduka_common.py").write_text('VERSION = "0.9.24"\n')
        self.assertEqual(eduka.installed_version(library), "0.9.24")


if __name__ == "__main__":
    unittest.main()
