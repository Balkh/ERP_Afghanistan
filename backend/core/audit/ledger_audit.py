import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db import connection, models
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.ledger")


class LedgerAuditEngine:

    def __init__(self):
        self.module = AuditModule.LEDGER

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        total_entries = 0
        total_lines = 0
        imbalanced_entries = 0
        total_imbalance = Decimal("0.00")

        try:
            from accounting.models import JournalEntry, JournalEntryLine
            from django.db.models import Sum

            entries = JournalEntry.objects.all()
            total_entries = entries.count()

            global_sum = JournalEntryLine.objects.aggregate(
                total_debit=Sum("debit"),
                total_credit=Sum("credit"),
            )
            total_debit = global_sum["total_debit"] or Decimal("0.00")
            total_credit = global_sum["total_credit"] or Decimal("0.00")
            total_lines = JournalEntryLine.objects.count()
            total_imbalance = total_debit - total_credit

            for entry in entries:
                entry_total = entry.lines.aggregate(
                    d=Sum("debit"), c=Sum("credit"),
                )
                if entry_total["d"] != entry_total["c"]:
                    imbalanced_entries += 1
                    findings.append(AuditFinding(
                        module=module,
                        severity=AuditSeverity.CRITICAL,
                        check_name="entry_balance",
                        passed=False,
                        detail=f"Entry {entry.entry_number}: debit={entry_total['d']}, credit={entry_total['c']}",
                        evidence={
                            "entry_id": str(entry.id),
                            "entry_number": entry.entry_number,
                            "debit": str(entry_total["d"]),
                            "credit": str(entry_total["c"]),
                        },
                    ))

            global_balanced = total_imbalance == Decimal("0.00")
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.CRITICAL,
                check_name="global_double_entry_balance",
                passed=global_balanced,
                detail=(
                    f"Net DEBIT-CREDIT imbalance: {total_imbalance} "
                    f"(debits={total_debit}, credits={total_credit}, "
                    f"entries={total_entries}, lines={total_lines})"
                ),
                evidence={
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit),
                    "net_imbalance": str(total_imbalance),
                    "total_entries": total_entries,
                    "total_lines": total_lines,
                },
            ))

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="imbalanced_entry_count",
                passed=imbalanced_entries == 0,
                detail=f"Entries with imbalance: {imbalanced_entries}/{total_entries}",
                evidence={
                    "imbalanced_entries": imbalanced_entries,
                    "total_entries": total_entries,
                },
            ))

            entry_types = list(JournalEntry.objects.values("entry_type").annotate(
                count=models.Count("id"),
                total_debit=Sum("lines__debit"),
                total_credit=Sum("lines__credit"),
            ))
            for et in entry_types:
                et_imbalance = (et["total_debit"] or Decimal("0.00")) - (et["total_credit"] or Decimal("0.00"))
                if et_imbalance != Decimal("0.00"):
                    findings.append(AuditFinding(
                        module=module,
                        severity=AuditSeverity.HIGH,
                        check_name=f"type_balance_{et['entry_type']}",
                        passed=False,
                        detail=f"Entry type {et['entry_type']}: balance={et_imbalance} ({et['count']} entries)",
                        evidence={
                            "entry_type": et["entry_type"],
                            "count": et["count"],
                            "imbalance": str(et_imbalance),
                        },
                    ))

            duplicate_entry_numbers = (
                JournalEntry.objects.values("entry_number")
                .annotate(cnt=models.Count("id"))
                .filter(cnt__gt=1)
            )
            dup_count = duplicate_entry_numbers.count()
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="duplicate_entry_numbers",
                passed=dup_count == 0,
                detail=f"Duplicate entry numbers: {dup_count}",
                evidence={"duplicates": dup_count},
            ))

            orphan_lines = JournalEntryLine.objects.filter(
                debit=Decimal("0.00"), credit=Decimal("0.00")
            ).count()
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="zero_value_lines",
                passed=orphan_lines == 0,
                detail=f"Lines with zero debit and credit: {orphan_lines}",
                evidence={"zero_lines": orphan_lines},
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.CRITICAL,
                check_name="audit_execution",
                passed=False,
                detail=f"Ledger audit failed: {e}",
            ))
            logger.error("Ledger audit error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )
        total_imbalance_str = str(total_imbalance)
        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Entries={total_entries}, Lines={total_lines}, "
                f"Imbalance={total_imbalance_str}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )
