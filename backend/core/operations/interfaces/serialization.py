"""
Phase 5A.5.5 — Interface Locking: Serialization Determinism & Compatibility.

Validates that all DTOs serialize deterministically and maintain
backward compatibility across schema versions.

No mutation. Deterministic validation only.
"""
import json
from typing import Any, Dict, List, Optional
from core.operations.interfaces.schemas import get_all_schemas


SERIALIZATION_VERSION = "1.0.0"


def is_serialization_deterministic(obj: Any) -> bool:
    """Check if an object serializes deterministically (same object → same JSON)."""
    try:
        json_str_1 = json.dumps(obj, sort_keys=True, default=str)
        json_str_2 = json.dumps(obj, sort_keys=True, default=str)
        return json_str_1 == json_str_2
    except (TypeError, ValueError):
        return False


def check_payload_determinism(payload: Dict[str, Any]) -> List[str]:
    """Check that all values in a payload are deterministically serializable."""
    violations = []
    try:
        _ = json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError) as e:
        violations.append(f"Payload not JSON-serializable: {e}")
    for key, value in payload.items():
        if isinstance(value, dict):
            violations.extend(check_payload_determinism(value))
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, dict):
                    violations.extend(check_payload_determinism(item))
    return violations


def get_schema_compatibility_report() -> Dict[str, Any]:
    """Generate a report on schema compatibility across versions."""
    schemas = get_all_schemas()
    report = {}
    for name, schema in schemas.items():
        report[name] = {
            "version": schema.get("version", "unknown"),
            "immutable_since": schema.get("immutable_since", "unknown"),
            "field_count": len(schema.get("fields", schema.get("envelope", {}))),
            "is_frozen": schema.get("immutable_since") is not None,
        }
    return report


SCHEMA_FIELD_INVENTORY = {
    "required_fields": {
        "OperationalSignal": ["signal_id", "signal_type", "severity", "source_phase", "tick", "description"],
        "AggregatedState": ["state", "severity_score", "active_signals", "critical_count", "incident_count"],
        "DashboardSnapshot": ["snapshot_id", "tick", "operational_state", "stability_score", "health_status", "active_incidents"],
        "SafetyReport": ["report_id", "is_safe", "recursion_depth", "graph_size", "memory_pressure", "violations"],
        "ReplaySession": ["session_id", "status", "mode", "start_tick", "current_tick", "end_tick", "events_replayed", "is_paused"],
        "IncidentRecord": ["incident_id", "signal_type", "severity", "status", "tick_detected", "description", "occurrence_count", "escalation_level"],
    },
}


def check_backward_compatibility(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[str]:
    """Check that new_schema is backward-compatible with old_schema."""
    violations = []
    old_fields = old_schema.get("fields", {})
    new_fields = new_schema.get("fields", {})
    for field_name, field_spec in old_fields.items():
        if field_spec.get("required", False):
            if field_name not in new_fields:
                violations.append(f"Required field removed: {field_name}")
            elif new_fields[field_name].get("required", False) == False:
                violations.append(f"Required field became optional: {field_name}")
    return violations
