"""
Sales calculators.

Extracted from SalesAccountingService in Sprint 4.
Pure math — no DB writes, no transaction boundaries, no save calls.
"""
from decimal import Decimal
from typing import List

from sales.models import SalesInvoice


CENTS = Decimal('0.01')


def calculate_cogs_from_allocations(invoice: SalesInvoice, allocations: List) -> Decimal:
    """
    Calculate Cost of Goods Sold from stock allocations.

    Uses actual batch unit costs from FIFO/FEFO selection.
    This ensures COGS reflects true cost, not average or std cost.

    Pure function: depends only on invoice.items and the allocations list.
    Caller is responsible for providing a fully-loaded invoice and a
    list of allocation objects with `product_id`, `quantity`, and
    optional `unit_cost`.
    """
    total_cogs = Decimal('0.00')

    for item in invoice.items.all():
        item_quantity = item.quantity
        item_cost = Decimal('0.00')

        matching_allocations = [
            a for a in allocations
            if str(a.product_id) == str(item.product_id)
        ]

        if matching_allocations:
            total_allocated = sum(a.quantity for a in matching_allocations)
            for alloc in matching_allocations:
                if alloc.unit_cost is not None:
                    proportion = (
                        alloc.quantity / total_allocated
                        if total_allocated > 0
                        else 0
                    )
                    item_cost += (item_quantity * proportion) * alloc.unit_cost
        else:
            if item.batch and item.batch.purchase_price:
                item_cost = item_quantity * item.batch.purchase_price

        total_cogs += item_cost

    return total_cogs.quantize(CENTS)
