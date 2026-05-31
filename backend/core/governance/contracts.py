"""
Governance Contracts — Explicit, deterministic, testable contracts for all governance domains.

Every contract defines:
  - Contract ID (unique, namespaced)
  - Domain (accounting, sales, purchases, returns, inventory, system)
  - Check function (deterministic, pure-ish)
  - Severity (critical | error | warning)
  - Description

Contracts are registered with the GovernanceKernel at startup
via register_invariant().
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class GovernanceContract:
    """A single deterministic governance contract."""
    contract_id: str
    domain: str
    description: str
    severity: str  # critical | error | warning
    check_fn: Callable[[dict], Tuple[bool, str]]
    priority: str = "high"

    def __call__(self, context: dict) -> Tuple[bool, str]:
        return self.check_fn(context)


def make_accounting_contracts() -> List[GovernanceContract]:
    """Build all accounting domain contracts."""
    contracts = []

    def je_balance(context: dict) -> Tuple[bool, str]:
        from accounting.models import JournalEntry
        from django.db.models import Sum
        entry_id = context.get("journal_entry_id")
        if not entry_id:
            return True, "No journal entry specified"
        try:
            je = JournalEntry.objects.get(id=entry_id)
            totals = je.lines.aggregate(
                d=Sum("debit"), c=Sum("credit")
            )
            if (totals["d"] or 0) != (totals["c"] or 0):
                return False, f"JE #{je.entry_number} unbalanced: D={totals['d']} C={totals['c']}"
            return True, "Balanced"
        except JournalEntry.DoesNotExist:
            return False, f"JE #{entry_id} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="accounting.je_balanced",
        domain="accounting",
        description="Posted journal entries must have equal debits and credits",
        severity="critical",
        check_fn=je_balance,
        priority="critical",
    ))

    def account_balance(context: dict) -> Tuple[bool, str]:
        from accounting.models import Account, JournalEntryLine
        from django.db.models import Sum
        from decimal import Decimal
        code = context.get("account_code")
        if not code:
            return True, "No account specified"
        try:
            acc = Account.objects.get(code=code)
            d = JournalEntryLine.objects.filter(
                account=acc, entry__is_posted=True
            ).aggregate(Sum("debit"))["debit__sum"] or Decimal("0")
            c = JournalEntryLine.objects.filter(
                account=acc, entry__is_posted=True
            ).aggregate(Sum("credit"))["credit__sum"] or Decimal("0")
            expected = d - c
            if abs(acc.balance - expected) > Decimal("0.02"):
                return False, f"Account {acc.code}: expected={expected} actual={acc.balance}"
            return True, "Consistent"
        except Account.DoesNotExist:
            return False, f"Account #{code} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="accounting.balance_consistency",
        domain="accounting",
        description="Account balance must match posted journal entry lines",
        severity="error",
        check_fn=account_balance,
        priority="critical",
    ))

    return contracts


def make_sales_contracts() -> List[GovernanceContract]:
    """Build all sales domain contracts."""
    contracts = []

    def customer_balance(context: dict) -> Tuple[bool, str]:
        from sales.models import SalesInvoice, Customer
        from decimal import Decimal
        customer_id = context.get("customer_id")
        if not customer_id:
            return True, "No customer specified"
        try:
            c = Customer.objects.get(id=customer_id)
            outstanding = SalesInvoice.objects.filter(
                customer=c, status__in=["CONFIRMED", "DISPATCHED", "PARTIAL_PAID"],
            ).aggregate(total=__import__("django.db.models").Sum("total_amount"))["total"] or Decimal("0")
            paid = c.customer_payments.aggregate(
                total=__import__("django.db.models").Sum("amount")
            )["total"] or Decimal("0")
            expected = outstanding - paid
            if abs(c.balance - expected) > Decimal("1"):
                return False, f"Customer {c.name}: expected={expected} actual={c.balance}"
            return True, "Consistent"
        except Customer.DoesNotExist:
            return False, f"Customer #{customer_id} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="sales.customer_balance_consistent",
        domain="sales",
        description="Customer balance must match outstanding invoices minus payments",
        severity="error",
        check_fn=customer_balance,
        priority="high",
    ))

    return contracts


def make_purchase_contracts() -> List[GovernanceContract]:
    """Build all purchase domain contracts."""
    contracts = []

    def supplier_balance(context: dict) -> Tuple[bool, str]:
        from purchases.models import PurchaseInvoice, Supplier
        from decimal import Decimal
        supplier_id = context.get("supplier_id")
        if not supplier_id:
            return True, "No supplier specified"
        try:
            s = Supplier.objects.get(id=supplier_id)
            outstanding = PurchaseInvoice.objects.filter(
                supplier=s, status__in=["RECEIVED", "PARTIAL_PAID"],
            ).aggregate(total=__import__("django.db.models").Sum("total_amount"))["total"] or Decimal("0")
            paid = s.supplier_payments.aggregate(
                total=__import__("django.db.models").Sum("amount")
            )["total"] or Decimal("0")
            expected = outstanding - paid
            if abs(s.balance - expected) > Decimal("1"):
                return False, f"Supplier {s.name}: expected={expected} actual={s.balance}"
            return True, "Consistent"
        except Supplier.DoesNotExist:
            return False, f"Supplier #{supplier_id} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="purchases.supplier_balance_consistent",
        domain="purchases",
        description="Supplier balance must match outstanding invoices minus payments",
        severity="error",
        check_fn=supplier_balance,
        priority="high",
    ))

    return contracts


def make_inventory_contracts() -> List[GovernanceContract]:
    """Build all inventory domain contracts."""
    contracts = []

    def batch_non_negative(context: dict) -> Tuple[bool, str]:
        from inventory.models import Batch
        batch_id = context.get("batch_id")
        if not batch_id:
            return True, "No batch specified"
        try:
            b = Batch.objects.get(id=batch_id)
            if b.remaining_quantity < 0:
                return False, f"Batch #{b.batch_number}: qty={b.remaining_quantity}"
            return True, "Positive"
        except Batch.DoesNotExist:
            return False, f"Batch #{batch_id} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="inventory.batch_quantity_non_negative",
        domain="inventory",
        description="Batch remaining quantity must never be negative",
        severity="critical",
        check_fn=batch_non_negative,
        priority="critical",
    ))

    return contracts


def make_return_contracts() -> List[GovernanceContract]:
    """Build all returns domain contracts."""
    contracts = []

    def return_has_journal(context: dict) -> Tuple[bool, str]:
        from returns.models import ReturnOrder
        return_id = context.get("return_order_id")
        if not return_id:
            return True, "No return specified"
        try:
            r = ReturnOrder.objects.get(id=return_id)
            if r.status in ("APPROVED", "COMPLETED") and not r.journal_entry_id:
                return False, f"Return {r.return_number} is {r.status} but has no journal entry"
            return True, "Has journal entry or not yet needed"
        except ReturnOrder.DoesNotExist:
            return False, f"Return #{return_id} not found"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="returns.approved_return_has_journal",
        domain="returns",
        description="Approved/completed returns must have associated journal entry",
        severity="error",
        check_fn=return_has_journal,
        priority="high",
    ))

    return contracts


def make_system_contracts() -> List[GovernanceContract]:
    """Build all system-level contracts."""
    contracts = []

    def db_connectivity(context: dict) -> Tuple[bool, str]:
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone()[0] == 1:
                    return True, "Database connection alive"
                return False, "Unexpected DB response"
        except Exception as e:
            return False, str(e)

    contracts.append(GovernanceContract(
        contract_id="system.database_connectivity",
        domain="system",
        description="Database connection must be alive",
        severity="critical",
        check_fn=db_connectivity,
        priority="critical",
    ))

    return contracts


def register_all_contracts(kernel) -> None:
    """Register all governance contracts with the kernel."""
    from core.governance.kernel import GovernanceKernel

    all_contracts = []
    all_contracts.extend(make_accounting_contracts())
    all_contracts.extend(make_sales_contracts())
    all_contracts.extend(make_purchase_contracts())
    all_contracts.extend(make_inventory_contracts())
    all_contracts.extend(make_return_contracts())
    all_contracts.extend(make_system_contracts())

    for contract in all_contracts:
        kernel.invariants.register(
            invariant_id=contract.contract_id,
            check_fn=contract.check_fn,
            meta={
                "domain": contract.domain,
                "severity": contract.severity,
                "description": contract.description,
                "priority": contract.priority,
            },
        )

    return all_contracts
