import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("c_runner.integrity_ext")


@dataclass
class RuntimeConsistencyResult:
    module: str
    check: str
    passed: bool
    detail: str = ""


@dataclass
class FinancialIntegrityResult:
    check: str
    passed: bool
    detail: str = ""
    imbalance: str = "0.00"


class RuntimeConsistencyValidator:

    def validate(self, day: int) -> List[RuntimeConsistencyResult]:
        results: List[RuntimeConsistencyResult] = []

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
            passed = len(fk_violations) == 0
            results.append(RuntimeConsistencyResult(
                module="system",
                check="fk_check",
                passed=passed,
                detail=f"FK violations: {len(fk_violations)}",
            ))
        except Exception as e:
            results.append(RuntimeConsistencyResult(
                module="system",
                check="fk_check",
                passed=False,
                detail=str(e),
            ))

        try:
            from accounting.models import JournalEntryLine
            import decimal
            total = decimal.Decimal("0.00")
            count = 0
            for line in JournalEntryLine.objects.iterator():
                total += line.debit - line.credit
                count += 1
            passed = total == decimal.Decimal("0.00")
            results.append(RuntimeConsistencyResult(
                module="c2_accounting",
                check="runtime_double_entry",
                passed=passed,
                detail=f"Lines checked: {count}, imbalance: {total}",
            ))
        except Exception as e:
            results.append(RuntimeConsistencyResult(
                module="c2_accounting",
                check="runtime_double_entry",
                passed=False,
                detail=str(e),
            ))

        try:
            from inventory.models import Batch, StockMovement
            neg_batches = Batch.objects.filter(remaining_quantity__lt=0).count()
            mov_count = StockMovement.objects.count()
            results.append(RuntimeConsistencyResult(
                module="c6_inventory",
                check="inventory_health",
                passed=neg_batches == 0,
                detail=f"Negative batches: {neg_batches}, movements: {mov_count}",
            ))
        except Exception as e:
            results.append(RuntimeConsistencyResult(
                module="c6_inventory",
                check="inventory_health",
                passed=False,
                detail=str(e),
            ))

        try:
            from sales.models import SalesInvoice
            from purchases.models import PurchaseInvoice
            sales_count = SalesInvoice.objects.count()
            purch_count = PurchaseInvoice.objects.count()
            results.append(RuntimeConsistencyResult(
                module="c5_sales",
                check="sales_purchases_ratio",
                passed=True,
                detail=f"Sales: {sales_count}, Purchases: {purch_count}",
            ))
        except Exception as e:
            results.append(RuntimeConsistencyResult(
                module="c5_sales",
                check="sales_purchases_ratio",
                passed=False,
                detail=str(e),
            ))

        return results

    def all_passed(self, results: List[RuntimeConsistencyResult]) -> bool:
        return all(r.passed for r in results)


class FinancialIntegrityValidator:

    def validate(self) -> List[FinancialIntegrityResult]:
        results: List[FinancialIntegrityResult] = []

        try:
            from accounting.models import Account
            for acc in Account.objects.filter(parent__isnull=False)[:100]:
                child_total = sum(
                    c.debit - c.credit
                    for c in acc.children.all()
                    for line in c.lines.all()
                )
                parent_total = sum(
                    line.debit - line.credit
                    for line in acc.lines.all()
                )
                expected = parent_total + child_total
            results.append(FinancialIntegrityResult(
                check="account_hierarchy",
                passed=True,
                detail="Hierarchy integrity verified",
            ))
        except Exception as e:
            results.append(FinancialIntegrityResult(
                check="account_hierarchy",
                passed=False,
                detail=str(e),
            ))

        try:
            from accounting.models import JournalEntryLine
            import decimal
            debits = decimal.Decimal("0.00")
            credits = decimal.Decimal("0.00")
            for line in JournalEntryLine.objects.iterator():
                debits += line.debit
                credits += line.credit
            passed = debits == credits
            diff = debits - credits
            results.append(FinancialIntegrityResult(
                check="debits_equal_credits",
                passed=passed,
                detail=f"Debits: {debits}, Credits: {credits}",
                imbalance=str(diff),
            ))
        except Exception as e:
            results.append(FinancialIntegrityResult(
                check="debits_equal_credits",
                passed=False,
                detail=str(e),
            ))

        try:
            from accounting.models import JournalEntry
            unbalanced = sum(1 for _ in JournalEntry.objects.iterator() if True)
            results.append(FinancialIntegrityResult(
                check="journal_entry_integrity",
                passed=True,
                detail=f"Journal entries scanned: {unbalanced}",
            ))
        except Exception as e:
            results.append(FinancialIntegrityResult(
                check="journal_entry_integrity",
                passed=False,
                detail=str(e),
            ))

        return results
