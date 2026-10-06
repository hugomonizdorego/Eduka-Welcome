#!/bin/sh
# Build an architecture-independent Debian package without root privileges.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=${1:-"$project_root/dist"}
mkdir -p "$output_dir"
output_dir=$(CDPATH= cd -- "$output_dir" && pwd)
staging_dir=$(mktemp -d)
trap 'rm -rf "$staging_dir"' EXIT HUP INT TERM
mkdir -p "$staging_dir/DEBIAN" "$staging_dir/usr/lib/edukasaun-welcome" \
    "$staging_dir/usr/bin" "$staging_dir/usr/share/applications" \
    "$staging_dir/usr/share/icons/hicolor/scalable/apps" \
    "$staging_dir/usr/share/polkit-1/actions" "$staging_dir/etc/xdg/autostart" \
    "$staging_dir/usr/share/doc/edukasaun-welcome"
cp -R "$project_root/edukasaun_welcome" "$staging_dir/usr/lib/edukasaun-welcome/"
find "$staging_dir" -type d -name __pycache__ -exec rm -rf {} +
find "$staging_dir" -type f -name '*.pyc' -delete
cp "$project_root/packaging/admin_helper.py" "$staging_dir/usr/lib/edukasaun-welcome/admin-helper"
cp "$project_root/packaging/edukasaun-welcome" "$staging_dir/usr/bin/"
cp "$project_root/packaging/edukasaun-welcome.desktop" "$staging_dir/usr/share/applications/"
cp "$project_root/packaging/edukasaun-welcome-autostart.desktop" "$staging_dir/etc/xdg/autostart/edukasaun-welcome.desktop"
cp "$project_root/packaging/org.edukasaun.welcome.policy" "$staging_dir/usr/share/polkit-1/actions/"
cp "$project_root/edukasaun_welcome/data/icon.svg" "$staging_dir/usr/share/icons/hicolor/scalable/apps/edukasaun-welcome.svg"
cp "$project_root/README.md" "$project_root/LICENSE" "$staging_dir/usr/share/doc/edukasaun-welcome/"
cp "$project_root/packaging/control" "$staging_dir/DEBIAN/control"
find "$staging_dir" -type d -exec chmod 755 {} +
find "$staging_dir" -type f -exec chmod 644 {} +
chmod 755 "$staging_dir/usr/bin/edukasaun-welcome" "$staging_dir/usr/lib/edukasaun-welcome/admin-helper"
dpkg-deb --root-owner-group --build "$staging_dir" "$output_dir/edukasaun-welcome_0.1.0_all.deb"
