import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('erp.simulation.predictive.safety.isolation')


class PredictionFailureIsolation:
    def __init__(self):
        self._failure_count: int = 0
        self._last_failure: Optional[str] = None
        self._in_degraded_mode: bool = False

    def safe_call(self, fn, default_return: Any = None, **kwargs):
        try:
            return fn(**kwargs)
        except Exception as e:
            self._failure_count += 1
            self._last_failure = str(e)
            logger.warning("Prediction failure isolated: %s", e)
            return default_return

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def last_failure(self) -> Optional[str]:
        return self._last_failure

    @property
    def degraded_mode(self) -> bool:
        return self._in_degraded_mode

    def enter_degraded_mode(self):
        self._in_degraded_mode = True
        logger.warning("Predictive system entering degraded mode")

    def exit_degraded_mode(self):
        self._in_degraded_mode = False
        logger.info("Predictive system exiting degraded mode")

    def reset(self):
        self._failure_count = 0
        self._last_failure = None
        self._in_degraded_mode = False
