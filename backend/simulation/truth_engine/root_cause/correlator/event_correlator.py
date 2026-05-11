"""
Task 1: EventCorrelator — Links mismatches to underlying event chains.
Read-only analysis of recorded simulation events. No assumptions.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    CausalChain, CausalLink, NodeType, EdgeType,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.correlator')


class EventCorrelator:
    """
    Correlates mismatches (Phase 3A) with underlying event chains.
    Uses only actual recorded events. Returns UNKNOWN_CAUSE when
    insufficient data.
    """

    def __init__(self):
        self._chains: Dict[str, CausalChain] = {}

    def correlate(
        self,
        mismatch_id: str,
        mismatch_type: str,
        mismatch_description: str,
        affected_module: str,
        mismatch_tick: int,
        event_history: List[Any],
        workflow_completions: Dict[str, int],
        agent_executions: Dict[str, int],
    ) -> CausalChain:
        chain = CausalChain(
            chain_id=f"chain_{mismatch_id}",
            mismatch_id=mismatch_id,
            tick=mismatch_tick,
        )
        relevant = self._filter_relevant_events(
            mismatch_type, affected_module, mismatch_tick,
            event_history,
        )
        for event in relevant:
            link = CausalLink(
                link_id=f"link_{event.id}_{mismatch_id}",
                source_id=event.id,
                target_id=mismatch_id,
                source_type=NodeType.EVENT,
                target_type=NodeType.MISMATCH,
                edge_type=EdgeType.CAUSES,
                confidence=self._compute_correlation_confidence(
                    event, mismatch_type, affected_module
                ),
                metadata={
                    'event_type': event.type,
                    'event_timestamp': str(event.timestamp),
                },
            )
            chain.add_link(link)
        if not chain.links:
            logger.info(
                "EventCorrelator: no correlating events for %s",
                mismatch_id,
            )
        self._chains[chain.chain_id] = chain
        return chain

    def _filter_relevant_events(
        self,
        mismatch_type: str,
        affected_module: str,
        tick: int,
        event_history: List[Any],
    ) -> List[Any]:
        module_map = {
            'accounting': ('workflow_completed', 'agent_executed',
                           'tick_executed'),
            'inventory': ('workflow_completed', 'agent_executed'),
            'sales': ('workflow_started', 'workflow_completed',
                      'agent_executed'),
            'purchases': ('workflow_started', 'workflow_completed',
                          'agent_executed'),
            'workflow': ('workflow_started', 'workflow_completed',
                         'workflow_failed'),
            'simulation': ('tick_executed', 'agent_executed',
                           'agent_failed'),
        }
        relevant_types = module_map.get(affected_module, ())
        return [
            e for e in event_history
            if hasattr(e, 'type') and e.type in relevant_types
            and hasattr(e, 'timestamp')
        ]

    def _compute_correlation_confidence(
        self, event, mismatch_type: str, affected_module: str,
    ) -> float:
        type_map = {
            'workflow_completed': 0.85,
            'workflow_started': 0.60,
            'workflow_failed': 0.95,
            'agent_executed': 0.50,
            'agent_failed': 0.80,
            'tick_executed': 0.30,
        }
        base = type_map.get(event.type, 0.30)
        if mismatch_type == 'financial_mismatch' and affected_module == 'accounting':
            if event.type == 'workflow_completed':
                return min(1.0, base + 0.10)
        if mismatch_type == 'inventory_mismatch' and affected_module == 'inventory':
            if event.type in ('agent_executed', 'workflow_completed'):
                return min(1.0, base + 0.10)
        return base

    def get_chain(self, chain_id: str) -> Optional[CausalChain]:
        return self._chains.get(chain_id)

    @property
    def chain_count(self) -> int:
        return len(self._chains)
