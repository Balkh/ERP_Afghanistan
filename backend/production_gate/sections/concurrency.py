"""SECTION: Concurrency + Stress Testing — extracted from gate_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
import importlib
import logging
import os
import sys
import json
import time
import threading
import hashlib
import uuid
from decimal import Decimal
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from production_gate.gate_validator import (
    GateIssue, SectionResult, ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW, logger,
)


def run(self) -> SectionResult:
    issues = []
    results_lock = threading.Lock()

    def _concurrent_invoice_create(invoice_id: int, results: list):
        try:
            from accounting.models import Account, JournalEntry, JournalEntryLine
            from decimal import Decimal
            cash = Account.objects.filter(code="1000").first()
            revenue = Account.objects.filter(account_type="REVENUE").first()
            if cash and revenue:
                je = JournalEntry.objects.create(
                    entry_number=f"CONC-{invoice_id}-{uuid.uuid4().hex[:6]}",
                    entry_date=date.today(), entry_type="SALE",
                    description=f"Concurrent test {invoice_id}", is_posted=True,
                )
                JournalEntryLine.objects.create(
                    entry=je, account=cash, debit=Decimal("100.00"), credit=Decimal("0.00"),
                )
                JournalEntryLine.objects.create(
                    entry=je, account=revenue, debit=Decimal("0.00"), credit=Decimal("100.00"),
                )
                with results_lock:
                    results.append(je.is_balanced)
        except Exception as e:
            with results_lock:
                results.append(False)
                issues.append(GateIssue(
                    section="concurrency", severity=ISSUE_MEDIUM,
                    check=f"concurrent_invoice_{invoice_id}",
                    detail=f"Concurrent invoice {invoice_id} error: {e}",
                ))

    threads = []
    results = []
    for i in range(20):
        t = threading.Thread(target=_concurrent_invoice_create, args=(i, results))
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=5)

    unbalanced = sum(1 for r in results if not r)
    if unbalanced > 0:
        issues.append(GateIssue(
            section="concurrency", severity=ISSUE_HIGH,
            check="concurrent_invoice_creation",
            detail=f"{unbalanced}/{len(results)} concurrent invoices unbalanced",
            evidence={"total": len(results), "unbalanced": unbalanced},
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    self.results["concurrency_validation"] = SectionResult(
        name="Concurrency + Stress Testing",
        passed=passed,
        issues=issues,
        detail=f"20 concurrent invoice threads, {len(results)} completed, {unbalanced} unbalanced",
    )
    self.issues.extend(issues)
    return self.results["concurrency_validation"]
