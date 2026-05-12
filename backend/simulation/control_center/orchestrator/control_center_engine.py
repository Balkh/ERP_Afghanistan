"""Central orchestration engine for the Operational Intelligence Control Center.

Orchestrates state, timeline, incidents, dashboard, reporting, and safety
subcomponents into a unified signal processing and snapshot pipeline.
Strictly read-only. All memory structures are bounded. Exception-safe.
"""
import uuid
import logging
from typing import Any, Dict, List

from simulation.control_center.models import (
    AggregatedState, DashboardSnapshot, IncidentRecord, IncidentStatus,
    IntelligenceSeverity, OperationalSignal, OperationalState,
    SafetyReport, SignalType, UnifiedTimelineEvent,
)
from simulation.control_center.state.operational_state_aggregator import (
    OperationalStateAggregator,
)
from simulation.control_center.state.system_health_matrix import SystemHealthMatrix
from simulation.control_center.state.intelligence_state_classifier import (
    IntelligenceStateClassifier,
)
from simulation.control_center.state.operational_priority_engine import (
    OperationalPriorityEngine,
)
from simulation.control_center.timeline.unified_timeline import UnifiedTimeline
from simulation.control_center.timeline.intelligence_timeline_builder import (
    IntelligenceTimelineBuilder,
)
from simulation.control_center.timeline.cross_phase_correlator import (
    CrossPhaseCorrelator,
)
from simulation.control_center.timeline.operational_sequence_tracker import (
    OperationalSequenceTracker,
)
from simulation.control_center.incidents.incident_registry import IncidentRegistry
from simulation.control_center.incidents.incident_classifier import IncidentClassifier
from simulation.control_center.incidents.incident_lifecycle import IncidentLifecycle
from simulation.control_center.incidents.escalation_engine import EscalationEngine
from simulation.control_center.dashboard.dashboard_models import DashboardModelFactory
from simulation.control_center.dashboard.stability_widgets import StabilityWidgets
from simulation.control_center.dashboard.health_summary import HealthSummary
from simulation.control_center.dashboard.operational_heatmap import OperationalHeatmap
from simulation.control_center.reporting.executive_summary import ExecutiveSummary
from simulation.control_center.reporting.operational_risk_report import (
    OperationalRiskReport,
)
from simulation.control_center.reporting.intelligence_digest import IntelligenceDigest
from simulation.control_center.reporting.system_stability_report import (
    SystemStabilityReport,
)
from simulation.control_center.safety.recursion_guard import RecursionGuard
from simulation.control_center.safety.graph_explosion_guard import GraphExplosionGuard
from simulation.control_center.safety.memory_pressure_guard import MemoryPressureGuard
from simulation.control_center.safety.orchestration_safety_monitor import (
    OrchestrationSafetyMonitor,
)

logger = logging.getLogger(__name__)


def _resolve_drift_visualization():
    try:
        from simulation.control_center.dashboard.drift_visualization import DriftVisualization
        return DriftVisualization
    except ImportError:
        from collections import deque as _deque

        class _Fallback:
            def __init__(self, max_data_points: int = 500):
                self._data_points = _deque(maxlen=max_data_points)
                self._max_data_points = max_data_points

            def add_data_point(self, *args: Any, **kwargs: Any) -> None:
                pass

            def get_data_points(self) -> List[Dict[str, Any]]:
                return []

            def get_visualization(self) -> Dict[str, Any]:
                return {
                    "data_points": [],
                    "count": 0,
                    "max_data_points": self._max_data_points,
                }

            def get_data_point_count(self) -> int:
                return len(self._data_points)

            def clear(self) -> None:
                self._data_points.clear()

        return _Fallback


_DriftVisualizationCls = _resolve_drift_visualization()


class ControlCenterEngine:
    """Central orchestrator for all Control Center subcomponents.

    Owns all subcomponent instances and exposes a unified pipeline for
    signal processing, dashboard snapshots, safety reports, and queries.
    """

    _CONTAINER_MAXLENS: Dict[str, int] = {
        "state_aggregator": 1000,
        "health_matrix": 500,
        "state_classifier": 200,
        "priority_engine": 200,
        "unified_timeline": 1000,
        "cross_phase_correlator": 500,
        "operational_sequence_tracker": 200,
        "incident_registry": 500,
        "incident_lifecycle": 500,
        "escalation_engine": 200,
        "dashboard_factory": 100,
        "stability_widgets": 200,
        "health_summary": 100,
        "heatmap": 500,
        "drift_visualization": 500,
        "executive_summary": 100,
        "risk_report": 100,
        "intelligence_digest": 100,
        "stability_report": 100,
        "recursion_guard": 500,
        "graph_explosion_guard": 200,
        "memory_pressure_guard": 200,
        "safety_monitor": 100,
    }

    def __init__(self) -> None:
        # ── State subcomponents ──
        self._state_aggregator = OperationalStateAggregator(max_signals=1000)
        self._health_matrix = SystemHealthMatrix(max_history=500)
        self._state_classifier = IntelligenceStateClassifier(max_history=200)
        self._priority_engine = OperationalPriorityEngine(max_history=200)

        # ── Timeline subcomponents ──
        self._unified_timeline = UnifiedTimeline(max_events=1000)
        self._timeline_builder = IntelligenceTimelineBuilder()
        self._cross_phase_correlator = CrossPhaseCorrelator(max_correlations=500)
        self._sequence_tracker = OperationalSequenceTracker(max_sequences=200)

        # ── Incidents subcomponents ──
        self._incident_registry = IncidentRegistry(max_incidents=500)
        self._incident_classifier = IncidentClassifier()
        self._incident_lifecycle = IncidentLifecycle(max_history=500)
        self._escalation_engine = EscalationEngine(max_escalations=200)

        # ── Dashboard subcomponents ──
        self._dashboard_factory = DashboardModelFactory(max_snapshots=100)
        self._stability_widgets = StabilityWidgets(max_history=200)
        self._health_summary = HealthSummary(max_summaries=100)
        self._heatmap = OperationalHeatmap(max_cells=500)
        self._drift_visualization: Any = _DriftVisualizationCls(max_data_points=500)

        # ── Reporting subcomponents ──
        self._executive_summary = ExecutiveSummary(max_reports=100)
        self._risk_report = OperationalRiskReport(max_reports=100)
        self._intelligence_digest = IntelligenceDigest(max_digests=100)
        self._stability_report = SystemStabilityReport(max_reports=100)

        # ── Safety subcomponents ──
        self._recursion_guard = RecursionGuard(max_depth=100, max_history=500)
        self._graph_guard = GraphExplosionGuard(
            max_nodes=1000, max_edges=5000, max_history=200
        )
        self._memory_guard = MemoryPressureGuard(
            max_pressure_threshold=0.9, max_history=200
        )
        self._safety_monitor = OrchestrationSafetyMonitor(max_reports=100)
        self._safety_monitor.init_subcomponents(
            self._recursion_guard,
            self._graph_guard,
            self._memory_guard,
        )

        self._orchestration_count: int = 0
        self._max_orchestration_depth: int = 100000

    # ──────────────────────────────────────────────
    # Signal Processing Pipeline
    # ──────────────────────────────────────────────

    def process_signal(self, signal: OperationalSignal) -> Dict[str, Any]:
        """Orchestrate the full signal processing pipeline.

        1. Depth check → 2. Ingest → 3. Build timeline event →
        4. Add to timeline → 5. Classify & register incident →
        6. Evaluate escalation → 7. Aggregate, compute health, classify.
        """
        try:
            self._orchestration_count += 1
            if self._orchestration_count > self._max_orchestration_depth:
                return {
                    "signal_id": signal.signal_id,
                    "success": False,
                    "error": (
                        f"orchestration depth {self._orchestration_count}"
                        f" exceeds max {self._max_orchestration_depth}"
                    ),
                }

            ingest_result = self._state_aggregator.ingest_signal(
                signal_id=signal.signal_id,
                signal_type=signal.signal_type,
                severity=signal.severity,
                source_phase=signal.source_phase,
                tick=signal.tick,
                description=signal.description,
                payload=dict(signal.payload),
            )

            timeline_event = self._timeline_builder.build_from_signal(
                signal, signal.tick
            )
            self._unified_timeline.add_event(
                event_id=timeline_event.event_id,
                tick=timeline_event.tick,
                source_phase=timeline_event.source_phase,
                event_type=timeline_event.event_type,
                description=timeline_event.description,
                severity=timeline_event.severity,
                payload=timeline_event.payload,
                related_event_ids=timeline_event.related_event_ids,
            )

            classification = self._incident_classifier.classify_signal(signal)
            incident_registered: IncidentRecord | None = None
            if classification.get("requires_escalation"):
                incident_id = f"inc_{signal.signal_id}"
                incident_registered = self._incident_registry.register_incident(
                    incident_id=incident_id,
                    signal_type=signal.signal_type,
                    severity=signal.severity,
                    tick=signal.tick,
                    description=signal.description,
                    details=dict(signal.payload),
                )

            escalation_result: Dict[str, Any] | None = None
            if incident_registered is not None:
                escalation_result = self._escalation_engine.evaluate_escalation(
                    incident=incident_registered,
                    tick=signal.tick,
                    active_incident_count=self._incident_registry.get_incident_count(),
                )

            aggregated = self._state_aggregator.aggregate_state()
            health_result = self._health_matrix.compute_health(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                active_signals=aggregated.active_signals,
                source_summaries=aggregated.source_summaries,
            )
            state_classification = self._state_classifier.classify(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                active_signals=aggregated.active_signals,
                source_count=len(aggregated.source_summaries),
            )

            self._recursion_guard.record_call("process_signal", self._orchestration_count)

            return {
                "signal_id": signal.signal_id,
                "success": True,
                "ingest": ingest_result,
                "timeline_event_id": timeline_event.event_id,
                "classification": classification,
                "incident": {
                    "registered": incident_registered is not None,
                    "incident_id": incident_registered.incident_id
                    if incident_registered is not None
                    else None,
                },
                "escalation": escalation_result,
                "aggregated_state": {
                    "state": aggregated.state.value,
                    "severity_score": aggregated.severity_score,
                    "active_signals": aggregated.active_signals,
                },
                "health": health_result,
                "state_classification": state_classification,
            }

        except Exception:
            logger.exception("process_signal failed for signal %s", signal.signal_id)
            return {
                "signal_id": signal.signal_id,
                "success": False,
                "error": f"process_signal failed for {signal.signal_id}",
            }

    # ──────────────────────────────────────────────
    # Dashboard Snapshot Generation
    # ──────────────────────────────────────────────

    def generate_dashboard_snapshot(self, tick: int) -> DashboardSnapshot:
        """Orchestrate full dashboard snapshot generation from all subcomponents."""
        try:
            aggregated = self._state_aggregator.aggregate_state()
            health_result = self._health_matrix.compute_health(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                active_signals=aggregated.active_signals,
                source_summaries=aggregated.source_summaries,
            )
            classification = self._state_classifier.classify(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                active_signals=aggregated.active_signals,
                source_count=len(aggregated.source_summaries),
            )
            priority_result = self._priority_engine.compute_priority(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                source_count=len(aggregated.source_summaries),
                cascading_risk=classification.get("cascading_risk", False),
            )
            stability = self._stability_widgets.compute_stability_score(
                severity_score=aggregated.severity_score,
                critical_count=aggregated.critical_count,
                incident_count=aggregated.incident_count,
                active_signals=aggregated.active_signals,
                cascading_risk=classification.get("cascading_risk", False),
            )
            summary_data = self._health_summary.generate_summary(
                health_status=health_result.get("status", "unknown"),
                health_score=health_result.get("health_score", 0.0),
                operational_state=classification.get("operational_state", "unknown"),
                active_signals=aggregated.active_signals,
                active_incidents=aggregated.incident_count,
                sources_monitored=len(aggregated.source_summaries),
            )

            events = self._unified_timeline.get_events(limit=50)
            heatmap = self._heatmap.build_heatmap(
                list(self._state_aggregator._signals)
            )
            drift_viz = self._drift_visualization.build_drift_series()

            active_incidents = self._incident_registry.get_active_incidents()
            escalations = self._escalation_engine.get_escalation_summary()

            snapshot_id = f"snapshot_{tick}"
            snapshot = self._dashboard_factory.create_snapshot(
                snapshot_id=snapshot_id,
                tick=tick,
                operational_state=classification.get("operational_state", "unknown"),
                stability_score=stability.get("stability_score", 0.5),
                health_status=health_result.get("status", "unknown"),
                active_incidents=aggregated.incident_count,
                widget_data={
                    "aggregated_state": {
                        "state": aggregated.state.value,
                        "severity_score": aggregated.severity_score,
                        "active_signals": aggregated.active_signals,
                        "critical_count": aggregated.critical_count,
                        "incident_count": aggregated.incident_count,
                    },
                    "health": health_result,
                    "classification": classification,
                    "priority": priority_result,
                    "stability": stability,
                    "health_summary": summary_data,
                    "heatmap": heatmap,
                    "drift_visualization": drift_viz,
                    "timeline_preview": [
                        {
                            "event_id": e.event_id,
                            "tick": e.tick,
                            "event_type": e.event_type,
                            "severity": e.severity.value,
                            "description": e.description,
                        }
                        for e in events[:10]
                    ],
                    "active_incidents": [
                        {
                            "incident_id": inc.incident_id,
                            "severity": inc.severity.value,
                            "status": inc.status.value,
                            "description": inc.description,
                        }
                        for inc in active_incidents[:10]
                    ],
                    "escalations": escalations,
                    "health_trend": self._health_matrix.get_health_trend(),
                    "stability_trend": self._stability_widgets.get_stability_trend(),
                    "timeline_event_count": self._unified_timeline.get_event_count(),
                    "correlation_count": (
                        self._cross_phase_correlator.get_correlation_count()
                    ),
                    "sequence_count": (
                        self._sequence_tracker.get_sequence_count()
                    ),
                    "transition_count": (
                        self._incident_lifecycle.get_transition_count()
                    ),
                },
                summary=summary_data.get("summary_text", ""),
            )

            if snapshot is None:
                return DashboardSnapshot(
                    snapshot_id=snapshot_id,
                    tick=tick,
                    operational_state="unknown",
                    stability_score=0.0,
                    health_status="unknown",
                    active_incidents=0,
                )

            return snapshot

        except Exception:
            logger.exception("generate_dashboard_snapshot failed at tick %s", tick)
            return DashboardSnapshot(
                snapshot_id=f"snapshot_{tick}",
                tick=tick,
                operational_state="unknown",
                stability_score=0.0,
                health_status="unknown",
                active_incidents=0,
            )

    # ──────────────────────────────────────────────
    # Safety Report Generation
    # ──────────────────────────────────────────────

    def generate_safety_report(self, context: str = "") -> SafetyReport:
        """Run a full safety check across all bounded containers."""
        try:
            container_sizes: Dict[str, int] = {}
            container_maxlens: Dict[str, int] = {}

            self._populate_container_info(container_sizes, container_maxlens)

            report_id = f"safety_{uuid.uuid4().hex[:8]}"
            return self._safety_monitor.perform_safety_check(
                report_id=report_id,
                current_depth=self._orchestration_count,
                node_count=self._graph_guard.get_check_count(),
                edge_count=0,
                container_sizes=container_sizes,
                container_maxlens=container_maxlens,
                context=context,
            )

        except Exception:
            logger.exception("generate_safety_report failed")
            return SafetyReport(
                report_id=f"safety_{uuid.uuid4().hex[:8]}",
                is_safe=False,
                recursion_depth=self._orchestration_count,
                graph_size=0,
                memory_pressure=1.0,
                violations=["generate_safety_report failed with unexpected error"],
                details={"error": True},
            )

    def _populate_container_info(
        self,
        sizes: Dict[str, int],
        maxlens: Dict[str, int],
    ) -> None:
        """Collect current sizes and maxlens for all bounded containers."""
        size_sources: Dict[str, int] = {
            "state_aggregator": self._state_aggregator.get_signal_count(),
            "unified_timeline": self._unified_timeline.get_event_count(),
            "cross_phase_correlator": (
                self._cross_phase_correlator.get_correlation_count()
            ),
            "sequence_tracker": self._sequence_tracker.get_sequence_count(),
            "incident_registry": self._incident_registry.get_incident_count(),
            "incident_lifecycle": self._incident_lifecycle.get_transition_count(),
            "escalation_engine": self._escalation_engine.get_escalation_count(),
            "dashboard_factory": self._dashboard_factory.get_snapshot_count(),
            "stability_widgets": len(self._stability_widgets._score_history),
            "health_summary": len(self._health_summary._summary_history),
            "heatmap": len(self._heatmap._cell_history),
            "drift_visualization": self._drift_visualization.get_drift_data_point_count(),
            "executive_summary": self._executive_summary.get_report_count(),
            "risk_report": self._risk_report.get_report_count(),
            "intelligence_digest": self._intelligence_digest.get_digest_count(),
            "stability_report": self._stability_report.get_report_count(),
            "recursion_guard": self._recursion_guard.get_call_count(),
            "graph_explosion_guard": self._graph_guard.get_check_count(),
            "memory_pressure_guard": self._memory_guard.get_check_count(),
            "safety_monitor": self._safety_monitor.get_report_count(),
        }
        sizes.update(size_sources)
        maxlens.update(self._CONTAINER_MAXLENS)

    # ──────────────────────────────────────────────
    # Delegation Getters
    # ──────────────────────────────────────────────

    def get_aggregated_state(self) -> AggregatedState:
        """Get the current aggregated operational state."""
        try:
            return self._state_aggregator.aggregate_state()
        except Exception:
            logger.exception("get_aggregated_state failed")
            return AggregatedState(
                state=OperationalState.NORMAL,
                severity_score=0.0,
                active_signals=0,
                critical_count=0,
                incident_count=0,
            )

    def get_unified_timeline(self) -> UnifiedTimeline:
        """Get the unified timeline instance."""
        return self._unified_timeline

    def get_incident_registry(self) -> IncidentRegistry:
        """Get the incident registry instance."""
        return self._incident_registry

    # ──────────────────────────────────────────────
    # Health / Subcomponent Accessors
    # ──────────────────────────────────────────────

    def get_health_matrix(self) -> SystemHealthMatrix:
        return self._health_matrix

    def get_state_classifier(self) -> IntelligenceStateClassifier:
        return self._state_classifier

    def get_priority_engine(self) -> OperationalPriorityEngine:
        return self._priority_engine

    def get_stability_widgets(self) -> StabilityWidgets:
        return self._stability_widgets

    def get_health_summary(self) -> HealthSummary:
        return self._health_summary

    def get_heatmap(self) -> OperationalHeatmap:
        return self._heatmap

    def get_drift_visualization(self) -> Any:
        return self._drift_visualization

    def get_dashboard_factory(self) -> DashboardModelFactory:
        return self._dashboard_factory

    def get_executive_summary(self) -> ExecutiveSummary:
        return self._executive_summary

    def get_risk_report(self) -> OperationalRiskReport:
        return self._risk_report

    def get_intelligence_digest(self) -> IntelligenceDigest:
        return self._intelligence_digest

    def get_stability_report(self) -> SystemStabilityReport:
        return self._stability_report

    def get_safety_monitor(self) -> OrchestrationSafetyMonitor:
        return self._safety_monitor

    def get_recursion_guard(self) -> RecursionGuard:
        return self._recursion_guard

    def get_graph_guard(self) -> GraphExplosionGuard:
        return self._graph_guard

    def get_memory_guard(self) -> MemoryPressureGuard:
        return self._memory_guard

    def get_cross_phase_correlator(self) -> CrossPhaseCorrelator:
        return self._cross_phase_correlator

    def get_sequence_tracker(self) -> OperationalSequenceTracker:
        return self._sequence_tracker

    def get_incident_lifecycle(self) -> IncidentLifecycle:
        return self._incident_lifecycle

    def get_escalation_engine(self) -> EscalationEngine:
        return self._escalation_engine

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    def clear_all(self) -> None:
        """Clear all subcomponent state. Resets orchestration count."""
        try:
            self._state_aggregator.clear()
            self._health_matrix.clear()
            self._state_classifier.clear()
            self._priority_engine.clear()
            self._unified_timeline.clear()
            self._cross_phase_correlator.clear()
            self._sequence_tracker.clear()
            self._incident_registry.clear()
            self._incident_lifecycle.clear()
            self._escalation_engine.clear()
            self._dashboard_factory.clear()
            self._stability_widgets.clear()
            self._health_summary.clear()
            self._heatmap.clear()
            self._drift_visualization.clear()
            self._executive_summary.clear()
            self._risk_report.clear()
            self._intelligence_digest.clear()
            self._stability_report.clear()
            self._recursion_guard.clear()
            self._graph_guard.clear()
            self._memory_guard.clear()
            self._safety_monitor.clear()
            self._orchestration_count = 0
        except Exception:
            logger.exception("clear_all encountered an error")

    def clear(self) -> None:
        """Alias for clear_all() for compatibility."""
        return self.clear_all()

    def get_orchestration_count(self) -> int:
        """Get the total number of signals processed."""
        return self._orchestration_count
