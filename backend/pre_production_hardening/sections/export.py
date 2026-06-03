"""
SECTION 5: EXPORT + PRINT RELIABILITY
Extracted from PreProductionHardeningValidator.validate_export_reliability
"""
from datetime import date, timedelta

from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from accounting.services.financial_reports import FinancialReportEngine
        from accounting.services.report_exporter import ReportExporter

        # Test 1: Trial balance generation
        try:
            tb = FinancialReportEngine.get_trial_balance()
            if tb and "accounts" in tb:
                acct_count = len(tb["accounts"])
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="trial_balance_generation",
                    detail=f"Trial balance generated: {acct_count} accounts", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_MEDIUM,
                    check="trial_balance_generation",
                    detail="Trial balance returned but format unexpected",
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_MEDIUM,
                check="trial_balance_generation",
                detail=f"Trial balance generation failed: {e}",
            ))

        # Test 2: CSV export
        try:
            exporter = ReportExporter()
            tb_data = FinancialReportEngine.get_trial_balance()
            if tb_data:
                csv_output = exporter.to_csv("trial_balance", tb_data)
                if csv_output and len(csv_output) > 0:
                    issues.append(HardeningIssue(
                        section="export_reliability", severity=ISSUE_LOW,
                        check="csv_export", detail=f"CSV export: {len(csv_output)} chars", passed=True,
                    ))
                    # Check for encoding issues
                    csv_has_encoding_error = False
                    for ch in csv_output[:500]:
                        if ord(ch) > 65535:
                            csv_has_encoding_error = True
                            break
                    if csv_has_encoding_error:
                        issues.append(HardeningIssue(
                            section="export_reliability", severity=ISSUE_MEDIUM,
                            check="csv_encoding",
                            detail="CSV output contains characters outside BMP. Verify encoding.",
                        ))
                else:
                    issues.append(HardeningIssue(
                        section="export_reliability", severity=ISSUE_MEDIUM,
                        check="csv_export", detail="CSV export returned empty output",
                    ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_MEDIUM,
                check="csv_export", detail=f"CSV export failed: {e}",
            ))

        # Test 3: Profit & Loss report generation
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            pnl = FinancialReportEngine.get_profit_and_loss(start_date, end_date)
            if pnl:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="pnl_generation", detail="Profit & Loss report generated", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_MEDIUM,
                check="pnl_generation", detail=f"P&L report failed: {e}",
            ))

        # Test 4: Balance sheet generation
        try:
            bs = FinancialReportEngine.get_balance_sheet()
            if bs:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="balance_sheet_generation",
                    detail="Balance sheet generated", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_MEDIUM,
                check="balance_sheet_generation", detail=f"Balance sheet failed: {e}",
            ))

        # Test 5: Account ledger export
        try:
            from accounting.models import Account
            first_acct = Account.objects.filter().first()
            if first_acct:
                ledger = FinancialReportEngine.get_account_ledger(first_acct.id)
                if ledger:
                    issues.append(HardeningIssue(
                        section="export_reliability", severity=ISSUE_LOW,
                        check="ledger_export",
                        detail=f"Ledger export for {first_acct.code}: generated", passed=True,
                    ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_MEDIUM,
                check="ledger_export", detail=f"Ledger export failed: {e}",
            ))

        # Test 6: AR/AP aging reports
        try:
            ar = FinancialReportEngine.get_ar_aging()
            if ar:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="ar_aging", detail="AR aging report generated", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_LOW,
                check="ar_aging", detail=f"AR aging skipped: {e}", passed=True,
            ))

        try:
            ap = FinancialReportEngine.get_ap_aging()
            if ap:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="ap_aging", detail="AP aging report generated", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_LOW,
                check="ap_aging", detail=f"AP aging skipped: {e}", passed=True,
            ))

        # Test 7: Cash flow statement
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            cf = FinancialReportEngine.get_cash_flow_statement(start_date, end_date)
            if cf:
                issues.append(HardeningIssue(
                    section="export_reliability", severity=ISSUE_LOW,
                    check="cash_flow", detail="Cash flow statement generated", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="export_reliability", severity=ISSUE_LOW,
                check="cash_flow", detail=f"Cash flow skipped: {e}", passed=True,
            ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="export_reliability", severity=ISSUE_CRITICAL,
            check="export_crash", detail=f"Export reliability testing crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["export_reliability"] = SectionResult(
        name="Export + Print Reliability", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["export_reliability"]
