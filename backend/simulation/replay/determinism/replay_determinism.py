"""Replay determinism — verifies deterministic replay behavior."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import DivergenceType, ForensicSeverity
from simulation.replay.determinism.replay_hashing import ReplayHashing


class ReplayDeterminism:
    def __init__(self, max_history: int = 100):
        self._determinism_history: deque = deque(maxlen=max_history)

    def verify_determinism(self, run1_events: List[Dict[str, Any]],
                            run2_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        hasher = ReplayHashing()
        hash1 = hasher.hash_events_batch(run1_events)
        hash2 = hasher.hash_events_batch(run2_events)
        is_deterministic = hash1 == hash2
        mismatches = []
        if not is_deterministic:
            for i, (e1, e2) in enumerate(zip(run1_events, run2_events)):
                h1 = hasher.hash_event(e1)
                h2 = hasher.hash_event(e2)
                if h1 != h2:
                    mismatches.append({
                        'index': i,
                        'event_id_1': e1.get('event_id', ''),
                        'event_id_2': e2.get('event_id', ''),
                    })
                    if len(mismatches) >= 10:
                        break
        self._determinism_history.append({
            'is_deterministic': is_deterministic,
            'run1_hash': hash1[:16], 'run2_hash': hash2[:16],
            'mismatches_found': len(mismatches),
        })
        return {'is_deterministic': is_deterministic,
                'run1_hash': hash1, 'run2_hash': hash2,
                'mismatches': mismatches,
                'total_mismatches': len(mismatches)}

    def clear(self):
        self._determinism_history.clear()
