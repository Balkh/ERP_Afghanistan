"""
Lightweight dev-only profiling hooks for measuring UI performance.
No-op in production — only active when DEBUG_PROFILE env var is set.

Usage:
    @profile_call
    def load_data(self):
        ...

    with profile_block("refresh"):
        ...
"""

import os
import time
from functools import wraps

_ENABLED = os.environ.get("DEBUG_PROFILE", "").lower() in ("1", "true", "yes")

_profile_data = {}  # name -> [count, total_ms]


def profile_call(fn):
    """Decorator that records call count and total duration."""
    if not _ENABLED:
        return fn

    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = (time.monotonic() - start) * 1000
            key = f"{fn.__module__}.{fn.__qualname__}"
            data = _profile_data.setdefault(key, [0, 0.0])
            data[0] += 1
            data[1] += elapsed

    return wrapper


class profile_block:
    """Context manager that times a block of code."""

    def __init__(self, name):
        self._name = name

    def __enter__(self):
        if _ENABLED:
            self._start = time.monotonic()
        return self

    def __exit__(self, *args):
        if _ENABLED:
            elapsed = (time.monotonic() - self._start) * 1000
            data = _profile_data.setdefault(self._name, [0, 0.0])
            data[0] += 1
            data[1] += elapsed


def dump_profile():
    """Print profiling summary to stdout."""
    if not _profile_data:
        return
    print("\n=== PROFILE DUMP ===")
    print(f"{'Name':<60} {'Calls':>8} {'Total(ms)':>12} {'Avg(ms)':>10}")
    for name, (count, total_ms) in sorted(
        _profile_data.items(), key=lambda x: -x[1][1]
    ):
        avg = total_ms / max(count, 1)
        print(f"{name:<60} {count:>8} {total_ms:>12.1f} {avg:>10.1f}")
    print("===================\n")


def reset_profile():
    _profile_data.clear()
