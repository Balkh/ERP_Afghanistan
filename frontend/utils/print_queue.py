"""
Print Queue Manager — reliable print job queuing with retry and offline support.
"""

import json
import os
import time
from typing import Dict, Any, Optional
from collections import deque
from enum import Enum

from utils.print_engine import PrintEngine


class PrintJobStatus(Enum):
    PENDING = "pending"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class PrintJob:
    def __init__(self, job_id: str, doc_type: str, data: Dict[str, Any],
                 target: str = "printer", max_retries: int = 3):
        self.job_id = job_id
        self.doc_type = doc_type
        self.data = data
        self.target = target
        self.max_retries = max_retries
        self.retry_count = 0
        self.status = PrintJobStatus.PENDING
        self.error: Optional[str] = None
        self.created_at = time.time()


class PrintQueue:
    """Manages print jobs with queue, retry, and offline persistence."""

    def __init__(self, print_engine: Optional[PrintEngine] = None,
                 queue_dir: Optional[str] = None):
        self._engine = print_engine or PrintEngine()
        self._queue: deque[PrintJob] = deque()
        self._history: list[PrintJob] = []
        self._is_processing = False
        self._queue_dir = queue_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "runtime", "print_queue"
        )
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self._queue_dir, exist_ok=True)

    def enqueue(self, job: PrintJob):
        self._queue.append(job)
        self._save_to_disk(job)
        if not self._is_processing:
            self._process_next()

    def enqueue_invoice(self, invoice_data: Dict[str, Any]) -> str:
        import uuid
        job_id = str(uuid.uuid4())
        job = PrintJob(job_id, "invoice", invoice_data)
        self.enqueue(job)
        return job_id

    def enqueue_receipt(self, receipt_data: Dict[str, Any]) -> str:
        import uuid
        job_id = str(uuid.uuid4())
        job = PrintJob(job_id, "receipt", receipt_data)
        self.enqueue(job)
        return job_id

    def _process_next(self):
        if not self._queue:
            self._is_processing = False
            return

        self._is_processing = True
        job = self._queue.popleft()

        try:
            job.status = PrintJobStatus.PRINTING
            if job.doc_type == "invoice":
                self._engine.print_invoice(job.data)
            elif job.doc_type == "receipt":
                self._engine.print_receipt(job.data)
            job.status = PrintJobStatus.COMPLETED
        except Exception as e:
            job.error = str(e)
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = PrintJobStatus.RETRYING
                self._queue.appendleft(job)
            else:
                job.status = PrintJobStatus.FAILED

        self._history.append(job)
        self._save_to_disk(job)

        self._process_next()

    def retry_failed(self):
        failed = [j for j in self._history if j.status == PrintJobStatus.FAILED]
        for job in failed:
            job.retry_count = 0
            job.status = PrintJobStatus.PENDING
            self._queue.append(job)
        if not self._is_processing:
            self._process_next()

    def get_status(self, job_id: str) -> Optional[PrintJobStatus]:
        for job in list(self._queue) + self._history:
            if job.job_id == job_id:
                return job.status
        return None

    def get_queue_length(self) -> int:
        return len(self._queue)

    def get_history(self) -> list[PrintJob]:
        return self._history

    def _save_to_disk(self, job: PrintJob):
        try:
            path = os.path.join(self._queue_dir, f"{job.job_id}.json")
            with open(path, "w") as f:
                json.dump({
                    "job_id": job.job_id,
                    "doc_type": job.doc_type,
                    "data": job.data,
                    "status": job.status.value,
                    "retry_count": job.retry_count,
                    "error": job.error,
                    "created_at": job.created_at,
                }, f)
        except Exception:
            pass

    def recover_from_disk(self):
        if not os.path.isdir(self._queue_dir):
            return
        for fname in sorted(os.listdir(self._queue_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                fpath = os.path.join(self._queue_dir, fname)
                with open(fpath) as f:
                    data = json.load(f)
                job = PrintJob(
                    job_id=data["job_id"],
                    doc_type=data["doc_type"],
                    data=data.get("data", {}),
                )
                job.retry_count = data.get("retry_count", 0)
                job.error = data.get("error")
                status = data.get("status", "pending")
                if status in ("pending", "retrying"):
                    job.status = PrintJobStatus.PENDING
                    self._queue.append(job)
                elif status == "printing":
                    job.status = PrintJobStatus.PENDING
                    self._queue.appendleft(job)
            except Exception:
                pass
