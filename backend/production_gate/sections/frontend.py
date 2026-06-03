"""SECTION: Frontend Validation — extracted from gate_validator.py
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
    issues: List[GateIssue] = []
    frontend_path = Path(__file__).parent.parent.parent / "frontend" / "ui"

    required_screens = {
        "dashboard": "dashboard.py",
        "accounting": "accounting",
        "sales": "sales",
        "purchases": "purchases",
        "inventory": "inventory",
        "hr": "hr",
        "reports": Path("accounting") / "report_browser.py",
        "backup": Path("system") / "backup_screen.py",
        "settings": Path("system") / "settings_screen.py",
    }

    for name, rel_path in required_screens.items():
        target = frontend_path / rel_path
        exists = target.exists()
        if not exists:
            issues.append(GateIssue(
                section="frontend", severity=ISSUE_HIGH,
                check=f"screen_{name}", detail=f"Screen '{name}' not found at {target}",
            ))

    if not issues:
        for name in required_screens:
            issues.append(GateIssue(
                section="frontend", severity=ISSUE_LOW,
                check=f"screen_{name}", detail=f"Screen '{name}' exists", passed=True,
            ))

    try:
        from frontend.api.client import APIClient
        issues.append(GateIssue(
            section="frontend", severity=ISSUE_LOW,
            check="api_client", detail="APIClient importable", passed=True,
        ))
    except Exception as e:
        issues.append(GateIssue(
            section="frontend", severity=ISSUE_MEDIUM,
            check="api_client", detail=f"APIClient import failed: {e}",
        ))

    real_issues = [i for i in issues if not getattr(i, 'passed', False)]
    passed = len([i for i in real_issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0

    self.results["frontend_validation"] = SectionResult(
        name="Frontend Operational Validation",
        passed=passed,
        issues=real_issues,
        detail=f"{len(required_screens)} screens checked, {len(real_issues)} issues",
    )
    self.issues.extend(real_issues)
    return self.results["frontend_validation"]
