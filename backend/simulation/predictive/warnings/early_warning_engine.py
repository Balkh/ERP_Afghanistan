import logging
from collections import deque
from typing import Any, Dict, List, Optional
from uuid import uuid4

from simulation.predictive.models import (
    EarlyWarning, WarningSeverity, PredictionConfidence,
    FailureProbability, DriftTrendResult, DriftVelocity,
    DriftForecastWindow, TrendDirection, EscalationLevel,
)
from simulation.predictive.warnings.warning_severity_classifier import WarningSeverityClassifier
from simulation.predictive.warnings.warning_retention_manager import WarningRetentionManager
from simulation.predictive.warnings.warning_deduplicator import WarningDeduplicator

logger = logging.getLogger('erp.simulation.predictive.warnings.engine')

WORKFLOW_MODULES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class EarlyWarningEngine:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._warning_history: deque = deque(maxlen=max_history)
        self._severity_classifier = WarningSeverityClassifier()
        self._retention_manager = WarningRetentionManager(max_warnings=500)
        self._deduplicator = WarningDeduplicator(max_history=500)

    def generate_warnings(self, drift_history: List[Dict[str, Any]],
                          trends: List[DriftTrendResult],
                          velocities: List[DriftVelocity],
                          forecast: DriftForecastWindow,
                          probability: FailureProbability,
                          root_cause_data: List[Dict[str, Any]],
                          current_tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        warnings.extend(self._check_inventory_drift_escalation(
            trends, velocities, current_tick))
        warnings.extend(self._check_workflow_instability_amplification(
            trends, probability, current_tick))
        warnings.extend(self._check_event_propagation_saturation(
            drift_history, current_tick))
        warnings.extend(self._check_causal_chain_overload(
            root_cause_data, current_tick))
        warnings.extend(self._check_reconciliation_degradation_trend(
            trends, forecast, current_tick))
        warnings.extend(self._check_critical_probability(
            probability, current_tick))
        warnings.extend(self._check_forecast_escalation(
            forecast, current_tick))
        deduplicated = self._deduplicator.deduplicate(warnings)
        retained = self._retention_manager.retain(deduplicated)
        for w in retained:
            w.tick = current_tick
            self._warning_history.append(w)
        return retained

    def _check_inventory_drift_escalation(self, trends: List[DriftTrendResult],
                                          velocities: List[DriftVelocity],
                                          tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        for trend in trends:
            if trend.module == 'inventory' and trend.direction in (
                    TrendDirection.WORSENING, TrendDirection.CRITICAL):
                severity = (WarningSeverity.CRITICAL
                            if trend.direction == TrendDirection.CRITICAL
                            else WarningSeverity.HIGH)
                warnings.append(EarlyWarning(
                    warning_id=str(uuid4()),
                    title='Inventory Drift Escalation Risk',
                    description=f'Inventory module shows {trend.direction.value} drift trend with {trend.mismatch_count} mismatches',
                    severity=severity,
                    source_module='inventory',
                    predicted_impact='Potential inventory inconsistency escalation',
                    confidence=PredictionConfidence.HIGH,
                    related_patterns=['repeated_inventory_drift'],
                    tick=tick,
                ))
        return warnings

    def _check_workflow_instability_amplification(
            self, trends: List[DriftTrendResult],
            probability: FailureProbability,
            tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        high_risk_modules = [
            t for t in trends
            if t.direction in (TrendDirection.WORSENING, TrendDirection.CRITICAL)
        ]
        if len(high_risk_modules) >= 3:
            modules = [t.module for t in high_risk_modules]
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Workflow Instability Amplification',
                description=f'{len(high_risk_modules)} modules showing worsening trends: {", ".join(modules)}',
                severity=WarningSeverity.HIGH,
                source_module='workflow',
                predicted_impact='Cross-workflow degradation propagation likely',
                confidence=PredictionConfidence.MEDIUM,
                related_patterns=['partial_workflow_execution'],
                tick=tick,
            ))
        return warnings

    def _check_event_propagation_saturation(self, drift_history: List[Dict],
                                            tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        if len(drift_history) < 10:
            return warnings
        recent = [d for d in drift_history
                  if d.get('tick', 0) >= tick - 10]
        if len(recent) >= len(drift_history) * 0.5:
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Event Propagation Saturation Risk',
                description=f'{len(recent)} recent events out of {len(drift_history)} total indicate saturation',
                severity=WarningSeverity.MEDIUM,
                source_module='events',
                predicted_impact='Event bus may be approaching capacity',
                confidence=PredictionConfidence.MEDIUM,
                tick=tick,
            ))
        return warnings

    def _check_causal_chain_overload(self, root_cause_data: List[Dict],
                                     tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        if len(root_cause_data) < 5:
            return warnings
        long_chains = [c for c in root_cause_data
                       if len(c.get('links', [])) >= 3]
        if len(long_chains) >= 3:
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Causal Chain Overload Risk',
                description=f'{len(long_chains)} causal chains with 3+ links indicate complex failure paths',
                severity=WarningSeverity.MEDIUM,
                source_module='root_cause',
                predicted_impact='Root cause analysis complexity increasing',
                confidence=PredictionConfidence.MEDIUM,
                tick=tick,
            ))
        return warnings

    def _check_reconciliation_degradation_trend(
            self, trends: List[DriftTrendResult],
            forecast: DriftForecastWindow,
            tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        financial_trend = [t for t in trends if t.module == 'sales' or t.module == 'purchase']
        worsening = [t for t in financial_trend
                     if t.direction in (TrendDirection.WORSENING, TrendDirection.CRITICAL)]
        if worsening and forecast.overall_trend in (
                TrendDirection.WORSENING, TrendDirection.CRITICAL):
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Reconciliation Degradation Trend',
                description='Financial modules show worsening drift with negative forecast',
                severity=WarningSeverity.HIGH,
                source_module='reconciliation',
                predicted_impact='Financial reconciliation may drift out of alignment',
                confidence=PredictionConfidence.MEDIUM,
                related_patterns=['journal_imbalance_concurrency'],
                tick=tick,
            ))
        return warnings

    def _check_critical_probability(self, probability: FailureProbability,
                                    tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        if probability.overall_risk_score >= 75:
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Critical Overall Risk Probability',
                description=f'Overall risk score {probability.overall_risk_score:.1f} exceeds critical threshold',
                severity=WarningSeverity.CRITICAL,
                source_module='probability',
                predicted_impact='Multiple risk factors at critical levels',
                confidence=PredictionConfidence.HIGH,
                tick=tick,
            ))
        return warnings

    def _check_forecast_escalation(self, forecast: DriftForecastWindow,
                                   tick: int) -> List[EarlyWarning]:
        warnings: List[EarlyWarning] = []
        if forecast.overall_trend == TrendDirection.CRITICAL:
            warnings.append(EarlyWarning(
                warning_id=str(uuid4()),
                title='Forecast Escalation Warning',
                description='All forecast horizons show critical drift trajectory',
                severity=WarningSeverity.CRITICAL,
                source_module='forecast',
                predicted_impact='System integrity at high risk across all timeframes',
                confidence=PredictionConfidence.MEDIUM,
                tick=tick,
            ))
        return warnings

    @property
    def warning_count(self) -> int:
        return len(self._warning_history)

    @property
    def active_warnings(self) -> List[EarlyWarning]:
        return self._retention_manager.get_active_warnings()

    def clear(self):
        self._warning_history.clear()
        self._retention_manager.clear()
        self._deduplicator.clear()
