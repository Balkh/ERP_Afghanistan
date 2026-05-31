"""
Phase 1 — ExecutionPolicyEngine.
Ensures safe execution ordering, prevents conflicting simultaneous operations,
and enforces cooldown periods. Fail-safe.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from core.governance.control_plane.schedule_registry import ScheduleEntry

logger = logging.getLogger("erp.governance.control_plane.execution")


class ExecutionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"


class ConflictError(RuntimeError):
    """Raised when conflicting operations would overlap."""
    pass


@dataclass
class ExecutionState:
    status: ExecutionStatus = ExecutionStatus.IDLE
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    last_error: str = ""


_CONFLICT_GROUPS: Dict[str, Set[str]] = {
    "certification": {"certification_weekly", "certification_monthly"},
    "health": {"health_snapshot", "drift_check"},
    "deployment": {"deployment_readiness"},
}

_CERTIFICATION_GROUP = {"certification_weekly", "certification_monthly"}
_HEALTH_GROUP = {"health_snapshot", "drift_check"}


class ExecutionPolicyEngine:
    """
    Prevents conflicting simultaneous operations, enforces cooldowns,
    and ensures safe execution ordering. Thread-safe.
    """

    def __init__(self):
        self._states: Dict[str, ExecutionState] = {}
        self._lock = threading.Lock()
        self._global_lock = threading.Lock()

    def can_execute(self, name: str, entry: ScheduleEntry, force: bool = False) -> bool:
        with self._lock:
            state = self._states.get(name, ExecutionState())
            if not force and state.status == ExecutionStatus.RUNNING:
                return False
            if not force and state.status == ExecutionStatus.COOLDOWN:
                if state.completed_at:
                    elapsed = time.time() - state.completed_at
                    if elapsed < entry.cooldown_minutes * 60:
                        return False
            conflict = self._detect_conflict(name)
            if conflict and not force:
                return False
            return True

    def start_execution(self, name: str) -> bool:
        with self._lock:
            state = self._states.get(name, ExecutionState())
            if state.status == ExecutionStatus.RUNNING:
                return False
            conflict = self._detect_conflict(name)
            if conflict:
                return False
            self._states[name] = ExecutionState(
                status=ExecutionStatus.RUNNING,
                started_at=time.time(),
            )
            return True

    def end_execution(self, name: str, error: str = "") -> None:
        with self._lock:
            self._states[name] = ExecutionState(
                status=ExecutionStatus.COOLDOWN,
                started_at=self._states.get(name, ExecutionState()).started_at,
                completed_at=time.time(),
                last_error=error,
            )

    def get_state(self, name: str) -> ExecutionState:
        with self._lock:
            return self._states.get(name, ExecutionState())

    def list_states(self) -> Dict[str, ExecutionState]:
        with self._lock:
            return dict(self._states)

    def _detect_conflict(self, name: str) -> bool:
        for group_name, members in _CONFLICT_GROUPS.items():
            if name in members:
                for member in members:
                    if member == name:
                        continue
                    state = self._states.get(member)
                    if state and state.status == ExecutionStatus.RUNNING:
                        return True
        return False

    def reset(self, name: str) -> None:
        with self._lock:
            self._states.pop(name, None)
