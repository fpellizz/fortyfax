"""System prerequisite checker for Fortyfax."""

import shutil
import subprocess
import sys
from dataclasses import dataclass


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
        fix="sudo dnf install python3",
    )


def check_openfortivpn() -> CheckResult:
    path = shutil.which("openfortivpn")
    return CheckResult(
        name="openfortivpn",
        ok=path is not None,
        message=f"Trovato: {path}" if path else "Non trovato",
        fix="sudo dnf install openfortivpn",
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
            fix="sudo dnf install gtk4 python3-gobject",
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
            fix="sudo dnf install libadwaita python3-gobject",
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
            fix="sudo dnf install webkitgtk6.0",
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
            fix="sudo dnf install libsecret python3-gobject",
        )


def check_pkexec() -> CheckResult:
    path = shutil.which("pkexec")
    return CheckResult(
        name="pkexec (PolicyKit)",
        ok=path is not None,
        message=f"Trovato: {path}" if path else "Non trovato",
        fix="sudo dnf install polkit",
    )


def check_pppd() -> CheckResult:
    # openfortivpn needs pppd
    for p in ["/usr/sbin/pppd", "/sbin/pppd"]:
        if shutil.which("pppd") or __import__("os").path.exists(p):
            return CheckResult(name="pppd", ok=True, message=f"Trovato")
    return CheckResult(
        name="pppd",
        ok=False,
        message="Non trovato (necessario per openfortivpn)",
        fix="sudo dnf install ppp",
    )


ALL_CHECKS = [
    check_python_version,
    check_openfortivpn,
    check_gtk4,
    check_adwaita,
    check_webkitgtk,
    check_libsecret,
    check_pkexec,
    check_pppd,
]


def run_all_checks() -> list[CheckResult]:
    return [check() for check in ALL_CHECKS]


def get_missing_deps_install_command(results: list[CheckResult]) -> str | None:
    """Return a single dnf command to fix all missing deps, or None if all ok."""
    fixes = []
    for r in results:
        if not r.ok and r.fix:
            # Extract packages from 'sudo dnf install ...'
            parts = r.fix.split("install ")
            if len(parts) == 2:
                fixes.extend(parts[1].split())
    if not fixes:
        return None
    unique = list(dict.fromkeys(fixes))  # deduplicate preserving order
    return f"sudo dnf install -y {' '.join(unique)}"


def print_check_report(results: list[CheckResult]) -> bool:
    """Print a human-readable report. Returns True if all checks pass."""
    all_ok = True
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║          Fortyfax - Verifica Prerequisiti       ║")
    print("╠══════════════════════════════════════════════════════╣")
    for r in results:
        icon = "  ✓" if r.ok else "  ✗"
        print(f"║ {icon}  {r.name:<20} {r.message:<27}║")
        if not r.ok:
            all_ok = False
    print("╚══════════════════════════════════════════════════════╝")

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
