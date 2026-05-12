from collections import deque
from typing import Any, Dict, List, Optional


class SystemHealthMatrix:
    def __init__(self, max_history: int = 500):
        self._health_history: deque = deque(maxlen=max_history)

    def compute_health(self, severity_score: float, critical_count: int,
                       incident_count: int, active_signals: int,
                       source_summaries: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        source_summaries = source_summaries or {}
        if severity_score == 0 and critical_count == 0 and incident_count == 0:
            status = 'healthy'
        elif severity_score >= 0.7 or critical_count > 5:
            status = 'critical'
        elif severity_score >= 0.4 or critical_count > 2:
            status = 'degraded'
        elif critical_count > 0 or incident_count > 0:
            status = 'warning'
        else:
            status = 'healthy'
        health_score = max(0.0, 1.0 - severity_score)
        self._health_history.append({
            'status': status, 'health_score': health_score,
            'severity_score': severity_score, 'critical_count': critical_count,
        })
        return {
            'status': status, 'health_score': health_score,
            'active_signals': active_signals,
            'critical_signals': critical_count,
            'active_incidents': incident_count,
            'sources_monitored': len(source_summaries),
        }

    def get_health_trend(self) -> str:
        if len(self._health_history) < 2:
            return 'stable'
        recent = list(self._health_history)[-5:]
        scores = [r['health_score'] for r in recent]
        if len(scores) < 2:
            return 'stable'
        if scores[-1] < scores[0] - 0.2:
            return 'degrading'
        if scores[-1] > scores[0] + 0.2:
            return 'improving'
        return 'stable'

    def clear(self):
        self._health_history.clear()
