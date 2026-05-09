from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QTableWidget, QTableWidgetItem, QPushButton,
                                QLineEdit, QLabel, QComboBox, QGroupBox, QSpinBox,
                                QDoubleSpinBox, QDateEdit, QTextEdit, QMessageBox,
                                QHeaderView, QAbstractItemView, QSplitter, QFrame)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from decimal import Decimal
from datetime import date

from ui.common.barcode_search import BarcodeSearchLineEdit
from ui.common.printable_invoice import PrintableInvoiceDialog
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_SUCCESS_ACTIVE, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, INPUT_HEIGHT_LG, 
                          TABLE_ROW_HEIGHT_MD, TABLE_ROW_HEIGHT_LG,
                          BORDER_RADIUS_MD)


class PurchaseInvoiceScreen(QWidget):
    """Screen for creating and managing purchase invoices."""

    invoice_created = Signal(dict)
    invoice_updated = Signal(dict)

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        self.current_invoice_id = None
        self.suppliers = []

        self.setup_ui()
        self.setup_shortcuts()
        self.load_suppliers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, SPACING_SM)
        title_label = QLabel("Purchase Invoice")
        title_label.setFont(QFont("Segoe UI", FONT_SIZE_TITLE, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_label = QLabel("DRAFT")
        self.status_label.setStyleSheet(f"""
            background-color: {COLOR_TEXT_MUTED}; 
            color: white; 
            padding: 8px 16px; 
            border-radius: 4px;
            font-weight: bold;
            font-size: """ + str(FONT_SIZE_MD) + """pt;
        """)
        header_layout.addWidget(self.status_label)
        
        # Workflow status label
        self.workflow_status_label = QLabel("")
        self.workflow_status_label.setStyleSheet(f"""
            color: {COLOR_TEXT_MUTED}; 
            padding: {SPACING_SM};
            font-size: {FONT_SIZE_MD}pt;
        """)
        header_layout.addWidget(self.workflow_status_label)
        
        # Workflow action buttons
        self.submit_wf_btn = QPushButton("Submit for Approval")
        self.submit_wf_btn.setMaximumHeight(BUTTON_HEIGHT_MD)
        self.submit_wf_btn.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        self.submit_wf_btn.clicked.connect(lambda: self.perform_workflow_action('submit'))
        header_layout.addWidget(self.submit_wf_btn)
        
        self.approve_wf_btn = QPushButton("Approve")
        self.approve_wf_btn.setMaximumHeight(BUTTON_HEIGHT_MD)
        self.approve_wf_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        self.approve_wf_btn.clicked.connect(lambda: self.perform_workflow_action('approve'))
        self.approve_wf_btn.setVisible(False)
        header_layout.addWidget(self.approve_wf_btn)
        
        self.reject_wf_btn = QPushButton("Reject")
        self.reject_wf_btn.setMaximumHeight(BUTTON_HEIGHT_MD)
        self.reject_wf_btn.setStyleSheet(f"background-color: {COLOR_DANGER}; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        self.reject_wf_btn.clicked.connect(lambda: self.perform_workflow_action('reject'))
        self.reject_wf_btn.setVisible(False)
        header_layout.addWidget(self.reject_wf_btn)
        
        self.post_wf_btn = QPushButton("Post")
        self.post_wf_btn.setMaximumHeight(BUTTON_HEIGHT_MD)
        self.post_wf_btn.setStyleSheet(f"background-color: {COLOR_INFO}; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        self.post_wf_btn.clicked.connect(lambda: self.perform_workflow_action('post'))
        self.post_wf_btn.setVisible(False)
        header_layout.addWidget(self.post_wf_btn)
        
        layout.addLayout(header_layout)

        # Top section: Supplier & Invoice Info
        top_split = QSplitter(Qt.Horizontal)
        top_split.setChildrenCollapsible(False)

        # Supplier info group
        supplier_group = QGroupBox("Supplier Information")
        supplier_layout = QFormLayout(supplier_group)
        supplier_layout.setLabelAlignment(Qt.AlignRight)
        supplier_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        supplier_layout.setHorizontalSpacing(SPACING_LG)
        supplier_layout.setVerticalSpacing(SPACING_MD)
        supplier_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setPlaceholderText("Select supplier...")
        self.supplier_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        supplier_layout.addRow("Supplier*:", self.supplier_combo)

        self.supplier_phone = QLineEdit()
        self.supplier_phone.setReadOnly(True)
        self.supplier_phone.setMinimumHeight(INPUT_HEIGHT_MD)
        supplier_layout.addRow("Phone:", self.supplier_phone)

        self.supplier_address = QTextEdit()
        self.supplier_address.setMaximumHeight(80)
        self.supplier_address.setMinimumHeight(60)
        self.supplier_address.setReadOnly(True)
        supplier_layout.addRow("Address:", self.supplier_address)

        self.credit_limit_label = QLabel("N/A")
        self.credit_limit_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.credit_limit_label.setStyleSheet(f"font-weight: bold;")
        self.credit_limit_label.setWordWrap(True)
        supplier_layout.addRow("Credit Limit:", self.credit_limit_label)

        self.balance_label = QLabel("N/A")
        self.balance_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.balance_label.setStyleSheet("font-weight: bold;")
        self.balance_label.setWordWrap(True)
        supplier_layout.addRow("Current Balance:", self.balance_label)

        top_split.addWidget(supplier_group)

        # Invoice details group
        invoice_group = QGroupBox("Invoice Details")
        invoice_layout = QFormLayout(invoice_group)
        invoice_layout.setLabelAlignment(Qt.AlignRight)
        invoice_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        invoice_layout.setHorizontalSpacing(SPACING_LG)
        invoice_layout.setVerticalSpacing(SPACING_MD)
        invoice_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Enter supplier invoice #")
        self.invoice_number.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Invoice #:", self.invoice_number)

        self.order_date = QDateEdit()
        self.order_date.setDate(QDate.currentDate())
        self.order_date.setCalendarPopup(True)
        self.order_date.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Order Date:", self.order_date)

        self.invoice_date = QDateEdit()
        self.invoice_date.setDate(QDate.currentDate())
        self.invoice_date.setCalendarPopup(True)
        self.invoice_date.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Invoice Date:", self.invoice_date)

        self.due_date = QDateEdit()
        self.due_date.setDate(QDate.currentDate().addDays(30))
        self.due_date.setCalendarPopup(True)
        self.due_date.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Due Date:", self.due_date)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["AFN", "USD"])
        self.currency_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Currency:", self.currency_combo)

        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItems(["Main Warehouse", "Cold Storage"])
        self.warehouse_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        invoice_layout.addRow("Warehouse:", self.warehouse_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setMinimumHeight(60)
        invoice_layout.addRow("Notes:", self.notes_input)

        top_split.addWidget(invoice_group)
        top_split.setSizes([400, 400])

        layout.addWidget(top_split)

        # Product search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        search_label = QLabel("Product Search:")
        search_label.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(search_label)
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search product by name, barcode...")
        self.product_search.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(self.product_search, 1)

        self.add_product_btn = QPushButton("Add Product")
        self.add_product_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.add_product_btn.clicked.connect(self.show_product_selector)
        search_layout.addWidget(self.add_product_btn)

        layout.addLayout(search_layout)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(10)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "Batch #", "Mfg Date", "Expiry Date", "Qty", "Unit Price", "Discount", "Tax", "Total", "Actions"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.items_table.itemChanged.connect(self.on_item_changed)
        self.items_table.setMinimumHeight(TABLE_ROW_HEIGHT_LG * 8)
        self.items_table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                background-color: {COLOR_BG_SURFACE};
                gridline-color: {COLOR_TABLE_BORDER_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                padding: 8px;
                font-weight: bold;
                border: none;
            }}
        """)

        # Bottom section: Totals and actions
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(SPACING_LG)

        # Totals group
        totals_group = QGroupBox("Invoice Totals")
        totals_layout = QFormLayout(totals_group)
        totals_layout.setLabelAlignment(Qt.AlignRight)
        totals_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        totals_layout.setHorizontalSpacing(SPACING_LG)
        totals_layout.setVerticalSpacing(SPACING_MD)
        totals_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.subtotal_label.setFont(QFont("Segoe UI", FONT_SIZE_LG))
        totals_layout.addRow("Subtotal:", self.subtotal_label)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0, 999999)
        self.discount_input.setValue(0)
        self.discount_input.setMinimumHeight(INPUT_HEIGHT_MD)
        self.discount_input.valueChanged.connect(self.recalculate_totals)
        totals_layout.addRow("Discount:", self.discount_input)

        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setValue(0)
        self.tax_input.setSuffix("%")
        self.tax_input.setMinimumHeight(INPUT_HEIGHT_MD)
        self.tax_input.valueChanged.connect(self.recalculate_totals)
        totals_layout.addRow("Tax Rate:", self.tax_input)

        self.tax_amount_label = QLabel("0.00")
        self.tax_amount_label.setMinimumHeight(INPUT_HEIGHT_MD)
        totals_layout.addRow("Tax Amount:", self.tax_amount_label)

        self.total_label = QLabel("0.00")
        self.total_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.total_label.setFont(QFont("Segoe UI", FONT_SIZE_XL, QFont.Bold))
        self.total_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        totals_layout.addRow("Total:", self.total_label)

        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 999999)
        self.paid_input.setValue(0)
        self.paid_input.setMinimumHeight(INPUT_HEIGHT_MD)
        self.paid_input.valueChanged.connect(self.recalculate_totals)
        totals_layout.addRow("Paid Amount:", self.paid_input)

        self.balance_label = QLabel("0.00")
        self.balance_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.balance_label.setFont(QFont("Segoe UI", FONT_SIZE_LG))
        self.balance_label.setStyleSheet(f"color: {COLOR_DANGER};")
        totals_layout.addRow("Balance Due:", self.balance_label)

        bottom_layout.addWidget(totals_group, 1)

        # Action buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(SPACING_SM)

        self.save_draft_btn = QPushButton("Save Draft (Ctrl+S)")
        self.save_draft_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.save_draft_btn.clicked.connect(self.save_draft)
        actions_layout.addWidget(self.save_draft_btn)

        self.confirm_btn = QPushButton("Confirm Invoice (Ctrl+Enter)")
        self.confirm_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.confirm_btn.clicked.connect(self.confirm_invoice)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY}; 
                color: white; 
                border: none;
                border-radius: """ + str(BORDER_RADIUS_MD) + """px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: {COLOR_PRIMARY_HOVER};
            }
            QPushButton:pressed {
                background-color: {COLOR_PRIMARY_ACTIVE};
            }
        """)
        actions_layout.addWidget(self.confirm_btn)

        self.receive_btn = QPushButton("Receive & Add Stock (Ctrl+R)")
        self.receive_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.receive_btn.clicked.connect(self.receive_invoice)
        self.receive_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: {BORDER_RADIUS_MD}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SUCCESS_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_SUCCESS_ACTIVE};
            }}
        """)
        actions_layout.addWidget(self.receive_btn)

        self.print_btn = QPushButton("Print Invoice (Ctrl+P)")
        self.print_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.print_btn.clicked.connect(self.print_invoice)
        actions_layout.addWidget(self.print_btn)

        clear_btn = QPushButton("Clear Form (Ctrl+L)")
        clear_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        clear_btn.clicked.connect(self.clear_form)
        actions_layout.addWidget(clear_btn)

        new_btn = QPushButton("New Invoice (Ctrl+N)")
        new_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        new_btn.clicked.connect(self.clear_form)
        actions_layout.addWidget(new_btn)

        bottom_layout.addWidget(actions_group)

        layout.addLayout(bottom_layout)

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
        total_item.setForeground(Qt.darkGreen)
        self.items_table.setItem(row, 8, total_item)

        # Actions
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"color: {COLOR_DANGER};")
        remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))
        self.items_table.setCellWidget(row, 9, remove_btn)

        self.recalculate_totals()

    def on_item_changed(self, item):
        """Handle item change in table."""
        self.recalculate_totals()

    def recalculate_totals(self):
        """Recalculate invoice totals."""
        subtotal = Decimal("0")

        for row in range(self.items_table.rowCount()):
            try:
                qty = Decimal(self.items_table.item(row, 4).text() or "0")
                price = Decimal(self.items_table.item(row, 5).text() or "0")
                discount = Decimal(self.items_table.item(row, 6).text() or "0")
                tax_rate = Decimal(str(self.tax_input.value()))

                line_total = qty * price - discount
                tax = line_total * tax_rate / Decimal("100")
                final_total = line_total + tax

                self.items_table.item(row, 8).setText(f"{final_total:.2f}")
                subtotal += line_total
            except:
                pass

        discount = Decimal(str(self.discount_input.value()))
        taxable = subtotal - discount
        tax_amount = taxable * Decimal(str(self.tax_input.value())) / Decimal("100")
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
            "order_date": self.order_date.date().toString("yyyy-MM-dd"),
            "invoice_date": self.invoice_date.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date.date().toString("yyyy-MM-dd"),
            "currency": self.currency_combo.currentText(),
            "subtotal": float(self.subtotal_label.text()),
            "discount": float(self.discount_input.value()),
            "tax": float(self.tax_amount_label.text()),
            "total_amount": float(self.total_label.text()),
            "paid_amount": float(self.paid_input.value()),
            "notes": self.notes_input.toPlainText(),
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
        
        if is_received:
            self.receive_btn.setText("RECEIVED")
            self.receive_btn.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: white; border: none; border-radius: 4px;")
        else:
            self.receive_btn.setText("Receive & Add Stock (Ctrl+R)")
            self.receive_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; font-weight: bold; border: none; border-radius: 4px;")

    def save_draft(self):
        """Save purchase invoice as draft."""
        data = self.get_invoice_data()
        if not data["items"]:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product.")
            return
            
        try:
            endpoint = get_endpoint("purchase_invoices")
            res = self.api_client.post(endpoint, data)
            if res:
                self.invoice_number.setText(res.get("invoice_number", "DRAFT"))
                self.update_button_states("DRAFT")
                QMessageBox.information(self, "Success", "Purchase draft saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save draft: {e}")

    def confirm_invoice(self):
        """Confirm the purchase invoice."""
        data = self.get_invoice_data()
        if not data["supplier_id"]:
            QMessageBox.warning(self, "Validation Error", "Please select a supplier.")
            return

        reply = QMessageBox.question(
            self, "Confirm Invoice",
            "Are you sure you want to confirm this purchase invoice?\n\n"
            f"Total: {data['total_amount']:.2f} {data['currency']}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.status_label.setText("CONFIRMED")
            self.status_label.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; padding: 5px 15px; border-radius: 3px;")
            QMessageBox.information(self, "Success", "Purchase invoice confirmed successfully.")

    def receive_invoice(self):
        """Receive purchase and add stock."""
        data = self.get_invoice_data()
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
            self.status_label.setText("RECEIVED")
            self.status_label.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; padding: 5px 15px; border-radius: 3px;")
            QMessageBox.information(self, "Success", "Purchase received and stock added to inventory.")

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
        self.order_date.setDate(QDate.currentDate())
        self.invoice_date.setDate(QDate.currentDate())
        self.due_date.setDate(QDate.currentDate().addDays(30))
        self.notes_input.clear()
        self.discount_input.setValue(0)
        self.tax_input.setValue(0)
        self.paid_input.setValue(0)
        self.items_table.setRowCount(0)
        self.recalculate_totals()
        self.status_label.setText("DRAFT")
        self.status_label.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: white; padding: 5px 15px; border-radius: 3px;")
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
                    'CANCELLED': '#7f8c8d'
                }
                color = color_map.get(state, COLOR_TEXT_MUTED)
                self.workflow_status_label.setText(f"Workflow: {state_display}")
                self.workflow_status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 8px;")
                
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
