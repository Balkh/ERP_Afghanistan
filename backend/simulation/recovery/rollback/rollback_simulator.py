"""Rollback simulation — estimates impact of rolling back to a given tick."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import RollbackSimulation


class RollbackSimulator:
    def __init__(self, max_history: int = 100):
        self._simulations: deque = deque(maxlen=max_history)

    def simulate_rollback(self, simulation_id: str, target_tick: int,
                          workflow_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        workflow_history = workflow_history or []
        affected = [w for w in workflow_history if w.get('tick', 0) >= target_tick]
        workflows_affected = len(affected)
        journal_entries = sum(w.get('journal_entries', 0) for w in affected)
        inventory_movements = sum(w.get('inventory_movements', 0) for w in affected)
        has_conflicts = any(w.get('is_posted', False) for w in affected)
        conflicts = []
        if has_conflicts:
            conflicts = [w.get('workflow_id', 'unknown') for w in affected if w.get('is_posted')]
        risk_score = min(100.0, workflows_affected * 5 + journal_entries * 2 + inventory_movements * 1)
        sim = RollbackSimulation(
            simulation_id=simulation_id, target_tick=target_tick,
            workflows_affected=workflows_affected,
            journal_entries_affected=journal_entries,
            inventory_movements_affected=inventory_movements,
            estimated_risk_score=risk_score,
            has_conflicts=has_conflicts, conflicts=conflicts,
        )
        self._simulations.append({
            'simulation_id': simulation_id, 'target_tick': target_tick,
            'risk_score': risk_score, 'has_conflicts': has_conflicts,
        })
        return {
            'simulation_id': simulation_id, 'target_tick': target_tick,
            'workflows_affected': workflows_affected,
            'journal_entries_affected': journal_entries,
            'inventory_movements_affected': inventory_movements,
            'estimated_risk_score': risk_score,
            'has_conflicts': has_conflicts, 'conflicts': conflicts,
        }

    def get_simulation_count(self) -> int:
        return len(self._simulations)

    def clear(self):
        self._simulations.clear()
