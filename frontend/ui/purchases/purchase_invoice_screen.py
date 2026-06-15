from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QLabel, QComboBox, QDoubleSpinBox,
                                QDateEdit, QHeaderView, QAbstractItemView,
                                QFrame, QMenu, QCheckBox, QTextEdit)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from decimal import Decimal
from utils.format import safe_float

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
from ui.components.tables import DataEntryGrid
from ui.screens.base_screen import BaseScreen


class PurchaseInvoiceScreen(BaseScreen):
    """Screen for creating and managing purchase invoices.

    Phase 15C: 3-zone architecture
    ZONE 1 — Header Context (supplier, metadata, status)
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
        self.suppliers = []
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
        self.load_suppliers()
        super().load_data(params)

    def _check_action(self, action: str) -> bool:
        """Check if user has permission for a purchase action."""
        if self.auth_manager and not self.auth_manager.has_action("purchases", action):
            from ui.components.notifications import show_warning
            show_warning(f"Access denied: you don't have permission to {action} purchase invoices")
            return False
        return True

    def _setup_screen(self):
        super()._setup_screen()
        layout = self.layout() or QVBoxLayout(self)
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
        title_label = QLabel("Purchase Invoice")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_label = QLabel("DRAFT")
        self.status_label.setStyleSheet(f"""
            background-color: {COLOR_TEXT_MUTED};
            color: {COLOR_TEXT_PRIMARY};
            padding: {SPACING_XS}px {SPACING_MD}px;
            border-radius: {BORDER_RADIUS_SM}px;
            font-weight: bold;
            font-size: {TEXT_TABLE}pt;
        """)
        header_layout.addWidget(self.status_label)

        self.workflow_status_label = QLabel("")
        self.workflow_status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}pt;")
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

    def _build_toolbar(self):
        # Zone 2 vertical container shared with _build_table
        self._zone2_layout = QVBoxLayout()
        self._zone2_layout.setSpacing(SPACING_SM)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search product by name, barcode...")
        self.product_search.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(self.product_search, 1)

        self.add_product_btn = EnterpriseButton(text="+ Add Product", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        search_layout.addWidget(self.add_product_btn)

        self.remove_item_btn = EnterpriseButton(text="Remove", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        search_layout.addWidget(self.remove_item_btn)

        self._zone2_layout.addLayout(search_layout)

    def _build_table(self):
        # Items table (DataEntryGrid, compact density)
        self.items_table = DataEntryGrid([
            "Product", "Batch #", "Mfg Date", "Expiry", "Qty", "Unit Price", "Discount %", "Tax %", "Total", ""
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setMinimumHeight(TABLE_ROW_HEIGHT_LG * 8)
        self.items_table.verticalHeader().setDefaultSectionSize(DENSITY_COMPACT_ROW)

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

        # Left: Supplier details (compact)
        details_form = QFormLayout()
        details_form.setSpacing(SPACING_XS)
        details_form.setContentsMargins(0, 0, 0, 0)
        details_form.setLabelAlignment(Qt.AlignRight)

        self.supplier_phone = QLabel("—")
        self.supplier_phone.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}pt;")
        details_form.addRow("Phone:", self.supplier_phone)

        self.credit_limit_label = QLabel("—")
        self.credit_limit_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}pt;")
        details_form.addRow("Credit Limit:", self.credit_limit_label)

        self.balance_label = QLabel("0.00")
        self.balance_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_TABLE}pt; font-weight: bold;")
        details_form.addRow("Balance:", self.balance_label)

        self.supplier_address = QTextEdit()
        self.supplier_address.setReadOnly(True)
        self.supplier_address.setMaximumHeight(40)
        self.supplier_address.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}pt; border: none; background: transparent;")
        details_form.addRow("Address:", self.supplier_address)

        zone3_layout.addLayout(details_form)
        zone3_layout.addSpacing(SPACING_LG)

        # Center: Totals
        totals_layout = QFormLayout()
        totals_layout.setSpacing(SPACING_XS)
        totals_layout.setContentsMargins(0, 0, 0, 0)
        totals_layout.setLabelAlignment(Qt.AlignRight)

        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt;")
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
        self.tax_amount_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_TABLE}pt;")
        totals_layout.addRow("Tax Amt:", self.tax_amount_label)

        self.total_label = QLabel("0.00")
        self.total_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}pt; font-weight: 700;")
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
        self.notes_input.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_TABLE}pt;")
        totals_layout.addRow("Notes:", self.notes_input)

        zone3_layout.addLayout(totals_layout)
        zone3_layout.addSpacing(SPACING_LG)

        # Right: Primary action + secondary menu
        action_layout = QVBoxLayout()
        action_layout.setSpacing(SPACING_SM)
        action_layout.setContentsMargins(0, 0, 0, 0)

        self.save_btn = EnterpriseButton(text="Save Invoice", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        action_layout.addWidget(self.save_btn)

        self.confirm_btn = EnterpriseButton(text="Confirm & Receive", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
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
        self.product_search.returnPressed.connect(self._on_product_search_submit)
        self.product_search.textChanged.connect(self._on_product_search_changed)
        self.add_product_btn.clicked.connect(self.show_product_selector)
        self.remove_item_btn.clicked.connect(self.remove_selected_item)

        # Table
        self.items_table.cell_value_changed.connect(self.on_item_changed)

        # Totals
        self.discount_input.valueChanged.connect(self.recalculate_totals)
        self.tax_enabled_cb.stateChanged.connect(self.on_tax_enabled_changed)
        self.tax_input.valueChanged.connect(self.recalculate_totals)
        self.paid_input.valueChanged.connect(self.recalculate_totals)

        # Primary actions
        self.save_btn.clicked.connect(self.save_draft)
        self.confirm_btn.clicked.connect(self.receive_invoice)
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

        # Guard: connect only once (load_suppliers is called from _on_screen_shown)
        if not getattr(self, '_supplier_combo_connected', False):
            self.supplier_combo.currentIndexChanged.connect(self.on_supplier_selected)
            self._supplier_combo_connected = True

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
        products = self._fetch_products("")

        if not products:
            from ui.components.dialogs import AlertDialog
            AlertDialog.info("No Products", "No products available. Add products first.", self)
            return

        product_name, ok = QInputDialog_getItem(
            self, "Select Product", "Choose product:",
            [p.get("name", "Unknown") for p in products]
        )

        if ok and product_name:
            product = next((p for p in products if p.get("name") == product_name), None)
            if product:
                self.add_item_to_table(product)

    def _fetch_products(self, query):
        """Fetch products from backend; falls back to a small list on failure."""
        try:
            response = self.api_client.search_products(query) if query else self.api_client.get("/api/inventory/products/")
            if isinstance(response, dict):
                data = response.get("data", response)
                if isinstance(data, dict):
                    return data.get("results", [])
                if isinstance(data, list):
                    return data
            elif isinstance(response, list):
                return response
        except Exception:
            pass
        # Fallback: small dev list (Phase Recovery — replaced by real fetch in production)
        return [
            {"id": "prod-1", "name": "Paracetamol 500mg", "unit": "pcs"},
            {"id": "prod-2", "name": "Amoxicillin 250mg", "unit": "pcs"},
            {"id": "prod-3", "name": "Omeprazole 20mg", "unit": "pcs"},
            {"id": "prod-4", "name": "Metformin 500mg", "unit": "pcs"},
            {"id": "prod-5", "name": "Atorvastatin 10mg", "unit": "pcs"},
        ]

    def _on_product_search_changed(self, text):
        """Debounced live-search handler (Phase Recovery)."""
        from PySide6.QtCore import QTimer
        if not hasattr(self, "_search_timer"):
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(300)
            self._search_timer.timeout.connect(self._run_product_search)
        self._pending_query = text
        self._search_timer.start()

    def _on_product_search_submit(self):
        """Submit handler — runs search immediately and adds first match to table."""
        if hasattr(self, "_search_timer"):
            self._search_timer.stop()
        self._run_product_search(add_first_match=True)

    def _run_product_search(self, add_first_match=False):
        """Execute product search and optionally add first match to table."""
        query = getattr(self, "_pending_query", "").strip()
        if not query:
            return
        products = self._fetch_products(query)
        if add_first_match and products:
            self.add_item_to_table(products[0])
        elif products:
            self._show_search_results(products)

    def _show_search_results(self, products):
        """Display search results in a pick dialog (Phase Recovery)."""
        from ui.components.dialogs import AlertDialog
        names = "\n".join(f"  • {p.get('name', 'Unknown')}" for p in products[:20])
        AlertDialog.info(f"{len(products)} Product(s) Found", f"Search results:\n\n{names}\n\nClick '+ Add Product' to pick one.", self)

    def add_item_to_table(self, product):
        """Add product to items table with batch info."""
        self.items_table.add_row([
            product["name"],
            "",
            QDate.currentDate().toString("yyyy-MM-dd"),
            QDate.currentDate().addYears(2).toString("yyyy-MM-dd"),
            "0",
            "0.00",
            "0.00",
            "0.00",
            "0.00",
            "",
        ])

        row = self.items_table.rowCount() - 1
        self.items_table.set_row_data(row, {"product_id": product["id"]})

        remove_btn = EnterpriseButton("Remove", variant=ButtonVariant.GHOST)
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER};")
        remove_btn.clicked.connect(lambda checked, r=row: self._on_remove_row(r))
        self.items_table.set_cell_widget(row, 9, remove_btn)

        self.recalculate_totals()

    def _on_remove_row(self, row):
        self.items_table.remove_row(row)
        self.recalculate_totals()

    def on_item_changed(self, row, col, value):
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
        self.items_table.blockSignals(True)
        subtotal = Decimal("0")

        for row in range(self.items_table.rowCount()):
            try:
                values = self.items_table.get_row_values(row)
                qty = Decimal(values[4] or "0")
                price = Decimal(values[5] or "0")
                discount = Decimal(values[6] or "0")

                line_total = qty * price - discount
                values[8] = f"{line_total:.2f}"
                self.items_table.set_row_values(row, values)
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
        self.items_table.blockSignals(False)

    def get_invoice_data(self):
        """Collect all invoice data."""
        items = []
        for row in range(self.items_table.rowCount()):
            values = self.items_table.get_row_values(row)
            row_data = self.items_table.get_row_data(row)
            items.append({
                "product_id": row_data.get("product_id"),
                "product_name": values[0],
                "batch_number": values[1],
                "manufacturing_date": values[2],
                "expiry_date": values[3],
                "quantity": int(values[4] or 0),
                "unit_price": float(values[5] or 0),
                "discount": float(values[6] or 0),
                "tax": float(values[7] or 0),
                "total": float(values[8] or 0),
            })

        return {
            "supplier_id": self.supplier_combo.currentData(),
            "supplier_name": self.supplier_combo.currentText(),
            "invoice_number": self.invoice_number.text(),
            "order_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "currency": self.currency_combo.currentText(),
            "subtotal": safe_float(self.subtotal_label.text()),
            "discount": float(self.discount_input.value()),
            "tax_enabled": self.tax_enabled_cb.isChecked(),
            "tax_rate": float(self.tax_input.value()),
            "tax": safe_float(self.tax_amount_label.text()),
            "total_amount": safe_float(self.total_label.text()),
            "paid_amount": float(self.paid_input.value()),
            "notes": "",
            "items": items,
        }

    def update_button_states(self, status):
        """Update action button states based on purchase status."""
        is_draft = status == "DRAFT"
        is_received = status == "RECEIVED"

        self.save_btn.setEnabled(is_draft)
        self.confirm_btn.setEnabled(is_draft)
        self.return_btn.setVisible(is_received)

    def save_draft(self):
        """Save purchase invoice as draft — stores invoice ID for subsequent actions."""
        data = self.get_invoice_data()
        if not data["items"]:
            AlertDialog.warning("Validation Error", "Please add at least one product.", self)
            return
            
        try:
            endpoint = get_endpoint("purchase_invoices")
            res = self.api_client.post(endpoint, data)
            if res:
                res_data = res.get('data', res) if isinstance(res, dict) else res
                self.current_invoice_id = res_data.get('id')
                self.invoice_number.setText(res_data.get("invoice_number", "DRAFT"))
                self.update_button_states("DRAFT")
                AlertDialog.info("Success", "Purchase draft saved.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to save draft: {e}", self)

    def confirm_invoice(self):
        """Confirm the purchase invoice — persists to backend."""
        data = self.get_invoice_data()
        if not data["supplier_id"]:
            AlertDialog.warning("Validation Error", "Please select a supplier.", self)
            return
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "Save the invoice as draft first.", self)
            return

        if not DestructiveActionGuard.confirm_irreversible(
            self, "Confirm Invoice",
            f"Are you sure you want to confirm this purchase invoice?\n\nTotal: {data['total_amount']:.2f} {data['currency']}"
        ):
            return

        try:
            endpoint = f"/api/purchases/invoices/{self.current_invoice_id}/confirm/"
            res = self.api_client.post(endpoint, {})
            if res:
                self.status_label.setText("CONFIRMED")
                self.status_label.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px;")
                self.update_button_states("CONFIRMED")
                AlertDialog.info("Success", "Purchase invoice confirmed successfully.", self)
            else:
                AlertDialog.error("Error", "Failed to confirm on server.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to confirm: {e}", self)

    def receive_invoice(self):
        """Receive purchase and add stock — persists to backend."""
        __data = self.get_invoice_data()
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "Save the invoice as draft first.", self)
            return
        if self.status_label.text() != "CONFIRMED":
            AlertDialog.warning("Error", "Invoice must be confirmed before receiving.", self)
            return

        # Validate batch numbers and expiry dates
        for row in range(self.items_table.rowCount()):
            batch = self.items_table.get_row_values(row)[1]
            if not batch:
                AlertDialog.warning("Validation Error", f"Please enter batch number for row {row + 1}.", self)
                return

        if not DestructiveActionGuard.confirm_irreversible(
            self, "Receive Purchase",
            "This will add stock to inventory.\n\nContinue?"
        ):
            return

        try:
            endpoint = f"/api/purchases/invoices/{self.current_invoice_id}/receive/"
            res = self.api_client.post(endpoint, {})
            if res:
                self.status_label.setText("RECEIVED")
                self.status_label.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px;")
                self.update_button_states("RECEIVED")
                AlertDialog.info("Success", "Purchase received and stock added to inventory.", self)
            else:
                AlertDialog.error("Error", "Failed to receive on server.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to receive: {e}", self)

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
            "subtotal": safe_float(self.subtotal_label.text()),
            "discount": float(self.discount_input.value()),
            "tax": safe_float(self.tax_amount_label.text()),
            "total_amount": safe_float(self.total_label.text()),
            "paid_amount": float(self.paid_input.value()),
            "remaining_balance": safe_float(self.balance_label.text()),
            "items": []
        }
        
        for row in range(self.items_table.rowCount()):
            values = self.items_table.get_row_values(row)
            data["items"].append({
                "product_name": values[0],
                "batch_number": values[1],
                "quantity": int(values[4] or 0),
                "unit_price": float(values[5] or 0),
                "discount": float(values[6] or 0),
                "tax": float(values[7] or 0),
                "total": float(values[8] or 0),
            })

        dialog = PrintableInvoiceDialog(self, data, "purchase", api_client=self.api_client)
        dialog.exec()

    def create_return(self):
        """Open return dialog pre-filled with current purchase invoice data."""
        if not self.current_invoice_id:
            AlertDialog.warning("No Invoice", "Please save the invoice first.", self)
            return
        
        try:
            from ui.returns.returns_screen import ReturnOrderDialog
            dialog = ReturnOrderDialog(self, api_client=self.api_client)
            dialog.set_invoice_type("PURCHASE_RETURN")
            dialog.prefill_from_invoice(self.current_invoice_id)
            if dialog.exec():
                AlertDialog.info("Return Created", "Return order created successfully.", self)
        except ImportError:
            AlertDialog.warning("Error", "Returns module not available.", self)

    def remove_selected_item(self):
        """Remove selected row from items table."""
        selected_rows = self.items_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.items_table.remove_row(index.row())
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
        self.items_table.clear_all_rows()
        self.recalculate_totals()
        self.status_label.setText("DRAFT")
        self.status_label.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM}px;")
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
            AlertDialog.warning("Error", "No invoice selected.", self)
            return
        
        try:
            status_result = self.api_client.get_workflow_status('PURCHASE_INVOICE', self.current_invoice_id)
            if not status_result.get('success') or not status_result.get('data', {}).get('has_workflow'):
                AlertDialog.warning("Error", "No workflow found for this invoice.", self)
                return
            
            workflow_id = status_result['data'].get('id')
            if not workflow_id:
                AlertDialog.warning("Error", "Could not find workflow ID.", self)
                return
            
            comment = ''
            if action in ['reject']:
                from PySide6.QtWidgets import QInputDialog
                comment, ok = QInputDialog.getText(self, f"{action.title()} Reason", f"Enter reason for {action}:")
                if not ok:
                    return
            
            result = self.api_client.workflow_action(workflow_id, action, comment)
            
            if result.get('success'):
                AlertDialog.info("Success", f"Invoice {action}ed successfully.", self)
                self.load_workflow_status(self.current_invoice_id)
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                AlertDialog.warning("Error", f"Failed to {action}: {error}", self)
        except Exception as e:
            AlertDialog.error("Error", f"Error performing workflow action: {str(e)}", self)


def QInputDialog_getItem(parent, title, label, items):
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getItem(parent, title, label, items)
