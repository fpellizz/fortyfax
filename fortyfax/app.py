"""Main Adwaita application."""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from . import __app_id__, __app_name__, __version__
from .check import get_missing_deps_install_command, run_all_checks
from .window import MainWindow

log = logging.getLogger(__name__)


class FortyfaxApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._window = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._setup_actions()

    def do_activate(self):
        if self._window is None:
            self._window = MainWindow(application=self)
        self._window.present()

    def _setup_actions(self):
        actions = {
            "about": self._on_about,
            "check-deps": self._on_check_deps,
            "quit": self._on_quit,
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # Keyboard shortcuts
        self.set_accels_for_action("app.quit", ["<primary>q"])

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=__app_name__,
            application_icon="network-vpn-symbolic",
            version=__version__,
            developer_name="Fortyfax",
            comments="GUI per openfortivpn con supporto SAML/SSO",
            license_type=Gtk.License.GPL_3_0,
            website="",  # TODO: impostare URL repository quando disponibile
        )
        about.present(self._window)

    def _on_check_deps(self, action, param):
        results = run_all_checks()
        all_ok = all(r.ok for r in results)

        if all_ok:
            body = "Tutti i prerequisiti sono soddisfatti."
            dialog = Adw.AlertDialog(
                heading="Prerequisiti OK",
                body=body,
            )
            dialog.add_response("ok", "OK")
        else:
            lines = []
            for r in results:
                icon = "✓" if r.ok else "✗"
                lines.append(f"{icon}  {r.name}: {r.message}")
                if not r.ok and r.fix:
                    lines.append(f"    Risolvi con: {r.fix}")

            cmd = get_missing_deps_install_command(results)
            if cmd:
                lines.append(f"\nComando unico per risolvere tutto:\n{cmd}")

            dialog = Adw.AlertDialog(
                heading="Dipendenze mancanti",
                body="\n".join(lines),
            )
            dialog.add_response("ok", "OK")

        dialog.present(self._window)

    def _on_quit(self, action, param):
        self.quit()


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Quick prerequisite check before launching
    critical_checks = run_all_checks()
    critical_failed = [r for r in critical_checks if not r.ok and r.name in ("GTK 4", "libadwaita", "Python >= 3.10")]

    if critical_failed:
        print("\n╔══════════════════════════════════════════════════════╗")
        print("║  ERRORE: Dipendenze critiche mancanti!              ║")
        print("╠══════════════════════════════════════════════════════╣")
        for r in critical_failed:
            print(f"║  ✗ {r.name:<20} {r.message:<27}║")
            if r.fix:
                print(f"║    → {r.fix:<46}║")
        print("╚══════════════════════════════════════════════════════╝")
        cmd = get_missing_deps_install_command(critical_failed)
        if cmd:
            print(f"\nEsegui: {cmd}\n")
        sys.exit(1)

    # Non-critical warnings
    warnings = [r for r in critical_checks if not r.ok and r.name not in ("GTK 4", "libadwaita", "Python >= 3.10")]
    if warnings:
        for r in warnings:
            log.warning("Dipendenza opzionale mancante: %s — %s (fix: %s)", r.name, r.message, r.fix)

    app = FortyfaxApp()
    return app.run(sys.argv)
