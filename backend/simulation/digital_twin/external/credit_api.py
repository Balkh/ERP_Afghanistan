from typing import Any, Dict, Optional

from simulation.digital_twin.external.base_simulator import (
    ExternalSystemSimulator,
)


class CustomerCreditAPISimulator(ExternalSystemSimulator):
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        default_config = {
            'failure_rate': 0.15,
            'latency_range': (1, 2),
            'failure_modes': ['downtime', 'rejection'],
        }
        merged = dict(default_config)
        if config:
            merged.update(config)
        super().__init__(name='CustomerCreditAPI', config=merged, seed=seed)
        self._approval_counter = 0
        self._hold_counter = 0
        self._holds = {}

    def check_credit(self, customer_id: str, amount: float) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'customer_id': customer_id, 'amount': amount}

            if failure == 'downtime':
                response = {'success': False, 'error': 'downtime'}
            elif failure == 'rejection':
                response = {
                    'success': False,
                    'error': 'rejection',
                    'reason': 'insufficient_credit',
                }
            else:
                self._approval_counter += 1
                response = {
                    'success': True,
                    'approval_code': f'APP-{self._approval_counter:06d}',
                    'approved_limit': amount,
                }

            self._record_request('check_credit', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def hold_credit(self, customer_id: str, amount: float) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'customer_id': customer_id, 'amount': amount}

            if failure is not None:
                response = {'success': False, 'error': failure}
                self._record_request('hold_credit', request, response)
                return response

            self._hold_counter += 1
            hold_id = f'HOLD-{self._hold_counter:06d}'
            self._holds[hold_id] = {
                'customer_id': customer_id,
                'amount': amount,
            }
            response = {
                'success': True,
                'hold_id': hold_id,
                'held_amount': amount,
            }
            self._record_request('hold_credit', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def release_hold(self, hold_id: str) -> Dict:
        try:
            request = {'hold_id': hold_id}
            released = self._holds.pop(hold_id, None)
            response = {
                'success': True,
                'hold_id': hold_id,
                'released': released is not None,
            }
            self._record_request('release_hold', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}
