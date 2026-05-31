from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CommandStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"


@dataclass
class SandboxEvent:
    event_id: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = ""
    processed: bool = False
    result: Optional[Dict[str, Any]] = None


@dataclass
class ERPCommand:
    command_id: str
    command_type: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    status: CommandStatus = CommandStatus.PENDING
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ExecutionResult:
    success: bool
    command_id: str = ""
    command_type: str = ""
    result: Any = None
    error: str = ""
    rolled_back: bool = False
    integrity_passed: bool = True
    duration_ms: float = 0.0
    chaos_injected: bool = False

    @classmethod
    def ok(cls, command_id="", command_type="", result=None, duration=0.0):
        return cls(
            success=True,
            command_id=command_id,
            command_type=command_type,
            result=result,
            duration_ms=duration,
        )

    @classmethod
    def fail(cls, command_id="", command_type="", error="", rolled_back=False):
        return cls(
            success=False,
            command_id=command_id,
            command_type=command_type,
            error=error,
            rolled_back=rolled_back,
        )


@dataclass
class ReplayEntry:
    sequence_id: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_type: str = ""
    command_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    integrity_result: str = ""
    chaos_injected: bool = False


@dataclass
class ObservabilitySnapshot:
    commands_executed: int = 0
    commands_succeeded: int = 0
    commands_failed: int = 0
    commands_rolled_back: int = 0
    commands_blocked: int = 0
    chaos_injections: int = 0
    integrity_violations: int = 0
    freeze_triggers: int = 0
    avg_duration_ms: float = 0.0
    uptime_seconds: float = 0.0


@dataclass
class FailureConfig:
    enabled: bool = False
    fk_violation_probability: float = 0.0
    invalid_op_probability: float = 0.0
    partial_failure_probability: float = 0.0
    corruption_probability: float = 0.0
