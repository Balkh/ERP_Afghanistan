import logging
from typing import Dict, Any, Optional, List
from enum import Enum, auto

logger = logging.getLogger("c_runner.isolation")


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class ModuleCircuitBreaker:

    def __init__(self, module_name: str, failure_threshold: int = 3,
                 recovery_timeout: int = 60):
        self.module_name = module_name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._history: List[Dict[str, Any]] = []

    def record_failure(self, detail: str = ""):
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._history.append({
            "time": time.time(),
            "failure_count": self._failure_count,
            "detail": detail,
        })
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("[CIRCUIT] %s OPEN after %d failures",
                           self.module_name, self._failure_count)

    def record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("[CIRCUIT] %s CLOSED (recovered)", self.module_name)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    @property
    def is_allowed(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if self._try_recovery():
                return True
            return False
        return True

    def _try_recovery(self) -> bool:
        import time
        if self._last_failure_time is None:
            return True
        elapsed = time.time() - self._last_failure_time
        if elapsed >= self._recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            logger.info("[CIRCUIT] %s HALF_OPEN (recovery window)", self.module_name)
            return True
        return False

    def reset(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    @property
    def state_name(self) -> str:
        return self._state.name

    @property
    def failure_count(self) -> int:
        return self._failure_count


class CascadingFailurePreventer:

    def __init__(self):
        self._breakers: Dict[str, ModuleCircuitBreaker] = {}
        self._module_dependencies: Dict[str, List[str]] = {}
        self._quarantine: set = set()

    def register_module(self, module_name: str, depends_on: Optional[List[str]] = None):
        self._breakers[module_name] = ModuleCircuitBreaker(module_name)
        self._module_dependencies[module_name] = depends_on or []
        if module_name in self._quarantine:
            self._quarantine.remove(module_name)

    def record_failure(self, module_name: str, detail: str = ""):
        breaker = self._breakers.get(module_name)
        if breaker:
            breaker.record_failure(detail)
            if breaker.state_name == "OPEN":
                self._quarantine.add(module_name)

        for dep_mod, deps in self._module_dependencies.items():
            if module_name in deps:
                dep_breaker = self._breakers.get(dep_mod)
                if dep_breaker and dep_breaker.is_allowed:
                    dep_breaker.record_failure(
                        f"Cascade from {module_name}: {detail}"
                    )

    def record_success(self, module_name: str):
        breaker = self._breakers.get(module_name)
        if breaker:
            breaker.record_success()
        if module_name in self._quarantine:
            self._quarantine.remove(module_name)

    def is_module_allowed(self, module_name: str) -> bool:
        if module_name in self._quarantine:
            return False
        breaker = self._breakers.get(module_name)
        if breaker:
            return breaker.is_allowed
        return True

    def get_blocked_modules(self) -> List[str]:
        return [
            name for name, br in self._breakers.items()
            if not br.is_allowed
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "quarantine": list(self._quarantine),
            "breakers": {
                name: {
                    "state": br.state_name,
                    "failures": br.failure_count,
                    "allowed": br.is_allowed,
                }
                for name, br in self._breakers.items()
            },
        }

    def reset_module(self, module_name: str):
        breaker = self._breakers.get(module_name)
        if breaker:
            breaker.reset()
        self._quarantine.discard(module_name)

    def reset_all(self):
        for breaker in self._breakers.values():
            breaker.reset()
        self._quarantine.clear()
