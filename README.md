# Edukasaun Welcome

A native **Python / Qt 6** first-run assistant for **Edukasaun OS**, targeting Debian 13 (Trixie) and LXQt. This is version **0.1.0**, ready for source review and testing on an Edukasaun OS VM.

![Welcome page](docs/welcome-preview.png)

## Run or install

From the extracted source directory on Edukasaun OS:

```bash
chmod +x scripts/*.sh
./scripts/install.sh
edukasaun-welcome
```

The installer builds a Debian package, refreshes APT indexes and installs **only this application and its dependencies**. It does not upgrade the operating system. A normal administrator prompt is used when needed.

Alternatively, install the included prebuilt package:

```bash
sudo apt install ./dist/edukasaun-welcome_0.1.0_all.deb
```

For development without a system installation:

```bash
sudo apt install python3-pyqt6
./scripts/run.sh
./scripts/run.sh --language tet
```

The development UI can scan applications and edit the current user's supported LXQt settings. APT application installation requires the system package, which installs the root-owned helper and PolicyKit action. Do not run the UI as root. A pip installation provides a development launcher, not the privileged system integration.

## Six pages

The requested specification says five pages but describes six separate screens. This implementation retains all six:

| Page | Contents |
| --- | --- |
| 1. Welcome | International, Portuguese/CPLP and ASEAN greetings; checked startup preference; Next |
| 2. Discover | Edukasaun OS; Eduka-Desktop, Menu, Panel and Menu-Settings explanations; related project tools; developers, sponsors, partners; About |
| 3. Desktop | Installed LXQt themes and icon themes, accent color, wallpaper, Apply; native cursor/font/color settings and session/effects tools |
| 4. Applications | Additional recommendations only; APT/Flatpak/Brave source choices; pre-install rescan; authentication, live output and inventory export |
| 5. Community | Website, Facebook, WhatsApp, configurable GitHub link and project goals |
| 6. Ready | Thank-you message, optional PayPal donation and Close |

Every page after the first has Back. Next can skip optional desktop changes or application installation. Donation is optional.

## Existing applications are excluded

The seven supplied screenshots were audited. **58 visible launcher entries** are recorded in [docs/screenshot-audit.md](docs/screenshot-audit.md). GCompris, Kiwix, TurboWarp, Tux Math, Tux Paint, Tux Typing, GIMP, Inkscape, Krita, Firefox, Thunderbird, ONLYOFFICE, Audacious, VLC and the other observed applications are not default installation recommendations.

The screenshots do not cover every category. At runtime, the application also reads:

- Installed APT packages, distinguishing `installed` from residual configuration entries.
- Flatpak applications in **both user and system scopes**.
- Application desktop IDs and executable launchers, including local user entries.
- Executables on PATH, to recognize programs installed outside APT.

Detection uses logical families: an installed Flatpak LibreOffice, for example, hides the APT LibreOffice recommendation too. The inventory is scanned again immediately before installation. Failed inventory checks disable installation rather than silently treating everything as absent.

There are **38 alternative application families**, including Chromium, GNOME Web, Falkon, Geary, Claws Mail, LibreOffice, Xournal++, Foliate, MPV, Audacity, Kdenlive, OBS Studio, HandBrake, Shotcut, GNOME Chess, Stellarium, KTouch, KAlgebra, Cantor, Scribus, Blender and selected utilities. Not every candidate is suitable for every machine; nothing is selected automatically. APT entries are enabled only when `apt-cache policy` reports a candidate in the local enabled repositories. Flatpak IDs are checked against the user's Flathub remote before installation.

Debian's Chromium package is **`chromium`**, not `chromium-browser`. The latter is accepted only as an installed-package detection alias. Brave uses its official signed APT repository, with a separate consent checkbox. No downloaded shell script is piped into a shell.

## Localization and startup

English is the source language. Full UI dictionaries are included for **English, Tetun, Portuguese and Indonesian**. The default is **Follow system**: `LC_ALL`, `LC_MESSAGES`, `LANG`, and GNU `LANGUAGE` preferences are respected. Tetun is explicitly supported even when Qt does not recognize `tet_TL`.

Other system languages fall back to English; international greeting strings do not imply complete UI translations for those languages. Additional translations can be added under `edukasaun_welcome/locales/` and registered in `i18n.py`. Tetun terminology should receive a native-speaker review before a stable release.

“Always show Welcome Screen” defaults to checked. Its value and language override are saved in `$XDG_CONFIG_HOME/edukasaun-welcome/preferences.json` (normally `~/.config/edukasaun-welcome/`). A per-user freedesktop autostart entry implements opt-in/opt-out; manually launching from the menu still works. System autostart is limited to LXQt sessions.

## Project credits and links

Edit `edukasaun_welcome/data/project.json` before publishing. **Developer, sponsor and partner lists are deliberately empty**, and the official GitHub link is blank until the maintainer supplies approved values. The disabled GitHub button becomes active when configured.

For a per-user override, create `~/.config/edukasaun-welcome/project.json` containing only the fields to override. Example:

```json
{
  "developers": ["Your approved developer name"],
  "sponsors": ["Your approved sponsor name"],
  "partners": ["Your approved partner name"],
  "github": "https://github.com/YOUR_USERNAME/edukasaun-welcome"
}
```

The donation link is `https://paypal.me/hugocenturion0311`. Verify the configured project website and social links before release. Optional integration commands for native desktop tools are in `suite_tools`; supply the actual installed Eduka-Menu-Settings command rather than guessing an executable name.

## Desktop behavior

Apply updates only per-user LXQt `icon_theme`, `theme`, and `Palette/highlight_color` values when chosen. It uses Qt's INI serializer, preserves unrelated keys and backs up existing `lxqt.conf` under `~/.config/edukasaun-welcome/backups/`. Wallpaper is applied using `pcmanfm-qt --set-wallpaper ... --wallpaper-mode zoom`. A failed wallpaper command restores the saved LXQt configuration; it cannot undo an external desktop process that partially changes its own state.

Cursor, fonts, the complete color palette and GTK synchronization are handled by **LXQt Appearance**, which has its own Apply button and native session handling. Compositor settings are opened through LXQt Session Settings; configure effects with the installed compositor's own tools. This release does not write undocumented Eduka-Desktop Suite or compositor settings. Reduced motion is a welcome preference; the wizard itself has no animated transitions. Some running applications may need reopening, and cursor/compositor changes can require a new session, especially under Wayland.

## Build, test and remove

```bash
./scripts/test.sh
./scripts/build-deb.sh
./scripts/uninstall.sh
```

Tests use fixture inventories and an offscreen Qt application. They never install additional applications or alter the host's desktop configuration. See [docs/validation.md](docs/validation.md) for the completed checks and remaining VM release checks. GitHub Actions runs the same tests and builds the Debian package.

Export the complete current inventory from the target system without opening the GUI:

```bash
edukasaun-welcome --export-inventory edukasaun-installed-apps.json
edukasaun-welcome --scan
```

Uninstalling preserves user preferences and configuration backups. No application previously selected in the welcome wizard is removed.

## Upload to GitHub

Create an empty repository named **`edukasaun-welcome`**, then from this source directory:

```bash
git init
git add .
git commit -m "Add Edukasaun Welcome 0.1.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/edukasaun-welcome.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account or organization. `dist/` is excluded from Git; attach the `.deb` to a GitHub release, or download the package built by Actions. Replace the placeholder maintainer contact in `packaging/control` with a real project address before distribution.

## License

GPL-3.0-or-later. PyQt6 is used under its GPL licensing option. The included book icon and UI are original source assets. Screenshots are not redistributed; the audit records the user's visible launcher names. See [LICENSE](LICENSE) and [docs/sources.md](docs/sources.md).
