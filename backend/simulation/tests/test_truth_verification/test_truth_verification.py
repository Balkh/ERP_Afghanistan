"""
Phase 5B.3 — Truth Verification & Live Reporting Layer Tests.

Validates:
A. Event Store immutability and append-only
B. Event existence verification
C. State reconstruction from events only
D. Drift detection
E. Projection engine (inventory, accounting, HR, sales/purchase)
F. Live reporting (all report types)
G. Consistency verification
H. Determinism
I. No fabricated data
J. Audit trail enforcement
K. Cross-domain integrity
"""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from core.operations.truth.models import (
    Event, SourceType, Domain, VerificationClaim,
    ClaimVerification, DriftReport, DriftType, DriftSeverity,
    ConsistencyResult, ReportAudit, VerifiedReport,
    InventorySnapshot, AccountBalance, EmployeeStatus, OrderStatus,
    ProjectionState,
)
from core.operations.truth.event_store import EventStore, get_event_store, reset_event_store, EventFactory
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
from core.operations.truth.gateway import TruthGateway, get_gateway, reset_gateway


def _make_event(
    event_type: str = "stock_movement",
    domain: Domain = Domain.INVENTORY,
    aggregate_id: str = "test_001",
    payload: Dict[str, Any] = None,
    source_type: SourceType = SourceType.REAL,
    sequence: int = 1,
) -> Event:
    return EventFactory.create_event(
        source_type=source_type,
        domain=domain,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        timestamp=datetime.utcnow().isoformat() + "Z",
        sequence=sequence,
    )


def _seed_inventory_events(store: EventStore, base_id: str = "prod_001") -> List[str]:
    ids = []
    e1 = _make_event("batch_created", Domain.INVENTORY, f"batch_{base_id}_001", {
        "product_id": base_id, "initial_quantity": 100, "warehouse_id": "wh_01",
    }, sequence=1)
    ids.append(store.append(e1))

    e2 = _make_event("stock_movement", Domain.INVENTORY, f"batch_{base_id}_001", {
        "product_id": base_id, "quantity": 30, "direction": "out", "warehouse_id": "wh_01",
    }, sequence=2)
    ids.append(store.append(e2))

    e3 = _make_event("stock_movement", Domain.INVENTORY, f"batch_{base_id}_001", {
        "product_id": base_id, "quantity": 10, "direction": "out", "warehouse_id": "wh_01",
    }, sequence=3)
    ids.append(store.append(e3))
    return ids


def _seed_accounting_events(store: EventStore, base_id: str = "acct_001") -> List[str]:
    ids = []
    e1 = _make_event("account_created", Domain.ACCOUNTING, base_id, {
        "account_code": "1000", "account_name": "Cash", "account_type": "Asset",
    }, sequence=1)
    ids.append(store.append(e1))

    e2 = _make_event("account_created", Domain.ACCOUNTING, "acct_002", {
        "account_code": "4000", "account_name": "Revenue", "account_type": "Revenue",
    }, sequence=1)
    ids.append(store.append(e2))

    e3 = _make_event("journal_entry_posted", Domain.ACCOUNTING, "je_001", {
        "description": "Test entry",
        "entries": [
            {"account_id": base_id, "debit": 1000, "credit": 0},
            {"account_id": "acct_002", "debit": 0, "credit": 1000},
        ],
    }, sequence=1)
    ids.append(store.append(e3))
    return ids


def _seed_hr_events(store: EventStore, base_id: str = "emp_001") -> List[str]:
    ids = []
    e1 = _make_event("employee_hired", Domain.HR, base_id, {
        "name": "John Doe", "department": "Sales", "position": "Manager",
    }, sequence=1)
    ids.append(store.append(e1))

    e2 = _make_event("attendance_recorded", Domain.HR, base_id, {
        "date": "2026-05-01", "type": "present",
    }, sequence=2)
    ids.append(store.append(e2))

    e3 = _make_event("attendance_recorded", Domain.HR, base_id, {
        "date": "2026-05-02", "type": "present",
    }, sequence=3)
    ids.append(store.append(e3))
    return ids


def _seed_sp_events(store: EventStore, base_id: str = "ord_001") -> List[str]:
    ids = []
    e1 = _make_event("order_created", Domain.SALES_PURCHASE, base_id, {
        "order_type": "SALE", "customer_id": "cust_001", "total_amount": 5000,
    }, sequence=1)
    ids.append(store.append(e1))

    e2 = _make_event("order_approved", Domain.SALES_PURCHASE, base_id, {
        "approver_id": "user_001",
    }, sequence=2)
    ids.append(store.append(e2))

    e3 = _make_event("payment_received", Domain.SALES_PURCHASE, base_id, {
        "amount": 3000, "method": "bank_transfer",
    }, sequence=3)
    ids.append(store.append(e3))
    return ids


# ═══════════════════════════════════════════════════════════
# A. EVENT STORE IMMUTABILITY & APPEND-ONLY
# ═══════════════════════════════════════════════════════════

class EventStoreTest(unittest.TestCase):
    """Event Store is immutable and append-only."""

    def setUp(self):
        reset_event_store()

    def test_append_event(self):
        """Events can be appended to the store."""
        store = get_event_store()
        event = _make_event()
        eid = store.append(event)
        self.assertIsNotNone(eid)
        self.assertEqual(store.count(), 1)

    def test_duplicate_event_id_rejected(self):
        """Duplicate event_id raises ValueError."""
        store = get_event_store()
        event = _make_event()
        store.append(event)
        with self.assertRaises(ValueError):
            store.append(event)

    def test_get_event_by_id(self):
        """Events can be retrieved by ID."""
        store = get_event_store()
        event = _make_event(aggregate_id="get_test")
        eid = store.append(event)
        retrieved = store.get(eid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.event_id, eid)

    def test_get_by_domain(self):
        """Events can be filtered by domain."""
        store = get_event_store()
        store.append(_make_event(domain=Domain.INVENTORY, aggregate_id="inv_001"))
        store.append(_make_event(domain=Domain.ACCOUNTING, aggregate_id="acct_001", event_type="account_created"))
        inv_events = store.get_by_domain(Domain.INVENTORY)
        acct_events = store.get_by_domain(Domain.ACCOUNTING)
        self.assertEqual(len(inv_events), 1)
        self.assertEqual(len(acct_events), 1)

    def test_get_by_aggregate(self):
        """Events can be filtered by aggregate."""
        store = get_event_store()
        store.append(_make_event(aggregate_id="agg_001", sequence=1))
        store.append(_make_event(aggregate_id="agg_001", sequence=2))
        store.append(_make_event(aggregate_id="agg_002", sequence=1))
        events = store.get_by_aggregate(Domain.INVENTORY, "agg_001")
        self.assertEqual(len(events), 2)

    def test_get_by_source_type(self):
        """Events can be filtered by source type."""
        store = get_event_store()
        store.append(_make_event(source_type=SourceType.REAL, aggregate_id="real_001"))
        store.append(_make_event(source_type=SourceType.SIMULATION, aggregate_id="sim_001"))
        real = store.get_by_source_type(SourceType.REAL)
        sim = store.get_by_source_type(SourceType.SIMULATION)
        self.assertEqual(len(real), 1)
        self.assertEqual(len(sim), 1)

    def test_events_immutable_after_append(self):
        """Events are immutable (frozen dataclass)."""
        event = _make_event()
        with self.assertRaises(AttributeError):
            event.event_type = "modified"

    def test_event_requires_type_and_aggregate(self):
        """Events require event_type and aggregate_id."""
        with self.assertRaises(ValueError):
            Event(domain=Domain.INVENTORY)
        with self.assertRaises(ValueError):
            Event(event_type="test", domain=Domain.INVENTORY)

    def test_sequence_must_be_non_negative(self):
        """Sequence must be >= 0."""
        with self.assertRaises(ValueError):
            Event(event_type="test", domain=Domain.INVENTORY, aggregate_id="x", sequence=-1)

    def test_store_bounded(self):
        """Event store enforces max events."""
        store = EventStore(max_events=5)
        for i in range(10):
            store.append(_make_event(aggregate_id=f"bound_{i}", sequence=i))
        self.assertLessEqual(store.count(), 5)

    def test_get_all_returns_copy(self):
        """get_all returns a copy of events list."""
        store = get_event_store()
        store.append(_make_event(aggregate_id="copy_test"))
        all_events = store.get_all()
        all_events.clear()
        self.assertEqual(store.count(), 1)

    def test_event_factory_creates_valid_events(self):
        """EventFactory creates valid events."""
        event = EventFactory.create_event(
            SourceType.REAL, Domain.INVENTORY, "test_type", "agg_001", {"key": "value"},
        )
        self.assertEqual(event.event_type, "test_type")
        self.assertEqual(event.source_type, SourceType.REAL)
        self.assertEqual(event.payload["key"], "value")

    def test_append_returns_event_id(self):
        """append returns the event_id."""
        store = get_event_store()
        event = _make_event()
        eid = store.append(event)
        self.assertEqual(eid, event.event_id)

    def test_count_by_domain(self):
        """count_by_domain returns correct distribution."""
        store = get_event_store()
        store.append(_make_event(domain=Domain.INVENTORY, aggregate_id="i1"))
        store.append(_make_event(domain=Domain.INVENTORY, aggregate_id="i2"))
        store.append(_make_event(domain=Domain.ACCOUNTING, aggregate_id="a1", event_type="account_created"))
        counts = store.count_by_domain()
        self.assertEqual(counts["inventory"], 2)
        self.assertEqual(counts["accounting"], 1)

    def test_rebuild_from_list(self):
        """rebuild_from_list reconstructs store state."""
        store = get_event_store()
        events = [
            _make_event(aggregate_id="rebuild_001", sequence=1),
            _make_event(aggregate_id="rebuild_001", sequence=2),
        ]
        for e in events:
            store.append(e)
        saved = store.get_all()
        store2 = EventStore()
        store2.rebuild_from_list(saved)
        self.assertEqual(store.count(), store2.count())
        self.assertEqual(store.compute_state_hash(), store2.compute_state_hash())


# ═══════════════════════════════════════════════════════════
# B. EVENT EXISTENCE VERIFICATION
# ═══════════════════════════════════════════════════════════

class EventExistenceValidatorTest(unittest.TestCase):
    """Verifies claimed events actually exist in Event Store."""

    def setUp(self):
        reset_event_store()

    def test_verify_claim_success(self):
        """Verification succeeds for existing events."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="batch_prod_001_001",
            domain=Domain.INVENTORY,
        )
        result = validator.verify_claim(claim)
        self.assertTrue(result.verified)
        self.assertGreater(len(result.evidence_event_ids), 0)

    def test_verify_claim_missing_aggregate(self):
        """Verification fails for non-existent aggregate."""
        store = get_event_store()
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="stock_movement",
            aggregate_id="nonexistent",
            domain=Domain.INVENTORY,
        )
        result = validator.verify_claim(claim)
        self.assertFalse(result.verified)
        self.assertGreater(len(result.missing_entities), 0)

    def test_verify_claim_wrong_domain(self):
        """Verification detects domain mismatch."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="batch_prod_001_001",
            domain=Domain.ACCOUNTING,
        )
        result = validator.verify_claim(claim)
        self.assertFalse(result.verified)

    def test_verify_claim_insufficient_count(self):
        """Verification detects insufficient event count."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="stock_movement",
            aggregate_id="batch_prod_001_001",
            domain=Domain.INVENTORY,
            expected_count=5,
        )
        result = validator.verify_claim(claim)
        self.assertFalse(result.verified)

    def test_verify_expected_field_match(self):
        """Verification succeeds when expected field matches."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="batch_prod_001_001",
            domain=Domain.INVENTORY,
            expected_fields={"product_id": "prod_001"},
        )
        result = validator.verify_claim(claim)
        self.assertTrue(result.verified)

    def test_verify_expected_field_mismatch(self):
        """Verification fails when expected field doesn't match."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="batch_prod_001_001",
            domain=Domain.INVENTORY,
            expected_fields={"product_id": "nonexistent"},
        )
        result = validator.verify_claim(claim)
        self.assertFalse(result.verified)

    def test_verify_event_id_exists(self):
        """Quick check for event_id existence works."""
        store = get_event_store()
        eid = store.append(_make_event())
        validator = EventExistenceValidator(store)
        self.assertTrue(validator.verify_event_id(eid))
        self.assertFalse(validator.verify_event_id("nonexistent_id"))

    def test_verify_aggregate_exists(self):
        """Aggregate existence check works."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        exists, count = validator.verify_aggregate_exists(
            Domain.INVENTORY, "batch_prod_001_001",
        )
        self.assertTrue(exists)
        self.assertEqual(count, 3)

    def test_verify_batch_claims(self):
        """Batch verification works for multiple claims."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        validator = EventExistenceValidator(store)
        claims = [
            VerificationClaim(event_type="batch_created", aggregate_id="batch_prod_001_001", domain=Domain.INVENTORY),
            VerificationClaim(event_type="account_created", aggregate_id="acct_001", domain=Domain.ACCOUNTING),
            VerificationClaim(event_type="nonexistent", aggregate_id="nothing", domain=Domain.INVENTORY),
        ]
        results = validator.verify_claims_batch(claims)
        self.assertTrue(results[0].verified)
        self.assertTrue(results[1].verified)
        self.assertFalse(results[2].verified)

    def test_simulation_source_detected(self):
        """SIMULATION source events are correctly identified."""
        store = get_event_store()
        e = _make_event(source_type=SourceType.SIMULATION, aggregate_id="sim_test")
        store.append(e)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="stock_movement",
            aggregate_id="sim_test",
            domain=Domain.INVENTORY,
            source_type=SourceType.REAL,
        )
        result = validator.verify_claim(claim)
        self.assertFalse(result.verified)
        self.assertGreater(len(result.inconsistencies), 0)


# ═══════════════════════════════════════════════════════════
# C. STATE RECONSTRUCTION FROM EVENTS ONLY
# ═══════════════════════════════════════════════════════════

class StateReconstructionEngineTest(unittest.TestCase):
    """State is reconstructed from Event Store only."""

    def setUp(self):
        reset_event_store()

    def test_reconstruct_inventory_aggregate(self):
        """Inventory state reconstructed correctly."""
        store = get_event_store()
        _seed_inventory_events(store)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.INVENTORY, "batch_prod_001_001")
        self.assertTrue(state["exists"])
        self.assertEqual(state["events_used"], 3)
        self.assertIn("current_state", state)
        self.assertEqual(state["current_state"].get("current_quantity"), 60)

    def test_reconstruct_accounting_aggregate(self):
        """Accounting state reconstructed correctly."""
        store = get_event_store()
        _seed_accounting_events(store)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.ACCOUNTING, "acct_001")
        self.assertTrue(state["exists"])
        state2 = engine.reconstruct_aggregate(Domain.ACCOUNTING, "je_001")
        self.assertTrue(state2["exists"])

    def test_reconstruct_hr_aggregate(self):
        """HR state reconstructed correctly."""
        store = get_event_store()
        _seed_hr_events(store)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.HR, "emp_001")
        self.assertTrue(state["exists"])
        self.assertEqual(state["current_state"].get("status"), "ACTIVE")

    def test_reconstruct_sp_aggregate(self):
        """Sales/Purchase state reconstructed correctly."""
        store = get_event_store()
        _seed_sp_events(store)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertTrue(state["exists"])
        cs = state["current_state"]
        self.assertEqual(cs.get("status"), "PARTIALLY_PAID")
        self.assertEqual(cs.get("paid_amount"), 3000)

    def test_reconstruct_nonexistent(self):
        """Non-existent aggregate returns exists=False."""
        engine = StateReconstructionEngine(get_event_store())
        state = engine.reconstruct_aggregate(Domain.INVENTORY, "nonexistent")
        self.assertFalse(state["exists"])
        self.assertEqual(state["events_used"], 0)

    def test_reconstruct_no_external_state(self):
        """Reconstruction does not use external state."""
        store = get_event_store()
        _seed_inventory_events(store)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.INVENTORY, "batch_prod_001_001")
        self.assertNotIn("cached", state)
        self.assertNotIn("external", state)
        self.assertNotIn("agent_provided", state)

    def test_reconstruct_inventory_with_adjustment(self):
        """Inventory adjustment is handled correctly."""
        store = get_event_store()
        _seed_inventory_events(store)
        e = _make_event("stock_adjusted", Domain.INVENTORY, "batch_prod_001_001", {
            "product_id": "prod_001", "new_quantity": 50,
        }, sequence=4)
        store.append(e)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.INVENTORY, "batch_prod_001_001")
        self.assertEqual(state["current_state"].get("current_quantity"), 50)

    def test_projection_hash_computed(self):
        """Projection hash is deterministic."""
        store = get_event_store()
        _seed_inventory_events(store)
        engine = StateReconstructionEngine(store)
        h1 = engine.compute_projection_hash(Domain.INVENTORY)
        h2 = engine.compute_projection_hash(Domain.INVENTORY)
        self.assertEqual(h1, h2)

    def test_reconstruct_employee_terminated(self):
        """Terminated employee status is correct."""
        store = get_event_store()
        _seed_hr_events(store)
        e = _make_event("employee_terminated", Domain.HR, "emp_001", {
            "termination_date": "2026-06-01", "reason": "Resigned",
        }, sequence=4)
        store.append(e)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.HR, "emp_001")
        self.assertEqual(state["current_state"].get("status"), "TERMINATED")

    def test_reconstruct_order_cancelled(self):
        """Cancelled order status is correct."""
        store = get_event_store()
        _seed_sp_events(store)
        e = _make_event("order_cancelled", Domain.SALES_PURCHASE, "ord_001", {
            "reason": "Customer request",
        }, sequence=4)
        store.append(e)
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertEqual(state["current_state"].get("status"), "CANCELLED")


# ═══════════════════════════════════════════════════════════
# D. DRIFT DETECTION
# ═══════════════════════════════════════════════════════════

class DriftDetectionTest(unittest.TestCase):
    """Drift between reported and actual state is detected."""

    def setUp(self):
        reset_event_store()

    def test_no_drift(self):
        """No drift when reported state matches actual."""
        store = get_event_store()
        _seed_inventory_events(store)
        detector = DriftDetectionLayer(store)
        report = detector.detect_drift(
            {"events_used": 3, "event_types": ["batch_created", "stock_movement"]},
            Domain.INVENTORY,
            "batch_prod_001_001",
        )
        self.assertFalse(report.drift_detected)

    def test_drift_missing_events(self):
        """Drift detected when events are missing."""
        store = get_event_store()
        _seed_inventory_events(store)
        detector = DriftDetectionLayer(store)
        report = detector.detect_drift(
            {"events_used": 10, "event_ids": ["nonexistent_001"]},
            Domain.INVENTORY,
            "batch_prod_001_001",
        )
        self.assertTrue(report.drift_detected)
        self.assertGreater(len(report.discrepancies), 0)

    def test_drift_by_event_ids(self):
        """Drift detected by event ID comparison."""
        store = get_event_store()
        eid = store.append(_make_event())
        detector = DriftDetectionLayer(store)
        report = detector.detect_drift_by_event_ids([eid, "nonexistent_id"])
        self.assertTrue(report.drift_detected)
        self.assertEqual(len(report.missing_event_ids), 1)

    def test_drift_nonexistent_aggregate(self):
        """Drift detected for non-existent aggregate."""
        detector = DriftDetectionLayer(get_event_store())
        report = detector.detect_drift(
            {"events_used": 5},
            Domain.INVENTORY,
            "nonexistent",
        )
        self.assertTrue(report.drift_detected)
        self.assertEqual(report.severity, DriftSeverity.HIGH)

    def test_drift_no_discrepancies(self):
        """No drift when all event IDs exist."""
        store = get_event_store()
        eid = store.append(_make_event(aggregate_id="drift_test"))
        detector = DriftDetectionLayer(store)
        report = detector.detect_drift_by_event_ids([eid])
        self.assertFalse(report.drift_detected)


# ═══════════════════════════════════════════════════════════
# E. PROJECTION ENGINE
# ═══════════════════════════════════════════════════════════

class InventoryProjectionTest(unittest.TestCase):
    """Inventory projection from Event Store."""

    def setUp(self):
        reset_event_store()

    def test_rebuild_tracks_quantities(self):
        """Inventory projection tracks stock quantities correctly."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        count = proj.rebuild()
        self.assertEqual(count, 3)
        snap = proj.get_snapshot("prod_001")
        self.assertIsNotNone(snap)
        self.assertEqual(snap.current_quantity, 60)

    def test_rebuild_tracks_movement_count(self):
        """Inventory projection tracks movement count."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        proj.rebuild()
        snap = proj.get_snapshot("prod_001")
        self.assertEqual(snap.movement_count, 2)

    def test_get_all_snapshots(self):
        """get_all_snapshots returns all entries."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        proj.rebuild()
        snaps = proj.get_all_snapshots()
        self.assertGreater(len(snaps), 0)

    def test_get_product_count(self):
        """get_product_count returns unique product count."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        proj.rebuild()
        self.assertEqual(proj.get_product_count(), 1)

    def test_get_snapshots_by_warehouse(self):
        """get_snapshots_by_warehouse filters correctly."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        proj.rebuild()
        snaps = proj.get_snapshots_by_warehouse("wh_01")
        self.assertGreater(len(snaps), 0)
        snaps2 = proj.get_snapshots_by_warehouse("wh_nonexistent")
        self.assertEqual(len(snaps2), 0)

    def test_projection_state(self):
        """get_projection_state returns valid metadata."""
        store = get_event_store()
        _seed_inventory_events(store)
        proj = InventoryProjection(store)
        proj.rebuild()
        state = proj.get_projection_state()
        self.assertEqual(state.domain, Domain.INVENTORY)
        self.assertEqual(state.event_count, 3)


class AccountingProjectionTest(unittest.TestCase):
    """Accounting projection from Event Store."""

    def setUp(self):
        reset_event_store()

    def test_rebuild_tracks_accounts(self):
        """Accounting projection tracks accounts correctly."""
        store = get_event_store()
        _seed_accounting_events(store)
        proj = AccountingProjection(store)
        count = proj.rebuild()
        self.assertGreater(count, 0)
        acct = proj.get_account_balance("acct_001")
        self.assertIsNotNone(acct)
        self.assertEqual(acct.account_code, "1000")

    def test_rebuild_tracks_balances(self):
        """Accounting projection tracks debit/credit balances."""
        store = get_event_store()
        _seed_accounting_events(store)
        proj = AccountingProjection(store)
        proj.rebuild()
        acct = proj.get_account_balance("acct_001")
        self.assertEqual(acct.total_debits, Decimal("1000"))
        self.assertEqual(acct.balance, Decimal("1000"))

    def test_get_trial_balance(self):
        """Trial balance is computed correctly."""
        store = get_event_store()
        _seed_accounting_events(store)
        proj = AccountingProjection(store)
        proj.rebuild()
        tb = proj.get_trial_balance()
        self.assertTrue(tb["is_balanced"])
        self.assertEqual(tb["account_count"], 2)

    def test_get_journal_entry(self):
        """Journal entry summary is tracked."""
        store = get_event_store()
        _seed_accounting_events(store)
        proj = AccountingProjection(store)
        proj.rebuild()
        je = proj.get_journal_entry("je_001")
        self.assertIsNotNone(je)
        self.assertTrue(je.is_balanced)
        self.assertEqual(je.line_count, 2)

    def test_projection_state(self):
        """get_projection_state returns valid metadata."""
        store = get_event_store()
        _seed_accounting_events(store)
        proj = AccountingProjection(store)
        proj.rebuild()
        state = proj.get_projection_state()
        self.assertEqual(state.domain, Domain.ACCOUNTING)


class HRProjectionTest(unittest.TestCase):
    """HR projection from Event Store."""

    def setUp(self):
        reset_event_store()

    def test_rebuild_tracks_employees(self):
        """HR projection tracks employees correctly."""
        store = get_event_store()
        _seed_hr_events(store)
        proj = HRProjection(store)
        count = proj.rebuild()
        self.assertGreater(count, 0)
        emp = proj.get_employee("emp_001")
        self.assertIsNotNone(emp)
        self.assertEqual(emp.status, "ACTIVE")

    def test_get_active_employees(self):
        """Active employees filtered correctly."""
        store = get_event_store()
        _seed_hr_events(store)
        proj = HRProjection(store)
        proj.rebuild()
        active = proj.get_active_employees()
        self.assertEqual(len(active), 1)

    def test_attendance_rate(self):
        """Attendance rate is computed correctly."""
        store = get_event_store()
        _seed_hr_events(store)
        proj = HRProjection(store)
        proj.rebuild()
        emp = proj.get_employee("emp_001")
        self.assertGreater(emp.attendance_rate, 0)

    def test_department_headcount(self):
        """Department headcount is computed correctly."""
        store = get_event_store()
        _seed_hr_events(store)
        proj = HRProjection(store)
        proj.rebuild()
        depts = proj.get_department_headcount()
        self.assertIn("Sales", depts)
        self.assertEqual(depts["Sales"], 1)


class SalesPurchaseProjectionTest(unittest.TestCase):
    """Sales/Purchase projection from Event Store."""

    def setUp(self):
        reset_event_store()

    def test_rebuild_tracks_orders(self):
        """SP projection tracks orders correctly."""
        store = get_event_store()
        _seed_sp_events(store)
        proj = SalesPurchaseProjection(store)
        count = proj.rebuild()
        self.assertGreater(count, 0)
        order = proj.get_order("ord_001")
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "PARTIALLY_PAID")

    def test_open_orders(self):
        """Open orders filtered correctly."""
        store = get_event_store()
        _seed_sp_events(store)
        proj = SalesPurchaseProjection(store)
        proj.rebuild()
        open_orders = proj.get_open_orders()
        self.assertGreater(len(open_orders), 0)

    def test_receivable_payable(self):
        """Receivable and payable totals computed."""
        store = get_event_store()
        _seed_sp_events(store)
        proj = SalesPurchaseProjection(store)
        proj.rebuild()
        receivable = proj.get_total_receivable()
        self.assertGreater(receivable, Decimal("0"))

    def test_fulfillment_state(self):
        """Fulfillment state tracked correctly."""
        store = get_event_store()
        _seed_sp_events(store)
        e = _make_event("goods_dispatched", Domain.SALES_PURCHASE, "ord_001", {
            "dispatched_at": "2026-05-13T10:00:00Z",
        }, sequence=4)
        store.append(e)
        proj = SalesPurchaseProjection(store)
        proj.rebuild()
        order = proj.get_order("ord_001")
        self.assertEqual(order.fulfillment_state, "DISPATCHED")


# ═══════════════════════════════════════════════════════════
# F. LIVE REPORTING
# ═══════════════════════════════════════════════════════════

class LiveReportingTest(unittest.TestCase):
    """All reports are query-driven and event-backed."""

    def setUp(self):
        reset_event_store()
        self.store = get_event_store()
        _seed_inventory_events(self.store)
        _seed_accounting_events(self.store)
        _seed_hr_events(self.store)
        _seed_sp_events(self.store)

    def test_inventory_stock_levels_report(self):
        """Stock levels report returns verified data."""
        builder = InventoryReportBuilder(store=self.store)
        report = builder.get_stock_levels()
        self.assertEqual(report.report_type, "stock_levels")
        self.assertIsNotNone(report.audit)
        self.assertGreater(report.audit.events_scanned, 0)
        self.assertIn("stock_levels", report.data)
        self.assertGreater(len(report.data["stock_levels"]), 0)

    def test_inventory_warehouse_distribution(self):
        """Warehouse distribution report works."""
        builder = InventoryReportBuilder(store=self.store)
        report = builder.get_warehouse_distribution()
        self.assertIsNotNone(report.audit)
        self.assertIn("warehouses", report.data)

    def test_inventory_batch_breakdown(self):
        """Batch breakdown report works."""
        builder = InventoryReportBuilder(store=self.store)
        report = builder.get_batch_breakdown()
        self.assertIsNotNone(report.audit)
        self.assertIn("batches", report.data)

    def test_accounting_ledger_balances(self):
        """Ledger balances report works."""
        builder = AccountingReportBuilder(store=self.store)
        report = builder.get_ledger_balances()
        self.assertIn("accounts", report.data)
        self.assertIsNotNone(report.audit)

    def test_accounting_journal_entries(self):
        """Journal entries report works."""
        builder = AccountingReportBuilder(store=self.store)
        report = builder.get_journal_entries()
        self.assertIn("journal_entries", report.data)

    def test_accounting_trial_balance(self):
        """Trial balance report works."""
        builder = AccountingReportBuilder(store=self.store)
        report = builder.get_trial_balance()
        self.assertTrue(report.data["is_balanced"])

    def test_hr_employee_roster(self):
        """Employee roster report works."""
        builder = HRReportBuilder(store=self.store)
        report = builder.get_employee_roster()
        self.assertIn("employees", report.data)
        self.assertGreater(report.data["total_employees"], 0)

    def test_hr_attendance_summary(self):
        """Attendance summary report works."""
        builder = HRReportBuilder(store=self.store)
        report = builder.get_attendance_summary()
        self.assertIn("attendance_records", report.data)

    def test_sp_order_status(self):
        """Order status report works."""
        builder = SalesPurchaseReportBuilder(store=self.store)
        report = builder.get_order_status()
        self.assertIn("orders", report.data)

    def test_sp_payment_status(self):
        """Payment status report works."""
        builder = SalesPurchaseReportBuilder(store=self.store)
        report = builder.get_payment_status()
        self.assertIn("payments", report.data)

    def test_sp_fulfillment_state(self):
        """Fulfillment state report works."""
        builder = SalesPurchaseReportBuilder(store=self.store)
        report = builder.get_fulfillment_state()
        self.assertIn("fulfillment", report.data)

    def test_report_has_verification(self):
        """Every report includes verification metadata."""
        builder = InventoryReportBuilder(store=self.store)
        report = builder.get_stock_levels()
        self.assertIsNotNone(report.verification)
        self.assertIsNotNone(report.audit.projection_hash)
        self.assertGreater(len(report.audit.projection_hash), 0)


# ═══════════════════════════════════════════════════════════
# G. CONSISTENCY VERIFICATION
# ═══════════════════════════════════════════════════════════

class ConsistencyVerificationTest(unittest.TestCase):
    """Event Store consistency checks work correctly."""

    def setUp(self):
        reset_event_store()

    def test_consistency_check_passes(self):
        """Consistency check passes with valid events."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        result = store.run_consistency_check()
        self.assertTrue(result.consistent)

    def test_consistency_check_reports_counts(self):
        """Consistency check reports event counts."""
        store = get_event_store()
        _seed_inventory_events(store)
        result = store.run_consistency_check()
        self.assertGreater(result.total_events, 0)
        self.assertIn("inventory", result.events_by_domain)

    def test_consistency_check_detects_sequence_gaps(self):
        """Consistency check detects sequence gaps."""
        store = get_event_store()
        store.append(_make_event(aggregate_id="gap_test", sequence=1))
        store.append(_make_event(aggregate_id="gap_test", sequence=3))
        result = store.run_consistency_check()
        self.assertFalse(result.consistent)
        self.assertGreater(len(result.sequence_gaps), 0)

    def test_state_hash_consistency(self):
        """State hash is consistent across identical stores."""
        store1 = get_event_store()
        _seed_inventory_events(store1)
        h1 = store1.compute_state_hash()
        store2 = EventStore()
        for e in store1.get_all():
            store2.append(e)
        h2 = store2.compute_state_hash()
        self.assertEqual(h1, h2)

    def test_state_hash_changes_with_new_events(self):
        """State hash changes when events are added."""
        store = get_event_store()
        _seed_inventory_events(store)
        h1 = store.compute_state_hash()
        store.append(_make_event(aggregate_id="new_event", sequence=1))
        h2 = store.compute_state_hash()
        self.assertNotEqual(h1, h2)


# ═══════════════════════════════════════════════════════════
# H. DETERMINISM
# ═══════════════════════════════════════════════════════════

class DeterminismTest(unittest.TestCase):
    """All operations are deterministic."""

    def test_identical_events_produce_identical_state(self):
        """Same events produce identical projection state."""
        store1 = EventStore()
        _seed_inventory_events(store1)
        proj1 = InventoryProjection(store1)
        proj1.rebuild()

        store2 = EventStore()
        for e in store1.get_all():
            store2.append(e)
        proj2 = InventoryProjection(store2)
        proj2.rebuild()

        self.assertEqual(
            proj1.get_state_hash(),
            proj2.get_state_hash(),
        )

    def test_verification_deterministic_across_calls(self):
        """Same claim produces same verification result."""
        store = get_event_store()
        _seed_inventory_events(store)
        validator = EventExistenceValidator(store)
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="batch_prod_001_001",
            domain=Domain.INVENTORY,
        )
        r1 = validator.verify_claim(claim)
        r2 = validator.verify_claim(claim)
        self.assertEqual(r1.verified, r2.verified)
        self.assertEqual(r1.evidence_event_ids, r2.evidence_event_ids)

    def test_report_deterministic(self):
        """Same store produces same report."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder1 = InventoryReportBuilder(store=store)
        builder2 = InventoryReportBuilder(store=store)
        r1 = builder1.get_stock_levels()
        r2 = builder2.get_stock_levels()
        self.assertEqual(len(r1.data["stock_levels"]), len(r2.data["stock_levels"]))

    def test_drift_deterministic(self):
        """Same drift detection produces same result."""
        store = get_event_store()
        _seed_inventory_events(store)
        detector = DriftDetectionLayer(store)
        r1 = detector.detect_drift({"events_used": 3}, Domain.INVENTORY, "batch_prod_001_001")
        r2 = detector.detect_drift({"events_used": 3}, Domain.INVENTORY, "batch_prod_001_001")
        self.assertEqual(r1.drift_detected, r2.drift_detected)


# ═══════════════════════════════════════════════════════════
# I. NO FABRICATED DATA
# ═══════════════════════════════════════════════════════════

class NoFabricatedDataTest(unittest.TestCase):
    """No data is fabricated — all outputs are event-backed."""

    def setUp(self):
        reset_event_store()

    def test_empty_store_returns_empty_reports(self):
        """Empty store produces empty reports."""
        builder = InventoryReportBuilder(store=get_event_store())
        report = builder.get_stock_levels()
        self.assertEqual(len(report.data["stock_levels"]), 0)

    def test_missing_aggregate_reported(self):
        """Missing aggregate is reported, not fabricated."""
        store = get_event_store()
        engine = StateReconstructionEngine(store)
        state = engine.reconstruct_aggregate(Domain.INVENTORY, "nonexistent")
        self.assertFalse(state["exists"])
        self.assertEqual(state["events_used"], 0)

    def test_no_synthetic_data_in_reports(self):
        """Reports do not contain synthetic data."""
        builder = InventoryReportBuilder(store=get_event_store())
        report = builder.get_stock_levels()
        for item in report.data["stock_levels"]:
            self.assertNotIn("estimated", item)
            self.assertNotIn("inferred", item)
            self.assertNotIn("predicted", item)

    def test_drift_detects_fake_events(self):
        """Drift detection catches fake event IDs."""
        detector = DriftDetectionLayer(get_event_store())
        report = detector.detect_drift_by_event_ids(["fake_event_001", "fake_event_002"])
        self.assertTrue(report.drift_detected)


# ═══════════════════════════════════════════════════════════
# J. AUDIT TRAIL ENFORCEMENT
# ═══════════════════════════════════════════════════════════

class AuditTrailEnforcementTest(unittest.TestCase):
    """Every report includes complete audit metadata."""

    def setUp(self):
        reset_event_store()

    def test_report_has_report_id(self):
        """Every report has a unique report_id."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertIsNotNone(report.report_id)
        self.assertGreater(len(report.report_id), 0)

    def test_report_has_audit(self):
        """Every report has an audit block."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertIsNotNone(report.audit)
        self.assertIsNotNone(report.audit.report_id)
        self.assertIsNotNone(report.audit.report_type)

    def test_audit_has_event_range(self):
        """Audit includes event range scanned."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertGreaterEqual(report.audit.event_range_end, report.audit.event_range_start)

    def test_audit_has_events_scanned_count(self):
        """Audit includes count of events scanned."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertGreater(report.audit.events_scanned, 0)

    def test_audit_has_projection_hash(self):
        """Audit includes projection verification hash."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertGreater(len(report.audit.projection_hash), 0)

    def test_audit_has_timestamp(self):
        """Audit includes generation timestamp."""
        store = get_event_store()
        _seed_inventory_events(store)
        builder = InventoryReportBuilder(store=store)
        report = builder.get_stock_levels()
        self.assertIsNotNone(report.generated_at)
        self.assertGreater(len(report.generated_at), 0)


# ═══════════════════════════════════════════════════════════
# K. CROSS-DOMAIN INTEGRITY
# ═══════════════════════════════════════════════════════════

class CrossDomainIntegrityTest(unittest.TestCase):
    """Multiple domains maintain independent integrity."""

    def setUp(self):
        reset_event_store()

    def test_multi_domain_event_store(self):
        """Event store handles multiple domains."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        _seed_hr_events(store)
        _seed_sp_events(store)
        self.assertEqual(store.count_by_domain()["inventory"], 3)
        self.assertEqual(store.count_by_domain()["accounting"], 3)
        self.assertEqual(store.count_by_domain()["hr"], 3)
        self.assertEqual(store.count_by_domain()["sales_purchase"], 3)

    def test_domain_independent_projections(self):
        """Each domain projection is independent."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        inv_proj = InventoryProjection(store)
        acct_proj = AccountingProjection(store)
        inv_count = inv_proj.rebuild()
        acct_count = acct_proj.rebuild()
        self.assertGreater(inv_count, 0)
        self.assertGreater(acct_count, 0)

    def test_consistency_across_domains(self):
        """Consistency check spans all domains."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        result = store.run_consistency_check()
        self.assertEqual(
            result.total_events,
            sum(result.events_by_domain.values()),
        )

    def test_verify_across_domains(self):
        """Verification works across multiple domains."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        validator = EventExistenceValidator(store)
        inv_claim = VerificationClaim(event_type="batch_created", aggregate_id="batch_prod_001_001", domain=Domain.INVENTORY)
        acct_claim = VerificationClaim(event_type="account_created", aggregate_id="acct_001", domain=Domain.ACCOUNTING)
        self.assertTrue(validator.verify_claim(inv_claim).verified)
        self.assertTrue(validator.verify_claim(acct_claim).verified)

    def test_cross_domain_report_independence(self):
        """Each domain's reports are independent."""
        store = get_event_store()
        _seed_inventory_events(store)
        _seed_accounting_events(store)
        inv_builder = InventoryReportBuilder(store=store)
        acct_builder = AccountingReportBuilder(store=store)
        inv_report = inv_builder.get_stock_levels()
        acct_report = acct_builder.get_ledger_balances()
        self.assertEqual(inv_report.domain, Domain.INVENTORY)
        self.assertEqual(acct_report.domain, Domain.ACCOUNTING)


# ═══════════════════════════════════════════════════════════
# L. TRUTH GATEWAY INTEGRATION
# ═══════════════════════════════════════════════════════════

class TruthGatewayIntegrationTest(unittest.TestCase):
    """TruthGateway orchestrates the complete pipeline."""

    def setUp(self):
        reset_gateway()

    def test_emit_event(self):
        """Gateway emits events to store."""
        gateway = get_gateway()
        eid = gateway.emit_event(
            SourceType.REAL, Domain.INVENTORY,
            "stock_movement", "prod_001",
            {"quantity": 10, "direction": "out"},
        )
        self.assertIsNotNone(eid)

    def test_emit_events_batch(self):
        """Gateway emits batch events."""
        gateway = get_gateway()
        ids = gateway.emit_events_batch([
            {"source_type": SourceType.REAL, "domain": Domain.INVENTORY,
             "event_type": "batch_created", "aggregate_id": "b1",
             "payload": {"initial_quantity": 100}},
            {"source_type": SourceType.REAL, "domain": Domain.INVENTORY,
             "event_type": "stock_movement", "aggregate_id": "b1",
             "payload": {"quantity": 10, "direction": "out"}},
        ])
        self.assertEqual(len(ids), 2)

    def test_get_event(self):
        """Gateway retrieves events by ID."""
        gateway = get_gateway()
        eid = gateway.emit_event(
            SourceType.REAL, Domain.INVENTORY,
            "test_event", "agg_001", {"key": "value"},
        )
        retrieved = gateway.get_event(eid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["event_type"], "test_event")

    def test_get_nonexistent_event(self):
        """Nonexistent event returns None."""
        gateway = get_gateway()
        self.assertIsNone(gateway.get_event("nonexistent"))

    def test_verify_event_exists(self):
        """Gateway verifies event existence."""
        gateway = get_gateway()
        eid = gateway.emit_event(
            SourceType.REAL, Domain.INVENTORY,
            "test_event", "agg_001", {},
        )
        self.assertTrue(gateway.verify_event_exists(eid))
        self.assertFalse(gateway.verify_event_exists("fake"))

    def test_verify_aggregate(self):
        """Gateway verifies aggregate state."""
        gateway = get_gateway()
        gateway.emit_event(
            SourceType.REAL, Domain.INVENTORY,
            "stock_movement", "agg_001", {"quantity": 10, "direction": "out"},
        )
        state = gateway.verify_aggregate(Domain.INVENTORY, "agg_001")
        self.assertTrue(state["exists"])

    def test_detect_drift(self):
        """Gateway detects drift."""
        gateway = get_gateway()
        report = gateway.detect_drift_by_event_ids(["fake_id"])
        self.assertTrue(report.drift_detected)

    def test_full_report_pipeline(self):
        """Full report pipeline works end-to-end."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "batch_001",
                           {"initial_quantity": 100, "product_id": "p1"})
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "stock_movement", "batch_001",
                           {"quantity": 20, "direction": "out", "product_id": "p1"})
        report = gateway.get_stock_levels()
        self.assertGreater(len(report.data["stock_levels"]), 0)

    def test_multiple_reports_independent(self):
        """Multiple reports are independent."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "batch_001",
                           {"initial_quantity": 100, "product_id": "p1"})
        stock = gateway.get_stock_levels()
        wh = gateway.get_warehouse_distribution()
        batch = gateway.get_batch_breakdown()
        self.assertIsNotNone(stock)
        self.assertIsNotNone(wh)
        self.assertIsNotNone(batch)

    def test_consistency_check_from_gateway(self):
        """Gateway provides consistency check."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "b1", {"initial_quantity": 100})
        result = gateway.run_consistency_check()
        self.assertTrue(result.consistent)

    def test_rebuild_all_projections(self):
        """Gateway rebuilds all projections."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "b1", {"initial_quantity": 100})
        counts = gateway.rebuild_all_projections()
        self.assertIn("inventory", counts)
        self.assertIn("accounting", counts)
        self.assertIn("hr", counts)
        self.assertIn("sales_purchase", counts)

    def test_gateway_reset(self):
        """Gateway reset clears all state."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "b1", {"initial_quantity": 100})
        gateway.reset()
        self.assertEqual(gateway._store.count(), 0)

    def test_gateway_store_summary(self):
        """Gateway provides store summary."""
        gateway = get_gateway()
        gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                           "batch_created", "b1", {"initial_quantity": 100})
        summary = gateway.get_store_summary()
        self.assertGreater(summary["total_events"], 0)
        self.assertIn("state_hash", summary)

    def test_gateway_verify_claim(self):
        """Gateway verifies claims end-to-end."""
        gateway = get_gateway()
        eid = gateway.emit_event(SourceType.REAL, Domain.INVENTORY,
                                 "batch_created", "b1", {"initial_quantity": 100})
        claim = VerificationClaim(
            event_type="batch_created",
            aggregate_id="b1",
            domain=Domain.INVENTORY,
        )
        result = gateway.verify_claim(claim)
        self.assertTrue(result.verified)

    def test_gateway_emit_wrong_source_type(self):
        """Gateway handles simulation source type correctly."""
        gateway = get_gateway()
        eid = gateway.emit_event(
            SourceType.SIMULATION, Domain.INVENTORY,
            "stock_movement", "sim_test", {"quantity": 50, "direction": "in"},
        )
        self.assertIsNotNone(eid)
        event = gateway.get_event(eid)
        self.assertEqual(event["source_type"], "SIMULATION")

    def test_gateway_stock_levels_empty(self):
        """Stock levels returns empty for empty store."""
        gateway = get_gateway()
        report = gateway.get_stock_levels()
        self.assertEqual(len(report.data["stock_levels"]), 0)


# ═══════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    unittest.main()
