import logging
import uuid
from typing import Any, Dict, List

from simulation.truth_engine.models.models import ExpectedState


logger = logging.getLogger('erp.simulation.truth.expected')


class ExpectedStateCollector:
    """
    Collects expected state from simulation layer.
    Derived ONLY from simulation outputs (Phase 2B workflows).
    NO ERP access. NO real data queries. READ ONLY.
    """

    def __init__(self, scenario_id: str, tick: int, timestamp,
                 collected_at):
        self._scenario_id = scenario_id
        self._tick = tick
        self._timestamp = timestamp
        self._collected_at = collected_at
        self._state = ExpectedState(
            scenario_id, tick, timestamp, collected_at
        )

    @classmethod
    def from_event_log(cls, scenario_id: str, tick: int,
                       timestamp, collected_at,
                       event_history: List[Any],
                       workflow_completions: Dict[str, int],
                       agent_executions: Dict[str, int]) -> ExpectedState:
        collector = cls(scenario_id, tick, timestamp, collected_at)
        for event in event_history:
            collector._state.add_workflow_event({
                'event_type': getattr(event, 'type', str(event)),
                'timestamp': str(getattr(event, 'timestamp', timestamp)),
                'payload': dict(getattr(event, 'payload', {})),
            })
        collector._state.set_returns_count(
            workflow_completions.get('return_workflow', 0)
        )
        collector._state.set_sales_count(
            workflow_completions.get('sales_workflow', 0)
        )
        collector._state.set_purchase_count(
            workflow_completions.get('purchase_workflow', 0)
        )
        for agent_id, count in agent_executions.items():
            collector._state.set_agent_execution(agent_id, count)
        return collector._state

    @classmethod
    def from_simulation_snapshot(
        cls, scenario_id: str, tick: int, timestamp,
        collected_at, snapshot: Dict[str, Any],
    ) -> ExpectedState:
        collector = cls(scenario_id, tick, timestamp, collected_at)
        collector._state.set_sales_count(
            snapshot.get('expected_sales_count', 0)
        )
        collector._state.set_purchase_count(
            snapshot.get('expected_purchase_count', 0)
        )
        collector._state.set_returns_count(
            snapshot.get('expected_returns_count', 0)
        )
        for product_id, delta in snapshot.get(
            'expected_inventory_delta', {}
        ).items():
            collector._state.set_inventory_delta(product_id, delta)
        for entry in snapshot.get('expected_accounting_entries', []):
            collector._state.add_accounting_entry(entry)
        collector._state.set_agent_execution(
            'sales_bot',
            snapshot.get('expected_sales_executions', 0)
        )
        collector._state.set_agent_execution(
            'inventory_bot',
            snapshot.get('expected_inventory_executions', 0)
        )
        collector._state.set_agent_execution(
            'accountant_bot',
            snapshot.get('expected_accounting_executions', 0)
        )
        return collector._state

    def set_sales_count(self, count: int):
        self._state.set_sales_count(count)

    def set_purchase_count(self, count: int):
        self._state.set_purchase_count(count)

    def set_returns_count(self, count: int):
        self._state.set_returns_count(count)

    def set_inventory_delta(self, product_id: str, delta: float):
        self._state.set_inventory_delta(product_id, delta)

    def add_accounting_entry(self, entry: Dict[str, Any]):
        self._state.add_accounting_entry(entry)

    def set_agent_execution(self, agent_id: str, count: int):
        self._state.set_agent_execution(agent_id, count)

    def build(self) -> ExpectedState:
        return self._state

    def to_dict(self) -> Dict[str, Any]:
        return self._state.to_dict()
