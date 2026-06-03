"""SECTION: Long-run Stability — extracted from gate_validator.py
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


def _cleanup_gate_data(self):
    """Remove test data created by previous gate sections to avoid false validation failures."""
    from accounting.models import JournalEntry, JournalEntryLine
    from inventory.models import Batch, StockMovement
    JournalEntryLine.objects.filter(entry__entry_number__startswith="GATE-").delete()
    JournalEntry.objects.filter(entry_number__startswith="GATE-").delete()
    StockMovement.objects.filter(reference_type__startswith="GATE-").delete()
    Batch.objects.filter(batch_number__startswith="BATCH-GATE-").delete()


def run(self) -> SectionResult:
    issues = []
    try:
        from core.runner.engine import CRunnerEngine

        _cleanup_gate_data(self)

        engine = CRunnerEngine.get_instance()
        engine.configure(start_day=1, end_day=180, seed=42)

        start = time.time()
        report = engine.run()
        duration = time.time() - start

        days_run = report.get("days_completed", 0)
        verdict = report.get("verdict", "UNKNOWN")
        stats = report.get("stats", {})
        events = stats.get("events_dispatched", 0)
        snapshots = stats.get("snapshots", 0)

        if "ALL_PASS" not in str(verdict):
            issues.append(GateIssue(
                section="long_run", severity=ISSUE_CRITICAL,
                check="simulation_completion",
                detail=f"180-day simulation verdict: {verdict}",
                evidence={"days": days_run, "verdict": verdict},
            ))

        if days_run < 180:
            issues.append(GateIssue(
                section="long_run", severity=ISSUE_HIGH,
                check="days_completed",
                detail=f"Only {days_run}/180 days completed",
            ))

        if duration > 30:
            issues.append(GateIssue(
                section="long_run", severity=ISSUE_MEDIUM,
                check="performance",
                detail=f"180 days took {duration:.1f}s",
                evidence={"duration_seconds": round(duration, 2)},
            ))

        issues.append(GateIssue(
            section="long_run", severity=ISSUE_LOW,
            check="180_day_simulation",
            detail=f"180-day: {days_run}d, {events} events, {snapshots} snapshots, {duration:.1f}s",
            passed=True,
        ))

    except Exception as e:
        issues.append(GateIssue(
            section="long_run", severity=ISSUE_CRITICAL,
            check="simulation_execution", detail=f"180-day run crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    self.results["long_run_validation"] = SectionResult(
        name="Long-Run Operational Validation",
        passed=passed,
        issues=issues,
        detail=f"180-day simulation completed",
    )
    self.issues.extend(issues)
    return self.results["long_run_validation"]
