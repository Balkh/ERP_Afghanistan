import logging
from typing import Dict, Any, List, Optional
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.event")


class EventConsistencyAuditor:

    def __init__(self):
        self.module = AuditModule.EVENT

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module
        event_log = existing_data.get("event_log", [])
        snapshot_history = existing_data.get("snapshot_history", [])

        total_events = len(event_log)
        total_snapshots = len(snapshot_history)

        try:
            self._check_event_ordering(event_log, findings, module)
            self._check_event_completeness(
                event_log, existing_data, findings, module,
            )
            self._check_duplicate_events(event_log, findings, module)
            self._check_snapshot_event_correlation(
                event_log, snapshot_history, existing_data, findings, module,
            )
            self._check_sequence_gaps(event_log, findings, module)

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="audit_execution",
                passed=False,
                detail=f"Event audit failed: {e}",
            ))
            logger.error("Event audit error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Events={total_events}, Snapshots={total_snapshots}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )

    def _check_event_ordering(
        self,
        event_log: List[Dict[str, Any]],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        if len(event_log) < 2:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="event_ordering",
                passed=True,
                detail="Insufficient events for ordering check",
            ))
            return

        out_of_order = 0
        for i in range(1, len(event_log)):
            prev_day = event_log[i - 1].get("day", 0)
            curr_day = event_log[i].get("day", 0)
            if curr_day < prev_day:
                out_of_order += 1

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.HIGH,
            check_name="event_ordering",
            passed=out_of_order == 0,
            detail=f"Out-of-order events: {out_of_order}/{len(event_log)}",
            evidence={
                "total_events": len(event_log),
                "out_of_order": out_of_order,
            },
        ))

    def _check_event_completeness(
        self,
        event_log: List[Dict[str, Any]],
        existing_data: Dict[str, Any],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        expected_days = existing_data.get("expected_days", 0)
        days_with_events = len(set(
            e.get("day", 0) for e in event_log
        ))
        if expected_days > 0:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="event_completeness",
                passed=days_with_events >= expected_days * 0.9,
                detail=(
                    f"Days with events: {days_with_events}/{expected_days} "
                    f"({days_with_events / max(expected_days, 1) * 100:.1f}%)"
                ),
                evidence={
                    "days_with_events": days_with_events,
                    "expected_days": expected_days,
                },
            ))

    def _check_duplicate_events(
        self,
        event_log: List[Dict[str, Any]],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        seen = set()
        duplicates = 0
        for event in event_log:
            event_type = event.get("event_type", "")
            day = event.get("day", 0)
            key = f"{day}:{event_type}"
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.MEDIUM,
            check_name="duplicate_events",
            passed=duplicates == 0,
            detail=f"Duplicate event signatures: {duplicates}/{len(event_log)}",
            evidence={"duplicates": duplicates, "total": len(event_log)},
        ))

    def _check_snapshot_event_correlation(
        self,
        event_log: List[Dict[str, Any]],
        snapshot_history: List[Dict[str, Any]],
        existing_data: Dict[str, Any],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        snapshot_days = set(s.get("day", 0) for s in snapshot_history)
        days_with_backup = set(
            e.get("day", 0) for e in event_log
            if e.get("event_type") == "daily_snapshot"
        )

        missing_snapshots = days_with_backup - snapshot_days
        extra_snapshots = snapshot_days - days_with_backup

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.MEDIUM,
            check_name="snapshot_event_correlation",
            passed=len(missing_snapshots) == 0,
            detail=(
                f"Backup events without snapshots: {len(missing_snapshots)}, "
                f"Snapshots without backup events: {len(extra_snapshots)}"
            ),
            evidence={
                "missing_snapshots": sorted(missing_snapshots),
                "extra_snapshots": sorted(extra_snapshots),
            },
        ))

    def _check_sequence_gaps(
        self,
        event_log: List[Dict[str, Any]],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        days = sorted(set(e.get("day", 0) for e in event_log))
        gaps = []
        for i in range(1, len(days)):
            if days[i] - days[i - 1] > 1:
                for gap in range(days[i - 1] + 1, days[i]):
                    gaps.append(gap)

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.HIGH,
            check_name="sequence_gaps",
            passed=len(gaps) == 0,
            detail=f"Day sequence gaps: {gaps}",
            evidence={"gaps": gaps, "total_gaps": len(gaps)},
        ))
