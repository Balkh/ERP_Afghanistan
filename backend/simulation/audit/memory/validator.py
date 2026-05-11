"""
Task C: MemoryBoundaryValidator — audits all simulation structures for bounds.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.audit.memory.validator')


class MemoryBoundaryValidator:
    def audit_structures(self, structures: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        for name, obj in structures.items():
            results[name] = self._audit_single(name, obj)
        results['all_bounded'] = all(
            r.get('bounded', False) for r in results.values()
        )
        return results

    def _audit_single(self, name: str, obj: Any) -> Dict[str, Any]:
        maxlen = None
        if hasattr(obj, 'maxlen'):
            maxlen = obj.maxlen
        elif hasattr(obj, '_maxlen'):
            maxlen = obj._maxlen
        elif hasattr(obj, '_max_snapshots'):
            maxlen = obj._max_snapshots
        elif hasattr(obj, '_max_history'):
            maxlen = obj._max_history
        length = 0
        if hasattr(obj, '__len__'):
            try:
                length = len(obj)
            except Exception:
                length = -1
        return {
            'name': name,
            'type': type(obj).__name__,
            'bounded': maxlen is not None,
            'maxlen': maxlen,
            'current_length': length,
            'overflow': length > maxlen if maxlen is not None else None,
        }
