# Contributing

Use English identifiers, comments, commit messages and default UI messages. Keep translated UI text in the locale JSON files. Run `./scripts/test.sh` and `./scripts/build-deb.sh` before submitting a change.

Application entries must represent logical families, include detection aliases across APT and Flatpak, and avoid the shipped families recorded in the screenshot audit. Verify package identifiers against Debian or upstream sources. Do not add arbitrary shell commands or broaden the privileged helper beyond explicit catalog installation.

Test desktop changes on Debian 13 / Edukasaun OS in both supported LXQt session types. Document any session-specific limitation. Obtain approved project credits and links from the maintainer before a release.
