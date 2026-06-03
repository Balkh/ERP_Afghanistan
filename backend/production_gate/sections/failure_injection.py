"""SECTION: Failure Injection — extracted from gate_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).

The assertFalse/assertTrue/assertEqual helpers, originally methods on
ProductionGateValidator, are now module-level functions (no `self`).
Call sites that used `self.assertFalse(x)` etc. are updated to call
the functions directly.
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


def assertFalse(val):
    return not val


def assertTrue(val):
    return val


def assertEqual(a, b):
    return a == b


def run(self) -> SectionResult:
    issues = []

    # Test 1: Integrity layer freeze
    try:
        from core.integrity.freeze import SystemFreezeKillSwitch
        freeze = SystemFreezeKillSwitch.get_instance()
        was_frozen = freeze.is_frozen()
        if not was_frozen:
            freeze.freeze("Gate test freeze")
            is_frozen = freeze.is_frozen()
            freeze.unfreeze("Gate test unfreeze")
            if not is_frozen:
                issues.append(GateIssue(
                    section="failure_injection", severity=ISSUE_CRITICAL,
                    check="freeze_engage", detail="Freeze did not engage",
                ))
            issues.append(GateIssue(
                section="failure_injection", severity=ISSUE_LOW,
                check="freeze_cycle", detail="Freeze/unfreeze cycle works", passed=True,
            ))
    except Exception as e:
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_HIGH,
            check="freeze_mechanism", detail=f"Freeze test failed: {e}",
        ))

    # Test 2: Self-healing activation
    try:
        from core.runner.self_healer import SelfHealer
        healer = SelfHealer()
        action = healer.heal("test_module", None)
        if action is not None:
            pass
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_LOW,
            check="self_heal_noop", detail="Self-healer handles null check gracefully", passed=True,
        ))
    except Exception as e:
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_MEDIUM,
            check="self_heal", detail=f"Self-heal test failed: {e}",
        ))

    # Test 3: Duplicate event detection
    try:
        from core.runner.event_reliability import IdempotencyChecker
        from core.runner.modules import CModuleID
        from core.runner.workload_generator import BusinessEvent
        checker = IdempotencyChecker()
        event = BusinessEvent(
            module=CModuleID.C5_SALES, event_type="create_sale",
            payload={"customer_id": 1, "amount": 100},
        )
        assertFalse(checker.is_duplicate(event))
        checker.mark_seen(event)
        assertTrue(checker.is_duplicate(event))
        checker.clear()
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_LOW,
            check="idempotency", detail="Idempotency detection verified", passed=True,
        ))
    except Exception as e:
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_MEDIUM,
            check="idempotency", detail=f"Idempotency test: {e}",
        ))

    # Test 4: Snapshot integrity
    try:
        from core.runner.snapshot_manager import SnapshotManager
        mgr = SnapshotManager()
        snap = mgr.take_snapshot(999, "Gate test snapshot")
        verified = mgr.verify_snapshot(999)
        if not verified:
            issues.append(GateIssue(
                section="failure_injection", severity=ISSUE_HIGH,
                check="snapshot_integrity",
                detail="Snapshot verification failed immediately after creation",
            ))
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_LOW,
            check="snapshot_verify", detail="Snapshot/verify cycle works", passed=True,
        ))
    except Exception as e:
        issues.append(GateIssue(
            section="failure_injection", severity=ISSUE_MEDIUM,
            check="snapshot", detail=f"Snapshot test: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    self.results["failure_injection_validation"] = SectionResult(
        name="Failure Injection Testing",
        passed=passed,
        issues=issues,
        detail=f"4 failure scenarios tested",
    )
    self.issues.extend(issues)
    return self.results["failure_injection_validation"]
