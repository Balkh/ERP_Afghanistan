"""
Domain Invariant Validation Engine.

Detects and reports invariant violations across business domains.
Read-only — never modifies state. Provides structured violation reports
for audit and remediation.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from decimal import Decimal


INVARIANT_VERSION = "1.0.0"


@dataclass
class InvariantViolation:
    domain: str
    entity_type: str
    entity_id: str
    invariant: str
    severity: str  # critical | error | warning
    message: str
    detail: str = ""
    source: str = "invariant_validator"


@dataclass
class InvariantReport:
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.utcnow().isoformat() + "Z")
    violations: List[InvariantViolation] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "critical")

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0


def check_accounting_invariants() -> List[InvariantViolation]:
    """Verify accounting domain invariants."""
    from django.db.models import Sum
    from accounting.models import JournalEntry, JournalEntryLine, Account

    violations = []

    # Invariant 1: Every posted JE must be balanced (Debit == Credit)
    for je in JournalEntry.objects.filter(is_posted=True):
        totals = je.lines.aggregate(
            debit_total=Sum("debit"),
            credit_total=Sum("credit"),
        )
        if (totals["debit_total"] or 0) != (totals["credit_total"] or 0):
            violations.append(InvariantViolation(
                domain="accounting",
                entity_type="JournalEntry",
                entity_id=str(je.entry_number),
                invariant="je_debit_equals_credit",
                severity="critical",
                message=f"JE #{je.entry_number}: Debit ({totals['debit_total']}) != Credit ({totals['credit_total']})",
            ))

    # Invariant 2: Account balance must match posted JE lines
    for acc in Account.objects.all():
        debit_total = JournalEntryLine.objects.filter(
            account=acc, entry__is_posted=True
        ).aggregate(Sum("debit"))["debit__sum"] or Decimal("0")
        credit_total = JournalEntryLine.objects.filter(
            account=acc, entry__is_posted=True
        ).aggregate(Sum("credit"))["credit__sum"] or Decimal("0")
        expected = debit_total - credit_total
        if abs(acc.balance - expected) > Decimal("0.02"):
            violations.append(InvariantViolation(
                domain="accounting",
                entity_type="Account",
                entity_id=str(acc.code),
                invariant="account_balance_matches_journal",
                severity="error",
                message=f"Account {acc.code} ({acc.name}): expected={expected}, actual={acc.balance}",
            ))

    return violations


def check_sales_invariants() -> List[InvariantViolation]:
    """Verify sales domain invariants."""
    from django.db.models import Sum
    from sales.models import SalesInvoice, Customer

    violations = []

    # Invariant 1: Customer balance must match outstanding invoices minus payments
    for customer in Customer.objects.all():
        outstanding = SalesInvoice.objects.filter(
            customer=customer,
            status__in=["CONFIRMED", "DISPATCHED", "PARTIAL_PAID"],
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        paid = customer.customer_payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        expected = outstanding - paid
        if abs(customer.balance - expected) > Decimal("1"):
            violations.append(InvariantViolation(
                domain="sales",
                entity_type="Customer",
                entity_id=str(customer.id),
                invariant="customer_balance_consistent",
                severity="error",
                message=f"Customer '{customer.name}': expected={expected}, actual={customer.balance}",
            ))

    # Invariant 2: Dispatched invoices must have journal entry
    for inv in SalesInvoice.objects.filter(status="DISPATCHED"):
        if not inv.journal_entry_id:
            violations.append(InvariantViolation(
                domain="sales",
                entity_type="SalesInvoice",
                entity_id=str(inv.invoice_number),
                invariant="dispatched_invoice_has_journal_entry",
                severity="error",
                message=f"Invoice {inv.invoice_number} is DISPATCHED but has no journal entry",
            ))

    return violations


def check_purchase_invariants() -> List[InvariantViolation]:
    """Verify purchase domain invariants."""
    from django.db.models import Sum
    from purchases.models import PurchaseInvoice, Supplier

    violations = []

    # Invariant 1: Supplier balance must match outstanding
    for supplier in Supplier.objects.all():
        outstanding = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=["RECEIVED", "PARTIAL_PAID"],
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        paid = supplier.supplier_payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        expected = outstanding - paid
        if abs(supplier.balance - expected) > Decimal("1"):
            violations.append(InvariantViolation(
                domain="purchases",
                entity_type="Supplier",
                entity_id=str(supplier.id),
                invariant="supplier_balance_consistent",
                severity="error",
                message=f"Supplier '{supplier.name}': expected={expected}, actual={supplier.balance}",
            ))

    # Invariant 2: Received invoices must have journal entry
    for inv in PurchaseInvoice.objects.filter(status="RECEIVED"):
        if not inv.journal_entry_id:
            violations.append(InvariantViolation(
                domain="purchases",
                entity_type="PurchaseInvoice",
                entity_id=str(inv.invoice_number),
                invariant="received_invoice_has_journal_entry",
                severity="error",
                message=f"Invoice {inv.invoice_number} is RECEIVED but has no journal entry",
            ))

    return violations


def check_return_invariants() -> List[InvariantViolation]:
    """Verify returns domain invariants."""
    from returns.models import ReturnOrder

    violations = []

    # Invariant: Approved/completed returns must have journal entry
    for ret in ReturnOrder.objects.filter(status__in=["APPROVED", "COMPLETED"]):
        if not ret.journal_entry_id:
            violations.append(InvariantViolation(
                domain="returns",
                entity_type="ReturnOrder",
                entity_id=str(ret.return_number),
                invariant="approved_return_has_journal_entry",
                severity="error",
                message=f"Return {ret.return_number} is {ret.status} but has no journal entry",
            ))

    return violations


def check_inventory_invariants() -> List[InvariantViolation]:
    """Verify inventory domain invariants."""
    from inventory.models import Batch

    violations = []

    # Invariant: Batch remaining_quantity must never be negative
    for batch in Batch.objects.filter(remaining_quantity__lt=0):
        violations.append(InvariantViolation(
            domain="inventory",
            entity_type="Batch",
            entity_id=str(batch.id),
            invariant="batch_quantity_non_negative",
            severity="critical",
            message=f"Batch #{batch.id} ({batch.batch_number}): remaining_quantity={batch.remaining_quantity}",
        ))

    return violations


def run_full_invariant_check() -> InvariantReport:
    """Run all invariant checks across all domains."""
    all_violations = []
    for check_fn in [
        check_accounting_invariants,
        check_sales_invariants,
        check_purchase_invariants,
        check_return_invariants,
        check_inventory_invariants,
    ]:
        try:
            all_violations.extend(check_fn())
        except Exception as e:
            all_violations.append(InvariantViolation(
                domain="system",
                entity_type="InvariantChecker",
                entity_id=check_fn.__name__,
                invariant="check_execution",
                severity="warning",
                message=f"Invariant check '{check_fn.__name__}' failed: {e}",
            ))

    return InvariantReport(violations=all_violations)
