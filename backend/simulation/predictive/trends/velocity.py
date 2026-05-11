import logging
from collections import deque
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.predictive.trends.velocity')


class DriftVelocityTracker:
    def __init__(self, max_window: int = 100):
        self._max_window = max_window
        self._velocity_samples: deque = deque(maxlen=max_window)

    def record_tick(self, tick: int, mismatch_count: int):
        self._velocity_samples.append({
            'tick': tick,
            'mismatch_count': mismatch_count,
        })

    def compute_velocity(self) -> Dict[str, Any]:
        samples = list(self._velocity_samples)
        if len(samples) < 2:
            return {
                'drift_acceleration': 0.0,
                'recurrence_velocity': 0.0,
                'instability_momentum': 0.0,
                'escalation_speed': 0.0,
                'sample_size': len(samples),
            }
        recent = samples[-5:] if len(samples) >= 5 else samples
        older_chunk = samples[:5] if len(samples) >= 10 else samples[:-5] if len(samples) > 5 else samples[:1]
        if not older_chunk:
            older_chunk = samples[:1]

        recent_delta = recent[-1]['mismatch_count'] - recent[0]['mismatch_count']
        older_delta = older_chunk[-1]['mismatch_count'] - older_chunk[0]['mismatch_count']
        drift_accel = (recent_delta - older_delta) / max(len(recent), 1)

        changes = [samples[i+1]['mismatch_count'] - samples[i]['mismatch_count']
                   for i in range(len(samples)-1)]
        positive_changes = [c for c in changes if c > 0]
        recurrence_vel = len(positive_changes) / max(len(changes), 1) * 100

        momentum = sum(c for c in changes[-5:]) / max(len(changes[-5:]), 1) if changes else 0

        escalation = self._calc_escalation_speed(samples)

        return {
            'drift_acceleration': round(drift_accel, 4),
            'recurrence_velocity': round(recurrence_vel, 2),
            'instability_momentum': round(momentum, 4),
            'escalation_speed': round(escalation, 4),
            'sample_size': len(samples),
        }

    def _calc_escalation_speed(self, samples: List[Dict]) -> float:
        if len(samples) < 3:
            return 0.0
        segment_size = max(len(samples) // 3, 1)
        segments = [samples[i:i+segment_size] for i in range(0, len(samples), segment_size)]
        if len(segments) < 2:
            return 0.0
        rates = []
        for seg in segments:
            if len(seg) >= 2:
                r = (seg[-1]['mismatch_count'] - seg[0]['mismatch_count']) / max(len(seg), 1)
                rates.append(r)
        if len(rates) < 2:
            return 0.0
        return rates[-1] - rates[0]

    @property
    def sample_count(self) -> int:
        return len(self._velocity_samples)

    def clear(self):
        self._velocity_samples.clear()
