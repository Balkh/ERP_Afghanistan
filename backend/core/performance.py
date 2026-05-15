"""
Performance instrumentation middleware.
Adds execution timing to all requests and flags slow endpoints.
Production-safe — no performance overhead for non-logged paths.
"""
import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('erp.performance')

# Thresholds
SLOW_REQUEST_MS = 300  # Flag requests taking >300ms
CRITICAL_PATHS = [
    '/api/control-center/',
    '/api/accounting/accounts/trial_balance/',
    '/api/accounting/accounts/ledger/',
    '/api/accounting/accounts/account_summary/',
    '/api/accounting/accounts/ar_aging/',
    '/api/accounting/accounts/ap_aging/',
]


class RequestTimingMiddleware(MiddlewareMixin):
    """Middleware that logs request execution time for all API requests."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        request._view_start_time = time.monotonic()
        return None

    def process_response(self, request, response):
        if not hasattr(request, '_view_start_time'):
            return response

        elapsed_ms = (time.monotonic() - request._view_start_time) * 1000
        path = request.path

        # Always log slow requests
        if elapsed_ms > SLOW_REQUEST_MS or any(path.startswith(cp) for cp in CRITICAL_PATHS):
            logger.info(
                f"PERF: {request.method} {path} took {elapsed_ms:.0f}ms",
                extra={
                    'path': path,
                    'method': request.method,
                    'duration_ms': round(elapsed_ms, 1),
                    'status_code': response.status_code if hasattr(response, 'status_code') else None,
                    'slow': elapsed_ms > SLOW_REQUEST_MS,
                }
            )

        return response
