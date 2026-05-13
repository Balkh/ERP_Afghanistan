"""
Phase 5B.4 — Observability Data Models.

All models are immutable frozen dataclasses.
These define the contracts for traces, timelines, correlations,
integrity reports, and stream monitoring — ALL read-only.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from enum import Enum


OBSERVABILITY_MODELS_VERSION = "1.0.0"


class IntegrityStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    DEGRADED = "DEGRADED"


class StreamHealth(str, Enum):
    HEALTHY = "HEALTHY"
    LAGGING = "LAGGING"
    STALLED = "STALLED"


@dataclass(frozen=True)
class TraceEvent:
    """A single event in a reconstructed trace chain."""
    event_id: str = ""
    event_type: str = ""
    domain: str = ""
    aggregate_id: str = ""
    sequence: int = 0
    timestamp: str = ""
    source_type: str = "REAL"
    payload_summary: Dict[str, Any] = field(default_factory=dict)
    causation_id: str = ""
    correlation_id: str = ""


@dataclass(frozen=True)
class CausationLink:
    """A cause → effect link between two events."""
    cause_event_id: str = ""
    effect_event_id: str = ""
    relationship: str = ""  # DIRECT_CAUSE, DERIVED, CORRELATED
    domain_crossing: bool = False


@dataclass(frozen=True)
class TraceObject:
    """Complete lifecycle trace of an entity."""
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    aggregate_id: str = ""
    domain: str = ""
    root_event_id: str = ""
    full_event_chain: List[TraceEvent] = field(default_factory=list)
    causation_graph: List[CausationLink] = field(default_factory=list)
    domain_participation_map: Dict[str, List[str]] = field(default_factory=dict)
    timestamp_range_start: str = ""
    timestamp_range_end: str = ""
    event_count: int = 0
    integrity_hash: str = ""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class CorrelationGraph:
    """Cross-domain correlation relationships."""
    graph_id: str = field(default_factory=lambda: f"cg_{uuid4().hex[:8]}")
    root_event_id: str = ""
    nodes: List[TraceEvent] = field(default_factory=list)
    edges: List[CausationLink] = field(default_factory=list)
    domains_involved: List[str] = field(default_factory=list)
    dependency_clusters: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class TimelineEntry:
    """A single entry in a deterministic timeline."""
    event_id: str = ""
    event_type: str = ""
    domain: str = ""
    aggregate_id: str = ""
    timestamp: str = ""
    sequence: int = 0
    source_type: str = "REAL"
    summary: str = ""


@dataclass(frozen=True)
class TimelineView:
    """Deterministic, ordered timeline of events."""
    timeline_id: str = field(default_factory=lambda: f"tl_{uuid4().hex[:8]}")
    from_timestamp: str = ""
    to_timestamp: str = ""
    entries: List[TimelineEntry] = field(default_factory=list)
    total_entries: int = 0
    domains_present: List[str] = field(default_factory=list)
    source_types_present: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class IntegrityReport:
    """System-wide integrity status."""
    report_id: str = field(default_factory=lambda: f"ir_{uuid4().hex[:8]}")
    status: IntegrityStatus = IntegrityStatus.PASS
    detected_anomalies: List[Dict[str, Any]] = field(default_factory=list)
    affected_domains: List[str] = field(default_factory=list)
    consistency_hash: str = ""
    total_events_checked: int = 0
    sequence_gaps: int = 0
    missing_events: int = 0
    domain_balances: Dict[str, bool] = field(default_factory=dict)
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class StreamMetrics:
    """Read-only stream monitoring metrics."""
    total_events_received: int = 0
    events_per_second: float = 0.0
    events_by_domain: Dict[str, int] = field(default_factory=dict)
    events_by_source: Dict[str, int] = field(default_factory=dict)
    last_event_timestamp: str = ""
    health: StreamHealth = StreamHealth.HEALTHY
    lag_seconds: int = 0
    sampled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class ReplayState:
    """Deterministic replay state."""
    replay_id: str = field(default_factory=lambda: f"rp_{uuid4().hex[:8]}")
    from_sequence: int = 0
    to_sequence: int = 0
    current_sequence: int = 0
    total_events_in_range: int = 0
    domains_in_range: List[str] = field(default_factory=list)
    is_complete: bool = False
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class DashboardView:
    """Read-only dashboard view."""
    dashboard_id: str = ""
    dashboard_type: str = ""
    domain: str = ""
    timeline: Optional[Any] = None
    projections: Dict[str, Any] = field(default_factory=dict)
    integrity: Optional[IntegrityReport] = None
    correlation: Optional[CorrelationGraph] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class ObservabilitySnapshot:
    """Point-in-time snapshot of the entire observability system."""
    snapshot_id: str = field(default_factory=lambda: f"os_{uuid4().hex[:8]}")
    total_events: int = 0
    total_traces_built: int = 0
    integrity_status: IntegrityStatus = IntegrityStatus.PASS
    stream_health: StreamHealth = StreamHealth.HEALTHY
    domain_event_counts: Dict[str, int] = field(default_factory=dict)
    correlation_graphs: int = 0
    taken_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
