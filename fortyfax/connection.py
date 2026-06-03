"""VPN connection management with pluggable backends."""

import logging
import os
import re
import shutil
import subprocess
import threading
from enum import Enum, auto
from typing import Callable

from .profile import VPNProfile

log = logging.getLogger(__name__)

# --- Interpretazione errori --------------------------------------------------
# Regole (regex → messaggio parlante) per tradurre le righe di log di
# openfortivpn/gpclient/openconnect in messaggi comprensibili. Per ogni riga
# vince la prima regola che matcha; a fine processo le righe vengono esaminate
# dalla più recente alla più vecchia.
_ERROR_RULES: list[tuple[re.Pattern, str]] = [
    # SSO/SAML prima della regola credenziali: "SAML authentication failed"
    # matcherebbe anche quella, ma "credenziali errate" sarebbe fuorviante.
    (re.compile(r"saml.*(fail|error|denied|cancel)|sso.*(fail|error|cancel)", re.I),
     "Autenticazione SSO non riuscita o annullata"),
    # Credenziali / autenticazione
    (re.compile(
        r"could not authenticate|authentication fail|login fail"
        r"|invalid (username|password|credential)|incorrect password"
        r"|failed to obtain webvpn cookie",
        re.I),
     "Credenziali errate: nome utente o password non validi"),
    (re.compile(r"two.?factor|second factor|otp token", re.I),
     "Il server richiede un secondo fattore di autenticazione (2FA)"),
    # Risoluzione nome / DNS
    (re.compile(
        r"name or service not known|could not resolve|failed to lookup"
        r"|temporary failure in name resolution|dns error|getaddrinfo|gethostbyname",
        re.I),
     "Indirizzo del server non risolvibile: controlla l'host nel profilo "
     "e la connessione a Internet"),
    # Rete
    (re.compile(r"connection refused", re.I),
     "Connessione rifiutata dal server: controlla indirizzo e porta"),
    (re.compile(r"network is unreachable|no route to host", re.I),
     "Rete non raggiungibile: controlla la connessione a Internet"),
    (re.compile(r"connection reset by peer", re.I),
     "Connessione interrotta dal server"),
    (re.compile(r"timed? out", re.I),
     "Timeout: il server VPN non risponde"),
    # Certificati / TLS
    (re.compile(
        r"certificate.*(fail|invalid|expired|unknown|not trusted)"
        r"|invalid peer certificate|self.signed|unable to get local issuer"
        r"|handshake fail",
        re.I),
     "Certificato del server non attendibile: verifica il certificato "
     "del gateway (o aggiungilo ai certificati fidati del profilo)"),
    # Sistema
    (re.compile(r"kernel does not support ppp", re.I),
     "Supporto PPP mancante nel sistema: verifica che pppd sia installato"),
    (re.compile(r"failed to (open|launch|spawn).*browser|browser.*not found", re.I),
     "Impossibile aprire il browser per il login SSO"),
]

# Codici di uscita noti (pkexec / segnali)
_EXIT_CODE_MESSAGES = {
    126: "Autenticazione amministratore annullata",
    127: "Autorizzazione amministratore negata (pkexec)",
    -15: "Processo VPN terminato esternamente (SIGTERM)",
    -9: "Processo VPN terminato forzatamente (SIGKILL)",
}


def _interpret_error_line(line: str) -> str | None:
    """Traduce una riga di log in un messaggio parlante, se riconosciuta."""
    for rx, msg in _ERROR_RULES:
        if rx.search(line):
            return msg
    return None

def _resolve_helper() -> str:
    """Resolve the helper script path.

    Prefer the system-installed helper because the PolicyKit policy is
    registered for those paths — using them avoids password prompts for
    the active user. Fall back to the dev copy (pwd prompt every time).
    """
    for path in ("/usr/bin/fortyfax-vpn-helper", "/usr/local/bin/fortyfax-vpn-helper"):
        if os.path.isfile(path):
            return path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fortyfax-vpn-helper")


_HELPER = _resolve_helper()


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTING = auto()
    ERROR = auto()


class VPNConnection:
    """Manages a single VPN connection (Fortinet or GlobalProtect)."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._state = ConnectionState.DISCONNECTED
        self._vpn_type: str = "fortinet"  # track active connection type
        self._monitor_thread: threading.Thread | None = None
        self._dns_watchdog_thread: threading.Thread | None = None
        self._dns_watchdog_stop = threading.Event()
        self._log_lines: list[str] = []
        self._on_state_changed: Callable[[ConnectionState, str], None] | None = None
        self._on_log_line: Callable[[str], None] | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def log_text(self) -> str:
        return "\n".join(self._log_lines)

    def set_callbacks(
        self,
        on_state_changed: Callable[[ConnectionState, str], None] | None = None,
        on_log_line: Callable[[str], None] | None = None,
    ):
        self._on_state_changed = on_state_changed
        self._on_log_line = on_log_line

    def _set_state(self, state: ConnectionState, message: str = ""):
        self._state = state
        log.info("State -> %s: %s", state.name, message)
        if self._on_state_changed:
            self._on_state_changed(state, message)

    def _append_log(self, line: str):
        self._log_lines.append(line)
        # Keep last 2000 lines
        if len(self._log_lines) > 2000:
            self._log_lines = self._log_lines[-1500:]
        if self._on_log_line:
            self._on_log_line(line)

    def _friendly_failure_message(self, retcode: int) -> str:
        """Messaggio parlante per una connessione fallita.

        Esamina le righe di log recenti (dalla più nuova) cercando una causa
        riconoscibile; in mancanza, traduce i codici di uscita noti.
        """
        for line in reversed(self._log_lines[-150:]):
            msg = _interpret_error_line(line)
            if msg:
                return msg
        if retcode in _EXIT_CODE_MESSAGES:
            return _EXIT_CODE_MESSAGES[retcode]
        return f"Connessione fallita (codice {retcode})"

    def connect(self, profile: VPNProfile, cookie: str = "", password: str = "") -> bool:
        """Start VPN connection based on profile type."""
        if profile.vpn_type == "globalprotect":
            return self._connect_globalprotect(profile, password=password)
        return self._connect_fortinet(profile, cookie=cookie, password=password)

    # --- Fortinet (openfortivpn) ---

    def _connect_fortinet(self, profile: VPNProfile, cookie: str = "", password: str = "") -> bool:
        """Start openfortivpn connection."""
        with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                return False

            self._log_lines.clear()
            self._set_state(ConnectionState.CONNECTING, f"Connessione a {profile.display_host}...")

            args = ["pkexec", _HELPER, "start", "openfortivpn"] + profile.to_openfortivpn_args(cookie=cookie)
            self._append_log(f"$ {' '.join(args)}")

            try:
                stdin_pipe = subprocess.PIPE if (cookie or password) else subprocess.DEVNULL
                self._process = subprocess.Popen(
                    args,
                    stdin=stdin_pipe,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env={**os.environ, "LANG": "C"},
                )

                if cookie:
                    self._process.stdin.write(cookie + "\n")
                    self._process.stdin.flush()
                    self._process.stdin.close()
                elif password:
                    self._process.stdin.write(password + "\n")
                    self._process.stdin.flush()
                    self._process.stdin.close()

            except FileNotFoundError as e:
                self._set_state(ConnectionState.ERROR, f"Comando non trovato: {e}")
                return False
            except PermissionError:
                self._set_state(ConnectionState.ERROR, "Permessi insufficienti")
                return False

            self._monitor_thread = threading.Thread(
                target=self._monitor_fortinet, daemon=True, name="vpn-monitor"
            )
            self._monitor_thread.start()
            return True

    def _monitor_fortinet(self):
        """Monitor openfortivpn output in background thread."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return

        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                self._append_log(line)

                if "Tunnel is up and running" in line or "Connected" in line:
                    self._set_state(ConnectionState.CONNECTED, "Tunnel attivo")

                if "Gateway certificate:" in line or "server certificate" in line.lower():
                    self._append_log("[INFO] Certificato del server rilevato nel log")

                if "ERROR" in line:
                    if self._state == ConnectionState.CONNECTING:
                        self._set_state(
                            ConnectionState.ERROR,
                            _interpret_error_line(line) or line,
                        )

        except Exception as e:
            self._append_log(f"[ERRORE monitor] {e}")
        finally:
            retcode = proc.wait()
            self._append_log(f"[openfortivpn terminato con codice {retcode}]")

            if self._state == ConnectionState.DISCONNECTING:
                self._set_state(ConnectionState.DISCONNECTED, "Disconnesso")
            elif self._state == ConnectionState.CONNECTED:
                self._set_state(ConnectionState.DISCONNECTED, "Connessione terminata")
            elif self._state == ConnectionState.CONNECTING:
                self._set_state(
                    ConnectionState.ERROR,
                    self._friendly_failure_message(retcode),
                )
            self._process = None

    # --- GlobalProtect (gpclient) ---

    @staticmethod
    def _kill_stale_gpclient():
        """Kill any leftover gpclient/openconnect processes from previous runs.

        Delegates to the helper script's 'cleanup-gp' action which does
        disconnect + pkill gpclient + pkill openconnect in a single
        privileged call — one pkexec invocation, one password prompt
        (or none at all if the PolicyKit policy allows the active user).
        """
        try:
            subprocess.run(
                ["pkexec", _HELPER, "cleanup-gp"],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

    def _connect_globalprotect(self, profile: VPNProfile, password: str = "") -> bool:
        """Start GlobalProtect (gpclient) connection."""
        with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                return False

            self._log_lines.clear()

            # Note: the helper 'start gpclient' action cleans up stale
            # processes inline before exec-ing gpclient, so we don't need
            # a separate pkexec call here.

            self._vpn_type = "globalprotect"
            self._set_state(ConnectionState.CONNECTING, f"Connessione a {profile.display_host}...")

            # Build gpclient command
            gp_args = profile.to_gpclient_args()

            if profile.auth_method == "saml":
                # SSO: use system browser via wrapper
                browser_wrapper = self._create_browser_wrapper()
                gp_args += ["--browser", browser_wrapper]
            elif profile.auth_method == "password" and password:
                gp_args.append("--passwd-on-stdin")

            # Find vpnc-script for network setup
            vpnc_script = self._find_vpnc_script()
            if vpnc_script:
                vpnc_wrapper = self._create_vpnc_wrapper(vpnc_script)
                gp_args += ["--script", vpnc_wrapper]

            gp_args.append("--verbose")

            args = ["pkexec", _HELPER, "start", "gpclient"] + gp_args
            self._append_log(f"$ {' '.join(args)}")

            try:
                stdin_pipe = subprocess.PIPE if (password and profile.auth_method == "password") else subprocess.DEVNULL
                self._process = subprocess.Popen(
                    args,
                    stdin=stdin_pipe,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env={**os.environ, "LANG": "C"},
                )

                if password and profile.auth_method == "password":
                    self._process.stdin.write(password + "\n")
                    self._process.stdin.flush()
                    self._process.stdin.close()

            except FileNotFoundError as e:
                self._set_state(ConnectionState.ERROR, f"Comando non trovato: {e}")
                return False
            except PermissionError:
                self._set_state(ConnectionState.ERROR, "Permessi insufficienti")
                return False

            self._monitor_thread = threading.Thread(
                target=self._monitor_globalprotect,
                args=(profile,),
                daemon=True,
                name="gp-monitor",
            )
            self._monitor_thread.start()
            return True

    def _monitor_globalprotect(self, profile: VPNProfile):
        """Monitor gpclient output in background thread."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return

        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                self._append_log(line)

                # Detect connection success (gpclient specific messages)
                if "Connected to VPN" in line or "ESP tunnel connected" in line or "Tunnel is up" in line:
                    self._set_state(ConnectionState.CONNECTED, "Tunnel GlobalProtect attivo")
                    # Start DNS watchdog if needed
                    if profile.gp_extra_dns or profile.gp_vpn_dns:
                        self._start_dns_watchdog(profile)

                # Detect errors (but ignore low-level connection log lines)
                if "ERROR" in line and self._state == ConnectionState.CONNECTING:
                    # Skip false positives from debug connection logs
                    if "connect" not in line.lower() or "failed" in line.lower():
                        self._set_state(
                            ConnectionState.ERROR,
                            _interpret_error_line(line) or line,
                        )

        except Exception as e:
            self._append_log(f"[ERRORE monitor GP] {e}")
        finally:
            retcode = proc.wait()
            self._append_log(f"[gpclient terminato con codice {retcode}]")
            self._stop_dns_watchdog()

            if self._state == ConnectionState.DISCONNECTING:
                self._set_state(ConnectionState.DISCONNECTED, "Disconnesso")
            elif self._state == ConnectionState.CONNECTED:
                self._set_state(ConnectionState.DISCONNECTED, "Connessione terminata")
            elif self._state == ConnectionState.CONNECTING:
                self._set_state(
                    ConnectionState.ERROR,
                    self._friendly_failure_message(retcode),
                )
            self._process = None
            # Cleanup temp files
            for f in ["/tmp/fortyfax_browser_wrapper.sh", "/tmp/fortyfax_vpnc_wrapper.sh"]:
                try:
                    os.unlink(f)
                except OSError:
                    pass

    # --- GlobalProtect helpers ---

    @staticmethod
    def _find_vpnc_script() -> str | None:
        """Find vpnc-script on the system."""
        for path in [
            "/usr/share/vpnc-scripts/vpnc-script",
            "/etc/vpnc/vpnc-script",
            "/usr/sbin/vpnc-script",
        ]:
            if os.path.isfile(path):
                return path
        return None

    @staticmethod
    def _find_sso_browser() -> str:
        """Find the best browser for SSO login.

        Priority: user preference > Chrome/Chromium > Edge > xdg-open fallback.
        Chrome and Edge have built-in password managers that remember SSO
        credentials, making repeated logins much smoother.
        """
        from . import settings

        pref = settings.get("sso_browser")

        # Explicit user preference
        browser_map = {
            "chrome": ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"],
            "edge": ["microsoft-edge-stable", "microsoft-edge"],
        }

        if pref in browser_map:
            for cmd in browser_map[pref]:
                found = shutil.which(cmd)
                if found:
                    return found

        # Auto-detect: try Chrome/Chromium first, then Edge
        if pref == "auto":
            for cmd in ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser",
                        "microsoft-edge-stable", "microsoft-edge"]:
                found = shutil.which(cmd)
                if found:
                    log.info("SSO browser auto-detected: %s", found)
                    return found

        # Fallback
        return shutil.which("xdg-open") or "/usr/bin/xdg-open"

    def _create_browser_wrapper(self) -> str:
        """Create a wrapper script that opens the SSO browser as the real user.

        gpclient runs as root via pkexec, so the wrapper uses sudo -u to launch
        the browser as the original user (for access to the user's profile/cookies).
        """
        import pwd
        real_user = pwd.getpwuid(os.getuid()).pw_name
        browser = self._find_sso_browser()
        self._append_log(f"[SSO] Browser: {browser}")
        path = "/tmp/fortyfax_browser_wrapper.sh"
        with open(path, "w") as f:
            f.write(f'#!/bin/bash\nsudo -u {real_user} {browser} "$@"\n')
        os.chmod(path, 0o755)
        return path

    @staticmethod
    def _create_vpnc_wrapper(real_script: str) -> str:
        """Create vpnc-script wrapper that suppresses non-fatal route errors."""
        path = "/tmp/fortyfax_vpnc_wrapper.sh"
        with open(path, "w") as f:
            f.write(
                f"#!/bin/bash\n"
                f"export IPROUTE_METRICS=0\n"
                f"{real_script} \"$@\"\n"
                f"exit 0\n"
            )
        os.chmod(path, 0o755)
        return path

    # --- DNS Watchdog ---

    def _start_dns_watchdog(self, profile: VPNProfile):
        """Start background DNS watchdog for GlobalProtect."""
        self._dns_watchdog_stop.clear()
        self._dns_watchdog_thread = threading.Thread(
            target=self._dns_watchdog_loop,
            args=(profile.gp_extra_dns, profile.gp_vpn_dns),
            daemon=True,
            name="dns-watchdog",
        )
        self._dns_watchdog_thread.start()

    def _stop_dns_watchdog(self):
        """Stop the DNS watchdog."""
        self._dns_watchdog_stop.set()

    def _dns_watchdog_loop(self, extra_dns: str, forced_dns: str):
        """Periodically check and fix DNS configuration for the VPN interface."""
        import time

        self._append_log("[DNS Watchdog] Avviato")

        # Wait for tun interface to appear
        tun_if = None
        for _ in range(30):
            if self._dns_watchdog_stop.is_set():
                return
            tun_if = self._find_tun_interface()
            if tun_if:
                break
            time.sleep(1)

        if not tun_if:
            self._append_log("[DNS Watchdog] Timeout: interfaccia tun non trovata")
            return

        self._append_log(f"[DNS Watchdog] Interfaccia rilevata: {tun_if}")

        # Initial DNS fix
        self._apply_dns_fix(tun_if, extra_dns, forced_dns)

        # Periodic check
        for _ in range(120):  # ~10 minutes
            if self._dns_watchdog_stop.wait(timeout=5):
                break
            if not self._interface_exists(tun_if):
                break
            # Check if domains are still correct
            if extra_dns and not self._check_dns_domains(tun_if, extra_dns):
                self._append_log("[DNS Watchdog] Domini mancanti, riapplico configurazione")
                self._apply_dns_fix(tun_if, extra_dns, forced_dns)

        self._append_log("[DNS Watchdog] Terminato")

    def _apply_dns_fix(self, tun_if: str, extra_dns: str, forced_dns: str):
        """Apply DNS configuration fixes on the VPN interface."""
        resolvectl = shutil.which("resolvectl")
        if not resolvectl:
            self._append_log("[DNS Watchdog] resolvectl non trovato, skip fix DNS")
            return

        try:
            if forced_dns:
                # Add route for DNS server through tunnel
                subprocess.run(
                    ["ip", "route", "add", forced_dns, "dev", tun_if],
                    capture_output=True, timeout=5,
                )
                subprocess.run(
                    [resolvectl, "dns", tun_if, forced_dns],
                    capture_output=True, timeout=5,
                )
                self._append_log(f"[DNS Watchdog] DNS forzato: {forced_dns}")

            if extra_dns:
                # Build domain list with ~ prefix
                domains = [f"~{d.strip()}" for d in extra_dns.split() if d.strip()]
                # Get current domains and merge
                current = self._get_current_domains(tun_if)
                for cd in current:
                    clean = cd.lstrip("~")
                    if clean and not any(clean == d.lstrip("~") for d in domains):
                        domains.append(f"~{clean}")

                if domains:
                    subprocess.run(
                        [resolvectl, "domain", tun_if] + domains,
                        capture_output=True, timeout=5,
                    )
                    self._append_log(f"[DNS Watchdog] Domini: {' '.join(domains)}")

            subprocess.run(
                [resolvectl, "default-route", tun_if, "false"],
                capture_output=True, timeout=5,
            )
            subprocess.run(
                [resolvectl, "flush-caches"],
                capture_output=True, timeout=5,
            )
        except Exception as e:
            self._append_log(f"[DNS Watchdog] Errore: {e}")

    @staticmethod
    def _find_tun_interface() -> str | None:
        """Find the tun interface name."""
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "tun" in line and ":" in line:
                    # Format: "N: tunX: <FLAGS> ..."
                    parts = line.split(":")
                    if len(parts) >= 2:
                        name = parts[1].strip().split("@")[0]
                        if name.startswith("tun"):
                            return name
        except Exception:
            pass
        return None

    @staticmethod
    def _interface_exists(name: str) -> bool:
        """Check if a network interface exists."""
        try:
            result = subprocess.run(
                ["ip", "link", "show", name],
                capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _get_current_domains(tun_if: str) -> list[str]:
        """Get current DNS domains for interface."""
        try:
            result = subprocess.run(
                ["resolvectl", "domain", tun_if],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                # Output like "Link 3 (tun0): ~domain1 ~domain2"
                parts = result.stdout.split(":")
                if len(parts) >= 2:
                    return parts[-1].strip().split()
        except Exception:
            pass
        return []

    @staticmethod
    def _check_dns_domains(tun_if: str, extra_dns: str) -> bool:
        """Check if all required domains are configured."""
        try:
            result = subprocess.run(
                ["resolvectl", "domain", tun_if],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout
            for domain in extra_dns.split():
                if domain.strip() and domain.strip() not in output:
                    return False
            return True
        except Exception:
            return False

    # --- Disconnect (shared) ---

    def disconnect(self):
        """Terminate the VPN connection."""
        with self._lock:
            if self._process is None:
                self._set_state(ConnectionState.DISCONNECTED)
                return

            self._set_state(ConnectionState.DISCONNECTING, "Disconnessione in corso...")
            self._stop_dns_watchdog()

            if self._vpn_type == "globalprotect":
                # Single pkexec call: disconnect + pkill gpclient + pkill openconnect
                self._kill_stale_gpclient()
            else:
                # Fortinet: terminate owned process, fallback to helper stop if root-owned
                try:
                    self._process.terminate()
                except PermissionError:
                    try:
                        subprocess.run(
                            ["pkexec", _HELPER, "stop", str(self._process.pid)],
                            timeout=5,
                            capture_output=True,
                        )
                    except Exception:
                        pass
                except ProcessLookupError:
                    pass

    def force_disconnect(self):
        """Force kill the connection."""
        with self._lock:
            if self._process is None:
                self._set_state(ConnectionState.DISCONNECTED)
                return
            self._stop_dns_watchdog()
            try:
                self._process.kill()
            except PermissionError:
                try:
                    subprocess.run(
                        ["pkexec", _HELPER, "kill", str(self._process.pid)],
                        timeout=5,
                        capture_output=True,
                    )
                except Exception:
                    pass
            except ProcessLookupError:
                pass
            self._set_state(ConnectionState.DISCONNECTED, "Connessione terminata forzatamente")
            self._process = None
