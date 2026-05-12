"""
Phase 5A.5.5 — Interface Locking: DTO Schema Definitions.

Frozen, versioned DTO schema definitions for all operational runtime
interfaces. These define the contract between components.

No mutation allowed after freeze. All schemas are dataclass-based
with version stamps for compatibility tracking.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


SCHEMA_VERSION = "1.0.0"


# ── Operational Signal Schema ──

OPERATIONAL_SIGNAL_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "signal_id": {"type": "str", "required": True, "description": "Unique signal identifier"},
        "signal_type": {"type": "SignalType (enum)", "required": True, "values": [
            "TRUTH_MISMATCH", "ROOT_CAUSE", "DRIFT_TREND", "RECOVERY_EVENT",
            "REPLAY_EVENT", "PREDICTIVE_WARNING", "INTEGRITY_BREACH",
            "ANOMALY", "INCIDENT", "ESCALATION",
        ]},
        "severity": {"type": "IntelligenceSeverity (enum)", "required": True, "values": [
            "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL",
        ]},
        "source_phase": {"type": "str", "required": True},
        "tick": {"type": "int", "required": True},
        "description": {"type": "str", "required": True},
        "payload": {"type": "dict", "required": False, "default": {}},
        "timestamp": {"type": "float", "required": False, "default": 0.0},
    },
    "immutable_since": "1.0.0",
}

# ── Aggregated State Schema ──

AGGREGATED_STATE_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "state": {"type": "OperationalState (enum)", "values": ["NORMAL", "DEGRADED", "CRITICAL", "EMERGENCY", "RECOVERING"]},
        "severity_score": {"type": "float", "range": [0.0, 1.0]},
        "active_signals": {"type": "int", "min": 0},
        "critical_count": {"type": "int", "min": 0},
        "incident_count": {"type": "int", "min": 0},
        "source_summaries": {"type": "dict"},
    },
    "immutable_since": "1.0.0",
}

# ── Dashboard Snapshot Schema ──

DASHBOARD_SNAPSHOT_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "snapshot_id": {"type": "str", "required": True},
        "tick": {"type": "int", "required": True},
        "operational_state": {"type": "str", "required": True},
        "stability_score": {"type": "float", "required": True, "range": [0.0, 1.0]},
        "health_status": {"type": "str", "required": True},
        "active_incidents": {"type": "int", "required": True, "min": 0},
        "widget_data": {"type": "dict", "required": False},
        "summary": {"type": "str", "required": False},
    },
    "immutable_since": "1.0.0",
}

# ── Safety Report Schema ──

SAFETY_REPORT_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "report_id": {"type": "str", "required": True},
        "is_safe": {"type": "bool", "required": True},
        "recursion_depth": {"type": "int", "required": True},
        "graph_size": {"type": "int", "required": True},
        "memory_pressure": {"type": "float", "required": True},
        "violations": {"type": "list", "required": True},
    },
    "immutable_since": "1.0.0",
}

# ── Observability API Response Schema ──

OBSERVABILITY_RESPONSE_SCHEMA = {
    "version": "1.0.0",
    "envelope": {
        "success": {"type": "bool", "required": True},
        "data": {"type": "any", "required": True},
        "meta": {
            "type": "dict",
            "required": True,
            "fields": {
                "request_id": {"type": "str", "required": True},
                "timestamp": {"type": "str", "required": True},
                "read_only": {"type": "bool", "required": False},
                "company_id": {"type": "str", "required": False},
            },
        },
    },
    "immutable_since": "1.0.0",
}

# ── Replay Session Schema ──

REPLAY_SESSION_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "session_id": {"type": "str", "required": True},
        "status": {"type": "ReplayStatus (enum)", "values": ["IDLE", "RUNNING", "PAUSED", "COMPLETED", "FAILED"]},
        "mode": {"type": "ReplayMode (enum)", "values": ["FULL", "STEP", "WINDOW", "BOOKMARK"]},
        "start_tick": {"type": "int", "required": True},
        "current_tick": {"type": "int", "required": True},
        "end_tick": {"type": "int", "required": True},
        "events_replayed": {"type": "int", "required": True},
        "is_paused": {"type": "bool", "required": True},
    },
    "immutable_since": "1.0.0",
}

# ── Incident Record Schema ──

INCIDENT_RECORD_SCHEMA = {
    "version": "1.0.0",
    "fields": {
        "incident_id": {"type": "str", "required": True},
        "signal_type": {"type": "SignalType (enum)", "required": True},
        "severity": {"type": "IntelligenceSeverity (enum)", "required": True},
        "status": {"type": "IncidentStatus (enum)", "values": ["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "CLOSED", "REOPENED"]},
        "tick_detected": {"type": "int", "required": True},
        "description": {"type": "str", "required": True},
        "occurrence_count": {"type": "int", "required": True},
        "escalation_level": {"type": "EscalationLevel (enum)", "values": ["NONE", "OBSERVE", "WARN", "ESCALATE", "EMERGENCY"]},
    },
    "immutable_since": "1.0.0",
}


ALL_SCHEMAS = {
    "operational_signal": OPERATIONAL_SIGNAL_SCHEMA,
    "aggregated_state": AGGREGATED_STATE_SCHEMA,
    "dashboard_snapshot": DASHBOARD_SNAPSHOT_SCHEMA,
    "safety_report": SAFETY_REPORT_SCHEMA,
    "observability_response": OBSERVABILITY_RESPONSE_SCHEMA,
    "replay_session": REPLAY_SESSION_SCHEMA,
    "incident_record": INCIDENT_RECORD_SCHEMA,
}


def get_schema(schema_name: str) -> Optional[Dict[str, Any]]:
    """Get a frozen schema by name."""
    return ALL_SCHEMAS.get(schema_name)


def get_all_schemas() -> Dict[str, Any]:
    """Get all frozen schemas."""
    return dict(ALL_SCHEMAS)


def validate_payload_against_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate a payload against a schema. Returns list of violation messages."""
    violations = []
    fields = schema.get("fields", {})
    for field_name, field_spec in fields.items():
        if field_spec.get("required", False):
            if field_name not in payload:
                violations.append(f"Missing required field: {field_name}")
            elif payload[field_name] is None:
                violations.append(f"Required field is None: {field_name}")
    return violations
