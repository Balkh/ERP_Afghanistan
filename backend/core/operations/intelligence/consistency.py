"""
Phase 5B.5 — Consistency Deviation Analyzer.

Compares Truth Layer state, Observability Layer traces, and Event Store projections.
Detects missing events, duplicated events, projection mismatches, and cross-domain inconsistencies.

Descriptive only. Never recommends actions.
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    ConsistencyDeviationReport, DeviationType,
    ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.consistency')

CONSISTENCY_ANALYZER_VERSION = "1.0.0"


class ConsistencyDeviationAnalyzer:
    """Cross-layer consistency deviation analysis.

    Compares:
    - Truth Layer state (event counts per domain)
    - Observability Layer traces
    - Event Store projections
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def analyze_deviations(self) -> List[ConsistencyDeviationReport]:
        """Run full consistency deviation analysis across all domains.

        Returns:
            List of ConsistencyDeviationReport — one per detected issue.
        """
        reports: List[ConsistencyDeviationReport] = []
        all_events = self._store.get_all()
        event_ids = [e.event_id for e in all_events]

        dup_report = self._check_duplicates(event_ids)
        if dup_report:
            reports.append(dup_report)

        for domain in Domain:
            domain_events = self._store.get_by_domain(domain)
            seq_report = self._check_sequence_anomalies(domain, domain_events)
            if seq_report:
                reports.append(seq_report)

            timing_report = self._check_timing_anomalies(domain, domain_events)
            if timing_report:
                reports.append(timing_report)

        cross_domain = self._check_cross_domain(all_events)
        if cross_domain:
            reports.append(cross_domain)

        return reports

    def compare_with_truth_layer(
        self,
        truth_layer_counts: Dict[str, int],
    ) -> ConsistencyDeviationReport:
        """Compare Event Store counts with Truth Layer reported counts.

        Args:
            truth_layer_counts: Event counts per domain from Truth Layer.

        Returns:
            ConsistencyDeviationReport with discrepancies.
        """
        store_counts = self._store.count_by_domain()
        discrepancies = []
        affected: List[str] = []
        total_dev = 0.0

        for domain, truth_count in truth_layer_counts.items():
            store_count = store_counts.get(domain, 0)
            if store_count != truth_count:
                diff = abs(store_count - truth_count)
                discrepancies.append({
                    "domain": domain,
                    "truth_layer_count": truth_count,
                    "event_store_count": store_count,
                    "difference": diff,
                })
                affected.append(domain)
                total_dev += diff

        return ConsistencyDeviationReport(
            deviation_type=DeviationType.CROSS_DOMAIN_INCONSISTENCY,
            affected_entities=affected,
            deviation_score=round(total_dev, 2),
            truth_layer_summary={"counts": truth_layer_counts},
            event_store_summary={"counts": store_counts},
            confidence_level=ConfidenceLevel.HIGH if total_dev > 0 else ConfidenceLevel.MEDIUM,
            model_limitations=ModelLimitations(
                statistical_approximations=["Direct count comparison"],
            ),
        )

    def _check_duplicates(self, event_ids: List[str]) -> Optional[ConsistencyDeviationReport]:
        if len(event_ids) == len(set(event_ids)):
            return None
        seen: set = set()
        dups = []
        for eid in event_ids:
            if eid in seen:
                dups.append(eid)
            seen.add(eid)
        if dups:
            return ConsistencyDeviationReport(
                deviation_type=DeviationType.DUPLICATE_EVENTS,
                affected_entities=dups,
                deviation_score=float(len(dups)),
                confidence_level=ConfidenceLevel.HIGH,
                model_limitations=ModelLimitations(
                    statistical_approximations=["Exact duplicate detection"],
                ),
            )
        return None

    def _check_sequence_anomalies(
        self,
        domain: Domain,
        events: List[Any],
    ) -> Optional[ConsistencyDeviationReport]:
        gaps = self._store.check_sequence_continuity(domain)
        if not gaps:
            return None
        return ConsistencyDeviationReport(
            deviation_type=DeviationType.SEQUENCE_ANOMALY,
            affected_entities=[g["aggregate_id"] for g in gaps],
            deviation_score=float(len(gaps)),
            confidence_level=ConfidenceLevel.HIGH,
            model_limitations=ModelLimitations(
                statistical_approximations=["Sequence gap detection"],
            ),
        )

    def _check_timing_anomalies(
        self,
        domain: Domain,
        events: List[Any],
    ) -> Optional[ConsistencyDeviationReport]:
        if len(events) < 2:
            return None
        inversions = 0
        for i in range(len(events) - 1):
            if events[i].timestamp > events[i + 1].timestamp:
                inversions += 1
        if inversions > 0:
            return ConsistencyDeviationReport(
                deviation_type=DeviationType.TIMING_ANOMALY,
                affected_entities=[domain.value],
                deviation_score=float(inversions),
                confidence_level=ConfidenceLevel.MEDIUM,
                model_limitations=ModelLimitations(
                    statistical_approximations=["Timestamp inversion detection"],
                ),
            )
        return None

    def _check_cross_domain(
        self,
        events: List[Any],
    ) -> Optional[ConsistencyDeviationReport]:
        domains = set(e.domain.value for e in events)
        if len(domains) < 2:
            return None
        correlation_ids = set()
        for e in events:
            cid = e.metadata.get("correlation_id", "")
            if cid:
                correlation_ids.add(cid)
        for cid in list(correlation_ids)[:5]:
            cid_events = [e for e in events if e.metadata.get("correlation_id") == cid]
            cid_domains = set(e.domain.value for e in cid_events)
            if len(cid_domains) > 1:
                event_counts = {d: sum(1 for e in cid_events if e.domain.value == d) for d in cid_domains}
                if max(event_counts.values()) > min(event_counts.values()) * 3:
                    return ConsistencyDeviationReport(
                        deviation_type=DeviationType.CROSS_DOMAIN_INCONSISTENCY,
                        affected_entities=[f"correlation_{cid}"],
                        deviation_score=float(max(event_counts.values()) - min(event_counts.values())),
                        confidence_level=ConfidenceLevel.MEDIUM,
                        model_limitations=ModelLimitations(
                            statistical_approximations=["Cross-domain event ratio analysis"],
                            known_bias=["Different domains have different event volumes"],
                        ),
                    )
        return None

    def get_all_reports(self) -> List[Dict[str, Any]]:
        """Get all deviation reports as serializable dicts."""
        return [
            {
                "deviation_type": r.deviation_type.value,
                "affected_entities": r.affected_entities,
                "deviation_score": r.deviation_score,
                "confidence_level": r.confidence_level.value,
            }
            for r in self.analyze_deviations()
        ]
