from collections import deque
from typing import Any, Dict, List, Optional
from simulation.control_center.models import (
    OperationalSignal, AggregatedState, OperationalState,
    IntelligenceSeverity, OperationalPriority, SignalType,
)


class OperationalStateAggregator:
    def __init__(self, max_signals: int = 1000):
        self._signals: deque = deque(maxlen=max_signals)
        self._signal_count: int = 0

    def ingest_signal(self, signal_id: str, signal_type: SignalType,
                      severity: IntelligenceSeverity, source_phase: str,
                      tick: int, description: str,
                      payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._signal_count += 1
        signal = OperationalSignal(
            signal_id=signal_id, signal_type=signal_type,
            severity=severity, source_phase=source_phase,
            tick=tick, description=description,
            payload=payload or {},
        )
        self._signals.append(signal)
        return {'signal_id': signal_id, 'tick': tick, 'severity': severity.value}

    def aggregate_state(self) -> AggregatedState:
        if not self._signals:
            return AggregatedState(
                state=OperationalState.NORMAL, severity_score=0.0,
                active_signals=0, critical_count=0, incident_count=0,
            )
        severity_map: Dict[str, int] = {}
        source_map: Dict[str, int] = {}
        critical_count = 0
        incident_count = 0
        for s in self._signals:
            sev = s.severity.value
            severity_map[sev] = severity_map.get(sev, 0) + 1
            src = s.source_phase
            source_map[src] = source_map.get(src, 0) + 1
            if sev == 'critical':
                critical_count += 1
            if s.signal_type == SignalType.INCIDENT:
                incident_count += 1
        severity_score = self._calculate_score(severity_map, len(self._signals))
        state = self._classify_state(severity_score, critical_count)
        priority = self._calculate_priority(severity_score, critical_count)
        return AggregatedState(
            state=state, severity_score=severity_score,
            active_signals=len(self._signals),
            critical_count=critical_count,
            incident_count=incident_count,
            source_summaries=dict(source_map),
            priority=priority,
        )

    def _calculate_score(self, severity_map: Dict[str, int],
                         total: int) -> float:
        weights = {'critical': 1.0, 'high': 0.7, 'medium': 0.4,
                   'low': 0.2, 'info': 0.0}
        weighted = sum(weights.get(k, 0) * v for k, v in severity_map.items())
        return min(1.0, weighted / max(total, 1))

    def _classify_state(self, score: float, critical_count: int) -> OperationalState:
        if critical_count > 5:
            return OperationalState.EMERGENCY
        if score >= 0.7:
            return OperationalState.CRITICAL
        if score >= 0.4:
            return OperationalState.DEGRADED
        if critical_count > 0:
            return OperationalState.DEGRADED
        return OperationalState.NORMAL

    def _calculate_priority(self, score: float,
                            critical_count: int) -> OperationalPriority:
        if critical_count > 5:
            return OperationalPriority.CRITICAL
        if score >= 0.7 or critical_count > 2:
            return OperationalPriority.HIGH
        if score >= 0.4 or critical_count > 0:
            return OperationalPriority.MEDIUM
        if score > 0:
            return OperationalPriority.LOW
        return OperationalPriority.LOWEST

    def get_signal_count(self) -> int:
        return len(self._signals)

    def clear(self):
        self._signals.clear()
        self._signal_count = 0
