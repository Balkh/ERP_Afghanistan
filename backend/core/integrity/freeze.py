import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.integrity.models import FreezeState, IntegrityEvent

logger = logging.getLogger(__name__)


class SystemFreezeKillSwitch:
    _instance = None
    _initialized = False

    def __init__(self):
        if not SystemFreezeKillSwitch._initialized:
            self._state: FreezeState = FreezeState.UNFROZEN
            self._freeze_reason: str = ""
            self._frozen_by: str = ""
            self._frozen_at: Optional[str] = None
            self._approval_required: bool = True
            SystemFreezeKillSwitch._initialized = True

    @classmethod
    def get_instance(cls) -> "SystemFreezeKillSwitch":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def freeze(self, reason: str, frozen_by: str = "system") -> Dict[str, Any]:
        was_frozen = self._state == FreezeState.FROZEN
        self._state = FreezeState.FROZEN
        self._freeze_reason = reason
        self._frozen_by = frozen_by
        self._frozen_at = datetime.now(timezone.utc).isoformat()
        logger.critical(
            f"[INTEGRITY] SYSTEM FREEZE: {reason} (by={frozen_by})"
        )
        return {
            "state": self._state.value,
            "reason": reason,
            "frozen_by": frozen_by,
            "frozen_at": self._frozen_at,
            "was_already_frozen": was_frozen,
        }

    def unfreeze(
        self, approver: str = "", reason: str = ""
    ) -> Dict[str, Any]:
        if self._approval_required and not approver:
            return {
                "state": self._state.value,
                "error": "Approval required to unfreeze",
                "unfrozen": False,
            }
        self._state = FreezeState.UNFROZEN
        self._freeze_reason = ""
        self._frozen_by = ""
        logger.info(
            f"[INTEGRITY] SYSTEM UNFROZEN (by={approver}, reason={reason})"
        )
        return {
            "state": self._state.value,
            "unfrozen_by": approver,
            "reason": reason,
            "unfrozen": True,
        }

    def is_frozen(self) -> bool:
        return self._state in (FreezeState.FROZEN, FreezeState.PERMANENT_FREEZE)

    def require_unfrozen(self) -> Optional[Dict[str, Any]]:
        if self.is_frozen():
            return {
                "allowed": False,
                "error": f"System frozen: {self._freeze_reason}",
                "state": self._state.value,
            }
        return None

    def permanent_freeze(self, reason: str) -> Dict[str, Any]:
        self._state = FreezeState.PERMANENT_FREEZE
        self._freeze_reason = reason
        logger.critical(
            f"[INTEGRITY] PERMANENT SYSTEM FREEZE: {reason}"
        )
        return {
            "state": self._state.value,
            "reason": reason,
            "permanent": True,
        }

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "reason": self._freeze_reason,
            "frozen_by": self._frozen_by,
            "frozen_at": self._frozen_at,
        }

    def set_approval_required(self, required: bool):
        self._approval_required = required


class ImmutableIntegrityLedger:
    _instance = None
    _initialized = False

    def __init__(self):
        if not ImmutableIntegrityLedger._initialized:
            self._events: List[IntegrityEvent] = []
            self._max_events: int = 10000
            ImmutableIntegrityLedger._initialized = True

    @classmethod
    def get_instance(cls) -> "ImmutableIntegrityLedger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log_event(self, event: IntegrityEvent) -> int:
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)
        return len(self._events)

    def log(
        self,
        operation_type: str = "",
        model_class: str = "",
        validation_result: str = "",
        verification_result: str = "",
        failure_reason: str = "",
        system_hash: str = "",
        rolled_back: bool = False,
        frozen: bool = False,
    ) -> int:
        event = IntegrityEvent(
            operation_type=operation_type,
            model_class=model_class,
            validation_result=validation_result,
            verification_result=verification_result,
            failure_reason=failure_reason,
            system_hash=system_hash,
            rolled_back=rolled_back,
            frozen=frozen,
        )
        return self.log_event(event)

    def get_events(
        self, since: Optional[str] = None, limit: int = 100
    ) -> List[IntegrityEvent]:
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

    def get_recent(self, limit: int = 50) -> List[IntegrityEvent]:
        return self._events[-limit:]

    def count(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._events)
        rollbacks = sum(1 for e in self._events if e.rolled_back)
        freezes = sum(1 for e in self._events if e.frozen)
        failures = sum(
            1
            for e in self._events
            if e.verification_result in ("FAIL", "ROLLBACK")
            or e.validation_result == "BLOCKED"
        )
        return {
            "total_events": total,
            "rollbacks": rollbacks,
            "freezes": freezes,
            "failures": failures,
            "clean": total - failures,
        }
