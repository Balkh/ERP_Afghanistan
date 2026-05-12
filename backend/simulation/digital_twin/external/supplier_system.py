from typing import Any, Dict, Optional

from simulation.digital_twin.external.base_simulator import (
    ExternalSystemSimulator,
)


class SupplierSystemSimulator(ExternalSystemSimulator):
    def __init__(self, config: Dict[str, Any] = None, seed: int = 42):
        default_config = {
            'failure_rate': 0.1,
            'latency_range': (3, 5),
            'failure_modes': ['delay', 'rejection'],
        }
        merged = dict(default_config)
        if config:
            merged.update(config)
        super().__init__(name='SupplierSystem', config=merged, seed=seed)
        self._po_counter = 0
        self._pos = {}

    def submit_po(self, po_data: Dict) -> Dict:
        try:
            latency = self.simulate_latency()
            failure = self.simulate_failure()
            request = {'po_data': po_data}

            if failure == 'delay':
                self._po_counter += 1
                po_id = f'PO-{self._po_counter:06d}'
                self._pos[po_id] = 'pending'
                response = {
                    'success': True,
                    'po_id': po_id,
                    'status': 'pending',
                }
            elif failure == 'rejection':
                response = {'success': False, 'error': 'rejected'}
            else:
                self._po_counter += 1
                po_id = f'PO-{self._po_counter:06d}'
                self._pos[po_id] = 'confirmed'
                response = {
                    'success': True,
                    'po_id': po_id,
                    'status': 'confirmed',
                }

            self._record_request('submit_po', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}

    def check_status(self, po_id: str) -> Dict:
        try:
            request = {'po_id': po_id}
            status = self._pos.get(po_id, 'unknown')
            response = {
                'success': True,
                'po_id': po_id,
                'status': status,
            }
            self._record_request('check_status', request, response)
            return response
        except Exception:
            return {'success': False, 'error': 'internal_error'}
