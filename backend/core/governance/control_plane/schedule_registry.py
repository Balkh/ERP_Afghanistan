"""
Phase 1 — OperationalScheduleRegistry.
Defines safe, bounded schedules for drift checks, health snapshots, and certification runs.
No infinite loops. Cooldown-aware.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("erp.governance.control_plane.schedule")


class ScheduleFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MANUAL = "manual"


@dataclass
class ScheduleEntry:
    name: str
    frequency: ScheduleFrequency
    interval_hours: float = 24.0
    max_duration_seconds: int = 120
    cooldown_minutes: int = 5
    allowed_during_degradation: bool = False
    requires_idle: bool = False
    description: str = ""
    timeout_seconds: int = 300


SCHEDULE_DEFAULTS: Dict[ScheduleFrequency, float] = {
    ScheduleFrequency.DAILY: 24.0,
    ScheduleFrequency.WEEKLY: 168.0,
    ScheduleFrequency.MONTHLY: 720.0,
    ScheduleFrequency.MANUAL: 0.0,
}


class OperationalScheduleRegistry:
    """
    Single authoritative registry for all operational schedules.
    Bounded, deterministic, read-only after registration.
    """

    def __init__(self):
        self._entries: Dict[str, ScheduleEntry] = {}
        self._frozen = False
        self._register_defaults()

    def _register_defaults(self) -> None:
        entries = [
            ScheduleEntry(
                name="drift_check",
                frequency=ScheduleFrequency.DAILY,
                interval_hours=24.0,
                max_duration_seconds=30,
                cooldown_minutes=5,
                allowed_during_degradation=True,
                description="Lightweight drift detection scan",
            ),
            ScheduleEntry(
                name="health_snapshot",
                frequency=ScheduleFrequency.DAILY,
                interval_hours=24.0,
                max_duration_seconds=60,
                cooldown_minutes=5,
                allowed_during_degradation=True,
                description="Operational health snapshot collection",
            ),
            ScheduleEntry(
                name="certification_weekly",
                frequency=ScheduleFrequency.WEEKLY,
                interval_hours=168.0,
                max_duration_seconds=300,
                cooldown_minutes=30,
                allowed_during_degradation=False,
                description="Weekly certification health summary",
            ),
            ScheduleEntry(
                name="certification_monthly",
                frequency=ScheduleFrequency.MONTHLY,
                interval_hours=720.0,
                max_duration_seconds=600,
                cooldown_minutes=60,
                allowed_during_degradation=False,
                requires_idle=True,
                description="Full operational certification (optional)",
            ),
            ScheduleEntry(
                name="deployment_readiness",
                frequency=ScheduleFrequency.MANUAL,
                interval_hours=0.0,
                max_duration_seconds=60,
                cooldown_minutes=10,
                allowed_during_degradation=False,
                description="Pre-deployment readiness check",
            ),
        ]
        for entry in entries:
            self._entries[entry.name] = entry

    def register(self, entry: ScheduleEntry) -> None:
        if self._frozen:
            raise RuntimeError("Schedule registry is frozen — no new registrations allowed")
        self._entries[entry.name] = entry

    def freeze(self) -> None:
        self._frozen = True

    def get(self, name: str) -> Optional[ScheduleEntry]:
        return self._entries.get(name)

    def list_all(self) -> Dict[str, ScheduleEntry]:
        return dict(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def is_due(self, name: str, last_run: Optional[datetime] = None) -> bool:
        entry = self.get(name)
        if not entry:
            return False
        if not last_run:
            return True
        elapsed = datetime.utcnow() - last_run
        return elapsed.total_seconds() >= entry.interval_hours * 3600
