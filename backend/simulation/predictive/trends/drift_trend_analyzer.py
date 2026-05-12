import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set

from simulation.predictive.models import (
    DriftTrendResult, TrendDirection, EscalationLevel,
)

logger = logging.getLogger('erp.simulation.predictive.trends.analyzer')

WORKFLOW_MODULES = ['sales', 'purchase', 'inventory', 'return', 'hr']
SEVERITY_ORDER = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}


class DriftTrendAnalyzer:
    def __init__(self, max_history: int = 1000):
        self._max_history = max_history
        self._trend_history: deque = deque(maxlen=max_history)
        self._module_history: Dict[str, deque] = {}

    def analyze(self, drift_history: List[Dict[str, Any]],
                current_tick: int) -> List[DriftTrendResult]:
        results: List[DriftTrendResult] = []
        for module in WORKFLOW_MODULES:
            module_drifts = [d for d in drift_history
                             if d.get('mismatch', {}).get('affected_module', '') == module]
            result = self._analyze_module(module, module_drifts, current_tick)
            if result:
                results.append(result)
            self._record_trend(module, result)
        return results

    def _analyze_module(self, module: str,
                        drifts: List[Dict[str, Any]],
                        current_tick: int) -> Optional[DriftTrendResult]:
        if not drifts:
            return None
        count = len(drifts)
        categories = self._extract_categories(drifts)
        escalation = self._measure_escalation(drifts)
        acceleration = self._compute_acceleration(drifts)
        cluster_count = self._cluster_drifts(drifts)
        direction = self._determine_direction(drifts, acceleration)
        return DriftTrendResult(
            module=module,
            direction=direction,
            severity_escalation=escalation,
            mismatch_count=count,
            recurring_categories=list(categories),
            instability_acceleration=round(acceleration, 4),
            drift_cluster_count=cluster_count,
            details={
                'total_drifts': count,
                'recent_drifts': len([d for d in drifts
                                      if d.get('tick', 0) >= current_tick - 10]),
                'severity_distribution': self._severity_distribution(drifts),
            },
        )

    def _extract_categories(self, drifts: List[Dict[str, Any]]) -> Set[str]:
        categories: Set[str] = set()
        for d in drifts:
            mm = d.get('mismatch', {})
            mtype = mm.get('mismatch_type', '')
            if mtype:
                categories.add(str(mtype))
        return categories

    def _measure_escalation(self, drifts: List[Dict[str, Any]]) -> EscalationLevel:
        recent = drifts[-20:] if len(drifts) >= 20 else drifts
        severities = [d.get('mismatch', {}).get('severity', 'info') for d in recent]
        if not severities:
            return EscalationLevel.NONE
        max_sev = max(SEVERITY_ORDER.get(s, 0) for s in severities)
        if max_sev >= 4:
            return EscalationLevel.CRITICAL
        if max_sev >= 3:
            return EscalationLevel.HIGH
        if max_sev >= 2:
            return EscalationLevel.MEDIUM
        if max_sev >= 1:
            return EscalationLevel.LOW
        return EscalationLevel.NONE

    def _compute_acceleration(self, drifts: List[Dict[str, Any]]) -> float:
        if len(drifts) < 4:
            return 0.0
        half = len(drifts) // 2
        first_half = drifts[:half]
        second_half = drifts[half:]
        first_rate = len(first_half) / max(len(first_half), 1)
        second_rate = len(second_half) / max(len(second_half), 1)
        if first_rate == 0:
            return 0.0
        return (second_rate - first_rate) / first_rate

    def _cluster_drifts(self, drifts: List[Dict[str, Any]]) -> int:
        if len(drifts) < 3:
            return 1
        clusters = 1
        gap_threshold = 5
        for i in range(1, len(drifts)):
            prev_tick = drifts[i - 1].get('tick', 0)
            curr_tick = drifts[i].get('tick', 0)
            if curr_tick - prev_tick > gap_threshold:
                clusters += 1
        return clusters

    def _determine_direction(self, drifts: List[Dict[str, Any]],
                             acceleration: float) -> TrendDirection:
        if len(drifts) < 3:
            return TrendDirection.STABLE
        recent = drifts[-3:]
        severities = [SEVERITY_ORDER.get(
            d.get('mismatch', {}).get('severity', 'info'), 0) for d in recent]
        if all(s >= 3 for s in severities):
            return TrendDirection.CRITICAL
        if acceleration > 0.3:
            return TrendDirection.WORSENING
        if acceleration < -0.3:
            return TrendDirection.IMPROVING
        return TrendDirection.STABLE

    def _severity_distribution(self, drifts: List[Dict]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for d in drifts:
            sev = d.get('mismatch', {}).get('severity', 'info')
            dist[sev] = dist.get(sev, 0) + 1
        return dist

    def _record_trend(self, module: str, result: Optional[DriftTrendResult]):
        entry = {
            'module': module,
            'result': result.to_dict() if result else None,
        }
        self._trend_history.append(entry)
        if module not in self._module_history:
            self._module_history[module] = deque(maxlen=100)
        self._module_history[module].append(result)

    @property
    def trend_count(self) -> int:
        return len(self._trend_history)

    def clear(self):
        self._trend_history.clear()
        self._module_history.clear()
