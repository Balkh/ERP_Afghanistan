import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type

from django.db import models

from core.integrity.engine import IntegrityEngine
from core.integrity.models import OperationType
from core.sandbox.event_bus import EventBus
from core.sandbox.models import (
    CommandStatus,
    EventPriority,
    ExecutionResult,
)
from core.sandbox.processor import CommandProcessor, ConcurrencyManager
from core.sandbox.chaos import FailureInjectionEngine
from core.sandbox.bridge import IntegrityBridge, ReplayBuffer
from core.sandbox.observability import ObservabilityLayer

logger = logging.getLogger(__name__)


class SandboxEngine:
    _instance = None
    _initialized = False

    def __init__(self):
        if not SandboxEngine._initialized:
            self._event_bus: Optional[EventBus] = None
            self._processor: Optional[CommandProcessor] = None
            self._concurrency: Optional[ConcurrencyManager] = None
            self._chaos: Optional[FailureInjectionEngine] = None
            self._bridge: Optional[IntegrityBridge] = None
            self._replay: Optional[ReplayBuffer] = None
            self._observability: Optional[ObservabilityLayer] = None
            self._int_engine: Optional[IntegrityEngine] = None
            self._chaos_mode: bool = False
            self._initialized_at: float = time.monotonic()
            SandboxEngine._initialized = True

    @classmethod
    def get_instance(cls) -> "SandboxEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        self._event_bus = EventBus.get_instance()
        self._processor = CommandProcessor.get_instance()
        self._concurrency = ConcurrencyManager.get_instance()
        self._chaos = FailureInjectionEngine.get_instance()
        self._bridge = IntegrityBridge.get_instance()
        self._replay = ReplayBuffer.get_instance()
        self._observability = ObservabilityLayer.get_instance()
        self._int_engine = IntegrityEngine.get_instance()
        self._int_engine.configure()
        self._bridge.connect(self._int_engine)
        self._register_core_event_handlers()

    def _register_core_event_handlers(self):
        def handle_command_event(event):
            cmd_type = event.payload.get("command_type", "")
            payload = event.payload.get("payload", {})
            result = self._execute_command_direct(cmd_type, payload)
            return result

        self._event_bus.subscribe("command.execute", handle_command_event)

    def enable_chaos(self, **kwargs):
        self._chaos_mode = True
        self._chaos.enable(**kwargs)
        logger.info("[SANDBOX] Chaos mode enabled")

    def disable_chaos(self):
        self._chaos_mode = False
        self._chaos.disable()
        logger.info("[SANDBOX] Chaos mode disabled")

    def register_command(self, command_type: str, handler: Callable):
        self._processor.register_command(command_type, handler)

    def run_command(
        self,
        command_type: str,
        payload: Dict[str, Any],
        model_class: Optional[Type[models.Model]] = None,
        operation_type: Optional[OperationType] = None,
        data: Optional[Dict[str, Any]] = None,
        verify_after: bool = True,
        chaos_mode: Optional[bool] = None,
    ) -> ExecutionResult:
        start = time.monotonic()

        use_chaos = (
            chaos_mode if chaos_mode is not None else self._chaos_mode
        )

        if use_chaos:
            injection = self._chaos.maybe_inject()
            if injection:
                self._observability.record_chaos_injection()
                inj_type = injection.get("type", "")
                if inj_type == "FK_VIOLATION":
                    data = data or {}
                    data["_chaos_fk_break"] = injection["injected_id"]
                elif inj_type == "INVALID_OPERATION":
                    return ExecutionResult.fail(
                        command_type=command_type,
                        error=f"Chaos injection: {injection['description']}",
                    )
                elif inj_type == "PARTIAL_FAILURE":
                    return ExecutionResult.fail(
                        command_type=command_type,
                        error=f"Chaos injection: {injection['description']}",
                        rolled_back=True,
                    )
                elif inj_type == "DATA_CORRUPTION":
                    data = data or {}
                    data[injection["corrupted_field"]] = injection["corrupted_value"]

        event_id = self._event_bus.publish(
            event_type="command.execute",
            payload={
                "command_type": command_type,
                "payload": payload,
                "model_class": model_class._meta.label_lower if model_class else None,
                "operation_type": operation_type.value if operation_type else None,
                "data": data,
                "verify_after": verify_after,
            },
        )

        result = self._execute_command_direct(
            command_type=command_type,
            payload=payload,
            model_class=model_class,
            operation_type=operation_type,
            data=data,
            verify_after=verify_after,
        )

        if result.success:
            result_msg = "SUCCESS"
        elif result.rolled_back:
            result_msg = "ROLLED_BACK"
        else:
            result_msg = "FAILED"

        seq = self._replay.record(
            event_type="command.execute",
            command_type=command_type,
            payload={**payload, "event_id": event_id},
            result=result_msg,
            integrity_result="PASS" if result.integrity_passed else "FAIL",
            chaos_injected=use_chaos and self._chaos.count_injections() > 0,
        )

        duration_ms = (time.monotonic() - start) * 1000
        result.duration_ms = duration_ms
        self._observability.record_execution_result(result)
        if not result.success and result.rolled_back:
            self._observability.record_rollback()
        if not result.integrity_passed:
            self._observability.record_integrity_violation()

        return result

    def _execute_command_direct(
        self,
        command_type: str,
        payload: Dict[str, Any],
        model_class=None,
        operation_type=None,
        data=None,
        verify_after=True,
    ) -> ExecutionResult:
        if self._int_engine.is_enabled() and model_class:
            bridge_result = self._bridge.execute_with_integrity(
                operation_fn=lambda: self._processor.execute(
                    command_type, payload
                ),
                model_class=model_class,
                operation_type=operation_type or OperationType.UPDATE,
                data=data,
                verify_after=verify_after,
            )
            if not bridge_result.get("success", False):
                return ExecutionResult.fail(
                    command_type=command_type,
                    error=bridge_result.get("error", "Integrity bridge blocked"),
                    rolled_back=bridge_result.get("verification") is not None,
                )
            inner = bridge_result.get("result")
            if isinstance(inner, ExecutionResult):
                inner.integrity_passed = True
                return inner
            return ExecutionResult.ok(
                command_type=command_type, result=inner
            )

        return self._processor.execute(command_type, payload)

    def run_batch(
        self,
        commands: List[Dict[str, Any]],
        parallel: bool = False,
        chaos_mode: Optional[bool] = None,
    ) -> List[ExecutionResult]:
        use_chaos = (
            chaos_mode if chaos_mode is not None else self._chaos_mode
        )

        def executor_fn(cmd):
            return self.run_command(
                command_type=cmd["command_type"],
                payload=cmd.get("payload", {}),
                model_class=cmd.get("model_class"),
                operation_type=cmd.get("operation_type"),
                data=cmd.get("data"),
                verify_after=cmd.get("verify_after", True),
                chaos_mode=use_chaos,
            )

        if parallel:
            return self._concurrency.execute_parallel(commands, executor_fn)
        else:
            return self._concurrency.execute_sequential(commands, executor_fn)

    def get_status_report(self) -> Dict[str, Any]:
        obs = self._observability.get_report()
        return {
            "observability": obs,
            "replay": {
                "entries": self._replay.count(),
                "last_sequence_id": self._replay.get_last_sequence_id(),
                "checksum": self._replay.checksum()[:16],
            },
            "event_bus": {
                "queue_length": self._event_bus.get_queue_length(),
                "queue_stats": self._event_bus.get_queue_stats(),
            },
            "chaos": {
                "enabled": self._chaos.is_enabled(),
                "injections": self._chaos.count_injections(),
            },
            "integrity_engine_enabled": self._int_engine.is_enabled(),
            "uptime_seconds": round(
                time.monotonic() - self._initialized_at, 2
            ),
        }
