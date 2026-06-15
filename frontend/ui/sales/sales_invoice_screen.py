from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                QTableWidget, QTableWidgetItem,
                                QLineEdit, QLabel, QComboBox, QDoubleSpinBox,
                                QDateEdit, QHeaderView, QAbstractItemView,
                                QFrame, QMenu, QCheckBox, QTextEdit)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from decimal import Decimal

from ui.common.batch_selection import BatchSelectionDialog
from ui.common.barcode_search import BarcodeSearchLineEdit
from ui.common.printable_invoice import PrintableInvoiceDialog
from api.endpoints import get_endpoint
from i18n import DateFormatter, DateFormat
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_CARD_TITLE, TEXT_BODY, TEXT_TABLE, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_LG, BORDER_RADIUS_SM, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING,
                           COLOR_DANGER, COLOR_INFO, DENSITY_COMPACT_ROW,
                           COLOR_TEXT_ON_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, ConfirmDialog
from ui.components.operator_safety import DestructiveActionGuard
from ui.screens.base_screen import BaseScreen


class SalesInvoiceScreen(BaseScreen):
    """Screen for creating and managing sales invoices.

    Phase 15C: 3-zone architecture
    ZONE 1 — Header Context (customer, metadata, status)
    ZONE 2 — Line Item Engine (unified table, inline editing)
    ZONE 3 — Financial Summary Panel (totals, primary action)
    """

    invoice_created = Signal(dict)
    invoice_updated = Signal(dict)

    def __init__(self, parent=None, api_client=None, auth_manager=None):
        self.api_client = api_client
        self.auth_manager = auth_manager
        self._api_client_init = api_client
        self._auth_manager_init = auth_manager
        self.invoice_items = []
        self.current_invoice_id = None
        self.customers = []
        self.products = []
        self._date_format = self._load_date_format()
        super().__init__(parent)
        self._apply_date_format()
        self.setup_shortcuts()

    def _load_date_format(self):
        """Load date format preference from theme config."""
        try:
            import json, os
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'theme_preference.json')
            if os.path.exists(config_path):
                with open(config_path) as f:
                    cfg = json.load(f)
                return cfg.get('date_format', 'gregorian')
        except Exception:
            pass
        return 'gregorian'

    def _apply_date_format(self):
        """Apply date format to all QDateEdit widgets."""
        is_jalali = self._date_format == 'shamsi'
        for w in [self.invoice_date, self.due_date]:
            if is_jalali:
                w.setDisplayFormat("yyyy/MM/dd")
            else:
                w.setDisplayFormat("yyyy-MM-dd")

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        self.load_customers()
        super().load_data(params)

    def _check_action(self, action: str) -> bool:
        """Check if user has permission for a sales action. Shows notification if denied."""
        if self.auth_manager and not self.auth_manager.has_action("sales", action):
            from ui.components.notifications import show_warning
            show_warning(f"Access denied: you don't have permission to {action} sales invoices")
            return False
        return True

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        self._build_header()
        self._build_filters()
        self._build_toolbar()
        self._build_table()
        self._build_footer()
        self._wire_signals()

    def _build_header(self):
        layout = self.layout()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, SPACING_SM)
        title_label = QLabel("Sales Invoice")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_label = QLabel("DRAFT")
        self.status_label.setStyleSheet(f"""
            background-color: {COLOR_TEXT_MUTED};
            color: {COLOR_TEXT_PRIMARY};
            padding: {SPACING_XS}px {SPACING_MD}px;
            border-radius: {BORDER_RADIUS_SM};
            font-weight: bold;
            font-size: {TEXT_TABLE}px;
        """)
        header_layout.addWidget(self.status_label)

        self.workflow_status_label = QLabel("")
        self.workflow_status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        header_layout.addWidget(self.workflow_status_label)

        layout.addLayout(header_layout)

    def _build_filters(self):
        layout = self.layout()
        zone1 = QFrame()
        zone1.setObjectName("zoneHeader")
        zone1.setStyleSheet(f"QFrame#zoneHeader {{ background: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}")
        zone1_layout = QHBoxLayout(zone1)
        zone1_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        zone1_layout.setSpacing(SPACING_LG)

        # Left: Customer + Invoice #
        left_form = QFormLayout()
        left_form.setSpacing(SPACING_SM)
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setLabelAlignment(Qt.AlignRight)
        left_form.setFormAlignment(Qt.AlignLeft)

        self.customer_combo = QComboBox()
        self.customer_combo.setPlaceholderText("Select customer...")
        self.customer_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self.customer_combo.setMinimumWidth(220)
        left_form.addRow("Customer:", self.customer_combo)

        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Auto-generated")
        self.invoice_number.setReadOnly(True)
        self.invoice_number.setMinimumHeight(INPUT_HEIGHT_MD)
        self.invoice_number.setMaximumWidth(160)
        left_form.addRow("Invoice #:", self.invoice_number)

        zone1_layout.addLayout(left_form)
        zone1_layout.addSpacing(SPACING_LG)

        # Center: Dates
        center_form = QFormLayout()
        center_form.setSpacing(SPACING_SM)
        center_form.setContentsMargins(0, 0, 0, 0)
        center_form.setLabelAlignment(Qt.AlignRight)
        center_form.setFormAlignment(Qt.AlignLeft)

        self.invoice_date = QDateEdit()
        self.invoice_date.setDate(QDate.currentDate())
        self.invoice_date.setCalendarPopup(True)
        self.invoice_date.setMinimumHeight(INPUT_HEIGHT_MD)
        self.invoice_date.setMaximumWidth(130)
        center_form.addRow("Date:", self.invoice_date)

        self.due_date = QDateEdit()
        self.due_date.setDate(QDate.currentDate().addDays(30))
        self.due_date.setCalendarPopup(True)
        self.due_date.setMinimumHeight(INPUT_HEIGHT_MD)
        self.due_date.setMaximumWidth(130)
        center_form.addRow("Due:", self.due_date)

        zone1_layout.addLayout(center_form)
        zone1_layout.addSpacing(SPACING_LG)

        # Right: Currency + Warehouse
        right_form = QFormLayout()
        right_form.setSpacing(SPACING_SM)
        right_form.setContentsMargins(0, 0, 0, 0)
        right_form.setLabelAlignment(Qt.AlignRight)
        right_form.setFormAlignment(Qt.AlignLeft)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["AFN", "USD"])
        self.currency_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self.currency_combo.setMaximumWidth(100)
        right_form.addRow("Currency:", self.currency_combo)

        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItems(["Main Warehouse", "Cold Storage"])
        self.warehouse_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self.warehouse_combo.setMaximumWidth(160)
        right_form.addRow("Warehouse:", self.warehouse_combo)

        zone1_layout.addLayout(right_form)
        zone1_layout.addStretch()

        layout.addWidget(zone1)

    def _build_toolbar(self):
        # Zone 2 vertical container shared with _build_table
        self._zone2_layout = QVBoxLayout()
        self._zone2_layout.setSpacing(SPACING_SM)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        self.barcode_search = BarcodeSearchLineEdit(api_client=self.api_client)
        self.barcode_search.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(self.barcode_search, 1)

        self.add_product_btn = EnterpriseButton(text="+ Add Product", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        search_layout.addWidget(self.add_product_btn)

        self.remove_item_btn = EnterpriseButton(text="Remove", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        search_layout.addWidget(self.remove_item_btn)

        self._zone2_layout.addLayout(search_layout)

    def _build_table(self):
        # Items table (EnterpriseTable density = compact)
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "Batch", "Qty", "Unit Price", "Discount %", "Tax %", "Total", ""
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.items_table.setMinimumHeight(TABLE_ROW_HEIGHT_LG * 8)
        self.items_table.verticalHeader().setDefaultSectionSize(DENSITY_COMPACT_ROW)
        self.items_table.setAlternatingRowColors(True)
        from ui.components.tables import build_table_stylesheet
        self.items_table.setStyleSheet(build_table_stylesheet())

        self._zone2_layout.addWidget(self.items_table)
        self.layout().addLayout(self._zone2_layout, stretch=1)

    def _build_footer(self):
        layout = self.layout()
        zone3 = QFrame()
        zone3.setObjectName("zoneSummary")
        zone3.setStyleSheet(f"QFrame#zoneSummary {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}")
        zone3_layout = QHBoxLayout(zone3)
        zone3_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        zone3_layout.setSpacing(SPACING_XXL)

        # Left: Customer details (compact)
        details_form = QFormLayout()
        details_form.setSpacing(SPACING_XS)
        details_form.setContentsMargins(0, 0, 0, 0)
        details_form.setLabelAlignment(Qt.AlignRight)

        self.customer_phone = QLabel("—")
        self.customer_phone.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
        details_form.addRow("Phone:", self.customer_phone)

        self.credit_limit_label = QLabel("—")
        self.credit_limit_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
        details_form.addRow("Credit Limit:", self.credit_limit_label)

        self.balance_label = QLabel("0.00")
        self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_TABLE}px; font-weight: bold;")
        details_form.addRow("Balance:", self.balance_label)

        self.customer_address = QTextEdit()
        self.customer_address.setReadOnly(True)
        self.customer_address.setMaximumHeight(40)
        self.customer_address.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px; border: none; background: transparent;")
        details_form.addRow("Address:", self.customer_address)

        zone3_layout.addLayout(details_form)
        zone3_layout.addSpacing(SPACING_LG)

        # Center: Totals
        totals_layout = QFormLayout()
        totals_layout.setSpacing(SPACING_XS)
        totals_layout.setContentsMargins(0, 0, 0, 0)
        totals_layout.setLabelAlignment(Qt.AlignRight)

        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}px;")
        totals_layout.addRow("Subtotal:", self.subtotal_label)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0, 999999)
        self.discount_input.setValue(0)
        self.discount_input.setMaximumWidth(120)
        totals_layout.addRow("Discount:", self.discount_input)

        self.tax_enabled_cb = QCheckBox()
        self.tax_enabled_cb.setChecked(False)
        totals_layout.addRow("Enable Tax:", self.tax_enabled_cb)

        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setValue(0)
        self.tax_input.setSuffix("%")
        self.tax_input.setMaximumWidth(120)
        self.tax_input.setEnabled(False)
        totals_layout.addRow("Tax Rate:", self.tax_input)

        self.tax_amount_label = QLabel("0.00")
        self.tax_amount_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
        totals_layout.addRow("Tax Amt:", self.tax_amount_label)

        self.total_label = QLabel("0.00")
        self.total_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}px; font-weight: 700;")
        totals_layout.addRow("Total:", self.total_label)

        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 999999)
        self.paid_input.setValue(0)
        self.paid_input.setMaximumWidth(120)
        totals_layout.addRow("Paid:", self.paid_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes...")
        self.notes_input.setMaximumHeight(40)
        self.notes_input.setMaximumWidth(120)
        self.notes_input.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_TABLE}px;")
        totals_layout.addRow("Notes:", self.notes_input)

        zone3_layout.addLayout(totals_layout)
        zone3_layout.addSpacing(SPACING_LG)

        # Right: Primary action + secondary menu
        action_layout = QVBoxLayout()
        action_layout.setSpacing(SPACING_SM)
        action_layout.setContentsMargins(0, 0, 0, 0)

        self.save_btn = EnterpriseButton(text="Save Invoice", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        action_layout.addWidget(self.save_btn)

        self.confirm_btn = EnterpriseButton(text="Confirm & Dispatch", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        action_layout.addWidget(self.confirm_btn)

        # Secondary actions menu
        self.more_btn = EnterpriseButton(text="More ▾", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.more_menu = QMenu(self)
        self.more_menu.addAction("Print Invoice (Ctrl+P)", self.print_invoice)
        self.more_menu.addAction("Save as Draft", self.save_draft)
        self.more_menu.addAction("Clear Form (Ctrl+L)", self.clear_form)
        self.more_menu.addAction("New Invoice (Ctrl+N)", self.clear_form)
        self.more_btn.setMenu(self.more_menu)
        action_layout.addWidget(self.more_btn)

        # Return action (visible only for dispatched invoices)
        self.return_btn = EnterpriseButton(text="Create Return", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.return_btn.setVisible(False)
        action_layout.addWidget(self.return_btn)

        # Workflow actions (hidden by default)
        self.submit_wf_btn = EnterpriseButton(text="Submit for Approval", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.submit_wf_btn.setVisible(False)
        action_layout.addWidget(self.submit_wf_btn)

        self.approve_wf_btn = EnterpriseButton(text="Approve", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.approve_wf_btn.setVisible(False)
        action_layout.addWidget(self.approve_wf_btn)

        self.reject_wf_btn = EnterpriseButton(text="Reject", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.reject_wf_btn.setVisible(False)
        action_layout.addWidget(self.reject_wf_btn)

        self.post_wf_btn = EnterpriseButton(text="Post", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.post_wf_btn.setVisible(False)
        action_layout.addWidget(self.post_wf_btn)

        action_layout.addStretch()
        zone3_layout.addLayout(action_layout)

        layout.addWidget(zone3)

    def _wire_signals(self):
        # Toolbar (search + add/remove)
        self.barcode_search.barcode_scanned.connect(self.on_barcode_scanned)
        self.barcode_search.product_selected.connect(self.on_product_selected)
        self.add_product_btn.clicked.connect(self.show_product_selector)
        self.remove_item_btn.clicked.connect(self.remove_selected_item)

        # Table
        self.items_table.itemChanged.connect(self.on_item_changed)

        # Totals
        self.discount_input.valueChanged.connect(self.recalculate_totals)
        self.tax_enabled_cb.stateChanged.connect(self.on_tax_enabled_changed)
        self.tax_input.valueChanged.connect(self.recalculate_totals)
        self.paid_input.valueChanged.connect(self.recalculate_totals)

        # Primary actions
        self.save_btn.clicked.connect(self.save_draft)
        self.confirm_btn.clicked.connect(self.confirm_invoice)
        self.return_btn.clicked.connect(self.create_return)

        # Workflow actions
        self.submit_wf_btn.clicked.connect(lambda: self.perform_workflow_action('submit'))
        self.approve_wf_btn.clicked.connect(lambda: self.perform_workflow_action('approve'))
        self.reject_wf_btn.clicked.connect(lambda: self.perform_workflow_action('reject'))
        self.post_wf_btn.clicked.connect(lambda: self.perform_workflow_action('post'))

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_draft)
        QShortcut(QKeySequence("Ctrl+Enter"), self).activated.connect(self.confirm_invoice)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.dispatch_invoice)
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.print_invoice)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.clear_form)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.clear_form)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.barcode_search.setFocus)
        QShortcut(QKeySequence("F2"), self).activated.connect(self.show_product_selector)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.remove_selected_item)

    def load_customers(self):
        """Load customers from API."""
        # Default customers
        self.customers = [
            {"id": "cust-1", "name": "Ahmad Pharmacy", "phone": "+93 70 111 1111", "address": "Kabul", "credit_limit": 50000, "balance": 12000},
            {"id": "cust-2", "name": "Kabul Hospital", "phone": "+93 70 222 2222", "address": "Kabul", "credit_limit": 200000, "balance": 85000},
            {"id": "cust-3", "name": "Walk-in Customer", "phone": "N/A", "address": "N/A", "credit_limit": 0, "balance": 0},
        ]

        # Try to load from API
        if self.api_client:
            try:
                endpoint = get_endpoint("customers")
                response = self.api_client.get(endpoint)
                api_customers = []
                if isinstance(response, list):
                    api_customers = [c for c in response if isinstance(c, dict)]
                elif isinstance(response, dict) and response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        api_customers = [c for c in data if isinstance(c, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            api_customers = [c for c in data.get('results', []) if isinstance(c, dict)]
                        elif 'id' in data:
                            api_customers = [data]
                if api_customers:
                    self.customers = api_customers
            except Exception as e:
                print(f"Failed to load customers: {e}")

        self.customer_combo.clear()
        self.customer_combo.addItem("Select Customer...", None)
        for customer in self.customers:
            if isinstance(customer, dict):
                self.customer_combo.addItem(customer.get("name", "Unknown"), customer.get("id", ""))

        self.customer_combo.currentIndexChanged.connect(self.on_customer_selected)

    def on_customer_selected(self, index):
        """Handle customer selection."""
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            self.customer_phone.clear()
            self.customer_address.clear()
            self.credit_limit_label.setText("N/A")
            self.balance_label.setText("N/A")
            return

        customer = None
        for c in self.customers:
            if isinstance(c, dict) and c.get("id") == customer_id:
                customer = c
                break
        
        if customer:
            self.customer_phone.setText(customer.get("phone") or "")
            self.customer_address.setText(customer.get("address") or "")
            credit_limit = customer.get("credit_limit") or 0
            balance = customer.get("balance") or 0
            self.credit_limit_label.setText(f"${float(credit_limit):,.2f}")
            self.balance_label.setText(f"${float(balance):,.2f}")

            if customer.get("balance", 0) > customer.get("credit_limit", 0):
                self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold;")
            else:
                self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS};")

    def on_barcode_scanned(self, barcode):
        """Handle barcode scan - product selection is already handled by BarcodeSearchLineEdit."""

    def on_product_selected(self, product):
        """Handle product selection from search or barcode."""
        if not product:
            return
            
        # Check if product already in table, if so just increase qty
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            if name_item and name_item.data(Qt.UserRole) == product.get("id"):
                qty_item = self.items_table.item(row, 2)
                current_qty = int(qty_item.text() or 0)
                qty_item.setText(str(current_qty + 1))
                self.barcode_search.clear()
                return

        self.add_item_to_table(product)
        self.barcode_search.clear()

    def show_product_selector(self):
        """Show professional product selection dialog."""
        from ui.common.product_selection_dialog import ProductSelectionDialog
        dialog = ProductSelectionDialog(self, api_client=self.api_client)
        if dialog.exec():
            if dialog.selected_product:
                self.on_product_selected(dialog.selected_product)

    def add_item_to_table(self, product):
        """Add product to items table."""
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        # Product name
        name_item = QTableWidgetItem(product["name"])
        name_item.setData(Qt.UserRole, product["id"])
        self.items_table.setItem(row, 0, name_item)

        # Batch (clickable)
        batch_btn = EnterpriseButton("Select Batch", variant=ButtonVariant.SECONDARY)
        batch_btn.clicked.connect(lambda checked, r=row: self.select_batch_for_row(r))
        self.items_table.setCellWidget(row, 1, batch_btn)

        # Quantity
        qty_item = QTableWidgetItem("1")
        qty_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 2, qty_item)

        # Unit price
        price_item = QTableWidgetItem(f"{product.get('sale_price', 0):.2f}")
        price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 3, price_item)

        # Discount
        discount_item = QTableWidgetItem("0.00")
        discount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 4, discount_item)

        # Tax
        tax_item = QTableWidgetItem("0.00")
        tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 5, tax_item)

        # Total
        total_item = QTableWidgetItem(f"{product.get('sale_price', 0):.2f}")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setForeground(QColor(COLOR_SUCCESS))
        self.items_table.setItem(row, 6, total_item)

        # Actions
        remove_btn = EnterpriseButton("Remove", variant=ButtonVariant.GHOST)
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER};")
        remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))
        self.items_table.setCellWidget(row, 7, remove_btn)

        # Batch data storage
        batch_data_item = QTableWidgetItem("")
        batch_data_item.setData(Qt.UserRole, None)
        self.items_table.setItem(row, 8, batch_data_item)

        self.recalculate_totals()

    def select_batch_for_row(self, row):
        """Show batch selection dialog for a row."""
        product_name = self.items_table.item(row, 0).text()
        product_id = self.items_table.item(row, 0).data(Qt.UserRole)
        qty = int(self.items_table.item(row, 2).text() or 1)

        dialog = BatchSelectionDialog(
            self, product_id, product_name, qty, self.api_client
        )
        dialog.batch_selected.connect(lambda batch: self.set_batch_for_row(row, batch))
        dialog.exec()

    def set_batch_for_row(self, row, batch):
        """Set batch for a table row."""
        batch_widget = self.items_table.cellWidget(row, 1)
        if batch_widget:
            batch_widget.setText(batch["batch_number"])
            batch_widget.setDisabled(True)

        # Store batch data
        batch_data_item = self.items_table.item(row, 8)
        batch_data_item.setData(Qt.UserRole, batch)

    def on_item_changed(self, item):
        """Handle item change in table."""
        __row = item.row()
        self.recalculate_totals()

    def on_tax_enabled_changed(self, state):
        """Enable/disable tax rate input when tax toggle changes."""
        enabled = state == 2  # Qt.Checked
        self.tax_input.setEnabled(enabled)
        if not enabled:
            self.tax_input.setValue(0)
        self.recalculate_totals()

    def recalculate_totals(self):
        """Recalculate invoice totals."""
        self.items_table.blockSignals(True)
        subtotal = Decimal("0")

        for row in range(self.items_table.rowCount()):
            try:
                qty_item = self.items_table.item(row, 2)
                price_item = self.items_table.item(row, 3)
                discount_item = self.items_table.item(row, 4)
                total_item = self.items_table.item(row, 6)
                
                if not all([qty_item, price_item, discount_item, total_item]):
                    continue
                    
                qty = Decimal(qty_item.text() or "0")
                price = Decimal(price_item.text() or "0")
                discount = Decimal(discount_item.text() or "0")

                line_total = qty * price - discount
                total_item.setText(f"{line_total:.2f}")
                subtotal += line_total
            except (Exception, Decimal.InvalidOperation):
                pass

        discount = Decimal(str(self.discount_input.value()))
        taxable = subtotal - discount
        tax_enabled = self.tax_enabled_cb.isChecked()
        tax_rate = Decimal(str(self.tax_input.value())) if tax_enabled else Decimal('0')
        tax_amount = taxable * tax_rate / Decimal("100") if tax_enabled else Decimal("0")
        total = taxable + tax_amount
        paid = Decimal(str(self.paid_input.value()))
        balance = total - paid

        self.subtotal_label.setText(f"{subtotal:.2f}")
        self.tax_amount_label.setText(f"{tax_amount:.2f}")
        self.total_label.setText(f"{total:.2f}")
        self.balance_label.setText(f"{balance:.2f}")
        self.items_table.blockSignals(False)

    def get_invoice_data(self):
        """Collect all invoice data."""
        items = []
        for row in range(self.items_table.rowCount()):
            batch_data = self.items_table.item(row, 8).data(Qt.UserRole)
            items.append({
                "product_id": self.items_table.item(row, 0).data(Qt.UserRole),
                "product_name": self.items_table.item(row, 0).text(),
                "batch_id": batch_data.get("id") if batch_data else None,
                "batch_number": batch_data.get("batch_number", "") if batch_data else "",
                "quantity": int(self.items_table.item(row, 2).text() or 0),
                "unit_price": float(self.items_table.item(row, 3).text() or 0),
                "discount": float(self.items_table.item(row, 4).text() or 0),
                "tax": float(self.items_table.item(row, 5).text() or 0),
                "total": float(self.items_table.item(row, 6).text() or 0),
            })

        return {
            "customer_id": self.customer_combo.currentData(),
            "customer_name": self.customer_combo.currentText(),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "currency": self.currency_combo.currentText(),
            "subtotal": float(self.subtotal_label.text()),
            "discount": float(self.discount_input.value()),
            "tax_enabled": self.tax_enabled_cb.isChecked(),
            "tax_rate": float(self.tax_input.value()),
            "tax": float(self.tax_amount_label.text()),
            "total_amount": float(self.total_label.text()),
            "paid_amount": float(self.paid_input.value()),
            "notes": self.notes_input.toPlainText(),
            "items": items,
        }

    def update_button_states(self, status):
        """Update action button states based on invoice status."""
        is_draft = status == "DRAFT"
        is_dispatched = status == "DISPATCHED"

        self.save_btn.setEnabled(is_draft)
        self.confirm_btn.setEnabled(is_draft)
        self.return_btn.setVisible(is_dispatched)

    def save_invoice(self):
        return self.confirm_invoice()

    def save_draft(self):
        """Save invoice as draft."""
        if not self._check_action("create"):
            return
        data = self.get_invoice_data()
        if not data["items"]:
            AlertDialog.warning("Validation Error", "Please add at least one product.", self)
            return
            
        try:
            endpoint = get_endpoint("sales_invoices")
            res = self.api_client.post(endpoint, data)
            if res:
                res_data = res.get('data', res) if isinstance(res, dict) else res
                self.current_invoice_id = res_data.get('id')
                self.invoice_number.setText(res_data.get("invoice_number", "DRAFT"))
                self.update_button_states("DRAFT")
                AlertDialog.info("Success", "Invoice saved as draft.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to save draft: {e}", self)

    def confirm_invoice(self):
        """Confirm the invoice — persists to backend."""
        data = self.get_invoice_data()
        if not data["customer_id"]:
            AlertDialog.warning("Validation Error", "Please select a customer.", self)
            return
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "Save the invoice as draft first.", self)
            return

        if not DestructiveActionGuard.confirm_irreversible(
            self, "Confirm Invoice",
            f"Are you sure you want to confirm this invoice?\n\nTotal: {data['total_amount']:.2f} {data['currency']}"
        ):
            return

        try:
            endpoint = f"/api/sales/invoices/{self.current_invoice_id}/confirm/"
            res = self.api_client.post(endpoint, {})
            if res:
                self.status_label.setText("CONFIRMED")
                self.status_label.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
                self.update_button_states("CONFIRMED")
                AlertDialog.info("Success", "Invoice confirmed successfully.", self)
            else:
                AlertDialog.error("Error", "Failed to confirm invoice on server.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to confirm: {e}", self)

    def dispatch_invoice(self):
        """Dispatch invoice and deduct stock — persists to backend."""
        if not self._check_action("dispatch"):
            return
        __data = self.get_invoice_data()
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "Save the invoice as draft first.", self)
            return
        if self.status_label.text() != "CONFIRMED":
            AlertDialog.warning("Error", "Invoice must be confirmed before dispatch.", self)
            return

        if not DestructiveActionGuard.confirm_irreversible(
            self, "Dispatch Invoice",
            "This will deduct stock from inventory.\n\nContinue?"
        ):
            return

        try:
            endpoint = f"/api/sales/invoices/{self.current_invoice_id}/dispatch_invoice/"
            res = self.api_client.post(endpoint, {})
            if res:
                self.status_label.setText("DISPATCHED")
                self.status_label.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
                self.update_button_states("DISPATCHED")
                AlertDialog.info("Success", "Invoice dispatched and stock deducted.", self)
            else:
                AlertDialog.error("Error", "Failed to dispatch invoice on server.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to dispatch: {e}", self)

    def print_invoice(self):
        """Print the invoice."""
        data = self.get_invoice_data()
        data["phone"] = self.customer_phone.text()
        data["address"] = self.customer_address.toPlainText()

        dialog = PrintableInvoiceDialog(self, data, "sale", api_client=self.api_client)
        dialog.exec()

    def create_return(self):
        """Open return dialog pre-filled with current invoice data."""
        if not self.current_invoice_id:
            AlertDialog.warning("No Invoice", "Please save the invoice first.", self)
            return
        
        try:
            from ui.returns.returns_screen import ReturnOrderDialog
            dialog = ReturnOrderDialog(self, api_client=self.api_client)
            dialog.set_invoice_type("SALE_RETURN")
            dialog.prefill_from_invoice(self.current_invoice_id)
            if dialog.exec():
                AlertDialog.info("Return Created", "Return order created successfully.", self)
        except ImportError:
            AlertDialog.warning("Error", "Returns module not available.", self)

    def remove_selected_item(self):
        """Remove selected row from items table."""
        selected_rows = self.items_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.items_table.removeRow(index.row())
        self.recalculate_totals()

    def clear_form(self):
        """Clear the entire form."""
        self.customer_combo.setCurrentIndex(0)
        self.invoice_number.clear()
        self.invoice_date.setDate(QDate.currentDate())
        self.due_date.setDate(QDate.currentDate().addDays(30))
        self.notes_input.clear()
        self.discount_input.setValue(0)
        self.tax_enabled_cb.setChecked(False)
        self.tax_input.setValue(0)
        self.tax_input.setEnabled(False)
        self.paid_input.setValue(0)
        self.items_table.setRowCount(0)
        self.recalculate_totals()
        self.status_label.setText("DRAFT")
        self.status_label.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
        self.current_invoice_id = None
        self.workflow_status_label.setText("")
        self.submit_wf_btn.setVisible(True)
        self.approve_wf_btn.setVisible(False)
        self.reject_wf_btn.setVisible(False)
        self.post_wf_btn.setVisible(False)
        AlertDialog.info("Cleared", "Form cleared successfully.", self)
    
    def load_workflow_status(self, invoice_id: int):
        """Load workflow status for current invoice."""
        if not invoice_id:
            return
        
        try:
            result = self.api_client.get_workflow_status('SALES_INVOICE', invoice_id)
            if result.get('success') and result.get('data'):
                data = result['data']
                if data.get('has_workflow') is False:
                    self.workflow_status_label.setText("")
                    return
                
                state = data.get('state', 'DRAFT')
                state_display = data.get('state_display', state)
                
                # Update workflow status label
                color_map = {
                    'DRAFT': COLOR_TEXT_MUTED,
                    'PENDING_APPROVAL': COLOR_WARNING,
                    'APPROVED': COLOR_SUCCESS,
                    'REJECTED': COLOR_DANGER,
                    'POSTED': COLOR_INFO,
                    'CANCELLED': COLOR_TEXT_MUTED
                }
                color = color_map.get(state, COLOR_TEXT_MUTED)
                self.workflow_status_label.setText(f"Workflow: {state_display}")
                self.workflow_status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: {SPACING_SM}px;")
                
                # Show/hide action buttons based on permissions
                self.submit_wf_btn.setVisible(data.get('can_submit', False))
                self.approve_wf_btn.setVisible(data.get('can_approve', False))
                self.reject_wf_btn.setVisible(data.get('can_approve', False))
                self.post_wf_btn.setVisible(data.get('can_post', False))
        except Exception as e:
            print(f"Error loading workflow status: {e}")
    
    def perform_workflow_action(self, action: str):
        """Perform workflow action on current invoice."""
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "No invoice selected.", self)
            return
        
        # Get workflow for this invoice
        try:
            status_result = self.api_client.get_workflow_status('SALES_INVOICE', self.current_invoice_id)
            if not status_result.get('success') or not status_result.get('data', {}).get('has_workflow'):
                AlertDialog.warning("Error", "No workflow found for this invoice.", self)
                return
            
            workflow_id = status_result['data'].get('id')
            if not workflow_id:
                AlertDialog.warning("Error", "Could not find workflow ID.", self)
                return
            
            # Get comment if needed
            comment = ''
            if action in ['reject']:
                from PySide6.QtWidgets import QInputDialog
                comment, ok = QInputDialog.getText(self, f"{action.title()} Reason", f"Enter reason for {action}:")
                if not ok:
                    return
            
            # Perform action
            result = self.api_client.workflow_action(workflow_id, action, comment)
            
            if result.get('success'):
                AlertDialog.info("Success", f"Invoice {action}ed successfully.", self)
                # Reload workflow status
                self.load_workflow_status(self.current_invoice_id)
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                AlertDialog.warning("Error", f"Failed to {action}: {error}", self)
        except Exception as e:
            AlertDialog.error("Error", f"Error performing workflow action: {str(e)}", self)


# Helper for QInputDialog (since we can't import it directly in some setups)
def QInputDialog_getItem(parent, title, label, items):
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getItem(parent, title, label, items)
