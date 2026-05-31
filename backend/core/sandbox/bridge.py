import hashlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type

from django.db import models

from core.integrity.engine import IntegrityEngine
from core.integrity.models import OperationType
from core.sandbox.models import ExecutionResult, ReplayEntry

logger = logging.getLogger(__name__)


class IntegrityBridge:
    _instance = None
    _initialized = False

    def __init__(self):
        if not IntegrityBridge._initialized:
            self._engine: Optional[IntegrityEngine] = None
            IntegrityBridge._initialized = True

    @classmethod
    def get_instance(cls) -> "IntegrityBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self, engine: IntegrityEngine):
        self._engine = engine

    def execute_with_integrity(
        self,
        operation_fn: Callable,
        model_class: Optional[Type[models.Model]] = None,
        operation_type: Optional[OperationType] = None,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        verify_after: bool = True,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._engine:
            try:
                eng = IntegrityEngine.get_instance()
                eng.configure()
                self._engine = eng
            except Exception as e:
                return {
                    "success": False,
                    "error": f"IntegrityEngine unavailable: {e}",
                    "integrity_passed": False,
                }

        return self._engine.enforce_operation(
            operation_fn=operation_fn,
            model_class=model_class,
            operation_type=operation_type,
            data=data,
            context=context,
            verify_after=verify_after,
        )

    def is_connected(self) -> bool:
        return self._engine is not None


class ReplayBuffer:
    _instance = None
    _initialized = False

    def __init__(self):
        if not ReplayBuffer._initialized:
            self._entries: List[ReplayEntry] = []
            self._max_entries: int = 10000
            self._next_id: int = 1
            ReplayBuffer._initialized = True

    @classmethod
    def get_instance(cls) -> "ReplayBuffer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(
        self,
        event_type: str = "",
        command_type: str = "",
        payload: Optional[Dict[str, Any]] = None,
        result: str = "",
        integrity_result: str = "",
        chaos_injected: bool = False,
    ) -> int:
        entry = ReplayEntry(
            sequence_id=self._next_id,
            event_type=event_type,
            command_type=command_type,
            payload=payload or {},
            result=result,
            integrity_result=integrity_result,
            chaos_injected=chaos_injected,
        )
        self._entries.append(entry)
        seq = self._next_id
        self._next_id += 1
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)
        return seq

    def get_sequence(
        self, from_id: int = 0, to_id: Optional[int] = None
    ) -> List[ReplayEntry]:
        if to_id is None:
            to_id = self._next_id - 1
        return [
            e for e in self._entries
            if from_id <= e.sequence_id <= to_id
        ]

    def replay(self, from_id: int = 0) -> List[ReplayEntry]:
        return self.get_sequence(from_id=from_id)

    def get_all(self) -> List[ReplayEntry]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def checksum(self) -> str:
        hasher = hashlib.sha256()
        for entry in self._entries:
            hasher.update(str(entry.sequence_id).encode())
            hasher.update(entry.event_type.encode())
            hasher.update(str(entry.payload).encode())
        return hasher.hexdigest()

    def clear(self):
        self._entries.clear()
        self._next_id = 1

    def get_last_sequence_id(self) -> int:
        return self._next_id - 1 if self._entries else 0
