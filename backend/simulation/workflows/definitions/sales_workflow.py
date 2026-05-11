from simulation.workflows.definitions.base import WorkflowDefinition, WorkflowStep


def create_sales_workflow() -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id='sales_workflow',
        name='Sales Processing Workflow',
        trigger_event='sales_triggered',
        description='Orchestrates sales invoice creation and processing',
    )
    wf.add_step(WorkflowStep('validate_order', 'Validate order details',
                             required_agent='sales_bot',
                             trigger_event='order_validated'))
    wf.add_step(WorkflowStep('check_inventory', 'Check product availability',
                             required_agent='inventory_bot',
                             trigger_event='inventory_checked'))
    wf.add_step(WorkflowStep('create_invoice', 'Create sales invoice',
                             required_agent='accountant_bot',
                             trigger_event='invoice_created'))
    wf.add_step(WorkflowStep('record_payment', 'Record customer payment',
                             required_agent='accountant_bot',
                             trigger_event='payment_recorded'))
    wf.add_required_agent('sales_bot')
    wf.add_required_agent('inventory_bot')
    wf.add_required_agent('accountant_bot')
    wf.add_expected_output('Sales invoice created')
    wf.add_expected_output('Inventory reserved')
    wf.add_expected_output('Payment processed')
    return wf
