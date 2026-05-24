"""
Phase 5B.13 — Timer Registry.

Global QTimer tracking to prevent timer leaks on navigation/shutdown.
All timers must be registered here for centralized lifecycle management.
"""
from typing import Any, Dict, List
from PySide6.QtCore import QTimer


_timers: Dict[int, QTimer] = {}
_owner_map: Dict[str, List[int]] = {}
_next_id: int = 0
MAX_TIMERS = 50
_skipped_refreshes: Dict[str, int] = {}
_metrics: Dict[str, int] = {
    "total_timer_fires": 0,
    "total_skipped": 0,
    "total_loads": 0,
}


def register_timer(owner_id: str, timer: QTimer) -> int:
    """Register a timer for lifecycle tracking.

    Args:
        owner_id: Unique identifier for the owning screen/module.
        timer: The QTimer instance to track.

    Returns:
        timer_id for later unregistration.
    """
    global _next_id
    if len(_timers) >= MAX_TIMERS:
        oldest_id = next(iter(_timers))
        unregister_timer(oldest_id)

    tid = _next_id
    _next_id += 1
    _timers[tid] = timer
    if owner_id not in _owner_map:
        _owner_map[owner_id] = []
    _owner_map[owner_id].append(tid)
    return tid


def unregister_timer(timer_id: int) -> None:
    """Unregister a timer by ID."""
    timer = _timers.pop(timer_id, None)
    if timer and timer.isActive():
        timer.stop()
    for owner, tids in list(_owner_map.items()):
        if timer_id in tids:
            tids.remove(timer_id)
            if not tids:
                del _owner_map[owner]


def unregister_owner(owner_id: str) -> None:
    """Stop and unregister all timers for an owner."""
    tids = _owner_map.pop(owner_id, [])
    for tid in tids:
        timer = _timers.pop(tid, None)
        if timer and timer.isActive():
            timer.stop()


def active_timer_count() -> int:
    return len(_timers)


def shutdown_all_timers() -> None:
    """Stop all tracked timers. Call on application shutdown."""
    for tid in list(_timers.keys()):
        unregister_timer(tid)
    _owner_map.clear()


def get_owner_timer_count(owner_id: str) -> int:
    return len(_owner_map.get(owner_id, []))

def record_skipped_refresh(endpoint: str) -> None:
    _skipped_refreshes[endpoint] = _skipped_refreshes.get(endpoint, 0) + 1
    _metrics["total_skipped"] += 1

def record_timer_fire() -> None:
    _metrics["total_timer_fires"] += 1

def record_load() -> None:
    _metrics["total_loads"] += 1

def get_perf_metrics() -> Dict[str, Any]:
    return {
        **_metrics,
        "active_timers": len(_timers),
        "owners": len(_owner_map),
        "skipped_by_endpoint": dict(sorted(_skipped_refreshes.items(), key=lambda x: -x[1])[:20]),
        "max_timers": MAX_TIMERS,
    }

def reset_metrics() -> None:
    _skipped_refreshes.clear()
    for k in _metrics:
        _metrics[k] = 0
