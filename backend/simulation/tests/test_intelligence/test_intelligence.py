"""
Phase 5B.5 — Anomaly & Drift Intelligence Engine Tests.

Validates:
A. Drift Detection (baseline, deviation, velocity)
B. Event Pattern Mining (sequences, rare, bursts, cycles)
C. Cross-Domain Anomaly Graph
D. Temporal Drift Analysis
E. Replay-Based Anomaly Reconstruction
F. Consistency Deviation Analysis
G. Gateway Integration
H. Determinism
I. No Prescription/Recommendation Paths
"""
import unittest
from datetime import datetime, timedelta
from typing import Any, Dict, List

from core.operations.truth.models import Domain, SourceType
from core.operations.truth.event_store import EventStore, EventFactory, get_event_store
from core.operations.intelligence.models import (
    DriftReport, BaselineReference, DeviationVector, DriftDirection,
    EventPattern, PatternType, ConfidenceLevel,
    AnomalyGraph, TemporalDriftReport, AnomalyTimeline,
    ConsistencyDeviationReport,
)
from core.operations.intelligence.drift import DriftDetectionEngine
from core.operations.intelligence.patterns import EventPatternMiningEngine
from core.operations.intelligence.anomaly_graph import CrossDomainAnomalyGraphEngine
from core.operations.intelligence.temporal import TemporalDriftAnalyzer
from core.operations.intelligence.reconstruction import ReplayAnomalyReconstructionEngine
from core.operations.intelligence.consistency import ConsistencyDeviationAnalyzer
from core.operations.intelligence.gateway import AnomalyIntelligenceGateway, get_gateway, reset_gateway


def _make_event(
    event_type: str = "stock_movement",
    domain: Domain = Domain.INVENTORY,
    aggregate_id: str = "test_001",
    payload: Dict[str, Any] = None,
    source_type: SourceType = SourceType.REAL,
    sequence: int = 1,
    correlation_id: str = "",
    causation_id: str = "",
) -> Any:
    meta = {}
    if correlation_id:
        meta["correlation_id"] = correlation_id
    if causation_id:
        meta["causation_id"] = causation_id
    return EventFactory.create_event(
        source_type=source_type,
        domain=domain,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        metadata=meta,
        sequence=sequence,
    )


def _seed_test_data(store: EventStore) -> None:
    """Seed events across multiple domains for analysis."""
    corr = "corr_test_001"
    store.append(_make_event("order_created", Domain.SALES_PURCHASE, "ord_001",
                             {"order_type": "SALE", "total_amount": 1000},
                             sequence=1, correlation_id=corr))
    store.append(_make_event("stock_movement", Domain.INVENTORY, "batch_001",
                             {"product_id": "p1", "quantity": 10, "direction": "out"},
                             sequence=1, correlation_id=corr))
    store.append(_make_event("journal_entry_posted", Domain.ACCOUNTING, "je_001",
                             {"description": "Sale", "entries": [{"debit": 1000, "credit": 0}, {"debit": 0, "credit": 1000}]},
                             sequence=1, correlation_id=corr))
    store.append(_make_event("employee_hired", Domain.HR, "emp_001",
                             {"name": "John", "department": "Sales", "position": "Rep"},
                             sequence=1))
    store.append(_make_event("stock_movement", Domain.INVENTORY, "batch_001",
                             {"product_id": "p1", "quantity": 5, "direction": "in"},
                             sequence=2))

    for i in range(3):
        store.append(_make_event("stock_movement", Domain.INVENTORY, f"batch_{i}",
                                 {"product_id": f"p{i}", "quantity": i * 10, "direction": "out"},
                                 sequence=i + 1))


# ═══════════════════════════════════════════════════════════
# A. DRIFT DETECTION
# ═══════════════════════════════════════════════════════════

class DriftDetectionTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_compute_baseline(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        baseline = engine.compute_baseline(Domain.INVENTORY)
        self.assertGreater(baseline.total_events_in_window, 0)
        self.assertGreater(len(baseline.window_start), 0)

    def test_detect_drift(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertEqual(report.entity_id, "batch_001")
        self.assertIsNotNone(report.deviation_vector)

    def test_drift_report_has_baseline(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertIsNotNone(report.baseline_reference)

    def test_drift_report_has_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertIn(report.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))

    def test_drift_report_has_model_limitations(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertIsNotNone(report.model_limitations)

    def test_detect_drift_all_aggregates(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        reports = engine.detect_drift_all_aggregates(Domain.INVENTORY)
        self.assertGreater(len(reports), 0)

    def test_drift_empty_aggregate(self):
        engine = DriftDetectionEngine(get_event_store())
        report = engine.detect_drift(Domain.INVENTORY, "nonexistent")
        self.assertEqual(report.entity_id, "nonexistent")

    def test_drift_velocity(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertGreaterEqual(report.drift_velocity, 0)


# ═══════════════════════════════════════════════════════════
# B. EVENT PATTERN MINING
# ═══════════════════════════════════════════════════════════

class EventPatternMiningTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_mine_frequent_sequences(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.mine_frequent_sequences(Domain.INVENTORY)
        for p in patterns:
            self.assertEqual(p.pattern_type, PatternType.FREQUENT_SEQUENCE)

    def test_detect_rare_events(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.detect_rare_events(Domain.INVENTORY)
        for p in patterns:
            self.assertEqual(p.pattern_type, PatternType.RARE_EVENT)

    def test_detect_bursts(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.detect_bursts(Domain.INVENTORY)
        for p in patterns:
            self.assertEqual(p.pattern_type, PatternType.BURST_DETECTION)

    def test_detect_cycles(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.detect_cycles(Domain.INVENTORY)
        for p in patterns:
            self.assertEqual(p.pattern_type, PatternType.CYCLIC_PATTERN)

    def test_mine_all_patterns(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        all_patterns = engine.mine_all_patterns(Domain.INVENTORY)
        self.assertIn("frequent_sequences", all_patterns)
        self.assertIn("rare_events", all_patterns)
        self.assertIn("bursts", all_patterns)
        self.assertIn("cycles", all_patterns)

    def test_patterns_have_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.mine_frequent_sequences(Domain.INVENTORY)
        for p in patterns:
            self.assertIn(p.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))

    def test_patterns_have_model_limitations(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = EventPatternMiningEngine(store)
        patterns = engine.mine_frequent_sequences(Domain.INVENTORY)
        for p in patterns:
            self.assertIsNotNone(p.model_limitations)

    def test_empty_store_patterns(self):
        engine = EventPatternMiningEngine(get_event_store())
        self.assertEqual(len(engine.mine_frequent_sequences(Domain.INVENTORY)), 0)
        self.assertEqual(len(engine.detect_rare_events(Domain.INVENTORY)), 0)
        self.assertEqual(len(engine.detect_bursts(Domain.INVENTORY)), 0)
        self.assertEqual(len(engine.detect_cycles(Domain.INVENTORY)), 0)


# ═══════════════════════════════════════════════════════════
# C. CROSS-DOMAIN ANOMALY GRAPH
# ═══════════════════════════════════════════════════════════

class AnomalyGraphTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_build_anomaly_graph(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = CrossDomainAnomalyGraphEngine(store)
        graph = engine.build_anomaly_graph(Domain.SALES_PURCHASE)
        self.assertIsNotNone(graph)
        self.assertIn("sales_purchase", graph.domains_involved)

    def test_build_cross_domain_graph(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = CrossDomainAnomalyGraphEngine(store)
        graph = engine.build_cross_domain_graph()
        self.assertGreater(len(graph.domains_involved), 0)

    def test_graph_has_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = CrossDomainAnomalyGraphEngine(store)
        graph = engine.build_anomaly_graph(Domain.INVENTORY)
        self.assertIn(graph.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))

    def test_graph_has_limitations(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = CrossDomainAnomalyGraphEngine(store)
        graph = engine.build_anomaly_graph(Domain.INVENTORY)
        self.assertIsNotNone(graph.model_limitations)


# ═══════════════════════════════════════════════════════════
# D. TEMPORAL DRIFT
# ═══════════════════════════════════════════════════════════

class TemporalDriftTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_analyze_temporal_drift(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = TemporalDriftAnalyzer(store)
        report = engine.analyze_temporal_drift(Domain.INVENTORY)
        self.assertIsNotNone(report)
        self.assertIn(report.overall_trend, (DriftDirection.INCREASING, DriftDirection.DECREASING,
                                              DriftDirection.STABLE, DriftDirection.UNKNOWN))

    def test_temporal_has_segments(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = TemporalDriftAnalyzer(store)
        report = engine.analyze_temporal_drift(Domain.INVENTORY)
        self.assertGreater(len(report.segments), 0)

    def test_temporal_has_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = TemporalDriftAnalyzer(store)
        report = engine.analyze_temporal_drift(Domain.INVENTORY)
        self.assertIn(report.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))

    def test_empty_store_temporal(self):
        engine = TemporalDriftAnalyzer(get_event_store())
        report = engine.analyze_temporal_drift(Domain.INVENTORY)
        self.assertEqual(report.confidence_level, ConfidenceLevel.LOW)

    def test_temporal_has_acceleration(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = TemporalDriftAnalyzer(store)
        report = engine.analyze_temporal_drift(Domain.INVENTORY)
        self.assertGreaterEqual(report.acceleration, 0)


# ═══════════════════════════════════════════════════════════
# E. ANOMALY RECONSTRUCTION
# ═══════════════════════════════════════════════════════════

class AnomalyReconstructionTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_reconstruct_from_aggregate(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ReplayAnomalyReconstructionEngine(store)
        timeline = engine.reconstruct_from_aggregate(Domain.INVENTORY, "batch_001")
        self.assertGreater(timeline.event_count, 0)
        self.assertGreater(len(timeline.integrity_hash), 0)

    def test_reconstruct_includes_roles(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ReplayAnomalyReconstructionEngine(store)
        timeline = engine.reconstruct_from_aggregate(Domain.INVENTORY, "batch_001")
        roles = set(e.role for e in timeline.full_event_chain)
        self.assertIn("FIRST_OCCURRENCE", roles)
        self.assertIn("DOWNSTREAM_EFFECT", roles)

    def test_reconstruct_has_affected_domains(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ReplayAnomalyReconstructionEngine(store)
        timeline = engine.reconstruct_from_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(len(timeline.affected_domains), 0)

    def test_reconstruct_empty_aggregate(self):
        engine = ReplayAnomalyReconstructionEngine(get_event_store())
        timeline = engine.reconstruct_from_aggregate(Domain.INVENTORY, "nonexistent")
        self.assertEqual(timeline.event_count, 0)
        self.assertEqual(timeline.confidence_level, ConfidenceLevel.LOW)

    def test_find_anomaly_clusters(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ReplayAnomalyReconstructionEngine(store)
        clusters = engine.find_anomaly_clusters(Domain.INVENTORY)
        self.assertGreater(len(clusters), 0)

    def test_reconstruct_has_temporal_spread(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ReplayAnomalyReconstructionEngine(store)
        timeline = engine.reconstruct_from_aggregate(Domain.INVENTORY, "batch_001")
        self.assertGreaterEqual(timeline.temporal_spread_seconds, 0)


# ═══════════════════════════════════════════════════════════
# F. CONSISTENCY DEVIATION
# ═══════════════════════════════════════════════════════════

class ConsistencyDeviationTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_analyze_deviations(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ConsistencyDeviationAnalyzer(store)
        reports = engine.analyze_deviations()
        self.assertIsNotNone(reports)

    def test_compare_with_truth_layer(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ConsistencyDeviationAnalyzer(store)
        report = engine.compare_with_truth_layer({"inventory": 10})
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.deviation_score, 0)

    def test_consistency_has_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = ConsistencyDeviationAnalyzer(store)
        reports = engine.analyze_deviations()
        for r in reports:
            self.assertIn(r.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))


# ═══════════════════════════════════════════════════════════
# G. GATEWAY INTEGRATION
# ═══════════════════════════════════════════════════════════

class IntelligenceGatewayTest(unittest.TestCase):
    def setUp(self):
        reset_gateway()

    def test_compute_baseline(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        baseline = gateway.compute_baseline("inventory")
        self.assertIsNotNone(baseline)

    def test_detect_drift(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        report = gateway.detect_drift("inventory", "batch_001")
        self.assertIsNotNone(report)

    def test_mine_patterns(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        patterns = gateway.mine_frequent_sequences("inventory")
        self.assertIsNotNone(patterns)

    def test_build_anomaly_graph(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        graph = gateway.build_anomaly_graph("inventory")
        self.assertIsNotNone(graph)

    def test_analyze_temporal(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        report = gateway.analyze_temporal_drift("inventory")
        self.assertIsNotNone(report)

    def test_reconstruct_anomaly(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        timeline = gateway.reconstruct_anomaly("inventory", "batch_001")
        self.assertIsNotNone(timeline)

    def test_analyze_consistency(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        reports = gateway.analyze_consistency_deviations()
        self.assertIsNotNone(reports)

    def test_get_snapshot(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        snap = gateway.get_snapshot()
        self.assertIsNotNone(snap)

    def test_get_status(self):
        gateway = get_gateway()
        status = gateway.get_status()
        self.assertIn("gateway_version", status)
        self.assertEqual(status["engine_status"], "read_only")

    def test_detect_rare_events(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        patterns = gateway.detect_rare_events("inventory")
        self.assertIsNotNone(patterns)

    def test_detect_bursts(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        patterns = gateway.detect_bursts("inventory")
        self.assertIsNotNone(patterns)

    def test_detect_cycles(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        patterns = gateway.detect_cycles("inventory")
        self.assertIsNotNone(patterns)

    def test_cross_domain_graph(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        graph = gateway.build_cross_domain_graph()
        self.assertIsNotNone(graph)

    def test_compare_with_truth_layer(self):
        store = get_event_store()
        _seed_test_data(store)
        gateway = get_gateway()
        report = gateway.compare_with_truth_layer({"inventory": 5})
        self.assertIsNotNone(report)


# ═══════════════════════════════════════════════════════════
# H. DETERMINISM
# ═══════════════════════════════════════════════════════════

class IntelligenceDeterminismTest(unittest.TestCase):
    def test_drift_deterministic(self):
        store = EventStore()
        _seed_test_data(store)
        e1 = DriftDetectionEngine(store)
        e2 = DriftDetectionEngine(store)
        r1 = e1.detect_drift(Domain.INVENTORY, "batch_001")
        r2 = e2.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertEqual(r1.drift_score, r2.drift_score)
        self.assertEqual(r1.drift_velocity, r2.drift_velocity)

    def test_patterns_deterministic(self):
        store = EventStore()
        _seed_test_data(store)
        e1 = EventPatternMiningEngine(store)
        e2 = EventPatternMiningEngine(store)
        p1 = e1.mine_frequent_sequences(Domain.INVENTORY)
        p2 = e2.mine_frequent_sequences(Domain.INVENTORY)
        self.assertEqual(len(p1), len(p2))

    def test_temporal_deterministic(self):
        store = EventStore()
        _seed_test_data(store)
        e1 = TemporalDriftAnalyzer(store)
        e2 = TemporalDriftAnalyzer(store)
        r1 = e1.analyze_temporal_drift(Domain.INVENTORY)
        r2 = e2.analyze_temporal_drift(Domain.INVENTORY)
        self.assertEqual(len(r1.segments), len(r2.segments))

    def test_reconstruction_deterministic(self):
        store = EventStore()
        _seed_test_data(store)
        e1 = ReplayAnomalyReconstructionEngine(store)
        e2 = ReplayAnomalyReconstructionEngine(store)
        t1 = e1.reconstruct_from_aggregate(Domain.INVENTORY, "batch_001")
        t2 = e2.reconstruct_from_aggregate(Domain.INVENTORY, "batch_001")
        self.assertEqual(t1.integrity_hash, t2.integrity_hash)


# ═══════════════════════════════════════════════════════════
# I. NO PRESCRIPTION PATHS
# ═══════════════════════════════════════════════════════════

class NoPrescriptionTest(unittest.TestCase):
    def test_gateway_no_execution_methods(self):
        gateway = AnomalyIntelligenceGateway()
        self.assertFalse(hasattr(gateway, 'execute'))
        self.assertFalse(hasattr(gateway, 'recommend'))
        self.assertFalse(hasattr(gateway, 'suggest'))
        self.assertFalse(hasattr(gateway, 'trigger'))
        self.assertFalse(hasattr(gateway, 'fix'))
        self.assertFalse(hasattr(gateway, 'optimize'))
        self.assertFalse(hasattr(gateway, 'prioritize'))

    def test_reports_have_limitations(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertIsNotNone(report.model_limitations)
        self.assertGreater(len(report.model_limitations.statistical_approximations), 0)

    def test_reports_have_confidence(self):
        store = get_event_store()
        _seed_test_data(store)
        engine = DriftDetectionEngine(store)
        report = engine.detect_drift(Domain.INVENTORY, "batch_001")
        self.assertIn(report.confidence_level, (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH))

    def test_models_immutable(self):
        report = DriftReport(domain="test", entity_id="test")
        with self.assertRaises(AttributeError):
            report.drift_score = 100.0

    def test_no_erp_imports(self):
        import sys
        intel_mods = [m for m in sys.modules if 'core.operations.intelligence' in m]
        for mod_name in intel_mods:
            mod = sys.modules.get(mod_name)
            if mod:
                for erp in ['inventory', 'accounting', 'sales', 'purchases', 'hr', 'payroll']:
                    if erp != 'intelligence':
                        self.assertNotIn(f'backend.{erp}', str(getattr(mod, '__file__', '')))


if __name__ == '__main__':
    unittest.main()
