#!/bin/bash
set -euo pipefail

APP_NAME="fortyfax"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/usr/local/share/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/${APP_NAME}.desktop"

echo "╔══════════════════════════════════════════════════════╗"
echo "║            Fortyfax - Installazione                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "⚠  Questo script deve essere eseguito come root."
    echo "   Usa: sudo ./install.sh"
    exit 1
fi

# Check prerequisites
echo "Verifica prerequisiti..."
MISSING=()

if ! command -v openfortivpn &>/dev/null; then
    MISSING+=("openfortivpn")
fi

if ! command -v pkexec &>/dev/null; then
    MISSING+=("polkit")
fi

if ! python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" 2>/dev/null; then
    MISSING+=("gtk4 python3-gobject")
fi

if ! python3 -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw" 2>/dev/null; then
    MISSING+=("libadwaita")
fi

if ! python3 -c "import gi; gi.require_version('WebKit', '6.0'); from gi.repository import WebKit" 2>/dev/null; then
    MISSING+=("webkitgtk6.0")
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo
    echo "⚠  Dipendenze mancanti rilevate!"
    echo "   Installa con:"
    echo
    echo "   sudo dnf install -y ${MISSING[*]}"
    echo
    read -rp "Vuoi installarle ora? [S/n] " answer
    if [[ "${answer,,}" != "n" ]]; then
        dnf install -y "${MISSING[@]}"
    else
        echo "Installazione annullata. Installa le dipendenze e riprova."
        exit 1
    fi
fi

# Install application
echo
echo "Installazione in ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
cp -r "${APP_DIR}/fortyfax" "${INSTALL_DIR}/"
cp "${APP_DIR}/fortyfax-bin" "${INSTALL_DIR}/"

# Create symlink
echo "Creazione link ${BIN_LINK}..."
ln -sf "${INSTALL_DIR}/fortyfax-bin" "${BIN_LINK}"

# Create .desktop file
echo "Creazione file .desktop..."
cat > "${DESKTOP_FILE}" <<DESKTOP
[Desktop Entry]
Name=Fortyfax
Comment=GUI per openfortivpn con supporto SAML/SSO
Exec=${BIN_LINK}
Icon=network-vpn
Type=Application
Terminal=false
Categories=Network;VPN;Security;
Keywords=VPN;Fortinet;FortiGate;SSL;SAML;SSO;
StartupNotify=true
DESKTOP

# Create polkit policy for openfortivpn (allows running without password prompt each time)
echo "Configurazione PolicyKit..."
cat > /usr/share/polkit-1/actions/com.github.fortyfax.policy <<POLKIT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <vendor>Fortyfax</vendor>
  <vendor_url>https://github.com</vendor_url>

  <action id="com.github.fortyfax.run-vpn">
    <description>Run openfortivpn VPN connection</description>
    <description xml:lang="it">Avvia connessione VPN openfortivpn</description>
    <message>Autenticazione richiesta per avviare la connessione VPN</message>
    <message xml:lang="it">Autenticazione richiesta per avviare la connessione VPN</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/bin/openfortivpn</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
POLKIT

echo
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✓ Installazione completata!                        ║"
echo "║                                                      ║"
echo "║  Avvia con: fortyfax                                 ║"
echo "║  Oppure dal menu applicazioni                        ║"
echo "╚══════════════════════════════════════════════════════╝"
