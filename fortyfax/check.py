"""System prerequisite checker for Fortyfax."""

import shutil
import sys
from dataclasses import dataclass

from . import distro


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    fix: str = ""


def check_python_version() -> CheckResult:
    v = sys.version_info
    ok = v >= (3, 10)
    return CheckResult(
        name="Python >= 3.10",
        ok=ok,
        message=f"Python {v.major}.{v.minor}.{v.micro}" if ok else f"Python {v.major}.{v.minor} è troppo vecchio",
        fix=distro.fix_for("python3"),
    )


def check_openfortivpn() -> CheckResult:
    path = shutil.which("openfortivpn")
    return CheckResult(
        name="openfortivpn",
        ok=path is not None,
        message=f"Trovato: {path}" if path else "Non trovato",
        fix=distro.fix_for("openfortivpn"),
    )


def check_gtk4() -> CheckResult:
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk  # noqa: F401
        return CheckResult(name="GTK 4", ok=True, message="OK")
    except (ImportError, ValueError) as e:
        return CheckResult(
            name="GTK 4",
            ok=False,
            message=str(e),
            fix=distro.install_cmd(["gtk4", "python3-gobject"]),
        )


def check_adwaita() -> CheckResult:
    try:
        import gi
        gi.require_version("Adw", "1")
        from gi.repository import Adw  # noqa: F401
        return CheckResult(name="libadwaita", ok=True, message="OK")
    except (ImportError, ValueError) as e:
        return CheckResult(
            name="libadwaita",
            ok=False,
            message=str(e),
            fix=distro.install_cmd(["libadwaita", "python3-gobject"]),
        )


def check_webkitgtk() -> CheckResult:
    try:
        import gi
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
        return CheckResult(name="WebKitGTK 6.0", ok=True, message="OK")
    except (ImportError, ValueError) as e:
        return CheckResult(
            name="WebKitGTK 6.0",
            ok=False,
            message=str(e),
            fix=distro.fix_for("webkitgtk6.0"),
        )


def check_libsecret() -> CheckResult:
    try:
        import gi
        gi.require_version("Secret", "1")
        from gi.repository import Secret  # noqa: F401
        return CheckResult(name="libsecret", ok=True, message="OK")
    except (ImportError, ValueError) as e:
        return CheckResult(
            name="libsecret",
            ok=False,
            message=str(e),
            fix=distro.install_cmd(["libsecret", "python3-gobject"]),
        )


def check_pkexec() -> CheckResult:
    path = shutil.which("pkexec")
    return CheckResult(
        name="pkexec (PolicyKit)",
        ok=path is not None,
        message=f"Trovato: {path}" if path else "Non trovato",
        fix=distro.fix_for("polkit"),
    )


def check_appindicator() -> CheckResult:
    try:
        import gi
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3  # noqa: F401
        return CheckResult(name="AppIndicator3", ok=True, message="OK")
    except (ImportError, ValueError) as e:
        return CheckResult(
            name="AppIndicator3",
            ok=False,
            message=str(e),
            fix=distro.fix_for("libappindicator-gtk3"),
        )


def check_pppd() -> CheckResult:
    import os
    for p in ["/usr/sbin/pppd", "/sbin/pppd"]:
        if shutil.which("pppd") or os.path.exists(p):
            return CheckResult(name="pppd", ok=True, message="Trovato")
    return CheckResult(
        name="pppd",
        ok=False,
        message="Non trovato (necessario per openfortivpn)",
        fix=distro.fix_for("ppp"),
    )


def check_gpclient() -> CheckResult:
    path = shutil.which("gpclient")
    if path:
        return CheckResult(
            name="gpclient (GlobalProtect)",
            ok=True,
            message=f"Trovato: {path}",
        )
    return CheckResult(
        name="gpclient (GlobalProtect)",
        ok=False,
        message="Non trovato (necessario per VPN Palo Alto)",
        fix=distro.gpclient_install_instructions(),
    )


def check_openconnect() -> CheckResult:
    path = shutil.which("openconnect")
    if path:
        return CheckResult(
            name="openconnect",
            ok=True,
            message=f"Trovato: {path}",
        )
    return CheckResult(
        name="openconnect",
        ok=False,
        message="Non trovato (necessario per GlobalProtect)",
        fix=distro.fix_for("openconnect"),
    )


def check_vpnc_script() -> CheckResult:
    import os
    for path in [
        "/usr/share/vpnc-scripts/vpnc-script",
        "/etc/vpnc/vpnc-script",
        "/usr/sbin/vpnc-script",
    ]:
        if os.path.isfile(path):
            return CheckResult(
                name="vpnc-script",
                ok=True,
                message=f"Trovato: {path}",
            )
    return CheckResult(
        name="vpnc-script",
        ok=False,
        message="Non trovato (necessario per GlobalProtect)",
        fix=distro.fix_for("vpnc-script"),
    )


# Core checks (always run)
CORE_CHECKS = [
    check_python_version,
    check_gtk4,
    check_adwaita,
    check_webkitgtk,
    check_libsecret,
    check_pkexec,
    check_appindicator,
]

# Fortinet-specific checks
FORTINET_CHECKS = [
    check_openfortivpn,
    check_pppd,
]

# GlobalProtect-specific checks
GLOBALPROTECT_CHECKS = [
    check_gpclient,
    check_openconnect,
    check_vpnc_script,
]

ALL_CHECKS = CORE_CHECKS + FORTINET_CHECKS + GLOBALPROTECT_CHECKS


def run_all_checks() -> list[CheckResult]:
    return [check() for check in ALL_CHECKS]


def get_missing_deps_install_command(results: list[CheckResult]) -> str | None:
    """Return a single install command to fix all missing simple deps."""
    packages = []
    for r in results:
        if not r.ok and r.fix:
            # Only aggregate simple "sudo <pm> install" commands, not multi-step ones
            parts = r.fix.split("install ")
            if len(parts) == 2 and "&&" not in r.fix:
                # Strip -y flag since we add our own
                pkgs = [p for p in parts[1].strip().split() if p != "-y"]
                packages.extend(pkgs)
    if not packages:
        return None
    unique = list(dict.fromkeys(packages))  # deduplicate preserving order
    pm = distro.pkg_manager()
    return f"sudo {pm} install -y {' '.join(unique)}"


def print_check_report(results: list[CheckResult]) -> bool:
    """Print a human-readable report. Returns True if all checks pass."""
    all_ok = True
    family = distro.detect()
    label = {"redhat": "Fedora/RHEL", "debian": "Debian/Ubuntu"}.get(family, "Linux")

    print(f"\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║       Fortyfax - Verifica Prerequisiti ({label:<14})    ║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    for r in results:
        icon = "  ✓" if r.ok else "  ✗"
        print(f"║ {icon}  {r.name:<24} {r.message:<30}║")
        if not r.ok:
            all_ok = False
    print("╚══════════════════════════════════════════════════════════════╝")

    if not all_ok:
        cmd = get_missing_deps_install_command(results)
        print("\n⚠  Alcune dipendenze mancano!")
        if cmd:
            print(f"\nPer installarle tutte in un colpo:\n\n  {cmd}\n")
        for r in results:
            if not r.ok and r.fix:
                print(f"  • {r.name}: {r.fix}")
        print()
    else:
        print("\n✓ Tutti i prerequisiti sono soddisfatti!\n")

    return all_ok


if __name__ == "__main__":
    results = run_all_checks()
    ok = print_check_report(results)
    sys.exit(0 if ok else 1)
