"""
Observability middleware for Pharmacy ERP.
Provides request tracking, API logging, performance monitoring, and error capture.
Enhanced with Bad Request Intelligence and Slow Request Detection.
"""
import logging
import time
import uuid
import json
from typing import Optional

from django.utils.deprecation import MiddlewareMixin

from core.logging.logger import Logger
from core.operations.api_observability import (
    process_bad_request,
    process_slow_request,
    get_metrics
)

PERFORMANCE_THRESHOLD_MS = 500


def _get_user_info(request):
    """Safely extract user info from request."""
    if hasattr(request, 'user'):
        try:
            if request.user.is_authenticated:
                return request.user.username
        except (AttributeError, Exception):
            pass
    return 'anonymous'


class ObservabilityMiddleware(MiddlewareMixin):
    """
    Middleware for API observability.
    Tracks request/response lifecycle, execution time, and errors.
    """

    def process_request(self, request):
        """Inject request ID and capture start time."""
        request.request_id = str(uuid.uuid4())
        request._start_time = time.time()

        # Skip non-API paths
        if not request.path.startswith('/api/'):
            return None

        logger = Logger.api()
        logger.info(
            f"{request.method} {request.path}",
            extra={
                'request_id': request.request_id,
                'extra_fields': {
                    'method': request.method,
                    'path': request.path,
                    'user': _get_user_info(request),
                }
            }
        )

        return None

    def process_response(self, request, response):
        """Log response and track performance."""
        if not hasattr(request, '_start_time'):
            return response

        duration_ms = (time.time() - request._start_time) * 1000
        request_id = getattr(request, 'request_id', '')

        # Add request ID to response headers
        if request_id:
            response['X-Request-ID'] = request_id

        # Skip non-API paths
        if not request.path.startswith('/api/'):
            return response

        # Extract response data for bad request detection
        response_data = None
        if response.status_code >= 400:
            try:
                if hasattr(response, 'data'):
                    response_data = response.data
                elif hasattr(response, 'content'):
                    response_data = json.loads(response.content) if response.content else {}
            except (json.JSONDecodeError, AttributeError):
                pass

        # Process bad request (400, 401, 403, 422)
        if response.status_code in [400, 401, 403, 422]:
            process_bad_request(request, response, response_data)

        # Process slow request
        if duration_ms > PERFORMANCE_THRESHOLD_MS:
            process_slow_request(request, duration_ms)

        logger = Logger.api()
        log_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'user': _get_user_info(request),
        }

        if duration_ms > PERFORMANCE_THRESHOLD_MS:
            Logger.performance().warning(
                f"Slow request: {request.method} {request.path} ({duration_ms:.0f}ms)",
                extra={
                    'request_id': request_id,
                    'extra_fields': {**log_data, 'threshold_exceeded': True, 'threshold_ms': PERFORMANCE_THRESHOLD_MS}
                }
            )

        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"{request.method} {request.path} -> {response.status_code} ({duration_ms:.0f}ms)",
            extra={
                'request_id': request_id,
                'extra_fields': {**log_data, 'threshold_exceeded': duration_ms > PERFORMANCE_THRESHOLD_MS}
            }
        )

        return response

    def process_exception(self, request, exception):
        """Capture and log unhandled exceptions."""
        duration_ms = 0
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000

        request_id = getattr(request, 'request_id', '')

        Logger.error().error(
            f"Exception in {request.method} {request.path}: {str(exception)}",
            extra={
                'request_id': request_id,
                'extra_fields': {
                    'method': request.method,
                    'path': request.path,
                    'user': _get_user_info(request),
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'duration_ms': round(duration_ms, 2),
                }
            },
            exc_info=True,
        )

        return None
