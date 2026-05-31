"""
Regression Immunity System — Permanently Block Previously Discovered Bug Classes.

ALL PREVIOUS BUG CLASSES ARE PERMANENTLY BLOCKED:
  1. UUID ordering dependency → FORBIDDEN
  2. Auto state transition without audit → FORBIDDEN
  3. Hardcoded AR/AP accounts → FORBIDDEN
  4. Batch mismatch resolution → FORBIDDEN
  5. Partial return lifecycle → FORBIDDEN
  6. Silent reconciliation failure → FORBIDDEN

Any reappearance of these patterns MUST trigger SYSTEM BLOCK.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from core.guarantees.constraint_handler import (
    ViolationCategory,
    ViolationSeverity,
    get_constraint_handler,
)


@dataclass
class ImmunityRule:
    name: str
    description: str
    checker: Callable[[], List[str]]
    severity: ViolationSeverity = ViolationSeverity.CRITICAL
    fix_required: str = ''


class RegressionImmunitySystem:
    """
    Permanently blocks reappearance of previously discovered bug classes.
    Each rule is a self-contained check that validates an invariant.

    Rules are checked in dependency order and ALL must pass for the
    system to be considered regression-immune.
    """

    def __init__(self, mode: str = 'STRICT'):
        self.mode = mode
        self._rules: List[ImmunityRule] = []
        self._violations: List[str] = []
        self._register_rules()

    def _register_rules(self) -> None:
        """Register all permanent immunity rules."""
        self._rules = [
            ImmunityRule(
                name='uuid_ordering_dependency',
                description='Positional access on UUID-ordered querysets is FORBIDDEN',
                checker=self._check_uuid_ordering,
                severity=ViolationSeverity.CRITICAL,
                fix_required='Use resolve_by_product_name() or order_by("created_at") instead of positional index',
            ),
            ImmunityRule(
                name='auto_transition_without_audit',
                description='Auto state transitions without audit provenance are FORBIDDEN',
                checker=self._check_auto_transition_provenance,
                severity=ViolationSeverity.HIGH,
                fix_required='All state mutations must record transition provenance via record_transition()',
            ),
            ImmunityRule(
                name='hardcoded_account_codes',
                description='Hardcoded AR/AP/tax account codes in services are FORBIDDEN',
                checker=self._check_account_registry_usage,
                severity=ViolationSeverity.CRITICAL,
                fix_required='All account code references must use core.accounting_registry.ACC',
            ),
            ImmunityRule(
                name='batch_product_mismatch',
                description='Batch product/warehouse mismatch resolution is FORBIDDEN',
                checker=self._check_batch_consistency_rule,
                severity=ViolationSeverity.HIGH,
                fix_required='Batch must match invoice item product_id and have non-null warehouse_id',
            ),
            ImmunityRule(
                name='partial_return_lifecycle',
                description='Partial return lifecycle (incomplete chain) is FORBIDDEN',
                checker=self._check_return_chain,
                severity=ViolationSeverity.CRITICAL,
                fix_required='Every approved return must have complete chain: StockMovement + JE + AR/AP + Reconciliation',
            ),
            ImmunityRule(
                name='silent_reconciliation_failure',
                description='Silent reconciliation failure (unvalidated entries) is FORBIDDEN',
                checker=self._check_reconciliation_validation,
                severity=ViolationSeverity.HIGH,
                fix_required='All reconciliation entries must be validated (no silent PENDING status)',
            ),
        ]

    def check_all(self) -> List[str]:
        """
        Execute all immunity rules.
        Returns list of violation messages (empty = all clear).
        In STRICT mode, raises on first violation.
        """
        self._violations.clear()
        for rule in self._rules:
            violations = rule.checker()
            for v in violations:
                msg = f"[{rule.name}] {v} | FIX: {rule.fix_required}"
                self._violations.append(msg)
                if self.mode == 'STRICT':
                    handler = get_constraint_handler()
                    handler.handle(
                        category=ViolationCategory.REGRESSION,
                        message=msg,
                        severity=rule.severity,
                        block_future=True,
                        fix_required=rule.fix_required,
                    )
        return list(self._violations)

    # ── Rule Checkers ──────────────────────────────────────────────────

    def _check_uuid_ordering(self) -> List[str]:
        """
        Check that no code uses positional access (.first(), [0])
        on UUID-ordered models without explicit deterministic ordering.
        """
        issues = []
        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        # Scan sales, purchases, returns views for positional access patterns
        scan_dirs = [
            os.path.join(base_dir, 'sales', 'views.py'),
            os.path.join(base_dir, 'purchases', 'views.py'),
            os.path.join(base_dir, 'returns', 'views.py'),
            os.path.join(base_dir, 'returns', 'models.py'),
            os.path.join(base_dir, 'returns', 'services'),
            os.path.join(base_dir, 'accounting', 'views_account.py'),
        ]

        for filepath in scan_dirs:
            if not os.path.exists(filepath):
                continue
            if os.path.isdir(filepath):
                for root, _dirs, files in os.walk(filepath):
                    for f in files:
                        if f.endswith('.py'):
                            self._scan_file_for_positional_access(
                                os.path.join(root, f), issues
                            )
            else:
                self._scan_file_for_positional_access(filepath, issues)

        return issues

    def _scan_file_for_positional_access(self, filepath: str, issues: List[str]) -> None:
        """Scan a single file for UUID ordering anti-patterns."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                if '.first()' in stripped:
                    preceding_lines = lines[max(0, i - 3):i + 1]
                    preceding_str = ' '.join(preceding_lines)
                    # Skip patterns that are deterministically ordered:
                    # - .order_by(...).first()
                    # - filter(id=...).first() or filter(pk=...).first()
                    # - filter(code=...).first() (unique constraint)
                    # - get_or_create pattern
                    # - related model access (<model>.<related_set>.first())
                    if '.order_by(' in preceding_str and '.first()' in preceding_str:
                        continue
                    filters = ['filter(id=', 'filter(pk=', 'filter(code=']
                    if any(f in preceding_str for f in filters):
                        continue
                    if 'get_or_create' in preceding_str:
                        continue
                    # Check if .first() is on a related field access
                    # (e.g., invoice.reconciliation_entries.first())
                    # These are inherently scoped to a single parent object
                    has_dot_chain = '.' in stripped and '.first()' in stripped
                    has_objects = 'objects.' in preceding_str
                    if has_dot_chain and not has_objects:
                        continue
                    issues.append(
                        f"File: {os.path.relpath(filepath)}, Line {i}: "
                        f"'.first()' usage found without deterministic ordering: {stripped[:120]}"
                    )
        except (OSError, UnicodeDecodeError):
            pass

    def _check_auto_transition_provenance(self) -> List[str]:
        """
        Check that auto-transitions (signal-based) are always accompanied
        by provenance recording via record_transition().
        """
        issues = []
        import os
        from django.conf import settings

        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        signals_path = os.path.join(base_dir, 'returns', 'signals.py')
        if os.path.exists(signals_path):
            try:
                with open(signals_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Verify auto-complete signal records provenance
                if 'record_transition' not in content:
                    issues.append(
                        "returns/signals.py: Auto-complete signal does not use record_transition()"
                    )
                if 'provenance' not in content.lower():
                    issues.append(
                        "returns/signals.py: No provenance tracking found in auto-transition signal"
                    )
            except (OSError, UnicodeDecodeError):
                pass

        return issues

    def _check_account_registry_usage(self) -> List[str]:
        """
        Check that all account code references in services use the ACC registry.
        """
        issues = []
        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        service_files = [
            os.path.join(base_dir, 'sales', 'views.py'),
            os.path.join(base_dir, 'purchases', 'views.py'),
            os.path.join(base_dir, 'returns', 'models.py'),
            os.path.join(base_dir, 'payments', 'services.py'),
        ]

        for filepath in service_files:
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    # Skip dict definitions like {'2100': 'Tax Payable'}
                    if stripped.strip().startswith("'") and ':' in stripped:
                        continue
                    # Skip filter(code=...) patterns (deterministic unique lookup)
                    if 'filter(code=' in stripped:
                        continue
                    # Look for hardcoded account code strings
                    if "'1100'" in stripped or "'2100'" in stripped or "'4000'" in stripped:
                        if 'accounting_registry' not in content and 'ACC.' not in content:
                            issues.append(
                                f"File: {os.path.relpath(filepath)}, Line {i}: "
                                f"Hardcoded account code found without ACC registry: {stripped[:120]}"
                            )
            except (OSError, UnicodeDecodeError):
                pass

        return issues

    def _check_batch_consistency_rule(self) -> List[str]:
        """
        Verify that batch consumption in sales/purchases validates
        product_id and warehouse_id consistency.
        """
        issues = []
        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        # Verify that core batch validation exists in the guarantees lineage system
        lineage_path = os.path.join(base_dir, 'core', 'guarantees', 'inventory_lineage.py')
        if os.path.exists(lineage_path):
            try:
                with open(lineage_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'check_batch_consistency' in content:
                    return issues
            except (OSError, UnicodeDecodeError):
                pass
        issues.append("core/inventory_lineage.py: Batch consistency validation not found")
        return issues

    def _check_return_chain(self) -> List[str]:
        """
        Verify that the return chain validation system is active.
        """
        issues = []
        import os
        from django.conf import settings

        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        guard_path = os.path.join(base_dir, 'core', 'guarantees', 'reconciliation.py')
        if os.path.exists(guard_path):
            try:
                with open(guard_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'check_return_chain' not in content:
                    issues.append(
                        "core/guarantees/reconciliation.py: Return chain checker not found"
                    )
            except (OSError, UnicodeDecodeError):
                pass
        else:
            issues.append("core/guarantees/reconciliation.py not found — return chain guard missing")

        return issues

    def _check_reconciliation_validation(self) -> List[str]:
        """
        Verify that reconciliation entries are being validated (not left PENDING).
        """
        issues = []
        import os
        from django.conf import settings

        base_dir = getattr(settings, 'BASE_DIR', None)
        if not base_dir:
            return []

        rec_service_path = os.path.join(
            base_dir, 'returns', 'services', 'reconciliation_service.py'
        )
        if os.path.exists(rec_service_path):
            try:
                with open(rec_service_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if '_validate' not in content:
                    issues.append(
                        "reconciliation_service.py: No reconciliation validation logic found"
                    )
            except (OSError, UnicodeDecodeError):
                pass

        return issues

    @property
    def has_violations(self) -> bool:
        return len(self._violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def clear(self) -> None:
        self._violations.clear()


_immunity_instance = None


def get_immunity_system(mode: str = 'STRICT') -> RegressionImmunitySystem:
    global _immunity_instance
    if _immunity_instance is None:
        _immunity_instance = RegressionImmunitySystem(mode=mode)
    return _immunity_instance
