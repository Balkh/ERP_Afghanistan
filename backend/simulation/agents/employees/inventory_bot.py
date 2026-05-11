import logging
from typing import Any, Dict, List

from simulation.agents.agent import SimulationAgent


logger = logging.getLogger('erp.simulation.agent.inventory')


class InventoryBot(SimulationAgent):
    """
    Virtual inventory agent shell.
    NO business logic. Only emits lifecycle events.
    """

    def __init__(self):
        super().__init__('inventory_bot', 'Inventory Bot')

    def initialize(self, context) -> None:
        self._context = context
        self._initialized = True
        context.event_bus.publish(
            'agent_initialized', context.clock.now(),
            {'agent_id': self.agent_id, 'name': self.name},
        )
        logger.debug("InventoryBot initialized")

    def execute(self) -> Dict[str, Any]:
        return {
            'status': 'ok',
            'agent_id': self.agent_id,
            'type': 'inventory',
            'message': 'InventoryBot executed tick',
        }

    def get_schedule(self) -> List[Dict[str, Any]]:
        return [{'type': 'recurring', 'interval_minutes': 3}]

    def validate(self) -> bool:
        return self._initialized
