from typing import Any, Dict, Optional

from simulation.digital_twin.external.base_simulator import (
    ExternalSystemSimulator,
)


class PaymentGatewaySimulator(ExternalSystemSimulator):
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        default_config = {
            'failure_rate': 0.2,
            'latency_range': (1, 2),
            'failure_modes': ['partial_approval', 'split_handling'],
        }
        merged = dict(default_config)
        if config:
            merged.update(config)
        super().__init__(name='PaymentGateway', config=merged, seed=seed)
        self._auth_counter = 0
        self._capture_counter = 0
        self._refund_counter = 0

    def authorize(
        self, amount: float, method: str, currency: str
    ) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {
                'amount': amount,
                'method': method,
                'currency': currency,
            }

            self._auth_counter += 1
            approved_amount = amount

            if failure == 'partial_approval':
                approved_amount = amount * 0.5
            elif failure is not None:
                response = {'success': False, 'error': failure}
                self._record_request('authorize', request, response)
                return response

            response = {
                'success': True,
                'auth_code': f'AUTH-{self._auth_counter:06d}',
                'approved_amount': approved_amount,
                'currency': currency,
            }
            self._record_request('authorize', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def capture(self, auth_code: str, amount: float) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'auth_code': auth_code, 'amount': amount}

            self._capture_counter += 1
            captured_amount = amount

            if failure == 'split_handling':
                captured_amount = amount * 0.8
            elif failure is not None:
                response = {'success': False, 'error': failure}
                self._record_request('capture', request, response)
                return response

            response = {
                'success': True,
                'capture_id': f'CAP-{self._capture_counter:06d}',
                'captured_amount': captured_amount,
            }
            self._record_request('capture', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def refund(self, transaction_id: str, amount: float) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'transaction_id': transaction_id, 'amount': amount}

            if failure is not None:
                response = {'success': False, 'error': failure}
                self._record_request('refund', request, response)
                return response

            self._refund_counter += 1
            response = {
                'success': True,
                'refund_id': f'REF-{self._refund_counter:06d}',
                'refunded_amount': amount,
                'transaction_id': transaction_id,
            }
            self._record_request('refund', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}
