# Edukasaun Welcome

The **Welcome Screen** for **Edukasaun OS** — a native **Python / Qt 6** application for Debian 13 (Trixie), LXQt and the **Eduka-Desktop Suite**.

> **Development build.** This is work in progress and will keep being revised. The interface is English only and does not show a version number.

![Welcome page](docs/welcome-preview.png)

## What the Welcome Screen does

1. **Comes first.** At login, the Welcome Screen runs *before* Eduka-Desktop. When the user finishes (or closes it), it starts Eduka-Desktop.
2. **Only on an installed system.** On the live image nothing is shown: the session gate detects live boots (`boot=live` / `boot=casper` on the kernel command line, or a mounted live medium such as `/run/live/medium`) and starts Eduka-Desktop directly.
3. **Every login until turned off.** "Show the Welcome Screen every time I log in" (on the last page) is checked by default. When unchecked, Eduka-Desktop starts directly. The Welcome Screen can still be opened from the application menu. Preferences are saved in `$XDG_CONFIG_HOME/edukasaun-welcome/preferences.json` (normally `~/.config/edukasaun-welcome/`).

## Seven pages

Screenshots of every page are in [`docs/`](docs/) (`page-1.png` … `page-7.png`).

| Page | Contents |
| --- | --- |
| 1. Welcome | Hero banner with a greeting that changes language every few seconds (Tetun first), three highlights (made in Timor-Leste, free and open, built for learning), CPLP, ASEAN and international greetings |
| 2. Date & time | Analog and digital clock for the chosen zone, quick choices (Dili, Jakarta, Makassar, Darwin, Singapore, Lisbon, UTC), a full time zone list that **always starts from Asia/Dili (Timor-Leste)**, NTP or manual time, and the Eduka-Panel clock (24/12 hours, digital/analog/LED face, seconds) |
| 3. Eduka-Desktop Suite | Eduka-Desktop, Eduka-Panel, Action Center and Eduka-Settings; highlights of Eduka-Desktop 0.9.24 (six themes, Parental Control, login screen, accessibility, languages, light on old PCs); EUS, Eduka-Konekta, Eduka-Block |
| 4. Your desktop | Live desktop preview plus **the look settings of Eduka-Settings** (see below) |
| 5. Applications | 67 education-first applications that are not yet installed; ★ "Recommended for Edukasaun OS" first; weight badge (lightweight / medium / needs a strong PC); APT, Flatpak or Brave sources |
| 6. Sponsors & support | Sponsor and partner **logos**, PayPal donation, how to become a sponsor, contributing on GitHub |
| 7. Community & finish | Summary (time zone, theme, new applications), website, Facebook, WhatsApp, GitHub (https://github.com/hugomonizdorego), goals, development team, startup preference, **Start Eduka-Desktop** |

The left rail shows every step with a check mark once done, and a progress bar. Icons, clocks, theme and panel previews are painted by the application itself, so they look the same on every computer without icon themes or SVG plugins.

## Your desktop: Eduka-Desktop 0.9.24 settings

Page 4 follows Eduka-Desktop **0.9.24** (branch `claude/festive-mayer-oxi3zl`) and offers the look settings of Eduka-Settings in five tabs:

| Tab | Settings |
| --- | --- |
| Theme & colors | Six theme cards (Eduka Default, Eduka Low, Liquid Glass, Edukasaun Dark, Eduka Transparan, Eduka MultiColor), 17 accent colors or a custom color, panel and desktop transparency, multi-color, blur behind Liquid Glass, shadows, low resource mode |
| Eduka-Panel | Panel style cards (Long, Floating bar, Short, Dock), position (bottom, top, left, right), height, width, taskbar buttons, menu button name, icon and size |
| Eduka-Desktop | Grid or List, opening section, tile size, width and height, Tetun or system language, animated effects (hover and launch) |
| Wallpaper | Pictures from `/usr/share/Edukasaun/Backgrounds` or any picture, placement mode |
| Accessibility | High contrast, status as text, Orca screen reader |

The same rules as Eduka-Settings apply: glass themes need about 2 GB RAM and two CPU threads (asked before enabling), animated effects need about 4 GB RAM and four threads, Eduka Low always runs in low resource mode.

**Apply** writes the per-user files Eduka-Settings uses (`~/.config/eduka-desktop/{panel,desktop,menu}/settings.json`, keeping unknown keys), then runs Eduka-Desktop's own code in a separate process (it uses PyQt5): `apply_desktop_theme` (GTK, Qt palette and window borders for the system-wide themes), `repair_qt_palette`, `configure_orca`, `eduka_wallpaper.apply_wallpaper`, `ensure_compositor` and the reload signals. **Open Eduka-Settings** opens the full tool for everything else (mouse, keyboard, login screen, Parental Control, notifications).

## Sponsor logos

Logos are listed in `edukasaun_welcome/data/project.json`:

```json
"sponsors": [{"name": "Example Foundation", "logo": "example.png", "url": "https://example.org"}],
"partners": ["Plain names also work"]
```

Logo files (PNG, SVG, JPG, WebP) are looked up by file name in `~/.config/edukasaun-welcome/sponsors/`, `edukasaun_welcome/data/sponsors/` and `/usr/share/edukasaun-welcome/sponsors/`. Only `https` website links are opened. Empty lists show "Your logo here" placeholders. Add only approved logos.

## Session gate: Welcome Screen first, then Eduka-Desktop

Two ways are supported; both skip the live system.

**Recommended — before the session starts.** Eduka-Desktop 0.9.24 starts every login with `eduka-desktop-session` → `exec startlxqt`. One line before `exec startlxqt` shows the Welcome Screen before LXQt, Eduka-Panel and Eduka-Desktop start:

```sh
command -v edukasaun-welcome >/dev/null 2>&1 && edukasaun-welcome --before-session || :
exec startlxqt
```

It returns at once on the live system (`boot=live`), when the user turned the Welcome Screen off, or when it is not installed. It marks the login in `$XDG_RUNTIME_DIR/edukasaun-welcome/`, so the autostart entry below does not show it a second time.

**Fallback — autostart.** The package installs `/etc/xdg/autostart/edukasaun-welcome.desktop` (`edukasaun-welcome --session`):

| Situation | Result |
| --- | --- |
| Live system | No Welcome Screen; Eduka-Desktop is started |
| Already shown before the session | Eduka-Desktop is started |
| Installed system, Welcome Screen enabled | Welcome Screen (maximized); `eduka-menu --daemon` and `eduka-panel` start when it closes |
| Installed system, Welcome Screen turned off | Eduka-Desktop is started immediately |

Components that are already running (matched by command line) are not started twice. Without the `eduka-desktop-session` line, Eduka-Panel's own autostart entry may start at the same time as the Welcome Screen.

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

There are **67 application families**, chosen for schools: learning and science (GeoGebra, Stellarium, KStars, Step, Kig, Avogadro, Anki, KWordQuiz, Parley, KTouch, Klavaro, KTurtle, gbrainy, Luanti), programming and STEM (Thonny, Mu, Geany, VSCodium, Arduino IDE, Fritzing), office and reading (LibreOffice, Xournal++, Okular, Foliate, calibre, Zim, Joplin), communication, audio and video (Audacity, OBS Studio, Kdenlive, LMMS, MuseScore), graphics (KolourPaint, Pinta, Scribus, Sweet Home 3D, Blender, FreeCAD), system tools (Timeshift, Disks, BleachBit, Flatseal) and accessibility (Onboard, KMag). 14 are marked ★ recommended, and each has a weight badge so schools with older computers can choose light applications. Package names were chosen from Debian 13 and Flathub knowledge and could not be checked online from the development workspace; the runtime check below disables any APT entry that is not available. Not every candidate is suitable for every machine; nothing is selected automatically. APT entries are enabled only when `apt-cache policy` reports a candidate in the local enabled repositories. Flatpak IDs are checked against the user's Flathub remote before installation.

Debian's Chromium package is **`chromium`**, not `chromium-browser`. The latter is accepted only as an installed-package detection alias. Brave uses its official signed APT repository, with a separate consent checkbox. No downloaded shell script is piped into a shell.

## Project credits and links

Edit `edukasaun_welcome/data/project.json` before publishing. **Developer, sponsor and partner lists are deliberately empty** until the maintainer supplies approved values. The GitHub link is https://github.com/hugomonizdorego.

For a per-user override, create `~/.config/edukasaun-welcome/project.json` containing only the fields to override. Example:

```json
{
  "developers": ["Your approved developer name"],
  "sponsors": ["Your approved sponsor name"],
  "partners": ["Your approved partner name"],
  "github": "https://github.com/hugomonizdorego"
}
```

The donation link is `https://paypal.me/hugocenturion0311`. Verify the configured project website and social links before release. Commands for native desktop tools are in `suite_tools`; `suite` opens `eduka-settings`, `menu` opens Eduka-Desktop.

## Build, test and remove

```bash
./scripts/test.sh
./scripts/build-deb.sh
./scripts/uninstall.sh
```

Tests use fixture inventories, fixture live/installed boot information and an offscreen Qt application. They never install applications, change the system time, or alter the host's desktop or Eduka-Desktop configuration. `scripts/render-previews.py` renders the seven screenshots in `docs/`. See [docs/validation.md](docs/validation.md).

Export the installed application inventory without opening the GUI:

```bash
edukasaun-welcome --export-inventory edukasaun-installed-apps.json
edukasaun-welcome --scan
```

Uninstalling preserves user preferences and configuration backups. No application previously selected in the Welcome Screen is removed.

## License

GPL-3.0-or-later. PyQt6 is used under its GPL licensing option. The included book icon and UI are original source assets. Screenshots are not redistributed; the audit records the user's visible launcher names. See [LICENSE](LICENSE) and [docs/sources.md](docs/sources.md).
