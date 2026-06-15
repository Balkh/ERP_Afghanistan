"""
Runtime Smoke Tests
====================
Instantiate real widgets, fire real signals, verify no crash.
Requires PySide6. Uses QApplication in offscreen mode.
"""
import os
import sys
import json
import unittest
import tempfile
import shutil

os.environ["QT_QPA_PLATFORM"] = "offscreen"

_FRONTEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FRONTEND_ROOT not in sys.path:
    sys.path.insert(0, _FRONTEND_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Single QApplication for the entire module
_app = QApplication.instance() or QApplication(sys.argv)


def _mock_api():
    """Return a mock API client that returns safe empty responses."""
    from unittest.mock import MagicMock
    client = MagicMock()
    client.get.return_value = {"success": True, "data": {"results": []}}
    client.post.return_value = {"success": True, "data": {}}
    client.put.return_value = {"success": True, "data": {}}
    client.delete.return_value = {"success": True}
    client._auth_token = "test_token"
    client._refresh_token = "test_refresh"
    client.base_url = "http://localhost:8000"
    return client


# ═══════════════════════════════════════════════════════════════
# SMOKE 1: Dashboard instantiation + refresh cycle
# ═══════════════════════════════════════════════════════════════

class TestDashboardSmoke(unittest.TestCase):

    def test_dashboard_creates_without_crash(self):
        from ui.dashboard import Dashboard
        d = Dashboard(api_client=_mock_api())
        self.assertIsNotNone(d)
        d.cleanup()
        d.deleteLater()
        _app.processEvents()

    def test_dashboard_refresh_with_no_api(self):
        from ui.dashboard import Dashboard
        d = Dashboard(api_client=None)
        d.refresh_data()  # Must not crash with None client
        d.cleanup()
        d.deleteLater()
        _app.processEvents()

    def test_dashboard_callback_after_cleanup(self):
        """Simulate thread callback arriving after widget cleanup."""
        from ui.dashboard import Dashboard
        d = Dashboard(api_client=_mock_api())
        d.cleanup()
        # Simulate callback on cleaned-up widget
        d._on_refresh_done({}, {})  # Must not crash
        d._on_refresh_error("test error")  # Must not crash
        d.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 2: Sidebar instantiation + navigation
# ═══════════════════════════════════════════════════════════════

class TestSidebarSmoke(unittest.TestCase):

    def test_sidebar_creates_without_crash(self):
        from ui.sidebar import Sidebar
        s = Sidebar()
        self.assertIsNotNone(s)
        self.assertGreater(len(s._navigation_items), 0)
        s.cleanup()
        s.deleteLater()
        _app.processEvents()

    def test_sidebar_set_active_item(self):
        from ui.sidebar import Sidebar
        s = Sidebar()
        s.set_active_item(0, emit_signal=False)
        s.cleanup()
        s.deleteLater()
        _app.processEvents()

    def test_sidebar_theme_update(self):
        from ui.sidebar import Sidebar
        s = Sidebar()
        s.update_theme("dark")
        s.update_theme("light")
        s.cleanup()
        s.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 3: AlertDialog instantiation
# ═══════════════════════════════════════════════════════════════

class TestAlertDialogSmoke(unittest.TestCase):

    def test_alert_dialog_creates(self):
        from ui.components.dialogs import AlertDialog
        d = AlertDialog("Test", "Message", "info")
        self.assertIsNotNone(d)
        d.deleteLater()
        _app.processEvents()

    def test_confirm_dialog_creates(self):
        from ui.components.dialogs import ConfirmDialog
        d = ConfirmDialog("Test", "Are you sure?")
        self.assertIsNotNone(d)
        d.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 4: EnterpriseTable + data loading
# ═══════════════════════════════════════════════════════════════

class TestEnterpriseTableSmoke(unittest.TestCase):

    def test_table_creates_and_loads_data(self):
        from ui.components.tables import EnterpriseTable, TableColumn
        cols = [
            TableColumn("name", "Name", width=200),
            TableColumn("value", "Value", width=100),
        ]
        t = EnterpriseTable(cols)
        t.set_data([
            {"name": "Item 1", "value": "100"},
            {"name": "Item 2", "value": "200"},
        ])
        self.assertEqual(t.rowCount(), 2)
        t.deleteLater()
        _app.processEvents()

    def test_table_empty_data(self):
        from ui.components.tables import EnterpriseTable, TableColumn
        t = EnterpriseTable([TableColumn("x", "X")])
        t.set_data([])
        self.assertEqual(t.rowCount(), 0)
        t.deleteLater()
        _app.processEvents()

    def test_table_set_data_multiple_times(self):
        """Simulate 100 refresh cycles — no duplicate signals."""
        from ui.components.tables import EnterpriseTable, TableColumn
        t = EnterpriseTable([TableColumn("x", "X")])
        for i in range(100):
            t.set_data([{"x": str(i)}])
        self.assertEqual(t.rowCount(), 1)
        t.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 5: EnterpriseButton variants
# ═══════════════════════════════════════════════════════════════

class TestEnterpriseButtonSmoke(unittest.TestCase):

    def test_all_variants_create(self):
        from ui.components.buttons import EnterpriseButton, ButtonVariant
        for variant in ButtonVariant:
            btn = EnterpriseButton("Test", variant=variant)
            self.assertIsNotNone(btn)
            btn.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 6: FormField + FormSection
# ═══════════════════════════════════════════════════════════════

class TestFormSmoke(unittest.TestCase):

    def test_form_field_types(self):
        from ui.components.forms import FormField, FieldType
        for ft in [FieldType.TEXT, FieldType.NUMBER, FieldType.DECIMAL,
                   FieldType.DATE, FieldType.SELECT, FieldType.CHECKBOX]:
            f = FormField(ft, label="Test")
            self.assertIsNotNone(f)
            f.deleteLater()
        _app.processEvents()

    def test_form_section_2col(self):
        from ui.components.forms import FormSection
        from PySide6.QtWidgets import QLineEdit
        s = FormSection("Test Section", columns=2)
        w1 = QLineEdit()
        w2 = QLineEdit()
        s.add_field_pair("Label1", w1, "Label2", w2)
        s.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 7: KPI Cards
# ═══════════════════════════════════════════════════════════════

class TestKPICardSmoke(unittest.TestCase):

    def test_kpi_card_creates(self):
        from ui.components.kpi_cards import KPICard
        c = KPICard("Revenue", "AFN 1,000", "Today", severity="success")
        c.update_value("AFN 2,000", severity="warning")
        c.deleteLater()
        _app.processEvents()

    def test_status_badge_creates(self):
        from ui.components.kpi_cards import StatusBadge
        b = StatusBadge("Active", severity="success")
        b.set_severity("danger")
        b.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 8: LicenseDetailsDialog
# ═══════════════════════════════════════════════════════════════

class TestLicenseDialogSmoke(unittest.TestCase):

    def test_license_details_creates(self):
        from ui.licensing.license_status_screen import LicenseDetailsDialog
        d = LicenseDetailsDialog({"key": "value", "status": "active"})
        self.assertTrue(hasattr(d, "exec"))
        d.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 9: Notification System
# ═══════════════════════════════════════════════════════════════

class TestNotificationSmoke(unittest.TestCase):

    def test_notification_create_and_dismiss(self):
        from ui.components.notifications import NotificationManager, NotificationType
        mgr = NotificationManager()
        mgr.show_notification("Test", NotificationType.INFO)
        _app.processEvents()
        mgr.clear_all()
        mgr.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 10: Login Dialog
# ═══════════════════════════════════════════════════════════════

class TestLoginDialogSmoke(unittest.TestCase):

    def test_login_dialog_creates(self):
        from ui.auth.login_screen import LoginDialog
        d = LoginDialog(api_client=_mock_api())
        self.assertIsNotNone(d.username)
        self.assertIsNotNone(d.password)
        self.assertIsNotNone(d.login_btn)
        d.deleteLater()
        _app.processEvents()

    def test_login_empty_validation(self):
        from ui.auth.login_screen import LoginDialog
        d = LoginDialog(api_client=_mock_api())
        d.username.setText("")
        d.password.setText("")
        d.do_login()  # Must not crash — should set error text
        # In offscreen mode, isVisible() returns False because dialog isn't shown.
        # Verify the error was set correctly instead.
        self.assertEqual(d.status_label.text(), "Username is required")
        self.assertFalse(d._loading)  # Must not enter loading state
        d.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 11: DataEntryGrid
# ═══════════════════════════════════════════════════════════════

class TestDataEntryGridSmoke(unittest.TestCase):

    def test_grid_add_remove_rows(self):
        from ui.components.tables import DataEntryGrid
        g = DataEntryGrid(["Col A", "Col B", "Col C"])
        g.add_row(["1", "2", "3"])
        g.add_row(["4", "5", "6"])
        self.assertEqual(g.rowCount(), 2)
        g.remove_row(0)
        self.assertEqual(g.rowCount(), 1)
        vals = g.get_row_values(0)
        self.assertEqual(vals, ["4", "5", "6"])
        g.clear_all_rows()
        self.assertEqual(g.rowCount(), 0)
        g.deleteLater()
        _app.processEvents()


# ═══════════════════════════════════════════════════════════════
# SMOKE 12: Theme Engine switch cycle
# ═══════════════════════════════════════════════════════════════

class TestThemeEngineSmoke(unittest.TestCase):

    def test_theme_switch_100_times(self):
        from theme.theme_engine import ThemeEngine
        engine = ThemeEngine.instance()
        for i in range(100):
            engine.apply_theme("dark" if i % 2 == 0 else "light")
        self.assertIn(engine.current_theme(), ("dark", "light"))


# ═══════════════════════════════════════════════════════════════
# SMOKE 13: Encrypted Session — full runtime cycle
# ═══════════════════════════════════════════════════════════════

class TestSessionRuntimeSmoke(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_session_100_save_load_cycles(self):
        from unittest.mock import patch
        with patch("security.session_store._get_session_path",
                   return_value=os.path.join(self.tmpdir, "s.enc")):
            from security.session_store import save_session_data, load_session_data
            for i in range(100):
                save_session_data({"access_token": f"tok_{i}", "cycle": i})
            loaded = load_session_data()
            self.assertEqual(loaded["access_token"], "tok_99")
            self.assertEqual(loaded["cycle"], 99)


if __name__ == "__main__":
    unittest.main()
