import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db.models import Sum, Q
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.arap")


class ARAuditEngine:

    def __init__(self):
        self.module = AuditModule.ARAP

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        ar_balance = Decimal("0.00")
        ap_balance = Decimal("0.00")
        expected_ar = Decimal("0.00")
        expected_ap = Decimal("0.00")

        try:
            from accounting.models import Account, JournalEntryLine

            ar_accounts = Account.objects.filter(account_category="CURRENT_ASSET")
            ar_accounts_by_type = Account.objects.filter(
                account_type="ASSET",
                name__icontains="receivable",
            )
            combined_ar = list(ar_accounts) + [
                a for a in ar_accounts_by_type
                if a not in ar_accounts
            ]
            for acct in combined_ar:
                lines = JournalEntryLine.objects.filter(account=acct)
                for line in lines:
                    ar_balance += line.debit - line.credit

            ap_accounts = Account.objects.filter(account_category="CURRENT_LIABILITY")
            ap_accounts_by_type = Account.objects.filter(
                account_type="LIABILITY",
                name__icontains="payable",
            )
            combined_ap = list(ap_accounts) + [
                a for a in ap_accounts_by_type
                if a not in ap_accounts
            ]
            for acct in combined_ap:
                lines = JournalEntryLine.objects.filter(account=acct)
                for line in lines:
                    ap_balance += line.credit - line.debit

            try:
                from sales.models import SalesInvoice
                unpaid_sales = SalesInvoice.objects.filter(
                    ~Q(status="paid") | Q(status__isnull=True)
                )
                for inv in unpaid_sales:
                    expected_ar += inv.total_amount if hasattr(inv, "total_amount") else Decimal("0.00")
            except Exception:
                pass

            try:
                from purchases.models import PurchaseInvoice
                unpaid_purchases = PurchaseInvoice.objects.filter(
                    ~Q(status="paid") | Q(status__isnull=True)
                )
                for inv in unpaid_purchases:
                    expected_ap += inv.total_amount if hasattr(inv, "total_amount") else Decimal("0.00")
            except Exception:
                pass

            ar_divergence = ar_balance - expected_ar
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="ar_balance_reconciliation",
                passed=abs(ar_divergence) < Decimal("0.01"),
                detail=(
                    f"AR balance={ar_balance}, "
                    f"Expected from invoices={expected_ar}, "
                    f"Divergence={ar_divergence}"
                ),
                evidence={
                    "ar_balance": str(ar_balance),
                    "expected_ar": str(expected_ar),
                    "divergence": str(ar_divergence),
                },
            ))

            ap_divergence = ap_balance - expected_ap
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="ap_balance_reconciliation",
                passed=abs(ap_divergence) < Decimal("0.01"),
                detail=(
                    f"AP balance={ap_balance}, "
                    f"Expected from invoices={expected_ap}, "
                    f"Divergence={ap_divergence}"
                ),
                evidence={
                    "ap_balance": str(ap_balance),
                    "expected_ap": str(expected_ap),
                    "divergence": str(ap_divergence),
                },
            ))

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="ar_ap_summary",
                passed=True,
                detail=f"AR={ar_balance}, AP={ap_balance}, Net=(AR-AP)={ar_balance - ap_balance}",
                evidence={
                    "ar_balance": str(ar_balance),
                    "ap_balance": str(ap_balance),
                    "net_receivable": str(ar_balance - ap_balance),
                },
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="audit_execution",
                passed=False,
                detail=f"AR/AP audit failed: {e}",
            ))
            logger.error("AR/AP audit error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"AR={ar_balance}, AP={ap_balance}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )
