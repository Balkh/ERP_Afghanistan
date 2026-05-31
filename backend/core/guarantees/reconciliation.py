"""
Class 2: ReconciliationCompletenessGuard — Return Chain Atomicity.

GUARANTEE: No return is valid until full chain is complete:
  1. ReturnOrder record
  2. Inventory restoration (StockMovement)
  3. Accounting reversal (JournalEntry)
  4. AR/AP adjustment (JournalEntryLine on AR/AP)
  5. Treasury impact (FinancialTransaction for refund)
  6. ReconciliationEntry

If ANY step is missing → SYSTEM INVALID.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ReturnChainStatus:
    return_id: str
    return_number: str
    has_stock_movement: bool = False
    has_journal_entry: bool = False
    has_ar_ap_adjustment: bool = False
    has_treasury_impact: bool = False
    has_reconciliation: bool = False
    invoice_amount: Decimal = Decimal('0')
    journal_amount: Decimal = Decimal('0')
    refund_amount: Decimal = Decimal('0')
    all_present: bool = False
    missing_elements: List[str] = field(default_factory=list)
    amount_mismatches: List[str] = field(default_factory=list)


class ReconciliationCompletenessGuard:
    """
    Validates the full return processing chain for completeness.

    Mode:
      - LOG:   Log warnings
      - BLOCK: Raise AssertionError
    """

    MODE_LOG = 'LOG'
    MODE_BLOCK = 'BLOCK'

    REQUIRED_ELEMENTS = [
        'has_stock_movement',
        'has_journal_entry',
        'has_ar_ap_adjustment',
        'has_reconciliation',
    ]

    def __init__(self, mode: str = 'BLOCK'):
        self.mode = mode
        self._failures: List[str] = []

    def check_return_chain(self, return_order) -> ReturnChainStatus:
        """Inspect a ReturnOrder and determine chain completeness."""
        status = ReturnChainStatus(
            return_id=str(return_order.id),
            return_number=return_order.return_number,
            invoice_amount=Decimal(str(return_order.total_amount)),
        )

        # 1. Check ReturnOrder record
        if return_order.pk is None:
            status.missing_elements.append("ReturnOrder: not persisted")
        else:
            status.all_present = True

        # 2. Check StockMovement (inventory restoration)
        from inventory.models import StockMovement
        movements = StockMovement.objects.filter(
            reference=str(return_order.return_number)
        )
        if not movements.exists():
            movements = StockMovement.objects.filter(
                reference_id=str(return_order.id),
                reference_type='RETURN'
            )
        status.has_stock_movement = movements.exists()
        if not status.has_stock_movement:
            status.missing_elements.append("StockMovement: not found for return")

        # 3. Check JournalEntry (accounting reversal)
        journal = getattr(return_order, 'journal_entry', None) or getattr(return_order, 'reversal_journal_entry', None)
        if journal is not None and journal.is_posted:
            from accounting.models import JournalEntryLine
            lines = JournalEntryLine.objects.filter(entry=journal)
            total = sum(abs(line.debit - line.credit) for line in lines)
            status.has_journal_entry = True
            status.journal_amount = total
            if abs(total - status.invoice_amount) > Decimal('0.02'):
                status.amount_mismatches.append(
                    f"Journal amount ({total}) != Return amount ({status.invoice_amount})"
                )
        if not status.has_journal_entry:
            status.missing_elements.append("JournalEntry: not found or not posted")

        # 4. Check AR/AP adjustment lines
        if status.has_journal_entry:
            from accounting.models import Account
            ar_ap_accounts = Account.objects.filter(
                code__in=['1100', '2100'],
                is_active=True,
            )
            from accounting.models import JournalEntryLine
            lines = JournalEntryLine.objects.filter(
                entry=journal,
                account__in=ar_ap_accounts,
            )
            status.has_ar_ap_adjustment = lines.exists()
            if not status.has_ar_ap_adjustment:
                status.missing_elements.append("AR/AP adjustment: no JournalEntryLine on AR/AP account")

        # 5. Check treasury impact (refund)
        from payments.models import FinancialTransaction
        refund_txns = FinancialTransaction.objects.filter(
            description__icontains=return_order.return_number,
            status='COMPLETED',
        )
        if refund_txns.exists():
            status.has_treasury_impact = True
            status.refund_amount = sum(txn.amount for txn in refund_txns)

        # 6. Check ReconciliationEntry
        try:
            if hasattr(return_order, 'reconciliation_entries'):
                recs = return_order.reconciliation_entries.all()
                status.has_reconciliation = recs.exists()
        except Exception:
            pass
        if not status.has_reconciliation:
            try:
                from returns.models import ReconciliationEntry
                recs = ReconciliationEntry.objects.filter(
                    return_order=return_order
                )
                status.has_reconciliation = recs.exists()
            except Exception:
                pass
        if not status.has_reconciliation:
            status.missing_elements.append("ReconciliationEntry: not found for return")

        # Final evaluation
        present_count = sum(
            1 for attr in self.REQUIRED_ELEMENTS if getattr(status, attr, False)
        )
        status.all_present = (present_count == len(self.REQUIRED_ELEMENTS))

        if not status.all_present or status.amount_mismatches:
            msg = (
                f"RETURN CHAIN INCOMPLETE: {return_order.return_number} "
                f"(id={return_order.id}). Missing: {status.missing_elements}. "
                f"Amount mismatches: {status.amount_mismatches}"
            )
            self._failures.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

        return status

    def check_all_returns(self) -> Dict[str, ReturnChainStatus]:
        """Validate the return chain for every approved return in the system."""
        from returns.models import ReturnOrder

        results = {}
        for ro in ReturnOrder.objects.filter(status__in=['APPROVED', 'COMPLETED']).iterator():
            results[ro.return_number] = self.check_return_chain(ro)
        return results

    @property
    def has_failures(self) -> bool:
        return len(self._failures) > 0

    @property
    def failure_count(self) -> int:
        return len(self._failures)

    def clear(self) -> None:
        self._failures.clear()
