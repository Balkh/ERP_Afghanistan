import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.dashboard.timeline')


TIMELINE_WINDOWS = [
    ('now', 0),
    ('near_future', 5),
    ('short_term', 10),
    ('medium_term', 25),
    ('long_term', 50),
]


class PredictiveTimeline:
    def __init__(self, max_entries: int = 200):
        self._max_entries = max_entries
        self._entries: deque = deque(maxlen=max_entries)

    def record(self, tick: int, event_type: str, description: str,
               risk_score: float, severity: str):
        self._entries.append({
            'tick': tick,
            'type': event_type,
            'description': description,
            'risk_score': risk_score,
            'severity': severity,
        })

    def build_timeline(self, forecast_windows: Dict[str, Any],
                       stability_score: Dict[str, Any],
                       high_risk_workflows: Dict[str, float]) -> Dict[str, Any]:
        entries = list(self._entries)
        current = entries[-10:] if entries else []
        predicted = []
        for name, offset in TIMELINE_WINDOWS:
            if name == 'now':
                continue
            horizon_entry = {
                'window': name,
                'tick_offset': offset,
                'predicted_score': max(0, stability_score.get('score', 100) - offset * 2),
                'predicted_risk_workflows': len(high_risk_workflows),
                'forecast_density': forecast_windows.get(name, 0),
            }
            predicted.append(horizon_entry)
        recent_risks = [e for e in entries if e.get('risk_score', 0) >= 40][-10:]
        return {
            'current_events': current,
            'predicted_horizons': predicted,
            'recent_high_risk_events': recent_risks,
        }

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def clear(self):
        self._entries.clear()
