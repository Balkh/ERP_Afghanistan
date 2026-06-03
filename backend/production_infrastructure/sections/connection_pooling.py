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

"""SECTION: Connection Pooling — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from django.conf import settings

        db_config = settings.DATABASES["default"]
        conn_max_age = db_config.get("CONN_MAX_AGE", 0)
        if conn_max_age > 0:
            issues.append(InfraIssue(
                section="connection_pooling", severity=LOW,
                check="conn_max_age", detail=f"CONN_MAX_AGE={conn_max_age}s", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="connection_pooling", severity=MEDIUM,
                check="conn_max_age",
                detail="CONN_MAX_AGE=0. Set to 60-600s for connection reuse in production.",
            ))

        atomic = db_config.get("ATOMIC_REQUESTS", False)
        if atomic:
            issues.append(InfraIssue(
                section="connection_pooling", severity=LOW,
                check="atomic_requests", detail="ATOMIC_REQUESTS=True", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="connection_pooling", severity=MEDIUM,
                check="atomic_requests",
                detail="ATOMIC_REQUESTS not enabled. Partial writes risk on error.",
            ))

        concurrency_count = 0
        try:
            from core.operations.concurrency import ConcurrencyMonitor
            monitor = ConcurrencyMonitor()
            concurrency_count = monitor.active_count()
            issues.append(InfraIssue(
                section="connection_pooling", severity=LOW,
                check="concurrency_monitor", detail=f"Active transactions: {concurrency_count}", passed=True,
            ))
        except Exception:
            issues.append(InfraIssue(
                section="connection_pooling", severity=LOW,
                check="concurrency_monitor",
                detail="ConcurrencyMonitor not available — additive check skipped", passed=True,
            ))

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            issues.append(InfraIssue(
                section="connection_pooling", severity=LOW,
                check="connection_alive", detail="Database connection pool active", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="connection_pooling", severity=HIGH,
                check="connection_alive", detail=f"Connection failed: {e}",
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="connection_pooling", severity=CRITICAL,
            check="validator_crash", detail=f"Connection pooling validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["connection_pooling"] = SectionResult(
        name="Connection Pooling", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["connection_pooling"]
