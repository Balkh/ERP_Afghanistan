import logging
import json
import hashlib
from typing import Dict, Any, List, Optional
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.replay")


class ReplayVerificationEngine:

    def __init__(self):
        self.module = AuditModule.REPLAY

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        snapshots = existing_data.get("snapshots", [])
        event_log = existing_data.get("event_log", [])
        comparison_pairs = existing_data.get("comparison_pairs", [])
        expected_checksums = existing_data.get("expected_checksums", {})

        total_snapshots = len(snapshots)
        verified = 0
        failed_verification = 0

        try:
            for snapshot in snapshots:
                day = snapshot.get("day", 0)
                stored_checksum = snapshot.get("checksum", "")
                row_counts = snapshot.get("table_row_counts", {})

                actual_checksum = self._compute_checksum(row_counts)

                if expected_checksums and day in expected_checksums:
                    stored_checksum = expected_checksums[day]

                if stored_checksum and actual_checksum == stored_checksum:
                    verified += 1
                    findings.append(AuditFinding(
                        module=module,
                        severity=AuditSeverity.LOW,
                        check_name=f"snapshot_checksum_day_{day}",
                        passed=True,
                        detail=f"Day {day}: checksum verified ({actual_checksum[:12]}...)",
                        evidence={
                            "day": day,
                            "checksum": actual_checksum,
                        },
                    ))
                else:
                    failed_verification += 1
                    findings.append(AuditFinding(
                        module=module,
                        severity=AuditSeverity.HIGH,
                        check_name=f"snapshot_checksum_day_{day}",
                        passed=False,
                        detail=(
                            f"Day {day}: checksum mismatch "
                            f"(stored={stored_checksum[:12] if stored_checksum else 'N/A'}..., "
                            f"actual={actual_checksum[:12]}...)"
                        ),
                        evidence={
                            "day": day,
                            "stored": stored_checksum,
                            "actual": actual_checksum,
                        },
                    ))

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="checksum_verification_summary",
                passed=failed_verification == 0,
                detail=(
                    f"Snapshots verified: {verified}/{total_snapshots}, "
                    f"Failed: {failed_verification}"
                ),
                evidence={
                    "verified": verified,
                    "total": total_snapshots,
                    "failed": failed_verification,
                },
            ))

            for pair in comparison_pairs:
                day_a = pair.get("day_a", 0)
                day_b = pair.get("day_b", 0)
                data_a = pair.get("data_a", {})
                data_b = pair.get("data_b", {})
                cs_a = self._compute_checksum(data_a)
                cs_b = self._compute_checksum(data_b)
                is_deterministic = cs_a == cs_b

                findings.append(AuditFinding(
                    module=module,
                    severity=AuditSeverity.CRITICAL,
                    check_name=f"deterministic_replay_day_{day_a}_vs_{day_b}",
                    passed=is_deterministic,
                    detail=(
                        f"Replay comparison day {day_a} vs {day_b}: "
                        f"{'IDENTICAL' if is_deterministic else 'DIVERGED'}"
                    ),
                    evidence={
                        "day_a": day_a,
                        "day_b": day_b,
                        "checksum_a": cs_a,
                        "checksum_b": cs_b,
                        "deterministic": is_deterministic,
                    },
                ))

            event_log_checksum = self._compute_checksum(
                {"events": event_log} if event_log else {}
            )
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="event_log_integrity",
                passed=True,
                detail=f"Event log checksum: {event_log_checksum[:16] if event_log_checksum else 'empty'}" if event_log else "Event log empty",
                evidence={
                    "event_count": len(event_log),
                    "checksum": event_log_checksum if event_log else "",
                },
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="audit_execution",
                passed=False,
                detail=f"Replay verification failed: {e}",
            ))
            logger.error("Replay verification error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Snapshots={total_snapshots}, Verified={verified}, "
                f"Failed={failed_verification}, Pairs={len(comparison_pairs)}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()
