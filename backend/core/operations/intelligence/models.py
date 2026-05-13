"""
Phase 5B.5 — Intelligence Data Models.

All models are immutable frozen dataclasses.
Every output MUST include confidence_level, baseline_source, and model_limitations.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from enum import Enum


INTELLIGENCE_MODELS_VERSION = "1.0.0"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DriftDirection(str, Enum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    CYCLICAL = "CYCLICAL"
    UNKNOWN = "UNKNOWN"


class PatternType(str, Enum):
    FREQUENT_SEQUENCE = "FREQUENT_SEQUENCE"
    RARE_EVENT = "RARE_EVENT"
    CYCLIC_PATTERN = "CYCLIC_PATTERN"
    BURST_DETECTION = "BURST_DETECTION"
    EVENT_CLUSTER = "EVENT_CLUSTER"


class DeviationType(str, Enum):
    MISSING_EVENTS = "MISSING_EVENTS"
    DUPLICATE_EVENTS = "DUPLICATE_EVENTS"
    PROJECTION_MISMATCH = "PROJECTION_MISMATCH"
    CROSS_DOMAIN_INCONSISTENCY = "CROSS_DOMAIN_INCONSISTENCY"
    SEQUENCE_ANOMALY = "SEQUENCE_ANOMALY"
    TIMING_ANOMALY = "TIMING_ANOMALY"


@dataclass(frozen=True)
class ModelLimitations:
    """Explicit limitations of the analytical model."""
    missing_data_assumptions: List[str] = field(default_factory=list)
    statistical_approximations: List[str] = field(default_factory=list)
    temporal_sampling_constraints: List[str] = field(default_factory=list)
    known_bias: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BaselineReference:
    """Reference window used for baseline computation."""
    window_start: str = ""
    window_end: str = ""
    total_events_in_window: int = 0
    domains_in_window: List[str] = field(default_factory=list)
    mean_event_rate: float = 0.0
    std_event_rate: float = 0.0


@dataclass(frozen=True)
class DeviationVector:
    """Multi-dimensional deviation measurement."""
    absolute_deviation: float = 0.0
    percentage_deviation: float = 0.0
    z_score: float = 0.0
    direction: DriftDirection = DriftDirection.UNKNOWN


@dataclass(frozen=True)
class DriftReport:
    """Single entity drift detection output."""
    report_id: str = field(default_factory=lambda: f"dr_{uuid4().hex[:8]}")
    domain: str = ""
    entity_id: str = ""
    drift_score: float = 0.0
    drift_velocity: float = 0.0
    baseline_reference: Optional[BaselineReference] = None
    deviation_vector: Optional[DeviationVector] = None
    timestamp_range_start: str = ""
    timestamp_range_end: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class EventPattern:
    """A detected event pattern."""
    pattern_id: str = field(default_factory=lambda: f"ep_{uuid4().hex[:8]}")
    pattern_type: PatternType = PatternType.EVENT_CLUSTER
    domain: str = ""
    event_types: List[str] = field(default_factory=list)
    occurrence_count: int = 0
    frequency: float = 0.0
    window_start: str = ""
    window_end: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None


@dataclass(frozen=True)
class AnomalyNode:
    """A single node in the cross-domain anomaly graph."""
    anomaly_id: str = ""
    event_id: str = ""
    domain: str = ""
    event_type: str = ""
    aggregate_id: str = ""
    timestamp: str = ""
    anomaly_score: float = 0.0


@dataclass(frozen=True)
class AnomalyEdge:
    """A correlation link between two anomaly nodes."""
    source_anomaly_id: str = ""
    target_anomaly_id: str = ""
    correlation_strength: float = 0.0
    domains_crossed: bool = False


@dataclass(frozen=True)
class AnomalyGraph:
    """Cross-domain anomaly correlation graph."""
    graph_id: str = field(default_factory=lambda: f"ag_{uuid4().hex[:8]}")
    nodes: List[AnomalyNode] = field(default_factory=list)
    edges: List[AnomalyEdge] = field(default_factory=list)
    domains_involved: List[str] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class TemporalDriftSegment:
    """A segment of temporal drift analysis."""
    period_start: str = ""
    period_end: str = ""
    drift_score: float = 0.0
    event_count: int = 0
    deviation_from_baseline: float = 0.0


@dataclass(frozen=True)
class TemporalDriftReport:
    """Temporal drift analysis across time windows."""
    report_id: str = field(default_factory=lambda: f"td_{uuid4().hex[:8]}")
    domain: str = ""
    segments: List[TemporalDriftSegment] = field(default_factory=list)
    overall_trend: DriftDirection = DriftDirection.UNKNOWN
    acceleration: float = 0.0
    persistence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None


@dataclass(frozen=True)
class AnomalyTimelineEntry:
    """A single entry in the anomaly reconstruction timeline."""
    sequence_index: int = 0
    event_id: str = ""
    event_type: str = ""
    domain: str = ""
    aggregate_id: str = ""
    timestamp: str = ""
    role: str = ""  # FIRST_OCCURRENCE, PROPAGATION, ROOT_CAUSE, DOWNSTREAM_EFFECT


@dataclass(frozen=True)
class AnomalyTimeline:
    """Full lifecycle reconstruction of an anomaly."""
    timeline_id: str = field(default_factory=lambda: f"at_{uuid4().hex[:8]}")
    anomaly_id: str = ""
    full_event_chain: List[AnomalyTimelineEntry] = field(default_factory=list)
    affected_domains: List[str] = field(default_factory=list)
    temporal_spread_seconds: float = 0.0
    first_occurrence: str = ""
    last_occurrence: str = ""
    event_count: int = 0
    integrity_hash: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None


@dataclass(frozen=True)
class ConsistencyDeviationReport:
    """Cross-layer consistency deviation analysis."""
    report_id: str = field(default_factory=lambda: f"cd_{uuid4().hex[:8]}")
    deviation_type: DeviationType = DeviationType.SEQUENCE_ANOMALY
    affected_entities: List[str] = field(default_factory=list)
    deviation_score: float = 0.0
    truth_layer_summary: Dict[str, Any] = field(default_factory=dict)
    observability_layer_summary: Dict[str, Any] = field(default_factory=dict)
    event_store_summary: Dict[str, Any] = field(default_factory=dict)
    projection_hash_diff: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    model_limitations: Optional[ModelLimitations] = None


@dataclass(frozen=True)
class IntelligenceSnapshot:
    """Point-in-time snapshot of intelligence state."""
    snapshot_id: str = field(default_factory=lambda: f"is_{uuid4().hex[:8]}")
    total_drift_reports: int = 0
    total_patterns_detected: int = 0
    total_anomalies_correlated: int = 0
    total_temporal_segments: int = 0
    total_consistency_deviations: int = 0
    domains_analyzed: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
