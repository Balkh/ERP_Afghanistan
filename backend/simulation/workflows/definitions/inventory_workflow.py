from simulation.workflows.definitions.base import WorkflowDefinition, WorkflowStep


def create_inventory_workflow() -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id='inventory_movement_workflow',
        name='Inventory Movement Workflow',
        trigger_event='inventory_movement_triggered',
        description='Orchestrates stock transfers and adjustments',
    )
    wf.add_step(WorkflowStep('validate_movement',
                             'Validate stock movement request',
                             required_agent='inventory_bot',
                             trigger_event='movement_validated'))
    wf.add_step(WorkflowStep('reserve_stock', 'Reserve stock from source',
                             required_agent='inventory_bot',
                             trigger_event='stock_reserved'))
    wf.add_step(WorkflowStep('update_ledger',
                             'Update inventory ledger entries',
                             required_agent='accountant_bot',
                             trigger_event='ledger_updated'))
    wf.add_required_agent('inventory_bot')
    wf.add_required_agent('accountant_bot')
    wf.add_expected_output('Stock movement recorded')
    wf.add_expected_output('Inventory ledger updated')
    return wf
