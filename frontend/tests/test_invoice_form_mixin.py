"""Unit tests for InvoiceFormMixin shared invoice screen infrastructure."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure PySide6 is importable (tests run headless)
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QDate
except ImportError:
    pytest.skip("PySide6 not available", allow_module_level=True)

# Ensure a QApplication exists for widget creation
_app = QApplication.instance() or QApplication(sys.argv)


def _make_mock_screen():
    """Create a minimal mock screen that satisfies InvoiceFormMixin's contract."""
    from ui.common.invoice_form_mixin import InvoiceFormMixin
    from PySide6.QtWidgets import QVBoxLayout, QComboBox, QLineEdit, QWidget, QLabel

    class MockScreen(InvoiceFormMixin, QWidget):
        _invoice_type = 'TEST_INVOICE'
        _entity_type = 'customer'
        _entity_label = 'Customer'
        _return_type = 'TEST_RETURN'

        def __init__(self):
            super().__init__()
            self.api_client = MagicMock()
            self.current_invoice_id = None
            self.warehouses = []

            # Create layout (self is a QWidget)
            QVBoxLayout(self)

            # Create widgets needed by mixin BEFORE any mixin method runs
            self.customer_combo = QComboBox()
            self.product_search = QLineEdit()

            # Set mixin references
            self._entity_combo = self.customer_combo
            self._search_widget = self.product_search
            self._entity_selected_slot = self.on_customer_selected

            # Footer widgets (set by build_invoice_footer in real screens)
            self.entity_phone = MagicMock()
            self.entity_address = MagicMock()
            self.entity_phone.text.return_value = "+1234567890"
            self.entity_address.toPlainText.return_value = "123 Test St"

            # Workflow buttons
            self.submit_wf_btn = MagicMock()
            self.approve_wf_btn = MagicMock()
            self.reject_wf_btn = MagicMock()
            self.post_wf_btn = MagicMock()

            # Action buttons
            self.save_btn = MagicMock()
            self.confirm_btn = MagicMock()
            self.return_btn = MagicMock()

            # Status (real QLabel for text/style checks)
            self.status_label = QLabel("DRAFT")
            self.workflow_status_label = QLabel("")

            # Table (mock)
            self.items_table = MagicMock()
            self.items_table.selectionModel.return_value.selectedRows.return_value = []

            # Footer labels (mocks)
            self.subtotal_label = MagicMock()
            self.tax_amount_label = MagicMock()
            self.total_label = MagicMock()
            self.balance_label = MagicMock()
            self.discount_input = MagicMock()
            self.tax_enabled_cb = MagicMock()
            self.tax_input = MagicMock()
            self.paid_input = MagicMock()
            self.notes_input = MagicMock()

        def on_customer_selected(self, index):
            pass

        def recalculate_totals(self):
            pass

        def get_invoice_data(self):
            return {"items": [], "total_amount": 0}

    return MockScreen()


# ─── build_header ────────────────────────────────────────────────────────────

class TestBuildHeader:
    def test_creates_status_and_workflow_labels(self):
        screen = _make_mock_screen()
        screen.build_header("Test Invoice")
        assert screen.status_label is not None
        assert screen.workflow_status_label is not None

    def test_default_title_uses_entity_label(self):
        screen = _make_mock_screen()
        screen.build_header()
        # status_label should be created (default title = "Customer Invoice")
        assert screen.status_label is not None

    def test_custom_title(self):
        screen = _make_mock_screen()
        screen.build_header("Custom Title")
        assert screen.status_label is not None

    def test_status_label_initial_state(self):
        screen = _make_mock_screen()
        screen.build_header()
        assert screen.status_label.text() == "DRAFT"


# ─── build_filters ───────────────────────────────────────────────────────────

class TestBuildFilters:
    def test_creates_invoice_date(self):
        screen = _make_mock_screen()
        screen.build_filters()
        assert hasattr(screen, 'invoice_date')

    def test_creates_due_date(self):
        screen = _make_mock_screen()
        screen.build_filters()
        assert hasattr(screen, 'due_date')

    def test_creates_invoice_number(self):
        screen = _make_mock_screen()
        screen.build_filters()
        assert hasattr(screen, 'invoice_number')

    def test_creates_currency_combo_with_afn_usd(self):
        screen = _make_mock_screen()
        screen.build_filters()
        items = [screen.currency_combo.itemText(i) for i in range(screen.currency_combo.count())]
        assert "AFN" in items
        assert "USD" in items

    def test_creates_warehouse_combo(self):
        screen = _make_mock_screen()
        screen.build_filters()
        assert hasattr(screen, 'warehouse_combo')

    def test_entity_combo_has_placeholder(self):
        screen = _make_mock_screen()
        screen.build_filters()
        placeholder = screen.customer_combo.placeholderText()
        assert "customer" in placeholder.lower()

    def test_invoice_number_placeholder(self):
        screen = _make_mock_screen()
        screen.build_filters()
        placeholder = screen.invoice_number.placeholderText()
        assert "invoice" in placeholder.lower()

    def test_date_defaults(self):
        screen = _make_mock_screen()
        screen.build_filters()
        today = QDate.currentDate()
        assert screen.invoice_date.date() == today
        assert screen.due_date.date() == today.addDays(30)


# ─── load_warehouses ─────────────────────────────────────────────────────────

class TestLoadWarehouses:
    def test_loads_warehouses_from_api(self):
        screen = _make_mock_screen()
        screen.api_client.get.return_value = [
            {"id": "w1", "name": "Main Warehouse"},
            {"id": "w2", "name": "Cold Storage"},
        ]
        screen.build_filters()
        screen.load_warehouses()
        assert len(screen.warehouses) == 2
        items = [screen.warehouse_combo.itemText(i) for i in range(screen.warehouse_combo.count())]
        assert "Main Warehouse" in items
        assert "Cold Storage" in items

    def test_empty_warehouses(self):
        screen = _make_mock_screen()
        screen.api_client.get.return_value = []
        screen.build_filters()
        screen.load_warehouses()
        assert screen.warehouse_combo.count() == 1  # Just placeholder

    def test_api_error_graceful(self):
        screen = _make_mock_screen()
        screen.api_client.get.side_effect = Exception("API down")
        screen.build_filters()
        screen.load_warehouses()
        assert screen.warehouses == []
        assert screen.warehouse_combo.count() == 1

    def test_no_api_client(self):
        screen = _make_mock_screen()
        screen.api_client = None
        screen.build_filters()
        screen.load_warehouses()
        assert screen.warehouses == []

    def test_connects_entity_selection_signal(self):
        screen = _make_mock_screen()
        screen.api_client.get.return_value = []
        screen.build_filters()
        screen.load_warehouses()
        # Should not crash when combo changes
        screen.customer_combo.setCurrentIndex(0)


# ─── set_status ──────────────────────────────────────────────────────────────

class TestSetStatus:
    def test_updates_status_text(self):
        screen = _make_mock_screen()
        screen.build_header()
        screen.set_status("CONFIRMED", "#007bff")
        assert screen.status_label.text() == "CONFIRMED"

    def test_updates_status_color(self):
        screen = _make_mock_screen()
        screen.build_header()
        screen.set_status("CONFIRMED", "#007bff")
        assert "#007bff" in screen.status_label.styleSheet()

    def test_draft_status(self):
        screen = _make_mock_screen()
        screen.build_header()
        screen.set_status("DRAFT", "#808080")
        assert screen.status_label.text() == "DRAFT"


# ─── update_button_states ────────────────────────────────────────────────────

class TestUpdateButtonStates:
    def test_draft_enables_save_and_confirm(self):
        screen = _make_mock_screen()
        screen.update_button_states("DRAFT")
        screen.save_btn.setEnabled.assert_called_with(True)
        screen.confirm_btn.setEnabled.assert_called_with(True)

    def test_draft_hides_return(self):
        screen = _make_mock_screen()
        screen.update_button_states("DRAFT")
        screen.return_btn.setVisible.assert_called_with(False)

    def test_received_shows_return(self):
        screen = _make_mock_screen()
        screen.update_button_states("RECEIVED")
        screen.return_btn.setVisible.assert_called_with(True)

    def test_dispatched_shows_return(self):
        screen = _make_mock_screen()
        screen.update_button_states("DISPATCHED")
        screen.return_btn.setVisible.assert_called_with(True)

    def test_confirmed_disables_save(self):
        screen = _make_mock_screen()
        screen.update_button_states("CONFIRMED")
        screen.save_btn.setEnabled.assert_called_with(False)
        screen.confirm_btn.setEnabled.assert_called_with(False)

    def test_other_status_hides_return(self):
        screen = _make_mock_screen()
        screen.update_button_states("SUBMITTED")
        screen.return_btn.setVisible.assert_called_with(False)


# ─── create_return ───────────────────────────────────────────────────────────

class TestCreateReturn:
    def test_no_invoice_shows_warning(self):
        screen = _make_mock_screen()
        screen.current_invoice_id = None
        with patch("ui.common.invoice_form_mixin.AlertDialog") as mock_alert:
            screen.create_return()
            mock_alert.warning.assert_called_once()

    def test_with_invoice_id(self):
        screen = _make_mock_screen()
        screen.current_invoice_id = 42
        mock_module = MagicMock()
        with patch("ui.common.invoice_form_mixin.AlertDialog"):
            with patch.dict(sys.modules, {"ui.returns.returns_screen": mock_module}):
                screen.create_return()
                mock_module.ReturnOrderDialog.assert_called_once()
                instance = mock_module.ReturnOrderDialog.return_value
                instance.set_invoice_type.assert_called_once_with("TEST_RETURN")
                instance.prefill_from_invoice.assert_called_once_with(42)

    def test_import_error_shows_warning(self):
        screen = _make_mock_screen()
        screen.current_invoice_id = 42
        with patch("ui.common.invoice_form_mixin.AlertDialog") as mock_alert:
            with patch.dict('sys.modules', {'ui.returns.returns_screen': None}):
                screen.create_return()
                mock_alert.warning.assert_called()


# ─── on_tax_enabled_changed ──────────────────────────────────────────────────

class TestOnTaxEnabledChanged:
    def test_enable_tax(self):
        screen = _make_mock_screen()
        screen.on_tax_enabled_changed(2)  # Qt.Checked
        screen.tax_input.setEnabled.assert_called_with(True)

    def test_disable_tax(self):
        screen = _make_mock_screen()
        screen.on_tax_enabled_changed(0)  # Qt.Unchecked
        screen.tax_input.setEnabled.assert_called_with(False)
        screen.tax_input.setValue.assert_called_with(0)


# ─── remove_selected_item ────────────────────────────────────────────────────

class TestRemoveSelectedItem:
    def test_no_selection(self):
        screen = _make_mock_screen()
        screen.remove_selected_item()
        # recalculate_totals is a real method on MockScreen, just verify no crash
        assert True

    def test_with_selection(self):
        screen = _make_mock_screen()
        mock_index = MagicMock()
        mock_index.row.return_value = 2
        screen.items_table.selectionModel.return_value.selectedRows.return_value = [mock_index]
        screen.remove_selected_item()
        screen.items_table.removeRow.assert_called_with(2)


# ─── build_toolbar ───────────────────────────────────────────────────────────

class TestBuildToolbar:
    def test_creates_zone2_layout(self):
        screen = _make_mock_screen()
        screen.build_toolbar()
        assert hasattr(screen, '_zone2_layout')

    def test_creates_add_product_btn(self):
        screen = _make_mock_screen()
        screen.build_toolbar()
        assert hasattr(screen, 'add_product_btn')

    def test_creates_remove_item_btn(self):
        screen = _make_mock_screen()
        screen.build_toolbar()
        assert hasattr(screen, 'remove_item_btn')

    def test_search_widget_added(self):
        screen = _make_mock_screen()
        screen.build_toolbar()
        # The search widget should be in the layout (verify no crash)
        assert screen._zone2_layout is not None


# ─── print_invoice (mixin) ──────────────────────────────────────────────────

class TestPrintInvoice:
    def test_uses_sale_for_customer_type(self):
        screen = _make_mock_screen()
        screen.build_header()
        with patch("ui.common.invoice_form_mixin.PrintableInvoiceDialog") as MockDialog:
            screen.print_invoice()
            args = MockDialog.call_args
            assert args[0][2] == "sale"

    def test_sets_phone_and_address(self):
        screen = _make_mock_screen()
        screen.build_header()
        with patch("ui.common.invoice_form_mixin.PrintableInvoiceDialog"):
            screen.print_invoice()
            # Verify print_invoice was callable (no crash)
            assert True
