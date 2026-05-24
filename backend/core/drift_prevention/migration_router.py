import time
import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from accounting.services.journal_engine import JournalEngine
from core.services.journal_gateway import JournalGateway
from core.drift_prevention.migration_registry import MigrationRegistry
from core.drift_prevention.equilibrium_checker import EquilibriumChecker
from core.drift_prevention.rollback_manager import RollbackManager
from core.drift_prevention.observability import Observability

logger = logging.getLogger('erp.switchover.router')


class MigrationRouter:
    """Central dispatch for all journal entry operations.

    Routes to JournalEngine or JournalGateway based on migration state.
    Handles pre-execution validation, equilibrium checking, rollback, and observability.
    """

    @staticmethod
    def create_entry(
        module: str,
        operation: str,
        entry_type: str,
        description: str,
        lines: List[Dict[str, Any]],
        entry_date=None,
        reference: str = '',
        auto_post: bool = False,
        entity_type: str = '',
        entity_id: str = '',
        company=None,
        source_document: str = '',
        change_reason: str = '',
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        use_gateway = MigrationRegistry.is_gateway(module, operation)

        params = {
            'entry_type': entry_type,
            'description': description,
            'lines': lines,
            'entry_date': str(entry_date) if entry_date else None,
            'reference': reference,
            'auto_post': auto_post,
        }

        if use_gateway:
            try:
                gateway_lines = MigrationRouter._normalize_lines(lines)
                result = JournalGateway.create_entry(
                    entry_type=entry_type,
                    description=description,
                    lines=gateway_lines,
                    entry_date=entry_date,
                    reference=reference,
                    auto_post=auto_post,
                    entity_type=entity_type or module,
                    entity_id=entity_id or reference,
                    company=company,
                )

                eq = EquilibriumChecker.verify(
                    module, operation, reference or '',
                    engine_result=result,
                    gateway_result=result,
                )

                if not EquilibriumChecker.is_stable(eq):
                    logger.warning(
                        f'[ROUTER] Gateway equilibrium FAILED for {module}.{operation}: '
                        f'{eq["reasons"][:2]}'
                    )
                    RollbackManager.rollback_function(
                        module, operation,
                        reason=f'Gateway equilibrium check failed: {eq["reasons"][:2]}',
                        equilibrium_result=eq,
                    )

                Observability.log(
                    module, operation, 'GATEWAY', params, result,
                    drift_score=0 if eq['in_equilibrium'] else 50,
                    validation_result='PASS' if eq['in_equilibrium'] else 'FAIL',
                    reference=reference,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return result

            except Exception as e:
                error_msg = str(e)
                logger.error(f'[ROUTER] Gateway create FAILED for {module}.{operation}: {error_msg}')
                RollbackManager.rollback_function(
                    module, operation,
                    reason=f'Gateway create exception: {error_msg}',
                )
                Observability.log(
                    module, operation, 'GATEWAY', params, {},
                    drift_score=100, validation_result='FAIL',
                    reference=reference,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return {'success': False, 'error': error_msg, 'rolled_back': True}

        result = JournalEngine.create_entry(
            entry_type=entry_type,
            description=description,
            lines=lines,
            entry_date=entry_date,
            reference=reference,
            auto_post=auto_post,
            source_module=module,
            source_document=source_document or entity_id,
            change_reason=change_reason or description,
            created_by=created_by,
        )

        Observability.log(
            module, operation, 'ENGINE', params, result,
            drift_score=0, validation_result='PASS',
            reference=reference,
            duration_ms=int((time.time() - start) * 1000),
        )
        return result

    @staticmethod
    def reverse_entry(
        module: str,
        operation: str,
        entry_id: str,
        reason: str = '',
        reversed_by: str = '',
        entity_type: str = '',
        entity_id: str = '',
        company=None,
    ) -> Dict[str, Any]:
        start = time.time()
        use_gateway = MigrationRegistry.is_gateway(module, operation)

        params = {'entry_id': entry_id, 'reason': reason}

        if use_gateway:
            try:
                result = JournalGateway.reverse_entry(
                    entry_id=entry_id,
                    reason=reason,
                    reversed_by=reversed_by,
                    entity_type=entity_type or module,
                    entity_id=entity_id or entry_id,
                    company=company,
                )
                Observability.log(
                    module, operation, 'GATEWAY', params, result,
                    drift_score=0, validation_result='PASS',
                    reference=entry_id,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return result
            except Exception as e:
                error_msg = str(e)
                logger.error(f'[ROUTER] Gateway reverse FAILED for {module}.{operation}: {error_msg}')
                RollbackManager.rollback_function(
                    module, operation,
                    reason=f'Gateway reverse exception: {error_msg}',
                )
                Observability.log(
                    module, operation, 'GATEWAY', params, {},
                    drift_score=100, validation_result='FAIL',
                    reference=entry_id,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return {'success': False, 'error': error_msg, 'rolled_back': True}

        result = JournalEngine.reverse_entry(
            entry_id=entry_id,
            reason=reason,
        )
        Observability.log(
            module, operation, 'ENGINE', params, result,
            drift_score=0, validation_result='PASS',
            reference=entry_id,
            duration_ms=int((time.time() - start) * 1000),
        )
        return result

    @staticmethod
    def post_entry(
        module: str,
        operation: str,
        entry_id: str,
        posted_by: str = '',
    ) -> Dict[str, Any]:
        start = time.time()
        use_gateway = MigrationRegistry.is_gateway(module, operation)

        params = {'entry_id': entry_id}

        if use_gateway:
            try:
                result = JournalGateway.post_entry(
                    entry_id=entry_id,
                    posted_by=posted_by,
                )
                Observability.log(
                    module, operation, 'GATEWAY', params, result,
                    drift_score=0, validation_result='PASS',
                    reference=entry_id,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return result
            except Exception as e:
                error_msg = str(e)
                logger.error(f'[ROUTER] Gateway post FAILED for {module}.{operation}: {error_msg}')
                RollbackManager.rollback_function(
                    module, operation,
                    reason=f'Gateway post exception: {error_msg}',
                )
                Observability.log(
                    module, operation, 'GATEWAY', params, {},
                    drift_score=100, validation_result='FAIL',
                    reference=entry_id,
                    duration_ms=int((time.time() - start) * 1000),
                )
                return {'success': False, 'error': error_msg, 'rolled_back': True}

        result = JournalEngine.post_entry(entry_id=entry_id)
        Observability.log(
            module, operation, 'ENGINE', params, result,
            drift_score=0, validation_result='PASS',
            reference=entry_id,
            duration_ms=int((time.time() - start) * 1000),
        )
        return result

    @staticmethod
    def _normalize_lines(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from accounting.models import Account
        result = []
        for line in lines:
            normalized = dict(line)
            if 'account_id' in line and 'account_code' not in line:
                try:
                    account = Account.objects.get(id=line['account_id'])
                    normalized['account_code'] = account.code
                except Account.DoesNotExist:
                    pass
            if 'description' not in normalized:
                normalized['description'] = ''
            result.append(normalized)
        return result
