"""Read installed applications without changing package state."""
import configparser
import json
import os
import shlex
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Inventory:
    packages: set = field(default_factory=set)
    flatpaks: set = field(default_factory=set)
    desktop_ids: set = field(default_factory=set)
    executables: set = field(default_factory=set)
    errors: list = field(default_factory=list)

    def export(self):
        return {key: sorted(value) if isinstance(value, set) else value
                for key, value in asdict(self).items()}


def run_read(command, timeout=30):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                            env={**os.environ, "LC_ALL": "C"}, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Command failed: " + command[0])
    return result.stdout


def parse_dpkg(text):
    result = set()
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) == 2 and fields[1].strip() == "installed":
            result.add(fields[0].split(":")[0])
    return result


def read_desktop_entries(inventory, directories):
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.desktop"):
            try:
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(path, encoding="utf-8")
                section = parser["Desktop Entry"]
                if section.get("Hidden", "false").lower() == "true":
                    continue
                inventory.desktop_ids.add(path.stem)
                tokens = shlex.split(section.get("Exec", ""))
                if tokens:
                    executable = Path(tokens[0]).name
                    inventory.executables.add(executable)
                    # Flatpak and wrappers are also covered by IDs/packages.
            except (OSError, ValueError, configparser.Error, KeyError):
                continue


def scan_inventory(home=None, runner=run_read):
    home = Path.home() if home is None else Path(home)
    inventory = Inventory()
    try:
        inventory.packages = parse_dpkg(runner([
            "dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\n"]))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        inventory.errors.append("APT: " + str(error))
    if shutil.which("flatpak"):
        for scope in ("--user", "--system"):
            try:
                inventory.flatpaks.update(runner([
                    "flatpak", "list", scope, "--app", "--columns=application"
                ]).splitlines())
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                inventory.errors.append("Flatpak " + scope + ": " + str(error))
    config_data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    directories = [config_data / "applications", home / ".local/share/flatpak/exports/share/applications",
                   Path("/var/lib/flatpak/exports/share/applications")]
    directories.extend(Path(p) / "applications" for p in
                       os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"))
    read_desktop_entries(inventory, directories)
    return inventory


def is_installed(app, inventory):
    detection = app["detect"]
    return bool(inventory.packages.intersection(detection.get("packages", [])) or
                inventory.flatpaks.intersection(detection.get("flatpaks", [])) or
                inventory.desktop_ids.intersection(detection.get("desktop_ids", [])) or
                inventory.executables.intersection(detection.get("executables", [])) or
                any(shutil.which(name) for name in detection.get("executables", [])))


def apt_available(package, runner=run_read):
    try:
        text = runner(["apt-cache", "policy", package])
        return any(line.strip().startswith("Candidate:") and "(none)" not in line
                   for line in text.splitlines())
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return False


def write_inventory(path, inventory):
    Path(path).write_text(json.dumps(inventory.export(), indent=2) + "\n", encoding="utf-8")
