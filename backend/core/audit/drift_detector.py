import logging
from typing import Dict, Any, List, Optional, Set
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.drift")


class DriftDetectionEngine:

    def __init__(self):
        self.module = AuditModule.DRIFT

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        snapshots = existing_data.get("snapshots", [])
        baseline = existing_data.get("baseline_snapshot", {})
        current = existing_data.get("current_snapshot", {})

        total_snapshots = len(snapshots)
        schema_drift = False
        data_drift = False
        financial_drift = False
        inventory_drift = False
        event_drift = False

        try:
            if baseline and current:
                schema_drift_findings = self._detect_schema_drift(
                    baseline, current, findings, module,
                )
                schema_drift = schema_drift_findings

                data_drift_findings = self._detect_data_drift(
                    baseline, current, findings, module,
                )
                data_drift = data_drift_findings

            if len(snapshots) >= 2:
                drift = self._detect_temporal_drift(
                    snapshots, findings, module,
                )
                financial_drift = drift.get("financial", False)
                inventory_drift = drift.get("inventory", False)
                event_drift = drift.get("event", False)

            if len(snapshots) >= 2:
                self._detect_checksum_drift(
                    snapshots, findings, module,
                )

            if len(snapshots) == 0 and not baseline and not current:
                findings.append(AuditFinding(
                    module=module,
                    severity=AuditSeverity.LOW,
                    check_name="no_snapshot_data",
                    passed=True,
                    detail="No snapshot data available for drift analysis",
                ))

            drift_categories = []
            if schema_drift:
                drift_categories.append("schema")
            if data_drift:
                drift_categories.append("data")
            if financial_drift:
                drift_categories.append("financial")
            if inventory_drift:
                drift_categories.append("inventory")
            if event_drift:
                drift_categories.append("event")

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="drift_summary",
                passed=len(drift_categories) == 0,
                detail=(
                    f"Drift detected in categories: {drift_categories}"
                    if drift_categories
                    else "No drift detected across any category"
                ),
                evidence={
                    "drift_categories": drift_categories,
                    "total_snapshots_analyzed": total_snapshots,
                },
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="audit_execution",
                passed=False,
                detail=f"Drift detection failed: {e}",
            ))
            logger.error("Drift detection error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Snapshots={total_snapshots}, Drift categories: "
                f"{'schema=' + str(schema_drift) + ' ' if schema_drift else ''}"
                f"{'data=' + str(data_drift) + ' ' if data_drift else ''}"
                f"{'financial=' + str(financial_drift) + ' ' if financial_drift else ''}"
                f"{'inventory=' + str(inventory_drift) + ' ' if inventory_drift else ''}"
                f"{'event=' + str(event_drift) if event_drift else 'none'}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )

    def _detect_schema_drift(
        self,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        findings: List[AuditFinding],
        module: AuditModule,
    ) -> bool:
        baseline_tables = set(baseline.get("table_row_counts", {}).keys())
        current_tables = set(current.get("table_row_counts", {}).keys())

        new_tables = current_tables - baseline_tables
        removed_tables = baseline_tables - current_tables

        has_drift = bool(new_tables) or bool(removed_tables)

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.HIGH,
            check_name="schema_drift",
            passed=not has_drift,
            detail=(
                f"New tables: {sorted(new_tables)}, "
                f"Removed tables: {sorted(removed_tables)}"
                if has_drift
                else "No schema drift detected"
            ),
            evidence={
                "new_tables": sorted(new_tables),
                "removed_tables": sorted(removed_tables),
                "baseline_count": len(baseline_tables),
                "current_count": len(current_tables),
            },
        ))
        return has_drift

    def _detect_data_drift(
        self,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        findings: List[AuditFinding],
        module: AuditModule,
    ) -> bool:
        baseline_counts = baseline.get("table_row_counts", {})
        current_counts = current.get("table_row_counts", {})

        diverged = []
        unchanged = 0
        for table, b_count in baseline_counts.items():
            c_count = current_counts.get(table)
            if c_count is not None and c_count != b_count:
                diverged.append({
                    "table": table,
                    "baseline": b_count,
                    "current": c_count,
                    "delta": c_count - b_count,
                })
            elif c_count is not None and c_count == b_count:
                unchanged += 1

        has_drift = len(diverged) > 0
        total_tracked = len(set(baseline_counts.keys()) & set(current_counts.keys()))

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.MEDIUM,
            check_name="data_drift",
            passed=not has_drift,
            detail=(
                f"Tables with row count changes: {len(diverged)}/{total_tracked}, "
                f"Unchanged: {unchanged}"
                if has_drift
                else f"All {total_tracked} tables unchanged"
            ),
            evidence={
                "diverged_tables": diverged,
                "total_tracked": total_tracked,
                "unchanged": unchanged,
            },
        ))
        return has_drift

    def _detect_temporal_drift(
        self,
        snapshots: List[Dict[str, Any]],
        findings: List[AuditFinding],
        module: AuditModule,
    ) -> Dict[str, bool]:
        result = {"financial": False, "inventory": False, "event": False}

        if len(snapshots) < 2:
            return result

        first = snapshots[0]
        last = snapshots[-1]

        first_counts = first.get("table_row_counts", {})
        last_counts = last.get("table_row_counts", {})

        financial_tables = [
            t for t in first_counts
            if any(kw in t.lower() for kw in [
                "account", "journal", "ledger", "fiscal",
            ])
        ]
        inventory_tables = [
            t for t in first_counts
            if any(kw in t.lower() for kw in [
                "batch", "stock", "inventory", "product",
            ])
        ]

        fin_drift = sum(
            abs(last_counts.get(t, 0) - first_counts.get(t, 0))
            for t in financial_tables
        )
        inv_drift = sum(
            abs(last_counts.get(t, 0) - first_counts.get(t, 0))
            for t in inventory_tables
        )

        result["financial"] = fin_drift > 0
        result["inventory"] = inv_drift > 0

        if fin_drift > 0:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="financial_drift",
                passed=False,
                detail=f"Financial table row count drift: {fin_drift} rows across {len(financial_tables)} tables",
                evidence={
                    "tables_checked": financial_tables,
                    "total_drift": fin_drift,
                },
            ))

        if inv_drift > 0:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="inventory_drift",
                passed=False,
                detail=f"Inventory table row count drift: {inv_drift} rows across {len(inventory_tables)} tables",
                evidence={
                    "tables_checked": inventory_tables,
                    "total_drift": inv_drift,
                },
            ))

        return result

    def _detect_checksum_drift(
        self,
        snapshots: List[Dict[str, Any]],
        findings: List[AuditFinding],
        module: AuditModule,
    ):
        if len(snapshots) < 2:
            return
        last_cs = snapshots[-1].get("checksum", "")
        if not last_cs:
            return
        drifts = 0
        for i in range(1, len(snapshots)):
            curr_cs = snapshots[i].get("checksum", "")
            prev_cs = snapshots[i - 1].get("checksum", "")
            if curr_cs != prev_cs:
                drifts += 1

        findings.append(AuditFinding(
            module=module,
            severity=AuditSeverity.MEDIUM,
            check_name="checksum_drift_timeline",
            passed=True,
            detail=(
                f"Checksum changes across {len(snapshots)} snapshots: {drifts}"
            ),
            evidence={
                "snapshot_count": len(snapshots),
                "checksum_changes": drifts,
            },
        ))
