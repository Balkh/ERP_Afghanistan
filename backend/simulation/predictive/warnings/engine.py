import logging
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.warnings.classifier import WarningSeverityClassifier
from simulation.predictive.warnings.retention import WarningRetentionManager
from simulation.predictive.warnings.deduplicator import WarningDeduplicator

logger = logging.getLogger('erp.simulation.predictive.warnings.engine')


class EarlyWarningEngine:
    def __init__(self):
        self._classifier = WarningSeverityClassifier()
        self._retention = WarningRetentionManager()
        self._deduplicator = WarningDeduplicator()
        self._generated_count: int = 0

    @property
    def classifier(self) -> WarningSeverityClassifier:
        return self._classifier

    @property
    def retention(self) -> WarningRetentionManager:
        return self._retention

    @property
    def deduplicator(self) -> WarningDeduplicator:
        return self._deduplicator

    def evaluate_inventory_drift_risk(self, tick: int,
                                      drift_trend: Dict[str, Any],
                                      forecast: Dict[str, Any],
                                      workflow_scores: Dict[str, float]) -> Optional[Dict[str, Any]]:
        inventory_score = workflow_scores.get('inventory', 0)
        growth = drift_trend.get('mismatch_growth_rate', 0)
        density = forecast.get('predicted_drift_density', 0)
        raw_risk = inventory_score * 0.4 + abs(growth) * 0.3 + density * 0.3
        severity = self._classifier.classify(raw_risk, raw_risk)
        return self._build_warning(tick, 'inventory_drift_escalation',
                                   'inventory', severity, raw_risk,
                                   {'growth_rate': growth, 'predicted_density': density})

    def evaluate_workflow_instability(self, tick: int,
                                      workflow_type: str,
                                      risk_score: float,
                                      degradation_prob: float,
                                      trend_direction: str) -> Optional[Dict[str, Any]]:
        raw_risk = risk_score * 0.5 + degradation_prob * 0.5
        if trend_direction == 'worsening':
            raw_risk *= 1.2
        severity = self._classifier.classify(raw_risk, raw_risk)
        return self._build_warning(tick, 'workflow_instability',
                                   workflow_type, severity, raw_risk,
                                   {'risk_score': risk_score,
                                    'degradation_prob': degradation_prob})

    def evaluate_event_propagation_saturation(
        self, tick: int, total_events: int,
        fan_out_chains: List[int],
        history_size: int
    ) -> Optional[Dict[str, Any]]:
        max_fan = max(fan_out_chains) if fan_out_chains else 0
        saturation = (total_events / max(history_size, 1)) * 100
        raw_risk = min(max_fan * 5 + saturation * 0.5, 100)
        severity = self._classifier.classify(raw_risk, raw_risk)
        return self._build_warning(tick, 'event_propagation_saturation',
                                   'events', severity, raw_risk,
                                   {'total_events': total_events,
                                    'max_fan_out': max_fan,
                                    'saturation_pct': round(saturation, 1)})

    def evaluate_causal_chain_overload(
        self, tick: int, chain_lengths: List[int],
        max_confidence_drops: List[float]
    ) -> Optional[Dict[str, Any]]:
        max_len = max(chain_lengths) if chain_lengths else 0
        avg_conf = sum(max_confidence_drops) / max(len(max_confidence_drops), 1) if max_confidence_drops else 1.0
        raw_risk = min(max_len * 8 + (1.0 - avg_conf) * 40, 100)
        severity = self._classifier.classify(raw_risk, raw_risk)
        return self._build_warning(tick, 'causal_chain_overload',
                                   'root_cause', severity, raw_risk,
                                   {'max_chain_length': max_len,
                                    'avg_confidence_drop': round(1.0 - avg_conf, 3)})

    def evaluate_reconciliation_degradation(
        self, tick: int, mismatch_count: int,
        severity_escalation: bool,
        trend_status: str
    ) -> Optional[Dict[str, Any]]:
        raw_risk = min(mismatch_count * 5 + (50 if severity_escalation else 0), 100)
        if trend_status == 'critical':
            raw_risk = min(raw_risk + 20, 100)
        severity = self._classifier.classify(raw_risk, raw_risk)
        return self._build_warning(tick, 'reconciliation_degradation',
                                   'reconciliation', severity, raw_risk,
                                   {'mismatch_count': mismatch_count,
                                    'severity_escalation': severity_escalation,
                                    'trend_status': trend_status})

    def _build_warning(self, tick: int, warning_type: str,
                       affected_module: str, severity: str,
                       raw_risk: float,
                       details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        warning = {
            'warning_id': str(uuid.uuid4()),
            'tick': tick,
            'warning_type': warning_type,
            'affected_module': affected_module,
            'severity': severity,
            'risk_score': round(raw_risk, 2),
            'details': dict(details),
            'generated': True,
        }
        if self._deduplicator.is_duplicate(warning):
            return None
        self._retention.add_warning(warning)
        self._generated_count += 1
        return warning

    @property
    def generated_count(self) -> int:
        return self._generated_count

    def clear(self):
        self._retention.clear()
        self._deduplicator.clear()
        self._generated_count = 0
