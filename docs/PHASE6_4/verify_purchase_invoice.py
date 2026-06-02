"""
Phase 6.4 Step 2 — Structural Verification
Verifies that the refactored purchase_invoice_screen.py preserves
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

from ui.purchases.purchase_invoice_screen import PurchaseInvoiceScreen


EXPECTED_WIDGETS = {
    'status_label', 'workflow_status_label',
    'supplier_combo', 'invoice_number',
    'invoice_date', 'due_date',
    'currency_combo', 'warehouse_combo',
    'product_search',
    'add_product_btn', 'remove_item_btn',
    'items_table',
    'supplier_phone', 'credit_limit_label', 'balance_label', 'supplier_address',
    'subtotal_label', 'discount_input', 'tax_enabled_cb', 'tax_input',
    'tax_amount_label', 'total_label', 'paid_input', 'notes_input',
    'save_btn', 'confirm_btn', 'return_btn', 'more_btn', 'more_menu',
    'submit_wf_btn', 'approve_wf_btn', 'reject_wf_btn', 'post_wf_btn',
}

EXPECTED_PRIVATE_BUILDERS = {'_build_header', '_build_filters', '_build_toolbar', '_build_table', '_build_footer', '_wire_signals'}

EXPECTED_PUBLIC_METHODS = {
    '__init__', 'load_data', '_on_screen_shown', '_setup_screen',
    'setup_shortcuts', 'load_suppliers',
    'on_supplier_selected', 'show_product_selector',
    '_fetch_products', '_on_product_search_changed', '_on_product_search_submit',
    '_run_product_search', '_show_search_results',
    'add_item_to_table', '_on_remove_row', 'on_item_changed',
    'on_tax_enabled_changed', 'recalculate_totals', 'get_invoice_data',
    'update_button_states', 'save_draft', 'confirm_invoice', 'receive_invoice',
    'print_invoice', 'create_return', 'remove_selected_item', 'clear_form',
    'load_workflow_status', 'perform_workflow_action',
}

EXPECTED_WIRE_SIGNALS = [
    'product_search.returnPressed.connect',
    'product_search.textChanged.connect',
    'add_product_btn.clicked.connect',
    'remove_item_btn.clicked.connect',
    'items_table.cell_value_changed.connect',
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


class TestPurchaseInvoiceRefactor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_mock = type('MockClient', (), {})()
        cls.screen = PurchaseInvoiceScreen(api_client=cls.api_mock, auth_manager=None)

    def test_class_inherits_base_screen(self):
        from ui.screens.base_screen import BaseScreen
        self.assertTrue(issubclass(PurchaseInvoiceScreen, BaseScreen))

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
        from PySide6.QtWidgets import (QComboBox, QLineEdit, QDateEdit, QDoubleSpinBox,
                                        QCheckBox, QTextEdit, QLabel, QMenu)
        from ui.components.buttons import EnterpriseButton
        from ui.components.tables import DataEntryGrid
        type_checks = [
            ('supplier_combo', QComboBox),
            ('invoice_number', QLineEdit),
            ('invoice_date', QDateEdit),
            ('due_date', QDateEdit),
            ('currency_combo', QComboBox),
            ('warehouse_combo', QComboBox),
            ('product_search', QLineEdit),
            ('add_product_btn', EnterpriseButton),
            ('remove_item_btn', EnterpriseButton),
            ('items_table', DataEntryGrid),
            ('supplier_phone', QLabel),
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

    def test_items_table_columns(self):
        from ui.components.tables import DataEntryGrid
        self.assertIsInstance(self.screen.items_table, DataEntryGrid)
        self.assertEqual(self.screen.items_table.columnCount(), 10)
        headers = [self.screen.items_table.horizontalHeaderItem(i).text()
                   for i in range(self.screen.items_table.columnCount())]
        self.assertEqual(headers, ["Product", "Batch #", "Mfg Date", "Expiry",
                                    "Qty", "Unit Price", "Discount %", "Tax %", "Total", ""])

    def test_signals_defined(self):
        from PySide6.QtCore import Signal
        signal_attrs = [a for a in dir(PurchaseInvoiceScreen)
                        if isinstance(getattr(PurchaseInvoiceScreen, a, None), Signal)]
        self.assertIn('invoice_created', signal_attrs)
        self.assertIn('invoice_updated', signal_attrs)

    def test_signal_wiring_via_source_analysis(self):
        """Verify all 16 expected signal connections are present in _wire_signals()."""
        source = inspect.getsource(self.screen._wire_signals)
        missing = [s for s in EXPECTED_WIRE_SIGNALS if s not in source]
        self.assertEqual(missing, [], f"Missing signal connections in _wire_signals: {missing}")

    def test_wire_signals_connects_exactly_16(self):
        """Verify _wire_signals() body has exactly 16 .connect() calls."""
        source = inspect.getsource(self.screen._wire_signals)
        connect_count = source.count('.connect(')
        self.assertEqual(connect_count, 16, f"_wire_signals should have 16 .connect() calls, got {connect_count}")

    def test_setup_screen_calls_all_builders(self):
        """Verify _setup_screen() calls all 6 builder methods in order."""
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
        """Screen layout should have zoneHeader + zoneSummary QFrames."""
        from PySide6.QtWidgets import QFrame, QVBoxLayout
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

    def test_no_runtime_errors_on_get_invoice_data(self):
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
            self.screen.update_button_states("RECEIVED")
            self.assertFalse(self.screen.save_btn.isEnabled())
            self.assertFalse(self.screen.confirm_btn.isEnabled())
            self.assertFalse(self.screen.return_btn.isHidden())
        except Exception as e:
            self.fail(f"update_button_states() raised: {e}")

    def test_product_search_signals_via_source(self):
        """Verify the 2 product_search signals (returnPressed, textChanged) are in _wire_signals."""
        source = inspect.getsource(self.screen._wire_signals)
        self.assertIn('product_search.returnPressed.connect', source)
        self.assertIn('product_search.textChanged.connect', source)


if __name__ == '__main__':
    print("=" * 70)
    print("PHASE 6.4 STEP 2 — STRUCTURAL VERIFICATION")
    print("=" * 70)
    print()
    print("Verifies the 6-method refactor of purchase_invoice_screen.py")
    print("preserves the exact same widget tree, signal connections, and")
    print("public API as the original implementation.")
    print()
    unittest.main(verbosity=2)
