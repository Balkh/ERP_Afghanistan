"""Shared models for the Operational Intelligence Control Center."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OperationalState(str, Enum):
    NORMAL = 'normal'
    DEGRADED = 'degraded'
    CRITICAL = 'critical'
    EMERGENCY = 'emergency'
    RECOVERING = 'recovering'


class IntelligenceSeverity(str, Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class SignalType(str, Enum):
    TRUTH_MISMATCH = 'truth_mismatch'
    ROOT_CAUSE = 'root_cause'
    DRIFT_TREND = 'drift_trend'
    RECOVERY_EVENT = 'recovery_event'
    REPLAY_EVENT = 'replay_event'
    PREDICTIVE_WARNING = 'predictive_warning'
    INTEGRITY_BREACH = 'integrity_breach'
    ANOMALY = 'anomaly'
    INCIDENT = 'incident'
    ESCALATION = 'escalation'


class IncidentStatus(str, Enum):
    OPEN = 'open'
    ACKNOWLEDGED = 'acknowledged'
    INVESTIGATING = 'investigating'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    REOPENED = 'reopened'


class OperationalPriority(str, Enum):
    LOWEST = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EscalationLevel(str, Enum):
    NONE = 'none'
    OBSERVE = 'observe'
    WARN = 'warn'
    ESCALATE = 'escalate'
    EMERGENCY = 'emergency'


class DashboardWidgetType(str, Enum):
    STABILITY_SCORE = 'stability_score'
    HEALTH_STATUS = 'health_status'
    INCIDENT_SUMMARY = 'incident_summary'
    DRIFT_TREND = 'drift_trend'
    RISK_HEATMAP = 'risk_heatmap'
    SYSTEM_METRICS = 'system_metrics'
    RECOVERY_READINESS = 'recovery_readiness'
    TIMELINE_PREVIEW = 'timeline_preview'


@dataclass
class OperationalSignal:
    signal_id: str
    signal_type: SignalType
    severity: IntelligenceSeverity
    source_phase: str
    tick: int
    description: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class AggregatedState:
    state: OperationalState
    severity_score: float
    active_signals: int
    critical_count: int
    incident_count: int
    source_summaries: Dict[str, Any] = field(default_factory=dict)
    priority: OperationalPriority = OperationalPriority.LOWEST


@dataclass
class UnifiedTimelineEvent:
    event_id: str
    tick: int
    source_phase: str
    event_type: str
    description: str
    severity: IntelligenceSeverity
    payload: Dict[str, Any] = field(default_factory=dict)
    related_event_ids: List[str] = field(default_factory=list)


@dataclass
class IncidentRecord:
    incident_id: str
    signal_type: SignalType
    severity: IntelligenceSeverity
    status: IncidentStatus
    tick_detected: int
    description: str
    occurrence_count: int = 1
    related_signal_ids: List[str] = field(default_factory=list)
    escalation_level: EscalationLevel = EscalationLevel.NONE
    resolved_tick: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardSnapshot:
    snapshot_id: str
    tick: int
    operational_state: str
    stability_score: float
    health_status: str
    active_incidents: int
    widget_data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass
class ExecutiveReport:
    report_id: str
    tick: int
    title: str
    operational_state: str
    stability_score: float
    summary: str
    sections: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SafetyReport:
    report_id: str
    is_safe: bool
    recursion_depth: int
    graph_size: int
    memory_pressure: float
    violations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
