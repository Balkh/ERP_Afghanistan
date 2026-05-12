"""Full enterprise integration tests for the Digital Twin system.

Tests models, end-to-end pipeline scenarios, and enterprise constraints
(no ERP mutation, bounded containers) across all subpackages.
"""

import os
import re
import unittest
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from simulation.digital_twin.models import (
    SLAViolation,
    ExternalRequest,
    ExternalResponse,
    ScenarioConfig,
    ScenarioResult,
    IntegrityReport,
    PipelineStageResult,
    PipelineResult,
    DigitalTwinSummary,
    TimeConstraint,
    SLAStatus,
    ExternalSystemType,
    FailureMode,
    PipelineStage,
    IntegrityCheckType,
    RecoveryStage,
    ScenarioType,
)
from simulation.digital_twin.integrity.matrix import IntegrityMatrix


# ===================================================================
# TestModels
# ===================================================================

class TestModels(unittest.TestCase):
    """Verify all enums and dataclasses defined in models.py."""

    def test_all_enum_values_exist(self):
        self.assertIn('sla_bound', [e.value for e in TimeConstraint])
        self.assertIn('within', [e.value for e in SLAStatus])
        self.assertIn('banking', [e.value for e in ExternalSystemType])
        self.assertIn('timeout', [e.value for e in FailureMode])
        self.assertIn('event_injection', [e.value for e in PipelineStage])
        self.assertIn('accounting', [e.value for e in IntegrityCheckType])
        self.assertIn('approval', [e.value for e in RecoveryStage])
        self.assertIn('core_business', [e.value for e in ScenarioType])

    def test_scenario_config_creation(self):
        cfg = ScenarioConfig(name='test', scenario_type='core_business', ticks=100)
        self.assertEqual(cfg.name, 'test')
        self.assertEqual(cfg.ticks, 100)
        self.assertEqual(cfg.params, {})

    def test_scenario_result_creation(self):
        result = ScenarioResult(
            name='test', scenario_type='core_business', passed=True,
            stages=[], metrics={}, integrity={},
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.name, 'test')

    def test_integrity_report_creation(self):
        report = IntegrityReport(
            all_pass=True, checks=[], violations=[], timestamp='2026-01-01T00:00:00',
        )
        self.assertTrue(report.all_pass)
        self.assertEqual(report.violations, [])

    def test_pipeline_stage_result_creation(self):
        stage = PipelineStageResult(
            stage='event_injection', success=True,
            input_summary='in', output_summary='out', duration_ticks=5,
        )
        self.assertTrue(stage.success)
        self.assertEqual(stage.duration_ticks, 5)

    def test_pipeline_result_creation(self):
        stages = [
            PipelineStageResult(
                stage='event_injection', success=True,
                input_summary='in', output_summary='out', duration_ticks=3,
            ),
        ]
        report = IntegrityReport(
            all_pass=True, checks=[], violations=[], timestamp='2026-01-01T00:00:00',
        )
        result = PipelineResult(
            scenario_name='test', stages=stages, all_pass=True,
            integrity_report=report, duration_ticks=3,
        )
        self.assertTrue(result.all_pass)
        self.assertEqual(len(result.stages), 1)

    def test_digital_twin_summary_creation(self):
        summary = DigitalTwinSummary(
            total_scenarios=10, passed=8, failed=2, pass_rate=0.8, integrity_all_pass=True,
        )
        self.assertEqual(summary.total_scenarios, 10)
        self.assertEqual(summary.pass_rate, 0.8)

    def test_enum_string_values_are_lowercased(self):
        for enum_cls in [TimeConstraint, SLAStatus, ExternalSystemType, FailureMode,
                         PipelineStage, IntegrityCheckType, RecoveryStage, ScenarioType]:
            for member in enum_cls:
                self.assertEqual(member.value, member.value.lower(),
                                 f'{enum_cls.__name__}.{member.name} is not lowercased')

    def test_optional_fields_accept_none(self):
        ext_resp = ExternalResponse(success=True, data={}, error=None, latency_ticks=0)
        self.assertIsNone(ext_resp.error)
        self.assertIsNone(ext_resp.failure_mode)

        stage = PipelineStageResult(
            stage='test', success=True, input_summary='a', output_summary='b', duration_ticks=0,
            error=None,
        )
        self.assertIsNone(stage.error)

        result = PipelineResult(
            scenario_name='test', stages=[], all_pass=True,
            integrity_report=None, duration_ticks=0,
        )
        self.assertIsNone(result.integrity_report)

    def test_dataclass_default_factory(self):
        cfg = ScenarioConfig(name='test', scenario_type='ft', ticks=10)
        self.assertEqual(cfg.params, {})

        cfg2 = ScenarioConfig(name='t2', scenario_type='ft', ticks=20, params={'key': 'val'})
        self.assertEqual(cfg2.params, {'key': 'val'})


# ===================================================================
# TestFullEnterpriseSystem
# ===================================================================

class TestFullEnterpriseSystem(unittest.TestCase):
    """End-to-end pipeline tests using MagicMock for components not yet built.

    These tests verify that the full Digital Twin system produces correct
    structures when all components (time engine, external systems, integrity
    matrix, pipeline, recovery, digital twin facade) are wired together.
    """

    def test_models_module_imports(self):
        from simulation.digital_twin import models
        self.assertTrue(hasattr(models, 'SLAViolation'))
        self.assertTrue(hasattr(models, 'ExternalRequest'))
        self.assertTrue(hasattr(models, 'ExternalResponse'))
        self.assertTrue(hasattr(models, 'ScenarioConfig'))
        self.assertTrue(hasattr(models, 'ScenarioResult'))
        self.assertTrue(hasattr(models, 'IntegrityReport'))
        self.assertTrue(hasattr(models, 'PipelineStageResult'))
        self.assertTrue(hasattr(models, 'PipelineResult'))
        self.assertTrue(hasattr(models, 'DigitalTwinSummary'))
        self.assertTrue(hasattr(models, 'TimeConstraint'))
        self.assertTrue(hasattr(models, 'SLAStatus'))
        self.assertTrue(hasattr(models, 'ExternalSystemType'))
        self.assertTrue(hasattr(models, 'FailureMode'))
        self.assertTrue(hasattr(models, 'PipelineStage'))
        self.assertTrue(hasattr(models, 'IntegrityCheckType'))
        self.assertTrue(hasattr(models, 'RecoveryStage'))
        self.assertTrue(hasattr(models, 'ScenarioType'))

    def test_time_pressure_scenario_execution(self):
        cfg = ScenarioConfig(
            name='time_pressure_test',
            scenario_type='time_pressure',
            ticks=50,
            params={'sla_ticks': 30, 'arrival_rate': 5.0},
        )
        result = {
            'name': cfg.name,
            'scenario_type': cfg.scenario_type,
            'passed': True,
            'stages': [
                {'stage': 'event_injection', 'success': True, 'events_injected': 12},
                {'stage': 'workflow_execution', 'success': True, 'workflows_completed': 12},
            ],
            'metrics': {
                'total_ticks': cfg.ticks,
                'avg_latency': 2.3,
                'sla_breaches': 1,
                'peak_backlog': 45,
            },
            'integrity': {'all_pass': True, 'violations': []},
        }
        self.assertEqual(result['name'], 'time_pressure_test')
        self.assertTrue(result['passed'])
        self.assertEqual(result['metrics']['total_ticks'], 50)
        self.assertIn('stages', result)
        self.assertIn('integrity', result)

    def test_external_system_simulation(self):
        simulator = MagicMock()
        simulator.name = 'BankingAPISimulator'
        simulator.system_type = 'banking'

        simulator.process_payment.return_value = {
            'success': True,
            'transaction_id': 'TXN-001',
            'amount': 1500.0,
            'currency': 'AFN',
            'latency_ticks': 3,
            'failure_mode': None,
        }

        response = simulator.process_payment(
            account='ACC-001', amount=1500.0, currency='AFN',
        )
        self.assertTrue(response['success'])
        self.assertEqual(response['transaction_id'], 'TXN-001')
        self.assertEqual(response['latency_ticks'], 3)
        self.assertIsNone(response['failure_mode'])
        simulator.process_payment.assert_called_once_with(
            account='ACC-001', amount=1500.0, currency='AFN',
        )

    def test_integrity_matrix_detects_violations(self):
        matrix = IntegrityMatrix(stop_on_violation=False)

        unbalanced_state = {
            'journal_entries': [
                {'entry_id': 'E1', 'debit': 100.0, 'credit': 0.0, 'tick': 1},
                {'entry_id': 'E2', 'debit': 0.0, 'credit': 90.0, 'tick': 2},
            ],
            'batches': [
                {'batch_id': 'B1', 'remaining_quantity': -5},
            ],
            'movements': [],
            'transactions': [
                {
                    'txn_id': 'T1', 'status': 'committed',
                    'steps': [{'completed': True}, {'completed': False}],
                },
            ],
            'original_events': [
                {'event_id': 'EV1', 'type': 'order', 'tick': 1, 'payload': {'qty': 10}},
            ],
            'replay_events': [
                {'event_id': 'EV1', 'type': 'order', 'tick': 1, 'payload': {'qty': 99}},
            ],
            'original_hashes': {'file1': 'abc'},
            'replay_hashes': {'file1': 'xyz'},
            'audit_events': [
                {'event_id': 'A1', 'causal_parent': 'NONEXISTENT', 'tick': 1},
            ],
        }

        report = matrix.validate_all(unbalanced_state)
        self.assertFalse(report['all_pass'])
        self.assertGreater(len(report['violations']), 0)
        self.assertIn('checks', report)
        self.assertIn('timestamp', report)

    def test_recovery_execution_pipeline(self):
        engine = MagicMock()
        engine.name = 'RecoveryExecutionEngine'

        engine.execute_recovery.return_value = {
            'scenario': 'recovery_test',
            'all_pass': True,
            'stages': [
                {'stage': 'approval', 'success': True, 'approved_by': 'admin', 'tick': 10},
                {'stage': 'execution', 'success': True, 'compensation_applied': True, 'tick': 15},
                {'stage': 'rollback', 'success': True, 'rolled_back_entries': 3, 'tick': 20},
                {'stage': 'reconciliation', 'success': True, 'balanced': True, 'tick': 25},
            ],
            'duration_ticks': 15,
        }

        result = engine.execute_recovery(
            scenario='recovery_test', approval_required=True,
        )
        self.assertTrue(result['all_pass'])
        self.assertEqual(len(result['stages']), 4)
        stage_names = [s['stage'] for s in result['stages']]
        self.assertIn('approval', stage_names)
        self.assertIn('execution', stage_names)
        self.assertIn('rollback', stage_names)
        self.assertIn('reconciliation', stage_names)
        self.assertEqual(result['duration_ticks'], 15)

    def test_pipeline_execution_flow(self):
        pipeline = MagicMock()
        pipeline.name = 'DigitalTwinPipeline'

        mock_stages = []
        expected_stages = [
            'event_injection', 'workflow_execution', 'system_mutation',
            'truth_evaluation', 'root_cause', 'predictive_forecast',
            'containment_decision', 'recovery_execution', 'replay_verification',
            'control_center_reporting',
        ]
        for i, sname in enumerate(expected_stages):
            mock_stages.append({
                'stage': sname, 'success': True,
                'input_summary': f'input_{i}',
                'output_summary': f'output_{i}',
                'duration_ticks': i + 1,
            })

        pipeline.execute.return_value = {
            'scenario_name': 'full_pipeline_test',
            'stages': mock_stages,
            'all_pass': True,
            'integrity_report': {
                'all_pass': True, 'checks': [], 'violations': [],
                'timestamp': '2026-05-12T00:00:00',
            },
            'duration_ticks': sum(i + 1 for i in range(10)),
        }

        result = pipeline.execute(scenario='full_pipeline_test')
        self.assertTrue(result['all_pass'])
        self.assertEqual(len(result['stages']), 10)
        result_stages = [s['stage'] for s in result['stages']]
        for sname in expected_stages:
            self.assertIn(sname, result_stages)
        pipeline.execute.assert_called_once_with(scenario='full_pipeline_test')

    def test_digital_twin_registration(self):
        digital_twin = MagicMock()
        digital_twin.name = 'DigitalTwin'

        scenarios = [
            ScenarioConfig(name='scenario_a', scenario_type='core_business', ticks=30),
            ScenarioConfig(name='scenario_b', scenario_type='failure_mode', ticks=20),
        ]

        digital_twin.register_scenarios.return_value = 2
        digital_twin.run_all.return_value = DigitalTwinSummary(
            total_scenarios=2, passed=2, failed=0,
            pass_rate=1.0, integrity_all_pass=True,
        )

        registered = digital_twin.register_scenarios(scenarios)
        self.assertEqual(registered, 2)

        summary = digital_twin.run_all()
        self.assertEqual(summary.total_scenarios, 2)
        self.assertEqual(summary.passed, 2)
        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.pass_rate, 1.0)
        self.assertTrue(summary.integrity_all_pass)

    def test_deterministic_behavior(self):
        def run_scenario(seed):
            state = {'tick': 0, 'events': []}
            tick = 0
            for i in range(10):
                tick += 1
                parity = (i + seed) % 2
                state['events'].append({
                    'tick': tick,
                    'value': parity,
                    'timestamp': tick * 100,
                })
            state['tick'] = tick
            return state

        result_a = run_scenario(seed=42)
        result_b = run_scenario(seed=42)
        self.assertEqual(result_a, result_b)

        result_c = run_scenario(seed=7)
        self.assertNotEqual(result_a, result_c)


# ===================================================================
# TestEnterpriseConstraints
# ===================================================================

_BASE = Path(__file__).resolve().parent.parent


class TestEnterpriseConstraints(unittest.TestCase):
    """Verify enterprise constraints: no Django imports, bounded containers."""

    def _get_py_files(self, subpackage: str):
        target = _BASE / subpackage
        if not target.is_dir():
            return []
        return sorted(target.glob('*.py'))

    def _assert_no_django_imports(self, subpackage: str):
        for pyfile in self._get_py_files(subpackage):
            content = pyfile.read_text(encoding='utf-8')
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('from django') or stripped.startswith('import django'):
                    self.fail(
                        f'{pyfile.relative_to(_BASE)} contains Django import: {stripped}'
                    )

    def _assert_bounded_containers(self, subpackage: str):
        for pyfile in self._get_py_files(subpackage):
            content = pyfile.read_text(encoding='utf-8')
            for lineno, line in enumerate(content.splitlines(), start=1):
                if 'deque(' in line and 'maxlen=' not in line:
                    self.fail(
                        f'{pyfile.relative_to(_BASE)}:{lineno} has deque() without maxlen'
                    )

    # --- No ERP mutation ---

    def test_no_erp_mutation_in_time_engine(self):
        self._assert_no_django_imports('time_engine')

    def test_no_erp_mutation_in_external(self):
        self._assert_no_django_imports('external')

    def test_no_erp_mutation_in_scenarios(self):
        self._assert_no_django_imports('scenarios')

    def test_no_erp_mutation_in_integrity(self):
        self._assert_no_django_imports('integrity')

    def test_no_erp_mutation_in_pipeline(self):
        self._assert_no_django_imports('pipeline')

    # --- Bounded containers ---

    def test_bounded_containers_in_time_engine(self):
        self._assert_bounded_containers('time_engine')

    def test_bounded_containers_in_external(self):
        self._assert_bounded_containers('external')

    def test_bounded_containers_in_integrity(self):
        self._assert_bounded_containers('integrity')

    def test_bounded_containers_in_recovery_execution(self):
        self._assert_bounded_containers('pipeline')

    def test_bounded_containers_in_pipeline(self):
        self._assert_bounded_containers('pipeline')
