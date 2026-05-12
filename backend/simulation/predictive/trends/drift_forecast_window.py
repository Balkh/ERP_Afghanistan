import logging
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.models import (
    DriftForecastPoint, DriftForecastWindow, DriftVelocity,
    TrendDirection, ForecastHorizon, PredictionConfidence,
)

logger = logging.getLogger('erp.simulation.predictive.trends.forecast')

WORKFLOW_MODULES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class DriftForecastWindowGenerator:
    def __init__(self, max_history: int = 200):
        self._max_history = max_history
        self._forecast_history: deque = deque(maxlen=max_history)

    def generate(self, drift_history: List[Dict[str, Any]],
                 velocities: List[DriftVelocity],
                 current_tick: int) -> DriftForecastWindow:
        short_term = self._generate_horizon(
            drift_history, velocities, current_tick,
            horizon_ticks=5, horizon=ForecastHorizon.SHORT_TERM,
        )
        medium_term = self._generate_horizon(
            drift_history, velocities, current_tick,
            horizon_ticks=15, horizon=ForecastHorizon.MEDIUM_TERM,
        )
        long_term = self._generate_horizon(
            drift_history, velocities, current_tick,
            horizon_ticks=30, horizon=ForecastHorizon.LONG_TERM,
        )
        overall_trend = self._determine_overall_trend(
            short_term, medium_term, long_term,
        )
        window = DriftForecastWindow(
            short_term=short_term,
            medium_term=medium_term,
            long_term=long_term,
            overall_trend=overall_trend,
        )
        self._forecast_history.append({
            'tick': current_tick,
            'window': window,
        })
        return window

    def _generate_horizon(self, drift_history: List[Dict],
                          velocities: List[DriftVelocity],
                          current_tick: int, horizon_ticks: int,
                          horizon: ForecastHorizon) -> List[DriftForecastPoint]:
        points: List[DriftForecastPoint] = []
        if not drift_history:
            return points
        avg_density = len(drift_history) / max(current_tick, 1)
        velocity_map: Dict[str, float] = {}
        for v in velocities:
            velocity_map[v.module] = v.instability_momentum
        for offset in range(1, horizon_ticks + 1):
            predicted_tick = current_tick + offset
            density = self._forecast_density(
                drift_history, avg_density, velocity_map, offset,
            )
            regions = self._forecast_escalation_regions(
                drift_history, velocity_map, offset,
            )
            confidence = self._calc_confidence(offset, horizon_ticks)
            points.append(DriftForecastPoint(
                tick=predicted_tick,
                predicted_drift_density=round(density, 4),
                probable_escalation_regions=regions,
                confidence=confidence,
                horizon=horizon,
            ))
        return points

    def _forecast_density(self, drift_history: List[Dict],
                          avg_density: float,
                          velocity_map: Dict[str, float],
                          offset: int) -> float:
        momentum_factor = 1.0
        if velocity_map:
            avg_momentum = sum(velocity_map.values()) / len(velocity_map)
            momentum_factor = 1.0 + (avg_momentum * offset * 0.1)
        decay = 0.95 ** offset
        return avg_density * momentum_factor * decay

    def _forecast_escalation_regions(self, drift_history: List[Dict],
                                     velocity_map: Dict[str, float],
                                     offset: int) -> List[str]:
        regions: List[str] = []
        for module in WORKFLOW_MODULES:
            momentum = velocity_map.get(module, 0)
            if momentum > 0.1:
                module_drifts = [d for d in drift_history
                                 if d.get('mismatch', {}).get('affected_module', '') == module]
                if len(module_drifts) >= 3 and momentum > 0.2:
                    regions.append(module)
        return regions

    def _calc_confidence(self, offset: int, horizon_ticks: int) -> PredictionConfidence:
        ratio = offset / max(horizon_ticks, 1)
        if ratio <= 0.33:
            return PredictionConfidence.HIGH
        if ratio <= 0.66:
            return PredictionConfidence.MEDIUM
        return PredictionConfidence.LOW

    def _determine_overall_trend(self, short: List[DriftForecastPoint],
                                 medium: List[DriftForecastPoint],
                                 long: List[DriftForecastPoint]) -> TrendDirection:
        all_points = short + medium + long
        if len(all_points) < 3:
            return TrendDirection.STABLE
        first_density = all_points[0].predicted_drift_density
        last_density = all_points[-1].predicted_drift_density
        diff = last_density - first_density
        if diff > 0.1:
            return TrendDirection.WORSENING
        if diff < -0.1:
            return TrendDirection.IMPROVING
        return TrendDirection.STABLE

    @property
    def record_count(self) -> int:
        return len(self._forecast_history)

    def clear(self):
        self._forecast_history.clear()
