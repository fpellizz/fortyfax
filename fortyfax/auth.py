"""SAML/SSO authentication via WebKitGTK webview."""

import logging
import os
from urllib.parse import urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, GLib, Gtk, WebKit

log = logging.getLogger(__name__)

# Persistent WebKit session directories
_DATA_DIR = os.path.join(GLib.get_user_data_dir(), "fortyfax", "webdata")
_CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "fortyfax", "webcache")

# Shared network session (singleton, persists cookies across auth windows)
_network_session: WebKit.NetworkSession | None = None


def _get_network_session() -> WebKit.NetworkSession:
    """Get or create a persistent WebKit network session."""
    global _network_session
    if _network_session is None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        os.makedirs(_CACHE_DIR, exist_ok=True)
        _network_session = WebKit.NetworkSession.new(_DATA_DIR, _CACHE_DIR)
        log.info("Persistent WebKit session: data=%s cache=%s", _DATA_DIR, _CACHE_DIR)
    return _network_session


_AUTOFILL_JS = """
(function() {
    // Common selectors for email/username fields
    var emailSelectors = [
        'input[type="email"]',
        'input[name="loginfmt"]',         // Microsoft
        'input[name="login"]',
        'input[name="username"]',
        'input[name="identifier"]',       // Google
        'input[name="userName"]',         // Okta
        'input[name="email"]',
        'input[id="i0116"]',             // Microsoft
        'input[id="username"]',
        'input[id="email"]',
        'input[id="login"]',
    ];
    // Common selectors for password fields
    var pwdSelectors = [
        'input[type="password"]',
        'input[name="passwd"]',           // Microsoft
        'input[name="password"]',
        'input[name="credentials.passcode"]', // Okta
        'input[id="i0118"]',             // Microsoft
        'input[id="passwordInput"]',
    ];

    var username = __AUTOFILL_USERNAME__;
    var password = __AUTOFILL_PASSWORD__;
    var filled = false;

    function setValue(el, val) {
        if (!el || !val) return false;
        // Use native setter to trigger React/Angular change detection
        var nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(el, val);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        return true;
    }

    function tryFill() {
        // Try email/username
        if (username) {
            for (var i = 0; i < emailSelectors.length; i++) {
                var el = document.querySelector(emailSelectors[i]);
                if (el && el.offsetParent !== null && !el.value) {
                    if (setValue(el, username)) { filled = true; break; }
                }
            }
        }
        // Try password
        if (password) {
            for (var i = 0; i < pwdSelectors.length; i++) {
                var el = document.querySelector(pwdSelectors[i]);
                if (el && el.offsetParent !== null && !el.value) {
                    if (setValue(el, password)) { filled = true; break; }
                }
            }
        }
    }

    // Try immediately and also after short delays (for dynamic pages)
    tryFill();
    if (!filled) {
        setTimeout(tryFill, 500);
        setTimeout(tryFill, 1500);
    }
})();
"""


class SAMLAuthWindow(Adw.Window):
    """Window that handles SAML/SSO login via embedded WebKitGTK webview.

    Flow:
    1. Navigate to https://<host>:<port>/remote/saml/start?realm=<realm>
    2. User authenticates via IdP in the webview
    3. FortiGate sets SVPNCOOKIE after successful auth
    4. We detect the cookie and close the window
    """

    def __init__(self, host: str, port: int = 443, realm: str = "",
                 sso_username: str = "", sso_password: str = "", **kwargs):
        super().__init__(
            title="Fortyfax - Autenticazione SSO",
            default_width=900,
            default_height=700,
            modal=True,
            **kwargs,
        )

        self._host = host
        self._port = port
        self._realm = realm
        self._sso_username = sso_username
        self._sso_password = sso_password
        self._cookie: str | None = None
        self._on_auth_complete = None
        self._cookie_check_id = None

        self._build_ui()

    def _build_ui(self):
        # Header bar
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Annulla")
        cancel_btn.connect("clicked", self._on_cancel)
        cancel_btn.add_css_class("destructive-action")
        header.pack_start(cancel_btn)

        self._spinner = Gtk.Spinner()
        header.pack_end(self._spinner)

        # Status label in header
        self._status_label = Gtk.Label(label="Caricamento pagina di login...")
        self._status_label.add_css_class("dim-label")
        header.set_title_widget(self._status_label)

        # WebView with persistent session (remembers SSO login cookies)
        self._webview = WebKit.WebView(network_session=_get_network_session())

        # Configure webview settings
        settings = self._webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(False)
        # Mimic FortiClient User-Agent to bypass host-check requirements
        settings.set_property(
            "user-agent",
            "Mozilla/5.0 (Linux) AppleWebKit/537.36 (KHTML, like Gecko) "
            "FortiClient/7.0 Chrome/120.0.0.0 Safari/537.36",
        )

        # Connect signals
        self._webview.connect("load-changed", self._on_load_changed)
        self._webview.connect("load-failed", self._on_load_failed)

        # Layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)
        box.append(self._webview)
        self._webview.set_vexpand(True)
        self._webview.set_hexpand(True)

        self.set_content(box)

        # Handle window close
        self.connect("close-request", self._on_close_request)

    def set_on_auth_complete(self, callback):
        """Set callback: callback(cookie: str | None)"""
        self._on_auth_complete = callback

    def start_auth(self):
        """Begin the SAML authentication flow."""
        scheme = "https"
        url = f"{scheme}://{self._host}:{self._port}/remote/saml/start"
        if self._realm:
            url += f"?realm={self._realm}"

        log.info("Starting SAML auth: %s", url)
        self._spinner.start()
        self._webview.load_uri(url)
        self.present()

    def _on_load_changed(self, webview, load_event):
        if load_event == WebKit.LoadEvent.STARTED:
            self._spinner.start()
            self._status_label.set_label("Caricamento...")
        elif load_event == WebKit.LoadEvent.COMMITTED:
            uri = webview.get_uri() or ""
            domain = urlparse(uri).hostname or uri
            self._status_label.set_label(f"Connesso a {domain}")
        elif load_event == WebKit.LoadEvent.FINISHED:
            self._spinner.stop()
            uri = webview.get_uri() or ""

            # Check if we landed back on the FortiGate (auth complete)
            parsed = urlparse(uri)
            target_host = self._host.lower()
            current_host = (parsed.hostname or "").lower()

            self._status_label.set_label(f"Pagina caricata: {current_host}")

            # Auto-fill SSO credentials on IdP login pages
            if self._sso_username or self._sso_password:
                if current_host != target_host:
                    self._inject_autofill()

            # Always check for the SVPNCOOKIE after page load
            self._check_cookies()

    def _on_load_failed(self, webview, load_event, failing_uri, error):
        self._spinner.stop()
        self._status_label.set_label(f"Errore di caricamento")
        log.error("Load failed for %s: %s", failing_uri, error.message if error else "unknown")

        # Show error in a toast or dialog
        dialog = Adw.AlertDialog(
            heading="Errore di connessione",
            body=f"Impossibile raggiungere il server VPN.\n\n{failing_uri}\n\n{error.message if error else 'Errore sconosciuto'}",
        )
        dialog.add_response("retry", "Riprova")
        dialog.add_response("close", "Chiudi")
        dialog.set_response_appearance("retry", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("retry")
        dialog.connect("response", self._on_error_response, failing_uri)
        dialog.present(self)
        return True  # handled

    def _on_error_response(self, dialog, response, uri):
        if response == "retry":
            self._webview.load_uri(uri)
        else:
            self._finish(None)

    def _inject_autofill(self):
        """Inject JavaScript to auto-fill login form fields."""
        import json

        js = _AUTOFILL_JS.replace(
            "__AUTOFILL_USERNAME__", json.dumps(self._sso_username)
        ).replace(
            "__AUTOFILL_PASSWORD__", json.dumps(self._sso_password)
        )
        self._webview.evaluate_javascript(js, -1, None, None, None, None, None)
        log.debug("Auto-fill JS injected for %s", self._webview.get_uri())

    def _check_cookies(self):
        """Check if SVPNCOOKIE has been set."""
        uri = self._webview.get_uri()
        if not uri:
            return

        network_session = self._webview.get_network_session()
        cookie_manager = network_session.get_cookie_manager()

        cookie_manager.get_cookies(uri, None, self._on_cookies_ready, None)

    def _on_cookies_ready(self, cookie_manager, result, user_data):
        try:
            cookies = cookie_manager.get_cookies_finish(result)
        except Exception as e:
            log.warning("Failed to get cookies: %s", e)
            return

        for cookie in cookies:
            name = cookie.get_name()
            if name == "SVPNCOOKIE":
                value = cookie.get_value()
                if value:
                    log.info("SVPNCOOKIE captured! (length=%d)", len(value))
                    self._cookie = f"SVPNCOOKIE={value}"
                    self._finish(self._cookie)
                    return

        # If not found and we're on the FortiGate, schedule another check
        uri = self._webview.get_uri() or ""
        parsed = urlparse(uri)
        current_host = (parsed.hostname or "").lower()
        if current_host == self._host.lower():
            # Retry after a short delay
            if self._cookie_check_id is None:
                self._cookie_check_id = GLib.timeout_add(500, self._retry_cookie_check)

    def _retry_cookie_check(self):
        self._cookie_check_id = None
        if self._cookie is None:
            self._check_cookies()
        return GLib.SOURCE_REMOVE

    def _finish(self, cookie: str | None):
        """Complete auth flow."""
        # Clear webview data for security
        if cookie is None:
            log.info("Auth cancelled or failed")
        else:
            log.info("Auth successful")

        if self._on_auth_complete:
            self._on_auth_complete(cookie)

        self.close()

    def _on_cancel(self, button):
        self._finish(None)

    def _on_close_request(self, window):
        if self._cookie is None:
            self._finish(None)
        return False  # allow close


def authenticate_saml(
    parent: Gtk.Window,
    host: str,
    port: int = 443,
    realm: str = "",
    sso_username: str = "",
    sso_password: str = "",
    callback=None,
):
    """Convenience function to start SAML auth.

    Args:
        parent: Parent window
        host: FortiGate hostname
        port: FortiGate port
        realm: SAML realm (optional)
        sso_username: SSO email/username for auto-fill
        sso_password: SSO password for auto-fill
        callback: Called with cookie string or None
    """
    win = SAMLAuthWindow(
        host=host, port=port, realm=realm,
        sso_username=sso_username, sso_password=sso_password,
        transient_for=parent,
    )
    win.set_on_auth_complete(callback)
    win.start_auth()
    return win
