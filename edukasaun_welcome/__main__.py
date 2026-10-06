"""Command line entry point; inventory export works without a graphical session."""
import argparse
import json
import os
import sys
from . import __version__
from .inventory import scan_inventory, write_inventory
from .preferences import load_preferences


def main():
    parser = argparse.ArgumentParser(description="Edukasaun Welcome")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--autostart", action="store_true")
    parser.add_argument("--language", choices=["system", "en", "tet", "pt", "id"])
    parser.add_argument("--export-inventory", metavar="FILE")
    parser.add_argument("--scan", action="store_true", help="Print installed application inventory")
    args = parser.parse_args()
    if args.scan or args.export_inventory:
        inventory = scan_inventory()
        if args.export_inventory:
            write_inventory(args.export_inventory, inventory)
        else:
            print(json.dumps(inventory.export(), indent=2))
        return 1 if inventory.errors else 0
    if os.geteuid() == 0:
        print("Run the welcome interface as a normal user, not as root.", file=sys.stderr)
        return 1
    preferences = load_preferences()
    if args.autostart and not preferences.get("always_show", True):
        return 0
    try:
        from .gui import launch
    except ImportError as error:
        print("Install python3-pyqt6 on Debian to run the interface: " + str(error), file=sys.stderr)
        return 1
    return launch(args.language or preferences.get("language", "system"), preferences)


if __name__ == "__main__":
    sys.exit(main())
