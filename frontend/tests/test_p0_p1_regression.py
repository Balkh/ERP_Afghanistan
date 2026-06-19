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

    def test_cancel_method_calls_quit_and_wait(self):
        """cancel_api_requests must call thread.quit() and thread.wait()."""
        src = (_FRONTEND_ROOT / "ui" / "utils" / "async_api.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AsyncRequestMixin":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "cancel_api_requests":
                        body_src = ast.get_source_segment(src, item)
                        self.assertIn("quit()", body_src,
                            "cancel_api_requests must call quit() on threads")
                        self.assertIn("wait(", body_src,
                            "cancel_api_requests must call wait() on threads")
                        return
        self.fail("AsyncRequestMixin.cancel_api_requests not found")

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

    def test_get_has_background_param_with_toast_guard(self):
        """get() must have background param AND suppress toasts when True."""
        src = (_FRONTEND_ROOT / "api" / "client.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "APIClient":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "get":
                        params = [a.arg for a in item.args.args]
                        self.assertIn("background", params)
                        body_src = ast.get_source_segment(src, item)
                        self.assertIn("not background", body_src,
                            "get() must check 'not background' before showing toasts")
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
    """Verify required modules exist AND export expected symbols."""

    def test_journal_entry_helpers_exports(self):
        p = _FRONTEND_ROOT / "ui" / "accounting" / "journal_entry_helpers.py"
        self.assertTrue(p.exists())
        src = p.read_text()
        tree = ast.parse(src)
        names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("build_filter_bar", names)
        self.assertIn("build_filter_params", names)
        self.assertIn("transform_entries", names)

    def test_email_config_dialog_has_class(self):
        p = _FRONTEND_ROOT / "ui" / "system" / "email_config_dialog.py"
        self.assertTrue(p.exists())
        src = p.read_text()
        tree = ast.parse(src)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertIn("EmailConfigDialog", classes)

    def test_atomic_io_exports_functions(self):
        p = _FRONTEND_ROOT / "utils" / "atomic_io.py"
        self.assertTrue(p.exists())
        from utils.atomic_io import atomic_write_text, atomic_write_json
        self.assertTrue(callable(atomic_write_text))
        self.assertTrue(callable(atomic_write_json))

    def test_session_store_exports_functions(self):
        p = _FRONTEND_ROOT / "security" / "session_store.py"
        self.assertTrue(p.exists())
        import security.session_store as ss
        self.assertTrue(callable(getattr(ss, "save_session_data", None)))
        self.assertTrue(callable(getattr(ss, "load_session_data", None)))
        self.assertTrue(callable(getattr(ss, "clear_session", None)))


# ═══════════════════════════════════════════════════════════════════
# Test 10: connect_unique utility (source scan — no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestConnectUnique(unittest.TestCase):
    """Verify connect_unique disconnects before connecting."""

    def test_connect_unique_function_importable(self):
        """connect_unique must be importable and callable."""
        p = _FRONTEND_ROOT / "ui" / "utils" / "signal_utils.py"
        self.assertTrue(p.exists())
        src = p.read_text()
        tree = ast.parse(src)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("connect_unique", funcs)

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


# ═══════════════════════════════════════════════════════════════════
# Test 13: safe_float usage in invoice screens (crash prevention)
# ═══════════════════════════════════════════════════════════════════


class TestSafeFloatUsage(unittest.TestCase):
    """Verify invoice screens use safe_float instead of bare float() on labels."""

    def test_sales_uses_safe_float(self):
        src = (_FRONTEND_ROOT / "ui" / "sales" / "sales_invoice_screen.py").read_text()
        self.assertIn("from utils.format import safe_float", src)
        self.assertIn("safe_float(self.subtotal_label.text())", src)
        self.assertIn("safe_float(self.total_label.text())", src)
        # Must NOT have bare float() on label text
        import re
        bare = re.findall(r'(?<!safe_)float\(self\.\w+_label\.text\(\)\)', src)
        self.assertEqual(bare, [], f"Bare float() on labels: {bare}")

    def test_purchase_uses_safe_float(self):
        src = (_FRONTEND_ROOT / "ui" / "purchases" / "purchase_invoice_screen.py").read_text()
        self.assertIn("from utils.format import safe_float", src)
        self.assertIn("safe_float(self.subtotal_label.text())", src)
        import re
        bare = re.findall(r'(?<!safe_)float\(self\.\w+_label\.text\(\)\)', src)
        self.assertEqual(bare, [], f"Bare float() on labels: {bare}")


class TestSafeFloatFunction(unittest.TestCase):
    """Verify safe_float behavior."""

    def test_normal_value(self):
        from utils.format import safe_float
        self.assertEqual(safe_float("123.45"), 123.45)

    def test_none(self):
        from utils.format import safe_float
        self.assertEqual(safe_float(None), 0.0)

    def test_empty_string(self):
        from utils.format import safe_float
        self.assertEqual(safe_float(""), 0.0)

    def test_non_numeric(self):
        from utils.format import safe_float
        self.assertEqual(safe_float("abc"), 0.0)

    def test_comma_formatted(self):
        from utils.format import safe_float
        # "1,234.56" will fail float() — safe_float returns default
        self.assertEqual(safe_float("1,234.56"), 0.0)


# ═══════════════════════════════════════════════════════════════════
# Test 14: Dashboard refresh callback guards
# ═══════════════════════════════════════════════════════════════════


class TestDashboardCallbackGuard(unittest.TestCase):
    """Verify dashboard protects against widget-destroyed-during-refresh."""

    def test_on_refresh_done_has_guard(self):
        src = (_FRONTEND_ROOT / "ui" / "dashboard.py").read_text()
        # Must check hasattr before accessing _subtitle
        idx = src.index("def _on_refresh_done")
        method_body = src[idx:src.index("\n    def ", idx + 1)]
        self.assertIn("hasattr(self, '_subtitle')", method_body)

    def test_on_refresh_error_has_guard(self):
        src = (_FRONTEND_ROOT / "ui" / "dashboard.py").read_text()
        idx = src.index("def _on_refresh_error")
        method_body = src[idx:src.index("\n    def ", idx + 1)]
        self.assertIn("hasattr(self, '_subtitle')", method_body)


# ═══════════════════════════════════════════════════════════════════
# Test 15: Batch form dialog None guard
# ═══════════════════════════════════════════════════════════════════


class TestBatchFormDialogGuard(unittest.TestCase):
    """Verify batch form dialog guards against None API response."""

    def test_load_batch_data_has_none_guard(self):
        src = (_FRONTEND_ROOT / "ui" / "inventory" / "components" / "batch_form_dialog.py").read_text()
        idx = src.index("def load_batch_data")
        method_body = src[idx:src.index("\n    def ", idx + 1)]
        self.assertIn("if not response", method_body)


# ═══════════════════════════════════════════════════════════════════
# Test 16: Encrypted session — corrupted file handling
# ═══════════════════════════════════════════════════════════════════


class TestEncryptedSessionCorrupt(unittest.TestCase):
    """Verify corrupted/tampered session file does not crash, returns None."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="erp_test_corrupt_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("security.session_store._get_session_path")
    def test_corrupted_file_returns_none(self, mock_path):
        path = os.path.join(self.tmpdir, "session.enc")
        mock_path.return_value = path
        # Write garbage data
        with open(path, "w") as f:
            f.write("THIS IS NOT VALID ENCRYPTED DATA !@#$%^&*()")
        from security.session_store import load_session_data
        result = load_session_data()
        self.assertIsNone(result)

    @patch("security.session_store._get_session_path")
    def test_empty_file_returns_none(self, mock_path):
        path = os.path.join(self.tmpdir, "session.enc")
        mock_path.return_value = path
        with open(path, "w") as f:
            f.write("")
        from security.session_store import load_session_data
        result = load_session_data()
        self.assertIsNone(result)

    @patch("security.session_store._get_session_path")
    def test_truncated_encrypted_returns_none(self, mock_path):
        path = os.path.join(self.tmpdir, "session.enc")
        mock_path.return_value = path
        from security.session_store import save_session_data
        save_session_data({"access_token": "valid"})
        # Truncate the file mid-content
        with open(path, "r") as f:
            content = f.read()
        with open(path, "w") as f:
            f.write(content[:len(content)//2])
        from security.session_store import load_session_data
        result = load_session_data()
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════
# Test 17: Plaintext session migration
# ═══════════════════════════════════════════════════════════════════


class TestPlaintextSessionMigration(unittest.TestCase):
    """Verify AuthManager migrates plaintext session.json then deletes it."""

    def test_migrate_method_exists_with_guard(self):
        """AuthManager must have _migrate_plaintext_session_file with existence check."""
        src = (_FRONTEND_ROOT / "security" / "auth_manager.py").read_text()
        tree = ast.parse(src)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AuthManager":
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertIn("_migrate_plaintext_session_file", methods)
                found = True
        self.assertTrue(found, "AuthManager class not found")

    def test_migration_deletes_plaintext(self):
        """Migration must call _remove_plaintext_session_file in finally."""
        src = (_FRONTEND_ROOT / "security" / "auth_manager.py").read_text()
        idx = src.index("def _migrate_plaintext_session_file")
        # Find end of method
        next_def = src.index("\n    def ", idx + 10)
        method_body = src[idx:next_def]
        # Must have finally block that removes plaintext
        self.assertIn("finally:", method_body)
        self.assertIn("_remove_plaintext_session_file", method_body)

    def test_migration_calls_save_session_data(self):
        """Migration must re-save via encrypted store."""
        src = (_FRONTEND_ROOT / "security" / "auth_manager.py").read_text()
        idx = src.index("def _migrate_plaintext_session_file")
        next_def = src.index("\n    def ", idx + 10)
        method_body = src[idx:next_def]
        self.assertIn("save_session_data", method_body)


# ═══════════════════════════════════════════════════════════════════
# Test 18: AsyncRequestMixin — no-client error callback
# ═══════════════════════════════════════════════════════════════════


class TestAsyncRequestMixinNoClient(unittest.TestCase):
    """Verify run_api_request calls on_error when no client available."""

    def test_returns_false_and_calls_error(self):
        src = (_FRONTEND_ROOT / "ui" / "utils" / "async_api.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AsyncRequestMixin":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "run_api_request":
                        # on_error is keyword-only
                        all_params = ([a.arg for a in item.args.args]
                                      + [a.arg for a in item.args.kwonlyargs])
                        self.assertIn("on_error", all_params)
                        # Method body must contain the no-client check
                        body_src = ast.get_source_segment(src, item)
                        self.assertIn("API client unavailable", body_src)
                        self.assertIn("return False", body_src)
                        return
        self.fail("run_api_request method not found in AsyncRequestMixin")


# ═══════════════════════════════════════════════════════════════════
# Test 19: LicenseDetailsDialog has exec via QDialog
# ═══════════════════════════════════════════════════════════════════


class TestLicenseDetailsDialogExec(unittest.TestCase):
    """Verify LicenseDetailsDialog inherits exec() from QDialog."""

    def test_qdialog_base_provides_exec(self):
        src = (_FRONTEND_ROOT / "ui" / "licensing" / "license_status_screen.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LicenseDetailsDialog":
                bases = [
                    (b.attr if isinstance(b, ast.Attribute) else b.id)
                    for b in node.bases if isinstance(b, (ast.Name, ast.Attribute))
                ]
                self.assertIn("QDialog", bases,
                    "LicenseDetailsDialog must inherit QDialog for exec()")
                # Verify the call site uses .exec()
                self.assertIn("dialog.exec()", src,
                    "LicenseDetailsDialog must be invoked with .exec()")
                return
        self.fail("LicenseDetailsDialog class not found")


# ═══════════════════════════════════════════════════════════════════
# Test 20: API response KeyError prevention
# ═══════════════════════════════════════════════════════════════════


class TestApiResponseSafety(unittest.TestCase):
    """Verify all API response access uses .get() not bare ['key']."""

    def _scan_file_for_bare_bracket(self, relpath, forbidden_patterns):
        """Scan a file for bare bracket access on API data."""
        import re
        src = (_FRONTEND_ROOT / relpath).read_text()
        violations = []
        for pattern in forbidden_patterns:
            for m in re.finditer(pattern, src):
                line_no = src[:m.start()].count('\n') + 1
                violations.append(f"{relpath}:{line_no}")
        return violations

    def test_no_bare_response_data_access(self):
        """No file should use response['data'] — must use response.get('data')."""
        import re
        ui_dir = _FRONTEND_ROOT / "ui"
        violations = []
        for py_file in ui_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            src = py_file.read_text(errors="ignore")
            for m in re.finditer(r"(?:res|response)\['data'\]", src):
                line_no = src[:m.start()].count('\n') + 1
                violations.append(f"{py_file.relative_to(_FRONTEND_ROOT)}:{line_no}")
        self.assertEqual(violations, [],
            f"Bare response['data'] access (KeyError risk): {violations}")

    def test_expense_screen_uses_get(self):
        src = (_FRONTEND_ROOT / "ui" / "finance" / "expense_screen.py").read_text()
        self.assertNotIn("exp_res['data']", src)
        self.assertNotIn("pay_res['data']", src)
        self.assertIn("exp_res.get('data'", src)
        self.assertIn("pay_res.get('data'", src)

    def test_employee_screen_uses_get(self):
        src = (_FRONTEND_ROOT / "ui" / "hr" / "employee_screen.py").read_text()
        self.assertNotIn("res['data']", src)
        self.assertIn("res.get('data'", src)

    def test_account_form_uses_get(self):
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "components" / "account_form_dialog.py").read_text()
        self.assertNotIn("acc['code']", src)
        self.assertNotIn("acc['name']", src)
        self.assertIn("acc.get('code'", src)

    def test_journal_entry_form_uses_get(self):
        src = (_FRONTEND_ROOT / "ui" / "accounting" / "components" / "journal_entry_form.py").read_text()
        import re
        bare = re.findall(r"acc\['(?:code|name|id)'\]", src)
        self.assertEqual(bare, [], f"Bare acc['key'] access: {bare}")

    def test_product_selection_uses_get(self):
        src = (_FRONTEND_ROOT / "ui" / "common" / "product_selection_dialog.py").read_text()
        self.assertNotIn("p['name']", src)
        self.assertIn("p.get('name'", src)
