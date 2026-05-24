import logging
from typing import Dict, Any, Optional
from core.drift_prevention.migration_registry import MigrationRegistry
from core.drift_prevention.equilibrium_checker import EquilibriumChecker
from core.drift_prevention.pattern_detector import PatternDriftDetector

logger = logging.getLogger('erp.switchover.rollback')


class RollbackManager:
    """Handles function-level and module-level rollback.

    Rollback means:
        1. Mark the function/module as ROLLED_BACK
        2. Restore JournalEngine as the active execution path
        3. Log the reason
        4. If pattern drift detected, auto-block
    """

    @staticmethod
    def rollback_function(
        module: str,
        function: str,
        reason: str,
        equilibrium_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.warning(
            f'[ROLLBACK] Rolling back {module}.{function}: {reason}'
        )

        result = MigrationRegistry.mark_rolled_back(module, function, reason)

        if equilibrium_result:
            drift_count = equilibrium_result.get('total_differences', 0)
            result['drift_count'] = drift_count

        if PatternDriftDetector.should_block_module(module):
            logger.warning(f'[ROLLBACK] Pattern drift detected in {module} — module auto-blocked.')
            result['module_blocked'] = True

        return result

    @staticmethod
    def rollback_module(module: str, reason: str) -> Dict[str, Any]:
        configs = MigrationRegistry.get_functions(module)
        results = []
        for cfg in configs:
            func = cfg['function']
            r = MigrationRegistry.mark_rolled_back(module, func, reason)
            results.append(r)

        logger.warning(f'[ROLLBACK] Full module rollback {module}: {len(results)} functions reverted.')

        return {
            'module': module,
            'functions_rolled_back': len(results),
            'reason': reason,
            'details': results,
        }

    @staticmethod
    def can_retry(module: str, function: str) -> bool:
        state = MigrationRegistry.get_state(module, function)
        if state == 'ROLLED_BACK':
            drift = PatternDriftDetector.analyze_module(module)
            if drift.get('has_emerging_pattern'):
                logger.warning(f'[ROLLBACK] {module}.{function} has emerging pattern — retry blocked.')
                return False
        return state in ('ENGINE', 'READY', 'ROLLED_BACK')
