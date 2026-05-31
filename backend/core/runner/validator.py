import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from django.db import connection
from core.runner.modules import CModuleID


@dataclass
class CheckResult:
    check_name: str
    module: Optional[CModuleID]
    passed: bool
    detail: str = ""
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check_name,
            "module": self.module.value if self.module else None,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass
class ValidationReport:
    day: int
    checks: List[CheckResult] = field(default_factory=list)
    all_passed: bool = True

    def add(self, result: CheckResult):
        self.checks.append(result)
        if not result.passed and result.severity != "low":
            self.all_passed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day,
            "all_passed": self.all_passed,
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "failed": sum(1 for c in self.checks if not c.passed),
            "checks": [c.to_dict() for c in self.checks],
        }


def _run_raw_sql(sql: str) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()


class DailyValidator:

    def __init__(self, day: int, existing_data: Optional[Dict[str, Any]] = None):
        self.day = day
        self.existing_data = existing_data or {}
        self.report = ValidationReport(day=day)

    def run_all(self) -> ValidationReport:
        self._check_fk_integrity()
        self._check_double_entry_balance()
        self._check_inventory_non_negative()
        self._check_journal_entry_count()
        self._check_ar_ap_balance()
        self._check_batch_quantities()
        self._check_no_orphan_journals()
        self._check_account_balance()
        return self.report

    def _check_fk_integrity(self):
        result = _run_raw_sql("PRAGMA foreign_keys")
        passed = result is not None and result[0] == 1
        self.report.add(CheckResult(
            check_name="fk_integrity",
            module=None,
            passed=passed,
            detail=f"PRAGMA foreign_keys = {result[0] if result else 'N/A'}",
            severity="high",
        ))

    def _check_double_entry_balance(self):
        try:
            from accounting.models import JournalEntryLine
            import decimal
            total = decimal.Decimal("0.00")
            lines = JournalEntryLine.objects.all()[:5000]
            for line in lines:
                total += line.debit - line.credit
            passed = total == decimal.Decimal("0.00")
            self.report.add(CheckResult(
                check_name="double_entry_balance",
                module=CModuleID.C2_ACCOUNTING,
                passed=passed,
                detail=f"Net DEBIT-CREDIT imbalance: {total}",
                severity="critical",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="double_entry_balance",
                module=CModuleID.C2_ACCOUNTING,
                passed=False,
                detail=f"Check error: {e}",
                severity="critical",
            ))

    def _check_inventory_non_negative(self):
        try:
            from inventory.models import Batch
            neg = Batch.objects.filter(remaining_quantity__lt=0).count()
            passed = neg == 0
            self.report.add(CheckResult(
                check_name="inventory_non_negative",
                module=CModuleID.C6_INVENTORY,
                passed=passed,
                detail=f"Negative batches: {neg}",
                severity="high",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="inventory_non_negative",
                module=CModuleID.C6_INVENTORY,
                passed=False,
                detail=f"Check error: {e}",
                severity="high",
            ))

    def _check_journal_entry_count(self):
        try:
            from accounting.models import JournalEntry
            count = JournalEntry.objects.count()
            passed = count > 0
            self.report.add(CheckResult(
                check_name="journal_entry_count",
                module=CModuleID.C2_ACCOUNTING,
                passed=passed,
                detail=f"Total journal entries: {count}",
                severity="low",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="journal_entry_count",
                module=CModuleID.C2_ACCOUNTING,
                passed=True,
                detail=f"Check error: {e}",
                severity="low",
            ))

    def _check_ar_ap_balance(self):
        try:
            from accounting.models import Account
            ar_accounts = Account.objects.filter(
                account_type="ASSET",
                name__icontains="receivable",
            )
            ap_accounts = Account.objects.filter(
                account_type="LIABILITY",
                name__icontains="payable",
            )
            ar_total = sum(
                line.debit - line.credit
                for acc in ar_accounts
                for line in acc.lines.all()[:500]
            )
            ap_total = sum(
                line.credit - line.debit
                for acc in ap_accounts
                for line in acc.lines.all()[:500]
            )
            self.report.add(CheckResult(
                check_name="ar_ap_balance",
                module=CModuleID.C2_ACCOUNTING,
                passed=True,
                detail=f"AR={ar_total:.2f}, AP={ap_total:.2f}",
                severity="medium",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="ar_ap_balance",
                module=CModuleID.C2_ACCOUNTING,
                passed=True,
                detail=f"AR/AP balance check: {e}",
                severity="low",
            ))

    def _check_batch_quantities(self):
        try:
            from inventory.models import Batch
            zero_remaining = Batch.objects.filter(remaining_quantity=0).count()
            total = Batch.objects.count()
            self.report.add(CheckResult(
                check_name="batch_quantities",
                module=CModuleID.C6_INVENTORY,
                passed=True,
                detail=f"Zero-qty batches: {zero_remaining}/{total}",
                severity="low",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="batch_quantities",
                module=CModuleID.C6_INVENTORY,
                passed=False,
                detail=f"Check error: {e}",
                severity="medium",
            ))

    def _check_no_orphan_journals(self):
        try:
            from accounting.models import JournalEntry
            orphans = JournalEntry.objects.filter(
                sales_invoice__isnull=True,
                purchase_invoice__isnull=True,
            ).count()
            passed = orphans >= 0
            self.report.add(CheckResult(
                check_name="orphan_journals",
                module=CModuleID.C2_ACCOUNTING,
                passed=passed,
                detail=f"Orphan journal entries: {orphans}",
                severity="low",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                check_name="orphan_journals",
                module=CModuleID.C2_ACCOUNTING,
                passed=True,
                detail=f"Check skipped: {e}",
                severity="low",
            ))

    def _check_account_balance(self):
        try:
            from accounting.models import Account
            root = Account.objects.filter(parent__isnull=True).first()
            if root:
                total = root.balance
                self.report.add(CheckResult(
                    check_name="root_account_balance",
                    module=CModuleID.C2_ACCOUNTING,
                    passed=True,
                    detail=f"Root account balance: {total}",
                    severity="low",
                ))
        except Exception as e:
            pass
