import logging
from typing import Any, Dict, List

from simulation.agents.agent import SimulationAgent


logger = logging.getLogger('erp.simulation.agent.sales')


class SalesBot(SimulationAgent):
    """
    Virtual sales agent shell.
    NO business logic. Only emits lifecycle events.
    """

    def __init__(self):
        super().__init__('sales_bot', 'Sales Bot')

    def initialize(self, context) -> None:
        self._context = context
        self._initialized = True
        context.event_bus.publish(
            'agent_initialized', context.clock.now(),
            {'agent_id': self.agent_id, 'name': self.name},
        )
        logger.debug("SalesBot initialized")

    def execute(self) -> Dict[str, Any]:
        return {
            'status': 'ok',
            'agent_id': self.agent_id,
            'type': 'sales',
            'message': 'SalesBot executed tick',
        }

    def get_schedule(self) -> List[Dict[str, Any]]:
        return [{'type': 'recurring', 'interval_minutes': 10}]

    def validate(self) -> bool:
        return self._initialized
