"""
Offline Transaction Queue — persists pending transactions to disk,
syncs when backend is available, handles conflict detection and replay.

Architecture:
  OfflineQueue
    ├── enqueue(transaction) → saves to local JSON file
    ├── sync_all() → replays queued transactions against API
    ├── recover() → loads pending transactions on startup
    └── conflict_detection → detects stale/superseded transactions
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from collections import deque


class TransactionStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class TransactionType(Enum):
    SALE = "sale"
    PAYMENT = "payment"
    PURCHASE = "purchase"
    RETURN = "return"
    STOCK_ADJUSTMENT = "stock_adjustment"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class QueuedTransaction:
    """A single pending transaction stored offline."""

    def __init__(self, tx_type: TransactionType, data: Dict[str, Any],
                 endpoint: str = "", method: str = "POST"):
        self.id = str(uuid.uuid4())
        self.tx_type = tx_type
        self.data = data
        self.endpoint = endpoint
        self.method = method
        self.status = TransactionStatus.PENDING
        self.created_at = time.time()
        self.last_sync_attempt = 0.0
        self.retry_count = 0
        self.max_retries = 5
        self.error: Optional[str] = None
        self.server_response: Optional[Dict] = None
        self.version_token: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.tx_type.value,
            "data": self.data,
            "endpoint": self.endpoint,
            "method": self.method,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_sync_attempt": self.last_sync_attempt,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": self.error,
            "version_token": self.version_token,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QueuedTransaction":
        tx = cls(
            tx_type=TransactionType(d.get("type", "sale")),
            data=d.get("data", {}),
            endpoint=d.get("endpoint", ""),
            method=d.get("method", "POST"),
        )
        tx.id = d.get("id", tx.id)
        tx.status = TransactionStatus(d.get("status", "pending"))
        tx.created_at = d.get("created_at", tx.created_at)
        tx.last_sync_attempt = d.get("last_sync_attempt", 0.0)
        tx.retry_count = d.get("retry_count", 0)
        tx.max_retries = d.get("max_retries", 5)
        tx.error = d.get("error")
        version_token = d.get("version_token")
        return tx


class OfflineQueue:
    """
    Persists transactions to disk when backend is unavailable.
    Syncs automatically when connection is restored.
    """

    def __init__(self, queue_dir: Optional[str] = None,
                 api_client=None, sync_callback: Optional[Callable] = None):
        self._api_client = api_client
        self._sync_callback = sync_callback
        self._queue_dir = queue_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "runtime", "offline_queue"
        )
        self._ensure_dir()
        self._pending: deque[QueuedTransaction] = deque()
        self._history: Dict[str, QueuedTransaction] = {}
        self._is_syncing = False
        self.recover()

    def _ensure_dir(self):
        os.makedirs(self._queue_dir, exist_ok=True)

    def enqueue(self, tx: QueuedTransaction) -> str:
        self._pending.append(tx)
        self._save_to_disk(tx)
        return tx.id

    def enqueue_sale(self, invoice_data: Dict[str, Any]) -> str:
        return self.enqueue(QueuedTransaction(
            TransactionType.SALE, invoice_data, "/api/sales/invoices/"
        ))

    def enqueue_payment(self, payment_data: Dict[str, Any]) -> str:
        return self.enqueue(QueuedTransaction(
            TransactionType.PAYMENT, payment_data, "/api/payments/transactions/"
        ))

    def get_pending_count(self) -> int:
        return len(self._pending)

    def get_pending(self) -> List[QueuedTransaction]:
        return list(self._pending)

    def get_history(self) -> List[QueuedTransaction]:
        return list(self._history.values())

    def sync_all(self) -> Dict[str, Any]:
        if self._is_syncing or not self._pending or not self._api_client:
            return {"synced": 0, "failed": 0, "pending": len(self._pending)}

        self._is_syncing = True
        synced = 0
        failed = 0
        results = []

        for _ in range(len(self._pending)):
            tx = self._pending.popleft()
            try:
                tx.status = TransactionStatus.SYNCING
                tx.last_sync_attempt = time.time()

                method = tx.method.lower()
                api_method = getattr(self._api_client, method, None)
                if api_method:
                    response = api_method(tx.endpoint, tx.data)
                else:
                    response = self._api_client.post(tx.endpoint, tx.data)

                if response and isinstance(response, dict):
                    success = response.get("success", True)
                    if success or "id" in response:
                        tx.status = TransactionStatus.COMPLETED
                        tx.server_response = response
                        synced += 1
                        if self._sync_callback:
                            self._sync_callback(tx, response)
                    else:
                        tx.retry_count += 1
                        tx.status = TransactionStatus.FAILED
                        tx.error = response.get("error", "API returned error")
                        failed += 1
                else:
                    raise ConnectionError("No response from server")

            except Exception as e:
                tx.retry_count += 1
                tx.error = str(e)
                if tx.retry_count >= tx.max_retries:
                    tx.status = TransactionStatus.FAILED
                    failed += 1
                else:
                    tx.status = TransactionStatus.PENDING
                    self._pending.append(tx)

            self._history[tx.id] = tx
            self._save_to_disk(tx)
            results.append(tx.to_dict())

        self._is_syncing = False
        return {"synced": synced, "failed": failed,
                "pending": len(self._pending), "results": results}

    def retry_failed(self) -> int:
        retried = 0
        for tx_id, tx in list(self._history.items()):
            if tx.status == TransactionStatus.FAILED and tx.retry_count < tx.max_retries:
                tx.retry_count = 0
                tx.status = TransactionStatus.PENDING
                self._pending.append(tx)
                retried += 1
        return retried

    def cancel(self, tx_id: str) -> bool:
        for tx in list(self._pending):
            if tx.id == tx_id:
                self._pending.remove(tx)
                tx.status = TransactionStatus.CONFLICT
                self._history[tx.id] = tx
                self._save_to_disk(tx)
                return True
        return False

    def detect_conflicts(self) -> List[QueuedTransaction]:
        conflicts = []
        seen_keys = {}
        for tx in self._pending:
            conflict_key = f"{tx.tx_type.value}:{tx.endpoint}"
            if conflict_key in seen_keys:
                if tx.created_at > seen_keys[conflict_key].created_at:
                    tx.status = TransactionStatus.CONFLICT
                    conflicts.append(tx)
            else:
                seen_keys[conflict_key] = tx
        return conflicts

    def recover(self):
        if not os.path.isdir(self._queue_dir):
            return
        for fname in sorted(os.listdir(self._queue_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                fpath = os.path.join(self._queue_dir, fname)
                with open(fpath) as f:
                    raw = json.load(f)
                tx = QueuedTransaction.from_dict(raw)
                if tx.status == TransactionStatus.PENDING:
                    self._pending.append(tx)
                elif tx.status in (TransactionStatus.COMPLETED,
                                   TransactionStatus.FAILED,
                                   TransactionStatus.CONFLICT):
                    self._history[tx.id] = tx
            except Exception:
                pass

    def _save_to_disk(self, tx: QueuedTransaction):
        try:
            fpath = os.path.join(self._queue_dir, f"{tx.id}.json")
            with open(fpath, "w") as f:
                json.dump(tx.to_dict(), f, indent=2)
        except Exception:
            pass

    def clear_completed(self):
        for tx_id, tx in list(self._history.items()):
            if tx.status == TransactionStatus.COMPLETED:
                del self._history[tx_id]
                try:
                    fpath = os.path.join(self._queue_dir, f"{tx_id}.json")
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception:
                    pass
