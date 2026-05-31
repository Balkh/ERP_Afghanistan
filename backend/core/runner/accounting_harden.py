import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("c_runner.accounting")


@dataclass
class TrialBalanceEntry:
    account_code: str
    account_name: str
    debit_total: float
    credit_total: float
    balance: float


@dataclass
class TrialBalanceReport:
    day: int
    entries: List[TrialBalanceEntry] = field(default_factory=list)
    total_debits: float = 0.0
    total_credits: float = 0.0
    balanced: bool = True
    detail: str = ""


@dataclass
class LedgerDriftRecord:
    drift_type: str
    module: str
    detail: str
    severity: str = "medium"


class DailyTrialBalanceValidator:

    def validate(self, day: int) -> TrialBalanceReport:
        report = TrialBalanceReport(day=day)
        total_debits = 0.0
        total_credits = 0.0

        try:
            from accounting.models import Account, JournalEntryLine
            import decimal
            accounts = Account.objects.filter(parent__isnull=False)[:200]
            for acc in accounts:
                debit_sum = decimal.Decimal("0.00")
                credit_sum = decimal.Decimal("0.00")
                lines = JournalEntryLine.objects.filter(account=acc)[:1000]
                for line in lines:
                    debit_sum += line.debit
                    credit_sum += line.credit
                d = float(debit_sum)
                c = float(credit_sum)
                report.entries.append(TrialBalanceEntry(
                    account_code=acc.code or "",
                    account_name=acc.name,
                    debit_total=round(d, 2),
                    credit_total=round(c, 2),
                    balance=round(d - c, 2),
                ))
                total_debits += d
                total_credits += c

            report.total_debits = round(total_debits, 2)
            report.total_credits = round(total_credits, 2)
            diff = abs(total_debits - total_credits)
            report.balanced = diff < 0.01
            report.detail = (f"Balanced" if report.balanced
                             else f"Imbalance: {diff:.2f}")

        except Exception as e:
            report.balanced = False
            report.detail = str(e)

        return report


class LedgerDriftMonitor:

    def __init__(self):
        self._records: List[LedgerDriftRecord] = []

    def check_drift(self) -> List[LedgerDriftRecord]:
        self._records.clear()

        try:
            from accounting.models import JournalEntryLine
            import decimal
            total = decimal.Decimal("0.00")
            count = 0
            for line in JournalEntryLine.objects.iterator():
                total += line.debit - line.credit
                count += 1
            drift = float(total)
            if abs(drift) > 0.001:
                self._records.append(LedgerDriftRecord(
                    drift_type="ledger_imbalance",
                    module="c2_accounting",
                    detail=f"Net imbalance: {drift:.4f} over {count} lines",
                    severity="critical",
                ))
            else:
                logger.info("[DRIFT] Ledger balanced: %.6f (%d lines)", drift, count)
        except Exception as e:
            self._records.append(LedgerDriftRecord(
                drift_type="ledger_check_error",
                module="c2_accounting",
                detail=str(e),
                severity="high",
            ))

        try:
            from inventory.models import Batch
            neg = Batch.objects.filter(remaining_quantity__lt=0).count()
            if neg > 0:
                self._records.append(LedgerDriftRecord(
                    drift_type="negative_inventory",
                    module="c6_inventory",
                    detail=f"{neg} batches with negative quantity",
                    severity="high",
                ))
        except Exception as e:
            pass

        return self._records

    @property
    def has_drift(self) -> bool:
        return len(self._records) > 0

    @property
    def critical_drift(self) -> bool:
        return any(r.severity == "critical" for r in self._records)


class StrictDoubleEntryEnforcer:

    def enforce(self) -> Dict[str, Any]:
        try:
            from accounting.models import JournalEntryLine
            import decimal
            total = decimal.Decimal("0.00")
            for line in JournalEntryLine.objects.iterator():
                total += line.debit - line.credit
            balanced = total == decimal.Decimal("0.00")
            return {
                "enforced": True,
                "balanced": balanced,
                "imbalance": str(total),
                "lines_scanned": JournalEntryLine.objects.count(),
            }
        except Exception as e:
            return {
                "enforced": False,
                "balanced": False,
                "error": str(e),
            }
