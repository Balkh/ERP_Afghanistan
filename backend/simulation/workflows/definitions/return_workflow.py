from simulation.workflows.definitions.base import WorkflowDefinition, WorkflowStep


def create_return_workflow() -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id='return_workflow',
        name='Return Processing Workflow',
        trigger_event='return_triggered',
        description='Orchestrates sales and purchase return processing',
    )
    wf.add_step(WorkflowStep('validate_return',
                             'Validate return request',
                             required_agent='inventory_bot',
                             trigger_event='return_validated'))
    wf.add_step(WorkflowStep('inspect_goods', 'Inspect returned goods',
                             required_agent='inventory_bot',
                             trigger_event='goods_inspected'))
    wf.add_step(WorkflowStep('restock_inventory',
                             'Return goods to inventory',
                             required_agent='inventory_bot',
                             trigger_event='inventory_restocked'))
    wf.add_step(WorkflowStep('process_refund',
                             'Process customer/supplier refund',
                             required_agent='accountant_bot',
                             trigger_event='refund_processed'))
    wf.add_required_agent('inventory_bot')
    wf.add_required_agent('accountant_bot')
    wf.add_expected_output('Return request validated')
    wf.add_expected_output('Goods restocked in inventory')
    wf.add_expected_output('Financial reversal triggered')
    return wf
