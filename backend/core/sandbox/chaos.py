import logging
import random
import uuid
from typing import Any, Dict, Optional

from core.sandbox.models import FailureConfig

logger = logging.getLogger(__name__)


class FailureInjectionEngine:
    _instance = None
    _initialized = False

    def __init__(self):
        if not FailureInjectionEngine._initialized:
            self._config = FailureConfig()
            self._injection_log: list = []
            FailureInjectionEngine._initialized = True

    @classmethod
    def get_instance(cls) -> "FailureInjectionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def enable(
        self,
        fk_violation_prob: float = 0.0,
        invalid_op_prob: float = 0.0,
        partial_failure_prob: float = 0.0,
        corruption_prob: float = 0.0,
    ):
        self._config = FailureConfig(
            enabled=True,
            fk_violation_probability=fk_violation_prob,
            invalid_op_probability=invalid_op_prob,
            partial_failure_probability=partial_failure_prob,
            corruption_probability=corruption_prob,
        )

    def disable(self):
        self._config.enabled = False

    def is_enabled(self) -> bool:
        return self._config.enabled

    def get_config(self) -> FailureConfig:
        return self._config

    def maybe_inject(
        self, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not self._config.enabled:
            return None

        roll = random.random()

        if roll < self._config.fk_violation_probability:
            return self._inject_fk_violation(context)

        roll -= self._config.fk_violation_probability
        if roll < self._config.invalid_op_probability:
            return self._inject_invalid_op(context)

        roll -= self._config.invalid_op_probability
        if roll < self._config.partial_failure_probability:
            return self._inject_partial_failure(context)

        roll -= self._config.partial_failure_probability
        if roll < self._config.corruption_probability:
            return self._inject_corruption(context)

        return None

    def _inject_fk_violation(self, context=None) -> Dict[str, Any]:
        injection = {
            "type": "FK_VIOLATION",
            "description": "Simulated FK violation",
            "injected_id": str(uuid.uuid4())[:8],
            "target_field": "non_existent_foreign_key",
        }
        self._injection_log.append(injection)
        logger.warning(
            f"[CHAOS] Injected FK violation: {injection['injected_id']}"
        )
        return injection

    def _inject_invalid_op(self, context=None) -> Dict[str, Any]:
        injection = {
            "type": "INVALID_OPERATION",
            "description": "Simulated invalid operation",
            "injected_id": str(uuid.uuid4())[:8],
            "operation": "DELETE_SYSTEM_TABLE",
        }
        self._injection_log.append(injection)
        logger.warning(
            f"[CHAOS] Injected invalid op: {injection['injected_id']}"
        )
        return injection

    def _inject_partial_failure(self, context=None) -> Dict[str, Any]:
        injection = {
            "type": "PARTIAL_FAILURE",
            "description": "Simulated partial transaction failure",
            "injected_id": str(uuid.uuid4())[:8],
        }
        self._injection_log.append(injection)
        logger.warning(
            f"[CHAOS] Injected partial failure: {injection['injected_id']}"
        )
        return injection

    def _inject_corruption(self, context=None) -> Dict[str, Any]:
        injection = {
            "type": "DATA_CORRUPTION",
            "description": "Simulated data corruption attempt",
            "injected_id": str(uuid.uuid4())[:8],
            "corrupted_field": "random_numeric_value",
            "corrupted_value": -999999,
        }
        self._injection_log.append(injection)
        logger.warning(
            f"[CHAOS] Injected corruption: {injection['injected_id']}"
        )
        return injection

    def get_injection_log(self, limit: int = 100) -> list:
        return self._injection_log[-limit:]

    def count_injections(self) -> int:
        return len(self._injection_log)

    def clear_log(self):
        self._injection_log.clear()
