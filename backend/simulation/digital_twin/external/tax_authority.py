from typing import Any, Dict, Optional

from simulation.digital_twin.external.base_simulator import (
    ExternalSystemSimulator,
)


class TaxAuthorityAPISimulator(ExternalSystemSimulator):
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        default_config = {
            'failure_rate': 0.2,
            'latency_range': (2, 4),
            'failure_modes': ['downtime', 'deferred'],
        }
        merged = dict(default_config)
        if config:
            merged.update(config)
        super().__init__(name='TaxAuthorityAPI', config=merged, seed=seed)
        self._validation_counter = 0
        self._submission_counter = 0

    def validate_return(self, tax_data: Dict) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'tax_data': tax_data}

            if failure == 'downtime':
                response = {'success': False, 'error': 'downtime'}
            elif failure == 'deferred':
                self._validation_counter += 1
                response = {
                    'success': True,
                    'validation_id': f'VAL-{self._validation_counter:06d}',
                    'is_valid': True,
                    'deferred': True,
                }
            else:
                self._validation_counter += 1
                response = {
                    'success': True,
                    'validation_id': f'VAL-{self._validation_counter:06d}',
                    'is_valid': True,
                }

            self._record_request('validate_return', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def submit_return(self, tax_data: Dict) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'tax_data': tax_data}

            if failure == 'downtime':
                response = {'success': False, 'error': 'downtime'}
            elif failure == 'deferred':
                self._submission_counter += 1
                response = {
                    'success': True,
                    'submission_id': f'SUB-{self._submission_counter:06d}',
                    'status': 'deferred',
                    'deferred_until': 10,
                }
            else:
                self._submission_counter += 1
                response = {
                    'success': True,
                    'submission_id': f'SUB-{self._submission_counter:06d}',
                    'status': 'posted',
                }

            self._record_request('submit_return', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}
