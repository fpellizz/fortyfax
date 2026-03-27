"""Dialog windows for profile editing and settings."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .profile import VPNProfile
from . import settings
from . import credential_store


class ProfileEditorDialog(Adw.Dialog):
    """Dialog for creating/editing a VPN profile."""

    def __init__(self, profile: VPNProfile | None = None, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Modifica Profilo" if profile else "Nuovo Profilo")
        self.set_content_width(550)
        self.set_content_height(680)

        self._profile = profile or VPNProfile()
        self._result: VPNProfile | None = None

        self._build_ui()
        self._populate()

    @property
    def result(self) -> VPNProfile | None:
        return self._result

    def _build_ui(self):
        # Toolbar view
        toolbar = Adw.ToolbarView()

        # Header
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Annulla")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Salva")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)
        self._save_btn = save_btn

        toolbar.add_top_bar(header)

        # Content - scrolled
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        clamp = Adw.Clamp(maximum_size=500, margin_top=12, margin_bottom=12,
                          margin_start=12, margin_end=12)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)

        # --- General group ---
        general_group = Adw.PreferencesGroup(title="Generale")

        self._name_row = Adw.EntryRow(title="Nome profilo")
        general_group.add(self._name_row)

        self._host_row = Adw.EntryRow(title="Host server VPN")
        self._host_row.set_input_purpose(Gtk.InputPurpose.URL)
        general_group.add(self._host_row)

        self._port_adj = Gtk.Adjustment(value=443, lower=1, upper=65535, step_increment=1)
        self._port_row = Adw.SpinRow(
            title="Porta", adjustment=self._port_adj, climb_rate=1, digits=0
        )
        general_group.add(self._port_row)

        main_box.append(general_group)

        # --- Authentication group ---
        auth_group = Adw.PreferencesGroup(title="Autenticazione")

        # Auth method selector
        self._auth_saml_check = Gtk.CheckButton(label="SAML / SSO (browser)")
        self._auth_pass_check = Gtk.CheckButton(label="Username / Password")
        self._auth_pass_check.set_group(self._auth_saml_check)

        auth_method_row = Adw.ActionRow(title="Metodo")
        method_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                             margin_top=8, margin_bottom=8)
        method_box.append(self._auth_saml_check)
        method_box.append(self._auth_pass_check)
        auth_method_row.set_child(method_box)
        auth_group.add(auth_method_row)

        self._username_row = Adw.EntryRow(title="Username")
        auth_group.add(self._username_row)

        self._realm_row = Adw.EntryRow(title="Realm (opzionale)")
        auth_group.add(self._realm_row)

        self._auth_saml_check.connect("toggled", self._on_auth_method_changed)
        self._auth_pass_check.connect("toggled", self._on_auth_method_changed)

        main_box.append(auth_group)

        # --- SSO Credentials group ---
        self._sso_group = Adw.PreferencesGroup(
            title="Credenziali SSO",
            description="Compilazione automatica del form di login dell'Identity Provider",
        )

        self._sso_username_row = Adw.EntryRow(title="Email / Username SSO")
        self._sso_username_row.set_input_purpose(Gtk.InputPurpose.EMAIL)
        self._sso_group.add(self._sso_username_row)

        self._sso_password_row = Adw.PasswordEntryRow(title="Password SSO")
        self._sso_group.add(self._sso_password_row)

        sso_info = Adw.ActionRow(
            subtitle="Le credenziali vengono usate per compilare automaticamente "
                     "il form di login SSO. La password è salvata nel portachiavi di sistema."
        )
        sso_info.add_css_class("property")
        self._sso_group.add(sso_info)

        main_box.append(self._sso_group)

        # --- Security group ---
        security_group = Adw.PreferencesGroup(title="Sicurezza")

        self._cert_row = Adw.EntryRow(title="Certificato trusted (SHA256)")
        self._cert_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        security_group.add(self._cert_row)

        cert_info = Adw.ActionRow(
            subtitle="L'hash SHA256 del certificato del server. "
                     "Lo trovi nel log alla prima connessione."
        )
        cert_info.add_css_class("property")
        security_group.add(cert_info)

        main_box.append(security_group)

        # --- Network group ---
        network_group = Adw.PreferencesGroup(title="Rete")

        self._routes_switch = Adw.SwitchRow(title="Imposta rotte", subtitle="Aggiungi le rotte VPN alla tabella di routing")
        network_group.add(self._routes_switch)

        self._dns_switch = Adw.SwitchRow(title="Imposta DNS", subtitle="Configura i DNS tramite il tunnel VPN")
        network_group.add(self._dns_switch)

        self._peerdns_switch = Adw.SwitchRow(title="PPP Peer DNS", subtitle="Usa i DNS forniti dal peer PPP")
        network_group.add(self._peerdns_switch)

        self._half_routes_switch = Adw.SwitchRow(
            title="Half internet routes",
            subtitle="Usa 0.0.0.0/1 + 128.0.0.0/1 invece di rotta default"
        )
        network_group.add(self._half_routes_switch)

        main_box.append(network_group)

        # --- Advanced group ---
        advanced_group = Adw.PreferencesGroup(title="Avanzate")

        self._extra_args_row = Adw.EntryRow(title="Argomenti extra per openfortivpn")
        advanced_group.add(self._extra_args_row)

        main_box.append(advanced_group)

        clamp.set_child(main_box)
        scrolled.set_child(clamp)
        toolbar.set_content(scrolled)

        self.set_child(toolbar)

    def _populate(self):
        """Fill UI with profile data."""
        p = self._profile
        self._name_row.set_text(p.name)
        self._host_row.set_text(p.host)
        self._port_adj.set_value(p.port)
        self._username_row.set_text(p.username)
        self._realm_row.set_text(p.realm)
        self._cert_row.set_text(p.trusted_cert)
        self._routes_switch.set_active(p.set_routes)
        self._dns_switch.set_active(p.set_dns)
        self._peerdns_switch.set_active(p.pppd_use_peerdns)
        self._half_routes_switch.set_active(p.half_internet_routes)
        self._extra_args_row.set_text(p.extra_args)

        # SSO credentials
        self._sso_username_row.set_text(p.sso_username)
        sso_pwd = credential_store.lookup_sso_password(p.uid)
        if sso_pwd:
            self._sso_password_row.set_text(sso_pwd)

        if p.auth_method == "saml":
            self._auth_saml_check.set_active(True)
        else:
            self._auth_pass_check.set_active(True)

        self._on_auth_method_changed(None)

    def _on_auth_method_changed(self, widget):
        is_password = self._auth_pass_check.get_active()
        self._username_row.set_sensitive(is_password)
        self._sso_group.set_sensitive(not is_password)

    def _on_save(self, button):
        p = self._profile
        p.name = self._name_row.get_text().strip()
        p.host = self._host_row.get_text().strip()
        p.port = int(self._port_adj.get_value())
        p.username = self._username_row.get_text().strip()
        p.realm = self._realm_row.get_text().strip()
        p.trusted_cert = self._cert_row.get_text().strip()
        p.auth_method = "saml" if self._auth_saml_check.get_active() else "password"
        p.set_routes = self._routes_switch.get_active()
        p.set_dns = self._dns_switch.get_active()
        p.pppd_use_peerdns = self._peerdns_switch.get_active()
        p.half_internet_routes = self._half_routes_switch.get_active()
        p.extra_args = self._extra_args_row.get_text().strip()
        p.sso_username = self._sso_username_row.get_text().strip()

        # Save SSO password in keyring
        sso_pwd = self._sso_password_row.get_text()
        if sso_pwd:
            credential_store.store_sso_password(p.uid, p.name, sso_pwd)
        else:
            credential_store.clear_sso_password(p.uid)

        errors = p.validate()
        if errors:
            self._show_validation_errors(errors)
            return

        self._result = p
        self.close()

    def _show_validation_errors(self, errors: list[str]):
        msg = "\n".join(f"• {e}" for e in errors)
        dialog = Adw.AlertDialog(
            heading="Errori di validazione",
            body=msg,
        )
        dialog.add_response("ok", "OK")
        dialog.present(self)


class PasswordDialog(Adw.AlertDialog):
    """Dialog to ask for VPN password."""

    def __init__(self, profile_name: str, **kwargs):
        super().__init__(
            heading=f"Password per {profile_name}",
            body="Inserisci la password per la connessione VPN.",
            **kwargs,
        )
        self.add_response("cancel", "Annulla")
        self.add_response("connect", "Connetti")
        self.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("connect")
        self.set_close_response("cancel")

        self._password_entry = Gtk.PasswordEntry(
            show_peek_icon=True,
            placeholder_text="Password",
        )
        self._password_entry.set_margin_top(12)
        self.set_extra_child(self._password_entry)

    @property
    def password(self) -> str:
        return self._password_entry.get_text()


class PreferencesDialog(Adw.PreferencesDialog):
    """Application preferences dialog."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Preferenze")

        page = Adw.PreferencesPage(
            title="Generali",
            icon_name="preferences-system-symbolic",
        )

        # --- Appearance group ---
        appearance_group = Adw.PreferencesGroup(
            title="Aspetto",
            description="Personalizza l'aspetto dell'applicazione",
        )

        self._theme_row = Adw.ComboRow(title="Tema", subtitle="Seleziona il tema dell'interfaccia")
        theme_list = Gtk.StringList.new(["Sistema", "Chiaro", "Scuro"])
        self._theme_row.set_model(theme_list)

        # Set current value
        current = settings.get("theme")
        idx = {"system": 0, "light": 1, "dark": 2}.get(current, 0)
        self._theme_row.set_selected(idx)

        self._theme_row.connect("notify::selected", self._on_theme_changed)
        appearance_group.add(self._theme_row)

        page.add(appearance_group)
        self.add(page)

    def _on_theme_changed(self, row, pspec):
        idx = row.get_selected()
        theme_key = {0: "system", 1: "light", 2: "dark"}.get(idx, "system")
        settings.set("theme", theme_key)
        settings.apply_theme()


class LogDialog(Adw.Dialog):
    """Dialog showing VPN connection logs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Log Connessione")
        self.set_content_width(700)
        self.set_content_height(500)

        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic", tooltip_text="Pulisci log")
        clear_btn.connect("clicked", self._on_clear)
        header.pack_end(clear_btn)
        toolbar.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        self._textview = Gtk.TextView(
            editable=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=8,
            bottom_margin=8,
            left_margin=8,
            right_margin=8,
        )
        scrolled.set_child(self._textview)
        toolbar.set_content(scrolled)

        self.set_child(toolbar)

    def set_log_text(self, text: str):
        self._textview.get_buffer().set_text(text)
        # Scroll to bottom
        buf = self._textview.get_buffer()
        mark = buf.get_insert()
        buf.place_cursor(buf.get_end_iter())
        self._textview.scroll_mark_onscreen(mark)

    def append_line(self, line: str):
        buf = self._textview.get_buffer()
        end = buf.get_end_iter()
        buf.insert(end, line + "\n")
        mark = buf.get_insert()
        buf.place_cursor(buf.get_end_iter())
        self._textview.scroll_mark_onscreen(mark)

    def _on_clear(self, button):
        self._textview.get_buffer().set_text("")
