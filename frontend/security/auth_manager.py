"""
Authentication Manager — handles login, logout, token storage, and session lifecycle.
Centralizes auth state for the frontend, integrates with APIClient and RoleRenderer.
SINGLE SOURCE OF TRUTH for session management (Rule 4 compliance).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal

from api.client import APIClient
from utils.logger import get_logger

log = get_logger('auth')

# Token storage path (managed exclusively by AuthManager)
_TOKEN_DIR = Path(__file__).parent.parent / "runtime" / "auth"
_TOKEN_FILE = _TOKEN_DIR / "session.json"


class AuthManager(QObject):
    """Manages authentication state, token lifecycle, and UI scoping."""

    # Signals
    login_success = Signal(dict)    # user data
    login_failed = Signal(str)      # error message
    logout_signal = Signal()
    session_expired = Signal()
    ui_scopes_changed = Signal(dict)  # ui_scopes payload

    def __init__(self, api_client: Optional[APIClient] = None):
        super().__init__()
        self.api_client = api_client or APIClient()
        self._user_data: Optional[Dict[str, Any]] = None
        self._ui_scopes: Dict[str, Any] = {"sidebar": [], "screens": [], "actions": {}, "hidden": []}
        self._roles: list = []
        self._permissions: list = []
        self._is_authenticated = False

        # Restore session if tokens exist
        self._restore_session()

    # ── Public API ──

    def login(self, username: str, password: str) -> bool:
        """Authenticate user and store session. Returns True on success.
        
        NOTE: This is a synchronous call to the API. 
        The caller is responsible for executing this in a non-blocking way 
        (e.g., via QTimer.singleShot or a Worker Thread).
        """
        try:
            result = self.api_client.post("/api/auth/login/", {
                "username": username,
                "password": password,
            })

            if not result.get("success"):
                error = result.get("error", {}).get("message", "Login failed")
                self.login_failed.emit(error)
                return False

            data = result.get("data", {})
            self._store_session(data)
            self._is_authenticated = True

            user_info = data.get("user", {})
            self._user_data = user_info
            self._roles = user_info.get("roles", [])
            self._ui_scopes = data.get("ui_scopes", self._ui_scopes)

            self.api_client.set_auth_data(data)
            self.ui_scopes_changed.emit(self._ui_scopes)
            self.login_success.emit(user_info)

            log.info(f"Login successful for {username}", extra={'extra_fields': {'tags': ['auth']}})
            return True

        except Exception as e:
            log.error(f"Login error: {e}", extra={'extra_fields': {'tags': ['auth', 'error']}})
            self.login_failed.emit(str(e))
            return False

    def logout(self) -> None:
        """Logout user, clear session, and revoke tokens."""
        try:
            self.api_client.post("/api/auth/logout/", {})
        except Exception:
            pass  # Best-effort: clear local state even if server logout fails

        self._clear_session()
        self._is_authenticated = False
        self._user_data = None
        self._roles = []
        self._ui_scopes = {"sidebar": [], "screens": [], "actions": {}, "hidden": []}
        self.logout_signal.emit()
        log.info("User logged out", extra={'extra_fields': {'tags': ['auth']}})

    def has_access(self, module: str) -> bool:
        """Check if current user has access to a module."""
        if not self._is_authenticated:
            return False
        if "Admin" in self._roles:
            return True
        return module in self._ui_scopes.get("sidebar", [])

    def has_screen_access(self, screen: str) -> bool:
        """Check if current user can see a specific screen."""
        if not self._is_authenticated:
            return False
        if "Admin" in self._roles:
            return True
        return screen in self._ui_scopes.get("screens", [])

    def has_action(self, module: str, action: str) -> bool:
        """Check if current user can perform an action in a module."""
        if not self._is_authenticated:
            return False
        if "Admin" in self._roles:
            return True
        module_actions = self._ui_scopes.get("actions", {}).get(module, [])
        return action in module_actions

    def get_visible_modules(self) -> list:
        """Return list of modules visible in sidebar for current user."""
        if not self._is_authenticated:
            return []
        if "Admin" in self._roles:
            return ["dashboard", "inventory", "sales", "purchases", "accounting",
                    "finance", "hr", "reports", "governance", "system", "observability"]
        return self._ui_scopes.get("sidebar", [])

    def get_hidden_modules(self) -> list:
        """Return list of modules hidden from current user."""
        if not self._is_authenticated:
            return ["dashboard", "inventory", "sales", "purchases", "accounting",
                    "finance", "hr", "reports", "governance", "system", "observability"]
        if "Admin" in self._roles:
            return []
        return self._ui_scopes.get("hidden", [])

    @property
    def user(self) -> Optional[Dict[str, Any]]:
        return self._user_data

    @property
    def roles(self) -> list:
        return self._roles

    @property
    def permissions(self) -> list:
        return self._permissions

    @property
    def ui_scopes(self) -> Dict[str, Any]:
        return self._ui_scopes

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    # ── Session Persistence (Single Source of Truth) ──

    def _store_session(self, data: Dict[str, Any]) -> None:
        """Persist session tokens and metadata in the encrypted session store."""
        try:
            from security.session_store import save_session_data
            session = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "user": data.get("user"),
                "ui_scopes": data.get("ui_scopes"),
            }
            if not save_session_data(session):
                raise RuntimeError("encrypted session save failed")
            self._remove_plaintext_session_file()
        except Exception as e:
            log.error(f"Failed to store session: {e}", extra={'extra_fields': {'tags': ['auth', 'error']}})

    def _migrate_plaintext_session_file(self) -> None:
        """One-time migration from the old plaintext session.json, then delete it."""
        if not _TOKEN_FILE.exists():
            return
        try:
            with open(_TOKEN_FILE, "r") as f:
                session = json.load(f)
            if isinstance(session, dict) and session.get("access_token"):
                from security.session_store import save_session_data
                save_session_data(session)
        except Exception as e:
            log.warning(f"Plaintext session migration skipped: {e}", extra={'extra_fields': {'tags': ['auth', 'session']}})
        finally:
            self._remove_plaintext_session_file()

    @staticmethod
    def _remove_plaintext_session_file() -> None:
        try:
            if _TOKEN_FILE.exists():
                _TOKEN_FILE.unlink()
        except Exception:
            pass

    def _restore_session(self) -> None:
        """Restore session from encrypted store if tokens exist."""
        self._migrate_plaintext_session_file()
        try:
            from security.session_store import load_session_data
            session = load_session_data()
            if not session:
                return

            access_token = session.get("access_token")
            if not access_token:
                return

            self.api_client.set_auth_data(session)
            self._user_data = session.get("user") if isinstance(session.get("user"), dict) else None
            self._ui_scopes = session.get("ui_scopes", self._ui_scopes) or self._ui_scopes
            self._roles = self._user_data.get("roles", []) if self._user_data else []
            self._is_authenticated = True

            log.info("Encrypted session restored", extra={'extra_fields': {'tags': ['auth']}})

        except Exception as e:
            log.error(f"Failed to restore session: {e}", extra={'extra_fields': {'tags': ['auth', 'error']}})
            self._clear_session()

    def _clear_session(self) -> None:
        """Remove ALL session data from disk and memory (single source of truth)."""
        self.api_client.clear_auth_token()
        self._remove_plaintext_session_file()
        try:
            from security.session_store import clear_session as _clear_encrypted
            _clear_encrypted()
        except Exception:
            pass
