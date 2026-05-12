"""
Phase 5A.5.5 — Interface Locking: Compatibility Validators.

Backward compatibility checking for schemas, replay payloads,
and observability responses.

No mutation. Deterministic validation only.
"""
from typing import Any, Dict, List, Optional
from core.operations.interfaces.schemas import get_schema
from core.operations.interfaces.serialization import is_serialization_deterministic


COMPATIBILITY_VERSION = "1.0.0"


def check_replay_payload_stability(payload: Dict[str, Any]) -> List[str]:
    """Check that a replay payload has stable structure."""
    violations = []
    expected_keys = {"tick", "event_type", "payload"}
    actual_keys = set(payload.keys())
    missing = expected_keys - actual_keys
    if missing:
        violations.append(f"Replay payload missing keys: {missing}")
    extra = actual_keys - expected_keys
    if extra:
        violations.append(f"Replay payload has unexpected keys: {extra}")
    if not is_serialization_deterministic(payload):
        violations.append("Replay payload serialization is not deterministic")
    return violations


def check_timeline_payload_stability(event: Dict[str, Any]) -> List[str]:
    """Check that a timeline event has stable ordering-critical fields."""
    violations = []
    ordering_keys = ["tick", "event_id", "event_type", "severity", "timestamp"]
    for key in ordering_keys:
        if key not in event:
            violations.append(f"Timeline event missing ordering key: {key}")
    return violations


def check_observability_response_stability(response: Dict[str, Any]) -> List[str]:
    """Check that an observability response has stable envelope."""
    violations = []
    if "success" not in response:
        violations.append("Response missing success field")
    if "data" not in response:
        violations.append("Response missing data field")
    if "meta" in response and isinstance(response["meta"], dict):
        meta = response["meta"]
        if "request_id" not in meta:
            violations.append("Response meta missing request_id")
        if "timestamp" not in meta:
            violations.append("Response meta missing timestamp")
    return violations


def verify_schema_backward_compatible(schema_name: str) -> List[str]:
    """Verify a schema against itself (self-consistency check)."""
    violations = []
    schema = get_schema(schema_name)
    if schema is None:
        return [f"Schema not found: {schema_name}"]
    fields = schema.get("fields", schema.get("envelope", {}))
    if not fields:
        return [f"Schema has no fields: {schema_name}"]
    version = schema.get("version")
    if version is None:
        violations.append(f"Schema missing version: {schema_name}")
    return violations
