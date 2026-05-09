"""
API Observability Enhancement Module.
Bad Request Intelligence & Slow Request Detection System.
"""
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.conf import settings

from core.operations.alerts import AlertManager, AlertSeverity, AlertCategory


SLOW_THRESHOLD_WARNING_MS = 500
SLOW_THRESHOLD_CRITICAL_MS = 1500
REPORT_WARNING_MS = 2000
REPORT_CRITICAL_MS = 5000

BAD_REQUEST_THRESHOLD_REPEAT = 5
SLOW_REQUEST_THRESHOLD_REPEAT = 10


class RequestMetrics:
    """In-memory request metrics storage."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._bad_requests: List[dict] = []
        self._slow_requests: List[dict] = []
        self._endpoint_errors: Dict[str, int] = defaultdict(int)
        self._endpoint_latency: Dict[str, List[float]] = defaultdict(list)
        self._user_bad_requests: Dict[str, int] = defaultdict(int)
        self._ip_bad_requests: Dict[str, int] = defaultdict(int)
        self._max_records = 1000

    def add_bad_request(self, data: dict):
        """Record a bad request."""
        self._bad_requests.append({
            **data,
            'timestamp': timezone.now().isoformat()
        })
        if len(self._bad_requests) > self._max_records:
            self._bad_requests = self._bad_requests[-self._max_records:]

    def add_slow_request(self, data: dict):
        """Record a slow request."""
        self._slow_requests.append({
            **data,
            'timestamp': timezone.now().isoformat()
        })
        if len(self._slow_requests) > self._max_records:
            self._slow_requests = self._slow_requests[-self._max_records:]

    def increment_endpoint_error(self, endpoint: str):
        """Increment error count for endpoint."""
        self._endpoint_errors[endpoint] += 1

    def record_latency(self, endpoint: str, latency_ms: float):
        """Record latency for endpoint."""
        self._endpoint_latency[endpoint].append(latency_ms)
        if len(self._endpoint_latency[endpoint]) > 100:
            self._endpoint_latency[endpoint] = self._endpoint_latency[endpoint][-100:]

    def increment_user_bad_requests(self, user_id: str):
        """Increment bad request count for user."""
        self._user_bad_requests[user_id] += 1

    def increment_ip_bad_requests(self, ip: str):
        """Increment bad request count for IP."""
        self._ip_bad_requests[ip] += 1

    def get_bad_requests(self, hours: int = 24, limit: int = 100) -> List[dict]:
        """Get recent bad requests."""
        cutoff = timezone.now() - timedelta(hours=hours)
        return [
            r for r in self._bad_requests
            if datetime.fromisoformat(r['timestamp']) > cutoff
        ][:limit]

    def get_slow_requests(self, hours: int = 24, limit: int = 100) -> List[dict]:
        """Get recent slow requests."""
        cutoff = timezone.now() - timedelta(hours=hours)
        return [
            r for r in self._slow_requests
            if datetime.fromisoformat(r['timestamp']) > cutoff
        ][:limit]

    def get_top_bad_endpoints(self, hours: int = 24, limit: int = 10) -> List[dict]:
        """Get top endpoints with bad requests."""
        cutoff = timezone.now() - timedelta(hours=hours)
        endpoint_counts = defaultdict(int)
        for r in self._bad_requests:
            if datetime.fromisoformat(r['timestamp']) > cutoff:
                endpoint_counts[r['path']] += 1
        return [
            {'endpoint': ep, 'count': count}
            for ep, count in sorted(endpoint_counts.items(), key=lambda x: -x[1])[:limit]
        ]

    def get_top_slow_endpoints(self, hours: int = 24, limit: int = 10) -> List[dict]:
        """Get top slow endpoints."""
        cutoff = timezone.now() - timedelta(hours=hours)
        endpoint_avg = defaultdict(list)
        for r in self._slow_requests:
            if datetime.fromisoformat(r['timestamp']) > cutoff:
                endpoint_avg[r['path']].append(r['duration_ms'])
        return [
            {'endpoint': ep, 'avg_ms': sum(times)/len(times), 'count': len(times)}
            for ep, times in sorted(endpoint_avg.items(), key=lambda x: -sum(x[1])/len(x[1]))[:limit]
        ]

    def get_error_rates(self) -> List[dict]:
        """Get error rates per endpoint."""
        return [
            {'endpoint': ep, 'errors': count}
            for ep, count in sorted(self._endpoint_errors.items(), key=lambda x: -x[1])[:20]
        ]

    def get_user_bad_request_count(self, user_id: str, hours: int = 24) -> int:
        """Get bad request count for user in time window."""
        cutoff = timezone.now() - timedelta(hours=hours)
        count = 0
        for r in self._bad_requests:
            if r.get('user_id') == user_id and datetime.fromisoformat(r['timestamp']) > cutoff:
                count += 1
        return count


_metrics = RequestMetrics()


def get_metrics() -> RequestMetrics:
    """Get the global request metrics instance."""
    return _metrics


def _is_report_endpoint(path: str) -> bool:
    """Check if endpoint is a report endpoint."""
    report_patterns = ['/reports/', '/report/', '/balance-sheet', '/profit-loss', '/trial-balance', '/cash-flow', '/ar_aging', '/ap_aging']
    return any(pattern in path.lower() for pattern in report_patterns)


def _classify_bad_request(status_code: int, response_data: dict) -> str:
    """Classify the type of bad request."""
    if status_code == 400:
        if 'detail' in response_data:
            if 'authentication' in str(response_data.get('detail', '')).lower():
                return 'auth'
            return 'validation'
        if isinstance(response_data, dict):
            if any(k in response_data for k in ['errors', 'non_field_errors', 'field_errors']):
                return 'validation'
        return 'malformed'
    if status_code == 401:
        return 'auth'
    if status_code == 403:
        return 'permission'
    if status_code == 422:
        return 'validation'
    return 'business_rule'


def process_bad_request(
    request,
    response,
    response_data: dict = None
):
    """Process and log a bad request."""
    if response.status_code not in [400, 401, 403, 422]:
        return

    error_type = _classify_bad_request(response.status_code, response_data or {})

    user_id = 'anonymous'
    try:
        if hasattr(request, 'user') and request.user:
            if getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'id', None):
                user_id = str(request.user.id)
    except Exception:
        pass

    ip = _get_client_ip(request)

    severity_map = {
        'auth': 'high',
        'permission': 'medium',
        'validation': 'low',
        'malformed': 'medium',
        'business_rule': 'low'
    }
    severity = severity_map.get(error_type, 'low')

    bad_request_data = {
        'event': 'bad_request',
        'severity': severity,
        'path': request.path,
        'method': request.method,
        'status': response.status_code,
        'request_id': getattr(request, 'request_id', ''),
        'user_id': user_id,
        'ip': ip,
        'error_type': error_type,
        'errors': _sanitize_errors(response_data or {}),
    }

    _metrics.add_bad_request(bad_request_data)
    _metrics.increment_user_bad_requests(user_id)
    _metrics.increment_ip_bad_requests(ip)
    _metrics.increment_endpoint_error(request.path)

    repeated_count = _metrics.get_user_bad_request_count(user_id)
    if repeated_count >= BAD_REQUEST_THRESHOLD_REPEAT:
        AlertManager.create_alert(
            severity=AlertSeverity.WARNING,
            category=AlertCategory.API,
            title='Repeated Bad Requests',
            message=f'User {user_id} has {repeated_count} bad requests',
            details={'user_id': user_id, 'recent_count': repeated_count, 'endpoint': request.path}
        )

    _log_bad_request(bad_request_data)


def process_slow_request(
    request,
    duration_ms: float
):
    """Process and log a slow request."""
    is_report = _is_report_endpoint(request.path)

    if is_report:
        threshold_warning = REPORT_WARNING_MS
        threshold_critical = REPORT_CRITICAL_MS
    else:
        threshold_warning = SLOW_THRESHOLD_WARNING_MS
        threshold_critical = SLOW_THRESHOLD_CRITICAL_MS

    severity = 'warning' if duration_ms < threshold_critical else 'critical'

    user_id = 'anonymous'
    try:
        if hasattr(request, 'user') and request.user:
            if getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'id', None):
                user_id = str(request.user.id)
    except Exception:
        pass

    slow_request_data = {
        'event': 'slow_request',
        'severity': severity,
        'path': request.path,
        'method': request.method,
        'duration_ms': round(duration_ms, 2),
        'request_id': getattr(request, 'request_id', ''),
        'user_id': user_id,
        'is_report': is_report,
    }

    _metrics.add_slow_request(slow_request_data)
    _metrics.record_latency(request.path, duration_ms)

    if severity == 'critical':
        AlertManager.create_alert(
            severity=AlertSeverity.ERROR,
            category=AlertCategory.API,
            title='Critical Slow Request',
            message=f'{request.path} took {duration_ms:.0f}ms',
            details={'path': request.path, 'duration_ms': duration_ms, 'is_report': is_report}
        )

    _log_slow_request(slow_request_data)


def _get_client_ip(request) -> str:
    """Get client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _sanitize_errors(response_data: dict) -> dict:
    """Remove sensitive data from error response."""
    sensitive_keys = ['password', 'token', 'secret', 'key', 'authorization']
    sanitized = {}

    def sanitize_value(k, v):
        if isinstance(v, dict):
            return {kk: sanitize_value(kk, vv) for kk, vv in v.items() if kk.lower() not in sensitive_keys}
        if isinstance(v, list):
            return [sanitize_value(k, item) for item in v]
        return v

    for key, value in response_data.items():
        if key.lower() not in sensitive_keys:
            sanitized[key] = sanitize_value(key, value)

    return sanitized


def _log_bad_request(data: dict):
    """Log bad request via structured logging."""
    logger = logging.getLogger('erp.bad_requests')
    logger.warning(
        f"Bad Request: {data['method']} {data['path']} - {data['error_type']} (status: {data['status']})",
        extra={
            'request_id': data.get('request_id'),
            'extra_fields': data
        }
    )


def _log_slow_request(data: dict):
    """Log slow request via structured logging."""
    logger = logging.getLogger('erp.performance')
    log_level = logging.WARNING if data['severity'] == 'warning' else logging.ERROR
    logger.log(
        log_level,
        f"Slow Request: {data['method']} {data['path']} - {data['duration_ms']}ms",
        extra={
            'request_id': data.get('request_id'),
            'extra_fields': data
        }
    )


def get_observability_summary(hours: int = 24) -> dict:
    """Get comprehensive observability summary."""
    return {
        'bad_requests': {
            'recent': _metrics.get_bad_requests(hours),
            'top_endpoints': _metrics.get_top_bad_endpoints(hours),
            'total_count': len(_metrics.get_bad_requests(hours))
        },
        'slow_requests': {
            'recent': _metrics.get_slow_requests(hours),
            'top_endpoints': _metrics.get_top_slow_endpoints(hours),
            'total_count': len(_metrics.get_slow_requests(hours))
        },
        'error_rates': _metrics.get_error_rates(),
        'generated_at': timezone.now().isoformat()
    }