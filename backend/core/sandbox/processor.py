import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from core.sandbox.models import CommandStatus, ERPCommand, ExecutionResult

logger = logging.getLogger(__name__)


class CommandProcessor:
    _instance = None
    _initialized = False

    def __init__(self):
        if not CommandProcessor._initialized:
            self._handlers: Dict[str, Callable] = {}
            self._execution_history: List[ExecutionResult] = []
            CommandProcessor._initialized = True

    @classmethod
    def get_instance(cls) -> "CommandProcessor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_command(self, command_type: str, handler: Callable):
        self._handlers[command_type] = handler

    def execute(
        self,
        command_type: str,
        payload: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        start = time.monotonic()
        command_id = str(uuid.uuid4())

        if command_type not in self._handlers:
            result = ExecutionResult.fail(
                command_id=command_id,
                command_type=command_type,
                error=f"Unknown command type: {command_type}",
            )
            self._execution_history.append(result)
            return result

        cmd = ERPCommand(
            command_id=command_id,
            command_type=command_type,
            payload=payload,
            context=context or {},
        )
        cmd.status = CommandStatus.RUNNING

        try:
            handler = self._handlers[command_type]
            handler_result = handler(cmd)
            elapsed = (time.monotonic() - start) * 1000
            cmd.status = CommandStatus.SUCCESS
            result = ExecutionResult.ok(
                command_id=command_id,
                command_type=command_type,
                result=handler_result,
                duration=elapsed,
            )
            self._execution_history.append(result)
            return result
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            cmd.status = CommandStatus.FAILED
            result = ExecutionResult.fail(
                command_id=command_id,
                command_type=command_type,
                error=str(e),
            )
            result.duration_ms = elapsed
            self._execution_history.append(result)
            return result

    def get_history(self, limit: int = 100) -> List[ExecutionResult]:
        return self._execution_history[-limit:]

    def clear_history(self):
        self._execution_history.clear()


class ConcurrencyManager:
    _instance = None
    _initialized = False

    def __init__(self):
        if not ConcurrencyManager._initialized:
            self._max_workers: int = 4
            self._executions: List[Dict[str, Any]] = []
            ConcurrencyManager._initialized = True

    @classmethod
    def get_instance(cls) -> "ConcurrencyManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_max_workers(self, n: int):
        self._max_workers = max(1, min(n, 16))

    def execute_parallel(
        self,
        commands: List[Dict[str, Any]],
        executor_fn: Callable,
    ) -> List[ExecutionResult]:
        results = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(executor_fn, cmd): cmd
                for cmd in commands
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, ExecutionResult):
                        results.append(result)
                    else:
                        results.append(
                            ExecutionResult.ok(result=result)
                        )
                except Exception as e:
                    results.append(
                        ExecutionResult.fail(error=str(e))
                    )
        self._executions.append({
            "batch_size": len(commands),
            "results": results,
            "success_count": sum(1 for r in results if r.success),
            "fail_count": sum(1 for r in results if not r.success),
        })
        return results

    def execute_sequential(
        self,
        commands: List[Dict[str, Any]],
        executor_fn: Callable,
    ) -> List[ExecutionResult]:
        results = []
        for cmd in commands:
            try:
                result = executor_fn(cmd)
                if isinstance(result, ExecutionResult):
                    results.append(result)
                else:
                    results.append(ExecutionResult.ok(result=result))
            except Exception as e:
                results.append(ExecutionResult.fail(error=str(e)))
        return results

    def get_execution_summary(self) -> Dict[str, Any]:
        total = sum(e["batch_size"] for e in self._executions)
        successes = sum(e["success_count"] for e in self._executions)
        failures = sum(e["fail_count"] for e in self._executions)
        return {
            "total_commands": total,
            "successes": successes,
            "failures": failures,
            "batches": len(self._executions),
        }

    def clear_execution_history(self):
        self._executions.clear()
