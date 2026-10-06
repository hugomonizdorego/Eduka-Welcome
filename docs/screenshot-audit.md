# Installed launcher audit

Evidence: seven screenshots supplied by the user on 2026-10-06. The visible system information identifies Edukasaun OS 1.0, codename Kameli, Debian GNU/Linux 13 (Trixie), Eduka-Desktop (LXQt Session). The separate menu banner shows Eduka-Desktop / Edukasaun OS 0.9.24; the welcome program reads the running `/etc/os-release` rather than hard-coding either version.

This is a **launcher audit**, not a complete APT/Flatpak manifest. Web shortcuts, configuration launchers and applications may all appear in the menu. Truncated titles are recorded as shown. Exact package IDs for those entries are not inferred from the image alone.

| Screenshot | Visible launchers | Count |
| --- | --- | ---: |
| 15-48-47.716 | 2048, Abacus, Blinken, Bovo, Duolingo, Filius, Fretboard, GCompris, GoldenDict-ng, Hex-a-hop, Kalzium, Kanagram, KAtomic, KBlocks, KBruch, KDE Marble | 16 |
| 15-49-27.697 | KGeography, KHangMan, Kiwix, KLettres, KNetWalk, KTuberling, Kubrick, Math Hurdler, Music Keyboard, NumptyPhysics, Palapeli, Swift Feet, Tetun L...sources, Trivia Quiz, TurboWarp, Tux Math | 16 |
| 15-49-51.677 | Repeats 12 entries from the previous screenshot; adds Tux Paint, Tux Paint Config., Linux Typing, Words | 4 new |
| 15-50-21.696 | Coulr, GNU Im...rogram (GIMP), ImageM...h-q16) (ImageMagick), Inkscape, Krita, LXImage-Qt, ScreenGrab, XSane | 8 |
| 15-50-44.692 | Dialect, Firefox, Google Earth, Icon Browser, Thunderbird, Whatsapp Linux, Wike, Zoom Workplace | 8 |
| 15-51-06.702 | FeatherNotes, ONLYOFFICE, qpdfview | 3 |
| 15-51-32.712 | Audacious, PulseAu...Control (PulseAudio volume control), VLC media player | 3 |
| Total | Distinct visible launcher entries, including Tux Paint configuration | **58** |

The Tux Typing icon is labeled “Linux Typing”. Its exclusion family is `tuxtype`. The unknown exact Tetun shortcut is represented by the internal family `tetun-resources`; it is not an installation package name.

The sidebar also shows Accessories, Programming, System Tools, Universal Access and Preferences, but their contents are not visible. Other educational entries might exist above/between captured scroll positions. Runtime inventory detection is therefore mandatory, not optional.

The catalogue baseline is `edukasaun_welcome/data/catalog.json` → `shipped_families`. No observed launcher is offered in the default additional-app list. A future catalogue change adding one of these families is still filtered out automatically.
