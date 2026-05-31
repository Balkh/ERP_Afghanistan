import hashlib
import logging
from typing import Dict, List, Optional

from django.db import connection

from core.integrity.models import DriftResult

logger = logging.getLogger(__name__)


class RealTimeDriftDetector:
    _instance = None
    _initialized = False

    def __init__(self):
        if not RealTimeDriftDetector._initialized:
            self._baseline: Optional[Dict[str, str]] = None
            RealTimeDriftDetector._initialized = True

    @classmethod
    def get_instance(cls) -> "RealTimeDriftDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def compute_schema_hash(self) -> str:
        hasher = hashlib.sha256()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type IN ('table','index','view','trigger') "
                "ORDER BY name"
            )
            for row in cursor.fetchall():
                hasher.update(f"{row[0]}:{row[1]}\n".encode())
        return hasher.hexdigest()

    def compute_table_registry_hash(self) -> str:
        hasher = hashlib.sha256()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            )
            for row in cursor.fetchall():
                cursor2 = connection.cursor()
                cursor2.execute(f"SELECT COUNT(*) FROM \"{row[0]}\"")
                count = cursor2.fetchone()[0]
                hasher.update(f"{row[0]}:{count}\n".encode())
        return hasher.hexdigest()

    def compute_governance_hash(self) -> str:
        try:
            from core.governance.kernel import get_kernel
            k = get_kernel()
            state = ""
            if hasattr(k, "policies"):
                state += str(k.policies)
            if hasattr(k, "invariants"):
                state += str(k.invariants)
            return hashlib.sha256(state.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(b"governance_unavailable").hexdigest()

    def compute_full_hash(self) -> Dict[str, str]:
        return {
            "schema": self.compute_schema_hash(),
            "table_registry": self.compute_table_registry_hash(),
            "governance": self.compute_governance_hash(),
        }

    def capture_baseline(self) -> Dict[str, str]:
        self._baseline = self.compute_full_hash()
        return self._baseline

    def get_baseline(self) -> Optional[Dict[str, str]]:
        return self._baseline

    def detect_drift(self) -> DriftResult:
        baseline = self._baseline
        if baseline is None:
            self.capture_baseline()
            return DriftResult.stable(
                baseline=hashlib.sha256(b"initial").hexdigest(),
                current=hashlib.sha256(b"initial").hexdigest(),
            )

        current = self.compute_full_hash()

        schema_change = current["schema"] != baseline["schema"]
        governance_change = current["governance"] != baseline["governance"]
        table_change = current["table_registry"] != baseline["table_registry"]

        if schema_change or governance_change or table_change:
            changes = []
            if schema_change:
                changes.append("schema")
            if governance_change:
                changes.append("governance")
            if table_change:
                changes.append("table_registry")
            return DriftResult.drift_detected(
                baseline=str(baseline),
                current=str(current),
                details=f"Drift detected in: {', '.join(changes)}",
            )

        return DriftResult.stable(
            baseline=str(baseline),
            current=str(current),
        )
