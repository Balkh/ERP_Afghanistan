"""Health summary generator for dashboard health status.

Strictly read-only, bounded memory, exception-safe.
"""
from collections import deque
from typing import Any, Dict, List


class HealthSummary:
    """Generator for health summary data with bounded history.
    
    Uses bounded deque for memory safety. All operations are exception-safe.
    """

    STATUS_ICONS = {
        'healthy': 'check',
        'degraded': 'warning',
        'critical': 'error',
        'unknown': 'question'
    }

    def __init__(self, max_summaries: int = 100):
        """Initialize the health summary with bounded history.
        
        Args:
            max_summaries: Maximum number of summaries to retain. Defaults to 100.
        """
        self._max_summaries = max(max_summaries, 1)
        self._summary_history: deque = deque(maxlen=self._max_summaries)

    def generate_summary(
        self,
        health_status: str,
        health_score: float,
        operational_state: str,
        active_signals: int,
        active_incidents: int,
        sources_monitored: int
    ) -> Dict[str, Any]:
        """Generate a health summary with text and structured data.
        
        Args:
            health_status: Raw health status string.
            health_score: Health score between 0.0 (worst) and 1.0 (best).
            operational_state: Current operational state.
            active_signals: Number of active signals.
            active_incidents: Number of active incidents.
            sources_monitored: Number of sources being monitored.
            
        Returns:
            Dict with: summary_text, health_label, status_icon, metrics dict.
        """
        try:
            score = max(0.0, min(1.0, float(health_score)))
            signals = max(0, int(active_signals))
            incidents = max(0, int(active_incidents))
            sources = max(0, int(sources_monitored))
            
            health_lower = str(health_status).lower() if health_status else 'unknown'
            op_lower = str(operational_state).lower() if operational_state else 'unknown'
            
            if 'critical' in health_lower or 'emergency' in op_lower:
                health_label = 'critical'
                status_icon = self.STATUS_ICONS['critical']
            elif 'degraded' in health_lower or 'degraded' in op_lower:
                health_label = 'degraded'
                status_icon = self.STATUS_ICONS['degraded']
            elif score >= 0.7:
                health_label = 'healthy'
                status_icon = self.STATUS_ICONS['healthy']
            elif score >= 0.4:
                health_label = 'degraded'
                status_icon = self.STATUS_ICONS['degraded']
            else:
                health_label = 'critical'
                status_icon = self.STATUS_ICONS['critical']
            
            if health_label == 'healthy':
                if incidents == 0 and signals == 0:
                    summary_text = f"System healthy. All {sources} sources monitored. No active incidents."
                elif signals > 0:
                    summary_text = f"System healthy. {sources} sources monitored. {signals} active signals, {incidents} incidents."
                else:
                    summary_text = f"System healthy. Monitoring {sources} sources."
            elif health_label == 'degraded':
                summary_text = f"System degraded. {signals} active signals, {incidents} active incidents across {sources} sources."
            else:
                summary_text = f"System critical. {incidents} active incidents, {signals} signals requiring attention."
            
            metrics = {
                'health_score': round(score, 4),
                'health_score_percent': round(score * 100, 1),
                'active_signals': signals,
                'active_incidents': incidents,
                'sources_monitored': sources,
                'operational_state': operational_state,
                'signals_per_source': round(signals / sources, 2) if sources > 0 else 0.0
            }
            
            result = {
                'summary_text': summary_text,
                'health_label': health_label,
                'status_icon': status_icon,
                'metrics': metrics
            }
            
            self._summary_history.append(result.copy())
            
            return result
        except Exception:
            return {
                'summary_text': "Health status unavailable.",
                'health_label': 'unknown',
                'status_icon': self.STATUS_ICONS['unknown'],
                'metrics': {'error': 'generation_failed'}
            }

    def get_summary_history(self) -> List[Dict[str, Any]]:
        """Get all stored summary history as a list.
        
        Returns:
            List of summary dicts, oldest first.
        """
        try:
            return list(self._summary_history)
        except Exception:
            return []

    def clear(self) -> None:
        """Clear all stored summary history."""
        try:
            self._summary_history.clear()
        except Exception:
            pass
