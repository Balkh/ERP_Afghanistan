import logging
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.models import (
    PredictiveTimeline, PredictiveTimelineEvent,
    EarlyWarning, DriftForecastWindow, FailureProbability,
    WarningSeverity, PredictionConfidence,
)

logger = logging.getLogger('erp.simulation.predictive.dashboard.timeline')


class PredictiveTimelineGenerator:
    def __init__(self, max_events: int = 200):
        self._max_events = max_events
        self._timeline_history: deque = deque(maxlen=max_events)

    def generate(self, warnings: List[EarlyWarning],
                 forecast: DriftForecastWindow,
                 probability: FailureProbability,
                 current_tick: int,
                 horizon_ticks: int = 30) -> PredictiveTimeline:
        events: List[PredictiveTimelineEvent] = []
        for w in warnings:
            events.append(PredictiveTimelineEvent(
                tick=current_tick,
                event_type='warning',
                description=w.title,
                severity=w.severity,
                probability=self._warning_to_probability(w),
            ))
        for point in forecast.short_term:
            if point.predicted_drift_density > 0.1:
                events.append(PredictiveTimelineEvent(
                    tick=point.tick,
                    event_type='forecast_drift',
                    description=f'Predicted drift density: {point.predicted_drift_density:.3f}',
                    severity=WarningSeverity.INFO,
                    probability={'high': 0.8, 'medium': 0.5, 'low': 0.3}.get(
                        point.confidence.value, 0.5),
                ))
        if probability.overall_risk_score >= 50:
            events.append(PredictiveTimelineEvent(
                tick=current_tick + 5,
                event_type='risk_milestone',
                description=f'Risk score projected at {probability.overall_risk_score:.1f}',
                severity=WarningSeverity.MEDIUM,
                probability=0.6,
            ))
        events.sort(key=lambda e: e.tick)
        events = events[:self._max_events]
        timeline = PredictiveTimeline(
            events=events,
            total_events=len(events),
            critical_events=sum(1 for e in events
                                if e.severity in (WarningSeverity.HIGH, WarningSeverity.CRITICAL)),
            horizon_ticks=horizon_ticks,
        )
        self._timeline_history.append({
            'tick': current_tick,
            'timeline': timeline,
        })
        return timeline

    def _warning_to_probability(self, warning: EarlyWarning) -> float:
        mapping = {
            WarningSeverity.CRITICAL: 0.9,
            WarningSeverity.HIGH: 0.7,
            WarningSeverity.MEDIUM: 0.5,
            WarningSeverity.LOW: 0.3,
            WarningSeverity.INFO: 0.1,
        }
        return mapping.get(warning.severity, 0.5)

    @property
    def record_count(self) -> int:
        return len(self._timeline_history)

    def clear(self):
        self._timeline_history.clear()
