import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger('erp.simulation.workflow_definition')


class WorkflowStep:
    """A single orchestration step in a workflow."""

    def __init__(self, step_id: str, description: str,
                 required_agent: Optional[str] = None,
                 trigger_event: Optional[str] = None):
        self.step_id = step_id
        self.description = description
        self.required_agent = required_agent
        self.trigger_event = trigger_event

    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_id': self.step_id,
            'description': self.description,
            'required_agent': self.required_agent,
            'trigger_event': self.trigger_event,
        }


class WorkflowDefinition:
    """
    Base class for workflow definitions.
    Pure orchestration metadata — NO business logic.
    """

    def __init__(self, workflow_id: str, name: str,
                 trigger_event: str, description: str = ''):
        self._workflow_id = workflow_id
        self._name = name
        self._trigger_event = trigger_event
        self._description = description
        self._steps: List[WorkflowStep] = []
        self._required_agents: List[str] = []
        self._expected_outputs: List[str] = []

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def trigger_event(self) -> str:
        return self._trigger_event

    @property
    def steps(self) -> List[WorkflowStep]:
        return list(self._steps)

    @property
    def required_agents(self) -> List[str]:
        return list(self._required_agents)

    @property
    def expected_outputs(self) -> List[str]:
        return list(self._expected_outputs)

    def add_step(self, step: WorkflowStep):
        self._steps.append(step)

    def add_required_agent(self, agent_id: str):
        if agent_id not in self._required_agents:
            self._required_agents.append(agent_id)

    def add_expected_output(self, output: str):
        self._expected_outputs.append(output)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'workflow_id': self._workflow_id,
            'name': self._name,
            'trigger_event': self._trigger_event,
            'description': self._description,
            'steps': [s.to_dict() for s in self._steps],
            'required_agents': list(self._required_agents),
            'expected_outputs': list(self._expected_outputs),
        }
