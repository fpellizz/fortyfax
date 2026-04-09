"""Linux distribution detection and package name mapping.

Detects whether the system is RedHat-based (Fedora, RHEL, CentOS) or
Debian-based (Ubuntu, Debian, Mint, Pop!_OS) and provides the correct
package names and install commands for each.
"""

import logging
import os

log = logging.getLogger(__name__)

# Distro families
REDHAT = "redhat"
DEBIAN = "debian"
UNKNOWN = "unknown"

_detected: str | None = None


def detect() -> str:
    """Detect the distro family from /etc/os-release. Cached after first call."""
    global _detected
    if _detected is not None:
        return _detected

    _detected = UNKNOWN
    try:
        if os.path.isfile("/etc/os-release"):
            with open("/etc/os-release") as f:
                content = f.read().lower()
            # Parse ID and ID_LIKE
            id_val = ""
            id_like = ""
            for line in content.splitlines():
                if line.startswith("id="):
                    id_val = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("id_like="):
                    id_like = line.split("=", 1)[1].strip().strip('"')

            all_ids = f"{id_val} {id_like}"
            if any(d in all_ids for d in ("fedora", "rhel", "centos", "rocky", "alma")):
                _detected = REDHAT
            elif any(d in all_ids for d in ("debian", "ubuntu", "mint", "pop")):
                _detected = DEBIAN
    except Exception as e:
        log.warning("Failed to detect distro: %s", e)

    log.info("Detected distro family: %s", _detected)
    return _detected


def pkg_manager() -> str:
    """Return the package manager command for this distro."""
    family = detect()
    if family == DEBIAN:
        return "apt"
    return "dnf"


def install_cmd(packages: str | list[str]) -> str:
    """Build an install command for the given package(s).

    Args:
        packages: package name(s) — can be a string "pkg1 pkg2" or a list.
                  Use the Fedora package name; it will be mapped automatically
                  if on Debian.
    """
    if isinstance(packages, str):
        packages = packages.split()

    family = detect()
    if family == DEBIAN:
        mapped = [_PACKAGE_MAP.get(p, {}).get("debian", p) for p in packages]
        return f"sudo apt install -y {' '.join(mapped)}"
    else:
        mapped = [_PACKAGE_MAP.get(p, {}).get("redhat", p) for p in packages]
        return f"sudo dnf install -y {' '.join(mapped)}"


def fix_for(fedora_pkg: str) -> str:
    """Return the install command for a single Fedora package name, mapped to current distro."""
    return install_cmd(fedora_pkg)


def gpclient_install_instructions() -> str:
    """Return instructions for installing gpclient (GlobalProtect-openconnect)."""
    family = detect()
    if family == DEBIAN:
        return (
            "sudo add-apt-repository ppa:yuezk/globalprotect-openconnect && "
            "sudo apt install -y globalprotect-openconnect"
        )
    return (
        "sudo dnf copr enable yuezk/globalprotect-openconnect && "
        "sudo dnf install -y globalprotect-openconnect"
    )


# Mapping: Fedora package name -> {redhat: ..., debian: ...}
_PACKAGE_MAP = {
    "python3": {
        "redhat": "python3",
        "debian": "python3",
    },
    "python3-gobject": {
        "redhat": "python3-gobject",
        "debian": "python3-gi",
    },
    "gtk4": {
        "redhat": "gtk4",
        "debian": "gir1.2-gtk-4.0",
    },
    "libadwaita": {
        "redhat": "libadwaita",
        "debian": "gir1.2-adw-1",
    },
    "webkitgtk6.0": {
        "redhat": "webkitgtk6.0",
        "debian": "gir1.2-webkit-6.0",
    },
    "libsecret": {
        "redhat": "libsecret",
        "debian": "gir1.2-secret-1",
    },
    "polkit": {
        "redhat": "polkit",
        "debian": "policykit-1",
    },
    "libappindicator-gtk3": {
        "redhat": "libappindicator-gtk3",
        "debian": "gir1.2-appindicator3-0.1",
    },
    "openfortivpn": {
        "redhat": "openfortivpn",
        "debian": "openfortivpn",
    },
    "ppp": {
        "redhat": "ppp",
        "debian": "ppp",
    },
    "openconnect": {
        "redhat": "openconnect",
        "debian": "openconnect",
    },
    "vpnc-script": {
        "redhat": "vpnc-script",
        "debian": "vpnc",
    },
    "globalprotect-openconnect": {
        "redhat": "globalprotect-openconnect",
        "debian": "globalprotect-openconnect",
    },
}
