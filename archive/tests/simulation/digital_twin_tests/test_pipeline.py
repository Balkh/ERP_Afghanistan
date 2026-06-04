"""Tests for Digital Twin Pipeline (orchestrator + digital_twin facade)."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from collections import deque

from simulation.digital_twin.pipeline.orchestrator import DigitalTwinPipeline
from simulation.digital_twin.pipeline.digital_twin import DigitalTwin, IntegrityMatrix


# ===================================================================
# DigitalTwinPipeline
# ===================================================================

class TestDigitalTwinPipeline(unittest.TestCase):
    """DigitalTwinPipeline: STAGES, execute, error handling, status."""

    def setUp(self):
        self.engine = MagicMock()
        self.control_center = MagicMock()
        self.truth_engine = MagicMock()
        self.root_cause = MagicMock()
        self.predictive = MagicMock()
        self.recovery = MagicMock()
        self.replay = MagicMock()
        self.integrity = MagicMock()

        self.scenario = MagicMock()
        self.scenario._name = 'test_scenario'
        self.scenario._config = {'ticks': 3}

    def test_stages_constant_has_10_stages(self):
        self.assertEqual(len(DigitalTwinPipeline.STAGES), 10)
        expected = [
            'event_injection',
            'workflow_execution',
            'system_mutation',
            'truth_evaluation',
            'root_cause',
            'predictive_forecast',
            'containment_decision',
            'recovery_execution',
            'replay_verification',
            'control_center_reporting',
        ]
        self.assertEqual(DigitalTwinPipeline.STAGES, expected)

    def test_init_stores_all_components(self):
        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            control_center=self.control_center,
            truth_engine=self.truth_engine,
            root_cause=self.root_cause,
            predictive=self.predictive,
            recovery=self.recovery,
            replay=self.replay,
            integrity=self.integrity,
            stop_on_failure=False,
        )
        self.assertIs(pipeline._engine, self.engine)
        self.assertIs(pipeline._control_center, self.control_center)
        self.assertIs(pipeline._truth_engine, self.truth_engine)
        self.assertIs(pipeline._root_cause, self.root_cause)
        self.assertIs(pipeline._predictive, self.predictive)
        self.assertIs(pipeline._recovery, self.recovery)
        self.assertIs(pipeline._replay, self.replay)
        self.assertIs(pipeline._integrity, self.integrity)
        self.assertFalse(pipeline._stop_on_failure)
        self.assertIsInstance(pipeline._results, deque)
        self.assertEqual(pipeline._results.maxlen, 100)

    def test_execute_runs_through_all_stages(self):
        self.engine.run.return_value = {'ticks_executed': 3}
        self.truth_engine.verify.return_value = {
            'summary': {'total_mismatches': 0},
        }
        self.control_center.generate_dashboard_snapshot.return_value = {'status': 'ok'}
        self.control_center.get_report.return_value = {'alerts': []}

        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            control_center=self.control_center,
            truth_engine=self.truth_engine,
            root_cause=self.root_cause,
            predictive=self.predictive,
            recovery=self.recovery,
            replay=self.replay,
            stop_on_failure=True,
        )

        result = pipeline.execute(self.scenario)

        self.assertEqual(result['scenario_name'], 'test_scenario')
        self.assertEqual(len(result['stages']), 10)
        self.assertTrue(result['all_pass'])
        self.assertIn('integrity_report', result)
        self.assertGreaterEqual(result['duration_ticks'], 0)

        stage_names = [s['stage'] for s in result['stages']]
        self.assertEqual(stage_names, DigitalTwinPipeline.STAGES)

        for stage in result['stages']:
            self.assertTrue(stage['success'], f"Stage {stage['stage']} failed")

        self.engine.run.assert_called_once_with(max_ticks=3)
        self.truth_engine.verify.assert_called_once()
        self.control_center.generate_dashboard_snapshot.assert_called_once()

    def test_execute_stops_on_failure(self):
        self.engine.run.side_effect = RuntimeError('engine crash')

        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            stop_on_failure=True,
        )

        result = pipeline.execute(self.scenario)

        self.assertFalse(result['all_pass'])
        self.assertLess(len(result['stages']), 10)

        failed_stage = result['stages'][-1]
        self.assertFalse(failed_stage['success'])
        self.assertIn('engine crash', failed_stage.get('error', ''))

    def test_execute_continues_on_failure_when_stop_on_failure_false(self):
        self.engine.run.side_effect = RuntimeError('engine crash')

        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            stop_on_failure=False,
        )

        result = pipeline.execute(self.scenario)

        self.assertFalse(result['all_pass'])
        self.assertEqual(len(result['stages']), 10)

    def test_get_stage_result_returns_correct_stage(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        pipeline.execute(self.scenario)
        stage = pipeline.get_stage_result('event_injection')
        self.assertIsNotNone(stage)
        self.assertEqual(stage['stage'], 'event_injection')

    def test_get_stage_result_returns_none_for_missing(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        self.assertIsNone(pipeline.get_stage_result('nonexistent'))

    def test_get_stage_result_returns_none_before_execution(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        self.assertIsNone(pipeline.get_stage_result('event_injection'))

    def test_get_pipeline_status_before_execution(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        status = pipeline.get_pipeline_status()
        self.assertEqual(status['stages_completed'], 0)
        self.assertEqual(status['total_stages'], 10)
        self.assertTrue(status['all_pass'])
        self.assertEqual(status['last_execution'], 'none')

    def test_get_pipeline_status_after_execution(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        pipeline.execute(self.scenario)
        status = pipeline.get_pipeline_status()
        self.assertEqual(status['stages_completed'], 10)
        self.assertEqual(status['total_stages'], 10)
        self.assertEqual(status['last_execution'], 'completed')

    def test_get_execution_count(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        self.assertEqual(pipeline.get_execution_count(), 0)
        pipeline.execute(self.scenario)
        self.assertEqual(pipeline.get_execution_count(), 1)
        pipeline.execute(self.scenario)
        self.assertEqual(pipeline.get_execution_count(), 2)

    def test_clear(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        pipeline.execute(self.scenario)
        self.assertIsNotNone(pipeline._last_execution_result)
        self.assertEqual(pipeline.get_execution_count(), 1)

        pipeline.clear()
        self.assertIsNone(pipeline._last_execution_result)
        self.assertEqual(pipeline.get_execution_count(), 0)
        self.assertEqual(len(pipeline._results), 0)

    def test_execute_with_minimal_config_only_engine(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        self.engine.run.return_value = {'ticks_executed': 5}
        result = pipeline.execute(self.scenario)

        self.assertEqual(len(result['stages']), 10)
        self.assertTrue(result['all_pass'])

        skipped = [s for s in result['stages'] if 'skipped' in s.get('output_summary', '')]
        self.assertGreater(len(skipped), 0)

    def test_truth_evaluation_skipped_when_no_truth_engine(self):
        pipeline = DigitalTwinPipeline(engine=self.engine)
        result = pipeline.execute(self.scenario)
        te_stage = pipeline.get_stage_result('truth_evaluation')
        self.assertIsNotNone(te_stage)
        self.assertTrue(te_stage['success'])
        self.assertIn('skipped', te_stage['output_summary'])

    def test_root_cause_skipped_when_no_mismatches(self):
        self.truth_engine.verify.return_value = {
            'summary': {'total_mismatches': 0},
        }
        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            truth_engine=self.truth_engine,
            root_cause=self.root_cause,
        )
        self.engine.run.return_value = {'ticks_executed': 3}
        pipeline.execute(self.scenario)
        rc_stage = pipeline.get_stage_result('root_cause')
        self.assertIsNotNone(rc_stage)
        self.assertTrue(rc_stage['success'])
        self.assertIn('skipped', rc_stage['output_summary'])
        self.root_cause.analyze.assert_not_called()

    def test_recovery_execution_skipped_when_no_containment(self):
        pipeline = DigitalTwinPipeline(
            engine=self.engine,
            recovery=self.recovery,
        )
        pipeline.execute(self.scenario)
        re_stage = pipeline.get_stage_result('recovery_execution')
        self.assertIsNotNone(re_stage)
        self.assertTrue(re_stage['success'])
        self.assertIn('skipped', re_stage['output_summary'])


# ===================================================================
# DigitalTwin
# ===================================================================

class TestDigitalTwin(unittest.TestCase):
    """DigitalTwin facade: registration, execution, reporting, summary."""

    def setUp(self):
        self.config = {'ticks': 3}
        self.twin = DigitalTwin(config=self.config)

        self.scenario = MagicMock()
        self.scenario._name = 'order_fulfillment'
        self.scenario._config = {'ticks': 3}
        self.scenario.setup = MagicMock()

    def test_init_stores_config_and_creates_bounded_deque(self):
        twin = DigitalTwin(config={'key': 'val'})
        self.assertEqual(twin._config, {'key': 'val'})
        self.assertIsInstance(twin._results, deque)
        self.assertEqual(twin._results.maxlen, 200)
        self.assertEqual(twin._scenarios, {})

    def test_register_scenario_adds_scenario(self):
        result = self.twin.register_scenario(self.scenario)
        self.assertTrue(result)
        self.assertIn('order_fulfillment', self.twin._scenarios)

    def test_register_scenario_returns_false_for_missing_name(self):
        bad_scenario = MagicMock()
        bad_scenario._name = ''
        result = self.twin.register_scenario(bad_scenario)
        self.assertFalse(result)

    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationEngine')
    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationContext')
    def test_run_scenario_with_mock_scenario(self, mock_context, mock_engine):
        self.twin.register_scenario(self.scenario)

        mock_engine_instance = MagicMock()
        mock_engine_instance.run.return_value = {'ticks_executed': 3}
        mock_engine.return_value = mock_engine_instance

        result = self.twin.run_scenario('order_fulfillment')

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('scenario_name'), 'order_fulfillment')
        self.assertIn('stages', result)
        self.assertIn('all_pass', result)

    def test_run_scenario_returns_error_for_missing_scenario(self):
        result = self.twin.run_scenario('nonexistent')
        self.assertFalse(result.get('success', True))
        self.assertIn('not found', result.get('error', ''))

    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationEngine')
    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationContext')
    def test_get_report_returns_stored_result(self, mock_context, mock_engine):
        self.twin.register_scenario(self.scenario)

        mock_engine_instance = MagicMock()
        mock_engine_instance.run.return_value = {'ticks_executed': 3}
        mock_engine.return_value = mock_engine_instance

        self.twin.run_scenario('order_fulfillment')

        report = self.twin.get_report('order_fulfillment')
        self.assertIsNotNone(report)
        self.assertEqual(report.get('scenario_name'), 'order_fulfillment')

    def test_get_report_returns_none_for_missing(self):
        self.assertIsNone(self.twin.get_report('nonexistent'))

    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationEngine')
    @patch('simulation.digital_twin.pipeline.digital_twin.SimulationContext')
    def test_get_summary_with_multiple_scenarios(self, mock_context, mock_engine):
        mock_engine_instance = MagicMock()
        mock_engine_instance.run.return_value = {'ticks_executed': 3}
        mock_engine.return_value = mock_engine_instance

        s1 = MagicMock()
        s1._name = 'scenario_a'
        s1._config = {'ticks': 3}
        self.twin.register_scenario(s1)

        s2 = MagicMock()
        s2._name = 'scenario_b'
        s2._config = {'ticks': 5}
        self.twin.register_scenario(s2)

        self.twin.run_scenario('scenario_a')
        self.twin.run_scenario('scenario_b')

        summary = self.twin.get_summary()
        self.assertEqual(summary['total'], 2)
        self.assertIn('passed', summary)
        self.assertIn('failed', summary)
        self.assertIn('pass_rate', summary)
        self.assertEqual(len(summary['scenarios']), 2)

    def test_get_summary_with_no_results(self):
        summary = self.twin.get_summary()
        self.assertEqual(summary['total'], 0)
        self.assertEqual(summary['passed'], 0)
        self.assertEqual(summary['failed'], 0)
        self.assertEqual(summary['pass_rate'], 0.0)
        self.assertEqual(summary['scenarios'], [])

    def test_validate_system_returns_integrity_report(self):
        result = self.twin.validate_system()
        self.assertIsInstance(result, dict)
        self.assertIn('passed', result)
        self.assertIn('checks', result)
        self.assertIn('violations', result)

    def test_clear(self):
        self.twin.register_scenario(self.scenario)
        self.twin._results.append({'scenario_name': 'test'})
        self.assertEqual(len(self.twin._results), 1)
        self.assertEqual(len(self.twin._scenarios), 1)

        self.twin.clear()
        self.assertEqual(len(self.twin._results), 0)
        self.assertEqual(len(self.twin._scenarios), 0)
        self.assertIsNone(self.twin._pipeline)
        self.assertIsNone(self.twin._engine)


# ===================================================================
# IntegrityMatrix
# ===================================================================

class TestIntegrityMatrix(unittest.TestCase):
    """IntegrityMatrix: validate_all with various state inputs."""

    def setUp(self):
        self.matrix = IntegrityMatrix()

    def test_validate_all_with_empty_state(self):
        result = self.matrix.validate_all({})
        self.assertIsInstance(result, dict)
        self.assertIn('passed', result)
        self.assertIn('checks', result)
        self.assertIn('violations', result)

    def test_validate_all_with_clean_state(self):
        state = {
            'batches': [{'batch_id': 'B001', 'remaining_quantity': 10}],
            'movements': [{'batch_id': 'B001', 'direction': 'IN', 'tick': 1}],
            'journal_entries': [{'entry_id': 'J001', 'debit': 100.0, 'credit': 100.0, 'tick': 1}],
            'transactions': [{'txn_id': 'T001', 'status': 'committed', 'steps': [{'completed': True}], 'entries': [{'posted': True}]}],
            'events': [{'event_id': 'E001', 'type': 'sale', 'tick': 1}],
        }
        result = self.matrix.validate_all(state)
        self.assertTrue(result['passed'])

    def test_validate_all_with_violations(self):
        state = {
            'batches': [{'batch_id': 'B001', 'remaining_quantity': -5}],
            'journal_entries': [{'entry_id': 'J001', 'debit': 100.0, 'credit': 50.0, 'tick': 1}],
        }
        result = self.matrix.validate_all(state)
        self.assertFalse(result['passed'])
        self.assertGreater(len(result['violations']), 0)

    def test_validate_all_exception_safety(self):
        result = self.matrix.validate_all(None)
        self.assertFalse(result['passed'])
        self.assertIn('violations', result)


if __name__ == '__main__':
    unittest.main()
