from typing import Any, Dict, List, Optional
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class TrendDirection(str, Enum):
    STABLE = 'stable'
    WORSENING = 'worsening'
    IMPROVING = 'improving'
    CRITICAL = 'critical'


class EscalationLevel(str, Enum):
    NONE = 'none'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class WarningSeverity(str, Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ForecastHorizon(str, Enum):
    SHORT_TERM = 'short_term'
    MEDIUM_TERM = 'medium_term'
    LONG_TERM = 'long_term'


class PredictionConfidence(str, Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


@dataclass
class DriftTrendResult:
    module: str
    direction: TrendDirection
    severity_escalation: EscalationLevel
    mismatch_count: int
    recurring_categories: List[str]
    instability_acceleration: float
    drift_cluster_count: int
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'module': self.module,
            'direction': self.direction.value if isinstance(self.direction, TrendDirection) else self.direction,
            'severity_escalation': self.severity_escalation.value if isinstance(self.severity_escalation, EscalationLevel) else self.severity_escalation,
            'mismatch_count': self.mismatch_count,
            'recurring_categories': list(self.recurring_categories),
            'instability_acceleration': self.instability_acceleration,
            'drift_cluster_count': self.drift_cluster_count,
            'details': dict(self.details),
        }


@dataclass
class DriftVelocity:
    module: str
    acceleration: float
    recurrence_velocity: float
    instability_momentum: float
    escalation_speed: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftForecastPoint:
    tick: int
    predicted_drift_density: float
    probable_escalation_regions: List[str]
    confidence: PredictionConfidence
    horizon: ForecastHorizon


@dataclass
class DriftForecastWindow:
    short_term: List[DriftForecastPoint]
    medium_term: List[DriftForecastPoint]
    long_term: List[DriftForecastPoint]
    overall_trend: TrendDirection


@dataclass
class FailureProbability:
    mismatch_probability: float
    workflow_failure_probability: float
    propagation_instability_probability: float
    causal_chain_failure_probability: float
    overall_risk_score: float
    components: Dict[str, float] = field(default_factory=dict)
    explanation: List[str] = field(default_factory=list)


@dataclass
class EarlyWarning:
    warning_id: str
    title: str
    description: str
    severity: WarningSeverity
    source_module: str
    predicted_impact: str
    confidence: PredictionConfidence
    related_patterns: List[str] = field(default_factory=list)
    related_root_causes: List[str] = field(default_factory=list)
    tick: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictiveHealthReport:
    top_risks: List[Dict[str, Any]]
    workflow_instability_ranking: List[Dict[str, Any]]
    escalation_indicators: List[Dict[str, Any]]
    forecasted_drift_density: Dict[str, Any]
    operational_pressure_indicators: List[Dict[str, Any]]
    confidence_summary: Dict[str, Any]
    stability_score: float
    overall_status: str


@dataclass
class PredictiveTimelineEvent:
    tick: int
    event_type: str
    description: str
    severity: WarningSeverity
    probability: float


@dataclass
class PredictiveTimeline:
    events: List[PredictiveTimelineEvent]
    total_events: int
    critical_events: int
    horizon_ticks: int
