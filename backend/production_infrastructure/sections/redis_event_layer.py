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

"""SECTION: Redis + Event Execution Layer — extracted from migration_validator.py
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

        cache_backend = settings.CACHES["default"]["BACKEND"]
        issues.append(InfraIssue(
            section="redis_event_layer", severity=LOW,
            check="cache_backend", detail=f"Cache backend: {cache_backend}", passed=True,
        ))

        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            issues.append(InfraIssue(
                section="redis_event_layer", severity=LOW,
                check="redis_url", detail="REDIS_URL configured", passed=True,
            ))
            try:
                import redis as redis_client
                r = redis_client.Redis.from_url(redis_url)
                r.ping()
                issues.append(InfraIssue(
                    section="redis_event_layer", severity=LOW,
                    check="redis_connection", detail="Redis connection verified", passed=True,
                ))
            except Exception as e:
                issues.append(InfraIssue(
                    section="redis_event_layer", severity=HIGH,
                    check="redis_connection", detail=f"Redis connection failed: {e}",
                ))
        else:
            issues.append(InfraIssue(
                section="redis_event_layer", severity=MEDIUM,
                check="redis_url", detail="REDIS_URL not set. Using local-memory cache.",
            ))

        from config.celery import celery_available, get_celery_app
        if celery_available:
            app = get_celery_app()
            issues.append(InfraIssue(
                section="redis_event_layer", severity=LOW,
                check="celery_app", detail="Celery app configured", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="redis_event_layer", severity=MEDIUM,
                check="celery_app",
                detail="Celery not installed. Install: pip install celery[redis]",
            ))

        try:
            from core.runner.event_reliability import IdempotencyChecker
            from core.runner.modules import CModuleID
            from core.runner.workload_generator import BusinessEvent
            checker = IdempotencyChecker()
            event = BusinessEvent(
                module=CModuleID.C5_SALES, event_type="create_sale",
                payload={"id": 1},
            )
            not_dup = not checker.is_duplicate(event)
            checker.mark_seen(event)
            is_dup = checker.is_duplicate(event)
            checker.clear()
            if not_dup and is_dup:
                issues.append(InfraIssue(
                    section="redis_event_layer", severity=LOW,
                    check="idempotency", detail="Event idempotency verified", passed=True,
                ))
            else:
                issues.append(InfraIssue(
                    section="redis_event_layer", severity=HIGH,
                    check="idempotency", detail="Idempotency check failed",
                ))
        except Exception as e:
            issues.append(InfraIssue(
                section="redis_event_layer", severity=MEDIUM,
                check="idempotency", detail=f"Idempotency test: {e}",
            ))

        try:
            from config.tasks import tasks_registered
            if tasks_registered:
                issues.append(InfraIssue(
                    section="redis_event_layer", severity=LOW,
                    check="task_definitions",
                    detail="Background tasks registered (report, export, snapshot, audit, backup)",
                    passed=True,
                ))
        except Exception:
            issues.append(InfraIssue(
                section="redis_event_layer", severity=LOW,
                check="task_definitions",
                detail="Task definitions skipped (Celery not installed)", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="redis_event_layer", severity=CRITICAL,
            check="validator_crash", detail=f"Redis/event layer validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["redis_event_layer"] = SectionResult(
        name="Redis + Event Execution Layer", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["redis_event_layer"]
