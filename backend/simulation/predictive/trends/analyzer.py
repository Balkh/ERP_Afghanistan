import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.trends.analyzer')


class DriftTrendAnalyzer:
    def __init__(self, max_history: int = 1000):
        self._max_history = max_history
        self._drift_snapshots: deque = deque(maxlen=max_history)

    def record_snapshot(self, tick: int, mismatch_count: int,
                        severity_counts: Dict[str, int],
                        affected_modules: Dict[str, int]):
        self._drift_snapshots.append({
            'tick': tick,
            'mismatch_count': mismatch_count,
            'severity_counts': dict(severity_counts),
            'affected_modules': dict(affected_modules),
        })

    def analyze_trends(self) -> Dict[str, Any]:
        snapshots = list(self._drift_snapshots)
        if len(snapshots) < 2:
            return {
                'trend_status': 'insufficient_data',
                'mismatch_growth_rate': 0.0,
                'severity_escalation': False,
                'instability_acceleration': 0.0,
                'dominant_drift_category': None,
                'stable': True,
                'worsening': False,
                'critical_escalation': False,
                'sample_size': len(snapshots),
            }
        recent = snapshots[-5:] if len(snapshots) >= 5 else snapshots
        older = snapshots[:5] if len(snapshots) >= 10 else snapshots[:-1]
        recent_avg = sum(s['mismatch_count'] for s in recent) / len(recent)
        older_avg = sum(s['mismatch_count'] for s in older) / len(older) if older else 0
        growth_rate = ((recent_avg - older_avg) / max(older_avg, 1)) * 100

        escalation = self._detect_severity_escalation(recent, older)
        acceleration = self._calc_acceleration(snapshots)
        dominant = self._find_dominant_category(recent)
        stable = abs(growth_rate) < 10 and not escalation and acceleration < 5
        worsening = growth_rate >= 10 or escalation
        critical = growth_rate >= 50 or acceleration >= 25
        return {
            'trend_status': 'critical' if critical else 'worsening' if worsening else 'stable',
            'mismatch_growth_rate': round(growth_rate, 2),
            'severity_escalation': escalation,
            'instability_acceleration': round(acceleration, 2),
            'dominant_drift_category': dominant,
            'stable': stable,
            'worsening': worsening,
            'critical_escalation': critical,
            'sample_size': len(snapshots),
        }

    def _detect_severity_escalation(self, recent: List[Dict],
                                    older: List[Dict]) -> bool:
        for sev in ('critical', 'high'):
            recent_crit = sum(s['severity_counts'].get(sev, 0) for s in recent)
            older_crit = sum(s['severity_counts'].get(sev, 0) for s in older)
            if older_crit > 0 and recent_crit > older_crit * 1.5:
                return True
        return False

    def _calc_acceleration(self, snapshots: List[Dict]) -> float:
        if len(snapshots) < 3:
            return 0.0
        mid = len(snapshots) // 2
        first_half = snapshots[:mid]
        second_half = snapshots[mid:]
        first_rate = (first_half[-1]['mismatch_count'] - first_half[0]['mismatch_count']) / max(len(first_half), 1)
        second_rate = (second_half[-1]['mismatch_count'] - second_half[0]['mismatch_count']) / max(len(second_half), 1)
        return second_rate - first_rate

    def _find_dominant_category(self, snapshots: List[Dict]) -> Optional[str]:
        categories: Dict[str, int] = {}
        for s in snapshots:
            for module, count in s['affected_modules'].items():
                categories[module] = categories.get(module, 0) + count
        if not categories:
            return None
        return max(categories, key=categories.get)

    @property
    def snapshot_count(self) -> int:
        return len(self._drift_snapshots)

    def clear(self):
        self._drift_snapshots.clear()
