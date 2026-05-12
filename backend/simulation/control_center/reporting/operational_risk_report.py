from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Optional

from ..models import (
    AggregatedState,
    ExecutiveReport,
    IncidentRecord,
    IntelligenceSeverity,
    OperationalState,
)


class OperationalRiskReport:
    def __init__(self, max_reports: int = 100):
        self._reports: deque = deque(maxlen=max_reports)
        self._reports_by_id: Dict[str, ExecutiveReport] = {}

    def generate_risk_report(
        self,
        report_id: str,
        tick: int,
        aggregated_state: AggregatedState,
        incidents: List[IncidentRecord],
        escalations: List[Dict[str, Any]],
    ) -> ExecutiveReport:
        severity_counts: Dict[str, int] = Counter(
            i.severity.value for i in incidents
        )
        incident_breakdown = dict(severity_counts)

        severity_order = [
            IntelligenceSeverity.CRITICAL,
            IntelligenceSeverity.HIGH,
            IntelligenceSeverity.MEDIUM,
            IntelligenceSeverity.LOW,
            IntelligenceSeverity.INFO,
        ]
        ranked = sorted(
            incidents,
            key=lambda i: (
                severity_order.index(i.severity)
                if i.severity in severity_order
                else len(severity_order)
            ),
            reverse=True,
        )
        top_risks = [
            {
                "incident_id": inc.incident_id,
                "severity": inc.severity.value,
                "description": inc.description,
                "occurrence_count": inc.occurrence_count,
                "status": inc.status.value,
                "escalation_level": inc.escalation_level.value,
            }
            for inc in ranked[:5]
        ]

        recommendations = self._build_recommendations(
            aggregated_state, incidents
        )

        summary = (
            f"Risk report for tick {tick}: "
            f"state={aggregated_state.state.value}, "
            f"severity_score={aggregated_state.severity_score:.2f}, "
            f"incidents={aggregated_state.incident_count}, "
            f"critical_signals={aggregated_state.critical_count}"
        )

        sections = {
            "risk_summary": {
                "operational_state": aggregated_state.state.value,
                "severity_score": aggregated_state.severity_score,
                "total_incidents": aggregated_state.incident_count,
                "active_signals": aggregated_state.active_signals,
                "critical_signals": aggregated_state.critical_count,
            },
            "incident_breakdown": incident_breakdown,
            "escalation_summary": {
                "total_escalations": len(escalations),
                "escalations": escalations,
            },
            "top_risks": top_risks,
        }

        report = ExecutiveReport(
            report_id=report_id,
            tick=tick,
            title=f"Operational Risk Report - Tick {tick}",
            operational_state=aggregated_state.state.value,
            stability_score=max(
                0.0, 100.0 - aggregated_state.severity_score * 10.0
            ),
            summary=summary,
            sections=sections,
            recommendations=recommendations,
        )
        self._store_report(report)
        return report

    def _build_recommendations(
        self,
        state: AggregatedState,
        incidents: List[IncidentRecord],
    ) -> List[str]:
        recommendations = []
        if state.state in (OperationalState.CRITICAL, OperationalState.EMERGENCY):
            recommendations.append(
                "Immediate escalation required: system is in critical/emergency state"
            )
        if state.critical_count > 0:
            recommendations.append(
                f"Address {state.critical_count} critical signal(s) with highest priority"
            )
        open_incidents = [
            i for i in incidents if i.status.value in ("open", "acknowledged")
        ]
        if open_incidents:
            recommendations.append(
                f"Resolve {len(open_incidents)} open/acknowledged incident(s)"
            )
        if state.severity_score > 5.0:
            recommendations.append(
                "High severity score detected — investigate root causes"
            )
        if not recommendations:
            recommendations.append("No immediate action required — system is stable")
        return recommendations

    def _store_report(self, report: ExecutiveReport) -> None:
        if report.report_id in self._reports_by_id:
            old_report = self._reports_by_id[report.report_id]
            try:
                self._reports.remove(old_report)
            except ValueError:
                pass
        self._reports.append(report)
        self._reports_by_id[report.report_id] = report

    def get_risk_report(self, report_id: str) -> Optional[ExecutiveReport]:
        return self._reports_by_id.get(report_id)

    def get_all_risk_reports(self) -> List[ExecutiveReport]:
        return list(self._reports)

    def get_report_count(self) -> int:
        return len(self._reports)

    def clear(self) -> None:
        self._reports.clear()
        self._reports_by_id.clear()
