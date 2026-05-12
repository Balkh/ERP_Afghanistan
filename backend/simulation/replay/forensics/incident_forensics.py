"""Incident forensics — forensic analysis of operational incidents."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ForensicSeverity


class IncidentForensics:
    def __init__(self, max_history: int = 100):
        self._forensic_history: deque = deque(maxlen=max_history)

    def analyze_incident(self, incident_id: str,
                         trigger_event: Optional[Dict[str, Any]],
                         related_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        timeline = sorted(related_events, key=lambda e: e.get('tick', 0))
        severity = ForensicSeverity.INFO
        if len(timeline) > 10:
            severity = ForensicSeverity.CRITICAL
        elif len(timeline) > 5:
            severity = ForensicSeverity.HIGH
        elif len(timeline) > 2:
            severity = ForensicSeverity.MEDIUM
        sources = set(e.get('source', '') for e in timeline)
        self._forensic_history.append({
            'incident_id': incident_id, 'events_analyzed': len(timeline),
            'severity': severity.value, 'sources_involved': len(sources),
        })
        return {
            'incident_id': incident_id,
            'severity': severity.value,
            'timeline': timeline,
            'total_events': len(timeline),
            'sources_involved': list(sources),
            'trigger': trigger_event,
            'findings': f"Incident involved {len(sources)} source(s) across {len(timeline)} events",
        }

    def clear(self):
        self._forensic_history.clear()
