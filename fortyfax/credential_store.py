"""Secure credential storage using libsecret (GNOME Keyring / KDE Wallet).

Uses the freedesktop.org Secret Service D-Bus API, which is implemented by:
- GNOME Keyring (gnome-keyring-daemon)
- KDE Wallet (kwalletd5/kwalletd6 via ksecretservice)
"""

import logging

import gi

gi.require_version("Secret", "1")
from gi.repository import Secret

log = logging.getLogger(__name__)

_SCHEMA = Secret.Schema.new(
    "com.github.fortyfax.sso",
    Secret.SchemaFlags.NONE,
    {"profile_uid": Secret.SchemaAttributeType.STRING},
)

_VPN_SCHEMA = Secret.Schema.new(
    "com.github.fortyfax.vpn",
    Secret.SchemaFlags.NONE,
    {"profile_uid": Secret.SchemaAttributeType.STRING},
)


def store_sso_password(profile_uid: str, profile_name: str, password: str) -> bool:
    """Store SSO password in the system keyring."""
    try:
        Secret.password_store_sync(
            _SCHEMA,
            {"profile_uid": profile_uid},
            Secret.COLLECTION_DEFAULT,
            f"Fortyfax SSO — {profile_name}",
            password,
            None,
        )
        log.info("SSO password stored for profile %s", profile_name)
        return True
    except Exception as e:
        log.warning("Failed to store SSO password: %s", e)
        return False


def lookup_sso_password(profile_uid: str) -> str | None:
    """Retrieve SSO password from the system keyring."""
    try:
        password = Secret.password_lookup_sync(_SCHEMA, {"profile_uid": profile_uid}, None)
        return password
    except Exception as e:
        log.warning("Failed to lookup SSO password: %s", e)
        return None


def clear_sso_password(profile_uid: str) -> bool:
    """Remove SSO password from the system keyring."""
    try:
        Secret.password_clear_sync(_SCHEMA, {"profile_uid": profile_uid}, None)
        log.info("SSO password cleared for profile %s", profile_uid)
        return True
    except Exception as e:
        log.warning("Failed to clear SSO password: %s", e)
        return False


# --- VPN password (GlobalProtect / Fortinet password auth) ---

def store_vpn_password(profile_uid: str, profile_name: str, password: str) -> bool:
    """Store VPN login password in the system keyring."""
    try:
        Secret.password_store_sync(
            _VPN_SCHEMA,
            {"profile_uid": profile_uid},
            Secret.COLLECTION_DEFAULT,
            f"Fortyfax VPN — {profile_name}",
            password,
            None,
        )
        log.info("VPN password stored for profile %s", profile_name)
        return True
    except Exception as e:
        log.warning("Failed to store VPN password: %s", e)
        return False


def lookup_vpn_password(profile_uid: str) -> str | None:
    """Retrieve VPN login password from the system keyring."""
    try:
        return Secret.password_lookup_sync(_VPN_SCHEMA, {"profile_uid": profile_uid}, None)
    except Exception as e:
        log.warning("Failed to lookup VPN password: %s", e)
        return None


def clear_vpn_password(profile_uid: str) -> bool:
    """Remove VPN login password from the system keyring."""
    try:
        Secret.password_clear_sync(_VPN_SCHEMA, {"profile_uid": profile_uid}, None)
        log.info("VPN password cleared for profile %s", profile_uid)
        return True
    except Exception as e:
        log.warning("Failed to clear VPN password: %s", e)
        return False


def is_keyring_available() -> bool:
    """Check if a Secret Service provider (GNOME Keyring or KDE Wallet) is available."""
    try:
        service = Secret.Service.get_sync(Secret.ServiceFlags.NONE, None)
        return service is not None
    except Exception:
        return False
