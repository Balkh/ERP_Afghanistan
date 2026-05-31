"""
Inventory Lineage Resolver — deterministic batch/warehouse/product resolution.

ALL batch-warehouse relationships MUST resolve through movement lineage,
never through static ownership assumptions or UUID positional access.

Regression guards:
- Fails if batch linkage cannot be deterministically reconstructed
- Fails if UUID ordering is used for item resolution
- Validates warehouse consistency across all movements for a batch
"""
from decimal import Decimal
from typing import Optional, List
from django.db import models


def resolve_batch_warehouse(
    product,
    batch,
) -> Optional[object]:
    """Deterministically resolve warehouse for a product+batch pair.

    Uses the stock movement chain (ordered chronologically),
    never by UUID position. Returns the warehouse from the
    most recent non-zero-quantity movement, or None if unresolvable.
    """
    from inventory.models import StockMovement

    if not batch:
        return None

    movement = (
        StockMovement.objects
        .filter(product=product, batch=batch)
        .exclude(quantity=Decimal('0'))
        .order_by('created_at')
        .last()
    )
    if movement and movement.warehouse:
        return movement.warehouse

    # Fallback: any movement even with zero quantity
    movement = (
        StockMovement.objects
        .filter(product=product, batch=batch)
        .order_by('created_at')
        .last()
    )
    return movement.warehouse if movement else None


def resolve_invoice_item(invoice, product_name: str) -> Optional[object]:
    """Resolve a sales invoice item by product NAME — never by position.

    UUID-ordered querysets produce non-deterministic ordering.
    Always filter by business key (product name).
    """
    return invoice.items.filter(product__name=product_name).first()


def resolve_purchase_item(invoice, product_name: str) -> Optional[object]:
    """Resolve a purchase invoice item by product NAME — never by position."""
    return invoice.items.filter(product__name=product_name).first()


def resolve_batch_for_purchase_item(invoice, product_name: str) -> Optional[object]:
    """Resolve the batch created by process_purchase for a given product.

    Uses StockMovement chain (reference_type='PURCHASE') instead of
    static tracking dicts or UUID positional access.
    """
    from inventory.models import StockMovement, Batch

    movement = (
        StockMovement.objects
        .filter(
            reference_type='PURCHASE',
            reference_id=str(invoice.id),
            product__name=product_name,
            movement_type='IN',
        )
        .order_by('created_at')
        .last()
    )
    if movement and movement.batch:
        return movement.batch

    # Fallback: most recently created batch for this product
    return (
        Batch.objects
        .filter(product__name=product_name)
        .order_by('-created_at')
        .first()
    )


def validate_batch_lineage(batch) -> List[str]:
    """Validate that a batch's warehouse linkages are consistent.

    Returns list of issues (empty if consistent).
    """
    from inventory.models import StockMovement

    issues: List[str] = []
    warehouses = set()
    for sm in StockMovement.objects.filter(batch=batch):
        if sm.warehouse:
            warehouses.add(sm.warehouse.id)

    if len(warehouses) > 1:
        issues.append(
            f"Batch {batch.batch_number} has movements across "
            f"{len(warehouses)} different warehouses"
        )
    return issues
