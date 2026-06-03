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

"""SECTION: Observability + Monitoring — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from core.logging.audit import AuditEventLogger, EventType
        logger_inst = AuditEventLogger()
        logger_inst.log_event(
            event_type=EventType.JOURNAL_POST,
            user_id="infra-validator",
            resource_type="test",
            resource_id="observability-check",
            details={"check": "infrastructure_migration"},
        )
        issues.append(InfraIssue(
            section="observability", severity=LOW,
            check="audit_logging", detail="Audit event logger works", passed=True,
        ))

        from core.logging.middleware import ObservabilityMiddleware
        issues.append(InfraIssue(
            section="observability", severity=LOW,
            check="observability_middleware", detail="ObservabilityMiddleware available", passed=True,
        ))

        from core.operations.api_observability import RequestMetrics
        intel = RequestMetrics()
        issues.append(InfraIssue(
            section="observability", severity=LOW,
            check="bad_request_intel", detail="Request metrics tracking active", passed=True,
        ))

        try:
            from core.operations.signal_coordinator import SignalCoordinator
            coord = SignalCoordinator()
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="signal_coordinator", detail="Signal coordination active", passed=True,
            ))
        except Exception:
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="signal_coordinator",
                detail="SignalCoordinator not available (additive)", passed=True,
            ))

        try:
            from core.governance.observability import OperationalHealthDashboard
            dashboard = OperationalHealthDashboard()
            dash_status = dashboard.get_status()
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="health_dashboard",
                detail=f"Health dashboard: {dash_status.get('overall', 'ok')}", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="health_dashboard",
                detail=f"Health dashboard: {e}", passed=True,
            ))

        try:
            from core.performance import RequestTimingMiddleware
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="request_timing", detail="Request timing middleware available", passed=True,
            ))
        except Exception:
            pass

        from core.operations.operational_intelligence import (
            RuleBasedAnomalyDetector, SLAMonitoringEngine,
        )
        detector = RuleBasedAnomalyDetector()
        sla = SLAMonitoringEngine()
        issues.append(InfraIssue(
            section="observability", severity=LOW,
            check="operational_intelligence",
            detail="Anomaly detection + SLA monitoring active", passed=True,
        ))

        from core.logging.config import logging_config
        config = logging_config()
        if config:
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="structured_logging", detail="Structured logging configured", passed=True,
            ))

        try:
            from core.audit.engine import AuditEngine
            engine = AuditEngine()
            report = engine.run_full_audit()
            score = report.get("production_readiness_score", 0) if isinstance(report, dict) else 0
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="audit_engine", detail=f"Audit engine score: {score}", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="observability", severity=LOW,
                check="audit_engine", detail=f"Audit: {e}", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="observability", severity=CRITICAL,
            check="validator_crash", detail=f"Observability validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["observability"] = SectionResult(
        name="Observability + Monitoring", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["observability"]
