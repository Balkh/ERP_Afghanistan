import time
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from collections import deque
from dataclasses import dataclass, field
from core.runner.workload_generator import BusinessEvent

logger = logging.getLogger("c_runner.reliability")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    backoff_factor: float = 2.0
    max_delay_seconds: float = 5.0


@dataclass
class DeadLetterRecord:
    event: BusinessEvent
    error: str
    attempts: int
    timestamp: str
    category: str = "unclassified"


class RetryHandler:

    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
        self._retry_log: List[Dict[str, Any]] = []

    def execute(
        self,
        event: BusinessEvent,
        executor: Callable[[BusinessEvent], bool],
    ) -> bool:
        last_error = ""
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                result = executor(event)
                if result:
                    if attempt > 1:
                        logger.info("[RETRY] Event %s succeeded on attempt %d",
                                    event.event_type, attempt)
                    return True
                last_error = f"executor returned False"
            except Exception as e:
                last_error = str(e)
                logger.warning("[RETRY] Event %s attempt %d failed: %s",
                               event.event_type, attempt, last_error)

            if attempt < self.policy.max_attempts:
                delay = min(
                    self.policy.base_delay_seconds * (self.policy.backoff_factor ** (attempt - 1)),
                    self.policy.max_delay_seconds,
                )
                time.sleep(delay)

        self._retry_log.append({
            "event_type": event.event_type,
            "module": event.module.value,
            "attempts": self.policy.max_attempts,
            "last_error": last_error,
        })
        logger.error("[RETRY] Event %s exhausted %d attempts: %s",
                     event.event_type, self.policy.max_attempts, last_error)
        return False

    @property
    def retry_count(self) -> int:
        return len(self._retry_log)


class DeadLetterQueue:

    def __init__(self, max_size: int = 1000):
        self._queue: deque = deque(maxlen=max_size)
        self._max_size = max_size

    def enqueue(self, record: DeadLetterRecord):
        self._queue.append(record)
        if len(self._queue) >= self._max_size:
            logger.warning("[DLQ] Capacity warning: %d/%d", len(self._queue), self._max_size)

    def replay(self, handler: Callable[[DeadLetterRecord], bool]) -> int:
        replayed = 0
        remaining = deque()
        while self._queue:
            record = self._queue.popleft()
            try:
                if handler(record):
                    replayed += 1
                else:
                    remaining.append(record)
            except Exception:
                remaining.append(record)
        self._queue = remaining
        return replayed

    @property
    def size(self) -> int:
        return len(self._queue)

    def peek(self, n: int = 10) -> List[DeadLetterRecord]:
        return list(self._queue)[:n]

    def clear(self):
        self._queue.clear()


class IdempotencyChecker:

    def __init__(self, window_size: int = 1000):
        self._seen: Dict[str, float] = {}
        self._window_size = window_size

    def _make_key(self, event: BusinessEvent) -> str:
        raw = f"{event.module.value}:{event.event_type}:{json.dumps(event.payload, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_duplicate(self, event: BusinessEvent) -> bool:
        key = self._make_key(event)
        return key in self._seen

    def mark_seen(self, event: BusinessEvent):
        key = self._make_key(event)
        self._seen[key] = time.time()
        if len(self._seen) > self._window_size:
            self._evict_old()

    def _evict_old(self):
        cutoff = time.time() - 3600
        self._seen = {k: v for k, v in self._seen.items() if v > cutoff}

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    def clear(self):
        self._seen.clear()
