import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from edukasaun_welcome.catalog import load_catalog, recommendations, install_commands
from edukasaun_welcome.i18n import Translator, system_language, LOCALES, SUPPORTED
from edukasaun_welcome.inventory import (
    Inventory, apt_available, parse_dpkg, read_desktop_entries, scan_inventory,
)
from edukasaun_welcome.preferences import save_preferences

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("admin_helper", ROOT / "packaging/admin_helper.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class LocaleTests(unittest.TestCase):
    def test_locale_precedence_and_tetun(self):
        self.assertEqual(system_language({"LANG": "id_ID.UTF-8", "LC_MESSAGES": "pt_BR.UTF-8"}), "pt")
        self.assertEqual(system_language({"LC_ALL": "tet_TL.UTF-8", "LC_MESSAGES": "id_ID"}), "tet")
        self.assertEqual(system_language({"LANG": "pt-PT"}), "pt")
        self.assertEqual(system_language({"LANG": "id_ID", "LANGUAGE": "de:tet:en"}), "tet")

    def test_english_fallback_and_c_locale(self):
        self.assertEqual(system_language({"LANG": "ja_JP"}), "en")
        self.assertEqual(system_language({"LANG": "C.UTF-8", "LANGUAGE": "pt"}), "en")
        self.assertEqual(system_language({}), "en")
        self.assertEqual(Translator("unknown")("next"), "Next")

    def test_translations_are_optional_subsets(self):
        # English is the development UI; other dictionaries may lag behind and fall back to English.
        english = json.loads((LOCALES / "en.json").read_text())
        for language in SUPPORTED:
            messages = json.loads((LOCALES / (language + ".json")).read_text())
            self.assertFalse(set(messages) - set(english))
            self.assertIn("3", Translator(language)("scanResult", count=3))
            self.assertEqual(Translator(language)("stepCounter", current=2, total=6),
                             messages.get("stepCounter", english["stepCounter"]).format(current=2, total=6))
            self.assertTrue(all(isinstance(value, str) and value for value in messages.values()))


class InventoryTests(unittest.TestCase):
    def test_dpkg_status_and_multiarch(self):
        data = "vlc:amd64\tinstalled\nold-app\tconfig-files\nbroken\tunpacked\nchromium\tinstalled\n"
        self.assertEqual(parse_dpkg(data), {"vlc", "chromium"})

    def test_scan_both_flatpak_scopes(self):
        seen = []
        def run(command):
            seen.append(command)
            if command[0] == "dpkg-query":
                return "libreoffice-writer\tinstalled\n"
            return "org.gnome.Chess\n" if "--user" in command else "org.chromium.Chromium\n"
        with tempfile.TemporaryDirectory() as folder, patch("shutil.which", return_value="/bin/flatpak"):
            inventory = scan_inventory(folder, run)
        self.assertEqual(inventory.flatpaks, {"org.gnome.Chess", "org.chromium.Chromium"})
        self.assertTrue(any("--system" in command for command in seen))
        self.assertIn("libreoffice-writer", inventory.packages)
        self.assertEqual(inventory.errors, [])

    def test_failure_is_reported(self):
        def fail(command):
            raise RuntimeError("unavailable")
        with tempfile.TemporaryDirectory() as folder, patch("shutil.which", return_value=None):
            inventory = scan_inventory(folder, fail)
        self.assertTrue(inventory.errors)

    def test_desktop_entry_and_hidden_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "custom-chess.desktop").write_text('[Desktop Entry]\nExec="/opt/apps/gnome-chess" %U\n')
            (root / "hidden.desktop").write_text('[Desktop Entry]\nHidden=true\nExec=absent\n')
            inventory = Inventory()
            read_desktop_entries(inventory, [root])
            self.assertEqual(inventory.executables, {"gnome-chess"})
            self.assertEqual(inventory.desktop_ids, {"custom-chess"})

    def test_available_candidate(self):
        self.assertTrue(apt_available("chromium", lambda command: "Candidate: 1.0\n"))
        self.assertFalse(apt_available("chromium", lambda command: "Candidate: (none)\n"))
        self.assertFalse(apt_available("chromium", lambda command: ""))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = load_catalog()
        self.apps = {app["id"]: app for app in self.data["apps"]}

    def test_shipped_baseline_and_alternatives(self):
        self.assertEqual(len(self.data["shipped_families"]), 58)
        self.assertEqual(len(self.apps), 38)
        self.assertIn("gnome-chess", self.apps)
        self.assertFalse(set(self.apps).intersection(self.data["shipped_families"]))
        future = json.loads(json.dumps(self.data))
        future["apps"].append({"id": "vlc", "detect": {}})
        with patch("shutil.which", return_value=None):
            self.assertNotIn("vlc", [app["id"] for app in recommendations(Inventory(), future)])

    def test_cross_source_and_component_exclusion(self):
        inventory = Inventory(packages={"libreoffice-writer", "chromium-browser"},
                              flatpaks={"org.gnome.Chess", "com.brave.Browser"})
        with patch("shutil.which", return_value=None):
            remaining = {app["id"] for app in recommendations(inventory)}
        self.assertFalse(remaining.intersection({"libreoffice", "chromium", "gnome-chess", "brave"}))
        self.assertIn("xournalpp", remaining)

    def test_path_and_desktop_alias_detection(self):
        inventory = Inventory(desktop_ids={"com.github.xournalpp.xournalpp"}, executables={"obs"})
        with patch("shutil.which", side_effect=lambda name: "/bin/ghb" if name == "ghb" else None):
            remaining = {app["id"] for app in recommendations(inventory)}
        self.assertFalse(remaining.intersection({"xournalpp", "obs-studio", "handbrake"}))

    def test_apt_argument_vectors(self):
        commands = install_commands([self.apps["chromium"]], "apt")
        self.assertEqual(commands, [["pkexec", "/usr/lib/edukasaun-welcome/admin-helper", "apt", "chromium"]])
        self.assertEqual(helper.validated_packages("apt", ["chromium"], self.data), ["chromium"])

    def test_flatpak_user_scope_and_preflight(self):
        commands = install_commands([self.apps["gnome-chess"]], "flatpak", add_remote=True)
        self.assertEqual(commands[0][1], "remote-add")
        self.assertEqual(commands[1][1], "remote-info")
        self.assertEqual(commands[-1][-1], "org.gnome.Chess")
        self.assertTrue(all("--user" in command for command in commands))

    def test_brave_requires_consent(self):
        with self.assertRaises(ValueError):
            install_commands([self.apps["brave"]], "brave")
        self.assertEqual(install_commands([self.apps["brave"]], "brave", add_brave=True)[0][-2:], ["brave", "brave"])

    def test_reject_arbitrary_ids_packages_and_commands(self):
        for ids in (["--allow-unauthenticated"], ["chromium;reboot"], ["vlc"], ["chromium", "chromium"]):
            with self.assertRaises(ValueError):
                helper.validated_packages("apt", ids, self.data)
        modified = json.loads(json.dumps(self.apps["chromium"]))
        modified["sources"]["apt"] = "bad;command"
        with self.assertRaises(ValueError):
            install_commands([modified], "apt")
        with self.assertRaises(ValueError):
            install_commands([], "apt")

    def test_helpers_refuse_untrusted_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "unsafe.json"
            path.write_text("{}")
            path.chmod(0o666)
            with self.assertRaises(PermissionError):
                helper.trusted_path(path)


class PreferencesTests(unittest.TestCase):
    def test_preference_saved_without_hiding_session_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = root / "autostart/edukasaun-welcome.desktop"
            legacy.parent.mkdir()
            legacy.write_text("[Desktop Entry]\nExec=edukasaun-welcome --autostart\nHidden=true\n")
            custom = root / "autostart/other.desktop"
            custom.write_text("[Desktop Entry]\nExec=other\n")
            save_preferences({"always_show": False}, root)
            self.assertFalse(legacy.exists())
            self.assertTrue(custom.exists())
            self.assertFalse(json.loads((root / "edukasaun-welcome/preferences.json").read_text())["always_show"])


if __name__ == "__main__":
    unittest.main()
