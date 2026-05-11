import logging
from typing import Any, Dict, List, Optional

from simulation.workflows.definitions.base import WorkflowDefinition


logger = logging.getLogger('erp.simulation.scenario')


class ScenarioDefinition:
    """
    Scenario definition — controlled simulation blueprint.
    Contains workflow sequences, agent participation, event triggers.
    NO execution engine. NO randomness.
    """

    def __init__(self, scenario_id: str, name: str,
                 description: str = ''):
        self._scenario_id = scenario_id
        self._name = name
        self._description = description
        self._workflow_sequences: List[str] = []
        self._agent_participation: Dict[str, int] = {}
        self._event_triggers: List[Dict[str, Any]] = []

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def workflow_sequences(self) -> List[str]:
        return list(self._workflow_sequences)

    @property
    def agent_participation(self) -> Dict[str, int]:
        return dict(self._agent_participation)

    @property
    def event_triggers(self) -> List[Dict[str, Any]]:
        return list(self._event_triggers)

    def add_workflow(self, workflow_id: str):
        self._workflow_sequences.append(workflow_id)

    def set_agent_count(self, agent_id: str, count: int):
        self._agent_participation[agent_id] = count

    def add_event_trigger(self, event_type: str,
                          payload: Optional[dict] = None):
        self._event_triggers.append({
            'event_type': event_type,
            'payload': dict(payload) if payload else {},
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self._scenario_id,
            'name': self._name,
            'description': self._description,
            'workflows': list(self._workflow_sequences),
            'agents': dict(self._agent_participation),
            'triggers': list(self._event_triggers),
        }


def create_normal_business_day_scenario() -> ScenarioDefinition:
    scenario = ScenarioDefinition(
        'normal_business_day',
        'Normal Business Day',
        'Standard daily operations with balanced workflow mix',
    )
    scenario.add_workflow('sales_workflow')
    scenario.add_workflow('purchase_workflow')
    scenario.add_workflow('inventory_movement_workflow')
    scenario.add_workflow('hr_workflow')
    scenario.set_agent_count('sales_bot', 2)
    scenario.set_agent_count('purchasing_bot', 1)
    scenario.set_agent_count('inventory_bot', 2)
    scenario.set_agent_count('accountant_bot', 2)
    scenario.set_agent_count('hr_bot', 1)
    scenario.add_event_trigger('sales_triggered')
    scenario.add_event_trigger('purchase_triggered')
    scenario.add_event_trigger('inventory_movement_triggered')
    scenario.add_event_trigger('hr_triggered')
    return scenario


def create_low_activity_scenario() -> ScenarioDefinition:
    scenario = ScenarioDefinition(
        'low_activity',
        'Low Activity Day',
        'Minimal operations — reduced workflow load',
    )
    scenario.add_workflow('sales_workflow')
    scenario.add_workflow('hr_workflow')
    scenario.set_agent_count('sales_bot', 1)
    scenario.set_agent_count('hr_bot', 1)
    scenario.add_event_trigger('sales_triggered')
    scenario.add_event_trigger('hr_triggered')
    return scenario


def create_high_load_scenario() -> ScenarioDefinition:
    scenario = ScenarioDefinition(
        'high_load',
        'High Load Day',
        'Elevated operations with all workflows active (structure only)',
    )
    scenario.add_workflow('sales_workflow')
    scenario.add_workflow('purchase_workflow')
    scenario.add_workflow('inventory_movement_workflow')
    scenario.add_workflow('return_workflow')
    scenario.add_workflow('hr_workflow')
    scenario.set_agent_count('sales_bot', 5)
    scenario.set_agent_count('purchasing_bot', 3)
    scenario.set_agent_count('inventory_bot', 4)
    scenario.set_agent_count('accountant_bot', 3)
    scenario.set_agent_count('hr_bot', 2)
    scenario.add_event_trigger('sales_triggered')
    scenario.add_event_trigger('purchase_triggered')
    scenario.add_event_trigger('inventory_movement_triggered')
    scenario.add_event_trigger('return_triggered')
    scenario.add_event_trigger('hr_triggered')
    return scenario
