import logging
from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.digital_twin.pipeline')


class DigitalTwinPipeline:

    STAGES = [
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

    def __init__(
        self,
        engine=None,
        control_center=None,
        truth_engine=None,
        root_cause=None,
        predictive=None,
        recovery=None,
        replay=None,
        integrity=None,
        stop_on_failure: bool = True,
    ):
        self._engine = engine
        self._control_center = control_center
        self._truth_engine = truth_engine
        self._root_cause = root_cause
        self._predictive = predictive
        self._recovery = recovery
        self._replay = replay
        self._integrity = integrity
        self._stop_on_failure = stop_on_failure
        self._results: deque = deque(maxlen=100)
        self._last_execution_result: Optional[Dict] = None
        self._execution_count: int = 0

    def execute(self, scenario) -> Dict:
        self._execution_count += 1
        stages: List[Dict] = []
        all_pass = True
        stage_input = None
        scenario_name = getattr(scenario, '_name', None) or getattr(scenario, 'get_name', lambda: 'unknown')()
        first_error = None

        for stage_name in self.STAGES:
            stage_func = self._get_stage_func(stage_name)
            if stage_func is None:
                stage_func = lambda inp, _sn=stage_name: self._skip_stage(_sn, inp)

            result = self._run_stage(stage_name, stage_input, stage_func, scenario)
            stages.append(result)

            if not result['success']:
                all_pass = False
                if first_error is None:
                    first_error = result.get('error')
                if self._stop_on_failure:
                    break

            stage_input = result.get('output_summary', '')

        duration = sum(s.get('duration_ticks', 0) for s in stages)

        pipeline_result = {
            'scenario_name': scenario_name,
            'stages': stages,
            'all_pass': all_pass,
            'integrity_report': self._build_integrity_report(stages),
            'duration_ticks': duration,
        }

        self._results.append(pipeline_result)
        self._last_execution_result = pipeline_result
        return pipeline_result

    def get_stage_result(self, stage: str) -> Optional[Dict]:
        if self._last_execution_result is None:
            return None
        for s in self._last_execution_result.get('stages', []):
            if s.get('stage') == stage:
                return s
        return None

    def get_pipeline_status(self) -> Dict:
        stages_completed = 0
        all_pass = True
        if self._last_execution_result is not None:
            stages_completed = len(self._last_execution_result.get('stages', []))
            all_pass = self._last_execution_result.get('all_pass', True)
        return {
            'stages_completed': stages_completed,
            'total_stages': len(self.STAGES),
            'all_pass': all_pass,
            'last_execution': 'completed' if self._last_execution_result is not None else 'none',
        }

    def get_execution_count(self) -> int:
        return self._execution_count

    def clear(self):
        self._results.clear()
        self._last_execution_result = None
        self._execution_count = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_stage_func(self, name: str):
        registry = {
            'event_injection': self._stage_event_injection,
            'workflow_execution': self._stage_workflow_execution,
            'system_mutation': self._stage_system_mutation,
            'truth_evaluation': self._stage_truth_evaluation,
            'root_cause': self._stage_root_cause,
            'predictive_forecast': self._stage_predictive_forecast,
            'containment_decision': self._stage_containment_decision,
            'recovery_execution': self._stage_recovery_execution,
            'replay_verification': self._stage_replay_verification,
            'control_center_reporting': self._stage_control_center_reporting,
        }
        return registry.get(name)

    def _run_stage(self, name: str, stage_input: Any, stage_func, scenario) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = stage_func(stage_input, scenario)
            if not isinstance(result, dict):
                result = {'output_summary': str(result)}
            if 'input_summary' not in result:
                result['input_summary'] = self._summarize(stage_input)
            if 'output_summary' not in result:
                result['output_summary'] = ''
            if 'duration_ticks' not in result:
                result['duration_ticks'] = 0
            result.setdefault('stage', name)
            result.setdefault('success', True)
            if 'error' not in result:
                result['error'] = None
            return result
        except Exception as e:
            logger.exception('Pipeline stage %s failed: %s', name, e)
            return {
                'stage': name,
                'success': False,
                'input_summary': self._summarize(stage_input),
                'output_summary': '',
                'duration_ticks': 0,
                'error': str(e),
            }

    def _skip_stage(self, name: str, stage_input: Any) -> Dict:
        return {
            'stage': name,
            'success': True,
            'input_summary': self._summarize(stage_input),
            'output_summary': 'skipped (component not configured)',
            'duration_ticks': 0,
            'error': None,
        }

    def _summarize(self, value: Any, max_len: int = 120) -> str:
        if value is None:
            return 'none'
        s = str(value)
        if len(s) > max_len:
            return s[:max_len] + '...'
        return s

    def _build_integrity_report(self, stages: List[Dict]) -> Dict:
        pass_ = all(s.get('success', False) for s in stages)
        return {
            'all_clean': pass_,
            'total_stages': len(stages),
            'failed_stages': [s['stage'] for s in stages if not s.get('success', False)],
        }

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_event_injection(self, stage_input: Any, scenario) -> Dict:
        scenario.setup(self._engine)
        return {'output_summary': 'events_injected', 'duration_ticks': 1}

    def _stage_workflow_execution(self, stage_input: Any, scenario) -> Dict:
        if self._engine is None:
            return {'output_summary': 'no_engine', 'duration_ticks': 0}

        config = getattr(scenario, '_config', {}) or {}
        ticks = config.get('ticks', 5)

        if hasattr(self._engine, 'run'):
            result = self._engine.run(max_ticks=ticks)
            duration = result.get('ticks_executed', ticks)
        elif hasattr(self._engine, 'execute_tick'):
            duration = 0
            for _ in range(ticks):
                self._engine.execute_tick()
                duration += 1
        else:
            duration = 0

        return {'output_summary': f'executed_{ticks}_ticks', 'duration_ticks': duration}

    def _stage_system_mutation(self, stage_input: Any, scenario) -> Dict:
        if self._engine is None or not hasattr(self._engine, 'metrics'):
            return {'output_summary': 'no_metrics', 'duration_ticks': 0}

        snapshot = self._engine.metrics.snapshot()
        output = self._summarize(snapshot)
        return {'output_summary': output, 'duration_ticks': 1}

    def _stage_truth_evaluation(self, stage_input: Any, scenario) -> Dict:
        if self._truth_engine is None:
            return {
                'output_summary': 'skipped_no_truth_engine',
                'duration_ticks': 0,
            }

        result = self._truth_engine.verify(self._engine)
        summary = self._summarize(result)
        return {
            'output_summary': summary,
            'duration_ticks': 1,
            '_mismatches': result.get('summary', {}).get('total_mismatches', 0) if isinstance(result, dict) else 0,
        }

    def _stage_root_cause(self, stage_input: Any, scenario) -> Dict:
        if self._root_cause is None:
            return {
                'output_summary': 'skipped_no_root_cause',
                'duration_ticks': 0,
            }

        prev_stage = self.get_stage_result('truth_evaluation')
        has_mismatches = False
        if prev_stage:
            mismatches = prev_stage.get('_mismatches', 0)
            has_mismatches = mismatches > 0

        if not has_mismatches:
            return {
                'output_summary': 'skipped_no_mismatches',
                'duration_ticks': 0,
            }

        result = self._root_cause.analyze(input_data=stage_input)
        summary = self._summarize(result)
        return {'output_summary': summary, 'duration_ticks': 1}

    def _stage_predictive_forecast(self, stage_input: Any, scenario) -> Dict:
        if self._predictive is None:
            return {
                'output_summary': 'skipped_no_predictive',
                'duration_ticks': 0,
            }

        result = self._predictive.analyze(stage_input)
        summary = self._summarize(result)
        return {'output_summary': summary, 'duration_ticks': 1}

    def _stage_containment_decision(self, stage_input: Any, scenario) -> Dict:
        if self._recovery is None:
            return {
                'output_summary': 'skipped_no_recovery',
                'duration_ticks': 0,
            }

        result = self._recovery.handle_integrity_incident(violation_data=stage_input)
        summary = self._summarize(result)
        was_contained = isinstance(result, dict) and result.get('contained', False)
        return {
            'output_summary': summary,
            'duration_ticks': 1,
            '_contained': was_contained,
        }

    def _stage_recovery_execution(self, stage_input: Any, scenario) -> Dict:
        if self._recovery is None:
            return {
                'output_summary': 'skipped_no_recovery',
                'duration_ticks': 0,
            }

        prev_stage = self.get_stage_result('containment_decision')
        has_containment = False
        if prev_stage:
            has_containment = prev_stage.get('_contained', False)

        if not has_containment:
            return {
                'output_summary': 'skipped_no_containment',
                'duration_ticks': 0,
            }

        result = self._recovery.execute_recovery(stage_input)
        summary = self._summarize(result)
        return {'output_summary': summary, 'duration_ticks': 1}

    def _stage_replay_verification(self, stage_input: Any, scenario) -> Dict:
        if self._replay is None:
            return {
                'output_summary': 'skipped_no_replay',
                'duration_ticks': 0,
            }

        result = self._replay.verify(stage_input)
        summary = self._summarize(result)
        return {'output_summary': summary, 'duration_ticks': 1}

    def _stage_control_center_reporting(self, stage_input: Any, scenario) -> Dict:
        if self._control_center is None:
            return {
                'output_summary': 'skipped_no_control_center',
                'duration_ticks': 0,
            }

        snapshot = self._control_center.generate_dashboard_snapshot()
        report = getattr(self._control_center, 'get_report', lambda: {})()

        combined = {
            'snapshot': self._summarize(snapshot),
            'report': self._summarize(report),
        }
        return {
            'output_summary': self._summarize(combined),
            'duration_ticks': 1,
        }
