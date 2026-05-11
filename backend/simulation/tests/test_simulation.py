"""
Tests for ERP Simulation Core Foundation.
Deterministic tests only. No random timing-based assertions.
"""
import unittest
from datetime import datetime, timedelta

from simulation.clocks.clock import VirtualClock
from simulation.events.bus import SimulationEventBus
from simulation.metrics.collector import SimulationMetricsCollector
from simulation.context.context import SimulationContext
from simulation.scheduler.scheduler import SimulationScheduler
from simulation.agents.agent import SimulationAgent
from simulation.engine.engine import SimulationEngine


class TestVirtualClock(unittest.TestCase):
    """Deterministic clock progression tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0),
            tick_interval_minutes=1
        )

    def test_initial_state(self):
        self.assertEqual(self.clock.now(), datetime(2024, 1, 1, 0, 0, 0))
        self.assertEqual(self.clock.tick_count, 0)
        self.assertFalse(self.clock.is_running)
        self.assertEqual(self.clock.tick_interval, timedelta(minutes=1))

    def test_tick_progression(self):
        self.clock.start()
        t1 = self.clock.tick()
        self.assertEqual(t1, datetime(2024, 1, 1, 0, 1, 0))
        self.assertEqual(self.clock.tick_count, 1)

        t2 = self.clock.tick()
        self.assertEqual(t2, datetime(2024, 1, 1, 0, 2, 0))
        self.assertEqual(self.clock.tick_count, 2)

    def test_advance_minutes(self):
        self.clock.advance(30)
        self.assertEqual(self.clock.now(), datetime(2024, 1, 1, 0, 30, 0))

    def test_advance_negative_raises(self):
        with self.assertRaises(ValueError):
            self.clock.advance(-5)

    def test_reset(self):
        self.clock.advance(60)
        self.assertEqual(self.clock.now(), datetime(2024, 1, 1, 1, 0, 0))
        self.clock.reset()
        self.assertEqual(self.clock.now(), datetime(2024, 1, 1, 0, 0, 0))
        self.assertEqual(self.clock.tick_count, 0)
        self.assertFalse(self.clock.is_running)

    def test_elapsed(self):
        self.clock.advance(120)
        self.assertEqual(self.clock.elapsed(), timedelta(hours=2))

    def test_start_stop(self):
        self.clock.start()
        self.assertTrue(self.clock.is_running)
        self.clock.stop()
        self.assertFalse(self.clock.is_running)

    def test_tick_starts_automatically(self):
        self.assertFalse(self.clock.is_running)
        self.clock.tick()
        self.assertTrue(self.clock.is_running)

    def test_different_tick_interval(self):
        clock = VirtualClock(tick_interval_minutes=5)
        clock.advance(5)
        self.assertEqual(clock.now(), datetime(2024, 1, 1, 0, 5, 0))

    def test_deterministic_same_start(self):
        c1 = VirtualClock(start_datetime=datetime(2024, 6, 15, 10, 30, 0))
        c2 = VirtualClock(start_datetime=datetime(2024, 6, 15, 10, 30, 0))
        c1.tick()
        c2.tick()
        self.assertEqual(c1.now(), c2.now())

    def test_set_time(self):
        new_time = datetime(2025, 12, 25, 8, 0, 0)
        self.clock.set_time(new_time)
        self.assertEqual(self.clock.now(), new_time)


class TestSimulationEventBus(unittest.TestCase):
    """Event bus publish/subscribe/history tests."""

    def setUp(self):
        self.bus = SimulationEventBus(max_history=100)
        self.received = []

    def handler(self, event):
        self.received.append(event)

    def test_publish_subscribe(self):
        self.bus.subscribe('test_event', self.handler)
        self.bus.publish('test_event', datetime(2024, 1, 1, 0, 0, 0),
                         {'key': 'value'})
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0].type, 'test_event')
        self.assertEqual(self.received[0].payload, {'key': 'value'})

    def test_bounded_history(self):
        bus = SimulationEventBus(max_history=5)
        for i in range(10):
            bus.publish('evt', datetime(2024, 1, 1, 0, i, 0))
        self.assertLessEqual(bus.event_count, 5)

    def test_exception_isolation(self):
        def failing_handler(event):
            raise RuntimeError("handler failed")

        self.bus.subscribe('fail_event', failing_handler)
        self.bus.subscribe('fail_event', self.handler)
        self.bus.publish('fail_event', datetime(2024, 1, 1, 0, 0, 0))
        self.assertEqual(len(self.received), 1)

    def test_unsubscribe(self):
        self.bus.subscribe('evt', self.handler)
        self.bus.unsubscribe('evt', self.handler)
        self.bus.publish('evt', datetime(2024, 1, 1, 0, 0, 0))
        self.assertEqual(len(self.received), 0)

    def test_event_history_in_order(self):
        ts1 = datetime(2024, 1, 1, 0, 0, 0)
        ts2 = datetime(2024, 1, 1, 0, 1, 0)
        self.bus.publish('a', ts1)
        self.bus.publish('b', ts2)
        history = self.bus.history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].type, 'a')
        self.assertEqual(history[1].type, 'b')

    def test_events_by_type(self):
        self.bus.publish('type_a', datetime(2024, 1, 1, 0, 0, 0))
        self.bus.publish('type_b', datetime(2024, 1, 1, 0, 0, 0))
        self.bus.publish('type_a', datetime(2024, 1, 1, 0, 0, 0))
        events_a = self.bus.events_by_type('type_a')
        self.assertEqual(len(events_a), 2)

    def test_clear(self):
        self.bus.publish('evt', datetime(2024, 1, 1, 0, 0, 0))
        self.bus.clear()
        self.assertEqual(self.bus.event_count, 0)
        self.assertEqual(len(self.bus.history), 0)

    def test_immutable_payload(self):
        payload = {'original': 'data'}
        self.bus.publish('evt', datetime(2024, 1, 1, 0, 0, 0), payload)
        payload['modified'] = 'yes'
        self.assertEqual(
            self.bus.history[0].payload,
            {'original': 'data'}
        )

    def test_valid_event_types_published(self):
        for event_type in SimulationEventBus.VALID_EVENT_TYPES:
            self.bus.publish(event_type, datetime(2024, 1, 1, 0, 0, 0))
        types_found = {e.type for e in self.bus.history}
        self.assertEqual(types_found, set(
            SimulationEventBus.VALID_EVENT_TYPES
        ))


class TestSimulationMetricsCollector(unittest.TestCase):
    """Metrics collector bounded-memory and aggregation tests."""

    def setUp(self):
        self.metrics = SimulationMetricsCollector(max_metric_history=100)

    def test_increment(self):
        self.metrics.increment('ops')
        self.assertEqual(self.metrics.get_counter('ops'), 1)
        self.metrics.increment('ops', 5)
        self.assertEqual(self.metrics.get_counter('ops'), 6)

    def test_latency_recording(self):
        self.metrics.record_latency('tick', 0.1)
        self.metrics.record_latency('tick', 0.2)
        stats = self.metrics.get_latency_stats('tick')
        self.assertEqual(stats['count'], 2)
        self.assertAlmostEqual(stats['avg'], 0.15)
        self.assertAlmostEqual(stats['min'], 0.1)
        self.assertAlmostEqual(stats['max'], 0.2)
        self.assertAlmostEqual(stats['sum'], 0.3)

    def test_latency_empty(self):
        stats = self.metrics.get_latency_stats('nonexistent')
        self.assertEqual(stats['count'], 0)

    def test_snapshot(self):
        self.metrics.increment('a', 10)
        self.metrics.record_latency('op', 0.5)
        snap = self.metrics.snapshot()
        self.assertEqual(snap['counters']['a'], 10)
        self.assertIn('op', snap['latencies'])

    def test_total_operations(self):
        self.metrics.increment('a', 3)
        self.metrics.increment('b', 7)
        self.assertEqual(self.metrics.total_operations, 10)

    def test_reset(self):
        self.metrics.increment('a', 100)
        self.metrics.reset()
        self.assertEqual(self.metrics.total_operations, 0)
        self.assertEqual(len(self.metrics.snapshot()['counters']), 0)

    def test_timeline_bounded(self):
        metrics = SimulationMetricsCollector(max_metric_history=10)
        for i in range(20):
            metrics.record_timeline('val', i)
        snap = metrics.snapshot()
        self.assertLessEqual(snap['timeline_count'], 10)

    def test_counters_property(self):
        self.metrics.increment('x', 5)
        self.metrics.increment('y', 3)
        self.assertEqual(self.metrics.counters, {'x': 5, 'y': 3})

    def test_concurrent_safety(self):
        for i in range(100):
            self.metrics.increment('concurrent')
        self.assertEqual(self.metrics.get_counter('concurrent'), 100)


class TestSimulationScheduler(unittest.TestCase):
    """Deterministic scheduler execution ordering tests."""

    def setUp(self):
        self.clock = VirtualClock(
            start_datetime=datetime(2024, 1, 1, 0, 0, 0),
            tick_interval_minutes=1
        )
        self.bus = SimulationEventBus(max_history=100)
        self.scheduler = SimulationScheduler(self.clock, self.bus)
        self.executed = []

    def record(self):
        self.executed.append(self.clock.now())

    def test_one_time_schedule(self):
        self.scheduler.one_time(self.record, delay_minutes=5)
        self.clock.advance(5)
        results = self.scheduler.execute_due()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'executed')
        self.assertEqual(len(self.executed), 1)

    def test_one_time_not_due(self):
        self.scheduler.one_time(self.record, delay_minutes=5)
        self.clock.advance(3)
        results = self.scheduler.execute_due()
        self.assertEqual(len(results), 0)
        self.assertEqual(len(self.executed), 0)

    def test_recurring_schedule(self):
        self.scheduler.recurring(self.record, interval_minutes=3)
        self.clock.advance(3)
        results = self.scheduler.execute_due()
        self.assertEqual(len(results), 1)
        self.assertEqual(len(self.executed), 1)
        self.clock.advance(3)
        results = self.scheduler.execute_due()
        self.assertEqual(len(results), 1)
        self.assertEqual(len(self.executed), 2)

    def test_cancellation(self):
        aid = self.scheduler.one_time(self.record, delay_minutes=5)
        self.assertTrue(self.scheduler.cancel(aid))
        self.clock.advance(5)
        results = self.scheduler.execute_due()
        self.assertEqual(len(results), 0)

    def test_cancel_nonexistent(self):
        self.assertFalse(self.scheduler.cancel('nonexistent'))

    def test_execution_order_by_time(self):
        results_list = []
        self.scheduler.one_time(
            lambda: results_list.append(1), delay_minutes=10
        )
        self.scheduler.one_time(
            lambda: results_list.append(2), delay_minutes=5
        )
        self.clock.advance(10)
        self.scheduler.execute_due()
        self.assertEqual(results_list, [2, 1])

    def test_pending_count(self):
        self.scheduler.one_time(self.record, delay_minutes=5)
        self.scheduler.one_time(self.record, delay_minutes=10)
        self.assertEqual(self.scheduler.pending_count, 2)
        self.clock.advance(5)
        self.scheduler.execute_due()
        self.assertEqual(self.scheduler.pending_count, 1)

    def test_exception_isolation(self):
        def failing():
            raise RuntimeError("scheduled failure")

        self.scheduler.one_time(failing, delay_minutes=1)
        self.scheduler.one_time(self.record, delay_minutes=1)
        self.clock.advance(1)
        results = self.scheduler.execute_due()
        failed = [r for r in results if r['status'] == 'failed']
        executed = [r for r in results if r['status'] == 'executed']
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(executed), 1)

    def test_clear(self):
        self.scheduler.one_time(self.record, delay_minutes=5)
        self.scheduler.clear()
        self.assertEqual(self.scheduler.pending_count, 0)

    def test_action_id_uniqueness(self):
        a1 = self.scheduler.one_time(self.record, delay_minutes=1)
        a2 = self.scheduler.one_time(self.record, delay_minutes=1)
        self.assertNotEqual(a1, a2)


class TestSimulationContext(unittest.TestCase):
    """Context access and lifecycle tests."""

    def setUp(self):
        self.clock = VirtualClock()
        self.bus = SimulationEventBus()
        self.metrics = SimulationMetricsCollector()
        self.context = SimulationContext(
            clock=self.clock,
            event_bus=self.bus,
            metrics=self.metrics,
            config={'env': 'test'},
        )

    def test_all_components_accessible(self):
        self.assertIs(self.context.clock, self.clock)
        self.assertIs(self.context.event_bus, self.bus)
        self.assertIs(self.context.metrics, self.metrics)
        self.assertIsNotNone(self.context.scheduler)

    def test_config_copy(self):
        cfg = self.context.config
        cfg['extra'] = True
        self.assertNotIn('extra', self.context.config)

    def test_scheduler_uses_given_clock(self):
        self.assertIs(self.context.scheduler._clock, self.clock)

    def test_scheduler_uses_given_bus(self):
        self.assertIs(self.context.scheduler._event_bus, self.bus)

    def test_reset(self):
        self.context.clock.advance(10)
        self.context.event_bus.publish('evt', datetime(2024, 1, 1, 0, 0, 0))
        self.context.metrics.increment('ops')
        self.context.scheduler.one_time(lambda: None, delay_minutes=1)
        self.context.reset()
        self.assertEqual(self.context.clock.tick_count, 0)
        self.assertEqual(self.context.event_bus.event_count, 0)
        self.assertEqual(self.context.metrics.total_operations, 0)
        self.assertEqual(self.context.scheduler.pending_count, 0)

    def test_finalize_does_not_prevent_read(self):
        self.context.finalize()
        self.assertIsNotNone(self.context.clock)


class TestableAgent(SimulationAgent):
    """Concrete agent for testing purposes."""

    def __init__(self, agent_id='test_agent', name='Test Agent',
                 schedule=None):
        super().__init__(agent_id, name)
        self._schedule = schedule or [
            {'type': 'recurring', 'interval_minutes': 5}
        ]
        self.execute_count = 0

    def initialize(self, context):
        self._context = context
        self._initialized = True

    def execute(self):
        self.execute_count += 1
        return {'status': 'ok', 'agent_id': self.agent_id}

    def get_schedule(self):
        return self._schedule

    def validate(self):
        return self._initialized


class TestSimulationAgent(unittest.TestCase):
    """Agent contract and lifecycle tests."""

    def test_abstract_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            SimulationAgent('a', 'b')

    def test_concrete_agent(self):
        agent = TestableAgent()
        self.assertEqual(agent.agent_id, 'test_agent')
        self.assertEqual(agent.name, 'Test Agent')

    def test_initialize_and_execute(self):
        agent = TestableAgent()
        clock = VirtualClock()
        context = SimulationContext(clock=clock)
        agent.initialize(context)
        self.assertTrue(agent.validate())
        result = agent.execute()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(agent.execute_count, 1)

    def test_safe_execute_wraps_exception(self):
        class FailingAgent(TestableAgent):
            def execute(self):
                raise RuntimeError("agent error")

        agent = FailingAgent()
        result = agent.safe_execute()
        self.assertEqual(result['status'], 'error')

    def test_shutdown(self):
        agent = TestableAgent()
        context = SimulationContext()
        agent.initialize(context)
        self.assertTrue(agent.validate())
        agent.shutdown()
        self.assertFalse(agent._initialized)

    def test_get_schedule(self):
        agent = TestableAgent(schedule=[
            {'type': 'one_time', 'delay_minutes': 10}
        ])
        schedule = agent.get_schedule()
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]['type'], 'one_time')


class TestSimulationEngine(unittest.TestCase):
    """Engine lifecycle and orchestration tests."""

    def setUp(self):
        self.engine = SimulationEngine(config={'max_ticks': 5})

    def test_initial_state_created(self):
        self.assertEqual(self.engine.state, SimulationEngine.STATE_CREATED)

    def test_initialize_transitions(self):
        self.engine.initialize()
        self.assertEqual(self.engine.state, SimulationEngine.STATE_INITIALIZED)

    def test_start_transitions(self):
        self.engine.start()
        self.assertEqual(self.engine.state, SimulationEngine.STATE_RUNNING)

    def test_stop_transitions(self):
        self.engine.start()
        self.engine.stop()
        self.assertEqual(self.engine.state, SimulationEngine.STATE_STOPPED)

    def test_execute_tick_requires_running(self):
        with self.assertRaises(RuntimeError):
            self.engine.execute_tick()

    def test_execute_tick(self):
        self.engine.start()
        result = self.engine.execute_tick()
        self.assertEqual(result['tick'], 1)
        self.assertIn('actions_executed', result)
        self.assertIn('latency_seconds', result)
        self.assertGreaterEqual(result['latency_seconds'], 0)

    def test_register_agent_and_initialize(self):
        agent = TestableAgent(agent_id='agent1', name='Agent 1')
        self.engine.register_agent(agent)
        self.engine.initialize()
        self.assertIn('agent1', self.engine.agents)

    def test_register_agent_after_init_raises(self):
        self.engine.initialize()
        agent = TestableAgent()
        with self.assertRaises(RuntimeError):
            self.engine.register_agent(agent)

    def test_run_executes_ticks(self):
        agent = TestableAgent(agent_id='a1')
        self.engine.register_agent(agent)
        result = self.engine.run(max_ticks=3)
        self.assertEqual(result['ticks_executed'], 3)

    def test_run_without_max_ticks_raises(self):
        engine = SimulationEngine()
        with self.assertRaises(ValueError):
            engine.run()

    def test_event_bus_has_lifecycle_events(self):
        self.engine.start()
        self.engine.stop()
        types = [e.type for e in self.engine.event_bus.history]
        self.assertIn('simulation_started', types)
        self.assertIn('simulation_stopped', types)

    def test_collect_metrics(self):
        self.engine.start()
        self.engine.execute_tick()
        metrics = self.engine.collect_metrics()
        self.assertIn('counters', metrics)
        self.assertIn('latencies', metrics)

    def test_reset_engine(self):
        agent = TestableAgent(agent_id='a1')
        self.engine.register_agent(agent)
        self.engine.initialize()
        self.engine.reset()
        self.assertEqual(self.engine.state, SimulationEngine.STATE_CREATED)
        self.assertEqual(len(self.engine.agents), 0)

    def test_multiple_ticks(self):
        self.engine.start()
        r1 = self.engine.execute_tick()
        r2 = self.engine.execute_tick()
        self.assertEqual(r2['tick'], 2)
        self.assertGreater(r2['timestamp'], r1['timestamp'])

    def test_agent_schedule_registered(self):
        agent = TestableAgent(
            agent_id='sched_agent',
            schedule=[{'type': 'recurring', 'interval_minutes': 2}]
        )
        self.engine.register_agent(agent)
        self.engine.initialize()
        self.assertGreater(self.engine.scheduler.pending_count, 0)

    def test_register_scenario(self):
        self.engine.register_scenario('test_scenario', {'data': 42})
        self.engine.initialize()
        self.engine.start()
        self.engine.stop()
        events = self.engine.event_bus.events_by_type(
            'scenario_registered'
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload['scenario_id'],
                         'test_scenario')


class TestIntegrationComposition(unittest.TestCase):
    """Full integration test of all components working together."""

    def test_deterministic_execution(self):
        agent = TestableAgent(
            agent_id='det_agent',
            schedule=[{'type': 'recurring', 'interval_minutes': 1}]
        )
        engine = SimulationEngine()
        engine.register_agent(agent)
        engine.run(max_ticks=5)
        self.assertEqual(agent.execute_count, 5)

    def test_event_flow_through_system(self):
        agent = TestableAgent(agent_id='evt_agent')
        engine = SimulationEngine()
        engine.register_agent(agent)
        engine.run(max_ticks=3)
        event_types = {e.type for e in engine.event_bus.history}
        self.assertIn('simulation_started', event_types)
        self.assertIn('simulation_stopped', event_types)
        self.assertIn('tick_executed', event_types)

    def test_metrics_recorded(self):
        agent = TestableAgent(agent_id='m_agent')
        engine = SimulationEngine()
        engine.register_agent(agent)
        engine.run(max_ticks=3)
        snap = engine.collect_metrics()
        self.assertEqual(snap['counters']['ticks_executed'], 3)

    def test_deterministic_idempotent_reset(self):
        engine = SimulationEngine()
        engine.run(max_ticks=2)
        snap1 = engine.collect_metrics()
        engine.reset()
        agent = TestableAgent(agent_id='a')
        engine.register_agent(agent)
        engine.run(max_ticks=2)
        snap2 = engine.collect_metrics()
        self.assertEqual(
            snap1['counters']['ticks_executed'],
            snap2['counters']['ticks_executed']
        )

    def test_clock_scheduler_alignment(self):
        clock = VirtualClock(
            start_datetime=datetime(2024, 6, 1, 8, 0, 0),
            tick_interval_minutes=5
        )
        bus = SimulationEventBus()
        scheduler = SimulationScheduler(clock, bus)
        results = []
        scheduler.recurring(lambda: results.append(clock.now()),
                            interval_minutes=10)
        for _ in range(4):
            clock.tick()
            scheduler.execute_due()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], datetime(2024, 6, 1, 8, 10, 0))
        self.assertEqual(results[1], datetime(2024, 6, 1, 8, 20, 0))

    def test_no_production_interference(self):
        import simulation
        mod_path = simulation.__path__[0]
        self.assertNotIn('inventory', mod_path)
        self.assertNotIn('accounting', mod_path)
        self.assertNotIn('sales', mod_path)
        self.assertNotIn('purchases', mod_path)
        self.assertNotIn('payments', mod_path)
        self.assertNotIn('payroll', mod_path)


class TestTruthEngineIntegration(unittest.TestCase):
    """Tests TruthEngine wiring into SimulationEngine as passive hook."""

    def test_truth_engine_disabled_by_default(self):
        engine = SimulationEngine()
        self.assertIsNone(engine.truth_engine)

    def test_truth_engine_enabled_via_config(self):
        engine = SimulationEngine(
            config={'enable_truth_engine': True}
        )
        self.assertIsNotNone(engine.truth_engine)

    def test_truth_engine_setter(self):
        from simulation.truth_engine.engine import TruthEngine
        engine = SimulationEngine()
        te = TruthEngine()
        engine.truth_engine = te
        self.assertIs(engine.truth_engine, te)

    def test_truth_engine_executes_passively(self):
        from simulation.agents.employees.sales_bot import SalesBot
        from simulation.workflows.definitions.sales_workflow import (
            create_sales_workflow,
        )
        engine = SimulationEngine(
            config={
                'enable_truth_engine': True,
                'max_ticks': 3,
            }
        )
        engine.register_agent(SalesBot())
        engine.orchestrator.register_workflow(create_sales_workflow())
        engine.register_scenario('test_scenario', {'name': 'test'})
        engine.run(max_ticks=3)
        self.assertIsNotNone(engine.truth_engine)
        self.assertIsNotNone(engine.truth_engine.last_formatted_report)
        report = engine.truth_engine.last_formatted_report
        self.assertEqual(report['scenario_id'], 'test_scenario')

    def test_truth_engine_verify_returns_report(self):
        from simulation.truth_engine.engine import TruthEngine
        te = TruthEngine()
        from datetime import datetime
        result = te.verify(
            scenario_id='test',
            tick=1,
            timestamp=datetime(2024, 1, 1),
            event_history=[],
            workflow_completions={'sales_workflow': 0},
            agent_executions={},
        )
        self.assertEqual(result['scenario_id'], 'test')
        self.assertEqual(result['tick'], 1)
        self.assertIn('summary', result)
        self.assertIn('scores', result['summary'])
        self.assertEqual(result['summary']['total_mismatches'], 0)

    def test_truth_engine_snapshot_stored(self):
        from simulation.truth_engine.engine import TruthEngine
        te = TruthEngine()
        from datetime import datetime
        te.verify('s1', 1, datetime(2024, 1, 1), [], {}, {})
        self.assertGreater(te.snapshot_manager.get_snapshot_count(), 0)

    def test_truth_engine_exception_does_not_crash_engine(self):
        engine = SimulationEngine(
            config={'enable_truth_engine': True}
        )
        from unittest.mock import patch
        with patch.object(
            engine.truth_engine, 'verify',
            side_effect=RuntimeError('expected test error')
        ):
            engine.register_agent(TestableAgent(agent_id='crash_test'))
            engine.run(max_ticks=2)
            self.assertEqual(engine.clock.tick_count, 2)

    def test_reset_clears_truth_engine(self):
        engine = SimulationEngine(
            config={'enable_truth_engine': True}
        )
        self.assertIsNotNone(engine.truth_engine)
        engine.reset()
        self.assertIsNone(engine.truth_engine)


if __name__ == '__main__':
    unittest.main()
