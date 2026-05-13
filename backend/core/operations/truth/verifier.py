"""
Phase 5B.3 — Truth Verification Engine.

Verifies claims against the Event Store and detects drift between
reported state and actual persisted state.

Core principle:
    "If it is not in the Event Store, it did not happen."

Three capabilities:
1. EventExistenceValidator — verify claimed events exist
2. StateReconstructionEngine — rebuild state from events only
3. DriftDetectionLayer — compare reported vs actual state
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.operations.truth.models import (
    Event, SourceType, Domain,
    ClaimVerification, VerificationClaim,
    DriftReport, DriftType, DriftSeverity,
    ConsistencyResult, ProjectionState,
)
from core.operations.truth.event_store import EventStore, get_event_store

logger = logging.getLogger('erp.truth.verifier')

VERIFIER_VERSION = "1.0.0"


class EventExistenceValidator:
    """Validates that claimed events actually exist in the Event Store.

    For every reported claim:
    - verify event_id exists in Event Store
    - verify domain consistency
    - verify timestamp ordering
    - verify source_type integrity
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def verify_claim(self, claim: VerificationClaim) -> ClaimVerification:
        """Verify a single claim against the Event Store.

        Deterministic — same claim + same store = same result.

        Args:
            claim: The claim to verify.

        Returns:
            ClaimVerification with evidence or missing entities.
        """
        evidence_ids: List[str] = []
        missing: List[str] = []
        inconsistencies: List[str] = []

        events = self._store.get_by_aggregate(claim.domain, claim.aggregate_id)
        matching = [
            e for e in events
            if e.event_type == claim.event_type
        ]

        if not matching:
            missing.append(
                f"No events of type '{claim.event_type}' for "
                f"aggregate '{claim.aggregate_id}' in domain '{claim.domain.value}'"
            )
        else:
            evidence_ids = [e.event_id for e in matching]

            actual_count = len(matching)
            if actual_count < claim.expected_count:
                missing.append(
                    f"Expected {claim.expected_count} events of type "
                    f"'{claim.event_type}', found {actual_count}"
                )

            if claim.expected_fields:
                for field, expected_value in claim.expected_fields.items():
                    found = False
                    for event in matching:
                        if event.payload.get(field) == expected_value:
                            found = True
                            break
                    if not found:
                        inconsistencies.append(
                            f"No event with {field}={expected_value} in "
                            f"aggregate '{claim.aggregate_id}'"
                        )

            if claim.source_type != SourceType.SIMULATION:
                real_events = [e for e in matching if e.source_type != SourceType.SIMULATION]
                if not real_events:
                    inconsistencies.append(
                        f"All matching events are SIMULATION, expected REAL source"
                    )

            if claim.timestamp_range:
                start, end = claim.timestamp_range
                range_events = [
                    e for e in matching
                    if start <= e.timestamp <= end
                ]
                if not range_events:
                    inconsistencies.append(
                        f"No events in timestamp range [{start}, {end}]"
                    )

        return ClaimVerification(
            claim_id=claim.claim_id,
            claim_event_type=claim.event_type,
            claim_aggregate_id=claim.aggregate_id,
            verified=len(missing) == 0 and len(inconsistencies) == 0,
            evidence_event_ids=evidence_ids,
            missing_entities=missing,
            inconsistencies=inconsistencies,
        )

    def verify_claims_batch(
        self,
        claims: List[VerificationClaim],
    ) -> List[ClaimVerification]:
        """Verify a batch of claims."""
        return [self.verify_claim(c) for c in claims]

    def verify_event_id(self, event_id: str) -> bool:
        """Quick check if an event_id exists."""
        return self._store.event_exists(event_id)

    def verify_aggregate_exists(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> Tuple[bool, int]:
        """Check if an aggregate has any events."""
        events = self._store.get_by_aggregate(domain, aggregate_id)
        return len(events) > 0, len(events)


class StateReconstructionEngine:
    """Reconstructs system state SOLELY from Event Store data.

    All state MUST be derived via:
        Event Store → Projection Engine → Current State

    NO cached or agent-provided state is allowed.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def reconstruct_aggregate(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> Dict[str, Any]:
        """Reconstruct the full state of an aggregate from its events.

        Applies all events in sequence order to derive current state.
        No external state is used.

        Args:
            domain: The domain of the aggregate.
            aggregate_id: The aggregate ID.

        Returns:
            Dict with reconstructed state including:
            - current_state: the derived state
            - events_used: number of events applied
            - first_event: first event timestamp
            - last_event: last event timestamp
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        if not events:
            return {
                "aggregate_id": aggregate_id,
                "domain": domain.value,
                "exists": False,
                "events_used": 0,
            }

        state: Dict[str, Any] = {
            "aggregate_id": aggregate_id,
            "domain": domain.value,
            "exists": True,
            "events_used": len(events),
            "first_event": events[0].timestamp,
            "last_event": events[-1].timestamp,
            "source_types": list(set(e.source_type.value for e in events)),
            "event_types": list(set(e.event_type for e in events)),
        }

        current = {}
        for event in events:
            if domain == Domain.INVENTORY:
                current = self._apply_inventory_event(current, event)
            elif domain == Domain.ACCOUNTING:
                current = self._apply_accounting_event(current, event)
            elif domain == Domain.HR:
                current = self._apply_hr_event(current, event)
            elif domain == Domain.SALES_PURCHASE:
                current = self._apply_sales_purchase_event(current, event)
            elif domain == Domain.FIXED_ASSETS:
                current = self._apply_fixed_asset_event(current, event)

        state["current_state"] = current
        return state

    def _apply_inventory_event(
        self,
        state: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        et = event.event_type
        p = event.payload
        if et == "stock_movement":
            qty = int(p.get("quantity", 0))
            direction = p.get("direction", "out")
            state["current_quantity"] = state.get("current_quantity", 0) + (
                -qty if direction == "out" else qty
            )
            state["last_movement"] = event.event_id
            state["last_movement_type"] = direction
        elif et == "stock_reconciled":
            state["current_quantity"] = p.get("actual_quantity", 0)
            state["last_reconciliation"] = event.event_id
            state["last_variance"] = p.get("variance", 0)
        elif et == "stock_adjusted":
            state["current_quantity"] = p.get("new_quantity", 0)
            state["last_adjustment"] = event.event_id
        elif et == "batch_created":
            state["initial_quantity"] = p.get("initial_quantity", 0)
            state["current_quantity"] = state.get("current_quantity", 0) or p.get("initial_quantity", 0)
            state["expiry_date"] = p.get("expiry_date")
            state["warehouse_id"] = p.get("warehouse_id")
        state["last_event_type"] = et
        state["last_event_id"] = event.event_id
        return state

    def _apply_accounting_event(
        self,
        state: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        et = event.event_type
        p = event.payload
        if et == "journal_entry_posted":
            lines = p.get("entries", [])
            total_debit = sum(line.get("debit", 0) for line in lines)
            total_credit = sum(line.get("credit", 0) for line in lines)
            state["last_journal_entry"] = event.event_id
            state["last_description"] = p.get("description", "")
            state["total_debit"] = state.get("total_debit", 0) + total_debit
            state["total_credit"] = state.get("total_credit", 0) + total_credit
            state["is_balanced"] = abs(total_debit - total_credit) < 0.001
            state["line_count"] = len(lines)
        elif et == "journal_entry_reversed":
            state["last_reversal"] = event.event_id
            state["reversal_reason"] = p.get("reason", "")
        elif et == "account_created":
            state["account_code"] = p.get("account_code", "")
            state["account_name"] = p.get("account_name", "")
            state["account_type"] = p.get("account_type", "")
        state["last_event_type"] = et
        state["last_event_id"] = event.event_id
        return state

    def _apply_hr_event(
        self,
        state: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        et = event.event_type
        p = event.payload
        if et == "employee_hired":
            state["name"] = p.get("name", "")
            state["department"] = p.get("department", "")
            state["position"] = p.get("position", "")
            state["status"] = "ACTIVE"
            state["hire_date"] = p.get("hire_date", event.timestamp)
        elif et == "employee_role_changed":
            state["department"] = p.get("new_department", state.get("department", ""))
            state["position"] = p.get("new_position", state.get("position", ""))
        elif et == "employee_terminated":
            state["status"] = "TERMINATED"
            state["termination_date"] = p.get("termination_date", event.timestamp)
            state["termination_reason"] = p.get("reason", "")
        elif et == "attendance_recorded":
            state["last_attendance_date"] = p.get("date", "")
            state["last_attendance_type"] = p.get("type", "")
        state["last_event_type"] = et
        state["last_event_id"] = event.event_id
        return state

    def _apply_sales_purchase_event(
        self,
        state: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        et = event.event_type
        p = event.payload
        if et == "order_created":
            state["order_type"] = p.get("order_type", "")
            state["status"] = "CREATED"
            state["total_amount"] = p.get("total_amount", 0)
            state["customer_supplier_id"] = p.get("customer_id") or p.get("supplier_id", "")
        elif et == "order_approved":
            state["status"] = "APPROVED"
            state["approved_by"] = p.get("approver_id", "")
        elif et == "payment_received":
            state["paid_amount"] = state.get("paid_amount", 0) + p.get("amount", 0)
            state["status"] = "PARTIALLY_PAID" if state.get("paid_amount", 0) < state.get("total_amount", 0) else "PAID"
            state["last_payment_method"] = p.get("method", "")
        elif et == "goods_dispatched":
            state["status"] = "DISPATCHED"
            state["dispatch_date"] = p.get("dispatched_at", event.timestamp)
        elif et == "goods_received":
            state["status"] = "RECEIVED"
            state["received_date"] = p.get("received_at", event.timestamp)
        elif et == "order_cancelled":
            state["status"] = "CANCELLED"
            state["cancellation_reason"] = p.get("reason", "")
        state["last_event_type"] = et
        state["last_event_id"] = event.event_id
        return state

    def _apply_fixed_asset_event(
        self,
        state: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        et = event.event_type
        p = event.payload
        if et == "asset_acquired":
            state["category"] = p.get("category", "")
            state["cost"] = p.get("cost", 0)
            state["useful_life"] = p.get("useful_life", 0)
            state["book_value"] = p.get("cost", 0)
            state["status"] = "ACTIVE"
            state["depreciation_method"] = p.get("depreciation_method", "")
        elif et == "depreciation_booked":
            dep_amount = p.get("amount", 0)
            state["book_value"] = state.get("book_value", 0) - dep_amount
            state["accumulated_depreciation"] = (
                state.get("accumulated_depreciation", 0) + dep_amount
            )
            state["last_depreciation_period"] = p.get("period", "")
        elif et == "asset_disposed":
            state["status"] = "DISPOSED"
            state["disposal_proceeds"] = p.get("proceeds", 0)
            state["disposal_gain_loss"] = p.get("gain_loss", 0)
            state["disposal_date"] = p.get("disposal_date", event.timestamp)
        state["last_event_type"] = et
        state["last_event_id"] = event.event_id
        return state

    def compute_projection_hash(self, domain: Domain) -> str:
        """Compute a deterministic projection state hash."""
        h = hashlib.sha256()
        events = self._store.get_by_domain(domain)
        for event in events:
            h.update(event.event_id.encode())
            h.update(str(event.sequence).encode())
        return h.hexdigest()


class DriftDetectionLayer:
    """Detects drift between reported state and actual Event Store state.

    Compares:
    - reported state (from agents / logs)
    - actual projected state (from Event Store)

    Detects:
    - missing events
    - duplicated ingestion
    - inconsistent counts
    - domain mismatches
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._reconstructor = StateReconstructionEngine(store)

    def detect_drift(
        self,
        reported_state: Dict[str, Any],
        domain: Domain,
        aggregate_id: str,
    ) -> DriftReport:
        """Detect drift between reported and actual state.

        Args:
            reported_state: The state as reported by an agent or log.
            domain: The domain of the aggregate.
            aggregate_id: The aggregate ID.

        Returns:
            DriftReport with findings.
        """
        actual = self._reconstructor.reconstruct_aggregate(domain, aggregate_id)
        discrepancies: List[Dict[str, Any]] = []
        drift_types: List[DriftType] = []

        if not actual.get("exists", False):
            return DriftReport(
                drift_detected=True,
                drift_type=DriftType.MISSING_EVENTS,
                severity=DriftSeverity.HIGH,
                affected_domains=[domain.value],
                reported_state_summary=reported_state,
                actual_state_summary=actual,
                discrepancies=[{"message": f"Aggregate {aggregate_id} has no events in store"}],
            )

        reported_count = reported_state.get("events_used", reported_state.get("event_count", 0))
        actual_count = actual.get("events_used", 0)
        if reported_count != actual_count:
            drift_types.append(DriftType.STATE_MISMATCH)
            discrepancies.append({
                "field": "events_used",
                "reported": reported_count,
                "actual": actual_count,
                "message": f"Event count mismatch: reported={reported_count}, actual={actual_count}",
            })

        reported_events = reported_state.get("event_ids", [])
        if reported_events:
            for eid in reported_events:
                if not self._store.event_exists(eid):
                    drift_types.append(DriftType.MISSING_EVENTS)
                    discrepancies.append({
                        "field": "event_id",
                        "reported": eid,
                        "actual": "not_found",
                        "message": f"Claimed event {eid} does not exist in store",
                    })

        reported_event_types = set(reported_state.get("event_types", []))
        actual_event_types = set(actual.get("event_types", []))
        if reported_event_types and reported_event_types != actual_event_types:
            drift_types.append(DriftType.DOMAIN_MISMATCH)
            missing_types = reported_event_types - actual_event_types
            if missing_types:
                discrepancies.append({
                    "field": "event_types",
                    "reported": list(reported_event_types),
                    "actual": list(actual_event_types),
                    "message": f"Missing event types in store: {missing_types}",
                })

        severity = DriftSeverity.LOW
        if discrepancies:
            severity = DriftSeverity.MEDIUM if len(discrepancies) <= 2 else DriftSeverity.HIGH
            for d in discrepancies:
                if "not_found" in str(d.get("actual", "")):
                    severity = DriftSeverity.CRITICAL
                    break

        drift_type = drift_types[0] if drift_types else DriftType.STATE_MISMATCH

        return DriftReport(
            drift_detected=len(discrepancies) > 0,
            drift_type=drift_type,
            severity=severity,
            affected_domains=[domain.value],
            reported_state_summary=reported_state,
            actual_state_summary=actual,
            missing_event_ids=[
                d["reported"] for d in discrepancies
                if d.get("actual") == "not_found"
            ],
            discrepancies=discrepancies,
        )

    def detect_drift_by_event_ids(
        self,
        claimed_event_ids: List[str],
    ) -> DriftReport:
        """Detect drift by comparing claimed event IDs against the store.

        Args:
            claimed_event_ids: List of event IDs claimed to exist.

        Returns:
            DriftReport with findings.
        """
        missing: List[str] = []
        for eid in claimed_event_ids:
            if not self._store.event_exists(eid):
                missing.append(eid)

        return DriftReport(
            drift_detected=len(missing) > 0,
            drift_type=DriftType.MISSING_EVENTS if missing else None,
            severity=DriftSeverity.CRITICAL if missing else DriftSeverity.LOW,
            missing_event_ids=missing,
            discrepancies=[
                {"message": f"Event {eid} not found in store"} for eid in missing
            ],
        )
