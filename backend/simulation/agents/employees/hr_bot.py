import logging
from typing import Any, Dict, List

from simulation.agents.agent import SimulationAgent


logger = logging.getLogger('erp.simulation.agent.hr')


class HRBot(SimulationAgent):
    """
    Virtual HR agent shell (placeholder).
    NO business logic. Only emits lifecycle events.
    """

    def __init__(self):
        super().__init__('hr_bot', 'HR Bot')

    def initialize(self, context) -> None:
        self._context = context
        self._initialized = True
        context.event_bus.publish(
            'agent_initialized', context.clock.now(),
            {'agent_id': self.agent_id, 'name': self.name},
        )
        logger.debug("HRBot initialized")

    def execute(self) -> Dict[str, Any]:
        return {
            'status': 'ok',
            'agent_id': self.agent_id,
            'type': 'hr',
            'message': 'HRBot executed tick',
        }

    def get_schedule(self) -> List[Dict[str, Any]]:
        return [{'type': 'recurring', 'interval_minutes': 15}]

    def validate(self) -> bool:
        return self._initialized
