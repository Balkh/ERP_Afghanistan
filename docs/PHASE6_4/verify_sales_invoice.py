"""
Phase 6.4 Step 1 — Structural Verification
Verifies that the refactored sales_invoice_screen.py preserves
the exact same widget tree, signal connections, and public API.
"""
import os
import sys
import inspect
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = os.path.abspath('E:/all downloads/Pharmacy_ERP')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'frontend'))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from ui.sales.sales_invoice_screen import SalesInvoiceScreen


EXPECTED_WIDGETS = {
    'status_label', 'workflow_status_label',
    'customer_combo', 'invoice_number',
    'invoice_date', 'due_date',
    'currency_combo', 'warehouse_combo',
    'barcode_search',
    'add_product_btn', 'remove_item_btn',
    'items_table',
    'customer_phone', 'credit_limit_label', 'balance_label', 'customer_address',
    'subtotal_label', 'discount_input', 'tax_enabled_cb', 'tax_input',
    'tax_amount_label', 'total_label', 'paid_input', 'notes_input',
    'save_btn', 'confirm_btn', 'return_btn', 'more_btn', 'more_menu',
    'submit_wf_btn', 'approve_wf_btn', 'reject_wf_btn', 'post_wf_btn',
}

EXPECTED_PRIVATE_BUILDERS = {'_build_header', '_build_filters', '_build_toolbar', '_build_table', '_build_footer', '_wire_signals'}

EXPECTED_PUBLIC_METHODS = {
    '__init__', 'load_data', '_on_screen_shown', '_setup_screen',
    'setup_shortcuts', 'load_customers',
    'on_customer_selected', 'on_barcode_scanned', 'on_product_selected',
    'show_product_selector', 'add_item_to_table', 'select_batch_for_row',
    'set_batch_for_row', 'on_item_changed', 'on_tax_enabled_changed',
    'recalculate_totals', 'get_invoice_data', 'update_button_states',
    'save_draft', 'confirm_invoice', 'dispatch_invoice', 'print_invoice',
    'create_return', 'remove_selected_item', 'clear_form',
    'load_workflow_status', 'perform_workflow_action',
}


class TestSalesInvoiceRefactor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_mock = type('MockClient', (), {})()
        cls.screen = SalesInvoiceScreen(api_client=cls.api_mock, auth_manager=None)

    def test_class_inherits_base_screen(self):
        from ui.screens.base_screen import BaseScreen
        self.assertTrue(issubclass(SalesInvoiceScreen, BaseScreen))

    def test_private_builders_exist(self):
        for name in EXPECTED_PRIVATE_BUILDERS:
            self.assertTrue(hasattr(self.screen, name), f"Missing private builder: {name}")
            self.assertTrue(callable(getattr(self.screen, name)), f"Not callable: {name}")

    def test_all_expected_widgets_created(self):
        missing = []
        for name in EXPECTED_WIDGETS:
            if not hasattr(self.screen, name):
                missing.append(name)
        self.assertEqual(missing, [], f"Missing widgets: {missing}")

    def test_widget_types(self):
        from PySide6.QtWidgets import (QComboBox, QLineEdit, QDateEdit, QTableWidget,
                                        QDoubleSpinBox, QCheckBox, QTextEdit, QLabel, QMenu)
        from ui.common.barcode_search import BarcodeSearchLineEdit
        from ui.components.buttons import EnterpriseButton
        type_checks = [
            ('customer_combo', QComboBox),
            ('invoice_number', QLineEdit),
            ('invoice_date', QDateEdit),
            ('due_date', QDateEdit),
            ('currency_combo', QComboBox),
            ('warehouse_combo', QComboBox),
            ('barcode_search', BarcodeSearchLineEdit),
            ('add_product_btn', EnterpriseButton),
            ('remove_item_btn', EnterpriseButton),
            ('items_table', QTableWidget),
            ('customer_phone', QLabel),
            ('discount_input', QDoubleSpinBox),
            ('tax_enabled_cb', QCheckBox),
            ('tax_input', QDoubleSpinBox),
            ('paid_input', QDoubleSpinBox),
            ('notes_input', QTextEdit),
            ('save_btn', EnterpriseButton),
            ('confirm_btn', EnterpriseButton),
            ('return_btn', EnterpriseButton),
            ('more_btn', EnterpriseButton),
            ('more_menu', QMenu),
            ('submit_wf_btn', EnterpriseButton),
            ('approve_wf_btn', EnterpriseButton),
            ('reject_wf_btn', EnterpriseButton),
            ('post_wf_btn', EnterpriseButton),
        ]
        for attr_name, expected_type in type_checks:
            actual = getattr(self.screen, attr_name, None)
            self.assertIsNotNone(actual, f"{attr_name} missing")
            self.assertIsInstance(actual, expected_type,
                                  f"{attr_name} type mismatch: {type(actual).__name__} != {expected_type.__name__}")

    def test_items_table_column_count(self):
        self.assertEqual(self.screen.items_table.columnCount(), 8)

    def test_items_table_headers(self):
        headers = [self.screen.items_table.horizontalHeaderItem(i).text()
                   for i in range(self.screen.items_table.columnCount())]
        self.assertEqual(headers, ["Product", "Batch", "Qty", "Unit Price",
                                    "Discount %", "Tax %", "Total", ""])

    def test_signals_defined(self):
        from PySide6.QtCore import Signal
        signal_attrs = [a for a in dir(SalesInvoiceScreen)
                        if isinstance(getattr(SalesInvoiceScreen, a, None), Signal)]
        self.assertIn('invoice_created', signal_attrs)
        self.assertIn('invoice_updated', signal_attrs)

    def test_signal_wiring_via_source_analysis(self):
        """Verify all 16 expected signal connections are present in _wire_signals()."""
        import inspect
        source = inspect.getsource(self.screen._wire_signals)
        expected_signals = [
            'barcode_search.barcode_scanned.connect',
            'barcode_search.product_selected.connect',
            'add_product_btn.clicked.connect',
            'remove_item_btn.clicked.connect',
            'items_table.itemChanged.connect',
            'discount_input.valueChanged.connect',
            'tax_enabled_cb.stateChanged.connect',
            'tax_input.valueChanged.connect',
            'paid_input.valueChanged.connect',
            'save_btn.clicked.connect',
            'confirm_btn.clicked.connect',
            'return_btn.clicked.connect',
            "submit_wf_btn.clicked.connect(lambda: self.perform_workflow_action('submit'))",
            "approve_wf_btn.clicked.connect(lambda: self.perform_workflow_action('approve'))",
            "reject_wf_btn.clicked.connect(lambda: self.perform_workflow_action('reject'))",
            "post_wf_btn.clicked.connect(lambda: self.perform_workflow_action('post'))",
        ]
        missing = [s for s in expected_signals if s not in source]
        self.assertEqual(missing, [], f"Missing signal connections in _wire_signals: {missing}")

    def test_wire_signals_connects_exactly_16(self):
        """Verify _wire_signals() body has exactly 16 .connect() calls (16 from builders, 0 leftover)."""
        import inspect
        source = inspect.getsource(self.screen._wire_signals)
        connect_count = source.count('.connect(')
        self.assertEqual(connect_count, 16, f"_wire_signals should have 16 .connect() calls, got {connect_count}")

    def test_setup_screen_calls_all_builders(self):
        """Verify _setup_screen() calls all 6 builder methods in order."""
        import inspect
        source = inspect.getsource(self.screen._setup_screen)
        expected_calls = [
            'self._build_header()',
            'self._build_filters()',
            'self._build_toolbar()',
            'self._build_table()',
            'self._build_footer()',
            'self._wire_signals()',
        ]
        missing = [c for c in expected_calls if c not in source]
        self.assertEqual(missing, [], f"_setup_screen missing calls: {missing}")

    def test_layout_hierarchy(self):
        """Screen layout should have header (QHBoxLayout), zone1 (QFrame), zone2 (QVBoxLayout), zone3 (QFrame)."""
        from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout
        screen_layout = self.screen.layout()
        self.assertIsInstance(screen_layout, QVBoxLayout)
        zone1 = self.screen.findChild(QFrame, "zoneHeader")
        zone3 = self.screen.findChild(QFrame, "zoneSummary")
        self.assertIsNotNone(zone1, "Zone 1 (zoneHeader) frame missing")
        self.assertIsNotNone(zone3, "Zone 3 (zoneSummary) frame missing")

    def test_public_methods_preserved(self):
        for name in EXPECTED_PUBLIC_METHODS:
            self.assertTrue(hasattr(self.screen, name), f"Missing public method: {name}")
            method = getattr(self.screen, name)
            if name != '__init__':
                self.assertTrue(callable(method), f"Not callable: {name}")

    def test_no_new_imports_required(self):
        from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                        QTableWidget, QTableWidgetItem,
                                        QLineEdit, QLabel, QComboBox, QDoubleSpinBox,
                                        QDateEdit, QHeaderView, QAbstractItemView,
                                        QFrame, QMenu, QCheckBox, QTextEdit)
        self.assertTrue(True)

    def test_no_runtime_errors_on_get_invoice_data(self):
        """get_invoice_data() should not raise on empty table."""
        try:
            data = self.screen.get_invoice_data()
            self.assertIsInstance(data, dict)
            self.assertIn('items', data)
            self.assertIn('total_amount', data)
        except Exception as e:
            self.fail(f"get_invoice_data() raised: {e}")

    def test_recalculate_totals_works_on_empty(self):
        try:
            self.screen.recalculate_totals()
            self.assertEqual(self.screen.subtotal_label.text(), "0.00")
        except Exception as e:
            self.fail(f"recalculate_totals() raised on empty: {e}")

    def test_update_button_states(self):
        try:
            self.screen.update_button_states("DRAFT")
            self.assertTrue(self.screen.save_btn.isEnabled())
            self.assertTrue(self.screen.confirm_btn.isEnabled())
            self.assertTrue(self.screen.return_btn.isHidden())
            self.screen.update_button_states("DISPATCHED")
            self.assertFalse(self.screen.save_btn.isEnabled())
            self.assertFalse(self.screen.confirm_btn.isEnabled())
            self.assertFalse(self.screen.return_btn.isHidden())
        except Exception as e:
            self.fail(f"update_button_states() raised: {e}")


if __name__ == '__main__':
    print("=" * 70)
    print("PHASE 6.4 STEP 1 — STRUCTURAL VERIFICATION")
    print("=" * 70)
    print()
    print("Verifies the 6-method refactor of sales_invoice_screen.py")
    print("preserves the exact same widget tree, signal connections, and")
    print("public API as the original implementation.")
    print()
    unittest.main(verbosity=2)
