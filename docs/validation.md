# Validation for 0.1.0

Completed on 2026-10-06 in the development workspace:

| Check | Result |
| --- | --- |
| Core and offscreen native Qt tests | **28 passed**, no skipped tests |
| Locale dictionaries | 148 UI messages in each of English, Tetun, Portuguese and Indonesian; matching keys |
| Package inventory status parsing | Installed packages included; residual configurations and unpacked packages excluded |
| Detection across sources | APT/Flatpak components, user/system scopes, desktop IDs and executable aliases covered |
| Screenshot baseline | 58 observed launcher entries excluded; 38 alternative application families |
| Installation command construction | Allowlisted IDs, argument vectors, per-user Flatpak scope and separate Brave consent verified |
| Native process handling | Success, failure, command not found and live output checked with harmless fixture commands |
| Desktop settings | Unrelated keys preserved, existing configuration backed up, restore after simulated wallpaper failure verified |
| Startup setting | Per-user autostart opt-in and opt-out verified |
| Native UI | All six pages rendered offscreen; locale switching and navigation checked |
| Python source and shell scripts | Compilation and shell syntax checks passed |
| Debian package | Built with `dpkg-deb --root-owner-group`; launcher, helper, policy, translations and data included |
| Live read-only inventory smoke check | Development host scanned successfully; **not an Edukasaun OS inventory** |

The images in this directory use fixture application availability and fixture Edukasaun OS release information. They show native Qt rendering for review; they do not show a completed installation on the user's machine.

## Target VM release checks still required

1. Install the `.deb` on an Edukasaun OS / Debian 13 LXQt VM as a normal user and confirm its application menu entry.
2. Compare the exported inventory with the VM's actual applications, including categories absent from the supplied screenshots and any custom AppImages or web launchers.
3. Install one missing APT application, authenticate through the LXQt PolicyKit agent, and confirm it disappears after the rescan. Verify cancellation and APT lock handling.
4. Install one missing Flatpak application in user scope, with and without an existing Flathub remote. Validate the remote's upstream origin on managed images before release.
5. If Brave is enabled, review the official repository setup, signing key and installed architecture in a disposable VM. The helper downloads the key over HTTPS from Brave's official domain and APT verifies repository signatures; it does not independently pin a key fingerprint.
6. Apply an installed icon/theme, accent and wallpaper in LXQt. Check immediate updates and any applications requiring a restart. Test cursor and compositor settings through their native tools in the supported X11/Wayland sessions.
7. Test startup checked/unchecked after logging out and back in. Test `tet_TL`, `pt_PT`, `id_ID` and an unsupported system locale.
8. Obtain native-speaker translation review and fill approved GitHub, developer, sponsor, partner and package maintainer values before a stable public release.

No actual package installation, PolicyKit authentication, remote repository modification or live Edukasaun desktop changes were performed in the development workspace.
