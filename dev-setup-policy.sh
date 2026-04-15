#!/bin/bash
# Install PolicyKit policy for running Fortyfax from a DEVELOPMENT copy
# (without installing the RPM/DEB package).
#
# After running this once (with sudo), pkexec will NOT ask for a password
# when launching the VPN helper from this development directory.
#
# Usage: sudo ./dev-setup-policy.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "⚠  Esegui con sudo: sudo ./dev-setup-policy.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER_PATH="${SCRIPT_DIR}/fortyfax-vpn-helper"

if [[ ! -x "$HELPER_PATH" ]]; then
    echo "⚠  Helper non trovato o non eseguibile: $HELPER_PATH"
    exit 1
fi

POLICY_FILE="/usr/share/polkit-1/actions/com.github.fortyfax.dev.policy"

echo "→ Installo policy PolicyKit per dev path:"
echo "   $HELPER_PATH"
echo

cat > "$POLICY_FILE" <<POLKIT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <vendor>Fortyfax (dev)</vendor>
  <vendor_url>https://bitbucket.org/decisyon/fortyfax</vendor_url>

  <action id="com.github.fortyfax.dev.run-vpn">
    <description>Manage VPN connection (Fortyfax dev)</description>
    <description xml:lang="it">Gestisci connessione VPN (Fortyfax dev)</description>
    <message>Authentication required to manage VPN connection</message>
    <message xml:lang="it">Autenticazione richiesta per gestire la connessione VPN</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>yes</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">${HELPER_PATH}</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
POLKIT

chmod 644 "$POLICY_FILE"

echo "✓ Policy installata: $POLICY_FILE"
echo
echo "Per rimuoverla:"
echo "   sudo rm $POLICY_FILE"
echo
echo "Ora pkexec non chiederà più la password per questo helper."
