from collections import Counter, deque
from typing import Any, Dict, List, Optional

from ..models import ExecutiveReport, IncidentRecord, OperationalSignal


class IntelligenceDigest:
    def __init__(self, max_digests: int = 100):
        self._digests: deque = deque(maxlen=max_digests)
        self._digests_by_id: Dict[str, ExecutiveReport] = {}

    def generate_digest(
        self,
        digest_id: str,
        tick: int,
        signals: List[OperationalSignal],
        incidents: List[IncidentRecord],
        health_data: Dict[str, Any],
    ) -> ExecutiveReport:
        signal_type_counts: Dict[str, int] = Counter(
            s.signal_type.value for s in signals
        )
        incident_status_counts: Dict[str, int] = Counter(
            i.status.value for i in incidents
        )

        severity_order = ["critical", "high", "medium", "low", "info"]
        significant_events: List[Dict[str, Any]] = []
        all_events: List[Dict[str, Any]] = []

        for s in signals:
            all_events.append(
                {
                    "type": "signal",
                    "id": s.signal_id,
                    "severity": s.severity.value,
                    "description": s.description,
                }
            )
        for i in incidents:
            all_events.append(
                {
                    "type": "incident",
                    "id": i.incident_id,
                    "severity": i.severity.value,
                    "description": i.description,
                }
            )

        all_events.sort(
            key=lambda e: (
                severity_order.index(e["severity"])
                if e["severity"] in severity_order
                else len(severity_order)
            )
        )
        significant_events = all_events[:5]

        recommendations = []
        open_count = incident_status_counts.get("open", 0)
        acknowledged_count = incident_status_counts.get("acknowledged", 0)
        unresolved = open_count + acknowledged_count
        if unresolved > 0:
            recommendations.append(
                f"Review {unresolved} unresolved incident(s)"
            )
        critical_signals = signal_type_counts.get(
            "integrity_breach", 0
        ) + signal_type_counts.get("anomaly", 0)
        if critical_signals > 0:
            recommendations.append(
                f"Investigate {critical_signals} integrity/anomaly signal(s)"
            )
        if not recommendations:
            recommendations.append("No significant issues detected")

        summary = (
            f"Digest for tick {tick}: "
            f"{len(signals)} signals, "
            f"{len(incidents)} incidents"
        )

        sections = {
            "signal_summary": {
                "total_signals": len(signals),
                "signal_type_counts": dict(signal_type_counts),
            },
            "incident_summary": {
                "total_incidents": len(incidents),
                "incident_status_counts": dict(incident_status_counts),
            },
            "health_overview": health_data,
            "key_findings": significant_events,
        }

        report = ExecutiveReport(
            report_id=digest_id,
            tick=tick,
            title=f"Intelligence Digest - Tick {tick}",
            operational_state=health_data.get("operational_state", "unknown"),
            stability_score=float(health_data.get("stability_score", 0.0)),
            summary=summary,
            sections=sections,
            recommendations=recommendations,
        )
        self._store_digest(report)
        return report

    def _store_digest(self, digest: ExecutiveReport) -> None:
        if digest.report_id in self._digests_by_id:
            old_digest = self._digests_by_id[digest.report_id]
            try:
                self._digests.remove(old_digest)
            except ValueError:
                pass
        self._digests.append(digest)
        self._digests_by_id[digest.report_id] = digest

    def get_digest(self, digest_id: str) -> Optional[ExecutiveReport]:
        return self._digests_by_id.get(digest_id)

    def get_latest_digest(self) -> Optional[ExecutiveReport]:
        if not self._digests:
            return None
        return self._digests[-1]

    def get_digest_count(self) -> int:
        return len(self._digests)

    def clear(self) -> None:
        self._digests.clear()
        self._digests_by_id.clear()
