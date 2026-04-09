"""Simple local encryption for VPN passwords.

Uses a random key stored in ~/.config/fortyfax/.secret (permissions 0600).
The encryption is XOR with a key derived via PBKDF2, then base64 encoded.
This prevents casual reading of passwords from JSON profile files.

The key never leaves the machine. If the key is lost, passwords must be
re-entered (they are not recoverable).
"""

import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path

log = logging.getLogger(__name__)

_KEY_FILE = Path.home() / ".config" / "fortyfax" / ".secret"
_KEY_LENGTH = 32  # bytes
_key_cache: bytes | None = None


def _get_key() -> bytes:
    """Get or create the local encryption key."""
    global _key_cache
    if _key_cache is not None:
        return _key_cache

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

    if _KEY_FILE.exists():
        raw = _KEY_FILE.read_bytes()
        if len(raw) >= _KEY_LENGTH:
            _key_cache = raw[:_KEY_LENGTH]
            return _key_cache

    # Generate new key
    key = secrets.token_bytes(_KEY_LENGTH)
    _KEY_FILE.write_bytes(key)
    os.chmod(_KEY_FILE, 0o600)
    log.info("Generated new encryption key: %s", _KEY_FILE)
    _key_cache = key
    return key


def _derive_key(key: bytes, salt: bytes) -> bytes:
    """Derive a key using PBKDF2."""
    return hashlib.pbkdf2_hmac("sha256", key, salt, iterations=100_000, dklen=64)


def encrypt(plaintext: str) -> str:
    """Encrypt a string, returning a base64-encoded token."""
    if not plaintext:
        return ""
    key = _get_key()
    salt = secrets.token_bytes(16)
    derived = _derive_key(key, salt)

    data = plaintext.encode("utf-8")
    # XOR with derived key (repeating)
    encrypted = bytes(b ^ derived[i % len(derived)] for i, b in enumerate(data))

    # salt (16 bytes) + encrypted data -> base64
    token = base64.b64encode(salt + encrypted).decode("ascii")
    return token


def decrypt(token: str) -> str:
    """Decrypt a base64-encoded token back to plaintext."""
    if not token:
        return ""
    try:
        key = _get_key()
        raw = base64.b64decode(token)
        salt = raw[:16]
        encrypted = raw[16:]
        derived = _derive_key(key, salt)

        data = bytes(b ^ derived[i % len(derived)] for i, b in enumerate(encrypted))
        return data.decode("utf-8")
    except Exception as e:
        log.warning("Failed to decrypt password: %s", e)
        return ""
