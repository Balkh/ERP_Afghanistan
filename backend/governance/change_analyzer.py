"""
Section 1 — Change Analyzer.
Scans modified files and classifies change types.
"""
import os
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChangeResult:
    modified_modules: Set[str]
    has_migrations: bool
    has_model_changes: bool
    has_api_changes: bool
    has_task_changes: bool
    change_count: int
    file_list: List[str]
    timestamp: str

    def to_dict(self) -> Dict:
        return {
            "modified_modules": list(self.modified_modules),
            "has_migrations": self.has_migrations,
            "has_model_changes": self.has_model_changes,
            "has_api_changes": self.has_api_changes,
            "has_task_changes": self.has_task_changes,
            "change_count": self.change_count,
            "file_list": self.file_list[:50],
            "timestamp": self.timestamp,
        }


def classify_file(path: str) -> str:
    """Classify a file path into a module name."""
    parts = path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] in ("accounting", "inventory", "sales", "purchases",
                                          "payments", "core", "config", "hr", "payroll",
                                          "governance"):
        return parts[0]
    if "migrations" in parts:
        return "migrations"
    if "api" in parts or "views" in parts or "serializers" in parts or "urls" in parts:
        return "api"
    if "tasks" in parts or "celery" in parts:
        return "tasks"
    if "test" in parts:
        return "tests"
    return "other"


def analyze_changes(modified_files: List[str]) -> ChangeResult:
    if not modified_files:
        return ChangeResult(set(), False, False, False, False, 0, [], datetime.utcnow().isoformat())

    modules: Set[str] = set()
    has_migrations = False
    has_model_changes = False
    has_api_changes = False
    has_task_changes = False

    for f in modified_files:
        module = classify_file(f)
        modules.add(module)
        if "models.py" in f:
            has_model_changes = True
        if "migrations" in f.replace("\\", "/").split("/"):
            has_migrations = True
        if any(x in f for x in ("views", "serializers", "urls", "api")):
            has_api_changes = True
        if "tasks" in f.replace("\\", "/").split("/"):
            has_task_changes = True

    return ChangeResult(
        modified_modules=modules,
        has_migrations=has_migrations,
        has_model_changes=has_model_changes,
        has_api_changes=has_api_changes,
        has_task_changes=has_task_changes,
        change_count=len(modified_files),
        file_list=sorted(modified_files)[:100],
        timestamp=datetime.utcnow().isoformat(),
    )


def scan_recent_git_changes(base_ref: str = "HEAD~1") -> ChangeResult:
    """Scan git diff between current and base ref."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            capture_output=True, text=True, timeout=30
        )
        files = [f for f in result.stdout.strip().split("\n") if f.strip()]
        return analyze_changes(files)
    except Exception:
        return ChangeResult(set(), False, False, False, False, 0, [],
                            datetime.utcnow().isoformat())
