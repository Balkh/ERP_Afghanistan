"""
Phase 5B.3 — Truth Verification Data Models.

All models are immutable frozen dataclasses.
These define the contracts for event verification, drift detection,
and live reporting — all backed by persisted Event Store data only.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from enum import Enum

TRUTH_MODELS_VERSION = "1.0.0"


class SourceType(str, Enum):
    REAL = "REAL"
    SIMULATION = "SIMULATION"
    MANUAL = "MANUAL"


class Domain(str, Enum):
    ACCOUNTING = "accounting"
    FIXED_ASSETS = "fixed_assets"
    HR = "hr"
    SALES_PURCHASE = "sales_purchase"
    INVENTORY = "inventory"


class DriftType(str, Enum):
    MISSING_EVENTS = "MISSING_EVENTS"
    DUPLICATION = "DUPLICATION"
    STATE_MISMATCH = "STATE_MISMATCH"
    DOMAIN_MISMATCH = "DOMAIN_MISMATCH"
    TIMESTAMP_VIOLATION = "TIMESTAMP_VIOLATION"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    SOURCE_TYPE_INCONSISTENCY = "SOURCE_TYPE_INCONSISTENCY"


class DriftSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Event:
    """Immutable event in the append-only Event Store.

    This is the canonical event format for the Digital Twin.
    Every event represents a single, atomic state change.
    """
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    source_type: SourceType = SourceType.REAL
    domain: Domain = Domain.INVENTORY
    event_type: str = ""
    aggregate_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sequence: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.aggregate_id:
            raise ValueError("aggregate_id is required")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")


@dataclass(frozen=True)
class ClaimVerification:
    """Result of verifying a claimed event against the Event Store."""
    claim_id: str = ""
    claim_event_type: str = ""
    claim_aggregate_id: str = ""
    verified: bool = False
    evidence_event_ids: List[str] = field(default_factory=list)
    missing_entities: List[str] = field(default_factory=list)
    verification_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    inconsistencies: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DriftReport:
    """Report of drift between reported state and actual Event Store state."""
    drift_detected: bool = False
    drift_type: Optional[DriftType] = None
    severity: DriftSeverity = DriftSeverity.LOW
    affected_domains: List[str] = field(default_factory=list)
    reported_state_summary: Dict[str, Any] = field(default_factory=dict)
    actual_state_summary: Dict[str, Any] = field(default_factory=dict)
    missing_event_ids: List[str] = field(default_factory=list)
    discrepancies: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class ReportAudit:
    """Audit metadata for every emitted report."""
    report_id: str = field(default_factory=lambda: f"rpt_{uuid4().hex[:8]}")
    report_type: str = ""
    domain: Domain = Domain.INVENTORY
    event_range_start: int = 0
    event_range_end: int = 0
    events_scanned: int = 0
    projection_hash: str = ""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    query_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConsistencyResult:
    """Cross-domain consistency verification result."""
    consistent: bool = False
    total_events: int = 0
    events_by_domain: Dict[str, int] = field(default_factory=dict)
    events_by_source: Dict[str, int] = field(default_factory=dict)
    sequence_gaps: List[Dict[str, Any]] = field(default_factory=list)
    timestamp_anomalies: List[str] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class InventorySnapshot:
    """Point-in-time inventory state derived from Event Store."""
    product_id: str = ""
    warehouse_id: str = ""
    batch_id: str = ""
    current_quantity: Decimal = Decimal("0")
    last_movement_event_id: str = ""
    last_movement_timestamp: str = ""
    movement_count: int = 0


@dataclass(frozen=True)
class AccountBalance:
    """Point-in-time account balance from Event Store."""
    account_id: str = ""
    account_code: str = ""
    account_name: str = ""
    account_type: str = ""
    total_debits: Decimal = Decimal("0")
    total_credits: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    last_journal_entry_id: str = ""


@dataclass(frozen=True)
class JournalEntrySummary:
    """Summary of a journal entry from Event Store."""
    journal_entry_id: str = ""
    description: str = ""
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    is_balanced: bool = False
    line_count: int = 0
    posted_at: str = ""


@dataclass(frozen=True)
class EmployeeStatus:
    """Employee status derived from HR events."""
    employee_id: str = ""
    name: str = ""
    department: str = ""
    position: str = ""
    status: str = ""  # ACTIVE, TERMINATED, ON_LEAVE
    hire_date: str = ""
    last_event_id: str = ""
    attendance_rate: float = 0.0


@dataclass(frozen=True)
class OrderStatus:
    """Order status derived from Sales/Purchase events."""
    order_id: str = ""
    order_type: str = ""  # SALE, PURCHASE
    status: str = ""  # CREATED, APPROVED, DISPATCHED, RECEIVED, CANCELLED
    total_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
    last_event_id: str = ""
    fulfillment_state: str = ""


@dataclass(frozen=True)
class ProjectionState:
    """Complete projection state hash for integrity verification."""
    domain: Domain = Domain.INVENTORY
    event_count: int = 0
    last_event_id: str = ""
    state_hash: str = ""
    projected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    entity_count: int = 0


@dataclass(frozen=True)
class VerificationClaim:
    """A claim to be verified against the Event Store."""
    claim_id: str = field(default_factory=lambda: f"clm_{uuid4().hex[:8]}")
    event_type: str = ""
    aggregate_id: str = ""
    domain: Domain = Domain.INVENTORY
    source_type: SourceType = SourceType.REAL
    expected_count: int = 1
    expected_fields: Dict[str, Any] = field(default_factory=dict)
    timestamp_range: Optional[tuple] = None


@dataclass(frozen=True)
class VerifiedReport:
    """A complete verified report output."""
    report_id: str = field(default_factory=lambda: f"vr_{uuid4().hex[:8]}")
    report_type: str = ""
    domain: Domain = Domain.INVENTORY
    audit: Optional[ReportAudit] = None
    data: Dict[str, Any] = field(default_factory=dict)
    verification: Optional[ConsistencyResult] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
