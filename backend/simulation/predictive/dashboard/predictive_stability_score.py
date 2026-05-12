import logging
from typing import Any, Dict, List, Optional

from simulation.predictive.models import (
    DriftTrendResult, FailureProbability, EarlyWarning,
    TrendDirection, WarningSeverity,
)

logger = logging.getLogger('erp.simulation.predictive.dashboard.stability')


class PredictiveStabilityScore:
    def calculate(self, trends: List[DriftTrendResult],
                  probability: FailureProbability,
                  warnings: List[EarlyWarning],
                  workflow_scores: Dict[str, float]) -> float:
        trend_score = self._score_trends(trends)
        probability_score = self._score_probability(probability)
        warning_score = self._score_warnings(warnings)
        workflow_score = self._score_workflows(workflow_scores)
        weights = {'trends': 0.25, 'probability': 0.30, 'warnings': 0.20, 'workflows': 0.25}
        raw = (trend_score * weights['trends']
               + probability_score * weights['probability']
               + warning_score * weights['warnings']
               + workflow_score * weights['workflows'])
        return round(min(max(raw, 0.0), 100.0), 2)

    def _score_trends(self, trends: List[DriftTrendResult]) -> float:
        if not trends:
            return 100.0
        penalty = 0.0
        for t in trends:
            if t.direction == TrendDirection.CRITICAL:
                penalty += 25
            elif t.direction == TrendDirection.WORSENING:
                penalty += 15
            elif t.direction == TrendDirection.IMPROVING:
                penalty -= 5
        return min(max(100.0 - penalty, 0.0), 100.0)

    def _score_probability(self, probability: FailureProbability) -> float:
        return 100.0 - probability.overall_risk_score

    def _score_warnings(self, warnings: List[EarlyWarning]) -> float:
        if not warnings:
            return 100.0
        penalty = 0.0
        for w in warnings:
            if w.severity == WarningSeverity.CRITICAL:
                penalty += 20
            elif w.severity == WarningSeverity.HIGH:
                penalty += 10
            elif w.severity == WarningSeverity.MEDIUM:
                penalty += 5
        return min(max(100.0 - penalty, 0.0), 100.0)

    def _score_workflows(self, workflow_scores: Dict[str, float]) -> float:
        if not workflow_scores:
            return 100.0
        avg = sum(workflow_scores.values()) / len(workflow_scores)
        return 100.0 - avg
