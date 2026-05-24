import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List
from core.models.migration_config import MigrationLog
from core.drift_prevention.registry import DriftRegistry

logger = logging.getLogger('erp.switchover.observability')


class Observability:
    """Execution observability for every financial operation during switchover.

    Every operation logs:
        - engine_used (ENGINE / GATEWAY)
        - execution_hash (SHA-256 of normalized params)
        - financial_signature (SHA-256 of resulting lines)
        - drift_score (0-100)
        - validation_result (PASS / FAIL / ROLLED_BACK)
    """

    @staticmethod
    def log(
        module: str,
        function: str,
        engine_used: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        drift_score: int = 0,
        validation_result: str = 'PASS',
        reference: str = '',
        duration_ms: int = 0,
    ) -> MigrationLog:
        execution_hash = Observability._compute_hash(params)
        financial_signature = Observability._compute_financial_signature(result)

        log_entry = MigrationLog.objects.create(
            module=module,
            function=function,
            engine_used=engine_used,
            execution_hash=execution_hash,
            financial_signature=financial_signature,
            drift_score=drift_score,
            validation_result=validation_result,
            reference=reference,
            duration_ms=duration_ms,
        )

        level = logging.WARNING if validation_result != 'PASS' else logging.INFO
        logger.log(
            level,
            f'[{engine_used}] {module}.{function} {validation_result} '
            f'ref={reference} hash={execution_hash[:12]}... '
            f'sig={financial_signature[:12]}... drift={drift_score} ({duration_ms}ms)'
        )

        return log_entry

    @staticmethod
    def _compute_hash(params: Dict[str, Any]) -> str:
        try:
            normalized = json.dumps(params, sort_keys=True, default=str)
            return hashlib.sha256(normalized.encode()).hexdigest()
        except Exception:
            return ''

    @staticmethod
    def _compute_financial_signature(result: Dict[str, Any]) -> str:
        try:
            entry_id = result.get('entry_id', '')
            success = result.get('success', False)
            sig_data = json.dumps({'entry_id': str(entry_id), 'success': success}, sort_keys=True)
            return hashlib.sha256(sig_data.encode()).hexdigest()
        except Exception:
            return ''

    @staticmethod
    def get_recent_logs(module: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        qs = MigrationLog.objects.all()
        if module:
            qs = qs.filter(module=module)
        logs = qs.order_by('-created_at')[:limit]
        return [
            {
                'module': l.module,
                'function': l.function,
                'engine_used': l.engine_used,
                'execution_hash': l.execution_hash[:16] if l.execution_hash else '',
                'financial_signature': l.financial_signature[:16] if l.financial_signature else '',
                'drift_score': l.drift_score,
                'validation_result': l.validation_result,
                'reference': l.reference,
                'duration_ms': l.duration_ms,
                'created_at': str(l.created_at),
            }
            for l in logs
        ]
