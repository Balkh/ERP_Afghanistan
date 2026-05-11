"""
Task A: EventLifecycleAnalyzer — analyzes event creation, propagation, archival.
Detects orphans, duplicates, recursion risks, buildup, fan-out chains.
"""
import logging
from typing import Any, Dict, List, Optional
from collections import Counter

logger = logging.getLogger('erp.simulation.audit.event_lifecycle.analyzer')


class EventLifecycleAnalyzer:
    def analyze(self, event_history: List[Any]) -> Dict[str, Any]:
        events = list(event_history)
        type_counts = Counter()
        emitter_counts = Counter()
        for e in events:
            etype = getattr(e, 'type', str(e))
            type_counts[etype] += 1
        chains = self._detect_fan_out_chains(events)
        return {
            'total_events': len(events),
            'unique_types': len(type_counts),
            'type_distribution': dict(type_counts),
            'orphan_events': self._detect_orphans(events),
            'duplicate_propagations': self._detect_duplicates(events),
            'recursion_risks': self._detect_recursion_risks(events),
            'unconsumed_buildup': self._detect_unconsumed(events),
            'fan_out_chains': chains,
            'longest_chain': max(chains) if chains else 0,
        }

    def _detect_orphans(self, events: List) -> int:
        types = [getattr(e, 'type', '') for e in events]
        starter_types = {'simulation_started', 'workflow_started'}
        starter_count = sum(1 for t in types if t in starter_types)
        completer_types = {'simulation_stopped', 'workflow_completed'}
        completer_count = sum(1 for t in types if t in completer_types)
        return max(0, starter_count - completer_count)

    def _detect_duplicates(self, events: List) -> List[str]:
        seen_ids = set()
        duplicates = []
        for e in events:
            eid = getattr(e, 'id', id(e))
            if eid in seen_ids:
                duplicates.append(str(eid))
            seen_ids.add(eid)
        return duplicates

    def _detect_recursion_risks(self, events: List) -> List[str]:
        types = [getattr(e, 'type', '') for e in events]
        risky_pairs = [
            ('workflow_started', 'workflow_started'),
            ('workflow_completed', 'workflow_completed'),
            ('tick_executed', 'tick_executed'),
        ]
        risks = []
        for t1, t2 in risky_pairs:
            if types.count(t1) > 5:
                risks.append(f"high_frequency:{t1}")
        return risks

    def _detect_unconsumed(self, events: List) -> Dict[str, int]:
        types = [getattr(e, 'type', '') for e in events]
        produced = {t: types.count(t) for t in set(types)}
        consumed_map = {
            'workflow_started': 'workflow_completed',
            'tick_executed': 'simulation_stopped',
        }
        unconsumed = {}
        for producer, consumer in consumed_map.items():
            prod_count = produced.get(producer, 0)
            cons_count = produced.get(consumer, 0)
            if prod_count > cons_count:
                unconsumed[producer] = prod_count - cons_count
        return unconsumed

    def _detect_fan_out_chains(self, events: List) -> List[int]:
        type_seq = [getattr(e, 'type', '') for e in events]
        chains = []
        current = 0
        for t in type_seq:
            if t in ('workflow_started', 'simulation_started'):
                current += 1
            elif t in ('workflow_completed', 'simulation_stopped'):
                chains.append(current)
                current = 0
        if current > 0:
            chains.append(current)
        return chains if chains else [0]
