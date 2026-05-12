"""Stability widgets for computing stability scores and trends.

Strictly read-only, bounded memory, exception-safe.
"""
from collections import deque
from typing import Any, Dict, List


class StabilityWidgets:
    """Widget for computing stability scores and tracking trends.
    
    Uses bounded deque for memory safety. All operations are exception-safe.
    """

    def __init__(self, max_history: int = 200):
        """Initialize the stability widgets with bounded history.
        
        Args:
            max_history: Maximum number of score entries to retain. Defaults to 200.
        """
        self._max_history = max(max_history, 5)
        self._score_history: deque = deque(maxlen=self._max_history)

    def compute_stability_score(
        self,
        severity_score: float,
        critical_count: int,
        incident_count: int,
        active_signals: int,
        cascading_risk: bool
    ) -> Dict[str, Any]:
        """Compute stability score based on input metrics.
        
        Score formula:
        - Base: 1.0 - severity_score (invert severity: 0 = best, 1 = worst)
        - Penalty: -0.1 per critical count
        - Penalty: -0.05 per incident count
        - Penalty: -0.2 if cascading_risk is True
        - Clamped to [0.0, 1.0]
        
        Args:
            severity_score: Severity score between 0.0 (best) and 1.0 (worst).
            critical_count: Number of critical signals/incidents.
            incident_count: Number of active incidents.
            active_signals: Number of active signals (informational only for breakdown).
            cascading_risk: Whether cascading failure risk exists.
            
        Returns:
            Dict with: stability_score (float 0.0-1.0), breakdown (dict of components),
            status ('stable' | 'unstable' | 'critical')
        """
        try:
            sev_score = max(0.0, min(1.0, float(severity_score)))
            crit_count = max(0, int(critical_count))
            inc_count = max(0, int(incident_count))
            act_signals = max(0, int(active_signals))
            
            base_score = 1.0 - sev_score
            critical_penalty = crit_count * 0.1
            incident_penalty = inc_count * 0.05
            cascading_penalty = 0.2 if cascading_risk else 0.0
            
            raw_score = base_score - critical_penalty - incident_penalty - cascading_penalty
            stability_score = max(0.0, min(1.0, raw_score))
            
            if stability_score >= 0.7:
                status = 'stable'
            elif stability_score >= 0.4:
                status = 'unstable'
            else:
                status = 'critical'
            
            breakdown = {
                'base_score': round(base_score, 4),
                'severity_score': round(sev_score, 4),
                'critical_count': crit_count,
                'critical_penalty': round(critical_penalty, 4),
                'incident_count': inc_count,
                'incident_penalty': round(incident_penalty, 4),
                'active_signals': act_signals,
                'cascading_risk': cascading_risk,
                'cascading_penalty': round(cascading_penalty, 4),
                'raw_score': round(raw_score, 4)
            }
            
            result = {
                'stability_score': round(stability_score, 4),
                'breakdown': breakdown,
                'status': status
            }
            
            self._score_history.append({
                'stability_score': round(stability_score, 4),
                'severity_score': round(sev_score, 4),
                'status': status
            })
            
            return result
        except Exception:
            return {
                'stability_score': 0.5,
                'breakdown': {'error': 'computation_failed'},
                'status': 'unknown'
            }

    def get_stability_trend(self) -> str:
        """Determine stability trend by comparing recent scores.
        
        Compares first vs last of the last 5 scores (or fewer if history is small).
        
        Returns:
            'improving' if scores going up, 'degrading' if going down, 'stable' otherwise.
        """
        try:
            if len(self._score_history) < 2:
                return 'stable'
            
            window_size = min(5, len(self._score_history))
            recent = list(self._score_history)[-window_size:]
            
            if len(recent) < 2:
                return 'stable'
            
            first_score = recent[0]['stability_score']
            last_score = recent[-1]['stability_score']
            
            delta = last_score - first_score
            
            if delta > 0.05:
                return 'improving'
            elif delta < -0.05:
                return 'degrading'
            else:
                return 'stable'
        except Exception:
            return 'stable'

    def clear(self) -> None:
        """Clear all stored score history."""
        try:
            self._score_history.clear()
        except Exception:
            pass
