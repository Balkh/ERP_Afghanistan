"""
Phase 31 Module 4 — Architectural Drift Prevention & Immunity Layer
=====================================================================
Establishes a permanent architectural immunity layer that prevents regression of:
- Permission surface drift (AllowAny reintroduction)
- Configuration duplication (SystemConfig / JSON / Installer resurrection)
- Contract violations (frontend-backend mismatch)
- Engine proliferation (new duplicate business engines)
- Silent fallback truth creation

This module does NOT change behavior.
It enforces long-term architectural stability.

Final outcome:
  ➡ SYSTEM CAN NO LONGER RE-INTRODUCE OLD ARCHITECTURAL ANTI-PATTERNS
  ➡ DRIFT BECOMES DETECTABLE AND BLOCKABLE
  ➡ SSOT IS SELF-PRESERVING

Usage:
    python backend/scripts/drift_check.py                    # Run all checks
    python backend/scripts/drift_check.py --rule A           # Run specific rule
    python backend/scripts/drift_check.py --layer 1          # Run specific layer
    python backend/scripts/drift_check.py --pre-commit       # Pre-commit validation mode
    python backend/scripts/drift_check.py --post-audit       # Post-change audit mode
    python backend/scripts/drift_check.py --immunity-state   # Full immunity state check
    python backend/scripts/drift_check.py --fix              # Auto-fix where possible
    python backend/scripts/drift_check.py --json             # JSON output for CI
"""
import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# =========================================================================
# ENUMS & DATA CLASSES
# =========================================================================

class Severity(Enum):
    BLOCK = "BLOCK"
    HIGH = "HIGH"
    WARNING = "WARNING"
    INFO = "INFO"


class Layer(Enum):
    LAYER1 = "1 — Drift Detection Ruleset"
    LAYER2 = "2 — Architectural Immunity Guards"
    LAYER3 = "3 — Engine Proliferation Control"
    LAYER4 = "4 — Contract Immutability System"
    LAYER5 = "5 — Drift Prevention Enforcement Mode"


@dataclass
class DriftViolation:
    rule: str
    severity: Severity
    file: str
    line: int
    message: str
    suggestion: str = ""
    context: str = ""
    layer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "suggestion": self.suggestion,
            "context": self.context,
            "layer": self.layer,
        }


@dataclass
class DriftReport:
    violations: List[DriftViolation] = field(default_factory=list)
    files_scanned: int = 0
    rules_applied: int = 0
    immunity_score: float = 100.0  # 100 = perfect, 0 = critical drift

    @property
    def has_blockers(self) -> bool:
        return any(v.severity == Severity.BLOCK for v in self.violations)

    @property
    def has_high_risk(self) -> bool:
        return any(v.severity == Severity.HIGH for v in self.violations)

    def add(self, violation: DriftViolation):
        self.violations.append(violation)

    def summary(self) -> str:
        blockers = sum(1 for v in self.violations if v.severity == Severity.BLOCK)
        high = sum(1 for v in self.violations if v.severity == Severity.HIGH)
        warnings = sum(1 for v in self.violations if v.severity == Severity.WARNING)
        info = sum(1 for v in self.violations if v.severity == Severity.INFO)

        status = "❌ BLOCKED" if blockers > 0 else (
            "⚠ HIGH RISK" if high > 0 else (
                "⚡ WARNINGS" if warnings > 0 else "✅ PASS"
            )
        )

        return (
            f"\n{'='*70}\n"
            f"  ARCHITECTURAL DRIFT & IMMUNITY REPORT\n"
            f"  Status: {status}  |  Immunity Score: {self.immunity_score:.1f}/100\n"
            f"{'='*70}\n"
            f"  Files scanned: {self.files_scanned}\n"
            f"  Rules applied: {self.rules_applied}\n"
            f"  BLOCK: {blockers} | HIGH: {high} | WARNING: {warnings} | INFO: {info}\n"
            f"{'='*70}\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_violations": len(self.violations),
                "blockers": sum(1 for v in self.violations if v.severity == Severity.BLOCK),
                "high_risk": sum(1 for v in self.violations if v.severity == Severity.HIGH),
                "warnings": sum(1 for v in self.violations if v.severity == Severity.WARNING),
                "info": sum(1 for v in self.violations if v.severity == Severity.INFO),
                "files_scanned": self.files_scanned,
                "rules_applied": self.rules_applied,
                "immunity_score": self.immunity_score,
                "passed": not self.has_blockers and not self.has_high_risk,
            },
            "violations": [v.to_dict() for v in self.violations],
        }


# =========================================================================
# CONFIGURATION — ALLOWED PATHS & ENDPOINTS
# =========================================================================

# Files where AllowAny is permitted (CLASS A endpoints only)
ALLOWANY_WHITELIST = {
    "security/views.py",
}

# Endpoint functions that may use AllowAny (login, refresh, logout, password_reset)
ALLOWANY_SAFE_ENDPOINTS = {
    "login_view",
    "refresh_token_view",
    "logout_view",
    "password_reset_request",
    "password_reset_confirm",
}

# Files to exclude from all drift checks (the drift checker itself, scripts, etc.)
DRIFT_CHECK_EXCLUDE = {
    "scripts/drift_check.py",
}

# Production domain modules — each must have exactly ONE source of truth
DOMAIN_OWNERSHIP = {
    "Company": {"models/system.py", "core/models/system.py"},
    "Permissions": {"security/models.py", "security/permissions.py"},
    "FinancialTruth": {"accounting/services/journal_engine.py"},
    "Config": {"core/models/system.py"},  # Company model ONLY
    "Roles": {"security/models.py", "security/ui_scopes.py"},
}

# Known/authorized Engine classes — all others are flagged
ENGINE_WHITELIST = {
    "journal_engine.py",
    "payment_engine.py",
    "invoice_template_engine.py",
    "template_registry.py",
    "operational_intelligence.py",
    "financial_reports.py",
    "export_engine.py",
    "cashflow_engine.py",
    "anomaly_detection.py",
    "credit_policy_engine.py",
    "financial_policy_engine.py",
    "financial_truth_engine.py",
    "anomaly_graph.py",
    "drift.py",
    "patterns.py",
    "reconstruction.py",
    "anomaly_foresight.py",
    "prediction_engine.py",
    "reasoning_engine.py",
    "risk_engine.py",
    "correlation.py",
    "replay.py",
    "trace_engine.py",
    "verifier.py",
    "rules_engine.py",
    "decision_engine.py",
    "import_pipeline.py",
}

# Business config keys that MUST NOT appear in SystemConfig, JSON, or installer
BUSINESS_CONFIG_KEYS = {
    "company_name", "company_code", "default_currency", "secondary_currency",
    "tax_number", "registration_number", "invoice_prefix", "invoice_footer",
    "business_address", "business_phone", "business_email",
    "invoice_terms", "payment_terms", "shipping_address",
}

# Technical config keys that ARE allowed in SystemConfig
TECHNICAL_CONFIG_KEYS = {
    "theme", "language", "timezone", "low_stock_threshold",
    "auto_backup", "backup_frequency", "email_notifications",
    "low_stock_alerts", "expiry_alerts", "session_timeout",
    "date_format", "number_format",
}

# Fallback patterns that indicate hidden business logic
FALLBACK_PATTERNS = [
    re.compile(r'fallback.*company', re.IGNORECASE),
    re.compile(r'fallback.*currency', re.IGNORECASE),
    re.compile(r'fallback.*config', re.IGNORECASE),
    re.compile(r'fallback.*default.*value', re.IGNORECASE),
    re.compile(r'silent.*default', re.IGNORECASE),
    re.compile(r'hidden.*fallback', re.IGNORECASE),
]

# Frontend role names that MUST be defined by backend only
HARDCODED_ROLES = {
    "Admin", "Manager", "Accountant", "Pharmacist", "Cashier",
    "Supervisor", "Warehouse", "HR", "General",
}

ROLE_ASSIGNMENT_PATTERN = re.compile(
    r'role\s*[=:]\s*["\'](' + '|'.join(HARDCODED_ROLES) + r')["\']'
)

# Simulation layer MUST NOT leak into production
SIMULATION_IMPORTS_TO_DETECT = {
    "from simulation",
    "import simulation",
}

# Production module directories
PRODUCTION_MODULES = {
    "accounting", "sales", "purchases", "inventory", "payments",
    "hr", "payroll", "expenses", "fixed_assets", "returns",
    "backup", "security", "core",
}

# Engine class detection
ENGINE_CLASS_PATTERN = re.compile(r'class\s+\w*Engine\b')

# Single execution path — branch indicators that create dual truth
DUAL_PATH_PATTERNS = [
    re.compile(r'if\s+\w+\s*==\s*["\'].*gateway.*["\']|\bgateway\b'),
    re.compile(r'if\s+\w+\s*==\s*["\'].*legacy.*["\']|\blegacy\b'),
]


# =========================================================================
# ═══════════════════════════════════════════════════════════════════════
# LAYER 1 — DRIFT DETECTION RULESET
# ═══════════════════════════════════════════════════════════════════════
# =========================================================================

def check_permission_drift(report: DriftReport, backend_root: Path):
    """
    RULE A — PERMISSION DRIFT
    Flag if any new AllowAny is added outside CLASS A endpoints:
      - login
      - refresh
      - logout
      - password reset
    """
    pattern = re.compile(
        r'permission_classes\s*=\s*\[.*AllowAny.*\]'
        r'|@permission_classes\(\[AllowAny\]\)'
    )

    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception:
            continue

        report.files_scanned += 1

        # Skip whitelisted files entirely
        if rel_path in ALLOWANY_WHITELIST:
            continue

        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                # Check if this is a CLASS A endpoint function
                function_name = _get_enclosing_function(lines, i)
                if function_name and function_name in ALLOWANY_SAFE_ENDPOINTS:
                    continue  # Allow CLASS A endpoints

                report.add(DriftViolation(
                    rule="A-PERMISSION-DRIFT",
                    severity=Severity.HIGH,
                    file=rel_path,
                    line=i,
                    message="AllowAny detected outside whitelisted endpoints. "
                            "Only login/refresh/logout/password_reset may use AllowAny.",
                    suggestion="Use IsAuthenticated or RoleBasedPermission. "
                               "All other endpoints must require authentication.",
                    context=line.strip(),
                    layer=Layer.LAYER1.value,
                ))


def check_config_drift(report: DriftReport, backend_root: Path, frontend_root: Path):
    """
    RULE B — CONFIG DRIFT
    Flag if any business field appears in:
      - SystemConfig
      - JSON settings
      - installer config
      - frontend local storage
    """
    # ── Check backend for SystemConfig business key usage ──
    business_access_allowed = {
        "models/system.py",
        "core/models/system.py",
        "core/serializers.py",
        "core/urls.py",
        "pdf_generator.py",
        "invoice_template_engine.py",
    }

    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1

        # Check if file uses SystemConfig
        uses_system_config = "SystemConfig" in content
        if not uses_system_config:
            continue

        # If it uses SystemConfig AND references business keys, flag it
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for key in BUSINESS_CONFIG_KEYS:
                if f"'{key}'" in line or f'"{key}"' in line:
                    # Allow if accessing from Company model (not SystemConfig)
                    if rel_path in business_access_allowed and "Company" in content:
                        continue
                    report.add(DriftViolation(
                        rule="B-CONFIG-DRIFT",
                        severity=Severity.BLOCK,
                        file=rel_path,
                        line=i,
                        message=f"Business config key '{key}' referenced in file that uses SystemConfig. "
                                "Business config MUST come from Company model, not SystemConfig.",
                        suggestion=f"Move '{key}' to Company model. "
                                   "SystemConfig is for technical settings only (theme, language, etc.).",
                        context=line.strip(),
                        layer=Layer.LAYER1.value,
                    ))
                    break

    # ── Check frontend JSON files for business config duplication ──
    for json_file in frontend_root.rglob("*.json"):
        rel_path = str(json_file.relative_to(frontend_root))
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        report.files_scanned += 1
        for key in BUSINESS_CONFIG_KEYS:
            if isinstance(data, dict) and key in data:
                report.add(DriftViolation(
                    rule="B-CONFIG-DRIFT",
                    severity=Severity.BLOCK,
                    file=rel_path,
                    line=0,
                    message=f"Business config key '{key}' found in frontend JSON file. "
                            "Frontend must NOT duplicate business configuration.",
                    suggestion=f"Remove '{key}' from JSON. "
                               "Frontend must read company config from /api/companies/ endpoint.",
                    context=f"Key: {key}",
                    layer=Layer.LAYER1.value,
                ))

    # ── Check installer config for business duplication ──
    for cfg_file in backend_root.rglob("installer_config.py") or frontend_root.rglob("installer_config.py"):
        try:
            content = cfg_file.read_text(encoding="utf-8")
        except Exception:
            continue
        report.files_scanned += 1
        for key in BUSINESS_CONFIG_KEYS:
            if key in content:
                report.add(DriftViolation(
                    rule="B-CONFIG-DRIFT",
                    severity=Severity.BLOCK,
                    file=str(cfg_file.relative_to(backend_root) if cfg_file.parents[0] == backend_root
                             else cfg_file.relative_to(frontend_root)),
                    line=0,
                    message=f"Business config key '{key}' found in installer config. "
                            "Installer must NOT define business configuration.",
                    suggestion=f"Remove '{key}' from installer config. "
                               "Business config is set via Company model only.",
                    context=f"Key: {key}",
                    layer=Layer.LAYER1.value,
                ))


def check_engine_drift(report: DriftReport, backend_root: Path):
    """
    RULE C — ENGINE DRIFT
    Flag if new class contains suffix "Engine" and is not in the whitelist.
    """
    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        if py_file.name in ENGINE_WHITELIST:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if ENGINE_CLASS_PATTERN.search(line):
                # Allow if in simulation layer
                if "simulation" in rel_path:
                    continue
                report.add(DriftViolation(
                    rule="C-ENGINE-DRIFT",
                    severity=Severity.HIGH,
                    file=rel_path,
                    line=i,
                    message=f"New Engine class detected: {line.strip()}. "
                            "No new Engine classes allowed without consolidation check.",
                    suggestion="Does this duplicate existing domain logic? "
                               "Consolidate with existing implementation or get explicit approval.",
                    context=line.strip(),
                    layer=Layer.LAYER1.value,
                ))


def check_contract_drift(report: DriftReport, frontend_root: Path):
    """
    RULE D — CONTRACT DRIFT
    Flag if frontend uses hardcoded role names, permission logic, or business rules.
    """
    # Exceptions: files that are allowed to reference role names
    role_exception_files = {
        "role_manager.py",
        "sidebar.py",
        "role_renderer.py",
    }

    for py_file in frontend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(frontend_root))
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            # Check for hardcoded role assignments (not comparisons)
            if ROLE_ASSIGNMENT_PATTERN.search(line):
                # Allow role_manager, sidebar, role_renderer
                if any(ex in rel_path for ex in role_exception_files):
                    continue
                # Allow if it's a comparison, not assignment
                if "==" in line or "!=" in line:
                    continue
                report.add(DriftViolation(
                    rule="D-CONTRACT-DRIFT",
                    severity=Severity.HIGH,
                    file=rel_path,
                    line=i,
                    message="Hardcoded role name detected in frontend. "
                            "Frontend must NOT define roles or permissions.",
                    suggestion="Use backend ui_scopes for all permission decisions. "
                               "Roles are defined by backend security/ui_scopes.py only.",
                    context=line.strip(),
                    layer=Layer.LAYER1.value,
                ))

    # Check for permission logic in frontend
    permission_logic_patterns = [
        re.compile(r'\.has_permission\b'),
        re.compile(r'can_access\b'),
        re.compile(r'is_authorized\b'),
    ]
    for py_file in frontend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(frontend_root))
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Only check role_manager for permission logic — no other frontend files
        if "role_manager" not in rel_path:
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                for pattern in permission_logic_patterns:
                    if pattern.search(line):
                        # Allow imports and definitions
                        if "import" in line or "def " in line or "class " in line:
                            continue
                        report.add(DriftViolation(
                            rule="D-CONTRACT-DRIFT-PERM",
                            severity=Severity.WARNING,
                            file=rel_path,
                            line=i,
                            message="Permission logic detected outside role_manager. "
                                    "All permission decisions belong in role_manager.py or backend.",
                            suggestion="Use backend ui_scopes for permission visibility decisions.",
                            context=line.strip(),
                            layer=Layer.LAYER1.value,
                        ))


# =========================================================================
# ═══════════════════════════════════════════════════════════════════════
# LAYER 2 — ARCHITECTURAL IMMUNITY GUARDS
# ═══════════════════════════════════════════════════════════════════════
# =========================================================================

def check_ssot_immutability(report: DriftReport, backend_root: Path):
    """
    GUARD 1 — SSOT IMMUTABILITY CHECK
    Verify that no second source of truth exists for company config.
    Each domain must have exactly ONE source of truth.
    """
    # Company-specific field names that are NOT common Django model fields
    company_specific_fields = {
        "company_name", "company_code", "default_currency", "company_logo",
        "tax_number", "registration_number", "invoice_prefix", "invoice_footer",
        "business_address", "business_phone", "business_email",
        "invoice_terms", "payment_terms", "shipping_address",
    }
    # Common Django field names that appear in many models - NOT company indicators
    common_django_fields = {"name", "code", "currency"}

    for py_file in backend_root.rglob("models*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1

        # Skip the canonical Company model file
        if "system.py" in rel_path:
            continue

        # Check for duplicate Company-specific model fields
        has_specific_fields = sum(1 for f in company_specific_fields if f in content)
        has_models_dot_model = "models.Model" in content or "BaseModel" in content

        # Only flag if it has company-specific fields (not just common Django fields)
        if has_specific_fields >= 2 and has_models_dot_model:
            detected = [f for f in company_specific_fields if f in content]
            report.add(DriftViolation(
                rule="GUARD1-SSOT",
                severity=Severity.BLOCK,
                file=rel_path,
                line=0,
                message=f"Model file defines {len(detected)} company-specific fields. "
                        "This creates a SECOND source of truth for company configuration.",
                suggestion="Company model (core/models/system.py) is the ONLY source of "
                           "business configuration. Remove duplicate fields.",
                context=f"Company-specific fields detected: {detected}",
                layer=Layer.LAYER2.value,
            ))


def check_domain_ownership(report: DriftReport, backend_root: Path):
    """
    GUARD 2 — DOMAIN OWNERSHIP CHECK
    Each domain must have exactly ONE owner.
    Verify no domain's truth is duplicated outside its canonical location.
    """
    # Domain-specific field patterns — high-specificity signals only
    domain_field_signals = {
        "Company": ["company_name", "company_code", "company_logo", "tax_number", "registration_number"],
        "FinancialTruth": ["JournalEngine", "journal_engine"],
        "Config": ["SystemConfig"],
    }

    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Only check model and service files
        if "models" not in rel_path and "services" not in rel_path:
            continue
        if "system.py" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1

        for domain, signals in domain_field_signals.items():
            matches = sum(1 for s in signals if s in content)
            if matches >= 2:
                # Determine if this file is the canonical owner
                is_canonical = any(
                    fn in rel_path for fn in DOMAIN_OWNERSHIP.get(domain, set())
                )
                if not is_canonical:
                    report.add(DriftViolation(
                        rule="GUARD2-DOMAIN-OWNERSHIP",
                        severity=Severity.WARNING,
                        file=rel_path,
                        line=0,
                        message=f"Found {matches} fields from '{domain}' domain outside its canonical location. "
                                f"'{domain}' is owned by: {DOMAIN_OWNERSHIP.get(domain, set())}",
                        suggestion=f"Move '{domain}' configuration back to its canonical owner location. "
                                   "Each domain must have exactly ONE source of truth.",
                        context=f"Signals found: {[s for s in signals if s in content]}",
                        layer=Layer.LAYER2.value,
                    ))


def check_fallback_elimination(report: DriftReport, backend_root: Path, frontend_root: Path):
    """
    GUARD 3 — FALLBACK ELIMINATION RULE
    Forbidden:
      - hidden fallback business logic
      - silent default values replacing backend truth
      - frontend-only recovery logic for business data
    Allowed:
      - UI-only fallback strings (non-business critical)
    """
    roots = [("backend", backend_root), ("frontend", frontend_root)]

    for side, root in roots:
        for py_file in root.rglob("*.py"):
            rel_path = str(py_file.relative_to(root))
            if rel_path in DRIFT_CHECK_EXCLUDE:
                continue
            if "tests" in rel_path or "migrations" in rel_path:
                continue
            # Skip UI-only fallback strings files
            if "constants.py" in rel_path or "i18n" in rel_path:
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            report.files_scanned += 1
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                for pattern in FALLBACK_PATTERNS:
                    if pattern.search(line):
                        stripped = line.strip()
                        # Allow comments and docstrings
                        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                            continue
                        report.add(DriftViolation(
                            rule="GUARD3-FALLBACK",
                            severity=Severity.WARNING,
                            file=f"{side}/{rel_path}",
                            line=i,
                            message="Potential fallback business logic detected. "
                                    "Fallback logic creates hidden truth that bypasses the Company model.",
                            suggestion="Use Company model directly instead of fallback defaults. "
                                       "UI-only display fallbacks are acceptable for non-critical strings.",
                            context=line.strip(),
                            layer=Layer.LAYER2.value,
                        ))
                        break


# =========================================================================
# ═══════════════════════════════════════════════════════════════════════
# LAYER 3 — ENGINE PROLIFERATION CONTROL
# ═══════════════════════════════════════════════════════════════════════
# =========================================================================

def check_engine_creation_control(report: DriftReport, backend_root: Path):
    """
    RULE 1 — ENGINE CREATION CONTROL
    No new "Engine" class allowed unless:
      - It does NOT duplicate existing domain logic
      - It passes consolidation check
      - It is explicitly required for isolation of external system logic only
    """
    check_engine_drift(report, backend_root)  # Reuses Rule C engine detection

    # Additional check: look for "new" duplicate patterns
    domain_patterns = {
        "journal": ["journal", "accounting", "ledger"],
        "payment": ["payment", "receipt", "settlement"],
        "inventory": ["inventory", "stock", "warehouse"],
        "reporting": ["report", "reporting", "export"],
    }

    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        if py_file.name in ENGINE_WHITELIST:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1

        # Check for duplicate domain service patterns
        for domain, keywords in domain_patterns.items():
            matches = sum(1 for k in keywords if k.lower() in content.lower())
            if matches >= 2:
                lines = content.splitlines()
                has_class_def = any("class " in line for line in lines[:30])
                if has_class_def:
                    report.add(DriftViolation(
                        rule="C-ENGINE-PROLIFERATION",
                        severity=Severity.WARNING,
                        file=rel_path,
                        line=0,
                        message=f"Potential duplicate '{domain}' domain logic. "
                                f"Found {matches} domain-related keywords.",
                        suggestion=f"Consolidate with existing {domain} service. "
                                   "Do not create new parallel implementations.",
                        context=f"Domain: {domain}, Keywords matched: {[k for k in keywords if k.lower() in content.lower()]}",
                        layer=Layer.LAYER3.value,
                    ))


def check_simulation_isolation(report: DriftReport, backend_root: Path):
    """
    RULE 2 — SIMULATION ISOLATION ENFORCEMENT
    Simulation layer:
      - MUST NOT affect production data
      - MUST NOT generate business truth
      - MUST NOT act as fallback execution path
    """
    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path or "simulation" in rel_path:
            continue

        # Only check production modules
        if not any(d in rel_path for d in PRODUCTION_MODULES):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for imp in SIMULATION_IMPORTS_TO_DETECT:
                if imp in line and ("import" in line):
                    report.add(DriftViolation(
                        rule="GUARD-SIMULATION-LEAK",
                        severity=Severity.BLOCK,
                        file=rel_path,
                        line=i,
                        message="Simulation import detected in production module. "
                                "Simulation layer MUST NOT affect production data or logic.",
                        suggestion="Move this import or refactor so simulation code does not "
                                   "leak into production execution paths.",
                        context=line.strip(),
                        layer=Layer.LAYER3.value,
                    ))
                    break


def check_single_execution_path(report: DriftReport, backend_root: Path):
    """
    RULE 3 — SINGLE EXECUTION PATH PRINCIPLE
    Every business operation MUST have:
      ONE input → ONE processing path → ONE output
    No branching engine selection allowed.
    """
    # Check for dual-path patterns in production modules
    for py_file in backend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(backend_root))
        if rel_path in DRIFT_CHECK_EXCLUDE:
            continue
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Only check production modules
        if not any(d in rel_path for d in PRODUCTION_MODULES):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            # Check for branching execution path selectors
            if "use_gateway" in line or "use_legacy" in line:
                if "=" in line and not line.strip().startswith("#"):
                    report.add(DriftViolation(
                        rule="GUARD-DUAL-PATH",
                        severity=Severity.WARNING,
                        file=rel_path,
                        line=i,
                        message="Branching execution path detected. "
                                "Single execution path principle requires ONE processing path.",
                        suggestion="Consolidate to a single execution path. "
                                   "The MigrationRouter already handles gateway/engine routing.",
                        context=line.strip(),
                        layer=Layer.LAYER3.value,
                    ))

            for pattern in DUAL_PATH_PATTERNS:
                if pattern.search(line):
                    if "migration_router" in line or "MigrationRouter" in line:
                        continue  # MigrationRouter is the single authorized router
                    if "gateway" in rel_path.lower():
                        continue  # Gateway files are expected to reference gateway
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""'):
                        continue
                    report.add(DriftViolation(
                        rule="GUARD-DUAL-PATH",
                        severity=Severity.INFO,
                        file=rel_path,
                        line=i,
                        message="Potential dual execution path detected. "
                                "Only MigrationRouter should handle routing decisions.",
                        suggestion="Delegate routing to MigrationRouter. "
                                   "Do not create branching execution logic.",
                        context=line.strip(),
                        layer=Layer.LAYER3.value,
                    ))


# =========================================================================
# ═══════════════════════════════════════════════════════════════════════
# LAYER 4 — CONTRACT IMMUTABILITY SYSTEM
# ═══════════════════════════════════════════════════════════════════════
# =========================================================================

def check_backend_truth_authority(report: DriftReport, frontend_root: Path):
    """
    RULE 1 — BACKEND IS ONLY TRUTH AUTHORITY
    Frontend MUST NOT:
      - define roles
      - define permissions
      - define business rules
      - define fallback logic for business data
    """
    # Check frontend for role definitions
    role_definition_patterns = [
        re.compile(r'class\s+\w*Role\b'),
        re.compile(r'class\s+\w*Permission\b'),
        re.compile(r'ROLE_\w+\s*='),
        re.compile(r'PERMISSION_\w+\s*='),
    ]

    for py_file in frontend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(frontend_root))
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Skip role_manager.py — it reads from backend but defines display helpers
        if "role_manager" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern in role_definition_patterns:
                if pattern.search(line):
                    report.add(DriftViolation(
                        rule="CONTRACT-BACKEND-TRUTH",
                        severity=Severity.BLOCK,
                        file=f"frontend/{rel_path}",
                        line=i,
                        message="Frontend defines roles or permissions. "
                                "Backend is the ONLY authority for roles and permissions.",
                        suggestion="Remove role/permission definitions from frontend. "
                                   "All roles and permissions must be defined in backend/models.py.",
                        context=line.strip(),
                        layer=Layer.LAYER4.value,
                    ))
                    break


def check_api_contract_freeze(report: DriftReport, frontend_root: Path, backend_root: Path):
    """
    RULE 2 — API CONTRACT FREEZE
    All API structures are considered STABLE CONTRACTS.
    Any change must preserve backward compatibility OR explicitly version API.
    """
    # Check frontend API client for hardcoded endpoint assumptions
    hardcoded_endpoint_patterns = [
        re.compile(r'\.get\(\s*["\']/api/[^"\'{}]*["\']'),
        re.compile(r'\.post\(\s*["\']/api/[^"\'{}]*["\']'),
        re.compile(r'\.put\(\s*["\']/api/[^"\'{}]*["\']'),
        re.compile(r'\.delete\(\s*["\']/api/[^"\'{}]*["\']'),
    ]

    for py_file in frontend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(frontend_root))
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Skip the API client itself
        if "client.py" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        hardcoded_calls = []
        for i, line in enumerate(lines, 1):
            for pattern in hardcoded_endpoint_patterns:
                if pattern.search(line):
                    # Extract the endpoint path
                    match = pattern.search(line)
                    hardcoded_calls.append((i, match.group(0)))
                    break

        if len(hardcoded_calls) >= 3:
            # Flag files with many hardcoded endpoints
            report.add(DriftViolation(
                rule="CONTRACT-API-FREEZE",
                severity=Severity.WARNING,
                file=f"frontend/{rel_path}",
                line=hardcoded_calls[0][0],
                message=f"File has {len(hardcoded_calls)} hardcoded API endpoint references. "
                        "API endpoints are STABLE CONTRACTS — changes must preserve backward compatibility.",
                suggestion="Use APIClient wrapper methods instead of raw endpoint strings. "
                           "Version API changes explicitly when breaking changes are unavoidable.",
                context=f"First endpoint: {hardcoded_calls[0][1]}",
                layer=Layer.LAYER4.value,
            ))


def check_frontend_projection_rule(report: DriftReport, frontend_root: Path):
    """
    RULE 3 — FRONTEND PROJECTION RULE
    Frontend data model = PURE PROJECTION ONLY
    - No business computation
    - No domain inference
    - No structural assumptions
    """
    # Check for business computation patterns in frontend
    business_computation_patterns = [
        (re.compile(r'calculate.*tax\b', re.IGNORECASE), "Tax calculation must come from backend"),
        (re.compile(r'calculate.*discount\b', re.IGNORECASE), "Discount calculation must come from backend"),
        (re.compile(r'compute.*total\b', re.IGNORECASE), "Total computation must come from backend"),
        (re.compile(r'def\s+.*cogs\b', re.IGNORECASE), "COGS computation belongs in backend only"),
        (re.compile(r'def\s+.*profit\b', re.IGNORECASE), "Profit computation belongs in backend only"),
    ]

    for py_file in frontend_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(frontend_root))
        if "tests" in rel_path or "migrations" in rel_path:
            continue
        # Skip role_manager — read-only display helpers
        if "role_manager" in rel_path:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        report.files_scanned += 1
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern, suggestion in business_computation_patterns:
                if pattern.search(line):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    report.add(DriftViolation(
                        rule="CONTRACT-FRONTEND-PROJECTION",
                        severity=Severity.WARNING,
                        file=f"frontend/{rel_path}",
                        line=i,
                        message=f"Frontend business computation detected: {pattern.pattern}. "
                                "Frontend must be a PURE PROJECTION of backend data.",
                        suggestion=suggestion,
                        context=line.strip(),
                        layer=Layer.LAYER4.value,
                    ))


# =========================================================================
# ═══════════════════════════════════════════════════════════════════════
# LAYER 5 — DRIFT PREVENTION ENFORCEMENT MODE
# ═══════════════════════════════════════════════════════════════════════
# =========================================================================

def run_pre_commit_validation(report: DriftReport, backend_root: Path, frontend_root: Path):
    """
    MODE 1 — PRE-COMMIT VALIDATION
    Before any change, check:
      - SSOT violation
      - duplicate truth creation
      - engine duplication
      - permission bypass
    If ANY fail: BLOCK CHANGE
    """
    # Run critical Layer 1 & 2 checks (fast subset for pre-commit)
    check_permission_drift(report, backend_root)
    check_ssot_immutability(report, backend_root)
    check_engine_drift(report, backend_root)
    check_simulation_isolation(report, backend_root)
    check_backend_truth_authority(report, frontend_root)


def run_post_change_audit(report: DriftReport, backend_root: Path, frontend_root: Path):
    """
    MODE 2 — POST-CHANGE AUDIT
    After change, verify:
      - no new AllowAny leakage
      - no new config duplication
      - no new engine overlap
      - no contract mismatch
    """
    # Run all checks
    report = run_all_checks(backend_root, frontend_root, report=report)

    # Calculate regression health
    if report.has_blockers:
        report.immunity_score = max(0, report.immunity_score - 30)
    if report.has_high_risk:
        report.immunity_score = max(0, report.immunity_score - 15)
    warning_count = sum(1 for v in report.violations if v.severity == Severity.WARNING)
    report.immunity_score = max(0, report.immunity_score - warning_count * 2)

    return report


def check_immunity_state(report: DriftReport, backend_root: Path, frontend_root: Path):
    """
    MODE 3 — ARCHITECTURAL IMMUNITY STATE
    System must maintain:
      - NO REGRESSION TO PRE-PHASE 31 STATE
      - NO SILENT DRIFT INTRODUCTION
      - NO MULTI-SOURCE TRUTH RECREATION
    """
    # Run comprehensive immunity health scan
    report = run_all_checks(backend_root, frontend_root, report=report)

    # Calculate immunity score
    base_score = 100.0
    blocker_penalty = 30.0
    high_penalty = 10.0
    warning_penalty = 2.0

    blocker_count = sum(1 for v in report.violations if v.severity == Severity.BLOCK)
    high_count = sum(1 for v in report.violations if v.severity == Severity.HIGH)
    warning_count = sum(1 for v in report.violations if v.severity == Severity.WARNING)

    report.immunity_score = max(
        0,
        base_score - (blocker_count * blocker_penalty) - (high_count * high_penalty) - (warning_count * warning_penalty)
    )

    return report


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def _get_enclosing_function(lines: List[str], line_number: int) -> Optional[str]:
    """Find the name of the function/method that contains the given line.
    Searches both backward (for simple function definitions) and forward
    (for decorator patterns where @permission_classes precedes def).
    """
    for i in range(line_number - 1, -1, -1):
        match = re.match(r'^\s*def\s+(\w+)', lines[i])
        if match:
            return match.group(1)
    for i in range(line_number - 1, min(len(lines), line_number + 3)):
        match = re.match(r'^\s*def\s+(\w+)', lines[i])
        if match:
            return match.group(1)
    return None


# =========================================================================
# MAIN EXECUTION
# =========================================================================

def run_all_checks(
    backend_root: Path,
    frontend_root: Path,
    specific_rule: Optional[str] = None,
    specific_layer: Optional[str] = None,
    report: Optional[DriftReport] = None,
) -> DriftReport:
    """Run all drift detection checks."""
    if report is None:
        report = DriftReport()

    # ── Layer 1: Drift Detection Ruleset ──
    layer1_checks = {
        "A": ("Permission Drift (AllowAny Detection)", lambda: check_permission_drift(report, backend_root)),
        "B": ("Config Drift (Duplication Detection)", lambda: check_config_drift(report, backend_root, frontend_root)),
        "C": ("Engine Drift (Proliferation Detection)", lambda: check_engine_drift(report, backend_root)),
        "D": ("Contract Drift (Frontend Truth Detection)", lambda: check_contract_drift(report, frontend_root)),
    }

    # ── Layer 2: Architectural Immunity Guards ──
    layer2_checks = {
        "G1": ("SSOT Immutability Check", lambda: check_ssot_immutability(report, backend_root)),
        "G2": ("Domain Ownership Check", lambda: check_domain_ownership(report, backend_root)),
        "G3": ("Fallback Elimination Rule", lambda: check_fallback_elimination(report, backend_root, frontend_root)),
    }

    # ── Layer 3: Engine Proliferation Control ──
    layer3_checks = {
        "EC1": ("Engine Creation Control", lambda: check_engine_creation_control(report, backend_root)),
        "EC2": ("Simulation Isolation Enforcement", lambda: check_simulation_isolation(report, backend_root)),
        "EC3": ("Single Execution Path Principle", lambda: check_single_execution_path(report, backend_root)),
    }

    # ── Layer 4: Contract Immutability System ──
    layer4_checks = {
        "CI1": ("Backend Truth Authority", lambda: check_backend_truth_authority(report, frontend_root)),
        "CI2": ("API Contract Freeze", lambda: check_api_contract_freeze(report, frontend_root, backend_root)),
        "CI3": ("Frontend Projection Rule", lambda: check_frontend_projection_rule(report, frontend_root)),
    }

    # ── Layer 5: Enforcement Mode ──
    layer5_checks = {
        "M1": ("Pre-Commit Validation", lambda: run_pre_commit_validation(report, backend_root, frontend_root)),
    }

    all_checks = {}
    if specific_layer in (None, "1"):
        all_checks.update(layer1_checks)
    if specific_layer in (None, "2"):
        all_checks.update(layer2_checks)
    if specific_layer in (None, "3"):
        all_checks.update(layer3_checks)
    if specific_layer in (None, "4"):
        all_checks.update(layer4_checks)
    if specific_layer in (None, "5"):
        all_checks.update(layer5_checks)

    for rule_id, (name, check_fn) in all_checks.items():
        if specific_rule and specific_rule.upper() != rule_id:
            continue
        try:
            check_fn()
            report.rules_applied += 1
        except Exception as e:
            print(f"  [ERROR] Rule {rule_id} ({name}) failed: {e}")

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 31 Module 4 — Architectural Drift Prevention & Immunity Layer"
    )
    parser.add_argument("--rule", help="Run specific rule (A, B, C, D, G1, G2, G3, EC1, EC2, EC3, CI1, CI2, CI3, M1)")
    parser.add_argument("--layer", choices=["1", "2", "3", "4", "5"], help="Run specific layer")
    parser.add_argument("--pre-commit", action="store_true", help="Pre-commit validation mode (fast, critical checks)")
    parser.add_argument("--post-audit", action="store_true", help="Post-change audit mode (full check + immunity score)")
    parser.add_argument("--immunity-state", action="store_true", help="Full immunity state check with score")
    parser.add_argument("--backend", default="backend", help="Backend root directory")
    parser.add_argument("--frontend", default="frontend", help="Frontend root directory")
    parser.add_argument("--fail-on", choices=["block", "high", "warning"], default="high",
                       help="Exit code threshold (default: high)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--fix", action="store_true", help="Auto-fix where possible")

    args = parser.parse_args()

    backend_root = Path(args.backend).resolve()
    frontend_root = Path(args.frontend).resolve()

    if not backend_root.exists():
        print(f"ERROR: Backend directory not found: {backend_root}")
        sys.exit(2)

    # Determine mode
    if args.pre_commit:
        report = DriftReport()
        run_pre_commit_validation(report, backend_root, frontend_root)
    elif args.post_audit:
        report = run_post_change_audit(DriftReport(), backend_root, frontend_root)
    elif args.immunity_state:
        report = check_immunity_state(DriftReport(), backend_root, frontend_root)
    elif args.rule or args.layer:
        report = run_all_checks(backend_root, frontend_root, specific_rule=args.rule, specific_layer=args.layer)
    else:
        report = run_all_checks(backend_root, frontend_root)

    # Auto-fix (limited capability)
    if args.fix:
        _auto_fix(report, backend_root, frontend_root)

    # Output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.summary())
        for v in report.violations:
            severity_str = v.severity.value
            print(f"  [{severity_str}] {v.rule}: {v.file}:{v.line}")
            print(f"    {v.message}")
            if v.suggestion:
                print(f"    => {v.suggestion}")
            print()

    # Exit code based on threshold
    if args.fail_on == "block" and report.has_blockers:
        sys.exit(1)
    elif args.fail_on == "high" and (report.has_blockers or report.has_high_risk):
        sys.exit(1)
    elif args.fail_on == "warning" and report.violations:
        sys.exit(1)

    sys.exit(0)


def _auto_fix(report: DriftReport, backend_root: Path, frontend_root: Path):
    """Auto-fix where possible (limited capability)."""
    fixes_applied = 0
    for v in report.violations:
        if v.rule == "B-CONFIG-DRIFT" and v.file.endswith(".json"):
            # Remove business keys from frontend JSON files (reported by rule B)
            json_path = frontend_root / v.file
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    key = v.context.replace("Key: ", "")
                    if isinstance(data, dict) and key in data:
                        del data[key]
                        with open(json_path, 'w') as f:
                            json.dump(data, f, indent=2)
                        fixes_applied += 1
                except Exception:
                    pass

    if fixes_applied > 0:
        print(f"\n  [FIX] Applied {fixes_applied} auto-fixes.")
    else:
        print("\n  [FIX] No auto-fixable violations found.")


if __name__ == "__main__":
    main()
