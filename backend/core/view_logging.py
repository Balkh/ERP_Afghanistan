"""
Lightweight view logging for critical business operations.
Adds structured request/response logging without performance overhead.
Usage:
    from core.view_logging import log_business_event
    log_business_event(request, 'journal_entry.posted', {'entry_id': entry.id})
"""

import logging
import time
from functools import wraps

logger = logging.getLogger('erp.views')

BUSINESS_EVENTS = {
    'journal_entry.created': 'Journal Entry created',
    'journal_entry.posted': 'Journal Entry posted',
    'journal_entry.unposted': 'Journal Entry unposted',
    'journal_entry.reversed': 'Journal Entry reversed',
    'invoice.sales.created': 'Sales Invoice created',
    'invoice.sales.confirmed': 'Sales Invoice confirmed',
    'invoice.sales.dispatched': 'Sales Invoice dispatched',
    'invoice.sales.cancelled': 'Sales Invoice cancelled',
    'invoice.purchase.created': 'Purchase Invoice created',
    'invoice.purchase.received': 'Purchase Invoice received',
    'invoice.purchase.confirmed': 'Purchase Invoice confirmed',
    'invoice.purchase.cancelled': 'Purchase Invoice cancelled',
    'payment.received': 'Customer payment received',
    'payment.made': 'Supplier payment made',
    'payment.transferred': 'Funds transferred',
    'stock.movement': 'Stock movement recorded',
    'stock.allocated': 'Stock allocated',
    'expense.created': 'Expense recorded',
    'account.created': 'Account created',
}


def log_business_event(request, event_type: str, metadata: dict = None):
    """Log a business event with structured context."""
    extra = {
        'event_type': event_type,
        'event_name': BUSINESS_EVENTS.get(event_type, event_type),
        'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
        'request_id': getattr(request, 'request_id', None),
        'path': request.path if hasattr(request, 'path') else None,
        'method': request.method if hasattr(request, 'method') else None,
    }
    if metadata:
        extra['metadata'] = metadata
    logger.info(f"{BUSINESS_EVENTS.get(event_type, event_type)}", extra=extra)


def log_view_execution(view_func):
    """Decorator that logs view execution time and basic info."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start = time.monotonic()
        try:
            response = view_func(request, *args, **kwargs)
            elapsed = (time.monotonic() - start) * 1000
            if elapsed > 500:
                logger.warning(
                    f"Slow view: {request.method} {request.path} took {elapsed:.0f}ms",
                    extra={'path': request.path, 'method': request.method, 'duration_ms': elapsed}
                )
            return response
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                f"View error: {request.method} {request.path} failed after {elapsed:.0f}ms: {e}",
                extra={'path': request.path, 'method': request.method, 'error': str(e)}
            )
            raise
    return wrapper
