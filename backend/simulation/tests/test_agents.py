"""
Tests for Phase 2A — Virtual Employee Foundation Layer.
Deterministic agent shell tests. NO business logic verification.
"""
import unittest
from datetime import datetime

from simulation.agents.agent import SimulationAgent
from simulation.agents.registry.registry import AgentRegistry
from simulation.agents.runtime.runtime import AgentRuntime
from simulation.agents.employees.accountant_bot import AccountantBot
from simulation.agents.employees.sales_bot import SalesBot
from simulation.agents.employees.inventory_bot import InventoryBot
from simulation.agents.employees.purchasing_bot import PurchasingBot
from simulation.agents.employees.hr_bot import HRBot
from simulation.clocks.clock import VirtualClock
from simulation.events.bus import SimulationEventBus
from simulation.metrics.collector import SimulationMetricsCollector
from simulation.context.context import SimulationContext
from simulation.scheduler.scheduler import SimulationScheduler
from simulation.engine.engine import SimulationEngine


class TestAgentRegistry(unittest.TestCase):
    """AgentRegistry registration, dedup, metadata tests."""

    def setUp(self):
        self.reg = AgentRegistry()

    def test_register_and_retrieve(self):
        self.reg.register('accountant', AccountantBot,
                          description='Handles accounting')
        entry = self.reg.get('accountant')
        self.assertIsNotNone(entry)
        self.assertEqual(entry['agent_type'], 'accountant')
        self.assertEqual(entry['class'], AccountantBot)
        self.assertEqual(entry['description'], 'Handles accounting')

    def test_duplicate_registration_raises(self):
        self.reg.register('sales', SalesBot)
        with self.assertRaises(ValueError):
            self.reg.register('sales', SalesBot)

    def test_contains(self):
        self.reg.register('inv', InventoryBot)
        self.assertTrue(self.reg.contains('inv'))
        self.assertFalse(self.reg.contains('nonexistent'))

    def test_count(self):
        self.assertEqual(self.reg.count, 0)
        self.reg.register('a', AccountantBot)
        self.reg.register('b', SalesBot)
        self.assertEqual(self.reg.count, 2)

    def test_registered_types_ordered(self):
        self.reg.register('z', AccountantBot)
        self.reg.register('a', SalesBot)
        types = self.reg.registered_types
        self.assertEqual(types, ['z', 'a'])

    def test_get_class(self):
        self.reg.register('hr', HRBot)
        cls = self.reg.get_class('hr')
        self.assertIs(cls, HRBot)
        self.assertIsNone(self.reg.get_class('nonexistent'))

    def test_get_all(self):
        self.reg.register('a', AccountantBot)
        self.reg.register('b', SalesBot)
        all_entries = self.reg.get_all()
        self.assertEqual(len(all_entries), 2)
        self.assertIn('a', all_entries)
        self.assertIn('b', all_entries)

    def test_unregister(self):
        self.reg.register('pur', PurchasingBot)
        self.assertTrue(self.reg.unregister('pur'))
        self.assertFalse(self.reg.contains('pur'))
        self.assertFalse(self.reg.unregister('nonexistent'))

    def test_clear(self):
        self.reg.register('a', AccountantBot)
        self.reg.register('b', SalesBot)
        self.reg.clear()
        self.assertEqual(self.reg.count, 0)
        self.assertEqual(len(self.reg.registered_types), 0)

    def test_metadata_stored(self):
        metadata = {'department': 'finance', 'priority': 1}
        self.reg.register('acc', AccountantBot, metadata=metadata)
        entry = self.reg.get('acc')
        self.assertEqual(entry['metadata']['department'], 'finance')
        self.assertEqual(entry['metadata']['priority'], 1)

    def test_metadata_immutable_copy(self):
        meta = {'key': 'original'}
        self.reg.register('t', AccountantBot, metadata=meta)
        meta['key'] = 'changed'
        entry = self.reg.get('t')
        self.assertEqual(entry['metadata']['key'], 'original')


class TestAgentShells(unittest.TestCase):
    """Five virtual employee agent shell lifecycle tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0)
        )
        self.bus = SimulationEventBus(max_history=100)
        self.context = SimulationContext(clock=self.clock,
                                         event_bus=self.bus)
        self.context.finalize()

    def _test_agent_shell_lifecycle(self, agent: SimulationAgent,
                                    expected_type: str):
        self.assertEqual(agent.agent_id, f'{expected_type}_bot')
        agent.initialize(self.context)
        self.assertTrue(agent.validate())
        result = agent.execute()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['agent_id'], agent.agent_id)
        self.assertEqual(result['type'], expected_type)
        self.assertIn('message', result)
        schedule = agent.get_schedule()
        self.assertIsInstance(schedule, list)
        self.assertGreater(len(schedule), 0)
        self.assertIn('type', schedule[0])
        agent.shutdown()

    def test_accountant_bot_lifecycle(self):
        self._test_agent_shell_lifecycle(AccountantBot(), 'accountant')

    def test_sales_bot_lifecycle(self):
        self._test_agent_shell_lifecycle(SalesBot(), 'sales')

    def test_inventory_bot_lifecycle(self):
        self._test_agent_shell_lifecycle(InventoryBot(), 'inventory')

    def test_purchasing_bot_lifecycle(self):
        self._test_agent_shell_lifecycle(PurchasingBot(), 'purchasing')

    def test_hr_bot_lifecycle(self):
        self._test_agent_shell_lifecycle(HRBot(), 'hr')

    def test_all_agents_emit_initialized_event(self):
        agents = [
            AccountantBot(), SalesBot(), InventoryBot(),
            PurchasingBot(), HRBot(),
        ]
        for agent in agents:
            agent.initialize(self.context)
        events = self.bus.events_by_type('agent_initialized')
        self.assertEqual(len(events), 5)
        agent_ids = {e.payload['agent_id'] for e in events}
        self.assertIn('accountant_bot', agent_ids)
        self.assertIn('sales_bot', agent_ids)
        self.assertIn('inventory_bot', agent_ids)
        self.assertIn('purchasing_bot', agent_ids)
        self.assertIn('hr_bot', agent_ids)

    def test_agent_schedules_have_recurring_type(self):
        agents = [
            AccountantBot(), SalesBot(), InventoryBot(),
            PurchasingBot(), HRBot(),
        ]
        for agent in agents:
            schedule = agent.get_schedule()
            for entry in schedule:
                self.assertEqual(entry['type'], 'recurring')

    def test_agent_ids_are_unique(self):
        ids = [
            AccountantBot().agent_id,
            SalesBot().agent_id,
            InventoryBot().agent_id,
            PurchasingBot().agent_id,
            HRBot().agent_id,
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_not_initialized_by_default(self):
        agent = AccountantBot()
        self.assertFalse(agent.validate())

    def test_shutdown_resets_state(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        self.assertTrue(agent.validate())
        agent.shutdown()
        self.assertFalse(agent._initialized)


class TestAgentRuntime(unittest.TestCase):
    """Safe execution wrapper and agent isolation tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0)
        )
        self.bus = SimulationEventBus(max_history=100)
        self.context = SimulationContext(clock=self.clock,
                                         event_bus=self.bus)
        self.context.finalize()
        self.runtime = AgentRuntime(self.context)

    def test_execute_agent_returns_result(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        result = self.runtime.execute_agent(agent)
        self.assertEqual(result['status'], 'ok')

    def test_execute_agent_emits_agent_executed(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        self.runtime.execute_agent(agent)
        events = self.bus.events_by_type('agent_executed')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload['agent_id'], 'accountant_bot')

    def test_execute_all_deterministic_order(self):
        agent_a = AccountantBot()
        agent_b = SalesBot()
        agent_a.initialize(self.context)
        agent_b.initialize(self.context)
        agents = {
            agent_b.agent_id: agent_b,
            agent_a.agent_id: agent_a,
        }
        results = self.runtime.execute_all(agents)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['agent_id'], 'accountant_bot')

    def test_failing_agent_emits_agent_failed(self):
        class FailingAccountant(AccountantBot):
            def execute(self):
                raise RuntimeError("accounting failure")

        agent = FailingAccountant()
        agent.initialize(self.context)
        self.runtime.execute_agent(agent)
        events = self.bus.events_by_type('agent_failed')
        self.assertEqual(len(events), 1)

    def test_execute_all_isolates_failures(self):
        class FailingBot(AccountantBot):
            def __init__(self):
                super().__init__()
                self._agent_id = 'failing_bot'

            @property
            def agent_id(self):
                return self._agent_id

            def execute(self):
                raise RuntimeError("bot failure")

        good = AccountantBot()
        bad = FailingBot()
        good.initialize(self.context)
        bad.initialize(self.context)
        agents = {
            good.agent_id: good,
            bad.agent_id: bad,
        }
        results = self.runtime.execute_all(agents)
        self.assertEqual(len(results), 2)
        failed = [r for r in results if r.get('status') == 'error']
        ok = [r for r in results if r.get('status') == 'ok']
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(ok), 1)

    def test_execute_empty_agents(self):
        results = self.runtime.execute_all({})
        self.assertEqual(results, [])

    def test_execute_agent_without_initialize_still_runs(self):
        agent = AccountantBot()
        result = self.runtime.execute_agent(agent)
        self.assertIn('status', result)


class TestEngineAgentCycle(unittest.TestCase):
    """Engine integration with agent registration and execution."""

    def setUp(self):
        self.engine = SimulationEngine()
        self.engine.register_agent(AccountantBot())
        self.engine.register_agent(SalesBot())

    def test_engine_has_registry(self):
        self.assertIsNotNone(self.engine.registry)

    def test_engine_has_runtime(self):
        self.assertIsNotNone(self.engine.runtime)

    def test_execute_registered_agents_before_start(self):
        self.engine.initialize()
        self.engine.start()
        results = self.engine.execute_registered_agents()
        self.assertEqual(len(results), 2)

    def test_run_agent_cycle_ticks_and_executes(self):
        self.engine.initialize()
        self.engine.start()
        cycle = self.engine.run_agent_cycle()
        self.assertIn('tick', cycle)
        self.assertIn('timestamp', cycle)
        self.assertIn('agents_executed', cycle)
        self.assertEqual(cycle['agents_executed'], 2)

    def test_run_agent_cycle_increments_tick(self):
        self.engine.initialize()
        self.engine.start()
        c1 = self.engine.run_agent_cycle()
        c2 = self.engine.run_agent_cycle()
        self.assertEqual(c2['tick'], c1['tick'] + 1)

    def test_execute_registered_agents_returns_results(self):
        self.engine.initialize()
        self.engine.start()
        results = self.engine.execute_registered_agents()
        for r in results:
            self.assertEqual(r['status'], 'ok')

    def test_empty_agents_returns_empty(self):
        engine = SimulationEngine()
        engine.initialize()
        engine.start()
        results = engine.execute_registered_agents()
        self.assertEqual(results, [])

    def test_agent_crash_does_not_crash_engine(self):
        class CrashBot(SimulationAgent):
            def __init__(self):
                super().__init__('crash_bot', 'Crash Bot')

            def initialize(self, context):
                self._context = context
                self._initialized = True

            def execute(self):
                raise RuntimeError("critical failure")

            def get_schedule(self):
                return []

            def validate(self):
                return True

        engine = SimulationEngine()
        engine.register_agent(CrashBot())
        engine.register_agent(AccountantBot())
        engine.initialize()
        engine.start()
        results = engine.execute_registered_agents()
        self.assertEqual(len(results), 2)
        failed = [r for r in results if r.get('status') == 'error']
        ok = [r for r in results if r.get('status') == 'ok']
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(ok), 1)

    def test_events_emitted_during_agent_cycle(self):
        self.engine.initialize()
        self.engine.start()
        self.engine.run_agent_cycle()
        event_types = {e.type for e in self.engine.event_bus.history}
        self.assertIn('agent_executed', event_types)

    def test_deterministic_execution_order(self):
        engine = SimulationEngine()
        engine.register_agent(AccountantBot())
        engine.register_agent(SalesBot())
        engine.register_agent(InventoryBot())
        engine.register_agent(PurchasingBot())
        engine.register_agent(HRBot())
        engine.initialize()
        engine.start()
        results = engine.execute_registered_agents()
        agent_ids = [r['agent_id'] for r in results]
        expected = [
            'accountant_bot', 'hr_bot', 'inventory_bot',
            'purchasing_bot', 'sales_bot',
        ]
        self.assertEqual(agent_ids, expected)


class TestEventEmissionLayer(unittest.TestCase):
    """Agent lifecycle event layer tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0)
        )
        self.bus = SimulationEventBus(max_history=100)
        self.context = SimulationContext(clock=self.clock,
                                         event_bus=self.bus)
        self.context.finalize()

    def test_agent_initialized_event_format(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        events = self.bus.events_by_type('agent_initialized')
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.payload['agent_id'], 'accountant_bot')
        self.assertEqual(event.payload['name'], 'Accountant Bot')
        self.assertEqual(event.timestamp, datetime(2024, 1, 1, 0, 0, 0))

    def test_agent_executed_event_format(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        runtime = AgentRuntime(self.context)
        runtime.execute_agent(agent)
        events = self.bus.events_by_type('agent_executed')
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.payload['agent_id'], 'accountant_bot')
        self.assertIn('result', event.payload)

    def test_agent_failed_event_format(self):
        class FailBot(AccountantBot):
            def execute(self):
                raise RuntimeError("fail")

        agent = FailBot()
        agent.initialize(self.context)
        runtime = AgentRuntime(self.context)
        runtime.execute_agent(agent)
        events = self.bus.events_by_type('agent_failed')
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.payload['agent_id'], 'accountant_bot')

    def test_no_business_events_generated(self):
        agent = AccountantBot()
        agent.initialize(self.context)
        runtime = AgentRuntime(self.context)
        runtime.execute_agent(agent)
        for event in self.bus.history:
            self.assertNotIn('accounting', event.type)
            self.assertNotIn('inventory', event.type)
            self.assertNotIn('sales', event.type)
            self.assertNotIn('purchase', event.type)
            self.assertNotIn('financial', event.type)

    def test_registry_event_types_in_valid_list(self):
        for event_type in ('agent_initialized', 'agent_executed',
                           'agent_failed'):
            self.assertIn(event_type,
                          SimulationEventBus.VALID_EVENT_TYPES)


class TestNoBusinessLogic(unittest.TestCase):
    """Strict isolation — zero business logic contamination."""

    def test_no_domain_imports_in_agent_shells(self):
        import ast
        import os
        agent_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'agents', 'employees'
        )
        forbidden_modules = (
            'accounting', 'inventory', 'sales', 'purchases',
            'payments', 'payroll', 'hr', 'core',
        )
        for fname in os.listdir(agent_dir):
            if not fname.endswith('.py') or fname == '__init__.py':
                continue
            fpath = os.path.join(agent_dir, fname)
            with open(fpath) as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split('.')[0]
                        self.assertNotIn(
                            mod, forbidden_modules,
                            f"{fname} imports production module '{mod}'"
                        )
                elif isinstance(node, ast.ImportFrom):
                    mod = (node.module or '').split('.')[0]
                    self.assertNotIn(
                        mod, forbidden_modules,
                        f"{fname} imports production module '{mod}'"
                    )

    def test_no_domain_imports_in_registry(self):
        import ast
        import os
        reg_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'agents', 'registry', 'registry.py'
        )
        forbidden = ('accounting', 'inventory', 'sales', 'purchases')
        with open(reg_file) as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    self.assertNotIn(mod, forbidden)
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or '').split('.')[0]
                self.assertNotIn(mod, forbidden)

    def test_no_domain_imports_in_runtime(self):
        import ast
        import os
        run_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'agents', 'runtime', 'runtime.py'
        )
        forbidden = ('accounting', 'inventory', 'sales', 'purchases')
        with open(run_file) as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    self.assertNotIn(mod, forbidden)
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or '').split('.')[0]
                self.assertNotIn(mod, forbidden)

    def test_agent_execute_returns_no_business_keys(self):
        agent = AccountantBot()
        context = SimulationContext()
        context.finalize()
        agent.initialize(context)
        result = agent.execute()
        business_keys = (
            'journal_entry', 'invoice', 'payment', 'batch',
            'stock_movement', 'account', 'transaction',
        )
        for key in business_keys:
            self.assertNotIn(key, result)

    def test_sales_bot_no_sales_logic(self):
        agent = SalesBot()
        context = SimulationContext()
        context.finalize()
        agent.initialize(context)
        result = agent.execute()
        self.assertEqual(result['message'], 'SalesBot executed tick')
        self.assertNotIn('customer', result)
        self.assertNotIn('invoice', result)

    def test_inventory_bot_no_stock_logic(self):
        agent = InventoryBot()
        context = SimulationContext()
        context.finalize()
        agent.initialize(context)
        result = agent.execute()
        self.assertEqual(result['message'],
                         'InventoryBot executed tick')
        self.assertNotIn('quantity', result)
        self.assertNotIn('batch', result)

    def test_purchasing_bot_no_purchase_logic(self):
        agent = PurchasingBot()
        context = SimulationContext()
        context.finalize()
        agent.initialize(context)
        result = agent.execute()
        self.assertEqual(result['message'],
                         'PurchasingBot executed tick')
        self.assertNotIn('supplier', result)
        self.assertNotIn('order', result)

    def test_context_properties_return_copies(self):
        agent = AccountantBot()
        context = SimulationContext(config={'secret': 'value'})
        context.finalize()
        agent.initialize(context)
        config_copy = agent.context.config
        config_copy['secret'] = 'modified'
        self.assertEqual(
            agent.context.config, {'secret': 'value'}
        )


if __name__ == '__main__':
    unittest.main()
