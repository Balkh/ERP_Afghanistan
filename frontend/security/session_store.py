"""Encrypted session store for frontend authentication data."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

from config.production_config import get_data_path
from utils.atomic_io import atomic_write_text
from utils.device_fingerprint import generate_device_id
from utils.logger import get_logger

log = get_logger('session')

SESSION_FILENAME = 'session.enc'
LEGACY_FILENAME = 'session.dat'


def _derive_fernet_key() -> bytes:
    """Derive a valid Fernet key from the local device fingerprint."""
    device_id = generate_device_id()
    raw = device_id.encode('utf-8').ljust(32, b'\x00')[:32]
    return base64.urlsafe_b64encode(raw)


def _fernet_encrypt(data: str) -> str:
    return Fernet(_derive_fernet_key()).encrypt(data.encode('utf-8')).decode('utf-8')


def _fernet_decrypt(encrypted: str) -> str:
    return Fernet(_derive_fernet_key()).decrypt(encrypted.encode('utf-8')).decode('utf-8')


def _get_session_path() -> str:
    return os.path.join(get_data_path(), SESSION_FILENAME)


def _get_legacy_path() -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..')
    return os.path.abspath(os.path.join(base, LEGACY_FILENAME))


def save_session_data(session: Dict[str, Any]) -> bool:
    """Encrypt and persist the full session payload."""
    try:
        payload = dict(session or {})
        payload['_v'] = '3'
        encrypted = _fernet_encrypt(json.dumps(payload))
        atomic_write_text(_get_session_path(), encrypted)
        _remove_legacy()
        log.info("Encrypted session saved")
        return True
    except Exception as e:
        log.error(f"Session save failed: {e}")
        return False


def load_session_data() -> Optional[Dict[str, Any]]:
    """Load only the encrypted Fernet session payload."""
    path = _get_session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            content = f.read()
        data = json.loads(_fernet_decrypt(content))
        if not isinstance(data, dict):
            clear_session()
            return None
        log.info(f"Encrypted session loaded for user: {data.get('username') or (data.get('user') or {}).get('username')}")
        return data
    except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning(f"Encrypted session invalid; clearing: {e}")
        clear_session()
        return None
    except Exception as e:
        log.warning(f"Session load error: {e}")
        return None


def save_session(username: str, access_token: str, refresh_token: str = '') -> bool:
    """Compatibility wrapper that still stores data in encrypted form only."""
    return save_session_data({
        'username': username,
        'access_token': access_token,
        'refresh_token': refresh_token,
    })


def load_session() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Compatibility wrapper for login prefill; no plaintext fallback."""
    data = load_session_data()
    if not data:
        return None, None, None
    user = data.get('user') if isinstance(data.get('user'), dict) else {}
    username = data.get('username') or user.get('username')
    return username, data.get('access_token'), data.get('refresh_token', '')


def clear_session() -> None:
    try:
        path = _get_session_path()
        if os.path.exists(path):
            os.remove(path)
            log.info("Encrypted session cleared")
    except Exception as e:
        log.warning(f"Session clear error: {e}")
    _remove_legacy()


def _remove_legacy() -> None:
    try:
        path = _get_legacy_path()
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _migrate_from_legacy() -> bool:
    """Legacy plaintext session restore is disabled; remove stale legacy file."""
    existed = os.path.exists(_get_legacy_path())
    _remove_legacy()
    return False if existed else False
