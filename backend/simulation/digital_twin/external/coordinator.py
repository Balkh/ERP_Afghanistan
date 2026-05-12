from typing import Any, Dict, Optional

from simulation.digital_twin.external.banking_api import (
    BankingAPISimulator,
)
from simulation.digital_twin.external.credit_api import (
    CustomerCreditAPISimulator,
)
from simulation.digital_twin.external.payment_gateway import (
    PaymentGatewaySimulator,
)
from simulation.digital_twin.external.supplier_system import (
    SupplierSystemSimulator,
)
from simulation.digital_twin.external.tax_authority import (
    TaxAuthorityAPISimulator,
)

COMPENSATION_MAP = {
    'timeout': {
        'action': 'retry_later',
        'desc': 'Schedule retry with exponential backoff',
    },
    'reversal': {
        'action': 'notify_accounting',
        'desc': 'Flag reversal for accounting reconciliation',
    },
    'partial_approval': {
        'action': 'adjust_order',
        'desc': 'Reduce order to approved amount',
    },
    'split_handling': {
        'action': 'reconcile_difference',
        'desc': 'Reconcile partial capture difference',
    },
    'delay': {
        'action': 'escalate',
        'desc': 'Escalate delayed PO to procurement team',
    },
    'rejection': {
        'action': 'contact_supplier',
        'desc': 'Contact supplier to resolve rejection',
    },
    'downtime': {
        'action': 'queue_for_retry',
        'desc': 'Queue request for retry when system recovers',
    },
    'deferred': {
        'action': 'schedule_retry',
        'desc': 'Schedule retry after deferred period',
    },
    'insufficient_credit': {
        'action': 'request_alternative',
        'desc': 'Request alternative payment method',
    },
    'unknown': {
        'action': 'manual_review',
        'desc': 'Manual review required',
    },
}


class ExternalSystemCoordinator:
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        config = config or {}
        self._seed = seed
        self._simulators = {
            'banking': BankingAPISimulator(
                config=config.get('banking'), seed=seed
            ),
            'payment_gateway': PaymentGatewaySimulator(
                config=config.get('payment_gateway'), seed=seed
            ),
            'supplier': SupplierSystemSimulator(
                config=config.get('supplier'), seed=seed
            ),
            'credit': CustomerCreditAPISimulator(
                config=config.get('credit'), seed=seed
            ),
            'tax': TaxAuthorityAPISimulator(
                config=config.get('tax'), seed=seed
            ),
        }

    def _get_simulator(self, system: str):
        return self._simulators.get(system)

    def execute_with_retry(
        self,
        system: str,
        operation: str,
        params: Dict,
        max_retries: int = 3,
    ) -> Dict:
        try:
            simulator = self._get_simulator(system)
            if simulator is None:
                return {
                    'success': False,
                    'error': f'Unknown system: {system}',
                    'attempts': 1,
                    'final': True,
                }

            method = getattr(simulator, operation, None)
            if method is None:
                return {
                    'success': False,
                    'error': f'Unknown operation: {operation}',
                    'attempts': 1,
                    'final': True,
                }

            response = None
            for attempt in range(1, max_retries + 2):
                try:
                    response = method(**params)
                except Exception:
                    response = {'success': False, 'error': 'exception'}

                if response.get('success', False):
                    return {
                        'success': True,
                        'response': response,
                        'attempts': attempt,
                        'final': True,
                    }

            return {
                'success': False,
                'response': response,
                'attempts': max_retries + 1,
                'final': True,
            }
        except Exception:
            return {
                'success': False,
                'error': 'coordinator_error',
                'attempts': 1,
                'final': True,
            }

    def handle_failure(
        self, system: str, request: Dict, response: Dict
    ) -> Dict:
        try:
            error = response.get('error', 'unknown')

            if response.get('success', True) and error == 'unknown':
                status = response.get('status', '')
                if status == 'pending':
                    error = 'delay'
                elif status == 'deferred':
                    error = 'deferred'
                elif 'approved_amount' in response:
                    req_amount = request.get('amount', 0)
                    if response['approved_amount'] < req_amount:
                        error = 'partial_approval'
                elif 'captured_amount' in response:
                    req_amount = request.get('amount', 0)
                    if response['captured_amount'] < req_amount:
                        error = 'split_handling'
                elif 'reversal_amount' in response:
                    error = 'reversal'

            if error == 'rejected':
                error = 'rejection'

            if 'reason' in response and response.get('reason') == 'insufficient_credit':
                error = 'insufficient_credit'

            info = COMPENSATION_MAP.get(
                error, COMPENSATION_MAP['unknown']
            )
            return {
                'system': system,
                'failure_mode': error,
                'compensation_action': info['action'],
                'description': info['desc'],
            }
        except Exception:
            return {
                'system': system,
                'failure_mode': 'unknown',
                'compensation_action': 'manual_review',
                'description': 'Manual review required',
            }

    def get_system_health(self) -> Dict[str, Dict]:
        result = {}
        for name, simulator in self._simulators.items():
            try:
                result[name] = simulator.get_health()
            except Exception:
                result[name] = {
                    'name': name,
                    'total_requests': 0,
                    'failure_count': 0,
                    'success_rate': 0.0,
                    'uptime': 0.0,
                }
        return result

    def reset(self) -> None:
        for simulator in self._simulators.values():
            try:
                simulator.reset()
            except Exception:
                pass

    def clear(self) -> None:
        for simulator in self._simulators.values():
            try:
                simulator.clear()
            except Exception:
                pass
