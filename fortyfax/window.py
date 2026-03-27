"""Main application window."""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk, Pango

from . import __app_name__, __version__
from .connection import ConnectionState, VPNConnection
from .dialogs import LogDialog, PasswordDialog, ProfileEditorDialog
from .profile import ProfileManager, VPNProfile

log = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, tray=None, **kwargs):
        super().__init__(
            title=__app_name__,
            default_width=520,
            default_height=620,
            **kwargs,
        )

        self._tray = tray
        self._profile_mgr = ProfileManager()
        self._connection = VPNConnection()
        self._connection.set_callbacks(
            on_state_changed=self._on_vpn_state_changed,
            on_log_line=self._on_vpn_log_line,
        )
        self._active_profile: VPNProfile | None = None
        self._log_dialog: LogDialog | None = None

        self._build_ui()
        self._refresh_profile_list()

    def _build_ui(self):
        # Main layout
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()

        # Add profile button
        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Nuovo profilo")
        add_btn.connect("clicked", self._on_add_profile)
        header.pack_start(add_btn)

        # Menu button
        menu = Gtk.PopoverMenu()
        menu_model = self._build_menu()
        menu.set_menu_model(menu_model)
        menu_btn = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
            menu_model=menu_model,
            tooltip_text="Menu",
        )
        header.pack_end(menu_btn)

        # Log button
        log_btn = Gtk.Button(icon_name="utilities-terminal-symbolic", tooltip_text="Mostra log")
        log_btn.connect("clicked", self._on_show_log)
        header.pack_end(log_btn)

        toolbar_view.add_top_bar(header)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Status banner
        self._status_banner = Adw.Banner(revealed=False)
        content.append(self._status_banner)

        # Connection status bar
        self._status_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_start=16, margin_end=16, margin_top=8, margin_bottom=8,
        )
        self._status_icon = Gtk.Image(icon_name="network-offline-symbolic")
        self._status_label = Gtk.Label(label="Disconnesso", xalign=0, hexpand=True)
        self._status_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._status_spinner = Gtk.Spinner(visible=False)
        self._status_bar.append(self._status_icon)
        self._status_bar.append(self._status_label)
        self._status_bar.append(self._status_spinner)
        content.append(self._status_bar)
        content.append(Gtk.Separator())

        # Profile list (scrollable)
        scrolled = Gtk.ScrolledWindow(vexpand=True)

        self._profiles_box = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            margin_start=0, margin_end=0,
        )
        self._profiles_box.add_css_class("boxed-list")
        self._profiles_box.set_margin_start(12)
        self._profiles_box.set_margin_end(12)
        self._profiles_box.set_margin_top(12)

        # Empty state
        self._empty_status = Adw.StatusPage(
            icon_name="network-vpn-symbolic",
            title="Nessun profilo VPN",
            description='Clicca "+" per creare un nuovo profilo di connessione',
        )

        self._stack = Gtk.Stack()
        self._stack.add_named(scrolled, "list")
        self._stack.add_named(self._empty_status, "empty")

        scrolled.set_child(self._profiles_box)
        content.append(self._stack)

        # Bottom action bar
        self._action_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=12, margin_end=12, margin_top=8, margin_bottom=12,
            halign=Gtk.Align.CENTER,
        )

        self._connect_btn = Gtk.Button(label="Connetti", hexpand=False)
        self._connect_btn.add_css_class("suggested-action")
        self._connect_btn.add_css_class("pill")
        self._connect_btn.set_size_request(160, -1)
        self._connect_btn.connect("clicked", self._on_connect_clicked)
        self._connect_btn.set_sensitive(False)

        self._disconnect_btn = Gtk.Button(label="Disconnetti", hexpand=False, visible=False)
        self._disconnect_btn.add_css_class("destructive-action")
        self._disconnect_btn.add_css_class("pill")
        self._disconnect_btn.set_size_request(160, -1)
        self._disconnect_btn.connect("clicked", self._on_disconnect_clicked)

        self._action_bar.append(self._connect_btn)
        self._action_bar.append(self._disconnect_btn)
        content.append(self._action_bar)

        toolbar_view.set_content(content)
        self.set_content(toolbar_view)

    def _build_menu(self):
        from gi.repository import Gio

        menu = Gio.Menu()
        menu.append("Preferenze", "app.preferences")
        menu.append("Verifica prerequisiti", "app.check-deps")
        menu.append("Informazioni", "app.about")
        return menu

    # --- Profile list ---

    def _refresh_profile_list(self):
        # Clear existing rows
        while True:
            row = self._profiles_box.get_row_at_index(0)
            if row is None:
                break
            self._profiles_box.remove(row)

        profiles = self._profile_mgr.load_all()

        if not profiles:
            self._stack.set_visible_child_name("empty")
            self._connect_btn.set_sensitive(False)
            return

        self._stack.set_visible_child_name("list")

        for profile in profiles:
            row = self._create_profile_row(profile)
            self._profiles_box.append(row)

    def _create_profile_row(self, profile: VPNProfile) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=profile.name,
            subtitle=f"{profile.display_host}  •  {profile.auth_method.upper()}",
            activatable=True,
        )
        row.set_name(profile.uid)

        # Radio-like selection via check button
        check = Gtk.CheckButton()
        check.set_name(profile.uid)
        if not hasattr(self, "_first_check"):
            self._first_check = check
            check.set_active(True)
            self._active_profile = profile
            self._connect_btn.set_sensitive(True)
        else:
            check.set_group(self._first_check)

        check.connect("toggled", self._on_profile_selected, profile)
        row.add_prefix(check)

        # Edit button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Modifica")
        edit_btn.connect("clicked", self._on_edit_profile, profile)
        row.add_suffix(edit_btn)

        # Delete button
        del_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        del_btn.add_css_class("flat")
        del_btn.set_tooltip_text("Elimina")
        del_btn.connect("clicked", self._on_delete_profile, profile)
        row.add_suffix(del_btn)

        # Connect on row activation
        row.connect("activated", self._on_row_activated, check, profile)

        return row

    def _on_row_activated(self, row, check, profile):
        check.set_active(True)
        self._active_profile = profile
        self._connect_btn.set_sensitive(True)

    def _on_profile_selected(self, check, profile):
        if check.get_active():
            self._active_profile = profile
            self._connect_btn.set_sensitive(True)
            if self._tray:
                self._tray.sync_selected_profile(profile)

    def select_profile_by_uid(self, uid: str):
        """Select a profile by UID (called from tray menu)."""
        profiles = self._profile_mgr.load_all()
        for profile in profiles:
            if profile.uid == uid:
                self._active_profile = profile
                self._connect_btn.set_sensitive(True)
                # Update radio buttons in the list
                idx = 0
                while True:
                    row = self._profiles_box.get_row_at_index(idx)
                    if row is None:
                        break
                    if row.get_name() == uid:
                        # Find the check button prefix
                        check = row.get_first_child()
                        while check is not None:
                            if isinstance(check, Gtk.CheckButton) and check.get_name() == uid:
                                check.set_active(True)
                                break
                            check = check.get_next_sibling()
                        break
                    idx += 1
                return

    # --- Profile CRUD ---

    def _on_add_profile(self, button):
        dialog = ProfileEditorDialog()
        dialog.connect("closed", self._on_editor_closed, None)
        dialog.present(self)

    def _on_edit_profile(self, button, profile):
        dialog = ProfileEditorDialog(profile=profile)
        dialog.connect("closed", self._on_editor_closed, profile.uid)
        dialog.present(self)

    def _on_editor_closed(self, dialog, old_uid):
        result = dialog.result
        if result is not None:
            self._profile_mgr.save(result)
            # Reset selection state
            if hasattr(self, "_first_check"):
                del self._first_check
            self._refresh_profile_list()

    def _on_delete_profile(self, button, profile):
        dialog = Adw.AlertDialog(
            heading=f"Eliminare «{profile.name}»?",
            body="Questa azione non può essere annullata.",
        )
        dialog.add_response("cancel", "Annulla")
        dialog.add_response("delete", "Elimina")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_confirmed, profile)
        dialog.present(self)

    def _on_delete_confirmed(self, dialog, response, profile):
        if response == "delete":
            self._profile_mgr.delete(profile.uid)
            if self._active_profile and self._active_profile.uid == profile.uid:
                self._active_profile = None
                self._connect_btn.set_sensitive(False)
            if hasattr(self, "_first_check"):
                del self._first_check
            self._refresh_profile_list()

    # --- Connection ---

    def _on_connect_clicked(self, button):
        if self._active_profile is None:
            return

        profile = self._active_profile

        if profile.auth_method == "saml":
            self._start_saml_auth(profile)
        else:
            self._start_password_auth(profile)

    def _start_saml_auth(self, profile: VPNProfile):
        try:
            from .auth import authenticate_saml
        except Exception as e:
            self._show_error(
                "WebKitGTK non disponibile",
                f"Per l'autenticazione SSO/SAML è necessario WebKitGTK 6.0.\n\n"
                f"Installalo con:\n  sudo dnf install webkitgtk6.0\n\nErrore: {e}",
            )
            return

        # Load SSO credentials for auto-fill
        sso_username = profile.sso_username
        sso_password = ""
        if sso_username:
            from .credential_store import lookup_sso_password
            sso_password = lookup_sso_password(profile.uid) or ""

        authenticate_saml(
            parent=self,
            host=profile.host,
            port=profile.port,
            realm=profile.realm,
            sso_username=sso_username,
            sso_password=sso_password,
            callback=lambda cookie: GLib.idle_add(self._on_saml_complete, cookie, profile),
        )

    def _on_saml_complete(self, cookie: str | None, profile: VPNProfile):
        if cookie is None:
            self._status_banner.set_title("Autenticazione SSO annullata")
            self._status_banner.set_revealed(True)
            GLib.timeout_add_seconds(5, lambda: self._status_banner.set_revealed(False))
            return
        self._connection.connect(profile, cookie=cookie)
        return False  # remove idle callback

    def _start_password_auth(self, profile: VPNProfile):
        dialog = PasswordDialog(profile_name=profile.name)
        dialog.connect("response", self._on_password_response, profile)
        dialog.present(self)

    def _on_password_response(self, dialog, response, profile):
        if response == "connect":
            password = dialog.password
            if password:
                self._connection.connect(profile, password=password)

    def _on_disconnect_clicked(self, button):
        self._connection.disconnect()

    # --- VPN state callbacks (called from background thread) ---

    def _on_vpn_state_changed(self, state: ConnectionState, message: str):
        GLib.idle_add(self._update_ui_state, state, message)
        if self._tray:
            self._tray.update_state(state, message)

    def _on_vpn_log_line(self, line: str):
        GLib.idle_add(self._append_log_line, line)

    def _update_ui_state(self, state: ConnectionState, message: str):
        if state == ConnectionState.DISCONNECTED:
            self._status_icon.set_from_icon_name("network-offline-symbolic")
            self._status_label.set_label(message or "Disconnesso")
            self._status_spinner.stop()
            self._status_spinner.set_visible(False)
            self._connect_btn.set_visible(True)
            self._connect_btn.set_sensitive(self._active_profile is not None)
            self._disconnect_btn.set_visible(False)
            self._set_profiles_sensitive(True)

        elif state == ConnectionState.CONNECTING:
            self._status_icon.set_from_icon_name("network-vpn-acquiring-symbolic")
            self._status_label.set_label(message or "Connessione in corso...")
            self._status_spinner.set_visible(True)
            self._status_spinner.start()
            self._connect_btn.set_visible(False)
            self._disconnect_btn.set_visible(True)
            self._set_profiles_sensitive(False)

        elif state == ConnectionState.CONNECTED:
            self._status_icon.set_from_icon_name("network-vpn-symbolic")
            self._status_label.set_label(message or "Connesso")
            self._status_spinner.stop()
            self._status_spinner.set_visible(False)
            self._connect_btn.set_visible(False)
            self._disconnect_btn.set_visible(True)
            self._set_profiles_sensitive(False)
            self._status_banner.set_title("VPN connessa")
            self._status_banner.set_revealed(True)
            GLib.timeout_add_seconds(3, lambda: self._status_banner.set_revealed(False))

        elif state == ConnectionState.DISCONNECTING:
            self._status_icon.set_from_icon_name("network-vpn-acquiring-symbolic")
            self._status_label.set_label(message or "Disconnessione...")
            self._status_spinner.set_visible(True)
            self._status_spinner.start()
            self._disconnect_btn.set_sensitive(False)

        elif state == ConnectionState.ERROR:
            self._status_icon.set_from_icon_name("dialog-error-symbolic")
            self._status_label.set_label(message or "Errore")
            self._status_spinner.stop()
            self._status_spinner.set_visible(False)
            self._connect_btn.set_visible(True)
            self._connect_btn.set_sensitive(self._active_profile is not None)
            self._disconnect_btn.set_visible(False)
            self._set_profiles_sensitive(True)
            self._show_error("Errore di connessione", message)

        return False  # remove idle

    def _set_profiles_sensitive(self, sensitive: bool):
        self._profiles_box.set_sensitive(sensitive)

    def _append_log_line(self, line: str):
        if self._log_dialog is not None:
            self._log_dialog.append_line(line)
        return False

    # --- Log ---

    def _on_show_log(self, button):
        self._log_dialog = LogDialog()
        self._log_dialog.set_log_text(self._connection.log_text)
        self._log_dialog.connect("closed", self._on_log_closed)
        self._log_dialog.present(self)

    def _on_log_closed(self, dialog):
        self._log_dialog = None

    # --- Helpers ---

    def _show_error(self, heading: str, body: str):
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "OK")
        dialog.present(self)
