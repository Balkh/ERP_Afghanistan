"""
Phase 5A.5.5 — Interface Locking Tests.

Validates:
- DTO schema immutability and versioning
- Serialization determinism
- Backward compatibility of schemas
- Replay payload stability
- Timeline ordering stability
"""
import unittest
from core.operations.interfaces.schemas import (
    get_schema, get_all_schemas, validate_payload_against_schema,
    ALL_SCHEMAS, SCHEMA_VERSION,
)
from core.operations.interfaces.serialization import (
    is_serialization_deterministic, check_payload_determinism,
    get_schema_compatibility_report, SCHEMA_FIELD_INVENTORY,
    check_backward_compatibility,
)
from core.operations.interfaces.compatibility import (
    check_replay_payload_stability, check_timeline_payload_stability,
    check_observability_response_stability, verify_schema_backward_compatible,
)


class SchemaImmutabilityTest(unittest.TestCase):
    """DTO schema definitions are frozen and versioned."""

    def test_schema_version(self):
        """Schema version is 1.0.0."""
        self.assertEqual(SCHEMA_VERSION, "1.0.0")

    def test_all_schemas_have_version(self):
        """All schemas have version field."""
        schemas = get_all_schemas()
        for name, schema in schemas.items():
            self.assertIn("version", schema, f"Schema {name} missing version")

    def test_all_schemas_have_immutable_since(self):
        """All schemas have immutable_since field."""
        schemas = get_all_schemas()
        for name, schema in schemas.items():
            self.assertIn("immutable_since", schema,
                          f"Schema {name} missing immutable_since")

    def test_seven_schemas_registered(self):
        """There are 7 registered schemas."""
        self.assertEqual(len(ALL_SCHEMAS), 7)

    def test_get_schema_by_name(self):
        """Can retrieve schema by name."""
        for name in ALL_SCHEMAS:
            schema = get_schema(name)
            self.assertIsNotNone(schema, f"Schema {name} not found")

    def test_get_nonexistent_schema(self):
        """Nonexistent schema returns None."""
        self.assertIsNone(get_schema("nonexistent_schema"))


class SerializationDeterminismTest(unittest.TestCase):
    """Serialization is deterministic."""

    def test_simple_dict_deterministic(self):
        """Simple dict serializes deterministically."""
        payload = {"key": "value", "number": 42, "flag": True}
        self.assertTrue(is_serialization_deterministic(payload))

    def test_nested_dict_deterministic(self):
        """Nested dict serializes deterministically."""
        payload = {"outer": {"inner": "value"}, "list": [1, 2, 3]}
        self.assertTrue(is_serialization_deterministic(payload))

    def test_payload_determinism_no_violations(self):
        """Valid payload has no determinism violations."""
        payload = {"signal_id": "test-1", "tick": 100, "severity": "LOW"}
        violations = check_payload_determinism(payload)
        self.assertEqual(violations, [])

    def test_schema_compatibility_report(self):
        """Compatibility report covers all schemas."""
        report = get_schema_compatibility_report()
        self.assertEqual(len(report), len(ALL_SCHEMAS))

    def test_backward_compatibility_same_schema(self):
        """Schema is backward-compatible with itself."""
        schema = get_schema("operational_signal")
        violations = check_backward_compatibility(schema, schema)
        self.assertEqual(violations, [])


class PayloadValidationTest(unittest.TestCase):
    """Payload validation works correctly."""

    def test_validate_required_fields_present(self):
        """No violations for payload with all required fields."""
        schema = get_schema("operational_signal")
        payload = {
            "signal_id": "test", "signal_type": "ANOMALY",
            "severity": "LOW", "source_phase": "test",
            "tick": 1, "description": "test",
        }
        violations = validate_payload_against_schema(payload, schema)
        self.assertEqual(violations, [])

    def test_validate_missing_required_field(self):
        """Violation for missing required field."""
        schema = get_schema("operational_signal")
        payload = {"signal_id": "test"}
        violations = validate_payload_against_schema(payload, schema)
        self.assertGreater(len(violations), 0)

    def test_validate_none_required_field(self):
        """Violation for None required field."""
        schema = get_schema("operational_signal")
        payload = {"signal_id": None, "signal_type": "ANOMALY",
                   "severity": "LOW", "source_phase": "test",
                   "tick": 1, "description": "test"}
        violations = validate_payload_against_schema(payload, schema)
        self.assertGreater(len(violations), 0)


class ReplayPayloadStabilityTest(unittest.TestCase):
    """Replay payloads maintain stable structure."""

    def test_valid_replay_payload(self):
        """Valid replay payload has no violations."""
        payload = {"tick": 1, "event_type": "TEST", "payload": {"val": 1}}
        violations = check_replay_payload_stability(payload)
        self.assertEqual(violations, [])

    def test_missing_tick_violation(self):
        """Replay payload missing tick has violations."""
        payload = {"event_type": "TEST", "payload": {}}
        violations = check_replay_payload_stability(payload)
        self.assertGreater(len(violations), 0)

    def test_timeline_event_stability(self):
        """Timeline event has all ordering-critical fields."""
        event = {"tick": 1, "event_id": "evt-1", "event_type": "TEST",
                 "severity": "LOW", "timestamp": 1000.0}
        violations = check_timeline_payload_stability(event)
        self.assertEqual(violations, [])

    def test_timeline_event_missing_ordering_key(self):
        """Timeline event missing ordering key has violations."""
        event = {"tick": 1}
        violations = check_timeline_payload_stability(event)
        self.assertGreater(len(violations), 0)


class ObservabilityResponseStabilityTest(unittest.TestCase):
    """Observability responses maintain stable envelope."""

    def test_valid_response_has_required_fields(self):
        """Valid response has all required fields."""
        response = {
            "success": True,
            "data": {"status": "healthy"},
            "meta": {"request_id": "abc", "timestamp": "2024-01-01T00:00:00Z"},
        }
        violations = check_observability_response_stability(response)
        self.assertEqual(violations, [])

    def test_missing_success_field(self):
        """Response without success has violations."""
        response = {"data": {}}
        violations = check_observability_response_stability(response)
        self.assertGreater(len(violations), 0)

    def test_missing_meta_fields(self):
        """Response meta missing required fields has violations."""
        response = {"success": True, "data": {}, "meta": {}}
        violations = check_observability_response_stability(response)
        self.assertGreater(len(violations), 0)


class SchemaBackwardCompatibilityTest(unittest.TestCase):
    """All schemas are backward compatible."""

    def test_operational_signal_compatible(self):
        """Operational signal schema is self-compatible."""
        violations = verify_schema_backward_compatible("operational_signal")
        self.assertEqual(violations, [])

    def test_dashboard_snapshot_compatible(self):
        """Dashboard snapshot schema is self-compatible."""
        violations = verify_schema_backward_compatible("dashboard_snapshot")
        self.assertEqual(violations, [])

    def test_all_schemas_self_compatible(self):
        """All schemas are self-compatible."""
        from core.operations.interfaces.schemas import ALL_SCHEMAS
        for name in ALL_SCHEMAS:
            violations = verify_schema_backward_compatible(name)
            self.assertEqual(violations, [], f"Schema {name} has violations")
