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

"""SECTION: Celery Background Execution — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from config.celery import celery_available, async_task

        if celery_available:
            issues.append(InfraIssue(
                section="celery_execution", severity=LOW,
                check="celery_available", detail="Celery is installed and configured", passed=True,
            ))
            try:
                from config.tasks import (
                    generate_report_task, export_csv_task,
                    take_snapshot_task, run_audit_task, rotate_backups_task,
                )
                issues.append(InfraIssue(
                    section="celery_execution", severity=LOW,
                    check="task_registration",
                    detail="All 5 background tasks registered", passed=True,
                ))
            except Exception as e:
                issues.append(InfraIssue(
                    section="celery_execution", severity=MEDIUM,
                    check="task_registration", detail=f"Task registration issue: {e}",
                ))
        else:
            issues.append(InfraIssue(
                section="celery_execution", severity=MEDIUM,
                check="celery_available",
                detail="Celery not installed. Production requires: pip install celery[redis]",
            ))

        try:
            from config.celery import get_celery_app
            app = get_celery_app()
            if app:
                registered = app.tasks.keys() if hasattr(app, 'tasks') else []
                issues.append(InfraIssue(
                    section="celery_execution", severity=LOW,
                    check="app_ready", detail="Celery app initialized", passed=True,
                ))
        except Exception:
            pass

        from security.rate_limiter import RateLimitMiddleware
        has_rate_limiter = True
        try:
            from django.conf import settings
            middleware = getattr(settings, "MIDDLEWARE", [])
            has_rate_limiter = any("RateLimit" in m for m in middleware)
            if has_rate_limiter:
                issues.append(InfraIssue(
                    section="celery_execution", severity=LOW,
                    check="rate_limiter", detail="Rate limiting middleware active", passed=True,
                ))
        except Exception:
            pass

    except Exception as e:
        issues.append(InfraIssue(
            section="celery_execution", severity=CRITICAL,
            check="validator_crash", detail=f"Celery validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["celery_execution"] = SectionResult(
        name="Celery Background Execution", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["celery_execution"]
