"""
Multi-Tenant Context Manager.
Thread-local storage for company context.
All data access is scoped to the current company automatically.
"""
import threading
from typing import Optional
from contextlib import contextmanager


class _ThreadLocal:
    """Thread-local storage for tenant context."""
    _storage = threading.local()

    @classmethod
    def get(cls, key: str, default=None):
        return getattr(cls._storage, key, default)

    @classmethod
    def set(cls, key: str, value):
        setattr(cls._storage, key, value)

    @classmethod
    def clear(cls):
        """Clear all thread-local data."""
        cls._storage.__dict__.clear()


class TenantContext:
    """
    Thread-safe tenant context manager.
    Provides company context for the current request/thread.
    """
    _COMPANY_ID_KEY = '_company_id'
    _COMPANY_CODE_KEY = '_company_code'
    _USER_ID_KEY = '_user_id'
    _REQUEST_ID_KEY = '_request_id'

    @classmethod
    def set_company_id(cls, company_id: Optional[str]):
        """Set current company ID for this thread."""
        _ThreadLocal.set(cls._COMPANY_ID_KEY, company_id)

    @classmethod
    def get_company_id(cls) -> Optional[str]:
        """Get current company ID for this thread."""
        return _ThreadLocal.get(cls._COMPANY_ID_KEY)

    @classmethod
    def set_company_code(cls, company_code: Optional[str]):
        """Set current company code for this thread."""
        _ThreadLocal.set(cls._COMPANY_CODE_KEY, company_code)

    @classmethod
    def get_company_code(cls) -> Optional[str]:
        """Get current company code for this thread."""
        return _ThreadLocal.get(cls._COMPANY_CODE_KEY)

    @classmethod
    def set_user_id(cls, user_id: Optional[str]):
        """Set current user ID for this thread."""
        _ThreadLocal.set(cls._USER_ID_KEY, user_id)

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get current user ID for this thread."""
        return _ThreadLocal.get(cls._USER_ID_KEY)

    @classmethod
    def set_request_id(cls, request_id: Optional[str]):
        """Set current request ID for this thread."""
        _ThreadLocal.set(cls._REQUEST_ID_KEY, request_id)

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Get current request ID for this thread."""
        return _ThreadLocal.get(cls._REQUEST_ID_KEY)

    @classmethod
    def clear(cls):
        """Clear all context for this thread."""
        _ThreadLocal.clear()

    @classmethod
    def has_context(cls) -> bool:
        """Check if company context is set."""
        return cls.get_company_id() is not None

    @classmethod
    def get_context(cls) -> dict:
        """Get full context snapshot."""
        return {
            'company_id': cls.get_company_id(),
            'company_code': cls.get_company_code(),
            'user_id': cls.get_user_id(),
            'request_id': cls.get_request_id(),
        }

    @classmethod
    @contextmanager
    def override(cls, company_id: Optional[str] = None, company_code: Optional[str] = None):
        """Temporarily override company context within a block."""
        prev_company_id = cls.get_company_id()
        prev_company_code = cls.get_company_code()
        try:
            if company_id is not None:
                cls.set_company_id(company_id)
            if company_code is not None:
                cls.set_company_code(company_code)
            yield
        finally:
            cls.set_company_id(prev_company_id)
            cls.set_company_code(prev_company_code)
