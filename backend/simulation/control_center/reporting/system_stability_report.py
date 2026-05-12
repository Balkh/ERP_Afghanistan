from collections import deque
from typing import Any, Dict, List, Optional

from ..models import ExecutiveReport


class SystemStabilityReport:
    def __init__(self, max_reports: int = 100):
        self._reports: deque = deque(maxlen=max_reports)
        self._reports_by_id: Dict[str, ExecutiveReport] = {}

    def generate_stability_report(
        self,
        report_id: str,
        tick: int,
        stability_score: float,
        health_status: str,
        trend: str,
        drift_data: List[Dict[str, Any]],
        violation_count: int,
    ) -> ExecutiveReport:
        recommendations: List[str] = []

        if trend == "degrading":
            recommendations.append(
                "System stability is degrading — investigate recent changes"
            )
        if violation_count > 0:
            recommendations.append(
                f"Address {violation_count} stability violation(s)"
            )
        if stability_score < 50.0:
            recommendations.append(
                "Critical stability score — immediate intervention required"
            )
        elif stability_score < 70.0:
            recommendations.append(
                "Low stability score — review drift data and violations"
            )
        elif trend == "improving" and violation_count == 0:
            recommendations.append(
                "System is stable and improving — continue monitoring"
            )
        else:
            recommendations.append("No urgent action required")

        drift_summary = {
            "total_drift_entries": len(drift_data),
            "entries": drift_data,
        }

        summary = (
            f"Stability report for tick {tick}: "
            f"score={stability_score:.1f}, "
            f"health={health_status}, "
            f"trend={trend}, "
            f"violations={violation_count}"
        )

        sections: Dict[str, Any] = {
            "stability_overview": {
                "stability_score": stability_score,
                "health_status": health_status,
                "trend": trend,
                "violation_count": violation_count,
            },
            "health_status": {
                "value": health_status,
                "description": self._describe_health(
                    health_status, stability_score
                ),
            },
            "trend_analysis": self._analyze_trend(trend, stability_score),
            "drift_summary": drift_summary,
            "violation_count": {
                "count": violation_count,
                "severity": self._classify_violation_severity(
                    violation_count
                ),
            },
        }

        report = ExecutiveReport(
            report_id=report_id,
            tick=tick,
            title=f"System Stability Report - Tick {tick}",
            operational_state=health_status,
            stability_score=stability_score,
            summary=summary,
            sections=sections,
            recommendations=recommendations,
        )
        self._store_report(report)
        return report

    def _describe_health(
        self, health_status: str, stability_score: float
    ) -> str:
        if health_status in ("emergency", "critical"):
            return "System requires immediate attention"
        if health_status == "degraded":
            return "System is operating below normal parameters"
        if health_status == "recovering":
            return "System is returning to normal operation"
        return "System is operating normally"

    def _analyze_trend(self, trend: str, stability_score: float) -> Dict[str, Any]:
        descriptions = {
            "improving": "System metrics are trending positively",
            "degrading": "System metrics are trending negatively",
            "stable": "System metrics remain consistent",
        }
        return {
            "direction": trend,
            "description": descriptions.get(
                trend, "Unknown trend direction"
            ),
            "current_score": stability_score,
        }

    def _classify_violation_severity(self, count: int) -> str:
        if count == 0:
            return "none"
        if count <= 3:
            return "low"
        if count <= 10:
            return "medium"
        return "high"

    def _store_report(self, report: ExecutiveReport) -> None:
        if report.report_id in self._reports_by_id:
            old_report = self._reports_by_id[report.report_id]
            try:
                self._reports.remove(old_report)
            except ValueError:
                pass
        self._reports.append(report)
        self._reports_by_id[report.report_id] = report

    def get_stability_report(
        self, report_id: str
    ) -> Optional[ExecutiveReport]:
        return self._reports_by_id.get(report_id)

    def get_all_stability_reports(self) -> List[ExecutiveReport]:
        return list(self._reports)

    def get_report_count(self) -> int:
        return len(self._reports)

    def clear(self) -> None:
        self._reports.clear()
        self._reports_by_id.clear()
