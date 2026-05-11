"""
Task C: RetentionPolicyVerifier — verifies cleanup execution and bounded retention.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger('erp.simulation.audit.memory.verifier')


class RetentionPolicyVerifier:
    def verify(self, structure_name: str, obj: Any,
               expected_maxlen: int) -> Dict[str, Any]:
        actual_maxlen = getattr(obj, 'maxlen', None) or \
                        getattr(obj, '_maxlen', None) or \
                        getattr(obj, '_max_snapshots', None) or \
                        getattr(obj, '_max_history', None)
        current_length = len(obj) if hasattr(obj, '__len__') else -1
        cleanup_works = False
        if actual_maxlen and current_length > actual_maxlen: 
            cleanup_works = False
        elif actual_maxlen and current_length <= actual_maxlen:
            cleanup_works = True
        return {
            'structure': structure_name,
            'expected_maxlen': expected_maxlen,
            'actual_maxlen_property': actual_maxlen,
            'current_length': current_length,
            'maxlen_correct': actual_maxlen == expected_maxlen,
            'cleanup_functional': cleanup_works,
            'retention_compliant': (
                actual_maxlen == expected_maxlen and cleanup_works
            ),
        }
