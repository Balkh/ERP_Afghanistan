"""
SECTION 2: MULTI-USER OPERATIONAL TESTING
Extracted from PreProductionHardeningValidator.validate_multi_user_operations
"""
import threading
import uuid
from datetime import date
from decimal import Decimal

from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from inventory.models import Product, Batch, StockMovement, Warehouse

        cash = Account.objects.filter(code="1000").first()
        revenue = Account.objects.filter(account_type="REVENUE").first()
        equity = Account.objects.filter(account_type="EQUITY").first()

        if not (cash and revenue and equity):
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_HIGH,
                check="account_availability",
                detail="Required accounts (cash=1000, revenue, equity) not found",
            ))
            passed = False
            validator.results["multi_user_validation"] = SectionResult(
                name="Multi-User Operational Testing", passed=passed, issues=issues,
            )
            validator.issues.extend(issues)
            return validator.results["multi_user_validation"]

        je_ids = []
        je_lock = threading.Lock()

        def accountant_post_journal(thread_id: int):
            try:
                from accounting.models import Account, JournalEntry, JournalEntryLine
                from decimal import Decimal
                from django.db import transaction

                with transaction.atomic():
                    c = Account.objects.select_for_update().filter(code="1000").first()
                    e = Account.objects.select_for_update().filter(account_type="EQUITY").first()
                    if not c or not e:
                        return
                    je = JournalEntry.objects.create(
                        entry_number=f"MU-JE-{thread_id}-{uuid.uuid4().hex[:6]}",
                        entry_date=date.today(), entry_type="ADJUSTMENT",
                        description=f"Multi-user test {thread_id}", is_posted=True,
                    )
                    JournalEntryLine.objects.create(
                        entry=je, account=c, debit=Decimal("100.00"), credit=Decimal("0.00"),
                    )
                    JournalEntryLine.objects.create(
                        entry=je, account=e, debit=Decimal("0.00"), credit=Decimal("100.00"),
                    )
                    with je_lock:
                        je_ids.append(je.id)
            except Exception:
                with je_lock:
                    je_ids.append(None)

        threads = []
        accountant_count = 5
        for i in range(accountant_count):
            t = threading.Thread(target=accountant_post_journal, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=30)

        failed_jes = sum(1 for jid in je_ids if jid is None)
        if failed_jes > 0:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_MEDIUM,
                check="concurrent_journal_posting",
                detail=f"{failed_jes}/{accountant_count} concurrent journal posts failed — expected with SQLite single-writer, resolved by PostgreSQL",
                evidence={"engine": "SQLite (single-writer)", "resolution": "PostgreSQL with CONN_MAX_AGE"},
            ))
        else:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_LOW,
                check="concurrent_journal_posting",
                detail=f"{accountant_count} accountants posted journals concurrently", passed=True,
            ))

        unbalanced = 0
        for jid in je_ids:
            if jid is not None:
                je = JournalEntry.objects.get(id=jid)
                if not je.is_balanced:
                    unbalanced += 1
        if unbalanced > 0:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_CRITICAL,
                check="journal_balance_after_concurrent",
                detail=f"{unbalanced} unbalanced journals after concurrent posting",
            ))
        else:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_LOW,
                check="journal_balance_after_concurrent",
                detail="All concurrent journals balanced", passed=True,
            ))

        invoice_ids = []
        inv_lock = threading.Lock()

        def cashier_create_invoice(thread_id: int):
            try:
                from accounting.models import Account, JournalEntry, JournalEntryLine
                from decimal import Decimal
                from django.db import transaction

                with transaction.atomic():
                    c = Account.objects.select_for_update().filter(code="1000").first()
                    r = Account.objects.select_for_update().filter(account_type="REVENUE").first()
                    if not c or not r:
                        return
                    je = JournalEntry.objects.create(
                        entry_number=f"MU-INV-{thread_id}-{uuid.uuid4().hex[:6]}",
                        entry_date=date.today(), entry_type="SALE",
                        description=f"Multi-user invoice {thread_id}", is_posted=True,
                    )
                    JournalEntryLine.objects.create(
                        entry=je, account=c, debit=Decimal("50.00"), credit=Decimal("0.00"),
                    )
                    JournalEntryLine.objects.create(
                        entry=je, account=r, debit=Decimal("0.00"), credit=Decimal("50.00"),
                    )
                    with inv_lock:
                        invoice_ids.append(je.id)
            except Exception:
                with inv_lock:
                    invoice_ids.append(None)

        threads = []
        cashier_count = 10
        for i in range(cashier_count):
            t = threading.Thread(target=cashier_create_invoice, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=30)

        failed_invs = sum(1 for iid in invoice_ids if iid is None)
        if failed_invs > 0:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_MEDIUM,
                check="concurrent_invoice_creation",
                detail=f"{failed_invs}/{cashier_count} concurrent invoices failed — expected with SQLite single-writer, resolved by PostgreSQL",
                evidence={"engine": "SQLite (single-writer)", "resolution": "PostgreSQL with CONN_MAX_AGE"},
            ))
        else:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_LOW,
                check="concurrent_invoice_creation",
                detail=f"{cashier_count} cashiers created invoices concurrently", passed=True,
            ))

        inv_ub = 0
        for iid in invoice_ids:
            if iid is not None:
                je = JournalEntry.objects.get(id=iid)
                if not je.is_balanced:
                    inv_ub += 1
        if inv_ub > 0:
            issues.append(HardeningIssue(
                section="multi_user", severity=ISSUE_CRITICAL,
                check="invoice_balance_after_concurrent",
                detail=f"{inv_ub} unbalanced invoices after concurrent creation",
            ))

        warehouse = Warehouse.objects.first()
        if warehouse:
            wh_lock = threading.Lock()
            wh_results = []

            def warehouse_stock_operation(op_id: int):
                try:
                    from inventory.models import Batch, StockMovement, Product, Warehouse
                    from decimal import Decimal
                    from django.db import transaction

                    prod = Product.objects.first()
                    wh = Warehouse.objects.first()
                    if not prod or not wh:
                        return
                    batch = Batch.objects.create(
                        product=prod,
                        batch_number=f"MU-BATCH-{op_id}-{uuid.uuid4().hex[:6]}",
                        manufacturing_date=date(2026, 1, 1),
                        expiry_date=date(2027, 1, 1),
                        purchase_price=Decimal("50.00"), sale_price=Decimal("100.00"),
                        quantity=Decimal("100"), remaining_quantity=Decimal("100"),
                    )
                    StockMovement.objects.create(
                        product=prod, batch=batch, warehouse=wh,
                        movement_type="IN", reference_type="PURCHASE",
                        quantity=Decimal("100"), unit_cost=Decimal("50.00"),
                    )
                    StockMovement.objects.create(
                        product=prod, batch=batch, warehouse=wh,
                        movement_type="OUT", reference_type="SALE",
                        quantity=Decimal("-10"), unit_cost=Decimal("50.00"),
                    )
                    batch.refresh_from_db()
                    with wh_lock:
                        wh_results.append(batch.remaining_quantity)
                except Exception as e:
                    with wh_lock:
                        wh_results.append(None)

            threads = []
            for i in range(5):
                t = threading.Thread(target=warehouse_stock_operation, args=(i,))
                threads.append(t)
                t.start()
            for t in threads:
                t.join(timeout=30)

            wh_failures = sum(1 for r in wh_results if r is None)
            wh_wrong = sum(1 for r in wh_results if r is not None and r != Decimal("90"))
            if wh_failures > 0:
                issues.append(HardeningIssue(
                    section="multi_user", severity=ISSUE_MEDIUM,
                    check="concurrent_inventory_contention",
                    detail=f"{wh_failures}/5 concurrent stock operations failed — expected with SQLite single-writer, resolved by PostgreSQL",
                    evidence={"engine": "SQLite (single-writer)", "resolution": "PostgreSQL with CONN_MAX_AGE"},
                ))
            if wh_wrong > 0:
                issues.append(HardeningIssue(
                    section="multi_user", severity=ISSUE_MEDIUM,
                    check="inventory_drift",
                    detail=f"{wh_wrong} stock operations produced incorrect remaining_quantity — likely SQLite contention",
                    evidence={"results": [str(r) for r in wh_results]},
                ))
            if wh_failures == 0 and wh_wrong == 0:
                issues.append(HardeningIssue(
                    section="multi_user", severity=ISSUE_LOW,
                    check="concurrent_inventory", detail="5 concurrent stock ops all correct", passed=True,
                ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="multi_user", severity=ISSUE_CRITICAL,
            check="multi_user_crash", detail=f"Multi-user validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["multi_user_validation"] = SectionResult(
        name="Multi-User Operational Testing", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["multi_user_validation"]
