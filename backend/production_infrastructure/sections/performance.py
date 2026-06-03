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

"""SECTION: Performance Validation — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from accounting.models import JournalEntry, JournalEntryLine, Account
        from inventory.models import Batch

        start = time.time()
        j_count = JournalEntry.objects.count()
        lines = list(JournalEntryLine.objects.all()[:5000])
        j_time = time.time() - start
        issues.append(InfraIssue(
            section="performance_validation", severity=LOW,
            check="journal_query", detail=f"{j_count} JEs, {len(lines)} lines in {j_time:.3f}s", passed=True,
        ))

        start = time.time()
        accts = list(Account.objects.all())
        for a in accts:
            _ = a.balance
        bal_time = time.time() - start
        threshold = 5.0
        if bal_time < threshold:
            issues.append(InfraIssue(
                section="performance_validation", severity=LOW,
                check="balance_aggregation",
                detail=f"{len(accts)} balances in {bal_time:.3f}s", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="performance_validation", severity=MEDIUM,
                check="balance_aggregation",
                detail=f"Slow: {len(accts)} balances in {bal_time:.3f}s ({threshold}s threshold)",
            ))

        start = time.time()
        from accounting.services.financial_reports import FinancialReportEngine
        tb = FinancialReportEngine.get_trial_balance()
        tb_time = time.time() - start
        if tb_time < 8.0:
            issues.append(InfraIssue(
                section="performance_validation", severity=LOW,
                check="trial_balance", detail=f"TB in {tb_time:.3f}s", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="performance_validation", severity=MEDIUM,
                check="trial_balance", detail=f"Slow TB: {tb_time:.3f}s",
            ))

        start = time.time()
        batches = list(Batch.objects.all().select_related("product")[:2000])
        inv_time = time.time() - start
        issues.append(InfraIssue(
            section="performance_validation", severity=LOW,
            check="inventory_query", detail=f"{len(batches)} batches in {inv_time:.3f}s", passed=True,
        ))

        read_results = []
        rl = threading.Lock()

        def concurrent_read(tid: int):
            try:
                list(JournalEntry.objects.all()[:100])
                list(JournalEntryLine.objects.all()[:300])
                with rl:
                    read_results.append(tid)
            except Exception:
                pass

        threads = []
        for i in range(5):
            t = threading.Thread(target=concurrent_read, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=10)

        if len(read_results) >= 4:
            issues.append(InfraIssue(
                section="performance_validation", severity=LOW,
                check="concurrent_reads",
                detail=f"{len(read_results)}/5 concurrent readers OK", passed=True,
            ))

        from django.core.paginator import Paginator
        all_journals = JournalEntry.objects.all().order_by("-entry_date")
        paginator = Paginator(all_journals, 50)
        if paginator.num_pages >= 1:
            issues.append(InfraIssue(
                section="performance_validation", severity=LOW,
                check="pagination", detail=f"{paginator.num_pages} pages, 50/page", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="performance_validation", severity=CRITICAL,
            check="validator_crash", detail=f"Performance validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["performance_validation"] = SectionResult(
        name="Performance Validation", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["performance_validation"]
