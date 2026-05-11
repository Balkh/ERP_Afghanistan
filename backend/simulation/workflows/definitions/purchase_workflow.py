from simulation.workflows.definitions.base import WorkflowDefinition, WorkflowStep


def create_purchase_workflow() -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id='purchase_workflow',
        name='Purchase Processing Workflow',
        trigger_event='purchase_triggered',
        description='Orchestrates purchase order creation and receiving',
    )
    wf.add_step(WorkflowStep('create_order', 'Create purchase order',
                             required_agent='purchasing_bot',
                             trigger_event='order_created'))
    wf.add_step(WorkflowStep('receive_goods', 'Receive goods from supplier',
                             required_agent='inventory_bot',
                             trigger_event='goods_received'))
    wf.add_step(WorkflowStep('record_invoice', 'Record supplier invoice',
                             required_agent='accountant_bot',
                             trigger_event='supplier_invoice_recorded'))
    wf.add_step(WorkflowStep('process_payment', 'Process supplier payment',
                             required_agent='accountant_bot',
                             trigger_event='payment_processed'))
    wf.add_required_agent('purchasing_bot')
    wf.add_required_agent('inventory_bot')
    wf.add_required_agent('accountant_bot')
    wf.add_expected_output('Purchase order created')
    wf.add_expected_output('Inventory updated')
    wf.add_expected_output('Supplier payment processed')
    return wf
