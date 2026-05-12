"""Operational evidence — tracks and manages forensic evidence chain."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ForensicEvidence


class OperationalEvidence:
    def __init__(self, max_evidence: int = 500):
        self._evidence_store: Dict[str, ForensicEvidence] = {}
        self._evidence_chain: deque = deque(maxlen=max_evidence)

    def add_evidence(self, evidence_id: str, tick: int, source: str,
                     description: str, evidence_type: str = "event",
                     related_events: Optional[List[str]] = None,
                     details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        evidence = ForensicEvidence(
            evidence_id=evidence_id, tick=tick, source=source,
            description=description, evidence_type=evidence_type,
            related_events=related_events or [],
            details=details or {},
        )
        self._evidence_store[evidence_id] = evidence
        self._evidence_chain.append(evidence_id)
        return {'evidence_id': evidence_id, 'tick': tick,
                'source': source, 'description': description}

    def get_evidence_chain(self, since_tick: int = 0) -> List[Dict[str, Any]]:
        return [{'evidence_id': e.evidence_id, 'tick': e.tick,
                 'source': e.source, 'description': e.description,
                 'evidence_type': e.evidence_type,
                 'related_events': e.related_events}
                for e in self._evidence_store.values()
                if e.tick >= since_tick]

    def get_evidence_count(self) -> int:
        return len(self._evidence_store)

    def clear(self):
        self._evidence_store.clear()
        self._evidence_chain.clear()
