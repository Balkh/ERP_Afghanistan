import sys
import os
import re
import time
import threading
import logging
from collections import defaultdict, deque
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
        record_error(exc_type=type(e).__name__, module=log_context, category='ui')
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
            record_error(exc_type=exc_type.__name__, module=self._context, category='ui')
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


# ============================================================
# Phase 14 — Error Aggregation + Pattern Detection + Telemetry
# ============================================================

_MAX_ERROR_RECORDS = 500
_MAX_AUTH_RECORDS = 100
_MAX_API_RECORDS = 200
_MAX_UI_RECORDS = 100
_MAX_API_TIMES = 200
_MAX_SCREEN_TIMES = 100

_BURST_AUTH_WINDOW = 60
_BURST_API_WINDOW = 60
_BURST_UI_WINDOW = 60
_BURST_AUTH_THRESHOLD = 5
_BURST_API_THRESHOLD = 10
_BURST_UI_THRESHOLD = 3


class _ErrorAggregator:
    """Lightweight, bounded, in-memory error aggregation for operational intelligence."""

    def __init__(self):
        self._lock = threading.Lock()
        self._errors = deque(maxlen=_MAX_ERROR_RECORDS)
        self._type_counts: dict = defaultdict(int)
        self._module_counts: dict = defaultdict(int)
        self._endpoint_counts: dict = defaultdict(int)
        self._auth_failures = deque(maxlen=_MAX_AUTH_RECORDS)
        self._api_failures = deque(maxlen=_MAX_API_RECORDS)
        self._ui_errors = deque(maxlen=_MAX_UI_RECORDS)

    def record_error(self, exc_type='', module='', endpoint='', category=''):
        with self._lock:
            now = time.time()
            self._errors.append({
                'ts': now, 'type': exc_type, 'module': module,
                'endpoint': endpoint, 'category': category,
            })
            if exc_type:
                self._type_counts[exc_type] += 1
            if module:
                self._module_counts[module] += 1
            if endpoint:
                self._endpoint_counts[endpoint] += 1
            if category == 'auth':
                self._auth_failures.append(now)
            elif category == 'api':
                self._api_failures.append(now)
            elif category == 'ui':
                self._ui_errors.append(now)

    def detect_bursts(self) -> dict:
        with self._lock:
            now = time.time()
            result: dict = {}
            auth_n = sum(1 for t in self._auth_failures if t > now - _BURST_AUTH_WINDOW)
            if auth_n >= _BURST_AUTH_THRESHOLD:
                result['auth_failure_burst'] = auth_n
            api_n = sum(1 for t in self._api_failures if t > now - _BURST_API_WINDOW)
            if api_n >= _BURST_API_THRESHOLD:
                result['api_failure_burst'] = api_n
            ui_n = sum(1 for t in self._ui_errors if t > now - _BURST_UI_WINDOW)
            if ui_n >= _BURST_UI_THRESHOLD:
                result['ui_error_burst'] = ui_n
            return result

    def generate_insight_report(self) -> dict:
        with self._lock:
            now = time.time()
            cutoff = now - 300  # 5-minute recency window

            top_errors = sorted(self._type_counts.items(), key=lambda x: -x[1])[:5]
            top_module = max(self._module_counts.items(), key=lambda x: x[1]) if self._module_counts else ('', 0)
            top_endpoint = max(self._endpoint_counts.items(), key=lambda x: x[1]) if self._endpoint_counts else ('', 0)

            recent_auth = sum(1 for t in self._auth_failures if t > cutoff)
            total_auth = len(self._auth_failures) or 1
            auth_ratio = round(recent_auth / total_auth, 2)

            recent_ui = sum(1 for t in self._ui_errors if t > cutoff)

            score = 100
            if recent_auth:
                score -= min(recent_auth * 5, 30)
            if recent_ui:
                score -= min(recent_ui * 10, 30)
            recent_total = sum(1 for e in self._errors if e['ts'] > cutoff)
            if recent_total > 10:
                score -= min((recent_total - 10) * 2, 20)
            score = max(0, min(100, score))

            return {
                'top_recurring_errors': top_errors,
                'most_failing_module': {'module': top_module[0], 'count': top_module[1]},
                'most_failing_endpoint': {'endpoint': top_endpoint[0], 'count': top_endpoint[1]},
                'auth_failure_ratio': auth_ratio,
                'ui_crash_count': recent_ui,
                'stability_score': score,
                'total_tracked_errors': len(self._errors),
            }


_aggregator_instance: Optional[_ErrorAggregator] = None
_aggregator_init_lock = threading.Lock()


def _get_aggregator() -> _ErrorAggregator:
    global _aggregator_instance
    if _aggregator_instance is None:
        with _aggregator_init_lock:
            if _aggregator_instance is None:
                _aggregator_instance = _ErrorAggregator()
    return _aggregator_instance


def record_error(exc_type='', module='', endpoint='', category=''):
    """Record an error in the aggregation store (never crashes)."""
    try:
        _get_aggregator().record_error(exc_type, module, endpoint, category)
    except Exception:
        pass


def detect_error_bursts() -> dict:
    """Detect active error bursts (auth, API, UI). Returns dict of burst types."""
    try:
        return _get_aggregator().detect_bursts()
    except Exception:
        return {}


def generate_operational_insight_report() -> dict:
    """Lightweight operational insight report from in-memory aggregated data."""
    try:
        return _get_aggregator().generate_insight_report()
    except Exception:
        return {'error': 'report generation failed', 'stability_score': 0}


# --- Performance Telemetry (bounded, lightweight) ---

_SLOW_API_THRESHOLD_MS = 5000
_SLOW_UI_THRESHOLD_MS = 3000


class _PerformanceTelemetry:
    """Bounded in-memory performance tracking for API and UI operations."""

    def __init__(self):
        self._lock = threading.Lock()
        self._api_times = deque(maxlen=_MAX_API_TIMES)
        self._screen_loads = deque(maxlen=_MAX_SCREEN_TIMES)

    def _get_current_time(self):
        return time.time()

    def record_api_time(self, endpoint: str, duration_ms: float):
        with self._lock:
            self._api_times.append((endpoint, duration_ms, self._get_current_time()))
            if duration_ms > _SLOW_API_THRESHOLD_MS:
                log_warning_once(
                    get_logger('perf'),
                    f"Slow API: {endpoint} took {duration_ms:.0f}ms",
                    dedup_key=f"slow_api_{endpoint}",
                    tags=['perf', 'slow_api'],
                )

    def record_screen_load(self, screen: str, duration_ms: float):
        with self._lock:
            self._screen_loads.append((screen, duration_ms, self._get_current_time()))
            if duration_ms > _SLOW_UI_THRESHOLD_MS:
                log_warning_once(
                    get_logger('perf'),
                    f"Slow screen: {screen} loaded in {duration_ms:.0f}ms",
                    dedup_key=f"slow_ui_{screen}",
                    tags=['perf', 'slow_ui'],
                )

    def get_slow_operations(self, min_threshold_ms: float = 3000) -> dict:
        with self._lock:
            return {
                'slow_api': [(e, d) for e, d, _ in self._api_times if d > min_threshold_ms][-10:],
                'slow_ui': [(s, d) for s, d, _ in self._screen_loads if d > min_threshold_ms][-10:],
            }


_perf_instance: Optional[_PerformanceTelemetry] = None
_perf_init_lock = threading.Lock()


def _get_perf_telemetry() -> _PerformanceTelemetry:
    global _perf_instance
    if _perf_instance is None:
        with _perf_init_lock:
            if _perf_instance is None:
                _perf_instance = _PerformanceTelemetry()
    return _perf_instance


def record_api_time(endpoint: str, duration_ms: float):
    """Record an API response time (never crashes)."""
    try:
        _get_perf_telemetry().record_api_time(endpoint, duration_ms)
    except Exception:
        pass


def record_screen_load(screen: str, duration_ms: float):
    """Record a UI screen load time (never crashes)."""
    try:
        _get_perf_telemetry().record_screen_load(screen, duration_ms)
    except Exception:
        pass


# ============================================================
# Phase 9 — Event Store (bounded, in-memory)
# ============================================================

MAX_EVENTS = 10000


class Event:
    """Lightweight structured event with sanitized metadata."""
    __slots__ = ['timestamp', 'epoch', 'event_type', 'module', 'action', 'metadata', 'correlation_id']

    def __init__(self, event_type: str, module: str, action: str,
                 metadata: dict = None, correlation_id: str = None):
        self.timestamp = datetime.now().strftime(DATE_FORMAT)
        self.epoch = time.time()
        self.event_type = event_type
        self.module = module
        self.action = action
        self.metadata = sanitize_dict(metadata) if metadata else {}
        self.correlation_id = correlation_id


class EventStore:
    """Bounded in-memory event store. Never blocks, never grows unbounded."""

    def __init__(self, max_events: int = MAX_EVENTS):
        self._max = max_events
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def append(self, event_type: str, module: str, action: str,
               metadata: dict = None, correlation_id: str = None) -> Event:
        event = Event(event_type, module, action, metadata, correlation_id)
        with self._lock:
            self._events.append(event)
        return event

    def query(self, event_type: str = None, module: str = None,
              action: str = None, since_seconds: float = None,
              limit: int = 100) -> list:
        with self._lock:
            events = list(self._events)
        if since_seconds:
            cutoff = time.time() - since_seconds
            events = [e for e in events if e.epoch > cutoff]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if module:
            events = [e for e in events if e.module == module]
        if action:
            events = [e for e in events if e.action == action]
        return events[-limit:]

    def replay(self, correlation_id: str) -> list:
        """Reconstruct all events for a given correlation ID."""
        if not correlation_id:
            return []
        with self._lock:
            return [e for e in self._events if e.correlation_id == correlation_id]

    def get_stats(self) -> dict:
        with self._lock:
            by_type: dict = defaultdict(int)
            by_module: dict = defaultdict(int)
            for e in self._events:
                by_type[e.event_type] += 1
                by_module[e.module] += 1
            return {
                'total_events': len(self._events),
                'by_type': dict(by_type),
                'by_module': dict(by_module),
            }


_event_store: Optional[EventStore] = None
_event_store_lock = threading.Lock()


def _get_event_store() -> EventStore:
    global _event_store
    if _event_store is None:
        with _event_store_lock:
            if _event_store is None:
                _event_store = EventStore()
    return _event_store


def emit_event(event_type: str, module: str, action: str,
               metadata: dict = None, correlation_id: str = None):
    """Emit a structured event to the store (never crashes, never blocks)."""
    try:
        _get_event_store().append(event_type, module, action, metadata, correlation_id)
    except Exception:
        pass


# ============================================================
# Phase 10 — Correlation Engine (lightweight pattern detection)
# ============================================================

_ANOMALY_WINDOW = 60  # seconds
_ANOMALY_THRESHOLDS = {
    'auth_failure': 5,
    'api_error': 10,
    'ui_error': 3,
}


class CorrelationEngine:
    """Lightweight engine for event linking, trace reconstruction, and anomaly detection."""

    def get_trace(self, correlation_id: str) -> list:
        """Reconstruct a full trace for a given correlation ID."""
        if not correlation_id:
            return []
        try:
            events = _get_event_store().replay(correlation_id)
            return sorted(events, key=lambda e: e.epoch)
        except Exception:
            return []

    def detect_anomalies(self) -> list:
        """Detect anomalies based on event frequency within a time window."""
        try:
            _now = time.time()
            events = _get_event_store().query(since_seconds=_ANOMALY_WINDOW, limit=MAX_EVENTS)
            type_counts: dict = defaultdict(int)
            for e in events:
                type_counts[e.event_type] += 1

            anomalies = []
            # Auth failure burst
            auth_count = type_counts.get('auth_event', 0)
            if auth_count >= _ANOMALY_THRESHOLDS['auth_failure']:
                anomalies.append({
                    'type': 'auth_failure_burst',
                    'count': auth_count,
                    'threshold': _ANOMALY_THRESHOLDS['auth_failure'],
                    'window_seconds': _ANOMALY_WINDOW,
                })
            # API error burst
            api_error_count = type_counts.get('error_event', 0)
            if api_error_count >= _ANOMALY_THRESHOLDS['api_error']:
                anomalies.append({
                    'type': 'api_error_burst',
                    'count': api_error_count,
                    'threshold': _ANOMALY_THRESHOLDS['api_error'],
                    'window_seconds': _ANOMALY_WINDOW,
                })
            # UI error burst
            ui_error_count = type_counts.get('ui_error', 0)
            if ui_error_count >= _ANOMALY_THRESHOLDS['ui_error']:
                anomalies.append({
                    'type': 'ui_error_burst',
                    'count': ui_error_count,
                    'threshold': _ANOMALY_THRESHOLDS['ui_error'],
                    'window_seconds': _ANOMALY_WINDOW,
                })
            return anomalies
        except Exception:
            return []

    def get_event_summary(self, limit: int = 50) -> dict:
        """Get a summary of recent events with distribution stats."""
        try:
            store = _get_event_store()
            events = store.query(limit=limit)
            stats = store.get_stats()
            return {
                'recent_count': len(events),
                'distribution': stats.get('by_type', {}),
                'top_modules': dict(sorted(
                    stats.get('by_module', {}).items(),
                    key=lambda x: -x[1]
                )[:5]),
            }
        except Exception:
            return {'recent_count': 0, 'distribution': {}, 'top_modules': {}}


_correlation_engine: Optional[CorrelationEngine] = None
_corr_engine_lock = threading.Lock()


def _get_correlation_engine() -> CorrelationEngine:
    global _correlation_engine
    if _correlation_engine is None:
        with _corr_engine_lock:
            if _correlation_engine is None:
                _correlation_engine = CorrelationEngine()
    return _correlation_engine


def detect_anomalies() -> list:
    """Detect system anomalies (never crashes)."""
    try:
        return _get_correlation_engine().detect_anomalies()
    except Exception:
        return []


def get_trace(correlation_id: str) -> list:
    """Get trace for a correlation ID (never crashes)."""
    try:
        return _get_correlation_engine().get_trace(correlation_id)
    except Exception:
        return []


def get_event_summary(limit: int = 50) -> dict:
    """Get event summary (never crashes)."""
    try:
        return _get_correlation_engine().get_event_summary(limit)
    except Exception:
        return {}


def generate_operational_dashboard_data() -> dict:
    """Unified dashboard data provider combining all telemetry sources."""
    try:
        insight = generate_operational_insight_report()
        anomalies = detect_anomalies()
        slow_ops = _get_perf_telemetry().get_slow_operations()
        event_stats = _get_event_store().get_stats()
        recent_events = _get_event_store().query(limit=50)

        recent_data = [
            {
                'timestamp': e.timestamp,
                'type': e.event_type,
                'module': e.module,
                'action': e.action,
                'correlation_id': e.correlation_id or '',
            }
            for e in recent_events
        ]

        return {
            'system_health': {
                'stability_score': insight.get('stability_score', 100),
                'crash_count': insight.get('ui_crash_count', 0),
                'error_rate': round(insight.get('auth_failure_ratio', 0), 3),
                'total_events': event_stats.get('total_events', 0),
                'anomalies': anomalies,
                'total_errors': insight.get('total_tracked_errors', 0),
            },
            'event_summary': {
                'recent_events': recent_data,
                'distribution': event_stats.get('by_type', {}),
            },
            'error_overview': {
                'top_errors': insight.get('top_recurring_errors', []),
                'most_failing_module': insight.get('most_failing_module', {}),
                'most_failing_endpoint': insight.get('most_failing_endpoint', {}),
                'total_tracked_errors': insight.get('total_tracked_errors', 0),
            },
            'performance_overview': {
                'avg_api_latency': _get_avg_api_latency(),
                'slow_operations': slow_ops.get('slow_api', []),
                'slow_ui_operations': slow_ops.get('slow_ui', []),
            },
        }
    except Exception:
        return {
            'system_health': {'stability_score': 0, 'anomalies': [], 'total_events': 0},
            'event_summary': {'recent_events': [], 'distribution': {}},
            'error_overview': {'top_errors': [], 'total_tracked_errors': 0},
            'performance_overview': {'avg_api_latency': 0, 'slow_operations': []},
        }


def _get_avg_api_latency() -> float:
    """Calculate average API latency from telemetry data."""
    try:
        perf = _get_perf_telemetry()
        with perf._lock:
            if not perf._api_times:
                return 0.0
            total = sum(d for _, d, _ in perf._api_times)
            return round(total / len(perf._api_times), 1)
    except Exception:
        return 0.0


# ============================================================
# Phase 13 — Decision Intelligence Engine (Frontend-side)
# Lightweight deterministic rules that run on the client side
# using in-memory event data. No AI/ML.
# ============================================================

_DECISION_RULES = {
    'ui_crash_cluster': {
        'category': 'ui',
        'risk_level': 'high',
        'threshold': 3,
        'description': 'Multiple UI errors detected in short window',
        'actions': ['Check browser console for errors', 'Review recent frontend deployments', 'Test affected workflows'],
    },
    'auth_failure_burst': {
        'category': 'security',
        'risk_level': 'critical',
        'threshold': 5,
        'description': 'Multiple authentication failures detected',
        'actions': ['Review failed auth logs', 'Enable account lockout', 'Consider MFA enforcement'],
    },
    'api_error_burst': {
        'category': 'performance',
        'risk_level': 'high',
        'threshold': 10,
        'description': 'High rate of API errors detected',
        'actions': ['Check API logs', 'Review recent backend changes', 'Check network connectivity'],
    },
    'slow_api_cluster': {
        'category': 'performance',
        'risk_level': 'medium',
        'threshold': 3,
        'description': 'Multiple slow API calls detected',
        'actions': ['Profile slow endpoints', 'Check database queries', 'Add caching if appropriate'],
    },
    'high_error_rate': {
        'category': 'performance',
        'risk_level': 'high',
        'description': 'Error rate above 5%',
        'actions': ['Check application logs', 'Review recent deployments', 'Rollback if regression'],
    },
    'system_event_burst': {
        'category': 'system',
        'risk_level': 'high',
        'threshold': 5,
        'description': 'Unusual burst of system events',
        'actions': ['Check system resources', 'Review system logs', 'Verify background services'],
    },
    'disk_warning': {
        'category': 'system',
        'risk_level': 'critical',
        'description': 'Disk space warning from telemetry',
        'actions': ['Free disk space', 'Archive old files', 'Expand storage'],
    },
}


def evaluate_decisions() -> dict:
    """
    Evaluate all decision rules against current in-memory telemetry.
    Returns structured decisions with risk levels and recommended actions.
    Never crashes, never blocks.
    """
    try:
        stats = _get_event_store().get_stats()
        anomalies = detect_anomalies()
        slow_ops = _get_perf_telemetry().get_slow_operations()
        _insight = generate_operational_insight_report()

        by_type = stats.get('by_type', {})
        _by_module = stats.get('by_module', {})
        total_events = stats.get('total_events', 0)

        decisions = []
        active_categories = set()

        # Rule: UI crash cluster
        ui_errors = by_type.get('ui_error', 0)
        if ui_errors >= _DECISION_RULES['ui_crash_cluster']['threshold']:
            rule = _DECISION_RULES['ui_crash_cluster']
            decisions.append({
                'decision_id': 'UI-CRASH-001',
                'category': rule['category'],
                'risk_level': rule['risk_level'],
                'decision': rule['description'],
                'confidence': min(ui_errors * 0.15, 0.95),
                'description': f'{ui_errors} UI errors in the event window.',
                'recommended_actions': rule['actions'],
                'triggered_by': ['ui_error'],
            })
            active_categories.add('ui')

        # Rule: Auth failure burst
        auth_events = by_type.get('auth_event', 0)
        if auth_events >= _DECISION_RULES['auth_failure_burst']['threshold']:
            rule = _DECISION_RULES['auth_failure_burst']
            decisions.append({
                'decision_id': 'SEC-AUTH-001',
                'category': rule['category'],
                'risk_level': rule['risk_level'],
                'decision': rule['description'],
                'confidence': min(auth_events * 0.12, 0.92),
                'description': f'{auth_events} authentication events detected.',
                'recommended_actions': rule['actions'],
                'triggered_by': ['auth_event'],
            })
            active_categories.add('security')

        # Rule: API error burst
        api_errors = by_type.get('error_event', 0)
        if api_errors >= _DECISION_RULES['api_error_burst']['threshold']:
            rule = _DECISION_RULES['api_error_burst']
            decisions.append({
                'decision_id': 'PERF-ERR-001',
                'category': rule['category'],
                'risk_level': rule['risk_level'],
                'decision': rule['description'],
                'confidence': min(api_errors * 0.08, 0.90),
                'description': f'{api_errors} API errors in the event window.',
                'recommended_actions': rule['actions'],
                'triggered_by': ['error_event'],
            })
            active_categories.add('performance')

        # Rule: Slow API cluster
        slow_api = slow_ops.get('slow_api', [])
        if len(slow_api) >= _DECISION_RULES['slow_api_cluster']['threshold']:
            rule = _DECISION_RULES['slow_api_cluster']
            decisions.append({
                'decision_id': 'PERF-SLOW-001',
                'category': rule['category'],
                'risk_level': rule['risk_level'],
                'decision': rule['description'],
                'confidence': min(len(slow_api) * 0.1, 0.80),
                'description': f'{len(slow_api)} slow API calls detected (>3s).',
                'recommended_actions': rule['actions'],
                'triggered_by': ['api_response'],
            })
            active_categories.add('performance')

        # Rule: High error rate
        if total_events > 20:
            error_count = by_type.get('error_event', 0) + by_type.get('ui_error', 0)
            error_rate = error_count / max(total_events, 1)
            if error_rate > 0.05:
                rule = _DECISION_RULES['high_error_rate']
                decisions.append({
                    'decision_id': 'PERF-ERR-RATE-001',
                    'category': rule['category'],
                    'risk_level': rule['risk_level'],
                    'decision': rule['description'],
                    'confidence': round(min(error_rate * 10, 0.95), 2),
                    'description': f'Error rate at {error_rate:.1%} ({error_count}/{total_events} events).',
                    'recommended_actions': rule['actions'],
                    'triggered_by': ['error_event', 'ui_error'],
                })
                active_categories.add('performance')

        # Rule: Anomaly-driven decisions
        for anomaly in anomalies:
            anomaly_type = anomaly.get('type', '')
            if 'auth' in anomaly_type and 'security' not in active_categories:
                decisions.append({
                    'decision_id': 'SEC-ANOMALY-001',
                    'category': 'security',
                    'risk_level': 'high',
                    'decision': 'Anomalous authentication pattern detected',
                    'confidence': 0.80,
                    'description': f"{anomaly.get('count', '?')}x {anomaly_type} (threshold: {anomaly.get('threshold', '?')}).",
                    'recommended_actions': ['Review auth logs', 'Check for credential stuffing', 'Enable MFA if not active'],
                    'triggered_by': ['anomaly'],
                })
                active_categories.add('security')
                break

        # Rule: System event burst
        sys_events = by_type.get('system_event', 0)
        if sys_events >= _DECISION_RULES['system_event_burst']['threshold']:
            rule = _DECISION_RULES['system_event_burst']
            decisions.append({
                'decision_id': 'SYS-BURST-001',
                'category': rule['category'],
                'risk_level': rule['risk_level'],
                'decision': rule['description'],
                'confidence': min(sys_events * 0.08, 0.80),
                'description': f'{sys_events} system events in the event window.',
                'recommended_actions': rule['actions'],
                'triggered_by': ['system_event'],
            })
            active_categories.add('system')

        # Determine overall risk
        risk_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        overall_risk = 'low'
        for d in decisions:
            if risk_order.get(d['risk_level'], 0) > risk_order.get(overall_risk, 0):
                overall_risk = d['risk_level']

        # Sort by risk descending
        risk_sort = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        decisions.sort(key=lambda d: risk_sort.get(d['risk_level'], 99))

        # Build category breakdown
        by_decision_category = {}
        for d in decisions:
            cat = d['category']
            by_decision_category[cat] = by_decision_category.get(cat, 0) + 1

        return {
            'active_decisions': decisions,
            'summary': {
                'total_active': len(decisions),
                'overall_risk_level': overall_risk,
                'by_category': by_decision_category,
            },
            'rule_count': len(_DECISION_RULES),
            'evaluated_at': _timestamp_now(),
        }

    except Exception:
        return {
            'active_decisions': [],
            'summary': {
                'total_active': 0,
                'overall_risk_level': 'unknown',
                'by_category': {},
            },
            'rule_count': len(_DECISION_RULES),
            'evaluated_at': _timestamp_now(),
            'error': 'Decision evaluation failed',
        }


def _timestamp_now() -> str:
    return datetime.now().strftime(DATE_FORMAT)
