import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from django.utils import timezone
from core.models.migration_config import MigrationConfig, MigrationLog


class MigrationRegistry:
    """Tracks per-function migration state.

    State machine:
        ENGINE → READY → GATEWAY (forward)
        GATEWAY → ROLLED_BACK (on drift/failure)
        ROLLED_BACK → READY (after manual clear)
    """

    @staticmethod
    def get_state(module: str, function: str) -> str:
        config = MigrationConfig.objects.filter(module=module, function=function).first()
        return config.state if config else 'ENGINE'

    @staticmethod
    def is_gateway(module: str, function: str) -> bool:
        return MigrationRegistry.get_state(module, function) == 'GATEWAY'

    @staticmethod
    def mark_ready(module: str, function: str) -> Dict[str, Any]:
        config, _ = MigrationConfig.objects.get_or_create(
            module=module, function=function,
            defaults={'state': 'READY'},
        )
        config.state = 'READY'
        config.save()
        return {'module': module, 'function': function, 'state': 'READY'}

    @staticmethod
    def mark_gateway(module: str, function: str) -> Dict[str, Any]:
        config, _ = MigrationConfig.objects.get_or_create(
            module=module, function=function,
            defaults={'state': 'GATEWAY', 'switched_at': timezone.now()},
        )
        config.state = 'GATEWAY'
        config.switched_at = timezone.now()
        config.rolled_back_at = None
        config.rollback_reason = ''
        config.drift_count_since_switch = 0
        config.save()
        return {'module': module, 'function': function, 'state': 'GATEWAY', 'switched_at': str(config.switched_at)}

    @staticmethod
    def mark_rolled_back(module: str, function: str, reason: str) -> Dict[str, Any]:
        config, _ = MigrationConfig.objects.get_or_create(
            module=module, function=function,
            defaults={'state': 'ROLLED_BACK', 'rollback_reason': reason, 'rolled_back_at': timezone.now()},
        )
        config.state = 'ROLLED_BACK'
        config.rolled_back_at = timezone.now()
        config.rollback_reason = reason
        config.save()
        return {'module': module, 'function': function, 'state': 'ROLLED_BACK', 'reason': reason}

    @staticmethod
    def mark_engine(module: str, function: str) -> Dict[str, Any]:
        config, _ = MigrationConfig.objects.get_or_create(
            module=module, function=function,
            defaults={'state': 'ENGINE'},
        )
        config.state = 'ENGINE'
        config.save()
        return {'module': module, 'function': function, 'state': 'ENGINE'}

    @staticmethod
    def all_configs() -> List[Dict[str, Any]]:
        configs = MigrationConfig.objects.all().order_by('module', 'function')
        return [
            {
                'module': c.module,
                'function': c.function,
                'state': c.state,
                'switched_at': str(c.switched_at) if c.switched_at else None,
                'rolled_back_at': str(c.rolled_back_at) if c.rolled_back_at else None,
                'rollback_reason': c.rollback_reason,
                'gateway_call_count': c.gateway_call_count,
                'drift_count_since_switch': c.drift_count_since_switch,
            }
            for c in configs
        ]

    @staticmethod
    def get_functions(module: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
        qs = MigrationConfig.objects.filter(module=module)
        if state:
            qs = qs.filter(state=state)
        return [
            {
                'module': c.module,
                'function': c.function,
                'state': c.state,
                'switched_at': str(c.switched_at) if c.switched_at else None,
            }
            for c in qs
        ]

    @staticmethod
    def module_summary(module: str) -> Dict[str, Any]:
        configs = MigrationConfig.objects.filter(module=module)
        total = configs.count()
        gateway = configs.filter(state='GATEWAY').count()
        rolled_back = configs.filter(state='ROLLED_BACK').count()
        ready = configs.filter(state='READY').count()
        engine = configs.filter(state='ENGINE').count()
        return {
            'module': module,
            'total_functions': total,
            'gateway': gateway,
            'rolled_back': rolled_back,
            'ready': ready,
            'engine': engine,
            'migration_progress': f'{gateway}/{total}' if total > 0 else '0/0',
            'percentage': round(gateway / total * 100, 1) if total > 0 else 0.0,
            'is_fully_migrated': gateway > 0 and rolled_back == 0 and engine == 0 and ready == 0,
        }
