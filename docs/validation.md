# Validation (development build)

Checked on 2026-10-06 in the development workspace:

| Check | Result |
| --- | --- |
| Core, session, time and offscreen native Qt tests | **43 passed**, no skipped tests |
| Live detection | `boot=live`, `boot=casper` and a mounted live medium detected; installed command line not treated as live |
| Session gate | Live system: no Welcome Screen, Eduka-Desktop started. Closing the Welcome Screen in session mode starts Eduka-Desktop once; already-running or missing Eduka-Desktop is not started again |
| Time zones | Asia/Dili first and selected by default (UTC+09:00); search filter; invalid or injected zone names rejected; `timedatectl` argument vectors verified |
| UI language and version | All messages in English; no version number shown in any label |
| Package inventory status parsing | Installed packages included; residual configurations and unpacked packages excluded |
| Detection across sources | APT/Flatpak components, user/system scopes, desktop IDs and executable aliases covered |
| Installation command construction | Allowlisted IDs, argument vectors, per-user Flatpak scope and separate Brave consent verified |
| Native process handling | Success, failure, command not found and live output checked with harmless fixture commands |
| Desktop settings | Unrelated keys preserved, existing configuration backed up, restore after simulated wallpaper failure verified |
| Startup preference | Saved per user; legacy per-user autostart override from earlier builds removed so the session gate is never hidden |
| Native UI | All six pages rendered offscreen (images in this directory use fixture data and a fixed UTC system zone) |
| Debian package | Built with `dpkg-deb --root-owner-group` |

## Still required on an Edukasaun OS VM

1. Boot the live image: confirm no Welcome Screen appears and Eduka-Desktop starts normally.
2. Install with the system installer, log in: confirm the Welcome Screen appears before Eduka-Desktop and that **Start Eduka-Desktop** starts it. Disable Eduka-Desktop's own autostart entry in the image so only the gate starts it, and confirm the real Eduka-Desktop executable name in `project.json`.
3. Apply Asia/Dili and another zone with NTP on and off; confirm the PolicyKit prompt and the result in Eduka-Panel's clock.
4. Uncheck "Show the Welcome Screen every time I log in", log out and back in: Eduka-Desktop must start directly.
5. Install one APT and one Flatpak application, apply a theme and wallpaper, as in earlier test rounds.
6. Fill approved GitHub, developer, sponsor, partner and maintainer values before a public release.

No package installation, PolicyKit authentication, system time change or live desktop change was performed in the development workspace.
