"""Logical application families prevent duplication between APT and Flatpak."""
import json
from pathlib import Path
from .inventory import is_installed

DATA = Path(__file__).parent / "data"


def load_catalog():
    return json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))


def recommendations(inventory, catalog=None):
    data = load_catalog() if catalog is None else catalog
    excluded = set(data["shipped_families"])
    return [app for app in data["apps"]
            if app["id"] not in excluded and not is_installed(app, inventory)]


def install_commands(apps, source, add_remote=False, add_brave=False):
    """Return argument vectors, never shell text."""
    if not apps:
        raise ValueError("Select at least one application")
    allowed = {app["id"]: app for app in load_catalog()["apps"]}
    for app in apps:
        if app["id"] not in allowed or app != allowed[app["id"]] or source not in app["sources"]:
            raise ValueError("Invalid catalog selection")
    if source == "apt":
        return [["pkexec", "/usr/lib/edukasaun-welcome/admin-helper", "apt",
                 *[app["id"] for app in apps]]]
    if source == "brave":
        if not add_brave:
            raise ValueError("Brave repository consent is required")
        return [["pkexec", "/usr/lib/edukasaun-welcome/admin-helper", "brave", "brave"]]
    if source == "flatpak":
        commands = []
        if add_remote:
            commands.append(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                             "https://dl.flathub.org/repo/flathub.flatpakrepo"])
        for app in apps:
            app_id = app["sources"]["flatpak"]
            commands.append(["flatpak", "remote-info", "--user", "flathub", app_id])
        commands.append(["flatpak", "install", "--user", "--noninteractive", "--assumeyes", "flathub",
                         *[app["sources"]["flatpak"] for app in apps]])
        return commands
    raise ValueError("Unsupported source")
