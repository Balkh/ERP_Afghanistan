"""SECTION: Backup + Restore — extracted from gate_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
import importlib
import logging
import os
import sys
import json
import time
import threading
import hashlib
import uuid
from decimal import Decimal
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from production_gate.gate_validator import (
    GateIssue, SectionResult, ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW, logger,
)


def run(self) -> SectionResult:
    issues = []
    try:
        from core.runner.snapshot_manager import SnapshotManager
        from backup.services.restore_service import RestoreService

        mgr = SnapshotManager()

        snap1 = mgr.take_snapshot(500, "Gate pre-restore")
        cs1_before = snap1.checksum

        snap2 = mgr.take_snapshot(501, "Gate post-restore")
        verified_500 = mgr.verify_snapshot(500)
        verified_501 = mgr.verify_snapshot(501)

        if not verified_500:
            issues.append(GateIssue(
                section="backup_restore", severity=ISSUE_HIGH,
                check="snapshot_500_verify",
                detail="Snapshot day 500 verification failed",
            ))
        if not verified_501:
            issues.append(GateIssue(
                section="backup_restore", severity=ISSUE_HIGH,
                check="snapshot_501_verify",
                detail="Snapshot day 501 verification failed",
            ))

        list_result = mgr.list_snapshots()
        if 500 not in list_result or 501 not in list_result:
            issues.append(GateIssue(
                section="backup_restore", severity=ISSUE_MEDIUM,
                check="snapshot_listing",
                detail="Snapshots not found in listing",
                evidence={"listed": list_result, "expected": [500, 501]},
            ))

        issues.append(GateIssue(
            section="backup_restore", severity=ISSUE_LOW,
            check="snapshot_cycle", detail="Backup cycle complete", passed=True,
        ))

    except Exception as e:
        issues.append(GateIssue(
            section="backup_restore", severity=ISSUE_CRITICAL,
            check="backup_execution", detail=f"Backup/restore validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    self.results["backup_restore_validation"] = SectionResult(
        name="Backup + Restore Validation",
        passed=passed,
        issues=issues,
        detail=f"Snapshot create/verify/listing tested",
    )
    self.issues.extend(issues)
    return self.results["backup_restore_validation"]
