#!/bin/sh
# Keep per-user preferences and backups for a future reinstall.
set -eu
if [ "$(id -u)" -eq 0 ]; then
    apt-get remove edukasaun-welcome
else
    sudo apt-get remove edukasaun-welcome
fi
