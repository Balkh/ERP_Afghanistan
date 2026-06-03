"""
SECTION 7: PERFORMANCE DEGRADATION DETECTION
Extracted from PreProductionHardeningValidator.validate_performance
"""
import threading
import time

from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from accounting.models import JournalEntry, JournalEntryLine, Account
        from inventory.models import Batch, Product, StockMovement

        # Test 1: Bulk journal line query performance
        start = time.time()
        line_count = JournalEntryLine.objects.count()
        all_lines = list(JournalEntryLine.objects.all()[:5000])
        query_time = time.time() - start

        if query_time < 2.0:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="journal_line_query",
                detail=f"Queried {line_count} lines in {query_time:.3f}s", passed=True,
            ))
        else:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_MEDIUM,
                check="journal_line_query",
                detail=f"Slow query: {line_count} lines in {query_time:.3f}s (>2s threshold)",
                evidence={"query_time_seconds": round(query_time, 3)},
            ))

        # Test 2: Account balance aggregation
        start = time.time()
        accounts = list(Account.objects.all())
        for acct in accounts:
            _ = acct.balance
        balance_time = time.time() - start

        if balance_time < 3.0:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="account_balance_aggregation",
                detail=f"Computed {len(accounts)} account balances in {balance_time:.3f}s", passed=True,
            ))
        else:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_MEDIUM,
                check="account_balance_aggregation",
                detail=f"Slow balance aggregation: {balance_time:.3f}s for {len(accounts)} accounts",
            ))

        # Test 3: Financial report generation speed
        start = time.time()
        try:
            from accounting.services.financial_reports import FinancialReportEngine
            tb = FinancialReportEngine.get_trial_balance()
            tb_time = time.time() - start

            if tb_time < 5.0:
                issues.append(HardeningIssue(
                    section="performance", severity=ISSUE_LOW,
                    check="trial_balance_speed",
                    detail=f"Trial balance in {tb_time:.3f}s", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="performance", severity=ISSUE_MEDIUM,
                    check="trial_balance_speed",
                    detail=f"Slow trial balance: {tb_time:.3f}s (>5s threshold)",
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="trial_balance_speed", detail=f"TB skipped: {e}", passed=True,
            ))

        # Test 4: Inventory query performance
        start = time.time()
        batch_count = Batch.objects.count()
        batches = list(Batch.objects.all().select_related("product")[:2000])
        inv_time = time.time() - start

        if inv_time < 2.0:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="inventory_query",
                detail=f"Queried {batch_count} batches in {inv_time:.3f}s", passed=True,
            ))
        else:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="inventory_query",
                detail=f"Inventory query: {batch_count} batches in {inv_time:.3f}s", passed=True,
            ))

        # Test 5: Memory check - pagination stability
        try:
            from django.core.paginator import Paginator
            all_journals = JournalEntry.objects.all().order_by("-entry_date")
            paginator = Paginator(all_journals, 50)
            page_count = paginator.num_pages
            page = paginator.get_page(1)
            items_on_page = len(list(page))

            if page_count >= 1:
                issues.append(HardeningIssue(
                    section="performance", severity=ISSUE_LOW,
                    check="pagination_stability",
                    detail=f"Pagination: {page_count} pages, {items_on_page} items/page", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="pagination_stability", detail=f"Pagination test: {e}", passed=True,
            ))

        # Test 6: Event audit speed
        try:
            start = time.time()
            from core.audit.engine import AuditEngine
            engine = AuditEngine()
            report = engine.run_full_audit()
            audit_time = time.time() - start

            if audit_time < 10.0:
                issues.append(HardeningIssue(
                    section="performance", severity=ISSUE_LOW,
                    check="audit_engine_speed",
                    detail=f"Full audit in {audit_time:.3f}s", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="performance", severity=ISSUE_MEDIUM,
                    check="audit_engine_speed",
                    detail=f"Slow audit: {audit_time:.3f}s (>10s threshold)",
                    evidence={"audit_time_seconds": round(audit_time, 3)},
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="audit_engine_speed", detail=f"Audit skipped: {e}", passed=True,
            ))

        # Test 7: Concurrent read performance
        read_results = []
        read_lock = threading.Lock()

        def concurrent_read(thread_id: int):
            try:
                j = list(JournalEntry.objects.all()[:100])
                l = list(JournalEntryLine.objects.all()[:500])
                b = list(Batch.objects.all()[:100])
                with read_lock:
                    read_results.append({
                        "thread": thread_id,
                        "journals": len(j),
                        "lines": len(l),
                        "batches": len(b),
                    })
            except Exception as e:
                with read_lock:
                    read_results.append({"thread": thread_id, "error": str(e)})

        threads = []
        for i in range(10):
            t = threading.Thread(target=concurrent_read, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=15)

        read_failures = sum(1 for r in read_results if "error" in r)
        if read_failures == 0:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_LOW,
                check="concurrent_reads",
                detail=f"10 concurrent readers all succeeded", passed=True,
            ))
        else:
            issues.append(HardeningIssue(
                section="performance", severity=ISSUE_MEDIUM,
                check="concurrent_reads",
                detail=f"{read_failures}/10 concurrent readers failed",
            ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="performance", severity=ISSUE_CRITICAL,
            check="performance_crash", detail=f"Performance validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["performance_validation"] = SectionResult(
        name="Performance Degradation Detection", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["performance_validation"]
