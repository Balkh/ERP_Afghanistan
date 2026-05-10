import sys
import os
import re
import time
import threading
import logging
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar
from config.production_config import get_log_path


LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}

MAX_FILE_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 3
LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Patterns to sanitize from log messages (tokens, passwords, secrets)
_SENSITIVE_PATTERNS = [
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(access_token["\']?\s*[:=]\s*["\']?)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(refresh_token["\']?\s*[:=]\s*["\']?)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)[^"\'}\s,;]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)[^"\'}\s,;]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(token["\']?\s*[:=]\s*["\']?)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'\1[REDACTED]'),
]

_SENSITIVE_KEYWORDS = ['password', 'secret', 'token', 'authorization', 'jwt', 'api_key', 'apikey']


def sanitize_message(message: str) -> str:
    """Strip sensitive data from log messages. Never logs passwords/tokens/secrets."""
    if not isinstance(message, str):
        return str(message)
    result = message
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _is_sensitive_key(key: str) -> bool:
    """Check if a dict key likely contains sensitive data."""
    key_lower = key.lower().replace('_', '').replace('-', '')
    return any(kw in key_lower for kw in _SENSITIVE_KEYWORDS)


def sanitize_dict(data: dict) -> dict:
    """Return a copy of dict with sensitive values redacted."""
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        if _is_sensitive_key(k):
            result[k] = '[REDACTED]'
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, str):
            result[k] = sanitize_message(v)
        else:
            result[k] = v
    return result


class ContextFormatter(logging.Formatter):
    """Formatter that consumes extra_fields and appends tags to log output."""

    def format(self, record):
        msg = super().format(record)
        extra = getattr(record, 'extra_fields', None)
        if isinstance(extra, dict):
            parts = []
            tags = extra.get('tags')
            if tags:
                parts.append(f"[{','.join(tags)}]")
            extra_clean = {k: v for k, v in extra.items() if k != 'tags' and v is not None}
            if extra_clean:
                for k, v in extra_clean.items():
                    parts.append(f"{k}={v}")
            if parts:
                msg = f"{msg} {' '.join(parts)}"
        msg = sanitize_message(msg)
        return msg


class _LoggerManager:
    def __init__(self):
        self._initialized = False
        self._root_logger = None

    def init_logging(self, level=logging.DEBUG):
        if self._initialized:
            return
        try:
            log_dir = get_log_path()
        except Exception:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        self._root_logger = logging.getLogger('PharmacyERP')
        self._root_logger.setLevel(level)
        self._root_logger.handlers.clear()

        formatter = ContextFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

        try:
            log_file = os.path.join(log_dir, 'pharmacy_erp.log')
            file_handler = RotatingFileHandler(
                log_file, maxBytes=MAX_FILE_SIZE, backupCount=BACKUP_COUNT, encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self._root_logger.addHandler(file_handler)
        except Exception:
            pass

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self._root_logger.addHandler(console_handler)

        self._initialized = True
        self._root_logger.info("=== Logging initialized ===", extra=self._extra(tags=['system', 'startup']))
        self._root_logger.info(f"Log directory: {log_dir}", extra=self._extra(tags=['system', 'startup']))

    def get_logger(self, name=None):
        if not self._initialized:
            self.init_logging()
        if name:
            return logging.getLogger(f'PharmacyERP.{name}')
        return self._root_logger

    def shutdown(self):
        if self._root_logger and self._initialized:
            self._root_logger.info("=== Application shutdown ===", extra=self._extra(tags=['system', 'shutdown']))
            logging.shutdown()

    def _extra(self, tags=None):
        return {'extra_fields': {'tags': tags or []}}


_manager = _LoggerManager()


def get_logger(name=None):
    return _manager.get_logger(name)


def get_log(name=None):
    """Backward-compatible alias for get_logger."""
    return _manager.get_logger(name)


def init_logging(level=logging.DEBUG):
    _manager.init_logging(level)


def shutdown():
    _manager.shutdown()


# Global screen context for crash diagnostics
_active_screen_context = ""


def get_active_screen() -> str:
    """Get the currently active screen name from any context."""
    return _active_screen_context


def set_active_screen(screen_name: str):
    """Set the current active screen for crash context tracking."""
    global _active_screen_context
    _active_screen_context = screen_name


class LoggerMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls = self.__class__
        self._log = get_logger(f'{cls.__module__}.{cls.__qualname__}')

    def log_debug(self, msg, **extra):
        self._log.debug(msg, extra={'extra_fields': extra})

    def log_info(self, msg, **extra):
        self._log.info(msg, extra={'extra_fields': extra})

    def log_warning(self, msg, **extra):
        self._log.warning(msg, extra={'extra_fields': extra})

    def log_error(self, msg, exc_info=True, **extra):
        self._log.error(msg, exc_info=exc_info, extra={'extra_fields': extra})

    def log_critical(self, msg, exc_info=True, **extra):
        self._log.critical(msg, exc_info=exc_info, extra={'extra_fields': extra})


# ============================================================
# Phase 13 — Log Intelligence + Crash Recovery + Diagnostics
# ============================================================

_LOG_CATEGORIES = {
    'api_error': ['api', 'error'],
    'auth_failure': ['auth', 'error'],
    'ui_error': ['ui', 'error'],
    'session_event': ['session'],
    'system_warning': ['system', 'warning'],
}


def log_category(category: str) -> list:
    """Return standardised tag list for a log category."""
    return _LOG_CATEGORIES.get(category, [category])


# --- Error Deduplication (noise reduction) ---

class _ErrorDeduplicator:
    """Suppress repeated identical error messages within a time window."""

    def __init__(self, window_seconds: int = 30):
        self._window = window_seconds
        self._cache: dict = {}
        self._lock = threading.Lock()

    def is_duplicate(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            last = self._cache.get(key)
            if last is not None and (now - last) < self._window:
                return True
            self._cache[key] = now
            return False

    def clean_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, t in self._cache.items()
                       if (now - t) > self._window * 2]
            for k in expired:
                del self._cache[k]


_deduplicator_instance: Optional[_ErrorDeduplicator] = None
_deduplicator_init_lock = threading.Lock()


def _get_deduplicator() -> _ErrorDeduplicator:
    global _deduplicator_instance
    if _deduplicator_instance is None:
        with _deduplicator_init_lock:
            if _deduplicator_instance is None:
                _deduplicator_instance = _ErrorDeduplicator()
    return _deduplicator_instance


def log_error_once(logger, msg: str, dedup_key: str = "",
                   tags: Optional[list] = None,
                   exc_info: bool = True, **extra):
    """Log an error only once within the deduplication window."""
    key = dedup_key or msg
    if not _get_deduplicator().is_duplicate(key):
        logger.error(msg, exc_info=exc_info,
                     extra={'extra_fields': {'tags': tags or ['error_once'], **extra}})


def log_warning_once(logger, msg: str, dedup_key: str = "",
                     tags: Optional[list] = None, **extra):
    """Log a warning only once within the deduplication window."""
    key = dedup_key or msg
    if not _get_deduplicator().is_duplicate(key):
        logger.warning(msg,
                       extra={'extra_fields': {'tags': tags or ['warning_once'], **extra}})


# --- Safe Execution Guard ---

T = TypeVar('T')


def safe_execute(fn: Callable[..., T],
                 fallback_return: Any = None,
                 log_context: str = "",
                 tags: Optional[list] = None) -> T:
    """Execute a function inside a safety boundary.

    Returns *fallback_return* on failure instead of raising.
    The exception is always logged with full traceback.
    """
    try:
        return fn()
    except Exception as e:
        _log = get_logger('safe_execute')
        _log.error(
            f"safe_execute failure [{log_context}]: {e}",
            exc_info=True,
            extra={'extra_fields': {
                'tags': tags or ['safe_execute'],
                'context': log_context,
            }}
        )
        return fallback_return


class SafeBoundary:
    """Context manager — any exception raised inside is caught and logged.

    Usage::

        with SafeBoundary(log_context="render_table"):
            self.table.populate(data)
    """

    def __init__(self, log_context: str = "",
                 tags: Optional[list] = None):
        self._context = log_context
        self._tags = tags or ['safe_boundary']
        self.exception: Optional[BaseException] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, Exception):
            _log = get_logger('safe_boundary')
            _log.error(
                f"Boundary caught [{self._context}]: {exc_val}",
                exc_info=True,
                extra={'extra_fields': {
                    'tags': self._tags,
                    'context': self._context,
                }}
            )
            self.exception = exc_val
            return True  # exception is suppressed
        return False


# --- Diagnostic Context (enriches error logs) ---

class DiagnosticContext:
    """Context manager that attaches diagnostic metadata to subsequent logs.

    Use it to correlate a set of operations::

        with DiagnosticContext(module="invoices", action="dispatch"):
            ...
    """

    _current: dict = {}
    _lock = threading.Lock()

    def __init__(self, **context):
        self._context = context

    def __enter__(self):
        with self._lock:
            DiagnosticContext._current.update(self._context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            for k in self._context:
                DiagnosticContext._current.pop(k, None)

    @classmethod
    def get_snapshot(cls) -> dict:
        with cls._lock:
            return dict(cls._current)


# --- Health Snapshot ---

def capture_health_snapshot() -> dict:
    """Return lightweight system-state dict for diagnostic logging."""
    snapshot: dict = {
        'ts': datetime.now().strftime(DATE_FORMAT),
        'screen': get_active_screen(),
    }
    try:
        import psutil
        proc = psutil.Process()
        snapshot['mem_mb'] = round(proc.memory_info().rss / 1_048_576, 1)
    except Exception:
        snapshot['mem_mb'] = '?'
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            snapshot['theme'] = app.property('currentTheme') or 'unknown'
            snapshot['auth'] = 'yes' if app.property('authenticated') else 'no'
    except Exception:
        pass
    return snapshot


# --- Correlation ID (trace continuity) ---

_corr_id_counter: int = 0
_corr_id_lock = threading.Lock()


def generate_correlation_id(prefix: str = "op") -> str:
    """Return monotonically increasing correlation id for trace continuity."""
    global _corr_id_counter
    with _corr_id_lock:
        _corr_id_counter += 1
        return f"{prefix}-{_corr_id_counter}"
