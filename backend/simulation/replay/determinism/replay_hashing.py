"""Replay hashing — generates deterministic hashes for replay validation."""
import hashlib
import json
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayHash


class ReplayHashing:
    def __init__(self, max_history: int = 500):
        self._hash_history: deque = deque(maxlen=max_history)
        self._previous_hash: Optional[str] = None

    def hash_event(self, event: Dict[str, Any]) -> str:
        canonical = json.dumps(event, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def hash_events_batch(self, events: List[Dict[str, Any]]) -> str:
        combined = ''.join(self.hash_event(e) for e in events)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def record_hash(self, hash_id: str, tick: int, component: str = "timeline") -> Dict[str, Any]:
        hash_value = hashlib.sha256(f"{hash_id}:{tick}:{component}".encode('utf-8')).hexdigest()
        rh = ReplayHash(
            hash_id=hash_id, tick=tick, hash_value=hash_value,
            component=component, previous_hash=self._previous_hash,
        )
        self._previous_hash = hash_value
        self._hash_history.append(rh)
        return {'hash_id': hash_id, 'tick': tick, 'hash_value': hash_value,
                'component': component, 'previous_hash': rh.previous_hash}

    def verify_hash_chain(self) -> Dict[str, Any]:
        broken = False
        history_list = list(self._hash_history)
        for i in range(1, len(history_list)):
            expected_prev = history_list[i].previous_hash
            actual_prev = history_list[i - 1].hash_value
            if expected_prev and expected_prev != actual_prev:
                broken = True
        return {'chain_intact': not broken, 'hashes_checked': len(history_list)}

    def reset(self):
        self._hash_history.clear()
        self._previous_hash = None
