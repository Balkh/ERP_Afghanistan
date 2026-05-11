import logging
from typing import Any, Dict, List, Optional

from simulation.events.bus import SimulationEventBus
from simulation.workflows.definitions.base import WorkflowDefinition


logger = logging.getLogger('erp.simulation.workflow_orchestrator')


class WorkflowOrchestrator:
    """
    Maps simulation events to workflow definitions.
    Coordinates agent participation. Tracks active workflows.
    NO direct service calls. NO parallel execution. NO randomness.
    """

    def __init__(self, event_bus: SimulationEventBus):
        self._event_bus = event_bus
        self._event_map: Dict[str, WorkflowDefinition] = {}
        self._active_workflows: Dict[str, dict] = {}
        self._completed_workflows: Dict[str, List[str]] = {}
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register_workflow(self, workflow: WorkflowDefinition):
        wf_id = workflow.workflow_id
        if wf_id in self._workflows:
            raise ValueError(
                f"Workflow '{wf_id}' already registered"
            )
        self._workflows[wf_id] = workflow
        trigger = workflow.trigger_event
        self._event_map[trigger] = workflow
        logger.debug("Orchestrator: registered workflow '%s'", wf_id)

    def trigger_workflow(self, workflow_id: str,
                         context) -> Optional[Dict[str, Any]]:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            logger.warning("Workflow '%s' not found", workflow_id)
            return None
        now = context.clock.now()
        self._active_workflows[workflow_id] = {
            'workflow_id': workflow_id,
            'started_at': now,
            'current_step_index': 0,
            'completed_steps': [],
            'status': 'running',
        }
        self._event_bus.publish(
            'workflow_started', now,
            {'workflow_id': workflow_id,
             'name': workflow.name,
             'total_steps': len(workflow.steps)},
        )
        logger.debug("Workflow '%s' triggered", workflow_id)
        result = self._advance_workflow(workflow_id, context)
        return result

    def _advance_workflow(self, workflow_id: str,
                          context) -> Dict[str, Any]:
        active = self._active_workflows.get(workflow_id)
        if active is None:
            return {'status': 'not_found'}
        workflow = self._workflows.get(workflow_id)
        if active['current_step_index'] >= len(workflow.steps):
            return self._complete_workflow(workflow_id, context)
        step = workflow.steps[active['current_step_index']]
        active['current_step_index'] += 1
        active['completed_steps'].append(step.step_id)
        if step.trigger_event:
            self._event_bus.publish(
                step.trigger_event, context.clock.now(),
                {'workflow_id': workflow_id, 'step_id': step.step_id},
            )
        return {
            'workflow_id': workflow_id,
            'step_id': step.step_id,
            'step_index': active['current_step_index'] - 1,
            'total_steps': len(workflow.steps),
            'status': 'step_completed',
        }

    def _complete_workflow(self, workflow_id: str,
                           context) -> Dict[str, Any]:
        active = self._active_workflows.pop(workflow_id, None)
        if active is None:
            return {'status': 'not_found'}
        now = context.clock.now()
        self._event_bus.publish(
            'workflow_completed', now,
            {'workflow_id': workflow_id,
             'total_steps': len(active['completed_steps'])},
        )
        if workflow_id not in self._completed_workflows:
            self._completed_workflows[workflow_id] = []
        self._completed_workflows[workflow_id].append(
            now.isoformat()
        )
        logger.debug("Workflow '%s' completed", workflow_id)
        return {
            'workflow_id': workflow_id,
            'status': 'completed',
            'completed_steps': active['completed_steps'],
        }

    def handle_event(self, event_type: str, context) -> Optional[Dict[str, Any]]:
        workflow = self._event_map.get(event_type)
        if workflow is None:
            return None
        if workflow.workflow_id not in self._active_workflows:
            return self.trigger_workflow(workflow.workflow_id, context)
        return self._advance_workflow(workflow.workflow_id, context)

    @property
    def active_workflows(self) -> Dict[str, dict]:
        return dict(self._active_workflows)

    @property
    def registered_workflows(self) -> Dict[str, WorkflowDefinition]:
        return dict(self._workflows)

    @property
    def completed_count(self) -> int:
        return sum(len(v) for v in self._completed_workflows.values())

    @property
    def workflow_completions(self) -> Dict[str, int]:
        return {
            wf_id: len(completions)
            for wf_id, completions in self._completed_workflows.items()
        }

    def reset(self):
        self._active_workflows.clear()
        self._completed_workflows.clear()
