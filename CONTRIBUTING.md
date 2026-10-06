# Contributing

Write everything in English: identifiers, comments, commit messages, documentation and UI messages. During development the interface is English only; translations in `edukasaun_welcome/locales/` are optional and fall back to English for any missing key. Do not show version numbers in the interface.

Run `./scripts/test.sh` and `./scripts/build-deb.sh` before submitting a change.

Application entries must represent logical families, include detection aliases across APT and Flatpak, and avoid the shipped families recorded in the screenshot audit. Verify package identifiers against Debian or upstream sources. Do not add arbitrary shell commands or broaden the privileged helper beyond explicit catalog installation.

Test desktop and time changes on Debian 13 / Edukasaun OS in both supported LXQt session types, on an installed system and on the live image. Document any session-specific limitation. Obtain approved project credits and links from the maintainer before a release.
