#!/bin/bash
set -euo pipefail

APP_NAME="fortyfax"

if [[ $EUID -ne 0 ]]; then
    echo "Usa: sudo ./uninstall.sh"
    exit 1
fi

echo "Rimozione Fortyfax..."

rm -rf "/usr/local/share/${APP_NAME}"
rm -f "/usr/local/bin/${APP_NAME}"
rm -f "/usr/share/applications/${APP_NAME}.desktop"
rm -f "/usr/share/polkit-1/actions/com.github.fortyfax.policy"

echo "✓ Disinstallazione completata."
echo "  I profili VPN in ~/.config/fortyfax/ NON sono stati rimossi."
