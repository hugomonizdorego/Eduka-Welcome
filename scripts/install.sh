#!/bin/sh
# Install only Edukasaun Welcome and its dependencies; never upgrade the OS.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v apt-get >/dev/null 2>&1 || { echo 'A Debian-based system is required.' >&2; exit 1; }
sh "$project_root/scripts/build-deb.sh"
package_path="$project_root/dist/edukasaun-welcome_dev_all.deb"
if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    apt-get --no-remove install "$package_path"
else
    sudo apt-get update
    sudo apt-get --no-remove install "$package_path"
fi
echo 'Installed. The Welcome Screen appears at the next login, before Eduka-Desktop starts.'
