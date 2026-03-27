"""Main Adwaita application."""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from . import __app_id__, __app_name__, __version__
from . import settings
from .check import get_missing_deps_install_command, run_all_checks
from .tray import TrayIcon
from .window import MainWindow

log = logging.getLogger(__name__)


class FortyfaxApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._window = None
        self._tray = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        settings.apply_theme()
        self._setup_actions()
        try:
            self._tray = TrayIcon(self)
        except Exception as e:
            log.warning("Could not initialize tray icon: %s", e)

    def do_activate(self):
        if self._window is None:
            self._window = MainWindow(application=self, tray=self._tray)
            # When tray is active, hide window on close instead of quitting
            if self._tray:
                self._window.connect("close-request", self._on_window_close_request)
        self._window.present()

    def _on_window_close_request(self, window):
        window.set_visible(False)
        return True  # prevent default close/destroy

    @property
    def tray(self):
        return self._tray

    def _setup_actions(self):
        actions = {
            "preferences": self._on_preferences,
            "export-profiles": self._on_export_profiles,
            "import-profiles": self._on_import_profiles,
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
        self.set_accels_for_action("app.preferences", ["<primary>comma"])

    def _on_preferences(self, action, param):
        from .dialogs import PreferencesDialog

        dialog = PreferencesDialog()
        dialog.present(self._window)

    def _on_export_profiles(self, action, param):
        from pathlib import Path
        from .profile import ProfileManager

        mgr = ProfileManager()
        profiles = mgr.load_all()
        if not profiles:
            dialog = Adw.AlertDialog(heading="Nessun profilo", body="Non ci sono profili da esportare.")
            dialog.add_response("ok", "OK")
            dialog.present(self._window)
            return

        file_dialog = Gtk.FileDialog(
            title="Esporta profili",
            initial_name="fortyfax-profiles.json",
        )
        json_filter = Gtk.FileFilter()
        json_filter.set_name("File JSON")
        json_filter.add_pattern("*.json")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(json_filter)
        file_dialog.set_filters(filters)

        file_dialog.save(self._window, None, self._on_export_save_response)

    def _on_export_save_response(self, dialog, result):
        from pathlib import Path
        from .profile import ProfileManager

        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return  # user cancelled

        path = Path(gfile.get_path())
        mgr = ProfileManager()
        count = mgr.export_profiles(path)

        msg = Adw.AlertDialog(heading="Esportazione completata", body=f"{count} profili esportati in:\n{path}")
        msg.add_response("ok", "OK")
        msg.present(self._window)

    def _on_import_profiles(self, action, param):
        file_dialog = Gtk.FileDialog(title="Importa profili")
        json_filter = Gtk.FileFilter()
        json_filter.set_name("File JSON")
        json_filter.add_pattern("*.json")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(json_filter)
        file_dialog.set_filters(filters)

        file_dialog.open(self._window, None, self._on_import_open_response)

    def _on_import_open_response(self, dialog, result):
        from pathlib import Path
        from .profile import ProfileManager

        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return  # user cancelled

        path = Path(gfile.get_path())
        mgr = ProfileManager()
        count, errors = mgr.import_profiles(path)

        lines = [f"{count} profili importati."]
        if errors:
            lines.append("")
            lines.append("Errori:")
            lines.extend(f"  - {e}" for e in errors)

        msg = Adw.AlertDialog(
            heading="Importazione completata" if count > 0 else "Importazione fallita",
            body="\n".join(lines),
        )
        msg.add_response("ok", "OK")
        msg.present(self._window)

        # Refresh profile list in window
        if count > 0 and self._window and hasattr(self._window, "_refresh_profile_list"):
            if hasattr(self._window, "_first_check"):
                del self._window._first_check
            self._window._refresh_profile_list()

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=__app_name__,
            application_icon="network-vpn-symbolic",
            version=__version__,
            developer_name="Fortyfax",
            comments="GUI per openfortivpn con supporto SAML/SSO",
            license_type=Gtk.License.GPL_3_0,
            website="https://bitbucket.org/decisyon/fortyfax",
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
        if self._tray:
            self._tray.shutdown()
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
