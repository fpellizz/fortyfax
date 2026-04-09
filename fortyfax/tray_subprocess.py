#!/usr/bin/env python3
"""Tray icon subprocess using GTK3 + AppIndicator3.

This runs as a separate process to avoid GTK3/GTK4 conflicts.
Communication with the main app is via stdin/stdout JSON messages.

Protocol (one JSON object per line):
  Main -> Tray:  {"cmd": "update_state", "state": "CONNECTED", "message": "..."}
                  {"cmd": "set_profiles", "profiles": [...], "selected_uid": "..."}
                  {"cmd": "quit"}
  Tray -> Main:  {"action": "toggle_window"}
                  {"action": "connect"}
                  {"action": "disconnect"}
                  {"action": "select_profile", "uid": "..."}
                  {"action": "quit"}
"""

import json
import os
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import AppIndicator3, GLib, Gtk

ICONS_DIR = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")
)

# Custom tray icon PNGs (shield in different colors)
_TRAY_ICONS = {
    "CONNECTED": os.path.join(ICONS_DIR, "tray_connected_32.png"),
    "CONNECTING": os.path.join(ICONS_DIR, "tray_idle_32.png"),
    "DISCONNECTING": os.path.join(ICONS_DIR, "tray_disconnected_32.png"),
    "DISCONNECTED": os.path.join(ICONS_DIR, "tray_disconnected_32.png"),
    "ERROR": os.path.join(ICONS_DIR, "tray_error_32.png"),
    "IDLE": os.path.join(ICONS_DIR, "tray_idle_32.png"),
}
_TRAY_ICON_DEFAULT = os.path.join(ICONS_DIR, "tray_idle_32.png")


class TraySubprocess:
    def __init__(self):
        self._state = "DISCONNECTED"
        self._profiles = []
        self._selected_uid = None

        self._indicator = AppIndicator3.Indicator.new(
            "fortyfax-vpn",
            _TRAY_ICON_DEFAULT,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_title("Fortyfax VPN")

        self._build_menu()

        # Read commands from stdin in a thread
        self._reader = threading.Thread(target=self._read_stdin, daemon=True)
        self._reader.start()

    def _build_menu(self):
        menu = Gtk.Menu()

        # Status
        self._status_item = Gtk.MenuItem.new_with_label("Disconnesso")
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)
        menu.append(Gtk.SeparatorMenuItem.new())

        # Profile section
        self._profile_section = Gtk.MenuItem.new_with_label("Profili VPN")
        self._profile_section.set_sensitive(False)
        menu.append(self._profile_section)

        self._profile_items = []
        self._profile_submenu_container = menu  # we'll insert items after header
        self._profile_insert_pos = 3  # after status, separator, header

        self._sep_after_profiles = Gtk.SeparatorMenuItem.new()
        menu.append(self._sep_after_profiles)

        # Connect / Disconnect
        self._connect_item = Gtk.MenuItem.new_with_label("Connetti")
        self._connect_item.connect("activate", lambda _: self._send("connect"))
        menu.append(self._connect_item)

        self._disconnect_item = Gtk.MenuItem.new_with_label("Disconnetti")
        self._disconnect_item.connect("activate", lambda _: self._send("disconnect"))
        menu.append(self._disconnect_item)

        menu.append(Gtk.SeparatorMenuItem.new())

        # Show window
        show_item = Gtk.MenuItem.new_with_label("Mostra/Nascondi finestra")
        show_item.connect("activate", lambda _: self._send("toggle_window"))
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem.new())

        # Quit
        quit_item = Gtk.MenuItem.new_with_label("Esci")
        quit_item.connect("activate", lambda _: self._send("quit"))
        menu.append(quit_item)

        menu.show_all()
        self._disconnect_item.hide()
        self._indicator.set_menu(menu)
        self._menu = menu

    def _rebuild_profiles(self):
        """Rebuild profile radio items in the menu."""
        # Remove old profile items
        for item in self._profile_items:
            self._menu.remove(item)
        self._profile_items.clear()

        if not self._profiles:
            self._profile_section.hide()
            self._sep_after_profiles.hide()
            return

        self._profile_section.show()
        self._sep_after_profiles.show()

        group = None
        for i, prof in enumerate(self._profiles):
            item = Gtk.RadioMenuItem.new_with_label([], prof.get("name", f"Profile {i}"))
            if group is not None:
                item.join_group(group)
            else:
                group = item

            uid = prof.get("uid", "")
            if uid == self._selected_uid:
                item.set_active(True)

            item.connect(
                "toggled",
                lambda w, u=uid: self._send("select_profile", uid=u) if w.get_active() else None,
            )
            # Insert after the profile header
            pos = self._profile_insert_pos + i
            self._menu.insert(item, pos)
            item.show()
            self._profile_items.append(item)

    def _update_state(self, state, message=""):
        self._state = state

        icon = _TRAY_ICONS.get(state, _TRAY_ICON_DEFAULT)
        self._indicator.set_icon_full(icon, f"Fortyfax — {state}")

        labels = {
            "DISCONNECTED": "Disconnesso",
            "CONNECTING": "Connessione in corso...",
            "CONNECTED": "Connesso",
            "DISCONNECTING": "Disconnessione...",
            "ERROR": f"Errore: {message}" if message else "Errore",
        }
        self._status_item.set_label(labels.get(state, state))

        is_connected = state in ("CONNECTED", "DISCONNECTING")
        if is_connected:
            self._connect_item.hide()
            self._disconnect_item.show()
        else:
            self._connect_item.show()
            self._disconnect_item.hide()

        can_connect = state in ("DISCONNECTED", "ERROR") and bool(self._profiles)
        self._connect_item.set_sensitive(can_connect)
        self._disconnect_item.set_sensitive(state == "CONNECTED")

    def _send(self, action, **kwargs):
        msg = {"action": action, **kwargs}
        try:
            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()
        except BrokenPipeError:
            Gtk.main_quit()

    def _read_stdin(self):
        """Read JSON commands from stdin (blocking, runs in thread)."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cmd = msg.get("cmd")
                if cmd == "update_state":
                    GLib.idle_add(
                        self._update_state,
                        msg.get("state", "DISCONNECTED"),
                        msg.get("message", ""),
                    )
                elif cmd == "set_profiles":
                    self._profiles = msg.get("profiles", [])
                    self._selected_uid = msg.get("selected_uid")
                    GLib.idle_add(self._rebuild_profiles)
                elif cmd == "quit":
                    GLib.idle_add(Gtk.main_quit)
                    return
        except Exception:
            pass
        GLib.idle_add(Gtk.main_quit)


def main():
    tray = TraySubprocess()
    Gtk.main()


if __name__ == "__main__":
    main()
