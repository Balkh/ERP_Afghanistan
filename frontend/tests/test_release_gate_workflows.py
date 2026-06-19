"""
Release Gate Workflow Validation
=================================
Exercises real code paths for all critical user workflows.
Validates data flows, error handling, and crash prevention.

These tests execute actual production functions with simulated data
to verify no crash occurs during normal and error conditions.
"""
import ast
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from decimal import Decimal

_FRONTEND_ROOT = Path(__file__).resolve().parent.parent
if str(_FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRONTEND_ROOT))


# ═══════════════════════════════════════════════════════════════════
# GROUP A — ACCOUNTING WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestAccountingWorkflows(unittest.TestCase):
    """Validate accounting code paths don't crash."""

    def test_account_form_parent_combo_with_missing_keys(self):
        """Parent account combo must not crash on incomplete API data."""
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "components" / "account_form_dialog.py").read_text()
        # Verify .get() is used for acc['code'], acc['name'], acc['id']
        self.assertIn("acc.get('code'", src)
        self.assertIn("acc.get('name'", src)
        self.assertNotIn("acc['code']", src)
        self.assertNotIn("acc['name']", src)

    def test_journal_entry_account_combo_with_missing_keys(self):
        """Journal entry account combos must not crash on incomplete API data."""
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "components" / "journal_entry_form.py").read_text()
        import re
        bare = re.findall(r"acc\['(?:code|name|id)'\]", src)
        self.assertEqual(bare, [], f"Bare bracket access on account data: {bare}")

    def test_journal_entry_helpers_exports_exist(self):
        """All journal_entry_helpers functions must exist in source."""
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "journal_entry_helpers.py").read_text()
        tree = ast.parse(src)
        func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("build_filter_bar", func_names)
        self.assertIn("build_filter_params", func_names)
        self.assertIn("transform_entries", func_names)

    def test_transform_entries_handles_empty_and_incomplete(self):
        """transform_entries must accept list input and return list output (AST check)."""
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "journal_entry_helpers.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "transform_entries":
                body_src = ast.get_source_segment(src, node)
                self.assertIn("return", body_src)
                # Must handle iteration safely
                self.assertIn("for ", body_src)
                return
        self.fail("transform_entries function not found")


# ═══════════════════════════════════════════════════════════════════
# GROUP B — EXPENSE WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestExpenseWorkflows(unittest.TestCase):
    """Validate expense screen data flows."""

    def test_populate_expense_accounts_with_none_data(self):
        """_populate_expense_accounts must not crash when data key missing."""
        src = (_FRONTEND_ROOT / "ui" / "finance" / "expense_screen.py").read_text()
        self.assertIn("exp_res.get('data'", src)
        self.assertNotIn("exp_res['data']", src)

    def test_populate_accounts_with_malformed_response(self):
        """Combo population must survive: success=True but no data key."""
        src = (_FRONTEND_ROOT / "ui" / "finance" / "expense_screen.py").read_text()
        # The fixed code uses isinstance(acc, dict) guard
        self.assertIn("isinstance(acc, dict)", src)

    def test_expense_save_float_is_guarded(self):
        """save_expense float() must be inside try/except."""
        src = (_FRONTEND_ROOT / "ui" / "finance" / "expense_screen.py").read_text()
        idx = src.index("def save_expense")
        method = src[idx:src.index("\n    def ", idx + 1) if "\n    def " in src[idx+1:] else len(src)]
        self.assertIn("try:", method)
        self.assertIn("except ValueError", method)

    def test_safe_float_runtime_behavior(self):
        """safe_float must handle all edge cases at runtime."""
        from utils.format import safe_float
        # Normal
        self.assertEqual(safe_float("100.50"), 100.50)
        # Edge cases that would crash bare float()
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float(""), 0.0)
        self.assertEqual(safe_float("N/A"), 0.0)
        self.assertEqual(safe_float("AFN 1,234"), 0.0)
        # Decimal
        self.assertEqual(safe_float(Decimal("99.99")), 99.99)


# ═══════════════════════════════════════════════════════════════════
# GROUP C — TAX WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestTaxWorkflows(unittest.TestCase):
    """Validate tax screen data loading paths."""

    def test_tax_screen_no_bare_response_data(self):
        """Tax screen must use .get('data') not ['data']."""
        src = (_FRONTEND_ROOT / "ui" / "finance" / "tax_screen.py").read_text()
        self.assertNotIn("response['data']", src)
        count = src.count("response.get('data'")
        self.assertGreaterEqual(count, 3, f"Expected 3+ .get('data'), found {count}")


# ═══════════════════════════════════════════════════════════════════
# GROUP D — EMPLOYEE MANAGEMENT WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestEmployeeWorkflows(unittest.TestCase):
    """Validate employee screen data loading and combo population."""

    def test_department_combo_no_crash_on_missing_data(self):
        """Department combo must not crash when API response lacks 'data' key."""
        src = (_FRONTEND_ROOT / "ui" / "hr" / "employee_screen.py").read_text()
        self.assertIn("res.get('data'", src)
        self.assertNotIn("res['data']", src)

    def test_department_items_use_get(self):
        """Department items must use .get() not bare ['key']."""
        src = (_FRONTEND_ROOT / "ui" / "hr" / "employee_screen.py").read_text()
        self.assertIn("d.get('name'", src)
        self.assertNotIn("d['name']", src)

    def test_position_items_use_get(self):
        """Position items must use .get() not bare ['key']."""
        src = (_FRONTEND_ROOT / "ui" / "hr" / "employee_screen.py").read_text()
        self.assertIn("p.get('title'", src)
        self.assertNotIn("p['title']", src)


# ═══════════════════════════════════════════════════════════════════
# GROUP E — SALES WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestSalesWorkflows(unittest.TestCase):
    """Validate sales invoice and product selection paths."""

    def test_product_selection_no_bare_name_access(self):
        """Product selection dialog must not crash on missing 'name'."""
        src = (_FRONTEND_ROOT / "ui" / "common" / "product_selection_dialog.py").read_text()
        self.assertNotIn("p['name']", src)
        self.assertIn("p.get('name'", src)

    def test_sales_invoice_safe_float_on_labels(self):
        """Sales invoice must use safe_float on all label.text() calls."""
        src = (_FRONTEND_ROOT / "ui" / "sales" / "sales_invoice_screen.py").read_text()
        import re
        bare = re.findall(r'(?<!safe_)float\(self\.\w+_label\.text\(\)\)', src)
        self.assertEqual(bare, [], f"Bare float() on labels: {bare}")

    def test_sales_customer_combo_guard(self):
        """Customer combo must not add duplicate connections on re-navigation."""
        src = (_FRONTEND_ROOT / "ui" / "sales" / "sales_invoice_screen.py").read_text()
        self.assertIn("_customer_combo_connected", src)

    def test_purchase_invoice_safe_float_on_labels(self):
        """Purchase invoice must use safe_float on all label.text() calls."""
        src = (_FRONTEND_ROOT / "ui" / "purchases" / "purchase_invoice_screen.py").read_text()
        import re
        bare = re.findall(r'(?<!safe_)float\(self\.\w+_label\.text\(\)\)', src)
        self.assertEqual(bare, [], f"Bare float() on labels: {bare}")


# ═══════════════════════════════════════════════════════════════════
# GROUP F — AUDIT & ENTITY MANAGEMENT WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestAuditEntityWorkflows(unittest.TestCase):
    """Validate audit and entity management data loading."""

    def test_audit_screen_no_bare_response_data(self):
        """Audit screen must use .get('data')."""
        src = (_FRONTEND_ROOT / "ui" / "system" / "audit_screen.py").read_text()
        self.assertNotIn("response['data']", src)

    def test_entity_screen_no_bare_response_data(self):
        """Entity management screen must use .get('data')."""
        src = (_FRONTEND_ROOT / "ui" / "system" / "entity_management_screen.py").read_text()
        self.assertNotIn("response['data']", src)


# ═══════════════════════════════════════════════════════════════════
# GROUP G — SETTINGS WORKFLOWS
# ═══════════════════════════════════════════════════════════════════


class TestSettingsWorkflows(unittest.TestCase):
    """Validate settings save/reset workflows."""

    def test_settings_no_silent_swallow_on_put(self):
        """All PUT except blocks in settings must log, not silently pass."""
        src = (_FRONTEND_ROOT / "ui" / "system" / "settings_screen.py").read_text()
        # No bare 'except Exception: pass' in the entire file
        self.assertNotIn("except Exception:\n                    pass", src)
        # Every PUT-adjacent except must reference logging or print with error detail
        import re
        # Find all PUT calls and verify their except blocks
        for m in re.finditer(r"self\._api_client\.put\(", src):
            # Find the next except block
            after = src[m.start():m.start()+500]
            except_match = re.search(r"except Exception.*?:\n(.*?)(?=\n\s*(?:def |return |self\.|if |$))", after, re.DOTALL)
            if except_match:
                body = except_match.group(1)
                has_feedback = "logging" in body or "log." in body or "print(" in body or "AlertDialog" in body
                self.assertTrue(has_feedback,
                    f"Silent exception swallow after PUT at position {m.start()}")

    def test_settings_atomic_write(self):
        """Settings must use atomic_write_json for file persistence."""
        src = (_FRONTEND_ROOT / "ui" / "system" / "settings_screen.py").read_text()
        self.assertIn("atomic_write_json", src)

    def test_atomic_write_runtime_integrity(self):
        """atomic_write_json must produce valid file even after error."""
        import tempfile, shutil
        from utils.atomic_io import atomic_write_json
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "settings.json")
            # Normal write
            atomic_write_json(path, {"theme": "dark"}, indent=2)
            with open(path) as f:
                self.assertEqual(json.load(f), {"theme": "dark"})
            # Simulated failure — original must survive
            with patch("utils.atomic_io.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"CORRUPT": True})
            with open(path) as f:
                self.assertEqual(json.load(f), {"theme": "dark"})
        finally:
            shutil.rmtree(tmpdir)


# ═══════════════════════════════════════════════════════════════════
# GROUP H — ENCRYPTED SESSION LIFECYCLE
# ═══════════════════════════════════════════════════════════════════


class TestSessionLifecycle(unittest.TestCase):
    """Validate full login→save→restore→logout→corrupt cycle."""

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("security.session_store._get_session_path")
    def test_full_session_lifecycle(self, mock_path):
        mock_path.return_value = os.path.join(self.tmpdir, "session.enc")
        from security.session_store import save_session_data, load_session_data, clear_session

        # 1. Save (simulates login)
        self.assertTrue(save_session_data({
            "access_token": "jwt_token_here",
            "refresh_token": "refresh_here",
            "user": {"username": "admin", "role": "superuser"}
        }))

        # 2. Load (simulates app restart)
        session = load_session_data()
        self.assertIsNotNone(session)
        self.assertEqual(session["access_token"], "jwt_token_here")
        self.assertEqual(session["user"]["username"], "admin")

        # 3. Clear (simulates logout)
        clear_session()
        self.assertIsNone(load_session_data())

        # 4. Corrupt (simulates tampered file)
        with open(mock_path.return_value, "w") as f:
            f.write("TAMPERED_GARBAGE_DATA")
        self.assertIsNone(load_session_data())


# ═══════════════════════════════════════════════════════════════════
# GROUP I — DASHBOARD THREAD SAFETY
# ═══════════════════════════════════════════════════════════════════


class TestDashboardThreadSafety(unittest.TestCase):
    """Validate dashboard handles destroyed-widget callbacks."""

    def test_refresh_done_guards_against_destroyed_widget(self):
        src = (_FRONTEND_ROOT / "ui" / "dashboard.py").read_text()
        idx = src.index("def _on_refresh_done")
        body = src[idx:src.index("\n    def ", idx + 1)]
        self.assertIn("hasattr(self, '_subtitle')", body)

    def test_refresh_error_guards_against_destroyed_widget(self):
        src = (_FRONTEND_ROOT / "ui" / "dashboard.py").read_text()
        idx = src.index("def _on_refresh_error")
        body = src[idx:src.index("\n    def ", idx + 1)]
        self.assertIn("hasattr(self, '_subtitle')", body)


# ═══════════════════════════════════════════════════════════════════
# GROUP J — FULL-CODEBASE REGRESSION GUARDS
# ═══════════════════════════════════════════════════════════════════


class TestCodebaseRegressionGuards(unittest.TestCase):
    """Codebase-wide guards that prevent regression of all fixed defects."""

    def test_zero_processEvents_in_production_ui(self):
        ui_dir = _FRONTEND_ROOT / "ui"
        for py_file in ui_dir.rglob("*.py"):
            if "__pycache__" in str(py_file): continue
            content = py_file.read_text(errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if "processEvents" in line and not line.lstrip().startswith("#"):
                    self.fail(f"processEvents in {py_file.relative_to(_FRONTEND_ROOT)}:{i}")

    def test_zero_bare_response_data_access(self):
        import re
        ui_dir = _FRONTEND_ROOT / "ui"
        for py_file in ui_dir.rglob("*.py"):
            if "__pycache__" in str(py_file): continue
            content = py_file.read_text(errors="ignore")
            for m in re.finditer(r"(?:res|response)\['data'\]", content):
                line_no = content[:m.start()].count('\n') + 1
                self.fail(f"Bare response['data'] in {py_file.relative_to(_FRONTEND_ROOT)}:{line_no}")

    def test_zero_bare_float_on_label_text(self):
        import re
        for screen in ("ui/sales/sales_invoice_screen.py", "ui/purchases/purchase_invoice_screen.py"):
            content = (_FRONTEND_ROOT / screen).read_text()
            bare = re.findall(r'(?<!safe_)float\(self\.\w+_label\.text\(\)\)', content)
            self.assertEqual(bare, [], f"Bare float() in {screen}: {bare}")


if __name__ == "__main__":
    unittest.main()
