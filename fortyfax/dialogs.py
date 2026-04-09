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

        # VPN type selector
        self._vpn_type_row = Adw.ComboRow(
            title="Tipo VPN",
            subtitle="Seleziona il tipo di server VPN",
        )
        vpn_type_list = Gtk.StringList.new(["Fortinet (openfortivpn)", "GlobalProtect (Palo Alto)"])
        self._vpn_type_row.set_model(vpn_type_list)
        self._vpn_type_row.connect("notify::selected", self._on_vpn_type_changed)
        general_group.add(self._vpn_type_row)

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

        self._vpn_password_row = Adw.PasswordEntryRow(title="Password VPN")
        auth_group.add(self._vpn_password_row)

        vpn_pwd_info = Adw.ActionRow(
            subtitle="Se compilata, la password viene usata automaticamente "
                     "alla connessione. Salvata cifrata nel profilo."
        )
        vpn_pwd_info.add_css_class("property")
        auth_group.add(vpn_pwd_info)
        self._vpn_pwd_info = vpn_pwd_info

        self._auth_saml_check.connect("toggled", self._on_auth_method_changed)
        self._auth_pass_check.connect("toggled", self._on_auth_method_changed)

        main_box.append(auth_group)

        # --- SSO Credentials group (Fortinet only: auto-fill webview) ---
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

        # --- Security group (Fortinet only) ---
        self._security_group = Adw.PreferencesGroup(title="Sicurezza")

        self._cert_row = Adw.EntryRow(title="Certificato trusted (SHA256)")
        self._cert_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        self._security_group.add(self._cert_row)

        cert_info = Adw.ActionRow(
            subtitle="L'hash SHA256 del certificato del server. "
                     "Lo trovi nel log alla prima connessione."
        )
        cert_info.add_css_class("property")
        self._security_group.add(cert_info)

        main_box.append(self._security_group)

        # --- Network group (Fortinet only) ---
        self._network_group = Adw.PreferencesGroup(title="Rete")

        self._routes_switch = Adw.SwitchRow(title="Imposta rotte", subtitle="Aggiungi le rotte VPN alla tabella di routing")
        self._network_group.add(self._routes_switch)

        self._dns_switch = Adw.SwitchRow(title="Imposta DNS", subtitle="Configura i DNS tramite il tunnel VPN")
        self._network_group.add(self._dns_switch)

        self._peerdns_switch = Adw.SwitchRow(title="PPP Peer DNS", subtitle="Usa i DNS forniti dal peer PPP")
        self._network_group.add(self._peerdns_switch)

        self._half_routes_switch = Adw.SwitchRow(
            title="Half internet routes",
            subtitle="Usa 0.0.0.0/1 + 128.0.0.0/1 invece di rotta default"
        )
        self._network_group.add(self._half_routes_switch)

        main_box.append(self._network_group)

        # --- GlobalProtect group ---
        self._gp_group = Adw.PreferencesGroup(
            title="GlobalProtect",
            description="Impostazioni specifiche per Palo Alto GlobalProtect",
        )

        self._gp_gateway_row = Adw.EntryRow(title="Gateway (opzionale)")
        self._gp_gateway_row.set_input_purpose(Gtk.InputPurpose.URL)
        self._gp_group.add(self._gp_gateway_row)

        self._gp_extra_dns_row = Adw.EntryRow(title="Domini DNS extra (separati da spazio)")
        self._gp_extra_dns_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        self._gp_group.add(self._gp_extra_dns_row)

        self._gp_vpn_dns_row = Adw.EntryRow(title="IP DNS VPN (opzionale)")
        self._gp_vpn_dns_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        self._gp_group.add(self._gp_vpn_dns_row)

        self._gp_hip_switch = Adw.SwitchRow(
            title="HIP Report",
            subtitle="Invia Host Identity Profile report al server",
        )
        self._gp_group.add(self._gp_hip_switch)

        self._gp_mtu_adj = Gtk.Adjustment(value=0, lower=0, upper=9000, step_increment=1)
        self._gp_mtu_row = Adw.SpinRow(
            title="MTU (0 = default)",
            adjustment=self._gp_mtu_adj,
            climb_rate=1,
            digits=0,
        )
        self._gp_group.add(self._gp_mtu_row)

        self._gp_no_dtls_switch = Adw.SwitchRow(
            title="Disabilita DTLS",
            subtitle="Forza TCP su HTTPS (più stabile, meno veloce)",
        )
        self._gp_group.add(self._gp_no_dtls_switch)

        self._gp_fix_openssl_switch = Adw.SwitchRow(
            title="Fix OpenSSL legacy",
            subtitle="Usa --fix-openssl per server con SSL datato",
        )
        self._gp_group.add(self._gp_fix_openssl_switch)

        gp_dns_info = Adw.ActionRow(
            subtitle="I domini DNS extra vengono forzati sull'interfaccia VPN "
                     "tramite systemd-resolved. Un watchdog li mantiene attivi."
        )
        gp_dns_info.add_css_class("property")
        self._gp_group.add(gp_dns_info)

        main_box.append(self._gp_group)

        # --- Advanced group ---
        advanced_group = Adw.PreferencesGroup(title="Avanzate")

        self._extra_args_row = Adw.EntryRow(title="Argomenti extra")
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

        # VPN type
        vpn_idx = 1 if p.vpn_type == "globalprotect" else 0
        self._vpn_type_row.set_selected(vpn_idx)

        # GlobalProtect fields
        self._gp_gateway_row.set_text(p.gp_gateway)
        self._gp_extra_dns_row.set_text(p.gp_extra_dns)
        self._gp_vpn_dns_row.set_text(p.gp_vpn_dns)
        self._gp_hip_switch.set_active(p.gp_hip)
        self._gp_mtu_adj.set_value(p.gp_mtu)
        self._gp_no_dtls_switch.set_active(p.gp_no_dtls)
        self._gp_fix_openssl_switch.set_active(p.gp_fix_openssl)

        # VPN password (from encrypted field in profile)
        from . import crypto
        vpn_pwd = crypto.decrypt(p.encrypted_password)
        if vpn_pwd:
            self._vpn_password_row.set_text(vpn_pwd)

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
        self._on_vpn_type_changed(None, None)

    def _on_vpn_type_changed(self, row, pspec):
        is_gp = self._vpn_type_row.get_selected() == 1
        is_password = self._auth_pass_check.get_active()
        # Fortinet-only sections
        self._port_row.set_visible(not is_gp)
        self._security_group.set_visible(not is_gp)
        self._network_group.set_visible(not is_gp)
        self._realm_row.set_visible(not is_gp)
        # SSO auto-fill only for Fortinet (GP uses system browser)
        self._sso_group.set_visible(not is_gp and not is_password)
        # VPN password visible for password auth
        self._vpn_password_row.set_visible(is_password)
        self._vpn_pwd_info.set_visible(is_password)
        # GlobalProtect-only section
        self._gp_group.set_visible(is_gp)
        # Username is always visible for GP
        if is_gp:
            self._username_row.set_sensitive(True)

    def _on_auth_method_changed(self, widget):
        is_password = self._auth_pass_check.get_active()
        is_gp = self._vpn_type_row.get_selected() == 1
        self._username_row.set_sensitive(is_password or is_gp)
        # VPN password field visible only for password auth
        self._vpn_password_row.set_visible(is_password)
        self._vpn_pwd_info.set_visible(is_password)
        # SSO auto-fill only for Fortinet SAML
        self._sso_group.set_visible(not is_password and not is_gp)

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

        # VPN type
        p.vpn_type = "globalprotect" if self._vpn_type_row.get_selected() == 1 else "fortinet"

        # GlobalProtect fields
        p.gp_gateway = self._gp_gateway_row.get_text().strip()
        p.gp_extra_dns = self._gp_extra_dns_row.get_text().strip()
        p.gp_vpn_dns = self._gp_vpn_dns_row.get_text().strip()
        p.gp_hip = self._gp_hip_switch.get_active()
        p.gp_mtu = int(self._gp_mtu_adj.get_value())
        p.gp_no_dtls = self._gp_no_dtls_switch.get_active()
        p.gp_fix_openssl = self._gp_fix_openssl_switch.get_active()

        # Save VPN password encrypted in profile
        from . import crypto
        vpn_pwd = self._vpn_password_row.get_text()
        p.encrypted_password = crypto.encrypt(vpn_pwd) if vpn_pwd else ""

        # Save SSO password in keyring (only for Fortinet SAML)
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

        # --- Notifications group ---
        notif_group = Adw.PreferencesGroup(
            title="Notifiche",
            description="Notifiche desktop per eventi di connessione VPN",
        )

        self._notif_switch = Adw.SwitchRow(
            title="Notifiche desktop",
            subtitle="Mostra notifiche per connessione, disconnessione ed errori",
        )
        self._notif_switch.set_active(settings.get("notifications"))
        self._notif_switch.connect("notify::active", self._on_notif_changed)
        notif_group.add(self._notif_switch)

        page.add(notif_group)
        self.add(page)

    def _on_theme_changed(self, row, pspec):
        idx = row.get_selected()
        theme_key = {0: "system", 1: "light", 2: "dark"}.get(idx, "system")
        settings.set("theme", theme_key)
        settings.apply_theme()

    def _on_notif_changed(self, row, pspec):
        settings.set("notifications", row.get_active())


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
