import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from django.db import connection

logger = logging.getLogger("c_runner.snapshot")


@dataclass
class SnapshotRecord:
    day: int
    timestamp: str
    label: str
    checksum: str
    table_row_counts: Dict[str, int] = field(default_factory=dict)
    path: str = ""


class SnapshotManager:

    def __init__(self, storage_path: str = "/tmp/c_runner_snapshots"):
        self._storage_path = storage_path
        self._snapshots: Dict[int, SnapshotRecord] = {}

    def take_snapshot(self, day: int, label: str = "") -> SnapshotRecord:
        import os
        os.makedirs(self._storage_path, exist_ok=True)
        ts = datetime.utcnow().isoformat()
        counts = self._get_table_row_counts()
        checksum = self._compute_checksum(counts)
        record = SnapshotRecord(
            day=day,
            timestamp=ts,
            label=label or f"Day_{day}",
            checksum=checksum,
            table_row_counts=counts,
            path=f"{self._storage_path}/snapshot_day_{day}.json",
        )
        self._save_snapshot_file(record)
        self._snapshots[day] = record
        logger.info("[SNAPSHOT] Day %d: %s (%d tables)", day, checksum[:12], len(counts))
        return record

    def get_snapshot(self, day: int) -> Optional[SnapshotRecord]:
        return self._snapshots.get(day)

    def verify_snapshot(self, day: int) -> bool:
        record = self._snapshots.get(day)
        if not record:
            return False
        current_counts = self._get_table_row_counts()
        current_checksum = self._compute_checksum(current_counts)
        return current_checksum == record.checksum

    def list_snapshots(self) -> List[int]:
        return sorted(self._snapshots.keys())

    def _get_table_row_counts(self) -> Dict[str, int]:
        counts = {}
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                    counts[table] = cursor.fetchone()[0]
                except Exception:
                    counts[table] = -1
        return counts

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _save_snapshot_file(self, record: SnapshotRecord):
        try:
            with open(record.path, "w") as f:
                json.dump({
                    "day": record.day,
                    "timestamp": record.timestamp,
                    "label": record.label,
                    "checksum": record.checksum,
                    "table_row_counts": record.table_row_counts,
                }, f, indent=2, default=str)
        except Exception as e:
            logger.warning("[SNAPSHOT] Failed to save file: %s", e)
