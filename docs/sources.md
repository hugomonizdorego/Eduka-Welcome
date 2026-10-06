# Primary implementation references

Checked while preparing this source on 2026-10-06. Availability on a target machine is verified again at runtime; this file does not promise specific versions or package availability on every architecture.

- Debian PyQt6: https://packages.debian.org/trixie/python3-pyqt6
- Debian Chromium: https://packages.debian.org/trixie/chromium
- Debian GNOME Chess: https://packages.debian.org/trixie/gnome-chess
- Debian Scribus: https://packages.debian.org/trixie/scribus
- Debian 7zip: https://packages.debian.org/trixie/7zip
- Brave official Linux installation and repository: https://brave.com/linux/
- Flatpak CLI and user/system scope: https://docs.flatpak.org/en/latest/using-flatpak.html
- Flathub Debian setup: https://flathub.org/en/setup/Debian
- LXQt Appearance source: https://github.com/lxqt/lxqt-config/tree/master/lxqt-config-appearance
- LXQt icon and theme setting keys: `iconthemeconfig.cpp`, `lxqtthemeconfig.cpp` in that directory.
- LXQt accent palette setting: `styleconfig.cpp` → `Palette/highlight_color`.
- LXQt cursor handling: `main.cpp` → `SelectWnd` from `liblxqt-config-cursor`.
- PCManFM-Qt wallpaper CLI: https://github.com/lxqt/pcmanfm-qt/blob/master/pcmanfm/application.cpp
- Qt settings serializer: https://doc.qt.io/qt-6/qsettings.html
- Qt process execution: https://doc.qt.io/qt-6/qprocess.html
- Freedesktop autostart: https://specifications.freedesktop.org/autostart-spec/latest/
- PolicyKit pkexec: https://www.freedesktop.org/software/polkit/docs/latest/pkexec.1.html

GeoGebra and the old Scratch community Flatpak wrapper are not included as default recommendations. TurboWarp and Kiwix are already visible in the screenshots and are likewise omitted. Public application descriptions are short original summaries; project credits remain configurable.
