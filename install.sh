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

# Detect distro family
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" == "fedora" || "${ID_LIKE:-}" =~ "fedora" || "${ID_LIKE:-}" =~ "rhel" ]]; then
            echo "redhat"
        elif [[ "$ID" == "debian" || "$ID" == "ubuntu" || "${ID_LIKE:-}" =~ "debian" || "${ID_LIKE:-}" =~ "ubuntu" ]]; then
            echo "debian"
        else
            echo "unknown"
        fi
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
echo "Distribuzione rilevata: ${DISTRO}"

if [[ "$DISTRO" == "unknown" ]]; then
    echo "⚠  Distribuzione non riconosciuta. L'installazione continua ma"
    echo "   potresti dover installare le dipendenze manualmente."
fi

# Check prerequisites
echo "Verifica prerequisiti..."
MISSING=()

if ! command -v pkexec &>/dev/null; then
    MISSING+=("polkit")
fi

if ! python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" 2>/dev/null; then
    if [[ "$DISTRO" == "debian" ]]; then
        MISSING+=("python3-gi" "gir1.2-gtk-4.0")
    else
        MISSING+=("gtk4" "python3-gobject")
    fi
fi

if ! python3 -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw" 2>/dev/null; then
    if [[ "$DISTRO" == "debian" ]]; then
        MISSING+=("gir1.2-adw-1")
    else
        MISSING+=("libadwaita")
    fi
fi

if ! python3 -c "import gi; gi.require_version('WebKit', '6.0'); from gi.repository import WebKit" 2>/dev/null; then
    if [[ "$DISTRO" == "debian" ]]; then
        MISSING+=("gir1.2-webkit-6.0")
    else
        MISSING+=("webkitgtk6.0")
    fi
fi

if ! command -v openfortivpn &>/dev/null; then
    MISSING+=("openfortivpn")
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo
    echo "⚠  Dipendenze mancanti rilevate!"

    if [[ "$DISTRO" == "debian" ]]; then
        PKG_CMD="apt install -y ${MISSING[*]}"
    else
        PKG_CMD="dnf install -y ${MISSING[*]}"
    fi

    echo "   Installa con:"
    echo
    echo "   sudo $PKG_CMD"
    echo
    read -rp "Vuoi installarle ora? [S/n] " answer
    if [[ "${answer,,}" != "n" ]]; then
        if [[ "$DISTRO" == "debian" ]]; then
            apt update && apt install -y "${MISSING[@]}"
        else
            dnf install -y "${MISSING[@]}"
        fi
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
cp -r "${APP_DIR}/icons" "${INSTALL_DIR}/"
cp "${APP_DIR}/fortyfax-bin" "${INSTALL_DIR}/"
cp "${APP_DIR}/fortyfax-vpn-helper" "${INSTALL_DIR}/"
chmod 755 "${INSTALL_DIR}/fortyfax-vpn-helper"

# Create symlinks
echo "Creazione link ${BIN_LINK}..."
ln -sf "${INSTALL_DIR}/fortyfax-bin" "${BIN_LINK}"
ln -sf "${INSTALL_DIR}/fortyfax-vpn-helper" "/usr/local/bin/fortyfax-vpn-helper"

# Install app icon into system hicolor theme
echo "Installazione icone..."
for size in 16 24 32 48 64 128 256 512; do
    dest="/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$dest"
    cp "${APP_DIR}/icons/fortyfax_${size}.png" "$dest/com.github.fortyfax.png"
done
mkdir -p "/usr/share/icons/hicolor/scalable/apps"
cp "${APP_DIR}/icons/fortyfax.svg" "/usr/share/icons/hicolor/scalable/apps/com.github.fortyfax.svg"
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

# Create .desktop file
echo "Creazione file .desktop..."
cat > "${DESKTOP_FILE}" <<DESKTOP
[Desktop Entry]
Name=Fortyfax
Comment=GUI per openfortivpn e GlobalProtect con supporto SAML/SSO
Exec=${BIN_LINK}
Icon=com.github.fortyfax
Type=Application
Terminal=false
Categories=Network;VPN;Security;
Keywords=VPN;Fortinet;FortiGate;GlobalProtect;PaloAlto;SSL;SAML;SSO;
StartupNotify=true
StartupWMClass=com.github.fortyfax
DESKTOP

# Create polkit policy
echo "Configurazione PolicyKit..."
POLKIT_DIR="/usr/share/polkit-1/actions"
mkdir -p "$POLKIT_DIR"
cat > "${POLKIT_DIR}/com.github.fortyfax.policy" <<POLKIT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <vendor>Fortyfax</vendor>
  <vendor_url>https://stazzo@bitbucket.org/decisyon/fortyfax</vendor_url>

  <action id="com.github.fortyfax.run-vpn">
    <description>Manage VPN connection (start/stop)</description>
    <description xml:lang="it">Gestisci connessione VPN (avvio/arresto)</description>
    <message>Authentication required to manage VPN connection</message>
    <message xml:lang="it">Autenticazione richiesta per gestire la connessione VPN</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>yes</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/local/bin/fortyfax-vpn-helper</annotate>
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
