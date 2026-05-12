import logging
from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Optional

from simulation.context.context import SimulationContext
from simulation.engine.engine import SimulationEngine

from simulation.digital_twin.pipeline.orchestrator import DigitalTwinPipeline
from simulation.digital_twin.integrity.accounting_validator import (
    AccountingValidator,
)
from simulation.digital_twin.integrity.inventory_validator import (
    InventoryValidator,
)
from simulation.digital_twin.integrity.transaction_validator import (
    TransactionValidator,
)
from simulation.digital_twin.integrity.audit_validator import AuditValidator
from simulation.digital_twin.integrity.replay_validator import ReplayValidator

logger = logging.getLogger('erp.simulation.digital_twin.pipeline.digital_twin')


class IntegrityMatrix:
    """Aggregates all validators and provides a unified validate_all."""

    def __init__(self):
        self._inventory = InventoryValidator()
        self._accounting = AccountingValidator()
        self._transactions = TransactionValidator()
        self._audit = AuditValidator()
        self._replay = ReplayValidator()

    def validate_all(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            checks = []
            violations = []

            batches = state.get('batches', [])
            movements = state.get('movements', [])
            entries = state.get('journal_entries', [])
            transactions = state.get('transactions', [])
            events = state.get('events', [])
            original_events = state.get('original_events', [])
            replay_events = state.get('replay_events', [])

            r = self._inventory.check_no_negative(batches)
            checks.append({'validator': 'inventory.no_negative', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._inventory.check_fifo(movements)
            checks.append({'validator': 'inventory.fifo', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._inventory.check_batch_integrity(batches)
            checks.append({'validator': 'inventory.batch_integrity', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._accounting.check_balance(entries)
            checks.append({'validator': 'accounting.balance', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._accounting.check_no_duplicates(entries)
            checks.append({'validator': 'accounting.no_duplicates', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._accounting.check_chronological(entries)
            checks.append({'validator': 'accounting.chronological', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._transactions.check_atomicity(transactions)
            checks.append({'validator': 'transactions.atomicity', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._transactions.check_no_partial(transactions)
            checks.append({'validator': 'transactions.no_partial', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._transactions.check_rollback(transactions)
            checks.append({'validator': 'transactions.rollback', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._audit.check_causal_traceability(events)
            checks.append({'validator': 'audit.causal_traceability', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            r = self._audit.check_completeness(events)
            checks.append({'validator': 'audit.completeness', 'passed': r['passed']})
            if not r['passed']:
                violations.append(r)

            if original_events and replay_events:
                r = self._replay.check_determinism(original_events, replay_events)
                checks.append({'validator': 'replay.determinism', 'passed': r['passed']})
                if not r['passed']:
                    violations.append(r)

            return {
                'passed': len(violations) == 0,
                'checks': checks,
                'violations': violations,
            }
        except Exception as e:
            return {
                'passed': False,
                'checks': [],
                'violations': [{'error': str(e)}],
            }


class DigitalTwin:

    def __init__(self, config: Optional[Dict] = None):
        self._config = dict(config) if config else {}
        self._scenarios: Dict[str, Any] = {}
        self._results: deque = deque(maxlen=200)
        self._pipeline: Optional[DigitalTwinPipeline] = None
        self._engine: Optional[SimulationEngine] = None

    def _build_engine(self) -> SimulationEngine:
        context = SimulationContext(config=self._config)
        engine = SimulationEngine(
            context=context,
            config=self._config,
        )
        return engine

    def _build_pipeline(self, engine) -> DigitalTwinPipeline:
        control_center = self._config.get('control_center')
        truth_engine = self._config.get('truth_engine') or getattr(engine, 'truth_engine', None)
        root_cause = self._config.get('root_cause')
        predictive = self._config.get('predictive')
        recovery = self._config.get('recovery')
        replay = self._config.get('replay')
        integrity = self._config.get('integrity')
        stop_on_failure = self._config.get('stop_on_failure', True)

        return DigitalTwinPipeline(
            engine=engine,
            control_center=control_center,
            truth_engine=truth_engine,
            root_cause=root_cause,
            predictive=predictive,
            recovery=recovery,
            replay=replay,
            integrity=integrity,
            stop_on_failure=stop_on_failure,
        )

    def _build_integrity_matrix(self) -> IntegrityMatrix:
        return IntegrityMatrix()

    def register_scenario(self, scenario) -> bool:
        try:
            name = getattr(scenario, '_name', None)
            if not name or not isinstance(name, str):
                return False
            self._scenarios[name] = scenario
            return True
        except Exception:
            return False

    def run_scenario(self, name: str) -> Dict[str, Any]:
        try:
            scenario = self._scenarios.get(name)
            if scenario is None:
                return {'success': False, 'error': f'Scenario "{name}" not found'}

            self._engine = self._build_engine()
            self._pipeline = self._build_pipeline(self._engine)

            result = self._pipeline.execute(scenario)
            self._results.append(result)
            return result
        except Exception as e:
            logger.exception('run_scenario failed for %s: %s', name, e)
            error_result = {
                'scenario_name': name,
                'success': False,
                'error': str(e),
            }
            self._results.append(error_result)
            return error_result

    def run_all(self) -> List[Dict[str, Any]]:
        results = []
        for name in list(self._scenarios.keys()):
            result = self.run_scenario(name)
            results.append(result)
        return results

    def run_batch(self, names: List[str]) -> List[Dict[str, Any]]:
        results = []
        for name in names:
            result = self.run_scenario(name)
            results.append(result)
        return results

    def get_report(self, name: str) -> Optional[Dict[str, Any]]:
        for r in self._results:
            if isinstance(r, dict) and r.get('scenario_name') == name:
                return r
        return None

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._results)
        passed = sum(1 for r in self._results if isinstance(r, dict) and r.get('all_pass', False))
        failed = total - passed
        pass_rate = round((passed / total * 100), 2) if total > 0 else 0.0

        scenarios_list = []
        for r in self._results:
            if isinstance(r, dict):
                scenarios_list.append({
                    'name': r.get('scenario_name', 'unknown'),
                    'all_pass': r.get('all_pass', False),
                    'duration_ticks': r.get('duration_ticks', 0),
                })

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate,
            'scenarios': scenarios_list,
        }

    def validate_system(self) -> Dict[str, Any]:
        try:
            matrix = self._build_integrity_matrix()
            aggregated_state: Dict[str, Any] = {
                'batches': [],
                'movements': [],
                'journal_entries': [],
                'transactions': [],
                'events': [],
                'original_events': [],
                'replay_events': [],
            }

            for r in self._results:
                if not isinstance(r, dict):
                    continue
                for stage in r.get('stages', []):
                    if not isinstance(stage, dict):
                        continue
                    output = stage.get('output_summary', '')
                    if output and output != 'none':
                        aggregated_state.setdefault('_stage_outputs', []).append(output)

            return matrix.validate_all(aggregated_state)
        except Exception as e:
            return {
                'passed': False,
                'checks': [],
                'violations': [{'error': str(e)}],
            }

    def clear(self):
        self._scenarios.clear()
        self._results.clear()
        self._pipeline = None
        self._engine = None
