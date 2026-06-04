"""
Tests for Phase 2B — Business Workflow Orchestration Layer.
Deterministic orchestration tests. NO business logic verification.
"""
import unittest
from datetime import datetime

from simulation.clocks.clock import VirtualClock
from simulation.events.bus import SimulationEventBus
from simulation.context.context import SimulationContext
from simulation.workflows.definitions.base import (
    WorkflowDefinition, WorkflowStep,
)
from simulation.workflows.definitions.sales_workflow import (
    create_sales_workflow,
)
from simulation.workflows.definitions.purchase_workflow import (
    create_purchase_workflow,
)
from simulation.workflows.definitions.inventory_workflow import (
    create_inventory_workflow,
)
from simulation.workflows.definitions.return_workflow import (
    create_return_workflow,
)
from simulation.workflows.definitions.hr_workflow import (
    create_hr_workflow,
)
from simulation.workflows.orchestrator.orchestrator import (
    WorkflowOrchestrator,
)
from simulation.workflows.scenarios.scenarios import (
    ScenarioDefinition,
    create_normal_business_day_scenario,
    create_low_activity_scenario,
    create_high_load_scenario,
)
from simulation.workflows.policies.policies import (
    SimulationPolicyEngine,
)
from simulation.engine.engine import SimulationEngine


class TestWorkflowDefinition(unittest.TestCase):
    """Workflow definition structural tests."""

    def test_workflow_step_to_dict(self):
        step = WorkflowStep('s1', 'Test step', 'agent1', 'evt1')
        d = step.to_dict()
        self.assertEqual(d['step_id'], 's1')
        self.assertEqual(d['description'], 'Test step')
        self.assertEqual(d['required_agent'], 'agent1')
        self.assertEqual(d['trigger_event'], 'evt1')

    def test_workflow_add_steps(self):
        wf = WorkflowDefinition('wf1', 'Test', 'trigger1')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        wf.add_step(WorkflowStep('s2', 'Step 2'))
        self.assertEqual(len(wf.steps), 2)

    def test_workflow_add_required_agents(self):
        wf = WorkflowDefinition('wf1', 'Test', 'trigger1')
        wf.add_required_agent('agent1')
        wf.add_required_agent('agent2')
        self.assertIn('agent1', wf.required_agents)
        self.assertIn('agent2', wf.required_agents)

    def test_workflow_add_expected_outputs(self):
        wf = WorkflowDefinition('wf1', 'Test', 'trigger1')
        wf.add_expected_output('Output A')
        self.assertIn('Output A', wf.expected_outputs)

    def test_workflow_to_dict(self):
        wf = WorkflowDefinition('wf1', 'Workflow 1', 'trigger1',
                                 'A test workflow')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        wf.add_required_agent('agent1')
        wf.add_expected_output('Result')
        d = wf.to_dict()
        self.assertEqual(d['workflow_id'], 'wf1')
        self.assertEqual(d['trigger_event'], 'trigger1')
        self.assertEqual(len(d['steps']), 1)
        self.assertEqual(len(d['required_agents']), 1)


class TestSalesWorkflow(unittest.TestCase):
    """Sales workflow definition tests."""

    def test_sales_workflow_structure(self):
        wf = create_sales_workflow()
        self.assertEqual(wf.workflow_id, 'sales_workflow')
        self.assertEqual(wf.trigger_event, 'sales_triggered')
        self.assertGreater(len(wf.steps), 0)
        self.assertIn('sales_bot', wf.required_agents)
        self.assertIn('accountant_bot', wf.required_agents)
        self.assertIn('inventory_bot', wf.required_agents)

    def test_sales_workflow_steps_have_descriptions(self):
        wf = create_sales_workflow()
        for step in wf.steps:
            self.assertIsNotNone(step.description)
            self.assertGreater(len(step.description), 0)

    def test_sales_workflow_steps_have_required_agents(self):
        wf = create_sales_workflow()
        for step in wf.steps:
            self.assertIsNotNone(step.required_agent)


class TestPurchaseWorkflow(unittest.TestCase):
    """Purchase workflow definition tests."""

    def test_purchase_workflow_structure(self):
        wf = create_purchase_workflow()
        self.assertEqual(wf.trigger_event, 'purchase_triggered')
        self.assertIn('purchasing_bot', wf.required_agents)
        self.assertIn('inventory_bot', wf.required_agents)
        self.assertIn('accountant_bot', wf.required_agents)


class TestInventoryWorkflow(unittest.TestCase):
    """Inventory movement workflow definition tests."""

    def test_inventory_workflow_structure(self):
        wf = create_inventory_workflow()
        self.assertEqual(wf.trigger_event,
                         'inventory_movement_triggered')
        self.assertIn('inventory_bot', wf.required_agents)
        self.assertIn('accountant_bot', wf.required_agents)


class TestReturnWorkflow(unittest.TestCase):
    """Return workflow definition tests."""

    def test_return_workflow_structure(self):
        wf = create_return_workflow()
        self.assertEqual(wf.trigger_event, 'return_triggered')
        self.assertIn('inventory_bot', wf.required_agents)
        self.assertIn('accountant_bot', wf.required_agents)

    def test_return_workflow_has_expected_outputs(self):
        wf = create_return_workflow()
        self.assertGreater(len(wf.expected_outputs), 0)
        outputs = ' '.join(wf.expected_outputs).lower()
        self.assertIn('return', outputs)

    def test_return_workflow_no_direct_mutation(self):
        wf = create_return_workflow()
        for step in wf.steps:
            self.assertNotIn(
                step.description.lower(),
                ['stock adjustment', 'batch update', 'quantity set'],
            )


class TestHRWorkflow(unittest.TestCase):
    """HR workflow definition tests."""

    def test_hr_workflow_structure(self):
        wf = create_hr_workflow()
        self.assertEqual(wf.trigger_event, 'hr_triggered')
        self.assertIn('hr_bot', wf.required_agents)


class TestWorkflowOrchestrator(unittest.TestCase):
    """Workflow orchestration tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0)
        )
        self.bus = SimulationEventBus(max_history=100)
        self.context = SimulationContext(clock=self.clock,
                                        event_bus=self.bus)
        self.context.finalize()
        self.orch = WorkflowOrchestrator(self.bus)

    def test_register_workflow(self):
        wf = create_sales_workflow()
        self.orch.register_workflow(wf)
        self.assertIn('sales_workflow',
                      self.orch.registered_workflows)

    def test_register_duplicate_workflow_raises(self):
        wf = create_sales_workflow()
        self.orch.register_workflow(wf)
        with self.assertRaises(ValueError):
            self.orch.register_workflow(wf)

    def test_trigger_workflow(self):
        self.orch.register_workflow(create_sales_workflow())
        result = self.orch.trigger_workflow('sales_workflow',
                                             self.context)
        self.assertIsNotNone(result)
        self.assertEqual(result['workflow_id'], 'sales_workflow')
        self.assertEqual(result['status'], 'step_completed')

    def test_workflow_advances_steps(self):
        self.orch.register_workflow(create_sales_workflow())
        r1 = self.orch.trigger_workflow('sales_workflow', self.context)
        self.assertEqual(r1['step_index'], 0)
        r2 = self.orch.handle_event('sales_triggered', self.context)
        self.assertEqual(r2['step_index'], 1)

    def test_workflow_completes(self):
        wf = WorkflowDefinition('tiny', 'Tiny', 'tiny_trigger')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        self.orch.register_workflow(wf)
        self.orch.trigger_workflow('tiny', self.context)
        result = self.orch.handle_event('tiny_trigger', self.context)
        self.assertEqual(result['status'], 'completed')

    def test_workflow_emits_started_event(self):
        self.orch.register_workflow(create_sales_workflow())
        self.orch.trigger_workflow('sales_workflow', self.context)
        started = self.bus.events_by_type('workflow_started')
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0].payload['workflow_id'],
                         'sales_workflow')

    def test_workflow_emits_completed_event(self):
        wf = WorkflowDefinition('tiny', 'Tiny', 'tiny_trigger')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        self.orch.register_workflow(wf)
        self.orch.trigger_workflow('tiny', self.context)
        self.orch.handle_event('tiny_trigger', self.context)
        completed = self.bus.events_by_type('workflow_completed')
        self.assertEqual(len(completed), 1)

    def test_handle_event_returns_none_for_unknown(self):
        result = self.orch.handle_event('unknown_event', self.context)
        self.assertIsNone(result)

    def test_trigger_nonexistent_workflow_returns_none(self):
        result = self.orch.trigger_workflow('nonexistent', self.context)
        self.assertIsNone(result)

    def test_active_workflows_tracked(self):
        self.orch.register_workflow(create_sales_workflow())
        self.orch.trigger_workflow('sales_workflow', self.context)
        self.assertIn('sales_workflow', self.orch.active_workflows)

    def test_completed_count(self):
        wf = WorkflowDefinition('tiny', 'Tiny', 'tiny_trigger')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        self.orch.register_workflow(wf)
        self.orch.trigger_workflow('tiny', self.context)
        self.orch.handle_event('tiny_trigger', self.context)
        self.assertEqual(self.orch.completed_count, 1)

    def test_reset_clears_state(self):
        self.orch.register_workflow(create_sales_workflow())
        self.orch.trigger_workflow('sales_workflow', self.context)
        self.orch.reset()
        self.assertEqual(len(self.orch.active_workflows), 0)

    def test_handle_event_triggers_workflow_from_event(self):
        self.orch.register_workflow(create_sales_workflow())
        result = self.orch.handle_event('sales_triggered', self.context)
        self.assertIsNotNone(result)
        self.assertEqual(result['workflow_id'], 'sales_workflow')


class TestScenarioDefinitions(unittest.TestCase):
    """Scenario definition tests."""

    def test_normal_business_day_scenario(self):
        s = create_normal_business_day_scenario()
        self.assertEqual(s.scenario_id, 'normal_business_day')
        self.assertIn('sales_workflow', s.workflow_sequences)
        self.assertIn('purchase_workflow', s.workflow_sequences)
        self.assertIn('inventory_bot', s.agent_participation)
        self.assertIn('sales_triggered', [t['event_type']
                                           for t in s.event_triggers])

    def test_low_activity_scenario(self):
        s = create_low_activity_scenario()
        self.assertLess(len(s.workflow_sequences),
                        len(create_normal_business_day_scenario().workflow_sequences))
        self.assertEqual(s.agent_participation['sales_bot'], 1)
        self.assertEqual(s.agent_participation['hr_bot'], 1)

    def test_high_load_scenario(self):
        s = create_high_load_scenario()
        self.assertIn('return_workflow', s.workflow_sequences)
        self.assertGreater(s.agent_participation['sales_bot'], 1)
        self.assertEqual(len(s.event_triggers), 5)

    def test_scenario_definition_add_workflow(self):
        s = ScenarioDefinition('test', 'Test', 'A test scenario')
        s.add_workflow('wf1')
        s.add_workflow('wf2')
        self.assertEqual(len(s.workflow_sequences), 2)

    def test_scenario_definition_set_agent_count(self):
        s = ScenarioDefinition('test', 'Test')
        s.set_agent_count('bot1', 5)
        self.assertEqual(s.agent_participation['bot1'], 5)

    def test_scenario_definition_add_trigger(self):
        s = ScenarioDefinition('test', 'Test')
        s.add_event_trigger('evt1', {'key': 'value'})
        triggers = s.event_triggers
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]['event_type'], 'evt1')
        self.assertEqual(triggers[0]['payload']['key'], 'value')

    def test_scenario_to_dict(self):
        s = create_normal_business_day_scenario()
        d = s.to_dict()
        self.assertIn('scenario_id', d)
        self.assertIn('workflows', d)
        self.assertIn('agents', d)
        self.assertIn('triggers', d)


class TestSimulationPolicyEngine(unittest.TestCase):
    """Policy engine validation tests."""

    def setUp(self):
        self.policy = SimulationPolicyEngine()

    def test_default_rules_registered(self):
        self.assertIn('inventory_non_negative', self.policy.rules)
        self.assertIn('balanced_financial', self.policy.rules)
        self.assertIn('valid_workflow_transition', self.policy.rules)

    def test_add_rule(self):
        self.policy.add_rule('custom_rule', {
            'name': 'Custom',
            'category': 'test',
            'severity': 'warning',
        })
        self.assertIn('custom_rule', self.policy.rules)

    def test_add_duplicate_rule_raises(self):
        with self.assertRaises(ValueError):
            self.policy.add_rule('inventory_non_negative', {})

    def test_validate_workflow_execution_valid_step(self):
        steps = ['s1', 's2', 's3']
        result = self.policy.validate_workflow_execution(
            'wf1', 's2', steps
        )
        self.assertTrue(result)

    def test_validate_workflow_execution_invalid_step(self):
        steps = ['s1', 's2', 's3']
        result = self.policy.validate_workflow_execution(
            'wf1', 'invalid_step', steps
        )
        self.assertFalse(result)
        self.assertGreater(self.policy.violation_count, 0)

    def test_validate_inventory_operation_valid(self):
        result = self.policy.validate_inventory_operation('in', 100)
        self.assertTrue(result)

    def test_validate_inventory_operation_negative_out(self):
        result = self.policy.validate_inventory_operation('out', -50)
        self.assertFalse(result)
        violations = self.policy.violations
        self.assertGreater(len(violations), 0)

    def test_validate_financial_balance_valid(self):
        result = self.policy.validate_financial_balance(1000.0, 1000.0)
        self.assertTrue(result)

    def test_validate_financial_balance_unbalanced(self):
        result = self.policy.validate_financial_balance(1000.0, 500.0)
        self.assertFalse(result)
        violations = self.policy.violations
        self.assertGreater(len(violations), 0)

    def test_block_workflow(self):
        result = self.policy.block_workflow('wf1', 'Invalid state')
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['workflow_id'], 'wf1')
        self.assertEqual(result['reason'], 'Invalid state')

    def test_clear_violations(self):
        self.policy.validate_financial_balance(100.0, 50.0)
        self.assertGreater(self.policy.violation_count, 0)
        self.policy.clear_violations()
        self.assertEqual(self.policy.violation_count, 0)

    def test_get_rule(self):
        rule = self.policy.get_rule('inventory_non_negative')
        self.assertIsNotNone(rule)
        self.assertEqual(rule['category'], 'inventory')

    def test_get_nonexistent_rule_returns_none(self):
        self.assertIsNone(self.policy.get_rule('nonexistent'))


class TestEngineWorkflowIntegration(unittest.TestCase):
    """Engine + workflow orchestration integration tests."""

    def setUp(self):
        self.engine = SimulationEngine()

    def test_engine_has_orchestrator(self):
        self.assertIsNotNone(self.engine.orchestrator)

    def test_engine_has_policy_engine(self):
        self.assertIsNotNone(self.engine.policy_engine)

    def test_engine_workflow_registration(self):
        wf = create_sales_workflow()
        self.engine.orchestrator.register_workflow(wf)
        self.assertIn('sales_workflow',
                      self.engine.orchestrator.registered_workflows)

    def test_engine_workflow_trigger(self):
        self.engine.orchestrator.register_workflow(
            create_sales_workflow()
        )
        self.engine.initialize()
        self.engine.start()
        result = self.engine.orchestrator.trigger_workflow(
            'sales_workflow', self.engine.context
        )
        self.assertIsNotNone(result)
        self.engine.stop()

    def test_workflow_events_in_event_bus(self):
        self.engine.orchestrator.register_workflow(
            create_sales_workflow()
        )
        self.engine.initialize()
        self.engine.start()
        self.engine.orchestrator.trigger_workflow(
            'sales_workflow', self.engine.context
        )
        event_types = {e.type for e in self.engine.event_bus.history}
        self.assertIn('workflow_started', event_types)
        self.engine.stop()

    def test_policy_blocks_invalid_workflow_step(self):
        valid_steps = ['s1', 's2']
        result = self.engine.policy_engine.validate_workflow_execution(
            'wf1', 'invalid', valid_steps
        )
        self.assertFalse(result)


class TestNoBusinessLogic(unittest.TestCase):
    """Strict isolation — zero business logic in workflows."""

    def test_no_domain_imports_in_workflows(self):
        import ast
        import os
        wf_dir = os.path.join(
            os.path.dirname(__file__), '..', 'workflows'
        )
        forbidden = ('accounting', 'inventory', 'sales', 'purchases',
                     'payments', 'payroll', 'hr', 'core')
        issues = []
        for root, dirs, files in os.walk(wf_dir):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            mod = alias.name.split('.')[0]
                            if mod in forbidden:
                                issues.append(
                                    f"{fname}: imports {alias.name}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        mod = (node.module or '').split('.')[0]
                        if mod in forbidden:
                            issues.append(
                                f"{fname}: from {node.module}"
                            )
        self.assertEqual(issues, [],
                         f"Business logic imports found: {issues}")

    def test_no_erp_calls_in_orchestrator(self):
        import ast
        import os
        orch_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'workflows', 'orchestrator', 'orchestrator.py'
        )
        with open(orch_file) as fh:
            content = fh.read()
        forbidden = ('JournalEngine', 'InventoryService', 'PaymentEngine',
                     'PayrollService', 'SaleInvoice', 'PurchaseInvoice',
                     'Batch', 'StockMovement', 'Account', 'JournalEntry')
        for keyword in forbidden:
            self.assertNotIn(keyword, content,
                             f"Business logic keyword '{keyword}' "
                             f"found in orchestrator")

    def test_workflow_steps_are_descriptions_only(self):
        wf = create_sales_workflow()
        business_keywords = ('CREATE', 'UPDATE', 'DELETE', 'POST',
                             'calculate', 'compute', 'set_quantity')
        for step in wf.steps:
            for kw in business_keywords:
                self.assertNotIn(
                    kw, step.description,
                    f"Step '{step.step_id}' contains business "
                    f"keyword: {kw}"
                )

    def test_scenario_definitions_no_execution_logic(self):
        s = create_normal_business_day_scenario()
        for wf_id in s.workflow_sequences:
            self.assertIsInstance(wf_id, str)
            self.assertGreater(len(wf_id), 0)
        for agent_id, count in s.agent_participation.items():
            self.assertIsInstance(agent_id, str)
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)

    def test_return_workflow_no_direct_stock_mutation(self):
        wf = create_return_workflow()
        mutation_keywords = ('update_batch', 'set_quantity',
                            'adjust_stock', 'modify_remaining')
        for step in wf.steps:
            for kw in mutation_keywords:
                self.assertNotIn(kw, step.description,
                                 f"Return step contains mutation: {kw}")


class TestEventEmissionLayer(unittest.TestCase):
    """Workflow event emission layer tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0)
        )
        self.bus = SimulationEventBus(max_history=100)
        self.context = SimulationContext(clock=self.clock,
                                         event_bus=self.bus)
        self.context.finalize()
        self.orch = WorkflowOrchestrator(self.bus)

    def test_workflow_started_event_format(self):
        wf = WorkflowDefinition('tiny', 'Tiny', 'tiny_trigger')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        self.orch.register_workflow(wf)
        self.orch.trigger_workflow('tiny', self.context)
        events = self.bus.events_by_type('workflow_started')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload['workflow_id'], 'tiny')

    def test_workflow_completed_event_format(self):
        wf = WorkflowDefinition('tiny', 'Tiny', 'tiny_trigger')
        wf.add_step(WorkflowStep('s1', 'Step 1'))
        self.orch.register_workflow(wf)
        self.orch.trigger_workflow('tiny', self.context)
        self.orch.handle_event('tiny_trigger', self.context)
        events = self.bus.events_by_type('workflow_completed')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload['workflow_id'], 'tiny')

    def test_no_business_events_in_workflow_emissions(self):
        self.orch.register_workflow(create_sales_workflow())
        self.orch.trigger_workflow('sales_workflow', self.context)
        for event in self.bus.history:
            self.assertNotIn('journal', event.type.lower())
            self.assertNotIn('invoice', event.type.lower())
            self.assertNotIn('batch', event.type.lower())

    def test_return_initiated_event_type_valid(self):
        self.assertIn('return_initiated',
                       SimulationEventBus.VALID_EVENT_TYPES)


if __name__ == '__main__':
    unittest.main()
