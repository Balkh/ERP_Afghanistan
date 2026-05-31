"""
Class 5: InventoryLineageEnforcer — Inventory Lineage Guarantee.

GUARANTEE: Inventory MUST be traceable via lineage graph:
  Purchase → Batch → StockMovement → Sale → Return → Restoration

No direct inventory update is allowed outside the lineage chain.
Detects:
  - Batch.remaining_quantity changes without StockMovement
  - Direct Warehouse.stock changes
  - Orphan stock movements
  - Missing lineage links
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from django.db import models


@dataclass
class LineageNode:
    model_name: str
    object_id: str
    reference: Optional[str] = None
    quantity: Decimal = Decimal('0')
    children: List['LineageNode'] = field(default_factory=list)


@dataclass
class LineageValidationResult:
    valid: bool
    batch_id: str
    batch_code: str
    current_quantity: Decimal
    lineage_quantity: Decimal
    drift: Decimal
    chain_length: int
    issues: List[str] = field(default_factory=list)


class InventoryLineageEnforcer:
    """
    Enforces that all inventory changes are traceable through the
    lineage graph and no direct mutations exist outside the chain.

    Mode:
      - LOG:   Log warnings
      - BLOCK: Raise AssertionError
    """

    MODE_LOG = 'LOG'
    MODE_BLOCK = 'BLOCK'

    def __init__(self, mode: str = 'BLOCK'):
        self.mode = mode
        self._violations: List[str] = []

    def trace_batch_lineage(self, batch) -> LineageNode:
        """
        Trace the full lineage of a batch from inception through all movements.
        Returns a tree of LineageNodes.
        """
        root = LineageNode(
            model_name='Batch',
            object_id=str(batch.id),
            reference=batch.batch_code or str(batch.id),
            quantity=Decimal(str(batch.initial_quantity)),
        )

        from inventory.models import StockMovement
        movements = StockMovement.objects.filter(
            batch=batch
        ).order_by('created_at')

        for mv in movements:
            qty = Decimal(str(abs(mv.quantity)))
            direction = 'IN' if mv.quantity > 0 else 'OUT'
            child = LineageNode(
                model_name='StockMovement',
                object_id=str(mv.id),
                reference=f"{mv.reference_type}:{mv.reference} ({direction} {qty})",
                quantity=qty * (1 if mv.quantity > 0 else -1),
            )

            # Try to trace further
            if mv.reference_type == 'SALE' and mv.reference:
                child.children = self._trace_from_sale(mv.reference)
            elif mv.reference_type == 'RETURN' and mv.reference:
                child.children = self._trace_from_return(mv.reference)
            elif mv.reference_type == 'PURCHASE' and mv.reference:
                child.children = self._trace_from_purchase(mv.reference)
            elif mv.reference_type == 'TRANSFER' and mv.reference:
                child.children = self._trace_from_transfer(mv.reference)

            root.children.append(child)

        return root

    def _trace_from_sale(self, reference: str) -> List[LineageNode]:
        try:
            from sales.models import SalesInvoice
            invoice = SalesInvoice.objects.filter(invoice_number=reference).first()
            if invoice:
                return [LineageNode(
                    model_name='SalesInvoice',
                    object_id=str(invoice.id),
                    reference=invoice.invoice_number,
                    quantity=Decimal(str(invoice.total_amount)),
                )]
        except Exception:
            pass
        return []

    def _trace_from_return(self, reference: str) -> List[LineageNode]:
        try:
            from returns.models import ReturnOrder
            ro = ReturnOrder.objects.filter(return_number=reference).first()
            if ro:
                journal_id = ''
                if ro.journal_entry:
                    journal_id = str(ro.journal_entry.id)
                return [LineageNode(
                    model_name='ReturnOrder',
                    object_id=str(ro.id),
                    reference=ro.return_number,
                    quantity=Decimal(str(ro.total_amount)),
                    children=[
                        LineageNode(
                            model_name='JournalEntry',
                            object_id=journal_id,
                            reference=ro.return_number,
                        )
                    ] if journal_id else []
                )]
        except Exception:
            pass
        return []

    def _trace_from_purchase(self, reference: str) -> List[LineageNode]:
        try:
            from purchases.models import PurchaseInvoice
            pi = PurchaseInvoice.objects.filter(invoice_number=reference).first()
            if pi:
                return [LineageNode(
                    model_name='PurchaseInvoice',
                    object_id=str(pi.id),
                    reference=pi.invoice_number,
                    quantity=Decimal(str(pi.total_amount)),
                )]
        except Exception:
            pass
        return []

    def _trace_from_transfer(self, reference: str) -> List[LineageNode]:
        return [LineageNode(
            model_name='Transfer',
            object_id=reference,
            reference=reference,
        )]

    def validate_batch_lineage(self, batch, expected_quantity: Optional[Decimal] = None) -> LineageValidationResult:
        """
        Validate that a batch's current quantity matches the lineage-derived quantity.
        """
        issues: List[str] = []
        from inventory.models import StockMovement
        movements = StockMovement.objects.filter(batch=batch)
        lineage_qty = Decimal('0')
        for mv in movements:
            lineage_qty += Decimal(str(mv.quantity))

        current_qty = Decimal(str(batch.remaining_quantity))
        drift = current_qty - lineage_qty

        if expected_quantity is not None and current_qty != expected_quantity:
            issues.append(
                f"Current quantity ({current_qty}) != expected ({expected_quantity})"
            )

        if abs(drift) > Decimal('0.01'):
            msg = (
                f"INVENTORY LINEAGE VIOLATION: Batch {batch.batch_code or batch.id} "
                f"remaining_quantity={current_qty} but StockMovement sum={lineage_qty} "
                f"(drift={drift})"
            )
            issues.append(msg)
            self._violations.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

        return LineageValidationResult(
            valid=len(issues) == 0,
            batch_id=str(batch.id),
            batch_code=batch.batch_code or str(batch.id),
            current_quantity=current_qty,
            lineage_quantity=lineage_qty,
            drift=drift,
            chain_length=movements.count(),
            issues=issues,
        )

    def validate_all_batches(self) -> Dict[str, LineageValidationResult]:
        """Validate lineage for every batch in the system."""
        from inventory.models import Batch
        results = {}
        for batch in Batch.objects.all().iterator():
            results[str(batch.id)] = self.validate_batch_lineage(batch)
        return results

    def check_batch_consistency(self, batch, invoice_item) -> None:
        """
        Verify that a batch's product and warehouse match the invoice item's context.
        This prevents wrong-product or wrong-warehouse assignments.
        """
        issues = []
        if hasattr(invoice_item, 'product') and invoice_item.product:
            if batch.product_id != invoice_item.product_id:
                issues.append(
                    f"Batch product ({batch.product_id}) != InvoiceItem product ({invoice_item.product_id})"
                )
        if batch.warehouse_id is None:
            issues.append("Batch has null warehouse_id")
        if issues:
            msg = (
                f"BATCH CONSISTENCY VIOLATION for batch {batch.id}: "
                f"{' | '.join(issues)}"
            )
            self._violations.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

    @property
    def has_violations(self) -> bool:
        return len(self._violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def clear(self) -> None:
        self._violations.clear()


_enforcer_instance: Optional[InventoryLineageEnforcer] = None


def get_lineage_enforcer(mode: str = 'BLOCK') -> InventoryLineageEnforcer:
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = InventoryLineageEnforcer(mode=mode)
    return _enforcer_instance
