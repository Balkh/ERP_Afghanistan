"""
Phase 5B.8 — Autonomous Intelligence Data Models.

All outputs are:
- Structured (IntelligenceReport)
- Non-executable (recommendations, not actions)
- Traceable to Event Store events
- Read-only by design
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum


AUTO_INTELLIGENCE_MODELS_VERSION = "1.0.0"


class RiskCategory(str, Enum):
    FINANCIAL = "FINANCIAL"
    OPERATIONAL = "OPERATIONAL"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    HR = "HR"
    COMPLIANCE = "COMPLIANCE"
    INVENTORY = "INVENTORY"


class InsightSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ForecastDirection(str, Enum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    CYCLICAL = "CYCLICAL"


@dataclass(frozen=True)
class Recommendation:
    """A structured, non-executable decision suggestion."""
    recommendation_id: str = field(default_factory=lambda: f"rec_{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    decision_type: str = ""
    risk_level: str = "MEDIUM"
    options: List[Dict[str, Any]] = field(default_factory=list)
    supporting_event_ids: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    projected_impact: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Insight:
    """A single structured insight with traceable provenance."""
    insight_id: str = field(default_factory=lambda: f"ins_{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    domain: str = ""
    severity: InsightSeverity = InsightSeverity.INFO
    supporting_event_ids: List[str] = field(default_factory=list)
    supporting_projection: Dict[str, Any] = field(default_factory=dict)
    causation_link: str = ""


@dataclass(frozen=True)
class RiskScore:
    """Cross-domain risk score (0–100)."""
    category: RiskCategory = RiskCategory.OPERATIONAL
    score: float = 0.0
    confidence: float = 0.0
    contributing_factors: List[str] = field(default_factory=list)
    trend: str = "STABLE"


@dataclass(frozen=True)
class Forecast:
    """Deterministic forecast output."""
    forecast_id: str = field(default_factory=lambda: f"fc_{uuid4().hex[:8]}")
    domain: str = ""
    metric: str = ""
    current_value: float = 0.0
    predicted_value: float = 0.0
    confidence_interval_low: float = 0.0
    confidence_interval_high: float = 0.0
    direction: ForecastDirection = ForecastDirection.STABLE
    supporting_event_count: int = 0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass(frozen=True)
class AnomalyWarning:
    """Early warning signal for a predicted anomaly."""
    warning_id: str = field(default_factory=lambda: f"aw_{uuid4().hex[:8]}")
    domain: str = ""
    signal_type: str = ""
    severity: InsightSeverity = InsightSeverity.INFO
    description: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    deviation_pct: float = 0.0
    supporting_event_ids: List[str] = field(default_factory=list)
    estimated_occurrence: str = ""
    confidence_score: float = 0.0


@dataclass(frozen=True)
class IntelligenceReport:
    """Complete intelligence output — the single output format.

    All intelligence outputs are wrapped in this structure.
    NEVER contains executable actions.
    """
    report_id: str = field(default_factory=lambda: f"air_{uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    domain_scope: str = "enterprise"
    risk_score_overall: float = 0.0
    confidence_score_overall: float = 0.0
    insights: List[Insight] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    risk_scores: List[RiskScore] = field(default_factory=list)
    forecasts: List[Forecast] = field(default_factory=list)
    anomaly_warnings: List[AnomalyWarning] = field(default_factory=list)
    supporting_events: List[str] = field(default_factory=list)
    causation_links: List[Dict[str, str]] = field(default_factory=list)
    projection_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionOption:
    """A single decision option (non-executable)."""
    option_id: str = field(default_factory=lambda: f"opt_{uuid4().hex[:8]}")
    action_summary: str = ""
    projected_impact: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "MEDIUM"
    confidence: float = 0.0
    prerequisites: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StructuredDecision:
    """A structured decision with alternatives (non-executable)."""
    decision_id: str = field(default_factory=lambda: f"dec_{uuid4().hex[:8]}")
    decision_type: str = ""
    domain: str = ""
    context_summary: str = ""
    options: List[DecisionOption] = field(default_factory=list)
    recommended_option_id: str = ""
    supporting_analysis: Dict[str, Any] = field(default_factory=dict)
    report_id: str = ""
