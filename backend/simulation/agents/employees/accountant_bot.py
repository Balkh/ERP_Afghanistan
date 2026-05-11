import logging
from typing import Any, Dict, List

from simulation.agents.agent import SimulationAgent


logger = logging.getLogger('erp.simulation.agent.accountant')


class AccountantBot(SimulationAgent):
    """
    Virtual accountant agent shell.
    NO business logic. Only emits lifecycle events.
    """

    def __init__(self):
        super().__init__('accountant_bot', 'Accountant Bot')

    def initialize(self, context) -> None:
        self._context = context
        self._initialized = True
        context.event_bus.publish(
            'agent_initialized', context.clock.now(),
            {'agent_id': self.agent_id, 'name': self.name},
        )
        logger.debug("AccountantBot initialized")

    def execute(self) -> Dict[str, Any]:
        return {
            'status': 'ok',
            'agent_id': self.agent_id,
            'type': 'accountant',
            'message': 'AccountantBot executed tick',
        }

    def get_schedule(self) -> List[Dict[str, Any]]:
        return [{'type': 'recurring', 'interval_minutes': 5}]

    def validate(self) -> bool:
        return self._initialized
