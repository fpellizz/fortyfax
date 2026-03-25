"""openfortivpn process management."""

import logging
import os
import signal
import subprocess
import threading
from enum import Enum, auto
from typing import Callable

from .profile import VPNProfile

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTING = auto()
    ERROR = auto()


class VPNConnection:
    """Manages a single openfortivpn connection."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._state = ConnectionState.DISCONNECTED
        self._monitor_thread: threading.Thread | None = None
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

    def connect(self, profile: VPNProfile, cookie: str = "", password: str = "") -> bool:
        """Start openfortivpn connection. Returns False if already connected."""
        with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                return False

            self._log_lines.clear()
            self._set_state(ConnectionState.CONNECTING, f"Connessione a {profile.display_host}...")

            args = ["pkexec", "openfortivpn"] + profile.to_openfortivpn_args(cookie=cookie)
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

                # Send cookie or password on stdin if needed
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
                target=self._monitor_process, daemon=True, name="vpn-monitor"
            )
            self._monitor_thread.start()
            return True

    def _monitor_process(self):
        """Monitor openfortivpn output in background thread."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return

        connected = False
        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                self._append_log(line)

                # Detect connection success
                if "Tunnel is up and running" in line or "Connected" in line:
                    connected = True
                    self._set_state(ConnectionState.CONNECTED, "Tunnel attivo")

                # Detect certificate hash for trusted-cert
                if "Gateway certificate:" in line or "server certificate" in line.lower():
                    self._append_log("[INFO] Certificato del server rilevato nel log")

                # Detect common errors
                if "ERROR" in line:
                    if self._state == ConnectionState.CONNECTING:
                        self._set_state(ConnectionState.ERROR, line)

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
                    f"Connessione fallita (codice {retcode})",
                )
            self._process = None

    def disconnect(self):
        """Terminate the VPN connection."""
        with self._lock:
            if self._process is None:
                self._set_state(ConnectionState.DISCONNECTED)
                return

            self._set_state(ConnectionState.DISCONNECTING, "Disconnessione in corso...")
            try:
                # Send SIGTERM to pkexec which forwards to openfortivpn
                self._process.terminate()
                # Also try to kill the openfortivpn child process
                try:
                    subprocess.run(
                        ["pkexec", "kill", "-SIGTERM", str(self._process.pid)],
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
            try:
                self._process.kill()
            except ProcessLookupError:
                pass
            self._set_state(ConnectionState.DISCONNECTED, "Connessione terminata forzatamente")
            self._process = None
