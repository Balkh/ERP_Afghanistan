import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from simulation.truth_engine.models.models import ActualState


logger = logging.getLogger('erp.simulation.truth.actual')


class ActualStateCollector:
    """
    Collects actual state from ERP system (read-only).
    NO modifications allowed. NO write operations.
    Uses Django ORM queries only.
    """

    def __init__(self, collected_at: Optional[datetime] = None):
        self._collected_at = collected_at or datetime.now()
        self._state = ActualState(self._collected_at, source='erp')

    def collect_journal_entries(
        self, since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        company_id: Optional[str] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of journal entries.
        """
        try:
            from accounting.models import JournalEntry
            qs = JournalEntry.objects.all()
            if since:
                qs = qs.filter(date__gte=since)
            if until:
                qs = qs.filter(date__lte=until)
            if company_id:
                qs = qs.filter(company_id=company_id)
            self._state.set_journal_count(qs.count())
            for je in qs[:100]:
                self._state.add_journal_entry({
                    'id': str(je.id),
                    'entry_number': je.entry_number,
                    'date': str(je.date),
                    'description': je.description or '',
                    'is_reversed': je.is_reversed,
                    'is_posted': je.is_posted,
                })
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read journal entries "
                "(DB may not be available in test context)"
            )
        return self

    def collect_stock_movements(
        self, since: Optional[datetime] = None,
        warehouse_id: Optional[str] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of stock movements.
        """
        try:
            from inventory.models import StockMovement
            qs = StockMovement.objects.all()
            if since:
                qs = qs.filter(created_at__gte=since)
            if warehouse_id:
                qs = qs.filter(warehouse_id=warehouse_id)
            for sm in qs[:100]:
                self._state.add_stock_movement({
                    'id': str(sm.id),
                    'movement_type': sm.movement_type,
                    'quantity': str(sm.quantity),
                    'created_at': str(sm.created_at),
                })
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read stock movements "
                "(DB may not be available)"
            )
        return self

    def collect_sales_invoices(
        self, since: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of sales invoices.
        """
        try:
            from sales.models import SalesInvoice
            qs = SalesInvoice.objects.all()
            if since:
                qs = qs.filter(invoice_date__gte=since)
            if status:
                qs = qs.filter(status=status)
            for inv in qs[:100]:
                self._state.add_invoice({
                    'id': str(inv.id),
                    'invoice_number': inv.invoice_number,
                    'total_amount': str(inv.total_amount),
                    'status': inv.status,
                    'invoice_date': str(inv.invoice_date),
                })
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read sales invoices"
            )
        return self

    def collect_purchase_invoices(
        self, since: Optional[datetime] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of purchase invoices.
        """
        try:
            from purchases.models import PurchaseInvoice
            qs = PurchaseInvoice.objects.all()
            if since:
                qs = qs.filter(invoice_date__gte=since)
            for inv in qs[:100]:
                self._state.add_invoice({
                    'id': str(inv.id),
                    'invoice_number': inv.invoice_number,
                    'total_amount': str(inv.total_amount),
                    'status': inv.status,
                    'invoice_date': str(inv.invoice_date),
                })
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read purchase invoices"
            )
        return self

    def collect_inventory_quantities(
        self, warehouse_id: Optional[str] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of current inventory quantities.
        """
        try:
            from inventory.models import Batch
            qs = Batch.objects.filter(remaining_quantity__gt=0)
            if warehouse_id:
                qs = qs.filter(warehouse_id=warehouse_id)
            for batch in qs:
                product_id = str(batch.product_id)
                current = self._state._inventory_quantity.get(
                    product_id, 0.0
                )
                self._state.set_inventory_quantity(
                    product_id,
                    current + float(batch.remaining_quantity)
                )
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read inventory quantities"
            )
        return self

    def collect_transactions(
        self, since: Optional[datetime] = None,
    ) -> 'ActualStateCollector':
        """
        Read-only query of financial transactions.
        """
        try:
            from payments.models import FinancialTransaction
            qs = FinancialTransaction.objects.all()
            if since:
                qs = qs.filter(created_at__gte=since)
            for txn in qs[:100]:
                self._state.add_transaction({
                    'id': str(txn.id),
                    'transaction_type': txn.transaction_type,
                    'amount': str(txn.amount),
                    'status': txn.status,
                    'created_at': str(txn.created_at),
                })
        except Exception:
            logger.warning(
                "ActualStateCollector: could not read transactions"
            )
        return self

    def build(self) -> ActualState:
        return self._state

    def to_dict(self) -> Dict[str, Any]:
        return self._state.to_dict()
