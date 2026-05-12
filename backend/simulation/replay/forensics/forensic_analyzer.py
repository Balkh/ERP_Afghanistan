"""Forensic analyzer — analyzes replay events for forensic evidence."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ForensicEvidence, ForensicSeverity


class ForensicAnalyzer:
    def __init__(self, max_evidence: int = 500):
        self._evidence: deque = deque(maxlen=max_evidence)
        self._evidence_count: int = 0

    def record_evidence(self, tick: int, source: str, description: str,
                        evidence_type: str = "event",
                        related_events: Optional[List[str]] = None,
                        details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._evidence_count += 1
        evidence_id = f"ev_{self._evidence_count}_{tick}"
        evidence = ForensicEvidence(
            evidence_id=evidence_id, tick=tick, source=source,
            description=description, evidence_type=evidence_type,
            related_events=related_events or [],
            details=details or {},
        )
        self._evidence.append(evidence)
        return {'evidence_id': evidence_id, 'tick': tick,
                'source': source, 'description': description}

    def analyze_event_pattern(self, events: List[Dict[str, Any]],
                               pattern_type: str = "error") -> List[Dict[str, Any]]:
        matches = []
        for e in events:
            e_type = e.get('event_type', '')
            if pattern_type in e_type.lower() or pattern_type in e.get('description', '').lower():
                matches.append({
                    'event_id': e.get('event_id', ''),
                    'tick': e.get('tick', 0),
                    'event_type': e_type,
                    'source': e.get('source', ''),
                    'description': e.get('description', ''),
                })
        return matches

    def get_evidence_count(self) -> int:
        return len(self._evidence)

    def clear(self):
        self._evidence.clear()
        self._evidence_count = 0
