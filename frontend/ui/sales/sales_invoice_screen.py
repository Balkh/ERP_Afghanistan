from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QTableWidget, QTableWidgetItem, QPushButton,
                                QLineEdit, QLabel, QComboBox, QGroupBox, QSpinBox,
                                QDoubleSpinBox, QDateEdit, QTextEdit, QMessageBox,
                                QHeaderView, QAbstractItemView, QSplitter, QFrame,
                                QDialog)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QKeySequence, QIcon, QShortcut
from decimal import Decimal
from datetime import date

from ui.common.batch_selection import BatchSelectionDialog
from ui.common.barcode_search import BarcodeSearchLineEdit
from ui.common.printable_invoice import PrintableInvoiceDialog
from api.endpoints import get_endpoint
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          SPACING_XS, SPACING_XXL, MARGIN_PAGE,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, INPUT_HEIGHT_LG,
                          TABLE_ROW_HEIGHT_MD, TABLE_ROW_HEIGHT_LG,
                          BORDER_RADIUS_MD,
                          COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                          COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY,
                          COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                          COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                          COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_SUCCESS_ACTIVE,
                          COLOR_WARNING, COLOR_DANGER,
                          COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class SalesInvoiceScreen(QWidget):
    """Screen for creating and managing sales invoices."""

    # Signals
    invoice_created = Signal(dict)
    invoice_updated = Signal(dict)

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        self.invoice_items = []
        self.current_invoice_id = None
        self.customers = []
        self.products = []

        self.setup_ui()
        self.setup_shortcuts()
        self.load_customers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, SPACING_SM)
        title_label = QLabel("Sales Invoice")
        title_label.setFont(QFont("Segoe UI", FONT_SIZE_TITLE, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

# Status badge
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
        self.workflow_status_label.setStyleSheet("""
            color: #666; 
            padding: 8px;
            font-size: """ + str(FONT_SIZE_MD) + """pt;
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

        # Top section: Customer & Invoice Info
        top_split = QSplitter(Qt.Horizontal)
        top_split.setChildrenCollapsible(False)

        # Customer info group
        customer_group = QGroupBox("Customer Information")
        customer_layout = QFormLayout(customer_group)
        customer_layout.setLabelAlignment(Qt.AlignRight)
        customer_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        customer_layout.setHorizontalSpacing(SPACING_LG)
        customer_layout.setVerticalSpacing(SPACING_MD)
        customer_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.customer_combo = QComboBox()
        self.customer_combo.setPlaceholderText("Select customer...")
        self.customer_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        customer_layout.addRow("Customer*:", self.customer_combo)

        self.customer_phone = QLineEdit()
        self.customer_phone.setReadOnly(True)
        self.customer_phone.setMinimumHeight(INPUT_HEIGHT_MD)
        customer_layout.addRow("Phone:", self.customer_phone)

        self.customer_address = QTextEdit()
        self.customer_address.setMaximumHeight(80)
        self.customer_address.setMinimumHeight(60)
        self.customer_address.setReadOnly(True)
        customer_layout.addRow("Address:", self.customer_address)

        self.credit_limit_label = QLabel("N/A")
        self.credit_limit_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.credit_limit_label.setStyleSheet(f"font-weight: bold;")
        self.credit_limit_label.setWordWrap(True)
        customer_layout.addRow("Credit Limit:", self.credit_limit_label)

        self.balance_label = QLabel("N/A")
        self.balance_label.setMinimumHeight(INPUT_HEIGHT_MD)
        self.balance_label.setStyleSheet("font-weight: bold;")
        self.balance_label.setWordWrap(True)
        customer_layout.addRow("Current Balance:", self.balance_label)

        top_split.addWidget(customer_group)

        # Invoice details group
        invoice_group = QGroupBox("Invoice Details")
        invoice_layout = QFormLayout(invoice_group)
        invoice_layout.setLabelAlignment(Qt.AlignRight)
        invoice_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        invoice_layout.setHorizontalSpacing(SPACING_LG)
        invoice_layout.setVerticalSpacing(SPACING_MD)
        invoice_layout.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)

        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Auto-generated")
        self.invoice_number.setReadOnly(True)
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

        # Middle section: Barcode search and items table
        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        search_label = QLabel("Barcode / Product Search:")
        search_label.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(search_label)
        self.barcode_search = BarcodeSearchLineEdit(api_client=self.api_client)
        self.barcode_search.barcode_scanned.connect(self.on_barcode_scanned)
        self.barcode_search.product_selected.connect(self.on_product_selected)
        self.barcode_search.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(self.barcode_search, 1)

        self.add_product_btn = QPushButton("Add Product")
        self.add_product_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.add_product_btn.clicked.connect(self.show_product_selector)
        search_layout.addWidget(self.add_product_btn)

        layout.addLayout(search_layout)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(9)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "Batch", "Qty", "Unit Price", "Discount", "Tax", "Total", "Actions", ""
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

        # Add remove button to header
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_item)
        remove_btn.setStyleSheet(f"background-color: {COLOR_DANGER}; color: white;")

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

        self.dispatch_btn = QPushButton("Dispatch & Deduct Stock (Ctrl+D)")
        self.dispatch_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.dispatch_btn.clicked.connect(self.dispatch_invoice)
        self.dispatch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS}; 
                color: white; 
                border: none;
                border-radius: """ + str(BORDER_RADIUS_MD) + """px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: {COLOR_SUCCESS_HOVER};
            }
            QPushButton:pressed {
                background-color: {COLOR_SUCCESS_ACTIVE};
            }
        """)
        actions_layout.addWidget(self.dispatch_btn)

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
        pass

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
        batch_btn = QPushButton("Select Batch")
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
        total_item.setForeground(Qt.darkGreen)
        self.items_table.setItem(row, 6, total_item)

        # Actions
        remove_btn = QPushButton("Remove")
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
        row = item.row()
        self.recalculate_totals()

    def recalculate_totals(self):
        """Recalculate invoice totals."""
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
                tax_rate = Decimal(str(self.tax_input.value()))

                line_total = qty * price - discount
                tax = line_total * tax_rate / Decimal("100")
                final_total = line_total + tax

                total_item.setText(f"{final_total:.2f}")
                subtotal += line_total
            except (Exception, Decimal.InvalidOperation):
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
        """Update action button states based on invoice status."""
        is_draft = status == "DRAFT"
        is_confirmed = status == "CONFIRMED"
        is_dispatched = status == "DISPATCHED"
        
        self.save_draft_btn.setEnabled(is_draft)
        self.confirm_btn.setEnabled(is_draft)
        self.dispatch_btn.setEnabled(is_confirmed)
        self.print_btn.setEnabled(is_dispatched or is_confirmed)
        
        # Style updates
        if is_dispatched:
            self.dispatch_btn.setText("DISPATCHED")
            self.dispatch_btn.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; color: white; border: none; border-radius: 4px;")
        else:
            self.dispatch_btn.setText("Dispatch & Deduct Stock (Ctrl+D)")
            self.dispatch_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; font-weight: bold; border: none; border-radius: 4px;")

    def save_draft(self):
        """Save invoice as draft."""
        data = self.get_invoice_data()
        if not data["items"]:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product.")
            return
            
        try:
            endpoint = get_endpoint("sales_invoices")
            res = self.api_client.post(endpoint, data)
            if res:
                self.invoice_number.setText(res.get("invoice_number", "DRAFT"))
                self.update_button_states("DRAFT")
                QMessageBox.information(self, "Success", "Invoice saved as draft.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save draft: {e}")

    def confirm_invoice(self):
        """Confirm the invoice."""
        data = self.get_invoice_data()
        if not data["customer_id"]:
            QMessageBox.warning(self, "Validation Error", "Please select a customer.")
            return

        reply = QMessageBox.question(
            self, "Confirm Invoice",
            "Are you sure you want to confirm this invoice?\n\n"
            f"Total: {data['total_amount']:.2f} {data['currency']}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.status_label.setText("CONFIRMED")
            self.status_label.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; padding: 5px 15px; border-radius: 3px;")
            QMessageBox.information(self, "Success", "Invoice confirmed successfully.")

    def dispatch_invoice(self):
        """Dispatch invoice and deduct stock."""
        data = self.get_invoice_data()
        if self.status_label.text() != "CONFIRMED":
            QMessageBox.warning(self, "Error", "Invoice must be confirmed before dispatch.")
            return

        reply = QMessageBox.question(
            self, "Dispatch Invoice",
            "This will deduct stock from inventory.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.status_label.setText("DISPATCHED")
            self.status_label.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; padding: 5px 15px; border-radius: 3px;")
            QMessageBox.information(self, "Success", "Invoice dispatched and stock deducted.")

    def print_invoice(self):
        """Print the invoice."""
        data = self.get_invoice_data()
        data["phone"] = self.customer_phone.text()
        data["address"] = self.customer_address.toPlainText()

        dialog = PrintableInvoiceDialog(self, data, "sale", api_client=self.api_client)
        dialog.exec()

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
                    'CANCELLED': '#7f8c8d'
                }
                color = color_map.get(state, COLOR_TEXT_MUTED)
                self.workflow_status_label.setText(f"Workflow: {state_display}")
                self.workflow_status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 8px;")
                
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
            QMessageBox.warning(self, "Error", "No invoice selected.")
            return
        
        # Get workflow for this invoice
        try:
            status_result = self.api_client.get_workflow_status('SALES_INVOICE', self.current_invoice_id)
            if not status_result.get('success') or not status_result.get('data', {}).get('has_workflow'):
                QMessageBox.warning(self, "Error", "No workflow found for this invoice.")
                return
            
            workflow_id = status_result['data'].get('id')
            if not workflow_id:
                QMessageBox.warning(self, "Error", "Could not find workflow ID.")
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
                QMessageBox.information(self, "Success", f"Invoice {action}ed successfully.")
                # Reload workflow status
                self.load_workflow_status(self.current_invoice_id)
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                QMessageBox.warning(self, "Error", f"Failed to {action}: {error}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error performing workflow action: {str(e)}")


# Helper for QInputDialog (since we can't import it directly in some setups)
def QInputDialog_getItem(parent, title, label, items):
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getItem(parent, title, label, items)
