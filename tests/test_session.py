import importlib.util
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from edukasaun_welcome import __main__ as entry
from edukasaun_welcome.session import is_live_session, process_running, should_show_welcome, start_desktop
from edukasaun_welcome.timesettings import (
    DEFAULT_TIMEZONE, format_clock, time_commands, timezone_choices, utc_offset, valid_timezone,
)


class LiveSessionTests(unittest.TestCase):
    def cmdline(self, folder, text):
        path = Path(folder) / "cmdline"
        path.write_text(text)
        return path

    def test_live_boot_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            for text in ("BOOT_IMAGE=/live/vmlinuz boot=live components quiet", "boot=casper"):
                self.assertTrue(is_live_session(self.cmdline(folder, text), ()))

    def test_installed_system_and_live_medium(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.cmdline(folder, "BOOT_IMAGE=/vmlinuz root=UUID=1234 ro quiet")
            self.assertFalse(is_live_session(path, ()))
            self.assertTrue(is_live_session(path, (folder,)))

    def test_welcome_only_after_install_and_when_enabled(self):
        self.assertTrue(should_show_welcome({}, live=False))
        self.assertFalse(should_show_welcome({}, live=True))
        self.assertFalse(should_show_welcome({"always_show": False}, live=False))


class DesktopLaunchTests(unittest.TestCase):
    SETTINGS = {"environment": {"QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1"},
                "components": [{"command": ["eduka-menu", "--daemon"], "process": "eduka-menu"},
                               {"command": ["eduka-panel"], "process": "eduka-panel"}]}

    def test_start_each_component_once(self):
        started = []
        def popen(command, **kwargs):
            started.append(command)
            self.assertEqual(kwargs["env"]["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"], "1")
        with patch("shutil.which", return_value="/usr/bin/fixture"), \
                patch("edukasaun_welcome.session.process_running", side_effect=lambda name: name == "eduka-panel"):
            self.assertTrue(start_desktop(self.SETTINGS, popen))
        self.assertEqual(started, [["eduka-menu", "--daemon"]])

    def test_missing_desktop_is_not_started(self):
        with patch("shutil.which", return_value=None):
            self.assertFalse(start_desktop(self.SETTINGS, lambda *a, **k: self.fail()))
        self.assertFalse(start_desktop({}, lambda *a, **k: self.fail()))

    def test_process_lookup_by_command_line(self):
        with tempfile.TemporaryDirectory() as folder:
            entry_dir = Path(folder) / "4242"
            entry_dir.mkdir()
            (entry_dir / "comm").write_text("python3\n")
            (entry_dir / "cmdline").write_bytes(b"python3\0/usr/bin/eduka-panel\0")
            self.assertTrue(process_running("eduka-panel", folder))
            self.assertFalse(process_running("eduka-menu", folder))

    def test_session_gate_on_live_system_starts_desktop_without_welcome(self):
        with patch.object(entry, "is_live_session", return_value=True), \
                patch.object(entry, "load_preferences", return_value={}), \
                patch.object(entry, "start_desktop") as start, patch("os.geteuid", return_value=1000):
            self.assertEqual(entry.main(["--session"]), 0)
            start.assert_called_once()

    @unittest.skipUnless(importlib.util.find_spec("PyQt6"), "Install python3-pyqt6 for native UI checks")
    def test_before_session_marker_skips_second_welcome(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict("os.environ", {"XDG_RUNTIME_DIR": folder}), \
                patch.object(entry, "is_live_session", return_value=False), \
                patch.object(entry, "load_preferences", return_value={}), patch("os.geteuid", return_value=1000), \
                patch("edukasaun_welcome.gui.launch", return_value=0) as launch, \
                patch.object(entry, "start_desktop") as start:
            self.assertEqual(entry.main(["--before-session"]), 0)
            launch.assert_called_once()
            self.assertFalse(launch.call_args.kwargs["session"])
            self.assertTrue(launch.call_args.kwargs["before_session"])
            # The autostart gate in the same login now only starts Eduka-Desktop.
            self.assertEqual(entry.main(["--session"]), 0)
            launch.assert_called_once()
            start.assert_called_once()

    def test_manual_launch_refused_on_live_system(self):
        with patch.object(entry, "is_live_session", return_value=True), \
                patch.object(entry, "load_preferences", return_value={}), \
                patch("os.geteuid", return_value=1000), patch("sys.stderr"):
            self.assertEqual(entry.main([]), 0)


class TimeTests(unittest.TestCase):
    def test_dili_is_first(self):
        zones = timezone_choices()
        self.assertEqual(zones[0], "Asia/Dili")
        self.assertEqual(DEFAULT_TIMEZONE, "Asia/Dili")
        self.assertEqual(zones.count("Asia/Dili"), 1)
        self.assertIn("Europe/Lisbon", zones)
        self.assertEqual(utc_offset("Asia/Dili"), "UTC+09:00")

    def test_commands_are_validated_vectors(self):
        self.assertEqual(time_commands("Asia/Dili"), [
            ["timedatectl", "set-timezone", "Asia/Dili"], ["timedatectl", "set-ntp", "true"]])
        manual = time_commands("Asia/Jakarta", False, datetime(2026, 10, 6, 9, 30))
        self.assertEqual(manual[-1], ["timedatectl", "set-time", "2026-10-06 09:30:00"])
        for zone in ("", "Asia/Dili; reboot", "../../etc/passwd", "Mars/Olympus"):
            self.assertFalse(valid_timezone(zone))
            with self.assertRaises(ValueError):
                time_commands(zone)
        with self.assertRaises(ValueError):
            time_commands("Asia/Dili", False, None)

    def test_clock_format(self):
        moment = datetime(2026, 10, 6, 5, 7, 9).astimezone()
        self.assertRegex(format_clock("Asia/Dili", True, moment), r"\d{2}:\d{2}:\d{2}$")
        self.assertRegex(format_clock("Asia/Dili", False, moment), r"(AM|PM)$")


if __name__ == "__main__":
    unittest.main()
