"""
Pharmacy POS Screen — optimized for high-throughput cashier workflow.
Touch-friendly, keyboard-first, barcode-integrated.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QTableWidget, QTableWidgetItem, QHeaderView,
                                QLineEdit, QLabel, QComboBox,
                                QGroupBox, QFrame, QSplitter,
                                QAbstractItemView)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from decimal import Decimal
from datetime import date
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn

from ui.common.barcode_search import BarcodeSearchLineEdit as BarcodeScannerInput
from ui.common.batch_selection import BatchSelectionDialog
from ui.common.printable_invoice import PrintableInvoiceDialog
from api.endpoints import get_endpoint
from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, TEXT_PAGE_TITLE,
    TEXT_SECTION_TITLE, TEXT_CARD_TITLE,
    TEXT_TABLE, TEXT_HELPER, BUTTON_HEIGHT_MD, BUTTON_HEIGHT_LG,
    BUTTON_HEIGHT_XL, INPUT_HEIGHT_MD, INPUT_HEIGHT_LG, BORDER_RADIUS_SM, BORDER_RADIUS_MD,
    BORDER_RADIUS_LG, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
    COLOR_BORDER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_ON_SUCCESS, COLOR_TEXT_ON_WARNING,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_INFO,
    FONT_WEIGHT_BOLD, BORDER_WIDTH_HAIRLINE, BORDER_WIDTH_MEDIUM,
)
from ui.screens.base_screen import BaseScreen


class POSScreen(BaseScreen):
    """
    Pharmacy POS screen optimized for cashier workflow.

    Layout:
    ┌─────────────────────────────────────────────────────┐
    │  HEADER: Title + Status + Quick Actions             │
    ├──────────────────┬──────────────────────────────────┤
    │  LEFT PANEL      │  RIGHT PANEL                     │
    │  ┌────────────┐  │  ┌────────────────────────────┐ │
    │  │ Scan Input │  │  │ CART TABLE                 │ │
    │  └────────────┘  │  │ Product | Qty | Price | Ttl│ │
    │  ┌────────────┐  │  └────────────────────────────┘ │
    │  │ Product    │  │  ┌────────────────────────────┐ │
    │  │ Search     │  │  │ TOTALS                     │ │
    │  └────────────┘  │  │ Subtotal | Disc | Tax | Tot│ │
    │  ┌────────────┐  │  └────────────────────────────┘ │
    │  │ Customer   │  │  ┌────────────────────────────┐ │
    │  └────────────┘  │  │ PAYMENT PANEL              │ │
    │                  │  │ Cash | Card | Split | Pay  │ │
    │                  │  └────────────────────────────┘ │
    ├──────────────────┴──────────────────────────────────┤
    │  FOOTER: Keyboard shortcuts + Status bar            │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None, api_client=None, auth_manager=None):
        self.api_client = api_client
        self.auth_manager = auth_manager
        self.cart_items = []
        self.customers = []
        self.products_cache = []
        self.current_customer = None
        self._is_loading = False
        self._held_sales = []
        self._last_invoice = None
        super().__init__(parent)
        self.setup_shortcuts()
        self.scan_input.setFocus()

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        self.load_customers()
        super().load_data(params)

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        self._build_header()
        self._build_main_splitter()
        self._build_footer()

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(SPACING_LG)

        title = QLabel("Pharmacy POS")
        title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD};"
        )
        header.addWidget(title)

        self.status_label = QLabel("READY")
        self.status_label.setStyleSheet(
            f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_SUCCESS}; "
            f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
        )
        header.addWidget(self.status_label)

        header.addStretch()

        self.hold_btn = self._action_button("Hold (F6)", ButtonVariant.WARNING, self.hold_sale)
        header.addWidget(self.hold_btn)

        self.recall_btn = self._action_button("Recall (F7)", ButtonVariant.GHOST, self.recall_sale)
        header.addWidget(self.recall_btn)

        self.new_btn = self._action_button("New Sale (F2)", ButtonVariant.PRIMARY, self.new_sale)
        header.addWidget(self.new_btn)

        self.layout().addLayout(header)

    def _build_main_splitter(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self.layout().addWidget(splitter, 1)

    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._build_scan_zone())
        layout.addWidget(self._build_product_search())
        layout.addWidget(self._build_customer_zone())
        layout.addWidget(self._build_alerts_zone())
        layout.addStretch()

        return panel

    def _build_scan_zone(self):
        zone = QGroupBox("Scan Barcode")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_MEDIUM}px solid {COLOR_PRIMARY}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; color: {COLOR_PRIMARY}; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setSpacing(SPACING_SM)

        self.scan_input = BarcodeScannerInput(api_client=self.api_client)
        self.scan_input.setFixedHeight(INPUT_HEIGHT_LG)
        self.scan_input.setFont(QFont("Consolas", TEXT_CARD_TITLE))
        self.scan_input.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_MEDIUM}px solid {COLOR_PRIMARY}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_MD}px;"
        )
        self.scan_input.barcode_scanned.connect(self._on_barcode_scanned)
        self.scan_input.product_selected.connect(self._add_to_cart)
        self.scan_input.scan_error.connect(self._show_scan_error)
        zone_layout.addWidget(self.scan_input)

        self.scan_status = QLabel("")
        self.scan_status.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_HELPER}pt;")
        zone_layout.addWidget(self.scan_status)

        return zone

    def _build_product_search(self):
        zone = QGroupBox("Product Search")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setSpacing(SPACING_SM)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, generic, brand...")
        self.search_input.setFixedHeight(INPUT_HEIGHT_MD)
        self.search_input.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_MD}px;"
        )
        self.search_input.returnPressed.connect(self._search_products)
        zone_layout.addWidget(self.search_input)

        search_columns = [
            TableColumn("name", "Product", width=220),
            TableColumn("sale_price", "Price", width=90, align="right"),
            TableColumn("stock", "Stock", width=80, align="right"),
            TableColumn("action", "Action", width=100, align="center"),
        ]
        self.search_results = EnterpriseTable(search_columns, density="compact")
        self.search_results.setMaximumHeight(200)
        self.search_results.row_double_clicked.connect(self._add_search_result_to_cart)
        zone_layout.addWidget(self.search_results)

        return zone

    def _build_customer_zone(self):
        zone = QGroupBox("Customer")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setSpacing(SPACING_SM)

        customer_layout = QHBoxLayout()
        customer_layout.setSpacing(SPACING_SM)

        self.customer_combo = QComboBox()
        self.customer_combo.setFixedHeight(INPUT_HEIGHT_MD)
        self.customer_combo.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.customer_combo.addItem("Walk-in Customer", None)
        customer_layout.addWidget(self.customer_combo, 1)

        self.customer_balance_label = QLabel("Balance: 0.00 AFN")
        self.customer_balance_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        customer_layout.addWidget(self.customer_balance_label)

        zone_layout.addLayout(customer_layout)

        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)

        return zone

    def _build_alerts_zone(self):
        zone = QGroupBox("Alerts")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setSpacing(SPACING_XS)

        self.alerts_label = QLabel("No alerts")
        self.alerts_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        self.alerts_label.setWordWrap(True)
        zone_layout.addWidget(self.alerts_label)

        return zone

    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        layout.addWidget(self._build_cart_table(), 2)
        layout.addWidget(self._build_totals_panel())
        layout.addWidget(self._build_payment_panel())

        return panel

    def _build_cart_table(self):
        zone = QGroupBox("Cart")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(7)
        self.cart_table.setHorizontalHeaderLabels(["#", "Product", "Batch", "Qty", "Price", "Total", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cart_table.setAlternatingRowColors(True)
        from ui.components.tables import build_table_stylesheet
        self.cart_table.setStyleSheet(build_table_stylesheet())
        self.cart_table.cellChanged.connect(self._on_cart_cell_changed)
        zone_layout.addWidget(self.cart_table)

        return zone

    def _build_totals_panel(self):
        zone = QFrame()
        zone.setStyleSheet(
            f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER};"
        )
        zone.setFixedHeight(120)
        layout = QGridLayout(zone)
        layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        layout.setHorizontalSpacing(SPACING_XL)
        layout.setVerticalSpacing(SPACING_XS)

        totals = [
            ("Subtotal:", "subtotal", COLOR_TEXT_SECONDARY),
            ("Discount:", "discount", COLOR_TEXT_SECONDARY),
            ("Tax:", "tax", COLOR_TEXT_SECONDARY),
            ("TOTAL:", "total", COLOR_PRIMARY),
        ]

        for i, (label, key, color) in enumerate(totals):
            is_total = key == "total"
            font_size = TEXT_SECTION_TITLE if is_total else TEXT_CARD_TITLE
            weight = "700" if is_total else "600"

            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color: {color}; font-size: {font_size}pt; font-weight: {weight};"
            )
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(lbl, i, 0)

            val = QLabel("0.00 AFN")
            val.setObjectName(f"val_{key}")
            val.setStyleSheet(
                f"color: {color}; font-size: {font_size}pt; font-weight: {weight};"
            )
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(val, i, 1)

        self.totals_layout = layout
        return zone

    def _build_payment_panel(self):
        zone = QGroupBox("Payment")
        zone.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; "
            f"font-weight: {FONT_WEIGHT_BOLD}; border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: {SPACING_MD}px; padding-top: {SPACING_LG}px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
            f"padding: 0 {SPACING_SM}px; }}"
        )
        zone_layout = QVBoxLayout(zone)
        zone_layout.setSpacing(SPACING_SM)

        payment_row = QHBoxLayout()
        payment_row.setSpacing(SPACING_SM)

        # Discount & Tax inputs (Phase Recovery — POS tax/discount support)
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("Discount %")
        self.discount_input.setFixedHeight(BUTTON_HEIGHT_LG)
        self.discount_input.setFixedWidth(110)
        self.discount_input.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.discount_input.setText("0")
        self.discount_input.textChanged.connect(lambda _: self._update_totals())
        payment_row.addWidget(self.discount_input)

        self.tax_input = QLineEdit()
        self.tax_input.setPlaceholderText("Tax %")
        self.tax_input.setFixedHeight(BUTTON_HEIGHT_LG)
        self.tax_input.setFixedWidth(110)
        self.tax_input.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.tax_input.setText("0")
        self.tax_input.textChanged.connect(lambda _: self._update_totals())
        payment_row.addWidget(self.tax_input)

        self.payment_method = QComboBox()
        self.payment_method.addItems(["Cash", "Card", "Mobile", "Hawala", "Bank Transfer"])
        self.payment_method.setFixedHeight(BUTTON_HEIGHT_LG)
        self.payment_method.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};"
        )
        payment_row.addWidget(self.payment_method, 1)

        self.amount_paid_input = QLineEdit()
        self.amount_paid_input.setPlaceholderText("Amount paid")
        self.amount_paid_input.setFixedHeight(BUTTON_HEIGHT_LG)
        self.amount_paid_input.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: {BORDER_WIDTH_HAIRLINE}px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.amount_paid_input.returnPressed.connect(self._process_payment)
        payment_row.addWidget(self.amount_paid_input, 1)

        self.change_label = QLabel("Change: 0.00 AFN")
        self.change_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD};")
        payment_row.addWidget(self.change_label)

        zone_layout.addLayout(payment_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(SPACING_SM)

        self.pay_btn = self._action_button("Complete Sale (F10)", ButtonVariant.SUCCESS, self._process_payment, size="lg")
        action_row.addWidget(self.pay_btn)

        self.print_btn = self._action_button("Print (F8)", ButtonVariant.GHOST, self._print_last_invoice)
        action_row.addWidget(self.print_btn)

        self.cancel_btn = self._action_button("Cancel (Esc)", ButtonVariant.DANGER, self.new_sale)
        action_row.addWidget(self.cancel_btn)

        zone_layout.addLayout(action_row)

        return zone

    def _build_footer(self):
        footer = QHBoxLayout()
        footer.setSpacing(SPACING_XL)

        shortcuts = [
            ("F2", "New"), ("F6", "Hold"), ("F7", "Recall"),
            ("F8", "Print"), ("F10", "Pay"), ("Del", "Remove"),
        ]
        for key, action in shortcuts:
            lbl = QLabel(f"<b>{key}</b> {action}")
            lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
            footer.addWidget(lbl)

        footer.addStretch()

        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        footer.addWidget(self.item_count_label)

        self.layout().addLayout(footer)

    def _action_button(self, text, variant, callback, size="md"):
        btn = EnterpriseButton(text, variant=variant)
        height = BUTTON_HEIGHT_XL if size == "lg" else BUTTON_HEIGHT_MD
        btn.setFixedHeight(height)
        btn.setStyleSheet(
            f"font-weight: {FONT_WEIGHT_BOLD}; "
            f"border-radius: {BORDER_RADIUS_MD}; padding: 0 {SPACING_MD}px;"
        )
        btn.clicked.connect(callback)
        return btn

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_F2), self, self.new_sale)
        QShortcut(QKeySequence(Qt.Key_F6), self, self.hold_sale)
        QShortcut(QKeySequence(Qt.Key_F7), self, self.recall_sale)
        QShortcut(QKeySequence(Qt.Key_F8), self, self._print_last_invoice)
        QShortcut(QKeySequence(Qt.Key_F10), self, self._process_payment)
        QShortcut(QKeySequence(Qt.Key_Delete), self, self._remove_selected_item)

    def load_customers(self):
        try:
            endpoint = get_endpoint("customers")
            response = self.api_client.get(endpoint)
            if response and isinstance(response, dict):
                data = response.get("results", response.get("data", []))
                if isinstance(data, list):
                    self.customers = data
                    self.customer_combo.clear()
                    self.customer_combo.addItem("Walk-in Customer", None)
                    for c in data:
                        name = c.get("name", c.get("full_name", "Unknown"))
                        self.customer_combo.addItem(name, c.get("id"))
        except Exception as e:
            # Phase Recovery: surface the error instead of silently failing
            AlertDialog.error("Connection Error", f"Could not load customers: {e}", self)

    def _on_barcode_scanned(self, barcode):
        self.scan_status.setText(f"Scanning: {barcode}")
        self.scan_status.setStyleSheet(f"color: {COLOR_INFO}; font-size: {TEXT_TABLE}px;")

    def _add_to_cart(self, product):
        if not product:
            return

        product_id = product.get("id")
        product_name = product.get("name", product.get("generic_name", "Unknown"))
        sale_price = Decimal(str(product.get("sale_price", 0)))
        total_stock = product.get("total_stock", 0)
        batches = product.get("batches", [])

        if total_stock <= 0:
            self._show_alert(f"Out of stock: {product_name}", "danger")
            return

        selected_batch = None
        if len(batches) == 1:
            selected_batch = batches[0]
        elif len(batches) > 1:
            dialog = BatchSelectionDialog(self, batches, api_client=self.api_client)
            if dialog.exec():
                selected_batch = dialog.selected_batch
            else:
                return

        if not selected_batch:
            return

        batch_number = selected_batch.get("batch_number", "")
        batch_price = Decimal(str(selected_batch.get("sale_price", sale_price)))
        batch_stock = Decimal(str(selected_batch.get("remaining_quantity", 0)))

        existing = None
        for item in self.cart_items:
            if item["product_id"] == product_id and item["batch_number"] == batch_number:
                existing = item
                break

        if existing:
            if existing["quantity"] + 1 > batch_stock:
                self._show_alert(f"Insufficient stock for batch {batch_number}", "warning")
                return
            existing["quantity"] += 1
            existing["total"] = existing["quantity"] * existing["price"]
        else:
            self.cart_items.append({
                "product_id": product_id,
                "product_name": product_name,
                "batch_number": batch_number,
                "quantity": 1,
                "price": batch_price,
                "total": batch_price,
                "max_stock": batch_stock,
                "requires_prescription": product.get("requires_prescription", False),
                "is_controlled": product.get("is_controlled_substance", False),
                "expiry_date": selected_batch.get("expiry_date", ""),
            })

        self._refresh_cart()
        self.scan_input.setFocus()

        if product.get("requires_prescription"):
            self._show_alert(f"Prescription required: {product_name}", "warning")
        if product.get("is_controlled_substance"):
            self._show_alert(f"Controlled substance: {product_name} — Pharmacist approval needed", "danger")

    def _search_products(self):
        query = self.search_input.text().strip()
        if not query or not self.api_client:
            return

        try:
            response = self.api_client.search_products(query)
            if response and isinstance(response, dict):
                data = response.get("results", response.get("data", []))
                if isinstance(data, list):
                    self.products_cache = data
                    rows = []
                    for i, p in enumerate(data):
                        name = p.get("name", p.get("generic_name", "Unknown"))
                        price = float(p.get("sale_price", 0) or 0)
                        stock = p.get("quantity", p.get("total_stock", 0))
                        rows.append({
                            **p,
                            "name": name,
                            "sale_price": f"{price:.2f}",
                            "stock": str(stock),
                            "action": "Double-click",
                            "_cache_index": i,
                        })
                    self.search_results.set_data(rows)
        except Exception as e:
            # Phase Recovery: surface the error instead of silently failing
            AlertDialog.error("Search Failed", f"Product search failed: {e}", self)

    def _add_search_result_to_cart(self, row, data=None):
        if data is None:
            data = self.search_results.get_row_data(row) if hasattr(self.search_results, "get_row_data") else None
        if data:
            product = dict(data)
            product["total_stock"] = product.get("quantity", product.get("total_stock", 0))
            product["batches"] = product.get("batches", [])
            self._add_to_cart(product)

    def _add_search_result_to_cart_by_index(self, index):
        if 0 <= index < len(self.products_cache):
            product = self.products_cache[index]
            product["total_stock"] = product.get("quantity", product.get("total_stock", 0))
            product["batches"] = product.get("batches", [])
            self._add_to_cart(product)

    def _refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart_items))
        for i, item in enumerate(self.cart_items):
            self.cart_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.cart_table.setItem(i, 1, QTableWidgetItem(item["product_name"]))
            self.cart_table.setItem(i, 2, QTableWidgetItem(item["batch_number"]))

            qty_item = QTableWidgetItem(str(item["quantity"]))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.cart_table.setItem(i, 3, qty_item)

            self.cart_table.setItem(i, 4, QTableWidgetItem(f"{item['price']:.2f}"))
            self.cart_table.setItem(i, 5, QTableWidgetItem(f"{item['total']:.2f}"))

            remove_btn = EnterpriseButton("✕", variant=ButtonVariant.DANGER)
            remove_btn.setFixedWidth(28)
            remove_btn.clicked.connect(lambda checked, idx=i: self._remove_item(idx))
            self.cart_table.setCellWidget(i, 6, remove_btn)

        self._update_totals()
        self.item_count_label.setText(f"Items: {len(self.cart_items)}")

    def _on_cart_cell_changed(self, row, col):
        if col == 3 and 0 <= row < len(self.cart_items):
            item = self.cart_items[row]
            try:
                new_qty = int(self.cart_table.item(row, col).text())
                if new_qty < 1:
                    new_qty = 1
                if new_qty > item["max_stock"]:
                    new_qty = item["max_stock"]
                    self._show_alert(f"Max stock: {item['max_stock']}", "warning")
                item["quantity"] = new_qty
                item["total"] = item["quantity"] * item["price"]
                self._refresh_cart()
            except ValueError:
                pass

    def _update_totals(self):
        subtotal = sum(item["total"] for item in self.cart_items)
        # Phase Recovery: read discount % and tax % from inputs (default 0)
        try:
            discount_pct = Decimal(self.discount_input.text() or "0") if hasattr(self, "discount_input") else Decimal("0")
        except Exception:
            discount_pct = Decimal("0")
        try:
            tax_pct = Decimal(self.tax_input.text() or "0") if hasattr(self, "tax_input") else Decimal("0")
        except Exception:
            tax_pct = Decimal("0")
        discount = subtotal * discount_pct / Decimal("100")
        taxable = subtotal - discount
        tax = taxable * tax_pct / Decimal("100")
        total = taxable + tax

        self._set_total("subtotal", subtotal)
        self._set_total("discount", discount)
        self._set_total("tax", tax)
        self._set_total("total", total)

        self._update_change_label()

    def _set_total(self, key, value):
        widget = self.findChild(QLabel, f"val_{key}")
        if widget:
            widget.setText(f"{value:.2f} AFN")

    def _update_change_label(self):
        total = sum(item["total"] for item in self.cart_items)
        try:
            paid = Decimal(self.amount_paid_input.text() or "0")
            change = paid - total
            self.change_label.setText(f"Change: {change:.2f} AFN")
            if change < 0:
                self.change_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_CARD_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD};")
            else:
                self.change_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD};")
        except Exception:
            self.change_label.setText("Change: 0.00 AFN")

    def _on_customer_changed(self, index):
        customer_id = self.customer_combo.itemData(index)
        if customer_id:
            for c in self.customers:
                if str(c.get("id")) == str(customer_id):
                    self.current_customer = c
                    balance = c.get("balance", 0)
                    self.customer_balance_label.setText(f"Balance: {balance:.2f} AFN")
                    return
        else:
            self.current_customer = None
            self.customer_balance_label.setText("Balance: 0.00 AFN")

    def _process_payment(self):
        if not self.cart_items:
            AlertDialog.warning("Empty Cart", "Add items to the cart before completing the sale.", self)
            return

        total = sum(item["total"] for item in self.cart_items)
        try:
            paid = Decimal(self.amount_paid_input.text() or str(total))
        except Exception:
            paid = total

        if paid < total:
            AlertDialog.warning("Insufficient Payment", f"Total: {total:.2f} AFN, Paid: {paid:.2f} AFN", self)
            return

        self.status_label.setText("PROCESSING...")
        self.status_label.setStyleSheet(
            f"background-color: {COLOR_WARNING}; color: {COLOR_TEXT_ON_WARNING}; "
            f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
        )

        try:
            customer_id = self.current_customer.get("id") if self.current_customer else None
            endpoint = get_endpoint("sales_invoices")

            invoice_data = {
                "customer": customer_id,
                "invoice_date": date.today().isoformat(),
                "due_date": date.today().isoformat(),
                "items": [],
                "payment_method": self.payment_method.currentText().lower(),
                "amount_paid": str(paid),
                "discount_percent": str(self.discount_input.text() or "0") if hasattr(self, "discount_input") else "0",
                "tax_percent": str(self.tax_input.text() or "0") if hasattr(self, "tax_input") else "0",
            }

            for item in self.cart_items:
                invoice_data["items"].append({
                    "product": item["product_id"],
                    "quantity": str(item["quantity"]),
                    "batch_number": item["batch_number"],
                    "unit_price": str(item["price"]),
                })

            response = self.api_client.post(endpoint, invoice_data)
            if response and response.get("success"):
                invoice = response.get("data", response)
                self.status_label.setText("COMPLETED")
                self.status_label.setStyleSheet(
                    f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_SUCCESS}; "
                    f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
                    f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
                )
                self._show_invoice_preview(invoice)
                self.new_sale()
            else:
                error = response.get("error", "Unknown error") if response else "No response"
                self.status_label.setText("FAILED")
                self.status_label.setStyleSheet(
                    f"background-color: {COLOR_DANGER}; color: {COLOR_TEXT_ON_PRIMARY}; "
                    f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
                    f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
                )
        except Exception as e:
            self.status_label.setText("ERROR")
            self.status_label.setStyleSheet(
                f"background-color: {COLOR_DANGER}; color: {COLOR_TEXT_ON_PRIMARY}; "
                f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
                f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
            )

    def _show_invoice_preview(self, invoice):
        self._last_invoice = invoice
        try:
            dialog = PrintableInvoiceDialog(
                self,
                invoice_data=invoice,
                invoice_type="sale",
                api_client=self.api_client,
            )
            dialog.exec()
        except Exception:
            pass

    def _print_last_invoice(self):
        """Print the last completed invoice."""
        if not self._last_invoice:
            from ui.components.dialogs import AlertDialog
            AlertDialog.warning("No Invoice", "No invoice to print. Complete a sale first.", self)
            return
        try:
            from ui.common.printable_invoice import PrintableInvoiceDialog
            dialog = PrintableInvoiceDialog(
                invoice=self._last_invoice,
                invoice_type="sale",
                api_client=self.api_client,
            )
            dialog.exec()
        except Exception as e:
            from ui.components.dialogs import AlertDialog
            AlertDialog.error("Print Error", f"Failed to print invoice: {e}", self)

    def new_sale(self):
        self.cart_items = []
        self.current_customer = None
        self.customer_combo.setCurrentIndex(0)
        self.amount_paid_input.clear()
        self.scan_input.clear()
        self.search_input.clear()
        self.search_results.set_data([])
        self._refresh_cart()
        self.scan_status.setText("")
        self.alerts_label.setText("No alerts")
        self.alerts_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        self.status_label.setText("READY")
        self.status_label.setStyleSheet(
            f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_SUCCESS}; "
            f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
        )
        self.scan_input.setFocus()

    def hold_sale(self):
        """Hold the current sale for later recall."""
        if not self.cart_items:
            return
        held = {
            "cart_items": list(self.cart_items),
            "customer": self.current_customer,
            "customer_index": self.customer_combo.currentIndex(),
        }
        self._held_sales.append(held)
        self.new_sale()
        self.status_label.setText(f"SALE HELD ({len(self._held_sales)} held)")
        self.status_label.setStyleSheet(
            f"background-color: {COLOR_WARNING}; color: {COLOR_TEXT_ON_PRIMARY}; "
            f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
        )

    def recall_sale(self):
        """Recall the last held sale."""
        if not self._held_sales:
            from ui.components.dialogs import AlertDialog
            AlertDialog.info("No Held Sales", "No held sales to recall.", self)
            return
        held = self._held_sales.pop()
        self.cart_items = held["cart_items"]
        self.current_customer = held["customer"]
        idx = held.get("customer_index", 0)
        if idx < self.customer_combo.count():
            self.customer_combo.setCurrentIndex(idx)
        self._refresh_cart()
        self.status_label.setText("READY")
        self.status_label.setStyleSheet(
            f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_SUCCESS}; "
            f"padding: {SPACING_XS}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_SM}; "
            f"font-weight: {FONT_WEIGHT_BOLD}; font-size: {TEXT_TABLE}px;"
        )

    def _remove_selected_item(self):
        row = self.cart_table.currentRow()
        if row >= 0:
            self._remove_item(row)

    def _remove_item(self, index):
        if 0 <= index < len(self.cart_items):
            self.cart_items.pop(index)
            self._refresh_cart()
            self.scan_input.setFocus()

    def _show_scan_error(self, message):
        self.scan_status.setText(message)
        self.scan_status.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_TABLE}px;")
        QTimer.singleShot(3000, lambda: self.scan_status.setText(""))

    def _show_alert(self, message, level="info"):
        color = {
            "warning": COLOR_WARNING,
            "danger": COLOR_DANGER,
            "success": COLOR_SUCCESS,
        }.get(level, COLOR_INFO)
        self.alerts_label.setText(message)
        self.alerts_label.setStyleSheet(f"color: {color}; font-size: {TEXT_TABLE}px; font-weight: {FONT_WEIGHT_BOLD};")
