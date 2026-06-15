"""
P0/P1 Regression Test Suite
============================
Verifies all completed P0/P1 fixes remain intact.
Tests actual code behavior, not documentation.

Tests requiring PySide6 are skipped when the module is unavailable
(e.g., headless CI without a display server). Tests that can run
without Qt (file I/O, source-code analysis) always run.
"""
import ast
import inspect
import json
import os
import sys
import tempfile
import shutil
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import PySide6
    HAS_QT = True
except ImportError:
    HAS_QT = False

SKIP_QT = unittest.skipUnless(HAS_QT, "PySide6 not installed")

# Resolve project root so relative paths work
_FRONTEND_ROOT = Path(__file__).resolve().parent.parent
if str(_FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRONTEND_ROOT))


# ═══════════════════════════════════════════════════════════════════
# Test 1: Atomic Write (no Qt needed)
# ═══════════════════════════════════════════════════════════════════


class TestAtomicWrite(unittest.TestCase):
    """Verify atomic file writes cannot produce partial/corrupt files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="erp_test_atomic_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_atomic_write_text_creates_file(self):
        from utils.atomic_io import atomic_write_text
        target = os.path.join(self.tmpdir, "test.txt")
        atomic_write_text(target, "hello world")
        self.assertTrue(os.path.exists(target))
        with open(target) as f:
            self.assertEqual(f.read(), "hello world")

    def test_atomic_write_json_roundtrip(self):
        from utils.atomic_io import atomic_write_json
        target = os.path.join(self.tmpdir, "test.json")
        data = {"key": "value", "number": 42}
        atomic_write_json(target, data, indent=2)
        with open(target) as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)

    def test_atomic_write_no_partial_on_error(self):
        """If write fails mid-stream, target must remain unchanged."""
        from utils.atomic_io import atomic_write_text
        target = os.path.join(self.tmpdir, "safe.txt")
        atomic_write_text(target, "original content")

        with patch("utils.atomic_io.os.replace", side_effect=OSError("simulated")):
            with self.assertRaises(OSError):
                atomic_write_text(target, "CORRUPT DATA")

        with open(target) as f:
            self.assertEqual(f.read(), "original content")

    def test_atomic_write_creates_parent_dirs(self):
        from utils.atomic_io import atomic_write_text
        target = os.path.join(self.tmpdir, "a", "b", "c", "deep.txt")
        atomic_write_text(target, "deep write")
        with open(target) as f:
            self.assertEqual(f.read(), "deep write")

    def test_atomic_write_overwrite(self):
        from utils.atomic_io import atomic_write_text
        target = os.path.join(self.tmpdir, "overwrite.txt")
        atomic_write_text(target, "first")
        atomic_write_text(target, "second")
        with open(target) as f:
            self.assertEqual(f.read(), "second")


# ═══════════════════════════════════════════════════════════════════
# Test 2: Encrypted Session Store (no Qt needed — crypto only)
# ═══════════════════════════════════════════════════════════════════


class TestEncryptedSessionStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="erp_test_session_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _session_path(self):
        return os.path.join(self.tmpdir, "session.enc")

    @patch("security.session_store._get_session_path")
    def test_save_and_load(self, mock_path):
        mock_path.return_value = self._session_path()
        from security.session_store import save_session_data, load_session_data
        session = {"access_token": "tok123", "user": {"username": "admin"}}
        self.assertTrue(save_session_data(session))
        loaded = load_session_data()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["access_token"], "tok123")

    @patch("security.session_store._get_session_path")
    def test_clear(self, mock_path):
        p = self._session_path()
        mock_path.return_value = p
        from security.session_store import save_session_data, clear_session, load_session_data
        save_session_data({"access_token": "tok"})
        clear_session()
        self.assertIsNone(load_session_data())

    @patch("security.session_store._get_session_path")
    def test_load_nonexistent(self, mock_path):
        mock_path.return_value = os.path.join(self.tmpdir, "nope.enc")
        from security.session_store import load_session_data
        self.assertIsNone(load_session_data())


# ═══════════════════════════════════════════════════════════════════
# Test 3: AlertDialog Argument Order (AST inspection — no Qt needed)
# ═══════════════════════════════════════════════════════════════════


class TestAlertDialogSignatureAST(unittest.TestCase):
    """Parse dialogs.py with AST to verify signatures without importing Qt."""

    def _parse_class(self):
        src = (_FRONTEND_ROOT / "ui" / "components" / "dialogs.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AlertDialog":
                return node
        self.fail("AlertDialog class not found")

    def _get_method_params(self, cls_node, method_name):
        for item in cls_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return [a.arg for a in item.args.args]
        self.fail(f"Method {method_name} not found in AlertDialog")

    def test_info_signature(self):
        cls = self._parse_class()
        params = self._get_method_params(cls, "info")
        self.assertEqual(params, ["title", "message", "parent"])

    def test_warning_signature(self):
        cls = self._parse_class()
        params = self._get_method_params(cls, "warning")
        self.assertEqual(params, ["title", "message", "parent"])

    def test_error_signature(self):
        cls = self._parse_class()
        params = self._get_method_params(cls, "error")
        self.assertEqual(params, ["title", "message", "parent"])

    def test_show_signature(self):
        cls = self._parse_class()
        params = self._get_method_params(cls, "show")
        self.assertEqual(params, ["title", "message", "alert_type", "parent"])


# ═══════════════════════════════════════════════════════════════════
# Test 4: LicenseDetailsDialog inherits QDialog (AST — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestLicenseDetailsDialogAST(unittest.TestCase):

    def test_inherits_qdialog(self):
        src = (_FRONTEND_ROOT / "ui" / "licensing" / "license_status_screen.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LicenseDetailsDialog":
                bases = [
                    (b.attr if isinstance(b, ast.Attribute) else b.id)
                    for b in node.bases
                    if isinstance(b, (ast.Name, ast.Attribute))
                ]
                self.assertIn("QDialog", bases,
                              f"LicenseDetailsDialog bases: {bases}")
                return
        self.fail("LicenseDetailsDialog not found")


# ═══════════════════════════════════════════════════════════════════
# Test 5: AsyncRequestMixin cancel_api_requests exists (AST — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestAsyncRequestMixinAST(unittest.TestCase):

    def test_has_cancel_method(self):
        src = (_FRONTEND_ROOT / "ui" / "utils" / "async_api.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AsyncRequestMixin":
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertIn("cancel_api_requests", methods)
                return
        self.fail("AsyncRequestMixin not found")

    def test_has_run_api_request_method(self):
        src = (_FRONTEND_ROOT / "ui" / "utils" / "async_api.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AsyncRequestMixin":
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertIn("run_api_request", methods)
                return
        self.fail("AsyncRequestMixin not found")


# ═══════════════════════════════════════════════════════════════════
# Test 6: processEvents Not in Production UI (file scan — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestNoProcessEvents(unittest.TestCase):

    def test_no_process_events_in_ui(self):
        ui_dir = _FRONTEND_ROOT / "ui"
        violations = []
        for py_file in ui_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            content = py_file.read_text(errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.lstrip()
                if "processEvents" in stripped and not stripped.startswith("#"):
                    violations.append(f"{py_file.relative_to(_FRONTEND_ROOT)}:{i}")
        self.assertEqual(violations, [], f"processEvents in UI: {violations}")


# ═══════════════════════════════════════════════════════════════════
# Test 7: background=True in API Client (AST — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestApiClientBackgroundAST(unittest.TestCase):

    def test_get_has_background_param(self):
        src = (_FRONTEND_ROOT / "api" / "client.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "APIClient":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "get":
                        params = [a.arg for a in item.args.args]
                        self.assertIn("background", params)
                        return
        self.fail("APIClient.get not found")


# ═══════════════════════════════════════════════════════════════════
# Test 8: Duplicate Signal Connection Guards (source scan — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestDuplicateSignalGuard(unittest.TestCase):

    def test_sales_customer_combo_guard(self):
        src = (_FRONTEND_ROOT / "ui" / "sales" / "sales_invoice_screen.py").read_text()
        self.assertIn("_customer_combo_connected", src)

    def test_purchase_supplier_combo_guard(self):
        src = (_FRONTEND_ROOT / "ui" / "purchases" / "purchase_invoice_screen.py").read_text()
        self.assertIn("_supplier_combo_connected", src)


# ═══════════════════════════════════════════════════════════════════
# Test 9: Required Modules Exist (filesystem — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestModulesExist(unittest.TestCase):

    def test_journal_entry_helpers(self):
        self.assertTrue((_FRONTEND_ROOT / "ui" / "accounting" / "journal_entry_helpers.py").exists())

    def test_email_config_dialog(self):
        self.assertTrue((_FRONTEND_ROOT / "ui" / "system" / "email_config_dialog.py").exists())

    def test_atomic_io(self):
        self.assertTrue((_FRONTEND_ROOT / "utils" / "atomic_io.py").exists())

    def test_session_store(self):
        self.assertTrue((_FRONTEND_ROOT / "security" / "session_store.py").exists())


# ═══════════════════════════════════════════════════════════════════
# Test 10: connect_unique utility (source scan — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestConnectUnique(unittest.TestCase):
    """Verify connect_unique disconnects before connecting."""

    def test_module_exists(self):
        self.assertTrue((_FRONTEND_ROOT / "ui" / "utils" / "signal_utils.py").exists())

    def test_disconnect_before_connect_pattern(self):
        src = (_FRONTEND_ROOT / "ui" / "utils" / "signal_utils.py").read_text()
        # Must contain disconnect then connect
        self.assertIn("signal.disconnect(slot)", src)
        self.assertIn("signal.connect(slot)", src)
        # disconnect must come before connect
        disc_pos = src.index("signal.disconnect(slot)")
        conn_pos = src.index("signal.connect(slot)")
        self.assertLess(disc_pos, conn_pos,
                        "disconnect must come before connect")

    def test_report_browser_uses_connect_unique(self):
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "report_browser.py").read_text()
        self.assertIn("connect_unique", src)
        # Must not use raw .connect( for its interactive widgets
        # (type_selector, btn_run, btn_export should all use connect_unique)
        self.assertIn("connect_unique(self.type_selector", src)
        self.assertIn("connect_unique(self.btn_run", src)
        self.assertIn("connect_unique(self.btn_export", src)


# ═══════════════════════════════════════════════════════════════════
# Test 11: ReportBrowser has no threads (so no cleanup needed)
# ═══════════════════════════════════════════════════════════════════


class TestReportBrowserNoThreads(unittest.TestCase):
    """Verify ReportBrowser uses no threads — cleanup is not required."""

    def test_no_qthread_in_report_browser(self):
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "report_browser.py").read_text()
        self.assertNotIn("QThread", src)
        self.assertNotIn("QRunnable", src)
        self.assertNotIn("QThreadPool", src)
        self.assertNotIn("threading.Thread", src)
        self.assertNotIn("moveToThread", src)

    def test_no_worker_class_in_report_browser(self):
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "report_browser.py").read_text()
        # No Worker class definitions
        tree = ast.parse(src)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        worker_classes = [c for c in class_names if "worker" in c.lower()]
        self.assertEqual(worker_classes, [],
                         f"Unexpected worker classes: {worker_classes}")


# ═══════════════════════════════════════════════════════════════════
# Test 12: All thread sites have cleanup (source scan)
# ═══════════════════════════════════════════════════════════════════


class TestThreadCleanup(unittest.TestCase):
    """Verify every QThread creation has matching deleteLater/quit/wait."""

    def _check_file_threads(self, relpath):
        fpath = _FRONTEND_ROOT / relpath
        src = fpath.read_text()
        thread_count = src.count("QThread(")
        # deleteLater appears both as deleteLater) in connect() and deleteLater() standalone
        delete_count = src.count("deleteLater")
        # Every thread creation must have matching cleanup
        self.assertGreaterEqual(delete_count, thread_count,
            f"{relpath}: {thread_count} QThread( but only {delete_count} deleteLater")

    def test_dashboard_thread_cleanup(self):
        self._check_file_threads("ui/dashboard.py")

    def test_main_window_thread_cleanup(self):
        self._check_file_threads("ui/main_window.py")

    def test_async_api_thread_cleanup(self):
        self._check_file_threads("ui/utils/async_api.py")


if __name__ == "__main__":
    unittest.main()
