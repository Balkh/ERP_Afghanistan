"""
Phase 5B.5 — Anomaly & Drift Intelligence Gateway.

Read-only orchestrator for all intelligence components.
"The system does not decide. It only reveals deviations."
"""
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    DriftReport, BaselineReference, EventPattern,
    AnomalyGraph, TemporalDriftReport,
    AnomalyTimeline, ConsistencyDeviationReport,
    IntelligenceSnapshot, ConfidenceLevel,
)
from core.operations.intelligence.drift import DriftDetectionEngine
from core.operations.intelligence.patterns import EventPatternMiningEngine
from core.operations.intelligence.anomaly_graph import CrossDomainAnomalyGraphEngine
from core.operations.intelligence.temporal import TemporalDriftAnalyzer
from core.operations.intelligence.reconstruction import ReplayAnomalyReconstructionEngine
from core.operations.intelligence.consistency import ConsistencyDeviationAnalyzer

logger = logging.getLogger('erp.intelligence.gateway')

INTELLIGENCE_GATEWAY_VERSION = "1.0.0"


class AnomalyIntelligenceGateway:
    """Read-only gateway to all intelligence engines.

    All operations are:
    - Descriptive only
    - Deterministic
    - Non-prescriptive
    - Audit-grade
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._drift = DriftDetectionEngine(self._store)
        self._patterns = EventPatternMiningEngine(self._store)
        self._graph = CrossDomainAnomalyGraphEngine(self._store)
        self._temporal = TemporalDriftAnalyzer(self._store)
        self._reconstruction = ReplayAnomalyReconstructionEngine(self._store)
        self._consistency = ConsistencyDeviationAnalyzer(self._store)

    # Drift Detection API
    def compute_baseline(self, domain: str) -> BaselineReference:
        return self._drift.compute_baseline(Domain(domain))

    def detect_drift(self, domain: str, aggregate_id: str) -> DriftReport:
        return self._drift.detect_drift(Domain(domain), aggregate_id)

    def detect_drift_all(self, domain: str) -> List[DriftReport]:
        return self._drift.detect_drift_all_aggregates(Domain(domain))

    # Pattern Mining API
    def mine_frequent_sequences(self, domain: str) -> List[EventPattern]:
        return self._patterns.mine_frequent_sequences(Domain(domain))

    def detect_rare_events(self, domain: str) -> List[EventPattern]:
        return self._patterns.detect_rare_events(Domain(domain))

    def detect_bursts(self, domain: str) -> List[EventPattern]:
        return self._patterns.detect_bursts(Domain(domain))

    def detect_cycles(self, domain: str) -> List[EventPattern]:
        return self._patterns.detect_cycles(Domain(domain))

    def mine_all_patterns(self, domain: str) -> Dict[str, List[EventPattern]]:
        return self._patterns.mine_all_patterns(Domain(domain))

    # Anomaly Graph API
    def build_anomaly_graph(self, domain: str) -> AnomalyGraph:
        return self._graph.build_anomaly_graph(Domain(domain))

    def build_cross_domain_graph(self) -> AnomalyGraph:
        return self._graph.build_cross_domain_graph()

    # Temporal Drift API
    def analyze_temporal_drift(self, domain: str) -> TemporalDriftReport:
        return self._temporal.analyze_temporal_drift(Domain(domain))

    # Reconstruction API
    def reconstruct_anomaly(self, domain: str, aggregate_id: str) -> AnomalyTimeline:
        return self._reconstruction.reconstruct_from_aggregate(Domain(domain), aggregate_id)

    def find_anomaly_clusters(self, domain: str) -> List[AnomalyTimeline]:
        return self._reconstruction.find_anomaly_clusters(Domain(domain))

    # Consistency API
    def analyze_consistency_deviations(self) -> List[ConsistencyDeviationReport]:
        return self._consistency.analyze_deviations()

    def compare_with_truth_layer(self, counts: Dict[str, int]) -> ConsistencyDeviationReport:
        return self._consistency.compare_with_truth_layer(counts)

    # System API
    def get_snapshot(self) -> IntelligenceSnapshot:
        drift = self.detect_drift_all("inventory") if self._store.count_by_domain().get("inventory", 0) > 0 else []
        patterns = self.mine_all_patterns("inventory") if self._store.count_by_domain().get("inventory", 0) > 0 else {}
        graph = self.build_anomaly_graph("inventory") if self._store.count_by_domain().get("inventory", 0) > 0 else None
        temporal = self.analyze_temporal_drift("inventory") if self._store.count_by_domain().get("inventory", 0) > 0 else None
        consistency = self.analyze_consistency_deviations()

        return IntelligenceSnapshot(
            total_drift_reports=len(drift),
            total_patterns_detected=sum(len(v) for v in patterns.values()),
            total_anomalies_correlated=len(graph.nodes) if graph else 0,
            total_temporal_segments=len(temporal.segments) if temporal else 0,
            total_consistency_deviations=len(consistency),
            domains_analyzed=list(self._store.count_by_domain().keys()),
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "gateway_version": INTELLIGENCE_GATEWAY_VERSION,
            "engine_status": "read_only",
            "event_count": self._store.count(),
            "domains": list(self._store.count_by_domain().keys()),
        }

    def reset(self) -> None:
        from core.operations.truth.event_store import reset_event_store
        reset_event_store()
        self._store = get_event_store()
        self._drift = DriftDetectionEngine(self._store)
        self._patterns = EventPatternMiningEngine(self._store)
        self._graph = CrossDomainAnomalyGraphEngine(self._store)
        self._temporal = TemporalDriftAnalyzer(self._store)
        self._reconstruction = ReplayAnomalyReconstructionEngine(self._store)
        self._consistency = ConsistencyDeviationAnalyzer(self._store)


_gateway: Optional[AnomalyIntelligenceGateway] = None


def get_gateway() -> AnomalyIntelligenceGateway:
    global _gateway
    if _gateway is None:
        _gateway = AnomalyIntelligenceGateway()
    return _gateway


def reset_gateway() -> None:
    global _gateway
    from core.operations.truth.event_store import reset_event_store
    reset_event_store()
    _gateway = None
