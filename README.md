# Edukasaun Welcome

The **Welcome Screen** for **Edukasaun OS** — a native **Python / Qt 6** application for Debian 13 (Trixie), LXQt and the **Eduka-Desktop Suite**.

> **Development build.** This is work in progress and will keep being revised. The interface is English only and does not show a version number.

![Welcome page](docs/welcome-preview.png)

## What the Welcome Screen does

1. **Comes first.** At login, the Welcome Screen runs *before* Eduka-Desktop. When the user finishes (or closes it), it starts Eduka-Desktop.
2. **Only on an installed system.** On the live image nothing is shown: the session gate detects live boots (`boot=live` / `boot=casper` on the kernel command line, or a mounted live medium such as `/run/live/medium`) and starts Eduka-Desktop directly.
3. **Every login until turned off.** "Show the Welcome Screen every time I log in" (on the last page) is checked by default. When unchecked, Eduka-Desktop starts directly. The Welcome Screen can still be opened from the application menu. Preferences are saved in `$XDG_CONFIG_HOME/edukasaun-welcome/preferences.json` (normally `~/.config/edukasaun-welcome/`).

## Six pages

| Page | Contents |
| --- | --- |
| 1. Welcome | Greetings from Timor-Leste & CPLP, ASEAN and around the world; overview of the setup steps; installed system name |
| 2. Date & time | Time zone list that **always starts from Asia/Dili (Timor-Leste)**, search, live clock preview with UTC offset, 24/12-hour clock format, automatic time (NTP) or manual date and time, Apply |
| 3. Eduka-Desktop Suite | Eduka-Desktop, Eduka-Menu, Eduka-Panel, Eduka-Menu-Settings; project tools EUS, Eduka-Konekta, Eduka-Block; About |
| 4. Your desktop | Installed LXQt themes and icon themes, accent color, wallpaper, Apply; native appearance, desktop and session tools |
| 5. Applications | Additional recommendations only; APT/Flatpak/Brave sources; pre-install rescan; authentication, live output and inventory export |
| 6. Community & finish | Website, Facebook, WhatsApp, GitHub; goals; credits; optional PayPal donation; startup preference; **Start Eduka-Desktop** |

Every page after the first has Back. All settings are optional; Next skips them.

## Session gate: Welcome Screen first, then Eduka-Desktop

The package installs `/etc/xdg/autostart/edukasaun-welcome.desktop`, which runs:

```bash
edukasaun-welcome --session
```

| Situation | Result |
| --- | --- |
| Live system | No Welcome Screen; Eduka-Desktop is started |
| Installed system, Welcome Screen enabled | Welcome Screen (maximized); Eduka-Desktop starts when it closes |
| Installed system, Welcome Screen turned off | Eduka-Desktop is started immediately |

The Eduka-Desktop command is configured in `edukasaun_welcome/data/project.json`:

```json
"eduka_desktop": { "command": ["eduka-desktop"], "process": "eduka-desktop" }
```

It is started only if it is installed and not already running. **For the Welcome Screen to really appear first, the Edukasaun OS image should start Eduka-Desktop through this gate** (remove or disable Eduka-Desktop's own autostart entry). Replace `eduka-desktop` with the actual Eduka-Desktop executable if it differs.

Manually launching `edukasaun-welcome` on the live system prints a notice and exits. Developers can preview it there with `edukasaun-welcome --force`.

## Date and time

- The list contains every IANA time zone from the system `tzdata`, with **Asia/Dili — Timor-Leste first and selected by default**, followed by the rest alphabetically and `UTC`.
- Apply runs `timedatectl set-timezone`, `timedatectl set-ntp` and, for manual time, `timedatectl set-time`, as argument vectors (no shell). systemd-timedated asks PolicyKit for administrator authentication.
- Only zones from the list are accepted.
- The 24/12-hour choice is saved as `clock_24h` in the user preferences so Eduka-Panel can use it later; it does not change the system clock.

## Run or install

On Edukasaun OS:

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

The installer builds a Debian package (`dist/edukasaun-welcome_dev_all.deb`), refreshes APT indexes and installs **only this application and its dependencies**. It does not upgrade the operating system.

For development without a system installation:

```bash
sudo apt install python3-pyqt6
./scripts/run.sh            # normal window
./scripts/run.sh --session  # login gate behavior
./scripts/run.sh --force    # preview on the live system
```

APT application installation requires the system package, which installs the root-owned helper and PolicyKit action. Do not run the UI as root.

## Language

During development the whole interface is **English**. The earlier Tetun, Portuguese and Indonesian dictionaries are kept under `edukasaun_welcome/locales/` for later work; they contain only strings whose English source did not change and fall back to English for everything else. Translators can test them with `--language tet|pt|id`.

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

The donation link is `https://paypal.me/hugocenturion0311`. Verify the configured project website and social links before release. Optional integration commands for native desktop tools are in `suite_tools`; put the actual Eduka-Menu-Settings command in `suite_tools.suite` to enable the "Open Eduka-Menu-Settings" button.

## Desktop behavior

Apply updates only per-user LXQt `icon_theme`, `theme`, and `Palette/highlight_color` values when chosen. It uses Qt's INI serializer, preserves unrelated keys and backs up existing `lxqt.conf` under `~/.config/edukasaun-welcome/backups/`. Wallpaper is applied using `pcmanfm-qt --set-wallpaper ... --wallpaper-mode zoom`. A failed wallpaper command restores the saved LXQt configuration; it cannot undo an external desktop process that partially changes its own state.

Cursor, fonts, the complete color palette and GTK synchronization are handled by **LXQt Appearance**, which has its own Apply button and native session handling. Compositor settings are opened through LXQt Session Settings; configure effects with the installed compositor's own tools. This release does not write undocumented Eduka-Desktop Suite or compositor settings. Some running applications may need reopening, and cursor/compositor changes can require a new session, especially under Wayland.

## Build, test and remove

```bash
./scripts/test.sh
./scripts/build-deb.sh
./scripts/uninstall.sh
```

Tests use fixture inventories, fixture live/installed boot information and an offscreen Qt application. They never install applications, change the system time or alter the host's desktop configuration. See [docs/validation.md](docs/validation.md).

Export the installed application inventory without opening the GUI:

```bash
edukasaun-welcome --export-inventory edukasaun-installed-apps.json
edukasaun-welcome --scan
```

Uninstalling preserves user preferences and configuration backups. No application previously selected in the Welcome Screen is removed.

## License

GPL-3.0-or-later. PyQt6 is used under its GPL licensing option. The included book icon and UI are original source assets. Screenshots are not redistributed; the audit records the user's visible launcher names. See [LICENSE](LICENSE) and [docs/sources.md](docs/sources.md).
