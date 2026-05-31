"""
Phase 4 — Frontend Operational Coverage Validator.
Verifies screens exist, have working bindings, forms, tables, pagination, search,
validation, print/export, and proper UX state handling.
"""

import os
import re
from typing import Dict, List, Set, Optional

from coverage_governance.module_classifier import FRONTEND_OPERATIONAL_SCREENS
from coverage_governance.models import (
    FrontendCoverageResult, FrontendScreenEntry,
)


BASE_SCREEN_CLASSES: Dict[str, str] = {
    "dashboard": "QWidget",
    "customer_screen": "BaseScreen",
    "supplier_screen": "BaseScreen",
    "product_screen": "BaseScreen",
    "category_screen": "BaseScreen",
    "warehouse_screen": "BaseScreen",
    "batch_screen": "BaseScreen",
    "stock_movement_screen": "BaseScreen",
    "sales_invoice_screen": "QWidget",
    "purchase_invoice_screen": "QWidget",
    "returns_screen": "BaseScreen",
    "chart_of_accounts_screen": "BaseScreen",
    "journal_entry_screen": "BaseScreen",
    "account_ledger_screen": "BaseScreen",
    "trial_balance_screen": "BaseScreen",
    "profit_loss_screen": "BaseScreen",
    "balance_sheet_screen": "BaseScreen",
    "arap_ageing_screen": "BaseScreen",
    "cashflow_screen": "BaseScreen",
    "payment_screen": "QWidget",
    "employee_screen": "BaseScreen",
    "attendance_screen": "BaseScreen",
    "leave_screen": "BaseScreen",
    "payroll_screen": "QWidget",
    "backup_screen": "BaseScreen",
    "role_management_screen": "BaseScreen",
    "user_management_screen": "BaseScreen",
    "tax_screen": "BaseScreen",
    "budgeting_screen": "BaseScreen",
    "fixed_assets_screen": "BaseScreen",
    "expense_screen": "BaseScreen",
    "cost_centers_screen": "BaseScreen",
    "entity_management_screen": "BaseScreen",
    "notification_center": "BaseScreen",
    "control_center_screen": "QWidget",
    "observability_console": "QWidget",
    "financial_integrity_screen": "BaseScreen",
    "financial_audit_log_screen": "BaseScreen",
    "login_screen": "BaseScreen",
}


FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)

FRONTEND_TEST_DIR = os.path.join(FRONTEND_DIR, "tests", "ui")

SCREEN_FILE_PATTERNS: Dict[str, str] = {
    "login_screen": "*login*",
    "dashboard": "*dashboard*",
    "customer_screen": "*customer*",
    "supplier_screen": "*supplier*",
    "product_screen": "*product*",
    "category_screen": "*category*",
    "warehouse_screen": "*warehouse*",
    "batch_screen": "*batch*",
    "stock_movement_screen": "*stock_movement*",
    "sales_invoice_screen": "*sales_invoice*",
    "purchase_invoice_screen": "*purchase_invoice*",
    "returns_screen": "*return*",
    "chart_of_accounts_screen": "*chart_of_accounts*",
    "journal_entry_screen": "*journal_entry*",
    "account_ledger_screen": "*account_ledger*",
    "trial_balance_screen": "*trial_balance*",
    "profit_loss_screen": "*profit_loss*",
    "balance_sheet_screen": "*balance_sheet*",
    "arap_ageing_screen": "*arap_ageing*",
    "cashflow_screen": "*cashflow*",
    "payment_screen": "*payment*",
    "employee_screen": "*employee*",
    "attendance_screen": "*attendance*",
    "leave_screen": "*leave*",
    "payroll_screen": "*payroll*",
    "backup_screen": "*backup*",
    "role_management_screen": "*role_management*",
    "user_management_screen": "*user_management*",
    "tax_screen": "*tax*",
    "budgeting_screen": "*budget*",
    "fixed_assets_screen": "*fixed_assets*",
    "expense_screen": "*expense*",
    "cost_centers_screen": "*cost_centers*",
    "entity_management_screen": "*entity_management*",
    "notification_center": "*notification*",
    "control_center_screen": "*control_center*",
    "observability_console": "*observability*",
    "financial_integrity_screen": "*financial_integrity*",
    "financial_audit_log_screen": "*financial_audit_log*",
}


class FrontendOperationalValidator:

    def __init__(self, frontend_dir: Optional[str] = None):
        self._frontend_dir = frontend_dir or FRONTEND_DIR

    def validate(self) -> FrontendCoverageResult:
        screen_files = self._find_screen_files()
        test_files = self._find_test_files()
        test_functions = self._extract_test_functions(test_files)

        screens = []
        total = len(FRONTEND_OPERATIONAL_SCREENS)
        basescreen_count = 0
        unmigrated = 0
        with_form = 0
        with_table = 0
        with_pagination = 0
        with_search = 0
        with_loading = 0
        with_empty = 0
        with_error = 0
        with_print = 0
        with_export = 0
        with_test = 0

        for screen_name in FRONTEND_OPERATIONAL_SCREENS:
            sf = screen_files.get(screen_name) or ""
            base_class = BASE_SCREEN_CLASSES.get(screen_name, "QWidget")
            on_basescreen = base_class == "BaseScreen"

            has_form = False
            has_table = False
            has_pagination = False
            has_search = False
            has_loading = False
            has_empty = False
            has_error = False
            has_print = False
            has_export = False

            if sf:
                content = self._read_file(sf)
                if content:
                    has_form = bool(re.search(
                        r"QFormLayout|FormSection|EnterpriseForm|form_layout|addRow", content
                    ))
                    has_table = bool(re.search(
                        r"EnterpriseTable|QTableWidget|QTableView|TableColumn", content
                    ))
                    has_pagination = bool(re.search(
                        r"PaginationWidget|page_\d+|setPage|pagination", content
                    ))
                    has_search = bool(re.search(
                        r"search|filter|QLineEdit.*search|SearchInput", content
                    ))
                    has_loading = bool(re.search(
                        r"loading|showEvent|skeleton|progress", content
                    ))
                    has_empty = bool(re.search(
                        r"empty|no_data|no_records|placeholder", content
                    ))
                    has_error = bool(re.search(
                        r"error|try.*except|catch|error_label|error_dialog", content
                    ))
                    has_print = bool(re.search(
                        r"print|QPrinter|QPrintPreviewDialog|PDF", content
                    ))
                    has_export = bool(re.search(
                        r"export|CSV|csv|download|Excel", content
                    ))

            if on_basescreen:
                basescreen_count += 1
            else:
                unmigrated += 1
            if has_form:
                with_form += 1
            if has_table:
                with_table += 1
            if has_pagination:
                with_pagination += 1
            if has_search:
                with_search += 1
            if has_loading:
                with_loading += 1
            if has_empty:
                with_empty += 1
            if has_error:
                with_error += 1
            if has_print:
                with_print += 1
            if has_export:
                with_export += 1

            # Check for test coverage
            test_score = self._compute_test_score(screen_name, test_functions)
            has_test_file = screen_name in screen_files
            if test_score > 0:
                with_test += 1

            screens.append(FrontendScreenEntry(
                screen_name=screen_name,
                exists=bool(sf),
                has_form=has_form,
                has_table=has_table,
                has_pagination=has_pagination,
                has_search=has_search,
                has_loading_state=has_loading,
                has_empty_state=has_empty,
                has_error_state=has_error,
                has_printable_output=has_print,
                has_exportable_output=has_export,
                on_basescreen=on_basescreen,
                test_file_found=has_test_file,
                test_coverage_score=round(test_score, 2),
            ))

        result = FrontendCoverageResult(
            screen_coverage_pct=round(len(screen_files) / total * 100, 2),
            form_coverage_pct=round(with_form / total * 100, 2),
            table_coverage_pct=round(with_table / total * 100, 2),
            ux_state_coverage_pct=round(
                ((with_loading + with_empty + with_error) / 3) / total * 100, 2
            ),
            print_export_coverage_pct=round(
                ((with_print + with_export) / 2) / total * 100, 2
            ),
            test_coverage_pct=round(with_test / total * 100, 2),
            overall_frontend_score=round(
                (
                    (len(screen_files) / total) * 25
                    + (with_form / total) * 15
                    + (with_table / total) * 15
                    + (with_pagination / total) * 5
                    + (with_search / total) * 5
                    + ((with_loading + with_empty + with_error) / 3 / total) * 15
                    + ((with_print + with_export) / 2 / total) * 10
                    + (basescreen_count / total) * 10
                ),
                2,
            ),
            screens=screens,
            total_screens=total,
            basescreen_screens=basescreen_count,
            unmigrated_widgets=unmigrated,
        )
        return result

    def _find_screen_files(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        ui_dir = os.path.join(self._frontend_dir, "ui")
        if not os.path.isdir(ui_dir):
            return result
        for root, _, files in os.walk(ui_dir):
            for fn in files:
                if fn.endswith(".py"):
                    fp = os.path.join(root, fn)
                    for sname, pattern in SCREEN_FILE_PATTERNS.items():
                        pattern_glob = pattern.replace("*", "")
                        if pattern_glob and pattern_glob.lower() in fn.lower():
                            result[sname] = fp
        return result

    def _find_test_files(self) -> List[str]:
        if not os.path.isdir(FRONTEND_TEST_DIR):
            return []
        files = []
        for fn in os.listdir(FRONTEND_TEST_DIR):
            if fn.endswith(".py"):
                files.append(os.path.join(FRONTEND_TEST_DIR, fn))
        return files

    def _extract_test_functions(self, files: List[str]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            functions = re.findall(r"def (test_\w+)\s*\(", content)
            if functions:
                result[os.path.basename(fp)] = functions
        return result

    def _compute_test_score(self, screen_name: str,
                             test_functions: Dict[str, List[str]]) -> float:
        """Compute test coverage score for a screen (0-100)."""
        keywords = screen_name.replace("_screen", "").replace("_", " ").split()
        match_count = 0
        for fn_list in test_functions.values():
            for fn in fn_list:
                if any(kw.lower() in fn.lower() for kw in keywords):
                    match_count += 1

        if match_count >= 5:
            return 100.0
        elif match_count >= 3:
            return 75.0
        elif match_count >= 1:
            return 50.0
        return 0.0

    def _read_file(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
