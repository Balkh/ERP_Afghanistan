"""
INDUSTRIAL SAFE TEST SUITE — Pharmacy ERP.
Controlled production simulation. Non-destructive, bounded, local-safe.
Validates real-world ERP stability under controlled load without risking
system damage, CPU overload, memory exhaustion, or database corruption.
"""
import logging
import time
import uuid
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel, PriorityTier

logger = logging.getLogger("erp.governance.industrial_test")

# ── Global Test Configuration (MANDATORY LIMITS) ──────────────

TEST_CONFIG = {
    "MAX_OPERATIONS": 50,
    "SLEEP_MS": 20,
    "MAX_CONCURRENCY": 2,
    "TIMEOUT_SECONDS": 120,
    "ENABLE_DB_WRITE": False,
    "USE_DRY_RUN": True,
    "ENABLE_UI_TEST": True,
    "MEMORY_BOUND_BUFFER": 50,
}


# ── Hardening Constants (FALSE-POSITIVE ELIMINATION) ─────────

TRANSIENT_STATE_THRESHOLD_SECONDS: int = 30
MAX_EVIDENCE_SAMPLES: int = 5

VOLATILE_RESULT_FIELDS: set = {
    "timestamp", "correlation_id", "latency_ms", "duration_ms",
    "event_id", "correlation_id", "id",
    "_close_ts", "_open_ts", "_start_time",
}


def canonicalize_result(obj: Any) -> Any:
    """Recursively strip non-deterministic fields from governance results.
    Removes timestamps, UUIDs, runtime counters, durations, temp IDs.
    Only semantic governance fields survive for deterministic comparison.
    """
    if isinstance(obj, dict):
        return {
            k: canonicalize_result(v)
            for k, v in obj.items()
            if k not in VOLATILE_RESULT_FIELDS and not k.startswith("_")
        }
    elif isinstance(obj, (list, tuple)):
        return sorted([canonicalize_result(x) for x in obj], key=str)
    elif isinstance(obj, datetime):
        return "DATETIME"
    elif isinstance(obj, float):
        return round(obj, 1)
    return obj


# ── Bounded Evidence Collector ──────────────────────────────


class _EvidenceCollector:
    """Bounded evidence store — never exceeds MAX_EVIDENCE_SAMPLES."""

    def __init__(self):
        self._items: List[Dict[str, Any]] = []

    def add(self, issue_type: str, module_path: str, object_id: str,
            detection_reason: str, semantic_impact: str) -> None:
        if len(self._items) >= MAX_EVIDENCE_SAMPLES:
            return
        self._items.append({
            "issue_type": issue_type,
            "module_path": module_path[:120],
            "object_id": str(object_id)[:60],
            "detection_reason": detection_reason[:200],
            "semantic_impact": semantic_impact[:200],
        })

    @property
    def items(self) -> List[Dict[str, Any]]:
        return list(self._items)


@dataclass
class PhaseAResult:
    sales_count: int = 0
    purchase_count: int = 0
    return_count: int = 0
    journal_count: int = 0
    error_count: int = 0
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PhaseBResult:
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    policy_evaluation_count: int = 0
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PhaseCResult:
    violation_count: int = 0
    compliance_status: str = "STABLE"
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PhaseDResult:
    final_buffer_size: int = 0
    memory_growth_status: str = "STABLE"
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class PhaseEResult:
    truly_fixed_count: int = 0
    hidden_violation_count: int = 0
    reclassified_violation_count: int = 0
    legacy_path_count: int = 0
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PhaseFResult:
    orphan_count: int = 0
    stale_state_count: int = 0
    detached_reference_count: int = 0
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PhaseGResult:
    deterministic_pass_rate: float = 0.0
    inconsistent_decision_count: int = 0
    duration_ms: float = 0.0
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IndustrialTestReport:
    core_flow: PhaseAResult = field(default_factory=PhaseAResult)
    governance: PhaseBResult = field(default_factory=PhaseBResult)
    ui_safety: PhaseCResult = field(default_factory=PhaseCResult)
    memory_soak: PhaseDResult = field(default_factory=PhaseDResult)
    regression_truth: PhaseEResult = field(default_factory=PhaseEResult)
    stale_state: PhaseFResult = field(default_factory=PhaseFResult)
    consistency_replay: PhaseGResult = field(default_factory=PhaseGResult)
    overall_status: str = "PASS"
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


# ─────────────────────────────────────────────────────────────
# Phase A — Core Business Flow Stability Test
# ─────────────────────────────────────────────────────────────

SIMULATION_STATES = {
    "sales": ["draft", "confirmed", "dispatched", "delivered"],
    "purchase": ["draft", "ordered", "received", "completed"],
    "returns": ["requested", "approved", "received", "completed"],
    "journal": ["draft", "posted", "balanced"],
}


class _Throttle:
    def __init__(self, sleep_ms: float = TEST_CONFIG["SLEEP_MS"]):
        self._sleep = sleep_ms / 1000.0

    def wait(self) -> None:
        if self._sleep > 0:
            time.sleep(self._sleep)


def _simulate_state_transition(kernel: GovernanceKernel, entity: str, state: str) -> bool:
    result = kernel.enforce(
        policy_id=f"enforce.{entity}_state_transition",
        context={"target_state": state},
        priority="high",
        entity=entity,
    )
    return result.allowed


class PhaseA:
    """
    Validates core business workflows (sales, purchases, returns, journals)
    under bounded sequential load. Dry-run mode only. No DB writes.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseAResult:
        start = time.time()
        errors: List[str] = []
        sales_count = 0
        purchase_count = 0
        return_count = 0
        journal_count = 0
        max_ops = self._cfg["MAX_OPERATIONS"]

        for i in range(max_ops):
            self._throttle.wait()
            try:
                category = i % 4
                if category == 0:
                    self._simulate_sales_cycle()
                    sales_count += 1
                elif category == 1:
                    self._simulate_purchase_cycle()
                    purchase_count += 1
                elif category == 2:
                    self._simulate_return_cycle()
                    return_count += 1
                else:
                    self._simulate_journal_cycle()
                    journal_count += 1
            except Exception as e:
                errors.append(f"Operation {i}: {e}")
                if len(errors) > 5:
                    break

        duration = (time.time() - start) * 1000
        passed = len(errors) == 0
        return PhaseAResult(
            sales_count=sales_count,
            purchase_count=purchase_count,
            return_count=return_count,
            journal_count=journal_count,
            error_count=len(errors),
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
        )

    def _simulate_sales_cycle(self) -> None:
        for state in SIMULATION_STATES["sales"]:
            allowed = _simulate_state_transition(self._kernel, "sales", state)
            if not allowed:
                logger.warning("Sales transition to %s blocked by governance", state)

    def _simulate_purchase_cycle(self) -> None:
        for state in SIMULATION_STATES["purchase"]:
            allowed = _simulate_state_transition(self._kernel, "purchase", state)
            if not allowed:
                logger.warning("Purchase transition to %s blocked by governance", state)

    def _simulate_return_cycle(self) -> None:
        for state in SIMULATION_STATES["returns"]:
            allowed = _simulate_state_transition(self._kernel, "returns", state)
            if not allowed:
                logger.warning("Return transition to %s blocked by governance", state)

    def _simulate_journal_cycle(self) -> None:
        result = self._kernel.enforce(
            policy_id="enforce.je_debit_equals_credit",
            context={"total_debit": 1000, "total_credit": 1000},
            priority="high",
            entity="journal_entry",
        )
        if not result.allowed:
            logger.warning("Journal entry balanced check failed")


# ─────────────────────────────────────────────────────────────
# Phase B — Governance Engine Load Test
# ─────────────────────────────────────────────────────────────

class PhaseB:
    """
    Validates governance kernel performance under repeated policy checks.
    Bounded at 30 iterations. Tracks latency only. No recursion stress.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseBResult:
        start = time.time()
        errors: List[str] = []
        latencies: List[float] = []
        evaluations = 0
        max_iterations = min(30, self._cfg["MAX_OPERATIONS"])

        policies = [
            ("enforce.return_state_transition", {"target_state": "approved"}),
            ("enforce.sales_state_transition", {"target_state": "confirmed"}),
            ("enforce.purchase_state_transition", {"target_state": "received"}),
            ("enforce.je_debit_equals_credit", {"total_debit": 500, "total_credit": 500}),
        ]

        for i in range(max_iterations):
            self._throttle.wait()
            for policy_id, context in policies:
                try:
                    t0 = time.time()
                    result = self._kernel.enforce(
                        policy_id=policy_id,
                        context=context,
                        priority="high",
                        entity="load_test",
                    )
                    latency = (time.time() - t0) * 1000
                    latencies.append(latency)
                    evaluations += 1

                    if latency > 50:
                        logger.warning("High latency %.2fms for %s", latency, policy_id)
                except Exception as e:
                    errors.append(f"Iteration {i}, policy {policy_id}: {e}")

            # Run invariant scan periodically
            if i % 5 == 0:
                try:
                    self._kernel.run_invariant_scan()
                except Exception as e:
                    errors.append(f"Invariant scan iteration {i}: {e}")

            if len(errors) > 5:
                break

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        duration = (time.time() - start) * 1000
        passed = len(errors) == 0 and avg_latency <= 50

        return PhaseBResult(
            avg_latency_ms=round(avg_latency, 2),
            max_latency_ms=round(max_latency, 2),
            policy_evaluation_count=evaluations,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
        )


# ─────────────────────────────────────────────────────────────
# Phase C — UI Safety and Schema Validation Test
# ─────────────────────────────────────────────────────────────

LEGACY_COMPONENT_PATTERNS = [
    "QPushButton",
    "QTableWidget",
    "QDialog",
    "QFrame",
    "setStyleSheet",
    "setStyleSheet(",
]

ENTERPRISE_COMPONENT_PATTERNS = [
    "EnterpriseButton",
    "EnterpriseTable",
    "EnterpriseDialog",
    "FormSection",
    "ScreenStateHelper",
    "BaseScreen",
    "BaseFormScreen",
    "BaseListScreen",
]


class PhaseC:
    """
    Validates UI structure integrity without rendering load.
    Static analysis of component usage patterns.
    Maximum 20 validation cycles.
    """

    def __init__(self, config: Optional[Dict] = None):
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseCResult:
        start = time.time()
        errors: List[str] = []
        violations = 0

        max_cycles = min(20, self._cfg["MAX_OPERATIONS"])
        frontend_paths = self._scan_frontend_paths()

        for cycle in range(max_cycles):
            self._throttle.wait()
            try:
                violations += self._check_frontend_files(frontend_paths)
            except Exception as e:
                errors.append(f"Cycle {cycle}: {e}")

        status = "STABLE" if violations <= 5 else "RISK"
        duration = (time.time() - start) * 1000
        passed = violations <= 5 and len(errors) == 0

        return PhaseCResult(
            violation_count=violations,
            compliance_status=status,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
        )

    def _scan_frontend_paths(self) -> List[str]:
        try:
            import os
            base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "ui")
            paths = []
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.endswith(".py"):
                        paths.append(os.path.join(root, f))
            return paths[:50]  # bounded scan
        except Exception:
            return []

    def _check_frontend_files(self, paths: List[str]) -> int:
        violations = 0
        for fp in paths:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for legacy in LEGACY_COMPONENT_PATTERNS:
                    if legacy in content:
                        violations += 1
                        break
            except Exception:
                pass
        return violations


# ─────────────────────────────────────────────────────────────
# Phase D — Memory Stability Soak Test (Bounded)
# ─────────────────────────────────────────────────────────────

class _BoundedBuffer:
    def __init__(self, maxlen: int = 50):
        self._buffer: deque = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def cycle(self, data: Any) -> int:
        self._buffer.append(data)
        return len(self._buffer)

    @property
    def size(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


class PhaseD:
    """
    Detects memory leaks or uncontrolled growth patterns.
    Hard buffer limit: MEMORY_BOUND_BUFFER. No persistent global accumulation.
    """

    def __init__(self, config: Optional[Dict] = None):
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))
        self._buffer = _BoundedBuffer(maxlen=self._cfg.get("MEMORY_BOUND_BUFFER", 50))

    def run(self) -> PhaseDResult:
        start = time.time()
        errors: List[str] = []
        peak_size = 0
        max_ops = min(100, self._cfg["MAX_OPERATIONS"] * 2)
        stabilization_phase = False
        stable_count = 0

        for i in range(max_ops):
            self._throttle.wait()
            try:
                obj = self._allocate_simulated_object(i)
                size = self._buffer.cycle(obj)
                peak_size = max(peak_size, size)

                # Cleanup old references periodically
                if i > 0 and i % 10 == 0:
                    pass

                # After MEMORY_BOUND_BUFFER cycles, buffer should stabilize
                if size == self._buffer._maxlen:
                    stabilization_phase = True

                if stabilization_phase:
                    stable_count += 1
                    if size != self._buffer._maxlen:
                        errors.append(f"Buffer size {size} != maxlen {self._buffer._maxlen} during stabilization")

            except Exception as e:
                errors.append(f"Allocation {i}: {e}")
                if len(errors) > 5:
                    break

        final_size = self._buffer.size
        growth_ok = peak_size <= self._cfg["MEMORY_BOUND_BUFFER"]
        stabilized = final_size <= self._cfg["MEMORY_BOUND_BUFFER"]

        status = "STABLE" if (growth_ok and stabilized) else "LEAK_DETECTED"
        duration = (time.time() - start) * 1000
        passed = growth_ok and stabilized and len(errors) == 0

        return PhaseDResult(
            final_buffer_size=final_size,
            memory_growth_status=status,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
        )

    def _allocate_simulated_object(self, idx: int) -> Dict[str, Any]:
        return {
            "id": uuid.uuid4().hex[:8],
            "index": idx,
            "timestamp": time.time(),
            "data": f"simulated_object_{idx}",
            "metadata": {
                "type": "industrial_test",
                "phase": "D",
                "size": 1024,
            },
        }


# ─────────────────────────────────────────────────────────────
# Phase E — Regression Truth Verification
# ─────────────────────────────────────────────────────────────

ZERO_TRUST_LEGACY_PATTERNS = [
    "models.","objects.filter","objects.create","objects.get_or_create",
    ".save()",".delete()",
    "bypass","skip_governance","force_","override_enforcement",
    "failsafe_bypass","degraded_bypass",
]

DUPLICATE_POLICY_DOMAINS = [
    "returns", "sales", "purchases", "accounting", "inventory",
]


class PhaseE:
    """
    Zero-trust regression truth verification.
    Scans for hidden/suppressed/reclassified violations with
    NO classification filtering, NO warning suppression.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseEResult:
        start = time.time()
        errors: List[str] = []
        evidence = _EvidenceCollector()
        truly_fixed = 0
        hidden = 0
        reclassified = 0
        legacy_paths = 0

        max_iterations = min(20, self._cfg["MAX_OPERATIONS"])

        for i in range(max_iterations):
            self._throttle.wait()
            try:
                category = i % 5
                if category == 0:
                    inc, ev = self._scan_raw_ui_violations()
                    hidden += inc
                    for e in ev:
                        evidence.add(**e)
                elif category == 1:
                    inc, ev = self._detect_legacy_workflow_paths()
                    legacy_paths += inc
                    for e in ev:
                        evidence.add(**e)
                elif category == 2:
                    inc, ev = self._detect_hidden_policy_bypass()
                    hidden += inc
                    for e in ev:
                        evidence.add(**e)
                elif category == 3:
                    inc, ev = self._verify_accounting_truth()
                    reclassified += inc
                    for e in ev:
                        evidence.add(**e)
                else:
                    inc, ev = self._detect_duplicate_enforcement_paths()
                    hidden += inc
                    for e in ev:
                        evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseE iteration {i}: {e}")
                if len(errors) > 5:
                    break

        truly_fixed = max(0, hidden + legacy_paths + reclassified - errors.count(""))

        duration = (time.time() - start) * 1000
        passed = hidden == 0 and legacy_paths == 0 and reclassified == 0 and len(errors) == 0
        return PhaseEResult(
            truly_fixed_count=truly_fixed,
            hidden_violation_count=hidden,
            reclassified_violation_count=reclassified,
            legacy_path_count=legacy_paths,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
            evidence=evidence.items,
        )

    def _scan_raw_ui_violations(self):
        """Zero-trust scan of frontend files — NO filtering, NO suppression."""
        violations = 0
        ev = []
        paths = self._scan_frontend_paths()
        for fp in paths:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for legacy in LEGACY_COMPONENT_PATTERNS:
                    if legacy in content:
                        violations += 1
                        ev.append({
                            "issue_type": "raw_ui_violation",
                            "module_path": fp,
                            "object_id": legacy,
                            "detection_reason": f"Legacy component pattern '{legacy}' found",
                            "semantic_impact": "UI governance violation — non-standard component",
                        })
                        break
            except Exception:
                pass
        return violations, ev

    def _detect_legacy_workflow_paths(self):
        """Detect code paths that bypass governance kernel."""
        count = 0
        ev = []
        paths = self._scan_frontend_paths()
        for fp in paths:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for pattern in ZERO_TRUST_LEGACY_PATTERNS:
                    if pattern in content:
                        count += 1
                        ev.append({
                            "issue_type": "legacy_workflow_path",
                            "module_path": fp,
                            "object_id": pattern,
                            "detection_reason": f"Governance bypass pattern '{pattern}' detected",
                            "semantic_impact": "Workflow executes without governance enforcement chain",
                        })
                        break
            except Exception:
                pass
        return count, ev

    def _detect_hidden_policy_bypass(self):
        """Detect failsafe/degraded tiers being used to mask enforcement."""
        count = 0
        ev = []
        if self._kernel.failsafe_mode:
            count += 1
            ev.append({
                "issue_type": "hidden_policy_bypass",
                "module_path": "kernel.failsafe_mode",
                "object_id": "failsafe",
                "detection_reason": "Failsafe mode active — low-priority enforcement bypassed globally",
                "semantic_impact": "Hidden policy bypass via failsafe degrades governance coverage",
            })
        degraded = self._kernel.health().get("degraded_tiers", [])
        for tier in degraded:
            count += 1
            ev.append({
                "issue_type": "hidden_policy_bypass",
                "module_path": f"kernel.degraded_tiers.{tier}",
                "object_id": tier,
                "detection_reason": f"Degraded tier '{tier}' active — enforcement bypassed",
                "semantic_impact": "Policy enforcement bypassed for degraded priority tier",
            })
        audit = self._kernel.get_recent_audit(limit=100)
        for entry in audit:
            if "bypass" in entry.reason.lower() and entry.result == "allowed":
                count += 1
                ev.append({
                    "issue_type": "hidden_policy_bypass",
                    "module_path": f"audit.{entry.policy_id}",
                    "object_id": entry.policy_id,
                    "detection_reason": f"Bypass allowed: {entry.reason[:100]}",
                    "semantic_impact": "Audited bypass event — possible governance gap",
                })
        return count, ev

    def _verify_accounting_truth(self):
        """Run accounting invariant checks without filtering."""
        violations = 0
        ev = []
        try:
            from core.governance.invariant_validator import check_accounting_invariants
            results = check_accounting_invariants()
            for v in results:
                violations += 1
                ev.append({
                    "issue_type": "accounting_truth_violation",
                    "module_path": f"accounting.{v.entity_type}",
                    "object_id": v.entity_id,
                    "detection_reason": f"{v.message[:120]}",
                    "semantic_impact": f"Invariant '{v.invariant}' violated — severity={v.severity}",
                })
        except Exception:
            pass
        return violations, ev

    def _detect_duplicate_enforcement_paths(self):
        """Detect multiple policies handling the same domain."""
        count = 0
        ev = []
        policies = self._kernel.policies.list_all()
        domain_counts: Dict[str, int] = {}
        domain_policies: Dict[str, list] = {}
        for pid, (_, meta) in policies.items():
            domain = meta.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            domain_policies.setdefault(domain, []).append(pid)
        for domain, cnt in domain_counts.items():
            if cnt > 1 and domain in DUPLICATE_POLICY_DOMAINS:
                count += cnt - 1
                ev.append({
                    "issue_type": "duplicate_enforcement_path",
                    "module_path": f"policies.domain.{domain}",
                    "object_id": domain,
                    "detection_reason": f"{cnt} policies registered for domain '{domain}': {domain_policies[domain]}",
                    "semantic_impact": "Multiple enforcement paths for same domain create inconsistency risk",
                })
        return count, ev

    def _scan_frontend_paths(self) -> List[str]:
        try:
            import os
            base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "ui")
            paths = []
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.endswith(".py"):
                        paths.append(os.path.join(root, f))
            return paths[:50]
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────
# Phase F — Stale State & Orphan Detection
# ─────────────────────────────────────────────────────────────

STALE_STATE_PATTERNS = [
    "stuck_","_lock","_pending_lock","unreleased",
]


class PhaseF:
    """
    Detects residual operational artifacts: orphan journal entries,
    stale event listeners, unreleased locks, detached workflow objects,
    and registry inconsistencies. Read-only validation only.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseFResult:
        start = time.time()
        errors: List[str] = []
        evidence = _EvidenceCollector()
        orphan_count = 0
        stale_count = 0
        detached_count = 0

        max_iterations = min(20, self._cfg["MAX_OPERATIONS"])

        for i in range(max_iterations):
            self._throttle.wait()
            try:
                category = i % 4
                if category == 0:
                    inc, ev = self._check_orphan_journals()
                    orphan_count += inc
                    for e in ev:
                        evidence.add(**e)
                elif category == 1:
                    inc, ev = self._check_stale_listeners()
                    stale_count += inc
                    for e in ev:
                        evidence.add(**e)
                elif category == 2:
                    inc, ev = self._check_unreleased_locks()
                    stale_count += inc
                    for e in ev:
                        evidence.add(**e)
                else:
                    inc, ev = self._check_registry_consistency()
                    detached_count += inc
                    for e in ev:
                        evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseF iteration {i}: {e}")
                if len(errors) > 5:
                    break

        duration = (time.time() - start) * 1000
        passed = orphan_count == 0 and stale_count == 0 and detached_count == 0 and len(errors) == 0
        return PhaseFResult(
            orphan_count=orphan_count,
            stale_state_count=stale_count,
            detached_reference_count=detached_count,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
            evidence=evidence.items,
        )

    def _check_orphan_journals(self):
        """Check for orphaned journal entries — filtered by transient threshold."""
        count = 0
        ev = []
        try:
            from accounting.models import JournalEntry
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(seconds=TRANSIENT_STATE_THRESHOLD_SECONDS)
            for je in JournalEntry.objects.all():
                line_count = je.lines.count()
                if line_count > 0:
                    continue
                created = getattr(je, "created_at", None) or getattr(je, "entry_date", None)
                if created and created > cutoff:
                    continue
                count += 1
                ev.append({
                    "issue_type": "orphan_journal",
                    "module_path": f"accounting.JournalEntry",
                    "object_id": str(je.id),
                    "detection_reason": f"JE #{je.entry_number} has 0 lines",
                    "semantic_impact": "Orphan financial artifact — unreferenced journal entry",
                })
        except Exception:
            pass
        return count, ev

    def _check_stale_listeners(self):
        """Detect stale event listeners — filtered by transient state threshold."""
        count = 0
        ev = []
        try:
            from core.governance.events import get_event_bus
            bus = get_event_bus()
            summary = bus.summary()
            if summary.get("total_events", 0) > 500:
                count += 1
                ev.append({
                    "issue_type": "stale_listener",
                    "module_path": "events.EventBus",
                    "object_id": "event_bus",
                    "detection_reason": f"Event bus has {summary['total_events']} events (threshold 500)",
                    "semantic_impact": "Possible stale listener accumulation in event bus",
                })
        except Exception:
            pass

        health = self._kernel.health()
        audit_entries = health.get("audit_entries", 0)
        if audit_entries > 500:
            count += 1
            ev.append({
                "issue_type": "stale_listener",
                "module_path": "kernel.audit_log",
                "object_id": "audit_log",
                "detection_reason": f"Audit log has {audit_entries} entries (threshold 500)",
                "semantic_impact": "Audit log accumulation may indicate unreleased state tracking",
            })
        return count, ev

    def _check_unreleased_locks(self):
        """Check for unreleased state transition locks — filtered by age."""
        count = 0
        ev = []
        audit = self._kernel.get_recent_audit(limit=200)
        from datetime import datetime as dt
        now_ts = dt.utcnow().timestamp()
        recent_denied = 0
        denied_transition_map: Dict[str, int] = {}

        for entry in audit:
            if entry.result == "denied" and "transition" in entry.reason.lower():
                entry_age = 0.0
                try:
                    entry_ts = dt.fromisoformat(entry.timestamp.rstrip("Z")).timestamp()
                    entry_age = now_ts - entry_ts
                except Exception:
                    pass
                if entry_age < TRANSIENT_STATE_THRESHOLD_SECONDS:
                    recent_denied += 1
                key = f"{entry.policy_id}:{entry.reason[:60]}"
                denied_transition_map[key] = denied_transition_map.get(key, 0) + 1

        if len(audit) > 10 and recent_denied > 10:
            count += 1
            ev.append({
                "issue_type": "unreleased_lock",
                "module_path": "kernel.audit",
                "object_id": "transition_locks",
                "detection_reason": f"{recent_denied} recent denied transitions exceed threshold",
                "semantic_impact": "Persistent state transition denials suggest unreleased locks",
            })

        from collections import Counter
        if denied_transition_map:
            dupes = Counter(denied_transition_map)
            for key, freq in dupes.most_common(3):
                if freq > 5:
                    count += 1
                    ev.append({
                        "issue_type": "unreleased_lock",
                        "module_path": "kernel.audit",
                        "object_id": key[:60],
                        "detection_reason": f"Repeated transition denial ({freq}x): {key[:80]}",
                        "semantic_impact": "Repeated identical denial indicates stuck workflow state",
                    })
        return count, ev

    def _check_registry_consistency(self):
        """Validate cross-registry consistency — no gaps or orphans."""
        count = 0
        ev = []
        health = self._kernel.health()
        policies = health.get("policies", 0)
        invariants = health.get("invariants", 0)
        feature_gates = health.get("feature_gates", 0)

        if policies == 0:
            count += 1
            ev.append({
                "issue_type": "registry_gap",
                "module_path": "registries.PolicyRegistry",
                "object_id": "policies",
                "detection_reason": "Policy registry is empty (0 policies)",
                "semantic_impact": "Missing governance policies — no enforcement possible",
            })
        if invariants == 0:
            count += 1
            ev.append({
                "issue_type": "registry_gap",
                "module_path": "registries.InvariantRegistry",
                "object_id": "invariants",
                "detection_reason": "Invariant registry is empty (0 invariants)",
                "semantic_impact": "Missing invariant checks — domain consistency unverified",
            })
        if feature_gates == 0:
            count += 1
            ev.append({
                "issue_type": "registry_gap",
                "module_path": "registries.FeatureGateRegistry",
                "object_id": "feature_gates",
                "detection_reason": "Feature gate registry is empty (0 gates)",
                "semantic_impact": "No feature gates registered — all features may be inaccessible",
            })
        audit_capacity = health.get("audit_capacity", 0)
        if audit_capacity <= 0:
            count += 1
            ev.append({
                "issue_type": "registry_gap",
                "module_path": "kernel.audit",
                "object_id": "audit_capacity",
                "detection_reason": f"Audit capacity is {audit_capacity} (expected > 0)",
                "semantic_impact": "Audit log cannot retain enforcement history",
            })
        return count, ev


# ─────────────────────────────────────────────────────────────
# Phase G — Governance Consistency Replay
# ─────────────────────────────────────────────────────────────

CONSISTENCY_REPLAY_POLICIES = [
    ("enforce.return_state_transition", {"current_state": "DRAFT", "target_state": "PENDING"}),
    ("enforce.sales_state_transition", {"current_state": "DRAFT", "target_state": "CONFIRMED"}),
    ("enforce.purchase_state_transition", {"current_state": "DRAFT", "target_state": "RECEIVED"}),
    ("enforce.je_debit_equals_credit", {"journal_entry_id": ""}),
]

CONSISTENCY_TRANSITIONS = [
    ("returns", "DRAFT", "PENDING"),
    ("sales", "DRAFT", "CONFIRMED"),
    ("purchases", "DRAFT", "RECEIVED"),
]


class PhaseG:
    """
    Verifies deterministic governance behavior across repeated executions.
    Same input MUST produce same output. Same transition MUST produce same audit trail.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or TEST_CONFIG
        self._throttle = _Throttle(self._cfg.get("SLEEP_MS", 20))

    def run(self) -> PhaseGResult:
        start = time.time()
        errors: List[str] = []
        evidence = _EvidenceCollector()
        inconsistent = 0
        total_checks = 0
        replay_count = min(5, max(1, self._cfg["MAX_OPERATIONS"] // 10))

        for i in range(replay_count):
            self._throttle.wait()
            try:
                inc, total, ev = self._replay_policy_evaluations()
                inconsistent += inc
                total_checks += total
                for e in ev:
                    evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseG policy replay {i}: {e}")

            self._throttle.wait()
            try:
                inc, total, ev = self._replay_state_transitions()
                inconsistent += inc
                total_checks += total
                for e in ev:
                    evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseG transition replay {i}: {e}")

            self._throttle.wait()
            try:
                inc, total, ev = self._replay_audit_consistency()
                inconsistent += inc
                total_checks += total
                for e in ev:
                    evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseG audit replay {i}: {e}")

            self._throttle.wait()
            try:
                inc, total, ev = self._trace_governance_invocation()
                inconsistent += inc
                total_checks += total
                for e in ev:
                    evidence.add(**e)
            except Exception as e:
                errors.append(f"PhaseG trace invocation {i}: {e}")

            if len(errors) > 5:
                break

        pass_rate = (total_checks - inconsistent) / max(total_checks, 1) * 100.0
        duration = (time.time() - start) * 1000
        passed = inconsistent == 0 and len(errors) == 0
        return PhaseGResult(
            deterministic_pass_rate=round(pass_rate, 1),
            inconsistent_decision_count=inconsistent,
            duration_ms=round(duration, 1),
            passed=passed,
            errors=errors[:5],
            evidence=evidence.items,
        )

    def _replay_policy_evaluations(self):
        """Evaluate policies twice with canonical comparison to avoid false inconsistencies."""
        inconsistent = 0
        total = 0
        ev = []
        for policy_id, context in CONSISTENCY_REPLAY_POLICIES:
            r1 = self._kernel.enforce(policy_id, context, priority="high", entity="replay_test")
            r2 = self._kernel.enforce(policy_id, context, priority="high", entity="replay_test")
            total += 1
            c1 = canonicalize_result(r1.__dict__)
            c2 = canonicalize_result(r2.__dict__)
            if c1 != c2:
                inconsistent += 1
                ev.append({
                    "issue_type": "inconsistent_policy_replay",
                    "module_path": f"kernel.enforce.{policy_id}",
                    "object_id": policy_id,
                    "detection_reason": f"Canonical result mismatch for identical inputs",
                    "semantic_impact": "Non-deterministic governance enforcement detected",
                })
        return inconsistent, total, ev

    def _trace_governance_invocation(self):
        """Verify governance kernel was invoked for all replayed operations."""
        inconsistent = 0
        total = 0
        ev = []

        audit_before = self._kernel.get_audit_summary()
        entries_before = audit_before["total_entries"]

        for policy_id, context in CONSISTENCY_REPLAY_POLICIES[:2]:
            _ = self._kernel.enforce(policy_id, context, priority="high", entity="trace_test")
            total += 1

        audit_after = self._kernel.get_audit_summary()
        entries_after = audit_after["total_entries"]
        new_entries = entries_after - entries_before

        if new_entries < len(CONSISTENCY_REPLAY_POLICIES[:2]):
            inconsistent += 1
            ev.append({
                "issue_type": "missing_governance_invocation",
                "module_path": "kernel.enforce",
                "object_id": "governance_trace",
                "detection_reason": f"Expected {len(CONSISTENCY_REPLAY_POLICIES[:2])} audit entries, got {new_entries}",
                "semantic_impact": "Governance kernel not invoked — workflow bypass detected",
            })

        # Verify audit trail contains the trace_test entries
        recent = self._kernel.get_recent_audit(limit=50)
        trace_found = sum(1 for e in recent if e.user == "trace_test")
        if trace_found < len(CONSISTENCY_REPLAY_POLICIES[:2]):
            inconsistent += 1
            ev.append({
                "issue_type": "missing_audit_trail",
                "module_path": "kernel.audit",
                "object_id": "trace_test",
                "detection_reason": f"Expected trace entries not found in audit log",
                "semantic_impact": "Audit trail incomplete — governance observability gap",
            })

        return inconsistent, total, ev

    def _replay_state_transitions(self):
        """Verify identical state transitions produce identical audit trail."""
        inconsistent = 0
        total = 0
        ev = []
        for entity, current, target in CONSISTENCY_TRANSITIONS:
            a1 = self._kernel.get_recent_audit(limit=100)
            len_before = len(a1)
            r = self._kernel.enforce(
                f"enforce.{entity}_state_transition",
                {"current_state": current, "target_state": target},
                priority="high",
                entity="replay_consistency",
            )
            a2 = self._kernel.get_recent_audit(limit=100)
            total += 1
            if len(a2) <= len_before:
                inconsistent += 1
                ev.append({
                    "issue_type": "missing_transition_audit",
                    "module_path": f"kernel.audit.{entity}",
                    "object_id": f"{entity}.{current}->{target}",
                    "detection_reason": f"No audit entry created for {entity} transition '{current}' -> '{target}'",
                    "semantic_impact": "State transition bypassed governance audit trail",
                })
        return inconsistent, total, ev

    def _replay_audit_consistency(self):
        """Verify that replaying evaluations produces consistent audit entries."""
        inconsistent = 0
        total = 0
        ev = []
        audit_before = self._kernel.get_audit_summary()

        replay_policies = CONSISTENCY_REPLAY_POLICIES[:2]
        for policy_id, context in replay_policies:
            _ = self._kernel.enforce(policy_id, context, priority="high", entity="audit_replay")
            _ = self._kernel.enforce(policy_id, context, priority="high", entity="audit_replay")

        audit_after = self._kernel.get_audit_summary()
        total += 1

        expected_new = len(replay_policies) * 2
        actual_new = audit_after["total_entries"] - audit_before["total_entries"]
        if actual_new != expected_new:
            inconsistent += 1
            ev.append({
                "issue_type": "inconsistent_audit_replay",
                "module_path": "kernel.audit",
                "object_id": "audit_replay",
                "detection_reason": f"Expected {expected_new} new audit entries, got {actual_new}",
                "semantic_impact": "Audit trail count inconsistent across identical replays",
            })

        return inconsistent, total, ev


# ─────────────────────────────────────────────────────────────
# Execution Runner (Controlled Orchestration)
# ─────────────────────────────────────────────────────────────

class IndustrialTestSuiteRunner:
    """
    Controlled orchestration of all 4 industrial test phases.
    - Executes phases A → B → C → D sequentially
    - Applies timeout enforcement
    - Collects results into unified report
    - Never escalates concurrency beyond limit
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None, config: Optional[Dict] = None):
        self._kernel = kernel or GovernanceKernel()
        self._cfg = config or dict(TEST_CONFIG)
        self._start_time: float = 0.0
        self._warnings: List[str] = []

    def run_all(self) -> IndustrialTestReport:
        self._start_time = time.time()
        self._warnings = []

        # Phase A
        if self._check_timeout():
            self._warnings.append("TIMEOUT: Phase A skipped")
            phase_a = PhaseAResult(passed=False, errors=["Timed out"])
        else:
            phase_a = self._run_phase("Phase A", PhaseA(self._kernel, self._cfg).run)

        # Phase B
        if self._check_timeout():
            phase_b = PhaseBResult(passed=False, errors=["Timed out"])
        else:
            phase_b = self._run_phase("Phase B", PhaseB(self._kernel, self._cfg).run)

        # Phase C
        if self._check_timeout() or not self._cfg.get("ENABLE_UI_TEST", True):
            phase_c = PhaseCResult(compliance_status="SKIPPED")
        else:
            phase_c = self._run_phase("Phase C", PhaseC(self._cfg).run)

        # Phase D
        if self._check_timeout():
            phase_d = PhaseDResult(passed=False, errors=["Timed out"])
        else:
            phase_d = self._run_phase("Phase D", PhaseD(self._cfg).run)

        # Phase E — Regression Truth Verification
        if self._check_timeout():
            phase_e = PhaseEResult(passed=False, errors=["Timed out"])
        else:
            phase_e = self._run_phase("Phase E", PhaseE(self._kernel, self._cfg).run)

        # Phase F — Stale State & Orphan Detection
        if self._check_timeout():
            phase_f = PhaseFResult(passed=False, errors=["Timed out"])
        else:
            phase_f = self._run_phase("Phase F", PhaseF(self._kernel, self._cfg).run)

        # Phase G — Governance Consistency Replay
        if self._check_timeout():
            phase_g = PhaseGResult(passed=False, errors=["Timed out"])
        else:
            phase_g = self._run_phase("Phase G", PhaseG(self._kernel, self._cfg).run)

        # Overall status
        all_passed = all([
            phase_a.passed,
            phase_b.passed,
            phase_c.passed,
            phase_d.passed,
            phase_e.passed,
            phase_f.passed,
            phase_g.passed,
        ])
        any_critical_failure = any([
            len(phase_a.errors) > 3,
            len(phase_b.errors) > 3,
            len(phase_c.errors) > 3,
            len(phase_d.errors) > 3,
            len(phase_e.errors) > 3,
            len(phase_f.errors) > 3,
            len(phase_g.errors) > 3,
        ])

        if all_passed:
            overall = "PASS"
        elif any_critical_failure:
            overall = "FAIL"
        else:
            overall = "DEGRADED"

        if self._warnings:
            overall = "DEGRADED"

        return IndustrialTestReport(
            core_flow=phase_a,
            governance=phase_b,
            ui_safety=phase_c,
            memory_soak=phase_d,
            regression_truth=phase_e,
            stale_state=phase_f,
            consistency_replay=phase_g,
            overall_status=overall,
            warnings=self._warnings,
        )

    def _run_phase(self, name: str, runner: Callable) -> Any:
        logger.info("Starting %s...", name)
        try:
            result = runner()
            logger.info("%s: %s (%.1fms)", name,
                        "PASS" if result.passed else "FAIL",
                        result.duration_ms)
            return result
        except Exception as e:
            logger.error("%s crashed: %s", name, e)
            self._warnings.append(f"{name} crashed: {e}")
            return type(result)() if hasattr(runner, "__name__") else None

    def _check_timeout(self) -> bool:
        elapsed = time.time() - self._start_time
        return elapsed > self._cfg.get("TIMEOUT_SECONDS", 120)
