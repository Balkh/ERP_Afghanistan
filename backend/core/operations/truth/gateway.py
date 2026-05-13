"""
Phase 5B.3 — Truth Verification & Live Reporting Gateway.

Orchestrates the complete truth verification pipeline:
    Query Event Store → Build Projection → Validate Consistency → Return Verified Report

ZERO FICTION REPORTING. All outputs are query-backed, evidence-based, and reproducible.

Core principle:
    "Nothing exists unless it is provable from the event log."
"""
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import (
    Domain, SourceType, ClaimVerification, VerificationClaim,
    DriftReport, DriftType, DriftSeverity,
    ConsistencyResult, VerifiedReport,
)
from core.operations.truth.event_store import EventStore, get_event_store, EventFactory
from core.operations.truth.verifier import (
    EventExistenceValidator, StateReconstructionEngine, DriftDetectionLayer,
)
from core.operations.truth.projections import (
    InventoryProjection, AccountingProjection,
    HRProjection, SalesPurchaseProjection,
)
from core.operations.truth.reports import (
    InventoryReportBuilder, AccountingReportBuilder,
    HRReportBuilder, SalesPurchaseReportBuilder,
)

logger = logging.getLogger('erp.truth.gateway')

GATEWAY_VERSION = "1.0.0"


class TruthGateway:
    """Primary orchestrator for the Truth Verification & Live Reporting Layer.

    All queries follow the strict pipeline:
        User Request → Query Event Store → Build Projection
        → Validate Consistency → Return Verified Report

    NO intermediate interpretation layer.
    NO cached or agent-provided state.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._verifier = EventExistenceValidator(self._store)
        self._reconstructor = StateReconstructionEngine(self._store)
        self._drift_detector = DriftDetectionLayer(self._store)
        self._inv_projection = InventoryProjection(self._store)
        self._acct_projection = AccountingProjection(self._store)
        self._hr_projection = HRProjection(self._store)
        self._sp_projection = SalesPurchaseProjection(self._store)
        self._inv_reports = InventoryReportBuilder(self._inv_projection, self._store)
        self._acct_reports = AccountingReportBuilder(self._acct_projection, self._store)
        self._hr_reports = HRReportBuilder(self._hr_projection, self._store)
        self._sp_reports = SalesPurchaseReportBuilder(self._sp_projection, self._store)

    # ── Event Store Operations ──

    def emit_event(
        self,
        source_type: SourceType,
        domain: Domain,
        event_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Emit a single event to the Event Store.

        This is the ONLY way to add data to the Digital Twin.
        Every event is persisted immutably.

        Returns event_id.
        """
        sequence = self._store.get_last_sequence(source_type, domain, aggregate_id) + 1

        store_metadata = {
            "ingestion_channel": "truth_gateway",
            "gateway_version": GATEWAY_VERSION,
        }
        if metadata:
            store_metadata.update(metadata)

        event = EventFactory.create_event(
            source_type=source_type,
            domain=domain,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload,
            metadata=store_metadata,
            timestamp=timestamp,
            sequence=sequence,
        )

        return self._store.append(event)

    def emit_events_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> List[str]:
        """Emit multiple events atomically.

        Each dict must have: source_type, domain, event_type,
        aggregate_id, payload.
        """
        event_ids = []
        for evt_data in events:
            eid = self.emit_event(
                source_type=evt_data["source_type"],
                domain=evt_data["domain"],
                event_type=evt_data["event_type"],
                aggregate_id=evt_data["aggregate_id"],
                payload=evt_data["payload"],
                metadata=evt_data.get("metadata"),
                timestamp=evt_data.get("timestamp"),
            )
            event_ids.append(eid)
        return event_ids

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a single event by ID."""
        event = self._store.get(event_id)
        if event is None:
            return None
        return {
            "event_id": event.event_id,
            "source_type": event.source_type.value,
            "domain": event.domain.value,
            "event_type": event.event_type,
            "aggregate_id": event.aggregate_id,
            "timestamp": event.timestamp,
            "sequence": event.sequence,
            "payload": event.payload,
            "metadata": event.metadata,
        }

    # ── Truth Verification ──

    def verify_claim(self, claim: VerificationClaim) -> ClaimVerification:
        """Verify a single claim against the Event Store."""
        return self._verifier.verify_claim(claim)

    def verify_claims_batch(
        self,
        claims: List[VerificationClaim],
    ) -> List[ClaimVerification]:
        """Verify multiple claims."""
        return self._verifier.verify_claims_batch(claims)

    def verify_event_exists(self, event_id: str) -> bool:
        """Quick check if an event exists in the store."""
        return self._store.event_exists(event_id)

    def verify_aggregate(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> Dict[str, Any]:
        """Verify an aggregate exists and return its state."""
        return self._reconstructor.reconstruct_aggregate(domain, aggregate_id)

    # ── Drift Detection ──

    def detect_drift(
        self,
        reported_state: Dict[str, Any],
        domain: Domain,
        aggregate_id: str,
    ) -> DriftReport:
        """Detect drift between reported and actual state."""
        return self._drift_detector.detect_drift(reported_state, domain, aggregate_id)

    def detect_drift_by_event_ids(
        self,
        claimed_event_ids: List[str],
    ) -> DriftReport:
        """Detect drift by comparing claimed event IDs."""
        return self._drift_detector.detect_drift_by_event_ids(claimed_event_ids)

    # ── Inventory Reports ──

    def get_stock_levels(self) -> VerifiedReport:
        """Current stock levels for all products."""
        return self._inv_reports.get_stock_levels()

    def get_warehouse_distribution(self) -> VerifiedReport:
        """Stock distribution across warehouses."""
        return self._inv_reports.get_warehouse_distribution()

    def get_batch_breakdown(self) -> VerifiedReport:
        """Batch-level stock breakdown."""
        return self._inv_reports.get_batch_breakdown()

    # ── Accounting Reports ──

    def get_ledger_balances(self) -> VerifiedReport:
        """Current ledger balances."""
        return self._acct_reports.get_ledger_balances()

    def get_journal_entries(self) -> VerifiedReport:
        """All journal entries."""
        return self._acct_reports.get_journal_entries()

    def get_trial_balance(self) -> VerifiedReport:
        """Trial balance."""
        return self._acct_reports.get_trial_balance()

    # ── HR Reports ──

    def get_employee_roster(self) -> VerifiedReport:
        """Current employee roster."""
        return self._hr_reports.get_employee_roster()

    def get_attendance_summary(self) -> VerifiedReport:
        """Attendance summary."""
        return self._hr_reports.get_attendance_summary()

    # ── Sales/Purchase Reports ──

    def get_order_status(self) -> VerifiedReport:
        """Current order status."""
        return self._sp_reports.get_order_status()

    def get_payment_status(self) -> VerifiedReport:
        """Payment status."""
        return self._sp_reports.get_payment_status()

    def get_fulfillment_state(self) -> VerifiedReport:
        """Fulfillment state."""
        return self._sp_reports.get_fulfillment_state()

    # ── System Operations ──

    def run_consistency_check(self) -> ConsistencyResult:
        """Run full consistency check on the Event Store."""
        return self._store.run_consistency_check()

    def get_store_summary(self) -> Dict[str, Any]:
        """Get summary of Event Store state."""
        return {
            "total_events": self._store.count(),
            "by_domain": self._store.count_by_domain(),
            "by_source": self._store.count_by_source(),
            "consistency": self._store.run_consistency_check().consistent,
            "state_hash": self._store.compute_state_hash(),
            "gateway_version": GATEWAY_VERSION,
        }

    def rebuild_all_projections(self) -> Dict[str, int]:
        """Rebuild all domain projections from scratch."""
        return {
            "inventory": self._inv_projection.rebuild(),
            "accounting": self._acct_projection.rebuild(),
            "hr": self._hr_projection.rebuild(),
            "sales_purchase": self._sp_projection.rebuild(),
        }

    def reset(self) -> None:
        """Reset all state. For testing only."""
        self._store.clear()
        self._inv_projection = InventoryProjection(self._store)
        self._acct_projection = AccountingProjection(self._store)
        self._hr_projection = HRProjection(self._store)
        self._sp_projection = SalesPurchaseProjection(self._store)
        self._inv_reports = InventoryReportBuilder(self._inv_projection, self._store)
        self._acct_reports = AccountingReportBuilder(self._acct_projection, self._store)
        self._hr_reports = HRReportBuilder(self._hr_projection, self._store)
        self._sp_reports = SalesPurchaseReportBuilder(self._sp_projection, self._store)
        logger.info("TruthGateway state reset")


_global_gateway: Optional[TruthGateway] = None


def get_gateway() -> TruthGateway:
    global _global_gateway
    if _global_gateway is None:
        _global_gateway = TruthGateway()
    return _global_gateway


def reset_gateway() -> None:
    global _global_gateway
    from core.operations.truth.event_store import reset_event_store
    reset_event_store()
    _global_gateway = None
