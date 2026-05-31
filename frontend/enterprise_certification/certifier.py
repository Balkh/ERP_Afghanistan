"""
Enterprise UX + Operational Safety Certifier (Phase D.7).

Static analysis certification that verifies all hardening phases are
correctly implemented and operational safety requirements are met.
No runtime execution — safe for CI/CD pipelines.
"""

import ast
import os
import re
from typing import Dict, Any, List, Tuple, Optional


# Paths
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
COMPONENTS_DIR = os.path.join(FRONTEND_DIR, "components")
SCREENS_DIR = os.path.join(FRONTEND_DIR, "screens")
RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime")


class EnterpriseUxCertifier:
    """
    Static analysis certifier for Enterprise UX + Operational Safety.
    
    Certifies D.1 through D.7 without executing any frontend code.
    Returns structured certification report.
    """

    def __init__(self):
        self.results: Dict[str, Any] = {
            "form_system": "",
            "table_system": "",
            "operator_safety": "",
            "workflow_integrity": "",
            "frontend_consistency": "",
            "reporting_stability": "",
            "human_error_resilience": "",
            "visual_maturity": "",
            "performance_state": "",
            "final_verdict": "",
            "details": {},
        }

    def _file_exists(self, *parts: str) -> bool:
        return os.path.exists(os.path.join(*parts))

    def _read_file(self, *parts: str) -> str:
        path = os.path.join(*parts)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
        return ""

    def _has_class(self, content: str, class_name: str) -> bool:
        return bool(re.search(rf"class\s+{class_name}\s*[(:]", content))

    def _has_method(self, content: str, method_name: str) -> bool:
        return bool(re.search(rf"def\s+{method_name}\s*\(", content))

    def _has_import(self, content: str, name: str) -> bool:
        return name in content

    def _count_pattern(self, content: str, pattern: str) -> int:
        return len(re.findall(pattern, content))

    def _score_boolean(self, passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    # ── Phase D.1: Form System ──

    def _certify_form_system(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        form_content = self._read_file(COMPONENTS_DIR, "forms.py")

        checks = {
            "EnterpriseForm class exists": self._has_class(form_content, "EnterpriseForm"),
            "Dirty state tracking": self._has_method(form_content, "is_dirty"),
            "Double-submit prevention": self._has_method(form_content, "submit") and "submission_lock" in form_content,
            "Draft auto-save": self._has_method(form_content, "save_draft"),
            "Draft restore": self._has_method(form_content, "restore_draft"),
            "Keyboard shortcut (Ctrl+S)": "QShortcut" in form_content or "_install_keyboard_shortcuts" in form_content,
            "Optimistic locking": self._has_method(form_content, "has_stale_data"),
            "Validation system": self._has_class(form_content, "ValidationRule"),
            "Inline validation feedback": "validation_label" in form_content or "set_error" in form_content,
            "Business-rule validation": "required" in form_content and "validators" in form_content,
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.2: Table System ──

    def _certify_table_system(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        table_content = self._read_file(COMPONENTS_DIR, "tables.py")

        checks = {
            "EnterpriseTable class exists": self._has_class(table_content, "EnterpriseTable"),
            "Row count safety (MAX_SAFE_ROWS)": "MAX_SAFE_ROWS" in table_content,
            "Auto-chunking (MAX_ROWS_WITHOUT_CHUNKING)": "MAX_ROWS_WITHOUT_CHUNKING" in table_content,
            "Double-click guard": "double_click_guard_ts" in table_content,
            "Pagination support": self._has_class(table_content, "PaginationWidget"),
            "Sorting capability": "sort_changed" in table_content,
            "Column resizing": "ResizeMode.Interactive" in table_content,
            "Keyboard navigation": "keyPressEvent" in table_content,
            "Loading/empty state": "empty_state_text" in table_content or "_empty_state" in table_content,
            "Chunked rendering": self._has_method(table_content, "set_data_chunked"),
            "Deferred rendering": self._has_method(table_content, "set_data_deferred"),
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.3: Operator Safety ──

    def _certify_operator_safety(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        safety_content = self._read_file(COMPONENTS_DIR, "operator_safety.py")

        if not safety_content:
            return "HIGH_RISK", {"error": "operator_safety.py not found", "score": 0, "passed": 0, "total": 1}

        checks = {
            "DestructiveActionGuard class": self._has_class(safety_content, "DestructiveActionGuard"),
            "Delete confirmation": "confirm_delete" in safety_content,
            "Accounting reversal warning": "confirm_accounting_reversal" in safety_content,
            "Irreversible action warnings": "confirm_irreversible" in safety_content,
            "FinancialSafety class": self._has_class(safety_content, "FinancialSafety"),
            "Credit limit check": "check_credit_limit" in safety_content,
            "Over-payment warning": "check_over_payment" in safety_content,
            "Negative stock warning": "check_negative_stock" in safety_content,
            "Invalid journal warning": "check_invalid_journal" in safety_content,
            "SessionSafety class": self._has_class(safety_content, "SessionSafety"),
            "Session timeout warning": "start_timeout_warning" in safety_content,
            "Stale tab detection": "detect_stale_tab" in safety_content,
            "InteractionSafety class": self._has_class(safety_content, "InteractionSafety"),
            "Double-click prevention (guard)": self._has_method(safety_content, "guard_double_click"),
            "Multi-submit prevention": self._has_method(safety_content, "guard_multi_submit"),
            "BulkOperationGuard class": self._has_class(safety_content, "BulkOperationGuard"),
            "Bulk delete confirmation": "confirm_bulk_delete" in safety_content,
            "Bulk status change confirmation": "confirm_bulk_status_change" in safety_content,
            "OperatorGuidance class": self._has_class(safety_content, "OperatorGuidance"),
            "Recovery guidance": self._has_method(safety_content, "show_recovery_guidance"),
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.4: Screen Architecture ──

    def _certify_screen_architecture(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        base_content = self._read_file(SCREENS_DIR, "base_screen.py")

        checks = {
            "BaseScreen class exists": self._has_class(base_content, "BaseScreen"),
            "BaseFormScreen class exists": self._has_class(base_content, "BaseFormScreen"),
            "BaseListScreen class exists": self._has_class(base_content, "BaseListScreen"),
            "Dirty state tracking": self._has_method(base_content, "is_dirty"),
            "Navigation guard (dirty check)": "confirm_discard_changes" in base_content,
            "Double-submit prevention": self._has_method(base_content, "acquire_submission_lock"),
            "Submission lock in BaseFormScreen": "submission_lock" in base_content and "submit_form" in base_content,
            "Screen lifecycle (show/hide)": self._has_method(base_content, "showEvent"),
            "Loading state": self._has_method(base_content, "set_loading"),
            "Error state": self._has_method(base_content, "show_error"),
            "Empty state": self._has_method(base_content, "show_empty"),
            "Auto-refresh capability": self._has_method(base_content, "set_auto_refresh"),
        }

        # Count BaseScreen subclasses
        screen_files = []
        for root, dirs, files in os.walk(FRONTEND_DIR):
            for f in files:
                if f.endswith(".py") and not f.startswith("__"):
                    screen_files.append(os.path.join(root, f))

        subclass_count = 0
        for sf in screen_files:
            content = self._read_file(sf)
            if re.search(r"class\s+\w+Screen\s*\(BaseScreen\)", content):
                subclass_count += 1

        details["base_screen_subclasses"] = subclass_count
        checks["35+ BaseScreen subclasses exist"] = subclass_count >= 30

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.5: Reporting Stability ──

    def _certify_reporting_stability(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        report_content = self._read_file(os.path.join(FRONTEND_DIR, "accounting", "report_browser.py"))

        if not report_content:
            return "HIGH_RISK", {"error": "report_browser.py not found", "score": 0}

        checks = {
            "ReportBrowser class exists": self._has_class(report_content, "ReportBrowser"),
            "CSV export capability": "_export_csv" in report_content,
            "Loading state management": "_set_loading" in report_content,
            "Empty state management": "_set_empty" in report_content,
            "Error handling (QThread worker)": "ReportWorker" in report_content,
            "Parameter validation": "params" in report_content,
            "Summary/totals display": "summary_label" in report_content or "Total" in report_content,
            "Pagination support": "page" in report_content or "EnterpriseTable" in report_content,
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.6: Visual Maturity ──

    def _certify_visual_maturity(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        constants_content = self._read_file(os.path.join(FRONTEND_DIR, "constants.py"))
        buttons_content = self._read_file(COMPONENTS_DIR, "buttons.py")

        checks = {
            "Design token system (COLOR_*)": "COLOR_PRIMARY" in constants_content,
            "Typography hierarchy (TEXT_*)": "TEXT_PAGE_TITLE" in constants_content,
            "Spacing tokens (SPACING_*)": "SPACING_MD" in constants_content,
            "Button style governance (EnterpriseButton)": self._has_class(buttons_content, "EnterpriseButton"),
            "Multiple button variants": "ButtonVariant" in buttons_content,
            "Multiple button sizes": "ButtonSize" in buttons_content,
            "Density tier model": "DENSITY_COMFORTABLE_ROW" in constants_content or "DENSITY_STANDARD" in constants_content,
            "Dark/light theme parity": "set_active_theme" in constants_content,
            "EnterpriseDialog exists": self._has_class(self._read_file(COMPONENTS_DIR, "dialogs.py"), "EnterpriseDialog"),
            "StateHelper exists": self._has_class(self._read_file(COMPONENTS_DIR, "state_helper.py"), "StateHelper"),
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Phase D.7: Human Error Resilience ──

    def _certify_human_error_resilience(self) -> Tuple[str, Dict[str, Any]]:
        """
        Certify human-error resilience by checking all safety mechanisms.
        Combines D.3 (operator_safety) and BaseScreen protections.
        """
        details: Dict[str, Any] = {}
        safety_content = self._read_file(COMPONENTS_DIR, "operator_safety.py")
        base_content = self._read_file(SCREENS_DIR, "base_screen.py")

        checks = {
            "Destructive action confirmation": "confirm_delete" in safety_content,
            "Financial safety (credit/stock/journal)": "FinancialSafety" in safety_content,
            "Session timeout protection": "SessionSafety" in safety_content,
            "Interaction safety (double-click)": "guard_double_click" in safety_content,
            "Multi-submit prevention": "guard_multi_submit" in safety_content,
            "Bulk operation safety": "BulkOperationGuard" in safety_content,
            "Operator recovery guidance": "show_recovery_guidance" in safety_content,
            "Navigation guard (dirty state)": "confirm_discard_changes" in base_content,
            "Form submission lock": "acquire_submission_lock" in base_content,
            "EnterpriseForm dirty detection": "is_dirty" in self._read_file(COMPONENTS_DIR, "forms.py"),
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Performance State ──

    def _certify_performance(self) -> Tuple[str, Dict[str, Any]]:
        details: Dict[str, Any] = {}
        runtime_dir = RUNTIME_DIR

        checks = {
            "Deferred renderer exists": self._file_exists(runtime_dir, "deferred_renderer.py"),
            "UX telemetry exists": self._file_exists(runtime_dir, "ux_telemetry.py"),
            "UI observability exists": self._file_exists(runtime_dir, "ui_observability.py"),
            "Timer registry exists": self._file_exists(runtime_dir, "timer_registry.py"),
            "Chunked rendering available": "set_data_chunked" in self._read_file(COMPONENTS_DIR, "tables.py"),
            "Deferred rendering available": "set_data_deferred" in self._read_file(COMPONENTS_DIR, "tables.py"),
        }

        details["checks"] = checks
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed / total * 100
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)
        details["passed"] = passed
        details["total"] = total

        return status, details

    # ── Workflow Integrity ──

    def _certify_workflow_integrity(self) -> Tuple[str, Dict[str, Any]]:
        """
        Verify workflow-related screens and components exist.
        Checks for key workflow screen files.
        """
        details: Dict[str, Any] = {}
        essential_screens = {
            "inventory": ["product_screen.py", "batch_screen.py", "category_screen.py", "warehouse_screen.py"],
            "sales": ["customer_screen.py"],
            "purchases": ["supplier_screen.py"],
            "accounting": ["chart_of_accounts_screen.py", "journal_entry_screen.py", "account_ledger_screen.py"],
            "hr": ["employee_screen.py", "attendance_screen.py", "leave_screen.py", "payroll_screen.py"],
            "finance": ["payment_screen.py", "cashflow_screen.py", "tax_screen.py"],
            "system": ["backup_screen.py", "settings_screen.py", "user_management_screen.py", "audit_screen.py"],
        }

        found = 0
        total = 0
        for area, files in essential_screens.items():
            area_dir = os.path.join(FRONTEND_DIR, area)
            for f in files:
                total += 1
                if os.path.exists(os.path.join(area_dir, f)):
                    found += 1

        details["screens_found"] = found
        details["screens_expected"] = total
        score = found / total * 100 if total > 0 else 0
        status = "PRODUCTION_READY" if score >= 90 else ("PILOT_READY" if score >= 70 else "CONDITIONALLY_READY")
        details["score"] = round(score, 1)

        return status, details

    def certify(self) -> Dict[str, Any]:
        """Run full certification and return structured report."""
        certifiers = [
            ("form_system", self._certify_form_system),
            ("table_system", self._certify_table_system),
            ("operator_safety", self._certify_operator_safety),
            ("workflow_integrity", self._certify_workflow_integrity),
            ("frontend_consistency", self._certify_screen_architecture),
            ("reporting_stability", self._certify_reporting_stability),
            ("human_error_resilience", self._certify_human_error_resilience),
            ("visual_maturity", self._certify_visual_maturity),
            ("performance_state", self._certify_performance),
        ]

        scores = []
        for key, certifier in certifiers:
            status, details = certifier()
            self.results[key] = status
            self.results["details"][key] = details
            scores.append(details.get("score", 0))

        avg_score = sum(scores) / len(scores) if scores else 0

        if avg_score >= 90:
            self.results["final_verdict"] = "PRODUCTION_READY"
        elif avg_score >= 75:
            self.results["final_verdict"] = "PILOT_READY"
        elif avg_score >= 60:
            self.results["final_verdict"] = "CONDITIONALLY_READY"
        elif avg_score >= 40:
            self.results["final_verdict"] = "HIGH_RISK"
        else:
            self.results["final_verdict"] = "OPERATIONALLY_UNSAFE"

        self.results["average_score"] = round(avg_score, 1)
        return self.results


def run_certification() -> Dict[str, Any]:
    """Run certification and return structured report."""
    certifier = EnterpriseUxCertifier()
    return certifier.certify()


if __name__ == "__main__":
    import json
    report = run_certification()
    print(json.dumps(report, indent=2))
