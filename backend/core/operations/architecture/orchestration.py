"""
Phase 5A.5.5 — Orchestration Flow Map & Interaction Graph.

Maps the signal processing pipeline, query routing paths,
and control center interaction topology. Read-only analysis.

No runtime mutation. Deterministic output.
"""
from typing import Any, Dict, List


SIGNAL_PIPELINE = {
    "name": "operational_signal_pipeline",
    "version": "1.0.0",
    "entry": "ControlCenterRouter.route_signal",
    "steps": [
        {
            "step": 1,
            "name": "depth_check",
            "component": "ControlCenterEngine",
            "action": "verify orchestration_count <= max_orchestration_depth",
        },
        {
            "step": 2,
            "name": "signal_ingest",
            "component": "OperationalStateAggregator.ingest_signal",
            "action": "store signal in bounded deque",
        },
        {
            "step": 3,
            "name": "timeline_event_build",
            "component": "IntelligenceTimelineBuilder.build_from_signal",
            "action": "convert signal to timeline event",
        },
        {
            "step": 4,
            "name": "event_add_to_timeline",
            "component": "UnifiedTimeline.add_event",
            "action": "append event to bounded deque",
        },
        {
            "step": 5,
            "name": "incident_classification",
            "component": "IncidentClassifier.classify_signal",
            "action": "determine if signal requires escalation",
        },
        {
            "step": 6,
            "name": "incident_registration",
            "component": "IncidentRegistry.register_incident",
            "action": "optionally create incident record",
        },
        {
            "step": 7,
            "name": "escalation_evaluation",
            "component": "EscalationEngine.evaluate_escalation",
            "action": "optionally escalate incident",
        },
        {
            "step": 8,
            "name": "state_aggregation",
            "component": "OperationalStateAggregator.aggregate_state",
            "action": "compute aggregated operational state",
        },
        {
            "step": 9,
            "name": "health_computation",
            "component": "SystemHealthMatrix.compute_health",
            "action": "compute system health score",
        },
        {
            "step": 10,
            "name": "state_classification",
            "component": "IntelligenceStateClassifier.classify",
            "action": "classify operational state",
        },
        {
            "step": 11,
            "name": "recursion_record",
            "component": "RecursionGuard.record_call",
            "action": "record pipeline execution",
        },
    ],
    "exit": "result dict with signal_id, success, ingest, timeline, classification",
}


QUERY_ROUTING = {
    "name": "control_center_query_routing",
    "version": "1.0.0",
    "entry": "ControlCenterRouter.route_query",
    "routes": {
        "state": {
            "handler": "get_aggregated_state",
            "return": "AggregatedState dataclass fields",
            "bounded": True,
        },
        "timeline": {
            "handler": "get_unified_timeline.get_events",
            "parameters": ["tick_start", "tick_end", "source_phase", "event_type", "severity", "limit"],
            "bounded": True,
        },
        "incidents": {
            "handler": "get_incident_registry.get_incidents",
            "parameters": ["status", "severity", "signal_type", "limit"],
            "bounded": True,
        },
        "dashboard": {
            "handler": "generate_dashboard_snapshot",
            "parameters": ["tick"],
            "bounded": True,
        },
        "health": {
            "handler": "get_health_matrix.compute_health",
            "parameters": ["severity_score", "critical_count", "incident_count", "active_signals", "source_summaries"],
            "bounded": True,
        },
        "safety": {
            "handler": "generate_safety_report",
            "parameters": ["context"],
            "bounded": True,
        },
        "reports": {
            "handler": "delegated_to_executive/risk/digest/stability_report",
            "parameters": ["report_type", "tick"],
            "bounded": True,
        },
    },
    "unknown_query": {"behavior": "returns error dict, never crashes"},
}


def get_orchestration_flow_map() -> Dict[str, Any]:
    """Return the complete orchestration flow map."""
    return {
        "signal_pipeline": SIGNAL_PIPELINE,
        "query_routing": QUERY_ROUTING,
        "version": "1.0.0",
        "generated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


def get_interaction_graph() -> Dict[str, List[str]]:
    """Return the control center interaction graph."""
    return {
        "ControlCenterEngine": [
            "Owns all subcomponents",
            "Processes signals through 11-step pipeline",
            "Generates dashboard snapshots",
            "Generates safety reports",
        ],
        "ControlCenterRouter": [
            "Routes signals to engine.process_signal",
            "Routes queries to engine subcomponents",
            "Handles unknown query types gracefully",
        ],
        "ObservabilityAPI": [
            "10 GET endpoints, all read-only",
            "Lazy-init singleton engines",
            "Sets observability_read_only flag on responses",
        ],
        "ReplayEngine": [
            "Session lifecycle management",
            "Safety-guarded event execution",
            "All writes blocked by safety guard",
        ],
        "DigitalTwin": [
            "Pipeline orchestrator for digital twin scenarios",
            "Bounded results storage",
            "Integrity validation matrix",
        ],
    }
