from typing import Dict, Any, Optional, List
from core.models.drift_prevention import ModuleDriftState
from core.drift_prevention.registry import DriftRegistry


class PreventionGate:
    """The gate that controls Phase 3 migration permissions.

    If a module has Class C (Financial Drift) or Class D (System Failure)
    drift detected, the gate BLOCKS that module from Phase 3 migration.

    The gate is FINAL — once blocked, only explicit clearing by an administrator
    (via the API or management command) can unblock a module.

    RULES:
        - One Class C drift → module is blocked
        - One Class D drift → module is blocked
        - Blocked module → cannot proceed to Phase 3
        - Block is sticky — persists across restarts via database
        - Clearing requires explicit acknowledgment (cleared_by, clear_reason)
    """

    BLOCKED_MODULES_KEY = 'drift_prevention:blocked_modules'

    @staticmethod
    def is_blocked(module: str) -> bool:
        """Check if a specific module is blocked from Phase 3 migration.

        Returns:
            True if the module has any unrecovered Class C or D drift
        """
        return DriftRegistry.is_module_blocked(module)

    @staticmethod
    def get_blocked_modules() -> List[str]:
        """Get list of all blocked module names."""
        return list(
            ModuleDriftState.objects
            .filter(is_blocked=True)
            .values_list('module', flat=True)
        )

    @staticmethod
    def get_allowed_modules() -> List[str]:
        """Get list of modules that are safe for Phase 3 migration."""
        return list(
            ModuleDriftState.objects
            .filter(is_blocked=False)
            .values_list('module', flat=True)
        )

    @staticmethod
    def module_status(module: str) -> Dict[str, Any]:
        """Get detailed migration status for a module."""
        state = DriftRegistry.get_module_state(module)
        if not state:
            return {
                'module': module,
                'status': 'UNKNOWN',
                'migration_allowed': True,
                'reason': 'No drift records — module not yet tracked',
                'latest_classification': 'A',
                'total_comparisons': 0,
                'class_c_count': 0,
                'class_d_count': 0,
            }

        return {
            'module': module,
            'status': 'BLOCKED' if state.is_blocked else 'ALLOWED',
            'migration_allowed': not state.is_blocked,
            'reason': state.block_reason if state.is_blocked else 'No blocking drift detected',
            'latest_classification': state.latest_classification,
            'total_comparisons': state.total_comparisons,
            'class_c_count': state.class_c_count,
            'class_d_count': state.class_d_count,
            'last_drift_at': str(state.last_drift_at) if state.last_drift_at else None,
            'last_checked_at': str(state.last_checked_at),
        }

    @staticmethod
    def block_module(module: str, reason: str) -> Dict[str, Any]:
        """Manually block a module from Phase 3 migration."""
        state, created = ModuleDriftState.objects.get_or_create(
            module=module,
            defaults={
                'is_blocked': True,
                'block_reason': reason,
                'latest_classification': 'D',
                'total_comparisons': 0,
                'class_c_count': 0,
                'class_d_count': 0,
            },
        )

        if not created:
            state.is_blocked = True
            state.block_reason = reason
            state.save()

        return {
            'module': module,
            'status': 'BLOCKED',
            'reason': reason,
        }

    @staticmethod
    def unblock_module(module: str, cleared_by: str, clear_reason: str) -> Dict[str, Any]:
        """Manually unblock a module (requires explicit acknowledgment)."""
        state = DriftRegistry.get_module_state(module)
        if not state:
            return {
                'module': module,
                'status': 'NOT_TRACKED',
                'error': f'Module {module} has no drift state',
            }

        state.is_blocked = False
        state.block_reason = (
            f'CLEARED by {cleared_by}: {clear_reason}. '
            f'Previous block: {state.block_reason}. '
            f'Class C count: {state.class_c_count}, Class D count: {state.class_d_count}'
        )
        state.save()

        return {
            'module': module,
            'status': 'ALLOWED',
            'cleared_by': cleared_by,
            'reason': clear_reason,
        }

    @staticmethod
    def all_module_statuses() -> List[Dict[str, Any]]:
        """Get migration status for ALL tracked modules."""
        states = DriftRegistry.get_all_states()
        results = []
        for state in states:
            results.append({
                'module': state.module,
                'status': 'BLOCKED' if state.is_blocked else 'ALLOWED',
                'migration_allowed': not state.is_blocked,
                'reason': state.block_reason if state.is_blocked else '',
                'latest_classification': state.latest_classification,
                'total_comparisons': state.total_comparisons,
                'class_c_count': state.class_c_count,
                'class_d_count': state.class_d_count,
            })
        return results
