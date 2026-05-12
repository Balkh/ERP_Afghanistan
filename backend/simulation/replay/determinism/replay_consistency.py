"""Replay consistency — checks consistency across replay runs."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.determinism.replay_hashing import ReplayHashing
from simulation.replay.determinism.divergence_detector import DivergenceDetector


class ReplayConsistency:
    def __init__(self, max_history: int = 100):
        self._consistency_history: deque = deque(maxlen=max_history)

    def check_consistency(self, run1_events: List[Dict[str, Any]],
                           run2_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        hasher = ReplayHashing()
        detector = DivergenceDetector()
        hash1 = hasher.hash_events_batch(run1_events)
        hash2 = hasher.hash_events_batch(run2_events)
        is_consistent = hash1 == hash2
        divergences = []
        if not is_consistent:
            order1 = [e.get('event_id', '') for e in run1_events]
            order2 = [e.get('event_id', '') for e in run2_events]
            order_div = detector.detect_order_mismatch(0, order1, order2)
            if order_div:
                divergences.append(order_div)
        self._consistency_history.append({
            'is_consistent': is_consistent,
            'divergences_found': len(divergences),
        })
        return {'is_consistent': is_consistent,
                'run1_hash': hash1, 'run2_hash': hash2,
                'divergences': divergences,
                'total_divergences': len(divergences)}

    def clear(self):
        self._consistency_history.clear()
