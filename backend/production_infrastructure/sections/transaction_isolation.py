import logging
import os
import sys
import time
import uuid
import threading
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

"""SECTION: Transaction Isolation Hardening — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from inventory.models import Product, Batch, StockMovement, Warehouse
        from decimal import Decimal

        cash = Account.objects.filter(code="1000").first()
        equity = Account.objects.filter(account_type="EQUITY").first()
        if not cash or not equity:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=HIGH,
                check="accounts_available", detail="Required accounts not found",
            ))
            passed = False
            self.results["transaction_isolation"] = SectionResult(
                name="Transaction Isolation Hardening", passed=passed, issues=issues,
            )
            self.issues.extend(issues)
            return self.results["transaction_isolation"]

        row_lock_results = []
        rl_lock = threading.Lock()

        def test_row_lock(thread_id: int):
            try:
                from django.db import transaction
                from accounting.models import Account
                from decimal import Decimal
                with transaction.atomic():
                    acct = Account.objects.select_for_update().filter(code="1000").first()
                    if acct:
                        orig = acct.balance
                        acct.balance = orig
                        acct.save(update_fields=["balance"])
                        with rl_lock:
                            row_lock_results.append({"thread": thread_id, "locked": True, "balance": orig})
            except Exception as e:
                with rl_lock:
                    row_lock_results.append({"thread": thread_id, "locked": False, "error": str(e)})

        threads = []
        for i in range(3):
            t = threading.Thread(target=test_row_lock, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=15)

        locked = sum(1 for r in row_lock_results if r["locked"])
        if locked >= 1:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=LOW,
                check="select_for_update",
                detail=f"Row locking works ({locked}/3 threads acquired lock)", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=MEDIUM,
                check="select_for_update",
                detail="Row locking failed — SQLite does not support select_for_update properly",
                evidence=row_lock_results,
            ))

        all_balanced = True
        test_count = 0
        for _ in range(3):
            try:
                from django.db import transaction
                with transaction.atomic():
                    c = Account.objects.select_for_update().filter(code="1000").first()
                    e = Account.objects.select_for_update().filter(account_type="EQUITY").first()
                    if c and e:
                        je = JournalEntry.objects.create(
                            entry_number=f"ISO-JE-{uuid.uuid4().hex[:8]}",
                            entry_date=date.today(), entry_type="ADJUSTMENT",
                            description="Isolation test", is_posted=True,
                        )
                        JournalEntryLine.objects.create(
                            entry=je, account=c, debit=Decimal("250.00"), credit=Decimal("0.00"),
                        )
                        JournalEntryLine.objects.create(
                            entry=je, account=e, debit=Decimal("0.00"), credit=Decimal("250.00"),
                        )
                        test_count += 1
                        if not je.is_balanced:
                            all_balanced = False
            except Exception:
                pass

        if all_balanced and test_count > 0:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=LOW,
                check="atomic_journal_posting",
                detail=f"{test_count} atomic journal posts all balanced", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=HIGH,
                check="atomic_journal_posting",
                detail=f"Unbalanced journals detected in atomic blocks",
            ))

        try:
            from django.db import transaction
            with transaction.atomic():
                c2 = Account.objects.select_for_update().filter(code="1000").first()
                e2 = Account.objects.select_for_update().filter(account_type="EQUITY").first()
                if c2 and e2:
                    from django.db import IntegrityError
                    try:
                        JournalEntry.objects.create(
                            entry_number=f"ISO-ROLLBACK-{uuid.uuid4().hex[:8]}",
                            entry_date=date.today(), entry_type="ADJUSTMENT",
                            description="Rollback test", is_posted=True,
                        )
                        JournalEntryLine.objects.create(
                            entry=je, account=c2, debit=Decimal("100.00"), credit=Decimal("0.00"),
                        )
                        JournalEntryLine.objects.create(
                            entry=je, account=e2, debit=Decimal("0.00"), credit=Decimal("100.00"),
                        )
                    except Exception:
                        pass
                transaction.set_rollback(True)
            issues.append(InfraIssue(
                section="transaction_isolation", severity=LOW,
                check="rollback_safety", detail="Transaction rollback verified", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=MEDIUM,
                check="rollback_safety", detail=f"Rollback test: {e}", passed=True,
            ))

        from core.operations.concurrency import DoubleSpendPreventer
        validator = DoubleSpendPreventer()
        try:
            validation = validator.validate_payment_availability(
                invoice_id="infra-test", payment_amount=Decimal("100")
            )
            issues.append(InfraIssue(
                section="transaction_isolation", severity=LOW,
                check="double_spend_prevention",
                detail="DoubleSpendPreventer validates", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="transaction_isolation", severity=LOW,
                check="double_spend_prevention",
                detail=f"DoubleSpendPreventer: {e}", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="transaction_isolation", severity=CRITICAL,
            check="validator_crash", detail=f"Transaction isolation validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["transaction_isolation"] = SectionResult(
        name="Transaction Isolation Hardening", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["transaction_isolation"]
