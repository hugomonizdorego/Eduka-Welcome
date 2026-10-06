#!/usr/bin/python3 -I
"""Root-only installation of applications from a root-owned catalog.

No shell, user-supplied paths, arbitrary packages or environment overrides.
"""
import json
import os
import platform
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

INSTALL_ROOT = Path("/usr/lib/edukasaun-welcome")
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C",
       "DEBIAN_FRONTEND": "noninteractive"}


def validated_packages(mode, identifiers, catalog):
    if not identifiers or len(identifiers) > 50 or len(set(identifiers)) != len(identifiers):
        raise ValueError("Invalid application selection")
    apps = {app["id"]: app for app in catalog["apps"]}
    excluded = set(catalog["shipped_families"])
    source = "apt" if mode == "apt" else "brave"
    if mode not in ("apt", "brave") or (mode == "brave" and identifiers != ["brave"]):
        raise ValueError("Unsupported operation")
    packages = []
    for identifier in identifiers:
        if identifier in excluded or identifier not in apps or source not in apps[identifier]["sources"]:
            raise ValueError("Application is not allowed")
        package = apps[identifier]["sources"][source]
        if not package or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789+.-" for c in package):
            raise ValueError("Invalid package name")
        if not package[0].isalnum():
            raise ValueError("Invalid package name")
        packages.append(package)
    return packages


def trusted_path(path):
    for target in [path, *path.parents]:
        info = target.stat()
        if info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or target.is_symlink():
            raise PermissionError("Installation files must be root-owned and not writable by other users")


def command(arguments):
    print("Running: " + " ".join(arguments), flush=True)
    subprocess.run(arguments, env=ENV, check=True)


def brave_repository():
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if not architecture:
        raise ValueError("Brave supports amd64 and arm64 in this installer")
    key_path = Path("/usr/share/keyrings/brave-browser-archive-keyring.gpg")
    source_path = Path("/etc/apt/sources.list.d/brave-browser-release.sources")
    # Refuse to overwrite a maintainer's existing setup; APT can use it unchanged.
    if source_path.exists() and key_path.exists():
        return
    if source_path.exists() or key_path.exists():
        raise RuntimeError("An incomplete Brave repository already exists; repair it first")
    url = "https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg"
    with urllib.request.urlopen(url, timeout=30) as response:
        if not response.geturl().startswith("https://brave-browser-apt-release.s3.brave.com/"):
            raise RuntimeError("Unexpected signing key redirect")
        key = response.read(1024 * 1024 + 1)
    if not key or len(key) > 1024 * 1024:
        raise RuntimeError("Invalid signing key size")
    source = ("Types: deb\nURIs: https://brave-browser-apt-release.s3.brave.com/\n"
              "Suites: stable\nComponents: main\nArchitectures: " + architecture +
              "\nSigned-By: " + str(key_path) + "\n")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    key_path.chmod(0o644)
    try:
        source_path.write_text(source)
        source_path.chmod(0o644)
    except Exception:
        key_path.unlink(missing_ok=True)
        raise


def main():
    if os.geteuid() != 0:
        raise PermissionError("Administrator authentication is required")
    trusted_path(Path(__file__).resolve())
    catalog_path = INSTALL_ROOT / "edukasaun_welcome/data/catalog.json"
    trusted_path(catalog_path)
    catalog = json.loads(catalog_path.read_text())
    if len(sys.argv) < 3:
        raise ValueError("Expected a source and application IDs")
    mode = sys.argv[1]
    packages = validated_packages(mode, sys.argv[2:], catalog)
    if mode == "brave":
        brave_repository()
    command(["/usr/bin/apt-get", "update"])
    # Refuse transactions that remove packages; handle dpkg locks through APT.
    command(["/usr/bin/apt-get", "--no-remove", "-s", "install", *packages])
    command(["/usr/bin/apt-get", "--no-remove", "-y", "install", *packages])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr, flush=True)
        sys.exit(1)
