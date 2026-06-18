"""Shared form infrastructure for sales and purchase invoice screens.

Extracted from SalesInvoiceScreen and PurchaseInvoiceScreen — both had
nearly identical _build_header, _build_filters, _build_toolbar, load_warehouses,
on_tax_enabled_changed, remove_selected_item, create_return, clear_form,
print_invoice, setup_shortcuts, and status-label styling methods.
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QLabel, QComboBox,
                                QDateEdit, QFrame)
from PySide6.QtCore import Qt, QDate

from ui.common.printable_invoice import PrintableInvoiceDialog
from ui.common.invoice_helpers import parse_api_list_response
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
                           MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_TABLE,
                           INPUT_HEIGHT_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG,
                           COLOR_BG_SURFACE, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_TEXT_ON_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog


class InvoiceFormMixin:
    """Mixin providing shared 3-zone form infrastructure for invoice screens.

    Subclasses **must** define:
      - ``_invoice_type``          — class attr ('SALES_INVOICE' / 'PURCHASE_INVOICE')
      - ``_entity_type``           — class attr ('customer' / 'supplier')
      - ``_entity_label``          — class attr ('Customer' / 'Supplier')
      - ``_entity_combo``          — attribute (customer_combo / supplier_combo)
      - ``_entity_items``          — attribute (customers / suppliers)
      - ``_entity_endpoint``       — class attr ('customers' / 'suppliers')
      - ``_search_widget``         — attribute (barcode_search / product_search)
      - ``_entity_selected_slot``  — callable (on_customer_selected / on_supplier_selected)
      - ``_load_entities``         — callable (load_customers / load_suppliers)
      - ``_return_type``           — class attr ('SALE_RETURN' / 'PURCHASE_RETURN')
      - ``api_client``
      - ``current_invoice_id``
      - All footer widgets (set by build_invoice_footer)

    Subclasses override:
      - ``_build_table()``         — table construction (DataEntryGrid vs QTableWidget)
      - ``_wire_signals()``        — screen-specific signal wiring
      - ``setup_shortcuts()``      — screen-specific shortcuts
      - ``recalculate_totals()``
      - ``get_invoice_data()``
    """

    _invoice_type = ''
    _entity_type = 'customer'
    _entity_label = 'Customer'
    _return_type = 'SALE_RETURN'

    # ------------------------------------------------------------------
    # Zone 1 — Header
    # ------------------------------------------------------------------

    def build_header(self, title_text=None):
        """Build the title bar with status badge."""
        title_text = title_text or f"{self._entity_label.title()} Invoice"
        layout = self.layout()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, SPACING_SM)

        title_label = QLabel(title_text)
        title_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;"
        )
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
        self.workflow_status_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;"
        )
        header_layout.addWidget(self.workflow_status_label)

        layout.addLayout(header_layout)

    # ------------------------------------------------------------------
    # Zone 1 — Filters
    # ------------------------------------------------------------------

    def build_filters(self):
        """Build the header context zone (entity combo, dates, currency, warehouse)."""
        layout = self.layout()
        zone1 = QFrame()
        zone1.setObjectName("zoneHeader")
        zone1.setStyleSheet(
            f"QFrame#zoneHeader {{ background: {COLOR_BG_SURFACE}; "
            f"border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; }}"
        )
        zone1_layout = QHBoxLayout(zone1)
        zone1_layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        zone1_layout.setSpacing(SPACING_LG)

        # Left: Entity combo + Invoice #
        left_form = QFormLayout()
        left_form.setSpacing(SPACING_SM)
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setLabelAlignment(Qt.AlignRight)
        left_form.setFormAlignment(Qt.AlignLeft)

        self._entity_combo.setPlaceholderText(f"Select {self._entity_type}...")
        self._entity_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self._entity_combo.setMinimumWidth(220)
        left_form.addRow(f"{self._entity_label}:", self._entity_combo)

        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText(f"Enter {self._entity_type} invoice #")
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
        self.warehouse_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        self.warehouse_combo.setMaximumWidth(160)
        right_form.addRow("Warehouse:", self.warehouse_combo)

        zone1_layout.addLayout(right_form)
        zone1_layout.addStretch()

        layout.addWidget(zone1)

    # ------------------------------------------------------------------
    # Zone 2 — Toolbar
    # ------------------------------------------------------------------

    def build_toolbar(self):
        """Build the search bar and add/remove buttons."""
        self._zone2_layout = QVBoxLayout()
        self._zone2_layout.setSpacing(SPACING_SM)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)

        search_widget = self._search_widget
        if hasattr(search_widget, 'setMinimumHeight'):
            search_widget.setMinimumHeight(INPUT_HEIGHT_MD)
        search_layout.addWidget(search_widget, 1)

        self.add_product_btn = EnterpriseButton(
            text="+ Add Product", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM
        )
        search_layout.addWidget(self.add_product_btn)

        self.remove_item_btn = EnterpriseButton(
            text="Remove", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM
        )
        search_layout.addWidget(self.remove_item_btn)

        self._zone2_layout.addLayout(search_layout)

    # ------------------------------------------------------------------
    # Shared actions
    # ------------------------------------------------------------------

    def load_warehouses(self):
        """Load warehouses from API into self.warehouse_combo."""
        if self.api_client:
            try:
                endpoint = get_endpoint("warehouses")
                response = self.api_client.get(endpoint)
                self.warehouses = parse_api_list_response(response)
            except Exception as e:
                print(f"Failed to load warehouses: {e}")
                self.warehouses = []

        self.warehouse_combo.clear()
        self.warehouse_combo.addItem("Select Warehouse...", None)
        for warehouse in getattr(self, 'warehouses', []):
            if isinstance(warehouse, dict):
                self.warehouse_combo.addItem(
                    warehouse.get("name", "Unknown"), warehouse.get("id", "")
                )

        # Wire entity selection after warehouse loads
        self._entity_combo.currentIndexChanged.connect(self._entity_selected_slot)

    def on_tax_enabled_changed(self, state):
        """Enable/disable tax rate input when tax toggle changes."""
        enabled = state == 2  # Qt.Checked
        self.tax_input.setEnabled(enabled)
        if not enabled:
            self.tax_input.setValue(0)
        self.recalculate_totals()

    def remove_selected_item(self):
        """Remove selected row(s) from items table."""
        selected_rows = self.items_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self._remove_row(index.row())
        self.recalculate_totals()

    def _remove_row(self, row):
        """Remove a single row — subclasses override for DataEntryGrid vs QTableWidget."""
        self.items_table.removeRow(row)

    def set_status(self, status_text, color):
        """Update the status badge text and color."""
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(
            f"background-color: {color}; color: {COLOR_TEXT_ON_PRIMARY}; "
            f"padding: {SPACING_SM}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_SM};"
        )

    def update_button_states(self, status):
        """Update action button states based on invoice status."""
        is_draft = status == "DRAFT"
        is_final = status in ("RECEIVED", "DISPATCHED")
        self.save_btn.setEnabled(is_draft)
        self.confirm_btn.setEnabled(is_draft)
        self.return_btn.setVisible(is_final)

    def create_return(self):
        """Open return dialog pre-filled with current invoice data."""
        if not self.current_invoice_id:
            AlertDialog.warning("No Invoice", "Please save the invoice first.", self)
            return

        try:
            from ui.returns.returns_screen import ReturnOrderDialog
            dialog = ReturnOrderDialog(self, api_client=self.api_client)
            dialog.set_invoice_type(self._return_type)
            dialog.prefill_from_invoice(self.current_invoice_id)
            if dialog.exec():
                AlertDialog.info("Return Created", "Return order created successfully.", self)
        except ImportError:
            AlertDialog.warning("Error", "Returns module not available.", self)

    def print_invoice(self):
        """Print the invoice using the shared printable dialog."""
        data = self.get_invoice_data()
        data["phone"] = self.entity_phone.text()
        data["address"] = self.entity_address.toPlainText()

        dialog = PrintableInvoiceDialog(
            self, data, "sale" if self._entity_type == "customer" else "purchase",
            api_client=self.api_client,
        )
        dialog.exec()
