import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from simulation.truth_engine.models.models import (
    Mismatch, MismatchType, MismatchSeverity,
    ExpectedState, ActualState, DriftReport,
)


logger = logging.getLogger('erp.simulation.truth.reports')


class TruthReportGenerator:
    """
    Generates structured mismatch reports.
    Classifies anomalies. Provides root-cause hints.
    NO auto-fix. NO UI coupling. Analytical only.
    """

    def __init__(self):
        self._reports: List[DriftReport] = []

    def generate(
        self, report: DriftReport,
        scores: Dict[str, float],
    ) -> Dict[str, Any]:
        report.set_score('financial_integrity_score',
                         scores.get('financial_integrity_score', 0))
        report.set_score('inventory_integrity_score',
                         scores.get('inventory_integrity_score', 0))
        report.set_score('workflow_completion_score',
                         scores.get('workflow_completion_score', 0))
        report.set_score('overall_system_score',
                         scores.get('overall_system_score', 0))
        report.set_score('drift_percentage',
                         scores.get('drift_percentage', 0))
        report.set_score('consistency_ratio',
                         scores.get('consistency_ratio', 0))
        self._reports.append(report)
        return self._build_report(report)

    def _build_report(self, report: DriftReport) -> Dict[str, Any]:
        severity_summary = self._classify_severity(report.mismatches)
        affected_modules = self._get_affected_modules(report.mismatches)
        mismatch_list = [m.to_dict() for m in report.mismatches]
        root_cause_hints = self._generate_hints(report.mismatches)
        return {
            'report_id': report.report_id,
            'scenario_id': report.scenario_id,
            'tick': report.tick,
            'generated_at': str(report.generated_at),
            'summary': {
                'total_mismatches': len(report.mismatches),
                'severity_summary': severity_summary,
                'affected_modules': affected_modules,
                'scores': report.scores,
            },
            'mismatches': mismatch_list,
            'root_cause_hints': root_cause_hints,
            'conclusion': self._generate_conclusion(
                report.scores, len(report.mismatches)
            ),
        }

    def _classify_severity(
        self, mismatches: List[Mismatch],
    ) -> Dict[str, int]:
        summary = {}
        for m in mismatches:
            sev = m.severity.value
            summary[sev] = summary.get(sev, 0) + 1
        return summary

    def _get_affected_modules(
        self, mismatches: List[Mismatch],
    ) -> List[str]:
        modules = set(m.affected_module for m in mismatches)
        return sorted(list(modules))

    def _generate_hints(
        self, mismatches: List[Mismatch],
    ) -> List[Dict[str, Any]]:
        hints = []
        for m in mismatches:
            hint = {
                'mismatch_id': m.mismatch_id,
                'type': m.mismatch_type.value,
                'hint': self._hint_for_type(m.mismatch_type, m),
            }
            hints.append(hint)
        return hints

    def _hint_for_type(
        self, mismatch_type: MismatchType, mismatch: Mismatch,
    ) -> str:
        hints = {
            MismatchType.FINANCIAL_MISMATCH: (
                "Verify journal entry creation and double-entry balance"
            ),
            MismatchType.INVENTORY_MISMATCH: (
                "Check stock movement recording and batch quantity tracking"
            ),
            MismatchType.TRANSACTION_MISSING: (
                "Verify transaction was recorded in ERP system"
            ),
            MismatchType.DUPLICATE_ENTRY: (
                "Check for duplicate journal entries or invoice numbers"
            ),
            MismatchType.WORKFLOW_INCOMPLETE: (
                "Verify all workflow steps completed successfully"
            ),
            MismatchType.STATE_DRIFT: (
                "Simulation state diverged from ERP actual state"
            ),
        }
        return hints.get(mismatch_type, "Investigate further")

    def _generate_conclusion(
        self, scores: Dict[str, float], mismatch_count: int,
    ) -> str:
        overall = scores.get('overall_system_score', 0)
        if overall >= 95 and mismatch_count == 0:
            return "SYSTEM INTEGRITY: EXCELLENT — No drift detected"
        elif overall >= 80:
            return (
                f"SYSTEM INTEGRITY: ACCEPTABLE — "
                f"{mismatch_count} mismatches found"
            )
        elif overall >= 60:
            return (
                f"SYSTEM INTEGRITY: WARNING — "
                f"{mismatch_count} mismatches found"
            )
        else:
            return (
                f"SYSTEM INTEGRITY: CRITICAL — "
                f"{mismatch_count} mismatches found"
            )

    @property
    def report_count(self) -> int:
        return len(self._reports)

    @property
    def reports(self) -> List[DriftReport]:
        return list(self._reports)
