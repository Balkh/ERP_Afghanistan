import threading
from typing import Dict, Any, Optional
from functools import wraps


_singleton_locks: Dict[str, threading.Lock] = {}


def thread_safe_singleton(cls):
    init_lock = threading.Lock()
    _singleton_locks[cls.__name__] = init_lock

    original_init = cls.__init__

    @wraps(original_init)
    def __init__(self, *args, **kwargs):
        with init_lock:
            if not getattr(self, '_ts_initialized', False):
                original_init(self, *args, **kwargs)
                self._ts_initialized = True

    cls.__init__ = __init__
    return cls


class AtomicCounter:
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, delta: int = 1) -> int:
        with self._lock:
            self._value += delta
            return self._value

    def decrement(self, delta: int = 1) -> int:
        with self._lock:
            self._value -= delta
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def reset(self, value: int = 0):
        with self._lock:
            self._value = value


class ThreadSafeEventBusProxy:
    def __init__(self, event_bus):
        self._bus = event_bus
        self._lock = threading.Lock()

    def publish(self, event_type: str, payload: Dict[str, Any],
                priority: int = 2, source: str = "") -> str:
        with self._lock:
            return self._bus.publish(event_type, payload, priority, source)

    def subscribe(self, event_type: str, handler):
        with self._lock:
            self._bus.subscribe(event_type, handler)

    def process_next(self):
        with self._lock:
            return self._bus.process_next()

    def process_all(self, max_events: int = 0) -> int:
        with self._lock:
            return self._bus.process_all(max_events)

    def get_queue_length(self) -> int:
        with self._lock:
            return self._bus.get_queue_length()

    def get_queue_stats(self) -> Dict[str, int]:
        with self._lock:
            return self._bus.get_queue_stats()

    def clear(self):
        with self._lock:
            self._bus.clear()
