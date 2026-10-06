"""Command line entry point; inventory export works without a graphical session."""
import argparse
import json
import os
import sys
from . import __version__
from .catalog import load_project
from .inventory import scan_inventory, write_inventory
from .preferences import load_preferences
from .session import is_live_session, should_show_welcome, start_desktop


def main(argv=None):
    parser = argparse.ArgumentParser(description="Edukasaun Welcome")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--session", action="store_true",
                        help="Login gate: show the Welcome Screen if due, then start Eduka-Desktop")
    parser.add_argument("--autostart", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force", action="store_true", help="Run even on the live system (development)")
    parser.add_argument("--language", choices=["en", "tet", "pt", "id", "system"], default="en",
                        help="UI language; English is the development default")
    parser.add_argument("--export-inventory", metavar="FILE")
    parser.add_argument("--scan", action="store_true", help="Print installed application inventory")
    args = parser.parse_args(argv)
    if args.scan or args.export_inventory:
        inventory = scan_inventory()
        if args.export_inventory:
            write_inventory(args.export_inventory, inventory)
        else:
            print(json.dumps(inventory.export(), indent=2))
        return 1 if inventory.errors else 0
    if os.geteuid() == 0:
        print("Run the Welcome Screen as a normal user, not as root.", file=sys.stderr)
        return 1
    preferences = load_preferences()
    live = is_live_session() and not args.force
    gate = args.session or args.autostart
    if gate and not should_show_welcome(preferences, live):
        # Nothing to welcome: go straight to Eduka-Desktop.
        if args.session:
            start_desktop(load_project().get("eduka_desktop", {}))
        return 0
    if live:
        print("The Welcome Screen is available after Edukasaun OS is installed. "
              "Use --force to preview it on the live system.", file=sys.stderr)
        return 0
    try:
        from .gui import launch
    except ImportError as error:
        print("Install python3-pyqt6 on Debian to run the interface: " + str(error), file=sys.stderr)
        if args.session:
            start_desktop(load_project().get("eduka_desktop", {}))
        return 1
    return launch(args.language, preferences, session=args.session)


if __name__ == "__main__":
    sys.exit(main())
