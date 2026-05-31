"""
Section 9 — CI/CD Hooks & Release Pipeline Integration.
Pre-commit, pre-push, and release validation hooks.
"""
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class HookResult:
    hook_name: str
    passed: bool
    detail: str
    severity: str = "high"


def pre_commit_hook() -> HookResult:
    """Pre-commit: validate no blocking issues."""
    try:
        import_success = _check_imports()
        if not import_success:
            return HookResult("pre_commit", False, "Import check failed", "high")
        return HookResult("pre_commit", True, "All pre-commit checks passed")
    except Exception as e:
        return HookResult("pre_commit", False, str(e), "high")


def pre_push_hook() -> HookResult:
    """Pre-push: validate migration safety + integrity."""
    try:
        from governance.migration_guard import check_migration_safety
        safety = check_migration_safety()
        if not safety.all_safe:
            return HookResult("pre_push", False,
                              f"Migration blocked: {'; '.join(safety.blocked)}", "critical")
        return HookResult("pre_push", True, "Pre-push checks passed")
    except Exception as e:
        return HookResult("pre_push", False, str(e), "critical")


def release_hook() -> HookResult:
    """Release validation: full gate certification."""
    try:
        from governance.release_gates import run_release_gates
        results = run_release_gates()
        failures = [r for r in results if not r.passed]
        if failures:
            detail = "; ".join(f"{f.name}: {f.detail}" for f in failures)
            return HookResult("release", False, f"Gate failures: {detail}", "critical")
        return HookResult("release", True, f"All {len(results)} gates passed")
    except Exception as e:
        return HookResult("release", False, str(e), "critical")


def _check_imports() -> bool:
    """Verify critical modules are importable."""
    critical = [
        "core.integrity.engine",
        "core.audit.engine",
        "core.runner.snapshot_manager",
        "accounting.models",
        "inventory.models",
    ]
    for mod_name in critical:
        import importlib
        try:
            importlib.import_module(mod_name)
        except ImportError:
            return False
    return True
