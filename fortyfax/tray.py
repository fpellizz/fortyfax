"""System tray icon — launches a GTK3 subprocess to avoid GTK3/GTK4 conflict.

The actual tray is rendered by tray_subprocess.py using AppIndicator3 (GTK3).
Communication is via stdin/stdout JSON lines.
"""

import json
import logging
import os
import subprocess
import sys
import threading

from gi.repository import GLib

from .connection import ConnectionState
from .profile import ProfileManager, VPNProfile

log = logging.getLogger(__name__)

_SUBPROCESS_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tray_subprocess.py"
)


class TrayIcon:
    """Tray icon proxy — communicates with a GTK3 subprocess."""

    def __init__(self, app):
        self._app = app
        self._process = None
        self._profile_mgr = ProfileManager()
        self._selected_profile_uid: str | None = None

        try:
            self._process = subprocess.Popen(
                [sys.executable, _SUBPROCESS_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            log.warning("Could not start tray subprocess: %s", e)
            return

        # Read actions from subprocess in a thread
        self._reader = threading.Thread(
            target=self._read_actions, daemon=True, name="tray-reader",
        )
        self._reader.start()

        # Send initial profile list
        self._send_profiles()

        log.info("Tray subprocess started (PID %d)", self._process.pid)

    def _send(self, msg: dict):
        if self._process is None or self._process.stdin is None:
            return
        try:
            self._process.stdin.write(json.dumps(msg) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            log.warning("Tray subprocess pipe broken")
            self._process = None

    def _send_profiles(self):
        profiles = self._profile_mgr.load_all()
        if not self._selected_profile_uid and profiles:
            self._selected_profile_uid = profiles[0].uid
        self._send({
            "cmd": "set_profiles",
            "profiles": [
                {"name": p.name, "uid": p.uid} for p in profiles
            ],
            "selected_uid": self._selected_profile_uid,
        })

    def _read_actions(self):
        """Read action messages from the subprocess."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                action = msg.get("action")
                if action == "toggle_window":
                    GLib.idle_add(self._on_toggle_window)
                elif action == "connect":
                    GLib.idle_add(self._on_connect)
                elif action == "disconnect":
                    GLib.idle_add(self._on_disconnect)
                elif action == "select_profile":
                    uid = msg.get("uid", "")
                    GLib.idle_add(self._on_select_profile, uid)
                elif action == "quit":
                    GLib.idle_add(self._app.quit)
                    return
        except Exception:
            pass

    # --- Public API ---

    def update_state(self, state: ConnectionState, message: str = ""):
        self._send({
            "cmd": "update_state",
            "state": state.name,
            "message": message,
        })

    def sync_selected_profile(self, profile: VPNProfile | None):
        self._selected_profile_uid = profile.uid if profile else None
        self._send_profiles()

    def shutdown(self):
        self._send({"cmd": "quit"})
        if self._process:
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()

    # --- Actions from tray ---

    def _on_toggle_window(self):
        window = self._app.get_active_window()
        if window is None:
            self._app.activate()
        elif window.get_visible():
            window.set_visible(False)
        else:
            window.present()

    def _on_select_profile(self, uid: str):
        self._selected_profile_uid = uid
        window = self._app.get_active_window()
        if window and hasattr(window, "select_profile_by_uid"):
            window.select_profile_by_uid(uid)

    def _on_connect(self):
        window = self._app.get_active_window()
        if window is None:
            self._app.activate()
            window = self._app.get_active_window()
        if window is None:
            return
        if self._selected_profile_uid and hasattr(window, "select_profile_by_uid"):
            window.select_profile_by_uid(self._selected_profile_uid)
        if hasattr(window, "_on_connect_clicked"):
            window._on_connect_clicked(None)

    def _on_disconnect(self):
        window = self._app.get_active_window()
        if window and hasattr(window, "_on_disconnect_clicked"):
            window._on_disconnect_clicked(None)
