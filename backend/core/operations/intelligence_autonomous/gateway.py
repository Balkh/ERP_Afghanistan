"""
Phase 5B.8 — Autonomous Intelligence Gateway.

Unified read-only orchestrator combining all engines.
Provides:
- /insights — domain-specific and cross-domain intelligence
- /risk-summary — cross-domain risk scoring
- /decision-options — structured decision alternatives
- /forecast — deterministic predictions
- /anomaly-warning — early warning signals
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    IntelligenceReport, Insight, Recommendation, RiskScore,
    Forecast, AnomalyWarning, StructuredDecision,
)
from core.operations.intelligence_autonomous.reasoning_engine import ReasoningEngine
from core.operations.intelligence_autonomous.prediction_engine import PredictionEngine
from core.operations.intelligence_autonomous.decision_suggester import DecisionSuggester
from core.operations.intelligence_autonomous.anomaly_foresight import AnomalyForesightEngine
from core.operations.intelligence_autonomous.risk_engine import RiskEngine

logger = logging.getLogger('erp.autonomous.gateway')

AUTO_GATEWAY_VERSION = "1.0.0"


class AutonomousIntelligenceGateway:
    """Unified read-only gateway for all autonomous intelligence.

    All outputs are:
    - NON-EXECUTABLE
    - Traceable to Event Store
    - Deterministic
    - Read-only
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._reasoning = ReasoningEngine(store)
        self._prediction = PredictionEngine(store)
        self._suggester = DecisionSuggester(store)
        self._foresight = AnomalyForesightEngine(store)
        self._risk = RiskEngine(store)

    def get_full_report(self, domain_scope: str = "enterprise") -> IntelligenceReport:
        """Get a complete intelligence report combining all engines."""
        insights: List[Insight] = []
        recommendations: List[Recommendation] = []
        risk_scores: List[RiskScore] = []
        forecasts: List[Forecast] = []
        anomaly_warnings: List[AnomalyWarning] = []

        if domain_scope == "enterprise" or domain_scope == "all":
            for d in Domain:
                insights.extend(self._reasoning.analyze_domain(d))
            insights.extend(self._reasoning.cross_domain_inference())
            recommendations = self._suggester.generate_recommendations()
            risk_scores = self._risk.score_all()
            forecasts = self._prediction.forecast_all()
            anomaly_warnings = self._foresight.predict_all()
        else:
            try:
                d = Domain(domain_scope)
                insights = self._reasoning.analyze_domain(d)
                recommendations = self._reasoning.generate_recommendations(d)
            except (ValueError, KeyError):
                pass

        overall_risk = self._risk.get_overall_risk()
        overall_confidence = self._compute_confidence(risk_scores)

        supporting_events = list(set(
            eid for ins in insights for eid in ins.supporting_event_ids
        ))

        h = hashlib.sha256()
        h.update(str(len(insights)).encode())
        h.update(str(overall_risk).encode())
        projection_hash = h.hexdigest()

        return IntelligenceReport(
            domain_scope=domain_scope,
            risk_score_overall=overall_risk,
            confidence_score_overall=overall_confidence,
            insights=insights,
            recommendations=recommendations,
            risk_scores=risk_scores,
            forecasts=forecasts,
            anomaly_warnings=anomaly_warnings,
            supporting_events=supporting_events,
            projection_hash=projection_hash,
        )

    def get_insights(self, domain: str = "") -> List[Insight]:
        """Get domain-specific or cross-domain insights."""
        if domain:
            try:
                return self._reasoning.analyze_domain(Domain(domain))
            except (ValueError, KeyError):
                return []
        insights = []
        for d in Domain:
            insights.extend(self._reasoning.analyze_domain(d))
        insights.extend(self._reasoning.cross_domain_inference())
        return insights

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get cross-domain risk summary."""
        scores = self._risk.score_all()
        return {
            "overall_risk": self._risk.get_overall_risk(),
            "scores": [{
                "category": s.category.value,
                "score": s.score,
                "confidence": s.confidence,
                "trend": s.trend,
            } for s in scores],
        }

    def get_decision_options(self) -> List[StructuredDecision]:
        """Get structured decision options."""
        decisions: List[StructuredDecision] = []
        try:
            decisions.append(self._suggester.suggest_inventory_restock())
        except Exception:
            pass
        try:
            decisions.append(self._suggester.suggest_financial_action())
        except Exception:
            pass
        return decisions

    def get_forecasts(self) -> List[Forecast]:
        """Get all deterministic forecasts."""
        return self._prediction.forecast_all()

    def get_anomaly_warnings(self) -> List[AnomalyWarning]:
        """Get predicted anomaly warnings."""
        return self._foresight.predict_all()

    def get_recommendations(self) -> List[Recommendation]:
        """Get all non-executable recommendations."""
        return self._suggester.generate_recommendations()

    def get_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        return {
            "gateway_version": AUTO_GATEWAY_VERSION,
            "engine_status": "read_only",
            "engines": ["reasoning", "prediction", "suggester", "foresight", "risk"],
            "event_count": self._store.count(),
        }

    def _compute_confidence(self, scores: List[RiskScore]) -> float:
        if not scores:
            return 0.0
        return round(sum(s.confidence for s in scores) / len(scores), 2)

    def reset(self):
        from core.operations.truth.event_store import reset_event_store
        reset_event_store()
        self._store = get_event_store()
        self._reasoning = ReasoningEngine(self._store)
        self._prediction = PredictionEngine(self._store)
        self._suggester = DecisionSuggester(self._store)
        self._foresight = AnomalyForesightEngine(self._store)
        self._risk = RiskEngine(self._store)
