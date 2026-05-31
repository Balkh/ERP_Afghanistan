"""
UUID Ordering Safety — regression guard against positional access on UUID-ordered models.

UUID primary keys produce non-deterministic ordering. Any code that assumes
positional ordering (items[0], items.first(), etc.) on UUID-ordered querysets
will produce intermittent failures.

Rules enforced:
1. NEVER access UUID-ordered querysets by positional index
2. ALWAYS resolve by product identity, business key, or explicit ordering field
3. ALL invoice/purchase item resolution must use product-name-based lookup
"""
import logging
from typing import List, Any
from django.db import models

logger = logging.getLogger('erp.uuid_safety')

# Models known to use UUID PK with non-deterministic ordering
UUID_ORDERED_MODELS = {
    'SalesItem', 'PurchaseItem', 'JournalEntryLine',
    'StockMovement', 'ReturnItem', 'ReconciliationEntry',
}


def warn_positional_access(queryset, caller: str = ''):
    """Emit a warning when code accesses UUID-ordered querysets positionally.

    Call this in places that CANNOT be migrated to deterministic lookup
    to surface regression risk in logs.
    """
    model_name = queryset.model.__name__ if hasattr(queryset, 'model') else 'unknown'
    logger.warning(
        f"[UUID-SAFETY] Positional access on {model_name} from {caller}. "
        f"This is non-deterministic with UUID PKs."
    )


def resolve_by_product_name(queryset, product_name: str):
    """Resolve a single item from a UUID-ordered queryset by product name.

    Usage:
        item = resolve_by_product_name(invoice.items, 'Amoxicillin 500mg')
    """
    return queryset.filter(product__name=product_name).first()


def resolve_items_by_product_map(queryset) -> dict:
    """Build a {product_name: item} mapping from a UUID-ordered queryset.

    Usage:
        by_product = resolve_items_by_product_map(invoice.items)
        item = by_product['Amoxicillin 500mg']
    """
    return {item.product.name: item for item in queryset.all()}


def assert_not_positional(queryset, message: str = ''):
    """Assert that a queryset is not being accessed positionally on UUID models.

    This is a development-time guard. Use in test assertions.
    """
    model_name = queryset.model.__name__ if hasattr(queryset, 'model') else ''
    if model_name in UUID_ORDERED_MODELS:
        raise AssertionError(
            message or
            f"Positional access on {model_name} is non-deterministic "
            f"(UUID primary keys). Use resolve_by_product_name() instead."
        )
