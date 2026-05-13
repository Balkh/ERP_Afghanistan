"""
Phase 5B.16 — Secure Session Store.

Replaces insecure XOR encryption with Fernet (AES-CBC + HMAC).
Backward compatible — can load legacy XOR-encrypted sessions.
"""
import os
import json
import base64
from cryptography.fernet import Fernet
from utils.device_fingerprint import generate_device_id
from config.production_config import get_data_path
from utils.logger import get_logger

log = get_logger('session')

SESSION_FILENAME = 'session.enc'
LEGACY_FILENAME = 'session.dat'


def _derive_fernet_key() -> bytes:
    """Derive a valid Fernet key (32 url-safe base64 bytes) from device fingerprint."""
    device_id = generate_device_id()
    # Fernet requires a 32-byte url-safe-base64 key
    raw = device_id.encode('utf-8').ljust(32, b'\x00')[:32]
    return base64.urlsafe_b64encode(raw)


def _fernet_encrypt(data: str) -> str:
    key = _derive_fernet_key()
    f = Fernet(key)
    return f.encrypt(data.encode('utf-8')).decode('utf-8')


def _fernet_decrypt(encrypted: str) -> str:
    key = _derive_fernet_key()
    f = Fernet(key)
    return f.decrypt(encrypted.encode('utf-8')).decode('utf-8')


def _xor_decrypt(encrypted_b64: str, key: bytes):
    """Legacy XOR decryption for backward compatibility with old session files."""
    try:
        enc = base64.b64decode(encrypted_b64.encode('utf-8'))
        dec = bytearray()
        for i, byte in enumerate(enc):
            dec.append(byte ^ key[i % len(key)])
        return dec.decode('utf-8')
    except Exception:
        return None


def _get_session_path() -> str:
    data_dir = get_data_path()
    return os.path.join(data_dir, SESSION_FILENAME)


def _get_legacy_path() -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..')
    return os.path.abspath(os.path.join(base, LEGACY_FILENAME))


def save_session(username: str, access_token: str, refresh_token: str = ''):
    """Encrypt (Fernet) and save session data to disk."""
    try:
        data = json.dumps({
            'username': username,
            'access_token': access_token,
            'refresh_token': refresh_token,
            '_v': '2',
        })
        encrypted = _fernet_encrypt(data)
        path = _get_session_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(encrypted)
        _remove_legacy()
        log.info(f"Session saved for user: {username}")
        return True
    except Exception as e:
        log.error(f"Session save failed: {e}")
        return False


def load_session():
    """Load session data. Tries Fernet first, falls back to legacy XOR."""
    try:
        path = _get_session_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
            # Try Fernet first (new format)
            try:
                decrypted = _fernet_decrypt(content)
                data = json.loads(decrypted)
                username = data.get('username')
                log.info(f"Session loaded for user: {username}")
                return (username, data.get('access_token'), data.get('refresh_token', ''))
            except Exception:
                pass
            # Fallback: legacy XOR
            key_bytes = generate_device_id().encode('utf-8')[:32].ljust(32, b'\x00')
            decrypted = _xor_decrypt(content, key_bytes)
            if decrypted:
                data = json.loads(decrypted)
                username = data.get('username')
                log.info(f"Session loaded (legacy) for user: {username}")
                return (username, data.get('access_token'), data.get('refresh_token', ''))
    except Exception as e:
        log.warning(f"Session load error: {e}")

    return _load_legacy()


def _load_legacy():
    """Load legacy plaintext session.dat for backward compatibility."""
    try:
        path = _get_legacy_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                parts = f.read().split(':')
                if len(parts) == 2:
                    return parts[0], parts[1], ''
    except Exception:
        pass
    return None, None, None


def clear_session():
    try:
        path = _get_session_path()
        if os.path.exists(path):
            os.remove(path)
            log.info("Session cleared")
    except Exception as e:
        log.warning(f"Session clear error: {e}")
    _remove_legacy()


def _remove_legacy():
    try:
        path = _get_legacy_path()
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _migrate_from_legacy():
    username, token, _ = _load_legacy()
    if username and token:
        save_session(username, token)
