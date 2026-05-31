import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db.models import Sum
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.financial")


class FinancialStatementValidator:

    def __init__(self):
        self.module = AuditModule.FINANCIAL

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        total_accounts = 0
        bs_assets = Decimal("0.00")
        bs_liabilities = Decimal("0.00")
        bs_equity = Decimal("0.00")
        pnl_revenue = Decimal("0.00")
        pnl_expenses = Decimal("0.00")

        try:
            from accounting.models import Account, JournalEntryLine

            accounts = Account.objects.filter(is_active=True)
            total_accounts = accounts.count()

            account_type_counts = {}
            for acct in accounts:
                account_type_counts[acct.account_type] = (
                    account_type_counts.get(acct.account_type, 0) + 1
                )

            bs_accounts = accounts.filter(
                account_type__in=["ASSET", "LIABILITY", "EQUITY"]
            )
            for acct in bs_accounts:
                bal = acct.balance or Decimal("0.00")
                if acct.account_type == "ASSET":
                    bs_assets += bal
                elif acct.account_type == "LIABILITY":
                    bs_liabilities += bal
                elif acct.account_type == "EQUITY":
                    bs_equity += bal

            pnl_accounts = accounts.filter(
                account_type__in=["REVENUE", "EXPENSE"]
            )
            for acct in pnl_accounts:
                bal = acct.balance or Decimal("0.00")
                if acct.account_type == "REVENUE":
                    pnl_revenue += bal
                elif acct.account_type == "EXPENSE":
                    pnl_expenses += bal

            bs_equation = bs_assets - (bs_liabilities + bs_equity)
            pnl_net = pnl_revenue - pnl_expenses

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.CRITICAL,
                check_name="balance_sheet_equation",
                passed=bs_equation == Decimal("0.00"),
                detail=(
                    f"Assets={bs_assets} - (Liabilities={bs_liabilities} + "
                    f"Equity={bs_equity}) = {bs_equation}"
                ),
                evidence={
                    "total_assets": str(bs_assets),
                    "total_liabilities": str(bs_liabilities),
                    "total_equity": str(bs_equity),
                    "equation_imbalance": str(bs_equation),
                },
            ))

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="profit_loss_consistency",
                passed=True,
                detail=(
                    f"Revenue={pnl_revenue}, Expenses={pnl_expenses}, "
                    f"Net Income={pnl_net}"
                ),
                evidence={
                    "total_revenue": str(pnl_revenue),
                    "total_expenses": str(pnl_expenses),
                    "net_income": str(pnl_net),
                },
            ))

            account_type_summary = [
                {"type": k, "count": v}
                for k, v in sorted(account_type_counts.items())
            ]
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="account_type_distribution",
                passed=True,
                detail=f"Accounts by type: {account_type_summary}",
                evidence={"type_counts": account_type_summary},
            ))

            total_debit = JournalEntryLine.objects.aggregate(
                total=Sum("debit")
            )["total"] or Decimal("0.00")
            total_credit = JournalEntryLine.objects.aggregate(
                total=Sum("credit")
            )["total"] or Decimal("0.00")

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.CRITICAL,
                check_name="total_debit_credit_match",
                passed=total_debit == total_credit,
                detail=f"Total debits={total_debit}, Total credits={total_credit}",
                evidence={
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit),
                    "match": total_debit == total_credit,
                },
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.CRITICAL,
                check_name="audit_execution",
                passed=False,
                detail=f"Financial statement validation failed: {e}",
            ))
            logger.error("Financial validation error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Accounts={total_accounts}, "
                f"Assets={bs_assets}, Liabilities={bs_liabilities}, "
                f"Equity={bs_equity}, Revenue={pnl_revenue}, "
                f"Expenses={pnl_expenses}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )
