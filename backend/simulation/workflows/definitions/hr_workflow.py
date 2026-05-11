from simulation.workflows.definitions.base import WorkflowDefinition, WorkflowStep


def create_hr_workflow() -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id='hr_workflow',
        name='HR Processing Workflow',
        trigger_event='hr_triggered',
        description='Orchestrates employee lifecycle processes (placeholder)',
    )
    wf.add_step(WorkflowStep('record_attendance',
                             'Record employee attendance',
                             required_agent='hr_bot',
                             trigger_event='attendance_recorded'))
    wf.add_step(WorkflowStep('process_leave',
                             'Process leave request',
                             required_agent='hr_bot',
                             trigger_event='leave_processed'))
    wf.add_required_agent('hr_bot')
    wf.add_expected_output('Attendance recorded')
    wf.add_expected_output('Leave processed')
    return wf
