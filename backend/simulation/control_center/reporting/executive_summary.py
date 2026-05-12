from collections import deque
from typing import Any, Dict, List, Optional

from ..models import ExecutiveReport


class ExecutiveSummary:
    def __init__(self, max_reports: int = 100):
        self._reports: deque = deque(maxlen=max_reports)
        self._reports_by_id: Dict[str, ExecutiveReport] = {}

    def generate_report(
        self,
        report_id: str,
        tick: int,
        title: str,
        operational_state: str,
        stability_score: float,
        summary: str,
        sections: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[str]] = None,
    ) -> ExecutiveReport:
        report = ExecutiveReport(
            report_id=report_id,
            tick=tick,
            title=title,
            operational_state=operational_state,
            stability_score=stability_score,
            summary=summary,
            sections=sections or {},
            recommendations=recommendations or [],
        )
        self._store_report(report)
        return report

    def _store_report(self, report: ExecutiveReport) -> None:
        if report.report_id in self._reports_by_id:
            old_report = self._reports_by_id[report.report_id]
            try:
                self._reports.remove(old_report)
            except ValueError:
                pass
        self._reports.append(report)
        self._reports_by_id[report.report_id] = report

    def get_report(self, report_id: str) -> Optional[ExecutiveReport]:
        return self._reports_by_id.get(report_id)

    def get_latest_report(self) -> Optional[ExecutiveReport]:
        if not self._reports:
            return None
        return self._reports[-1]

    def get_reports(
        self,         tick_start: Optional[int] = None, tick_end: Optional[int] = None, limit: int = 20
    ) -> List[ExecutiveReport]:
        result = list(self._reports)
        if tick_start is not None:
            result = [r for r in result if r.tick >= tick_start]
        if tick_end is not None:
            result = [r for r in result if r.tick <= tick_end]
        result.reverse()
        return result[:limit]

    def get_report_count(self) -> int:
        return len(self._reports)

    def clear(self) -> None:
        self._reports.clear()
        self._reports_by_id.clear()
