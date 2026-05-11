import logging
from typing import Any, Dict, List, Mapping


logger = logging.getLogger('erp.simulation.agent_runtime')


class AgentRuntime:
    """
    Deterministic agent execution layer.
    Wraps safe_execute. Maintains execution ordering.
    No business logic. No retry. No fallback.
    """

    def __init__(self, context):
        self._context = context

    def execute_agent(self, agent) -> Dict[str, Any]:
        result = agent.safe_execute()
        if result.get('status') == 'error':
            self._context.event_bus.publish(
                'agent_failed', self._context.clock.now(),
                {'agent_id': agent.agent_id, 'name': agent.name},
            )
        else:
            self._context.event_bus.publish(
                'agent_executed', self._context.clock.now(),
                {'agent_id': agent.agent_id, 'name': agent.name,
                 'result': result},
            )
        return result

    def execute_all(self, agents: Mapping[str, Any]) -> List[Dict[str, Any]]:
        results = []
        for agent_id in sorted(agents.keys()):
            agent = agents[agent_id]
            result = self.execute_agent(agent)
            results.append(result)
        return results
