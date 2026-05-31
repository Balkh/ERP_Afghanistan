import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.sandbox.models import ObservabilitySnapshot

logger = logging.getLogger(__name__)


class ObservabilityLayer:
    _instance = None
    _initialized = False

    def __init__(self):
        if not ObservabilityLayer._initialized:
            self._start_time: float = time.monotonic()
            self._total_commands: int = 0
            self._succeeded: int = 0
            self._failed: int = 0
            self._rolled_back: int = 0
            self._blocked: int = 0
            self._chaos_injections: int = 0
            self._integrity_violations: int = 0
            self._freeze_triggers: int = 0
            self._durations: List[float] = []
            self._events_processed: int = 0
            ObservabilityLayer._initialized = True

    @classmethod
    def get_instance(cls) -> "ObservabilityLayer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_success(self, duration_ms: float = 0.0):
        self._total_commands += 1
        self._succeeded += 1
        self._durations.append(duration_ms)

    def record_failure(self, duration_ms: float = 0.0):
        self._total_commands += 1
        self._failed += 1
        self._durations.append(duration_ms)

    def record_rollback(self):
        self._rolled_back += 1

    def record_blocked(self):
        self._blocked += 1

    def record_chaos_injection(self):
        self._chaos_injections += 1

    def record_integrity_violation(self):
        self._integrity_violations += 1

    def record_freeze_trigger(self):
        self._freeze_triggers += 1

    def record_event_processed(self):
        self._events_processed += 1

    def record_execution_result(self, result) -> str:
        if result.success:
            self.record_success(result.duration_ms)
            return "SUCCESS"
        else:
            self.record_failure(result.duration_ms)
            if result.rolled_back:
                self.record_rollback()
            return "FAILED"

    def get_snapshot(self) -> ObservabilitySnapshot:
        uptime = (time.monotonic() - self._start_time)
        avg_dur = (
            sum(self._durations) / len(self._durations)
            if self._durations else 0.0
        )
        return ObservabilitySnapshot(
            commands_executed=self._total_commands,
            commands_succeeded=self._succeeded,
            commands_failed=self._failed,
            commands_rolled_back=self._rolled_back,
            commands_blocked=self._blocked,
            chaos_injections=self._chaos_injections,
            integrity_violations=self._integrity_violations,
            freeze_triggers=self._freeze_triggers,
            avg_duration_ms=round(avg_dur, 2),
            uptime_seconds=round(uptime, 2),
        )

    def get_report(self) -> Dict[str, Any]:
        s = self.get_snapshot()
        success_rate = (
            (s.commands_succeeded / s.commands_executed * 100)
            if s.commands_executed > 0 else 0.0
        )
        return {
            "snapshot": s,
            "success_rate": round(success_rate, 2),
            "events_processed": self._events_processed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "durations": {
                "avg_ms": s.avg_duration_ms,
                "samples": len(self._durations),
            },
        }

    def reset(self):
        self._start_time = time.monotonic()
        self._total_commands = 0
        self._succeeded = 0
        self._failed = 0
        self._rolled_back = 0
        self._blocked = 0
        self._chaos_injections = 0
        self._integrity_violations = 0
        self._freeze_triggers = 0
        self._durations.clear()
        self._events_processed = 0
