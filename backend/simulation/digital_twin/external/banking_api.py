from typing import Any, Dict, Optional

from simulation.digital_twin.external.base_simulator import (
    ExternalSystemSimulator,
)


class BankingAPISimulator(ExternalSystemSimulator):
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        default_config = {
            'failure_rate': 0.3,
            'latency_range': (1, 3),
            'failure_modes': ['timeout', 'reversal'],
        }
        merged = dict(default_config)
        if config:
            merged.update(config)
        super().__init__(name='BankingAPI', config=merged, seed=seed)
        self._payment_counter = 0

    def process_payment(
        self, amount: float, currency: str, target_account: str
    ) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {
                'amount': amount,
                'currency': currency,
                'target_account': target_account,
            }

            if failure == 'timeout':
                response = {'success': False, 'error': 'timeout'}
            elif failure == 'reversal':
                response = {
                    'success': False,
                    'error': 'reversal',
                    'reversal_amount': amount,
                }
            else:
                self._payment_counter += 1
                response = {
                    'success': True,
                    'payment_id': f'PAY-{self._payment_counter:06d}',
                    'settled_amount': amount,
                    'currency': currency,
                    'status': 'settled',
                }

            self._record_request('process_payment', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def reverse_payment(self, payment_id: str) -> Dict:
        try:
            request = {'payment_id': payment_id}
            response = {
                'success': True,
                'payment_id': payment_id,
                'reversed': True,
            }
            self._record_request('reverse_payment', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}
