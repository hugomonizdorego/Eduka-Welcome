# Validation (development build)

Checked on 2026-10-06 in the development workspace:

| Check | Result |
| --- | --- |
| Core, session, time, Eduka-Desktop and offscreen native Qt tests | **58 passed**, no skipped tests |
| Live detection | `boot=live`, `boot=casper` and a mounted live medium detected; installed command line not treated as live |
| Session gate | Live system: no Welcome Screen, Eduka-Desktop started. Closing the Welcome Screen in session mode starts `eduka-menu --daemon` and `eduka-panel`; running components (matched by command line) or missing ones are not started |
| Time zones | Asia/Dili first and selected by default (UTC+09:00); search filter; invalid or injected zone names rejected; `timedatectl` argument vectors verified |
| UI language and version | All messages in English; no version number shown in any label |
| Package inventory status parsing | Installed packages included; residual configurations and unpacked packages excluded |
| Detection across sources | APT/Flatpak components, user/system scopes, desktop IDs and executable aliases covered |
| Installation command construction | Allowlisted IDs, argument vectors, per-user Flatpak scope and separate Brave consent verified |
| Native process handling | Success, failure, command not found and live output checked with harmless fixture commands |
| Desktop settings | Unrelated keys preserved, existing configuration backed up, restore after simulated wallpaper failure verified |
| Startup preference | Saved per user; legacy per-user autostart override from earlier builds removed so the session gate is never hidden |
| Eduka-Desktop settings | Same JSON files and keys as Eduka-Settings 0.9.24 (six themes, accent color, panel style and position, clock, effects, tile size, Tetun, wallpaper); unknown keys preserved; ranges clamped; invalid choices rejected; settings revision marker kept so Eduka-Desktop does not reset transparency; reload signals written; glass themes and effects refused on weak hardware; Eduka-Desktop's own apply functions run in a separate process |
| Sponsors | Logo lookup by file name only in sponsor folders; non-https links ignored; placeholders when empty |
| Native UI | All seven pages rendered offscreen at full length (images in this directory use fixture data and a fixed UTC system zone) |
| Debian package | Built with `dpkg-deb --root-owner-group` |

## Still required on an Edukasaun OS VM

1. Boot the live image: confirm no Welcome Screen appears and Eduka-Desktop starts normally.
2. Add `edukasaun-welcome --before-session` before `exec startlxqt` in `eduka-desktop-session`. Install with the system installer, log in: confirm the Welcome Screen appears before LXQt, Eduka-Panel and Eduka-Desktop, and that the desktop starts after **Start Eduka-Desktop**. Also try the autostart fallback without that line.
3. On page 4, change each Eduka-Desktop setting and confirm Eduka-Panel and Eduka-Desktop refresh; enable and disable Orca; try a glass theme and Edukasaun-Dark on a 1 GB and a 4 GB machine.
4. Apply Asia/Dili and another zone with NTP on and off; confirm the PolicyKit prompt and the result in Eduka-Panel's clock.
5. Uncheck "Show the Welcome Screen every time I log in", log out and back in: Eduka-Desktop must start directly.
6. Install one APT and one Flatpak application, apply a theme and wallpaper, as in earlier test rounds.
7. Add approved sponsor and partner logos, developer names and the package maintainer address before a public release.

No package installation, Eduka-Desktop change, PolicyKit authentication, system time change or live desktop change was performed in the development workspace.
