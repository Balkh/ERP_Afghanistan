import os
import json
import base64
from utils.device_fingerprint import generate_device_id
from config.production_config import get_data_path
from utils.logger import get_logger

log = get_logger('session')

SESSION_FILENAME = 'session.enc'
LEGACY_FILENAME = 'session.dat'


def _derive_key() -> bytes:
    """Derive encryption key from device fingerprint."""
    device_id = generate_device_id()
    key = device_id.encode('utf-8')
    # Pad or truncate to 32 bytes
    if len(key) < 32:
        key = key.ljust(32, b'\x00')
    else:
        key = key[:32]
    return key


def _xor_encrypt(data: str, key: bytes) -> str:
    """XOR encrypt data with key, return base64."""
    data_bytes = data.encode('utf-8')
    encrypted = bytearray()
    for i, byte in enumerate(data_bytes):
        encrypted.append(byte ^ key[i % len(key)])
    return base64.b64encode(bytes(encrypted)).decode('utf-8')


def _xor_decrypt(encrypted_b64: str, key: bytes):
    """Decrypt base64 XOR data, return string or None on failure."""
    try:
        encrypted = base64.b64decode(encrypted_b64.encode('utf-8'))
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])
        return decrypted.decode('utf-8')
    except Exception:
        return None


def _get_session_path() -> str:
    """Get path to encrypted session file."""
    data_dir = get_data_path()
    return os.path.join(data_dir, SESSION_FILENAME)


def _get_legacy_path() -> str:
    """Get path to legacy plaintext session file."""
    # Legacy path was relative to frontend/ directory
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..')
    return os.path.abspath(os.path.join(base, LEGACY_FILENAME))


def save_session(username: str, access_token: str, refresh_token: str = ''):
    """Encrypt and save session data to disk."""
    try:
        key = _derive_key()
        data = json.dumps({
            'username': username,
            'access_token': access_token,
            'refresh_token': refresh_token,
        })
        encrypted = _xor_encrypt(data, key)
        path = _get_session_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(encrypted)
        _remove_legacy()
        log.info(f"Session saved for user: {username}",
                 extra={'extra_fields': {'tags': ['auth', 'session']}})
        return True
    except Exception as e:
        log.error(f"Session save failed: {e}",
                   extra={'extra_fields': {'tags': ['auth', 'session', 'error']}})
        return False


def load_session():
    """Load session data.
    Returns (username, access_token, refresh_token) or (None, None, None).
    Falls back to legacy session.dat if encrypted file not found.
    """
    try:
        path = _get_session_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                encrypted = f.read()
            key = _derive_key()
            decrypted = _xor_decrypt(encrypted, key)
            if decrypted:
                data = json.loads(decrypted)
                username = data.get('username')
                log.info(f"Session loaded for user: {username}",
                         extra={'extra_fields': {'tags': ['auth', 'session']}})
                return (
                    username,
                    data.get('access_token'),
                    data.get('refresh_token', ''),
                )
            log.warning("Session decryption returned None",
                         extra={'extra_fields': {'tags': ['auth', 'session', 'error']}})
    except Exception as e:
        log.warning(f"Session load error: {e}",
                     extra={'extra_fields': {'tags': ['auth', 'session', 'error']}})

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
    """Remove session file."""
    try:
        path = _get_session_path()
        if os.path.exists(path):
            os.remove(path)
            log.info("Session cleared",
                     extra={'extra_fields': {'tags': ['auth', 'session']}})
    except Exception as e:
        log.warning(f"Session clear error: {e}",
                     extra={'extra_fields': {'tags': ['auth', 'session', 'error']}})
    _remove_legacy()


def _remove_legacy():
    """Remove legacy session.dat if it exists."""
    try:
        path = _get_legacy_path()
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _migrate_from_legacy():
    """Migrate legacy session to encrypted format. Call on startup."""
    username, token, _ = _load_legacy()
    if username and token:
        save_session(username, token)
