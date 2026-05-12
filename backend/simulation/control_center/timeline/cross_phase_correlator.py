from collections import deque
from typing import Any, Dict, List

from simulation.control_center.models import UnifiedTimelineEvent


class CrossPhaseCorrelator:
    def __init__(self, max_correlations: int = 500):
        self._correlations: deque = deque(maxlen=max_correlations)

    def correlate_by_time(
        self, events: List[UnifiedTimelineEvent], window_ticks: int = 5
    ) -> List[Dict[str, Any]]:
        sorted_events = sorted(events, key=lambda e: e.tick)
        groups = []
        visited = [False] * len(sorted_events)

        for i, ev in enumerate(sorted_events):
            if visited[i]:
                continue
            group = [ev]
            visited[i] = True
            for j in range(i + 1, len(sorted_events)):
                if not visited[j] and abs(sorted_events[j].tick - ev.tick) <= window_ticks:
                    group.append(sorted_events[j])
                    visited[j] = True
            if len(group) > 1:
                correlation = self._build_correlation(group, f"time_window_{ev.tick}")
                groups.append(correlation)
                self._correlations.append(correlation)

        return groups

    def correlate_by_source(
        self, events: List[UnifiedTimelineEvent]
    ) -> List[Dict[str, Any]]:
        source_map: Dict[str, List[UnifiedTimelineEvent]] = {}
        for ev in events:
            source_map.setdefault(ev.source_phase, []).append(ev)

        groups = []
        for source, group in source_map.items():
            if len(group) > 1:
                correlation = self._build_correlation(group, f"source_{source}")
                groups.append(correlation)
                self._correlations.append(correlation)

        return groups

    def correlate_by_chain(
        self, events: List[UnifiedTimelineEvent], max_chain_depth: int = 100
    ) -> List[Dict[str, Any]]:
        event_map = {e.event_id: e for e in events}
        visited: set = set()
        chains = []

        for ev in events:
            if ev.event_id in visited:
                continue
            chain = []
            stack = [(ev.event_id, 0)]
            seen_in_chain: set = set()

            while stack and len(chain) < max_chain_depth:
                eid, depth = stack.pop()
                if eid in seen_in_chain or depth > max_chain_depth:
                    continue
                seen_in_chain.add(eid)
                current = event_map.get(eid)
                if current is None:
                    continue
                chain.append(current)
                visited.add(eid)
                for rid in getattr(current, 'related_event_ids', []):
                    if rid in event_map and rid not in seen_in_chain:
                        stack.append((rid, depth + 1))

            if len(chain) > 1:
                correlation = self._build_correlation(chain, f"chain_{chain[0].event_id}")
                chains.append(correlation)
                self._correlations.append(correlation)

        return chains

    @staticmethod
    def _build_correlation(
        group: List[UnifiedTimelineEvent], label: str
    ) -> Dict[str, Any]:
        sources = list({e.source_phase for e in group})
        severities = [e.severity.value for e in group]
        return {
            'correlation_id': label,
            'event_count': len(group),
            'source_phases': sources,
            'severities': severities,
            'tick_start': min(e.tick for e in group),
            'tick_end': max(e.tick for e in group),
            'event_ids': [e.event_id for e in group],
        }

    def get_correlation_count(self) -> int:
        return len(self._correlations)

    def clear(self):
        self._correlations.clear()
