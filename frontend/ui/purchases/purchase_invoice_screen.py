from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QTableWidget, QTableWidgetItem,
                                QLineEdit, QLabel, QComboBox, QDoubleSpinBox,
                                QDateEdit, QMessageBox, QHeaderView, QAbstractItemView,
                                QFrame, QMenu, QPushButton, QCheckBox)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from decimal import Decimal

from ui.common.printable_invoice import PrintableInvoiceDialog
from api.endpoints import get_endpoint
from i18n import DateFormatter, DateFormat
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_CARD_TITLE, TEXT_BODY, TEXT_TABLE, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_LG, BORDER_RADIUS_SM, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING,
                           COLOR_DANGER, COLOR_INFO, DENSITY_COMPACT_ROW)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


class PurchaseInvoiceScreen(QWidget):
    """Screen for creating and managing purchase invoices.

    Phase 15C: 3-zone architecture
    ZONE 1 — Header Context (supplier, metadata, status)
    ZONE 2 — Line Item Engine (unified table, inline editing)
    ZONE 3 — Financial Summary Panel (totals, primary action)
    """

    invoice_created = Signal(dict)
    invoice_updated = Signal(dict)

    def __init__(self, parent=None, api_client=None, auth_manager=None):
        super().__init__(parent)
        self.api_client = api_client
        self.auth_manager = auth_manager
        self.invoice_items = []
        self.current_invoice_id = None
        self.suppliers = []
        self.products = []
        self._date_format = self._load_date_format()

        self.setup_ui()
        self._apply_date_format()
        self.setup_shortcuts()
        self.load_suppliers()

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

    def _check_action(self, action: str) -> bool:
        """Check if user has permission for a purchase action."""
        if self.auth_manager and not self.auth_manager.has_action("purchases", action):
            from ui.components.notifications import show_warning
            show_warning(f"Access denied: you don't have permission to {action} purchase invoices")
            return False
        return True

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # ── PAGE HEADER ──
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, SPACING_SM)
        title_label = QLabel("Purchase Invoice")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_label = QLabel("DRAFT")
        self.status_label.setStyleSheet("""
            background-color: {COLOR_TEXT_MUTED};
            color: white;
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

        # ═══════════════════════════════════════════════════════
        # ZONE 1 — HEADER CONTEXT (compact metadata bar)
        # ═══════════════════════════════════════════════════════
        zone1 = QFrame()
        zone1.setObjectName("zoneHeader")
        zone1.setStyleSheet(f"QFrame#zoneHeader {{ background: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}")
        zone1_layout = QHBoxLayout(zone1)
        zone1_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        zone1_layout.setSpacing(SPACING_LG)

        # Left: Supplier + Invoice #
        left_form = QFormLayout()
        left_form.setSpacing(SPACING_SM)
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setLabelAlignment(Qt.AlignRight)
        left_form.setFormAlignment(Qt.AlignLeft)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setPlaceholderText("Select supplier...")
        self.supplier_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self.supplier_combo.setMinimumWidth(220)
        left_form.addRow("Supplier:", self.supplier_combo)

        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Enter supplier invoice #")
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

        # ═══════════════════════════════════════════════════════
        # ZONE 2 — LINE ITEM ENGINE (unified table + search)
        # ═══════════════════════════════════════════════════════
        zone2_layout = QVBoxLayout()
        zone2_layout.setSpacing(SPACING_SM)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search product by name, barcode...")
        self.product_search.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(self.product_search, 1)

        self.add_product_btn = EnterpriseButton(text="+ Add Product", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.add_product_btn.clicked.connect(self.show_product_selector)
        search_layout.addWidget(self.add_product_btn)

        self.remove_item_btn = EnterpriseButton(text="Remove", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.remove_item_btn.clicked.connect(self.remove_selected_item)
        search_layout.addWidget(self.remove_item_btn)

        zone2_layout.addLayout(search_layout)

        # Items table (compact density)
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(9)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "Batch #", "Mfg Date", "Expiry", "Qty", "Unit Price", "Discount %", "Tax %", "Total"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.items_table.itemChanged.connect(self.on_item_changed)
        self.items_table.setMinimumHeight(TABLE_ROW_HEIGHT_LG * 8)
        self.items_table.verticalHeader().setDefaultSectionSize(DENSITY_COMPACT_ROW)
        self.items_table.setAlternatingRowColors(True)
        from ui.components.tables import build_table_stylesheet
        self.items_table.setStyleSheet(build_table_stylesheet())

        zone2_layout.addWidget(self.items_table)
        layout.addLayout(zone2_layout, stretch=1)

        # ═══════════════════════════════════════════════════════
        # ZONE 3 — FINANCIAL SUMMARY PANEL (totals + primary action)
        # ═══════════════════════════════════════════════════════
        zone3 = QFrame()
        zone3.setObjectName("zoneSummary")
        zone3.setStyleSheet(f"QFrame#zoneSummary {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}")
        zone3_layout = QHBoxLayout(zone3)
        zone3_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        zone3_layout.setSpacing(SPACING_XXL)

        # Left: Supplier details (compact)
        details_form = QFormLayout()
        details_form.setSpacing(SPACING_XS)
        details_form.setContentsMargins(0, 0, 0, 0)
        details_form.setLabelAlignment(Qt.AlignRight)

        self.supplier_phone = QLabel("—")
        self.supplier_phone.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
        details_form.addRow("Phone:", self.supplier_phone)

        self.credit_limit_label = QLabel("—")
        self.credit_limit_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}px;")
        details_form.addRow("Credit Limit:", self.credit_limit_label)

        self.balance_label = QLabel("0.00")
        self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_TABLE}px; font-weight: bold;")
        details_form.addRow("Balance:", self.balance_label)

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
        self.discount_input.valueChanged.connect(self.recalculate_totals)
        totals_layout.addRow("Discount:", self.discount_input)

        self.tax_enabled_cb = QCheckBox()
        self.tax_enabled_cb.setChecked(False)
        self.tax_enabled_cb.stateChanged.connect(self.on_tax_enabled_changed)
        totals_layout.addRow("Enable Tax:", self.tax_enabled_cb)

        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setValue(0)
        self.tax_input.setSuffix("%")
        self.tax_input.setMaximumWidth(120)
        self.tax_input.setEnabled(False)
        self.tax_input.valueChanged.connect(self.recalculate_totals)
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
        self.paid_input.valueChanged.connect(self.recalculate_totals)
        totals_layout.addRow("Paid:", self.paid_input)

        zone3_layout.addLayout(totals_layout)
        zone3_layout.addSpacing(SPACING_LG)

        # Right: Primary action + secondary menu
        action_layout = QVBoxLayout()
        action_layout.setSpacing(SPACING_SM)
        action_layout.setContentsMargins(0, 0, 0, 0)

        self.save_btn = EnterpriseButton(text="Save Invoice", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.save_btn.clicked.connect(self.save_draft)
        action_layout.addWidget(self.save_btn)

        self.confirm_btn = EnterpriseButton(text="Confirm & Receive", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.confirm_btn.clicked.connect(self.receive_invoice)
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

        # Return action (visible only for received invoices)
        self.return_btn = EnterpriseButton(text="Create Return", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.return_btn.clicked.connect(self.create_return)
        self.return_btn.setVisible(False)
        action_layout.addWidget(self.return_btn)

        # Workflow actions (hidden by default)
        self.submit_wf_btn = EnterpriseButton(text="Submit for Approval", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.submit_wf_btn.clicked.connect(lambda: self.perform_workflow_action('submit'))
        self.submit_wf_btn.setVisible(False)
        action_layout.addWidget(self.submit_wf_btn)

        self.approve_wf_btn = EnterpriseButton(text="Approve", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.approve_wf_btn.clicked.connect(lambda: self.perform_workflow_action('approve'))
        self.approve_wf_btn.setVisible(False)
        action_layout.addWidget(self.approve_wf_btn)

        self.reject_wf_btn = EnterpriseButton(text="Reject", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.reject_wf_btn.clicked.connect(lambda: self.perform_workflow_action('reject'))
        self.reject_wf_btn.setVisible(False)
        action_layout.addWidget(self.reject_wf_btn)

        self.post_wf_btn = EnterpriseButton(text="Post", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.post_wf_btn.clicked.connect(lambda: self.perform_workflow_action('post'))
        self.post_wf_btn.setVisible(False)
        action_layout.addWidget(self.post_wf_btn)

        action_layout.addStretch()
        zone3_layout.addLayout(action_layout)

        layout.addWidget(zone3)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_draft)
        QShortcut(QKeySequence("Ctrl+Enter"), self).activated.connect(self.confirm_invoice)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.receive_invoice)
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.print_invoice)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.clear_form)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.clear_form)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.product_search.setFocus)
        QShortcut(QKeySequence("F2"), self).activated.connect(self.show_product_selector)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.remove_selected_item)

    def load_suppliers(self):
        """Load suppliers from API."""
        self.suppliers = [
            {"id": "sup-1", "name": "Pharma Corp", "phone": "+93 70 333 3333", "address": "Kabul Industrial", "credit_limit": 500000, "balance": 125000},
            {"id": "sup-2", "name": "MedSupply International", "phone": "+93 70 444 4444", "address": "Herat", "credit_limit": 1000000, "balance": 450000},
            {"id": "sup-3", "name": "Local Distributor", "phone": "+93 70 555 5555", "address": "Mazar", "credit_limit": 200000, "balance": 80000},
        ]

        # Try to load from API
        if self.api_client:
            try:
                endpoint = get_endpoint("suppliers")
                response = self.api_client.get(endpoint)
                api_suppliers = []
                if isinstance(response, list):
                    api_suppliers = [s for s in response if isinstance(s, dict)]
                elif isinstance(response, dict) and response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        api_suppliers = [s for s in data if isinstance(s, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            api_suppliers = [s for s in data.get('results', []) if isinstance(s, dict)]
                        elif 'id' in data:
                            api_suppliers = [data]
                if api_suppliers:
                    self.suppliers = api_suppliers
            except Exception as e:
                print(f"Failed to load suppliers: {e}")

        self.supplier_combo.clear()
        self.supplier_combo.addItem("Select Supplier...", None)
        for supplier in self.suppliers:
            if isinstance(supplier, dict):
                self.supplier_combo.addItem(supplier.get("name", "Unknown"), supplier.get("id", ""))

        self.supplier_combo.currentIndexChanged.connect(self.on_supplier_selected)

    def on_supplier_selected(self, index):
        """Handle supplier selection."""
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            self.supplier_phone.clear()
            self.supplier_address.clear()
            self.credit_limit_label.setText("N/A")
            self.balance_label.setText("N/A")
            return

        supplier = next((s for s in self.suppliers if s["id"] == supplier_id), None)
        if supplier:
            self.supplier_phone.setText(supplier.get("phone", ""))
            self.supplier_address.setText(supplier.get("address", ""))
            self.credit_limit_label.setText(f"${supplier.get('credit_limit', 0):,.2f}")
            self.balance_label.setText(f"${supplier.get('balance', 0):,.2f}")

            if supplier.get("balance", 0) > supplier.get("credit_limit", 0):
                self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold;")
            else:
                self.balance_label.setStyleSheet(f"color: {COLOR_SUCCESS};")

    def show_product_selector(self):
        """Show product selection dialog for purchase."""
        products = [
            {"id": "prod-1", "name": "Paracetamol 500mg", "unit": "pcs"},
            {"id": "prod-2", "name": "Amoxicillin 250mg", "unit": "pcs"},
            {"id": "prod-3", "name": "Omeprazole 20mg", "unit": "pcs"},
            {"id": "prod-4", "name": "Metformin 500mg", "unit": "pcs"},
            {"id": "prod-5", "name": "Atorvastatin 10mg", "unit": "pcs"},
        ]

        product_name, ok = QInputDialog_getItem(
            self, "Select Product", "Choose product:",
            [p["name"] for p in products]
        )

        if ok and product_name:
            product = next((p for p in products if p["name"] == product_name), None)
            if product:
                self.add_item_to_table(product)

    def add_item_to_table(self, product):
        """Add product to items table with batch info."""
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        # Product name
        name_item = QTableWidgetItem(product["name"])
        name_item.setData(Qt.UserRole, product["id"])
        self.items_table.setItem(row, 0, name_item)

        # Batch number
        batch_item = QTableWidgetItem("")
        batch_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 1, batch_item)

        # Manufacturing date
        mfg_item = QTableWidgetItem(QDate.currentDate().toString("yyyy-MM-dd"))
        mfg_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 2, mfg_item)

        # Expiry date
        expiry_item = QTableWidgetItem(QDate.currentDate().addYears(2).toString("yyyy-MM-dd"))
        expiry_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 3, expiry_item)

        # Quantity
        qty_item = QTableWidgetItem("0")
        qty_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 4, qty_item)

        # Unit price
        price_item = QTableWidgetItem("0.00")
        price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 5, price_item)

        # Discount
        discount_item = QTableWidgetItem("0.00")
        discount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 6, discount_item)

        # Tax
        tax_item = QTableWidgetItem("0.00")
        tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.items_table.setItem(row, 7, tax_item)

        # Total
        total_item = QTableWidgetItem("0.00")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setForeground(QColor(COLOR_SUCCESS))
        self.items_table.setItem(row, 8, total_item)

        # Actions
        remove_btn = EnterpriseButton("Remove", variant=ButtonVariant.GHOST)
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER};")
        remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))
        self.items_table.setCellWidget(row, 9, remove_btn)

        self.recalculate_totals()

    def on_item_changed(self, item):
        """Handle item change in table."""
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
        subtotal = Decimal("0")

        for row in range(self.items_table.rowCount()):
            try:
                qty = Decimal(self.items_table.item(row, 4).text() or "0")
                price = Decimal(self.items_table.item(row, 5).text() or "0")
                discount = Decimal(self.items_table.item(row, 6).text() or "0")

                line_total = qty * price - discount
                self.items_table.item(row, 8).setText(f"{line_total:.2f}")
                subtotal += line_total
            except (ValueError, TypeError, AttributeError):
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

    def get_invoice_data(self):
        """Collect all invoice data."""
        items = []
        for row in range(self.items_table.rowCount()):
            items.append({
                "product_id": self.items_table.item(row, 0).data(Qt.UserRole),
                "product_name": self.items_table.item(row, 0).text(),
                "batch_number": self.items_table.item(row, 1).text(),
                "manufacturing_date": self.items_table.item(row, 2).text(),
                "expiry_date": self.items_table.item(row, 3).text(),
                "quantity": int(self.items_table.item(row, 4).text() or 0),
                "unit_price": float(self.items_table.item(row, 5).text() or 0),
                "discount": float(self.items_table.item(row, 6).text() or 0),
                "tax": float(self.items_table.item(row, 7).text() or 0),
                "total": float(self.items_table.item(row, 8).text() or 0),
            })

        return {
            "supplier_id": self.supplier_combo.currentData(),
            "supplier_name": self.supplier_combo.currentText(),
            "invoice_number": self.invoice_number.text(),
            "order_date": self.invoice_date.date().toString("yyyy-MM-dd"),
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
            "notes": "",
            "items": items,
        }

    def update_button_states(self, status):
        """Update action button states based on purchase status."""
        is_draft = status == "DRAFT"
        is_confirmed = status == "CONFIRMED"
        is_received = status == "RECEIVED"
        
        self.save_draft_btn.setEnabled(is_draft)
        self.confirm_btn.setEnabled(is_draft)
        self.receive_btn.setEnabled(is_confirmed)
        self.print_btn.setEnabled(is_received or is_confirmed)
        self.return_btn.setVisible(is_received)
        
        if is_received:
            self.receive_btn.setText("RECEIVED")
            self.receive_btn.set_variant(ButtonVariant.SECONDARY)
        else:
            self.receive_btn.setText("Receive & Add Stock (Ctrl+R)")
            self.receive_btn.set_variant(ButtonVariant.SUCCESS)

    def save_draft(self):
        """Save purchase invoice as draft — stores invoice ID for subsequent actions."""
        data = self.get_invoice_data()
        if not data["items"]:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product.")
            return
            
        try:
            endpoint = get_endpoint("purchase_invoices")
            res = self.api_client.post(endpoint, data)
            if res:
                res_data = res.get('data', res) if isinstance(res, dict) else res
                self.current_invoice_id = res_data.get('id')
                self.invoice_number.setText(res_data.get("invoice_number", "DRAFT"))
                self.update_button_states("DRAFT")
                QMessageBox.information(self, "Success", "Purchase draft saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save draft: {e}")

    def confirm_invoice(self):
        """Confirm the purchase invoice — persists to backend."""
        data = self.get_invoice_data()
        if not data["supplier_id"]:
            QMessageBox.warning(self, "Validation Error", "Please select a supplier.")
            return
        if not self.current_invoice_id:
            QMessageBox.warning(self, "Error", "Save the invoice as draft first.")
            return

        reply = QMessageBox.question(
            self, "Confirm Invoice",
            "Are you sure you want to confirm this purchase invoice?\n\n"
            f"Total: {data['total_amount']:.2f} {data['currency']}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                endpoint = f"/api/purchases/invoices/{self.current_invoice_id}/confirm/"
                res = self.api_client.post(endpoint, {})
                if res:
                    self.status_label.setText("CONFIRMED")
                    self.status_label.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
                    self.update_button_states("CONFIRMED")
                    QMessageBox.information(self, "Success", "Purchase invoice confirmed successfully.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to confirm on server.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to confirm: {e}")

    def receive_invoice(self):
        """Receive purchase and add stock — persists to backend."""
        __data = self.get_invoice_data()
        if not self.current_invoice_id:
            QMessageBox.warning(self, "Error", "Save the invoice as draft first.")
            return
        if self.status_label.text() != "CONFIRMED":
            QMessageBox.warning(self, "Error", "Invoice must be confirmed before receiving.")
            return

        # Validate batch numbers and expiry dates
        for row in range(self.items_table.rowCount()):
            batch = self.items_table.item(row, 1).text()
            if not batch:
                QMessageBox.warning(self, "Validation Error", f"Please enter batch number for row {row + 1}.")
                return

        reply = QMessageBox.question(
            self, "Receive Purchase",
            "This will add stock to inventory.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                endpoint = f"/api/purchases/invoices/{self.current_invoice_id}/receive/"
                res = self.api_client.post(endpoint, {})
                if res:
                    self.status_label.setText("RECEIVED")
                    self.status_label.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
                    self.update_button_states("RECEIVED")
                    QMessageBox.information(self, "Success", "Purchase received and stock added to inventory.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to receive on server.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to receive: {e}")

    def print_invoice(self):
        """Print the invoice."""
        # Collect data for printing
        data = {
            "supplier_name": self.supplier_combo.currentText(),
            "phone": self.supplier_phone.text(),
            "address": self.supplier_address.toPlainText(),
            "invoice_number": self.invoice_number.text() or "DRAFT",
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "currency": self.currency_combo.currentText(),
            "subtotal": float(self.subtotal_label.text()),
            "discount": float(self.discount_input.value()),
            "tax": float(self.tax_amount_label.text()),
            "total_amount": float(self.total_label.text()),
            "paid_amount": float(self.paid_input.value()),
            "remaining_balance": float(self.balance_label.text()),
            "items": []
        }
        
        for row in range(self.items_table.rowCount()):
            data["items"].append({
                "product_name": self.items_table.item(row, 0).text(),
                "batch_number": self.items_table.item(row, 1).text(),
                "quantity": int(self.items_table.item(row, 4).text() or 0),
                "unit_price": float(self.items_table.item(row, 5).text() or 0),
                "discount": float(self.items_table.item(row, 6).text() or 0),
                "tax": float(self.items_table.item(row, 7).text() or 0),
                "total": float(self.items_table.item(row, 8).text() or 0),
            })

        dialog = PrintableInvoiceDialog(self, data, "purchase", api_client=self.api_client)
        dialog.exec()

    def create_return(self):
        """Open return dialog pre-filled with current purchase invoice data."""
        if not self.current_invoice_id:
            QMessageBox.warning(self, "No Invoice", "Please save the invoice first.")
            return
        
        try:
            from ui.returns.returns_screen import ReturnOrderDialog
            dialog = ReturnOrderDialog(self, api_client=self.api_client)
            dialog.set_invoice_type("PURCHASE_RETURN")
            dialog.prefill_from_invoice(self.current_invoice_id)
            if dialog.exec():
                QMessageBox.information(self, "Return Created", "Return order created successfully.")
        except ImportError:
            QMessageBox.warning(self, "Error", "Returns module not available.")

    def remove_selected_item(self):
        """Remove selected row from items table."""
        selected_rows = self.items_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.items_table.removeRow(index.row())
        self.recalculate_totals()

    def clear_form(self):
        """Clear the entire form."""
        self.supplier_combo.setCurrentIndex(0)
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
        self.status_label.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: white; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};")
        self.current_invoice_id = None
        self.workflow_status_label.setText("")
        self.submit_wf_btn.setVisible(True)
        self.approve_wf_btn.setVisible(False)
        self.reject_wf_btn.setVisible(False)
        self.post_wf_btn.setVisible(False)
        QMessageBox.information(self, "Cleared", "Form cleared successfully.")
    
    def load_workflow_status(self, invoice_id: int):
        """Load workflow status for current invoice."""
        if not invoice_id:
            return
        
        try:
            result = self.api_client.get_workflow_status('PURCHASE_INVOICE', invoice_id)
            if result.get('success') and result.get('data'):
                data = result['data']
                if data.get('has_workflow') is False:
                    self.workflow_status_label.setText("")
                    return
                
                state = data.get('state', 'DRAFT')
                state_display = data.get('state_display', state)
                
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
                
                self.submit_wf_btn.setVisible(data.get('can_submit', False))
                self.approve_wf_btn.setVisible(data.get('can_approve', False))
                self.reject_wf_btn.setVisible(data.get('can_approve', False))
                self.post_wf_btn.setVisible(data.get('can_post', False))
        except Exception as e:
            print(f"Error loading workflow status: {e}")
    
    def perform_workflow_action(self, action: str):
        """Perform workflow action on current invoice."""
        if not self.current_invoice_id:
            QMessageBox.warning(self, "Error", "No invoice selected.")
            return
        
        try:
            status_result = self.api_client.get_workflow_status('PURCHASE_INVOICE', self.current_invoice_id)
            if not status_result.get('success') or not status_result.get('data', {}).get('has_workflow'):
                QMessageBox.warning(self, "Error", "No workflow found for this invoice.")
                return
            
            workflow_id = status_result['data'].get('id')
            if not workflow_id:
                QMessageBox.warning(self, "Error", "Could not find workflow ID.")
                return
            
            comment = ''
            if action in ['reject']:
                from PySide6.QtWidgets import QInputDialog
                comment, ok = QInputDialog.getText(self, f"{action.title()} Reason", f"Enter reason for {action}:")
                if not ok:
                    return
            
            result = self.api_client.workflow_action(workflow_id, action, comment)
            
            if result.get('success'):
                QMessageBox.information(self, "Success", f"Invoice {action}ed successfully.")
                self.load_workflow_status(self.current_invoice_id)
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                QMessageBox.warning(self, "Error", f"Failed to {action}: {error}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error performing workflow action: {str(e)}")


def QInputDialog_getItem(parent, title, label, items):
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getItem(parent, title, label, items)
