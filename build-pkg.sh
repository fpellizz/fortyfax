#!/bin/bash
# Build RPM and/or DEB packages for Fortyfax using fpm.
#
# Usage:
#   ./build-pkg.sh          # Build both RPM and DEB
#   ./build-pkg.sh rpm      # Build RPM only
#   ./build-pkg.sh deb      # Build DEB only
#
# Requirements:
#   gem install fpm
#   dnf install rpm-build     (for RPM)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Extract version from Python package
VERSION=$(python3 -c "
import sys; sys.path.insert(0, '.')
from fortyfax import __version__; print(__version__)
")
NAME="fortyfax"
ARCH="noarch"
MAINTAINER="Fabio Pellizzaro <fabio.pellizzaro@decisyon.com>"
URL="https://bitbucket.org/decisyon/fortyfax"
DESCRIPTION="GUI per openfortivpn e GlobalProtect con supporto SAML/SSO"
LICENSE="GPL-3.0"

echo "╔══════════════════════════════════════════════════════╗"
echo "║         Fortyfax — Build pacchetti v${VERSION}          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo

# Check fpm is available
if ! command -v fpm &>/dev/null; then
    echo "❌ fpm non trovato. Installa con: sudo gem install fpm"
    exit 1
fi

# Create staging directory
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT

echo "→ Staging in $STAGING"

# --- Stage files ---

# Python package (exclude __pycache__)
PYDIR="$STAGING/usr/share/fortyfax"
mkdir -p "$PYDIR"
rsync -a --exclude='__pycache__' --exclude='*.pyc' fortyfax/ "$PYDIR/fortyfax/"
rsync -a icons/ "$PYDIR/icons/"
cp fortyfax-bin "$PYDIR/"
cp fortyfax-vpn-helper "$PYDIR/"
chmod 755 "$PYDIR/fortyfax-bin"
chmod 755 "$PYDIR/fortyfax-vpn-helper"

# Launcher symlinks (created via fpm --after-install)
BINDIR="$STAGING/usr/bin"
mkdir -p "$BINDIR"
ln -sf "/usr/share/fortyfax/fortyfax-bin" "$BINDIR/fortyfax"
ln -sf "/usr/share/fortyfax/fortyfax-vpn-helper" "$BINDIR/fortyfax-vpn-helper"

# Desktop file
APPDIR="$STAGING/usr/share/applications"
mkdir -p "$APPDIR"
cat > "$APPDIR/com.github.fortyfax.desktop" <<DESKTOP
[Desktop Entry]
Name=Fortyfax
Comment=GUI per openfortivpn e GlobalProtect con supporto SAML/SSO
Exec=/usr/bin/fortyfax
Icon=com.github.fortyfax
Type=Application
Terminal=false
Categories=Network;VPN;Security;
Keywords=VPN;Fortinet;FortiGate;GlobalProtect;PaloAlto;SSL;SAML;SSO;
StartupNotify=true
StartupWMClass=com.github.fortyfax
DESKTOP

# Icons in hicolor theme
for size in 16 24 32 48 64 128 256 512; do
    ICONDIR="$STAGING/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$ICONDIR"
    cp "icons/fortyfax_${size}.png" "$ICONDIR/com.github.fortyfax.png"
done
mkdir -p "$STAGING/usr/share/icons/hicolor/scalable/apps"
cp "icons/fortyfax.svg" "$STAGING/usr/share/icons/hicolor/scalable/apps/com.github.fortyfax.svg"

# PolicyKit policy
POLKITDIR="$STAGING/usr/share/polkit-1/actions"
mkdir -p "$POLKITDIR"
cat > "$POLKITDIR/com.github.fortyfax.policy" <<POLKIT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <vendor>Fortyfax</vendor>
  <vendor_url>${URL}</vendor_url>
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
    <annotate key="org.freedesktop.policykit.exec.path">/usr/bin/fortyfax-vpn-helper</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
POLKIT

# Post-install script (update icon cache)
POSTINSTALL=$(mktemp)
cat > "$POSTINSTALL" <<'SCRIPT'
#!/bin/bash
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
SCRIPT
chmod +x "$POSTINSTALL"

# Output directory
OUTDIR="$SCRIPT_DIR/dist"
mkdir -p "$OUTDIR"

# Common fpm args
FPM_ARGS=(
    --name "$NAME"
    --version "$VERSION"
    --architecture "$ARCH"
    --maintainer "$MAINTAINER"
    --url "$URL"
    --description "$DESCRIPTION"
    --license "$LICENSE"
    --after-install "$POSTINSTALL"
    --after-remove "$POSTINSTALL"
    -C "$STAGING"
)

BUILD_WHAT="${1:-all}"

# --- Build RPM ---
if [[ "$BUILD_WHAT" == "all" || "$BUILD_WHAT" == "rpm" ]]; then
    echo
    echo "→ Building RPM..."
    fpm -s dir -t rpm \
        "${FPM_ARGS[@]}" \
        --depends python3 \
        --depends gtk4 \
        --depends libadwaita \
        --depends python3-gobject \
        --depends polkit \
        --rpm-summary "$DESCRIPTION" \
        --package "$OUTDIR/${NAME}-${VERSION}-1.noarch.rpm" \
        .

    echo "  ✓ $OUTDIR/${NAME}-${VERSION}-1.noarch.rpm"
fi

# --- Build DEB ---
if [[ "$BUILD_WHAT" == "all" || "$BUILD_WHAT" == "deb" ]]; then
    echo
    echo "→ Building DEB..."
    fpm -s dir -t deb \
        "${FPM_ARGS[@]}" \
        --depends python3 \
        --depends "python3-gi" \
        --depends "gir1.2-gtk-4.0" \
        --depends "gir1.2-adw-1" \
        --depends "policykit-1" \
        --deb-priority optional \
        --category net \
        --package "$OUTDIR/${NAME}_${VERSION}_all.deb" \
        .

    echo "  ✓ $OUTDIR/${NAME}_${VERSION}_all.deb"
fi

echo
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✓ Build completato!                                ║"
echo "║                                                      ║"
echo "║  Pacchetti in: dist/                                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo
ls -lh "$OUTDIR/"*.{rpm,deb} 2>/dev/null

# Cleanup
rm -f "$POSTINSTALL"
