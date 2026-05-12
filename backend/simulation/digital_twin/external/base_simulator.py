from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List, Optional


class ExternalSystemSimulator(ABC):
    def __init__(self, name: str, config: Dict[str, Any] = None, seed: int = 42):
        self.name = name
        self.config = config or {}
        self._initial_seed = seed
        self._rng_state = seed
        self._request_history = deque(maxlen=1000)
        self._total_requests = 0
        self._failure_count = 0
        self._success_count = 0
        self._uptime = 100.0
        self._latency_range = self.config.get('latency_range', (1, 3))
        self._failure_rate = self.config.get('failure_rate', 0.0)
        self._failure_modes = self.config.get('failure_modes', [])

    def _next_int(self, max_val: int) -> int:
        if max_val <= 0:
            return 0
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0x7fffffff
        return self._rng_state % max_val

    def simulate_latency(self) -> int:
        min_ticks, max_ticks = self._latency_range
        if min_ticks >= max_ticks:
            return min_ticks
        return min_ticks + self._next_int(max_ticks - min_ticks + 1)

    def simulate_failure(self) -> Optional[str]:
        if self._failure_rate <= 0.0 or not self._failure_modes:
            return None
        if self._next_int(100) / 100.0 < self._failure_rate:
            idx = self._next_int(len(self._failure_modes))
            return self._failure_modes[idx]
        return None

    def _record_request(self, operation: str, request: Dict, response: Dict) -> None:
        self._total_requests += 1
        if response.get('success', False):
            self._success_count += 1
        else:
            self._failure_count += 1
        self._request_history.append({
            'operation': operation,
            'request': dict(request),
            'response': dict(response),
        })

    def get_health(self) -> Dict:
        total = self._total_requests
        success_rate = (self._success_count / total * 100.0) if total > 0 else 100.0
        return {
            'name': self.name,
            'total_requests': total,
            'failure_count': self._failure_count,
            'success_rate': round(success_rate, 2),
            'uptime': self._uptime,
        }

    def get_request_history(self) -> List[Dict]:
        return list(self._request_history)

    def reset(self) -> None:
        self._rng_state = self._initial_seed
        self._total_requests = 0
        self._failure_count = 0
        self._success_count = 0

    def clear(self) -> None:
        self.reset()
        self._request_history.clear()
