"""Return order creation dialog."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit, QComboBox, QGroupBox,
                                QTextEdit, QHeaderView, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.constants import (MARGIN_PAGE, SPACING_SM, SPACING_MD, SPACING_LG,
                           TEXT_SECTION_TITLE, TEXT_BODY, BORDER_RADIUS_MD,
                           BORDER_RADIUS_LG, COLOR_BG_INPUT, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TITLE,
                           COLOR_BORDER_DIALOG, COLOR_BORDER_INPUT, COLOR_PRIMARY, FONT_NAME_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, EnterpriseDialog, DialogType
from ui.components.forms import FormSection
from ui.components.tables import DataEntryGrid


class ReturnOrderDialog(EnterpriseDialog):
    """Dialog for creating return orders with line-item entry."""

    def __init__(self, api_client=None, parent=None):
        self.api_client = api_client
        self._invoice_data = None
        self._items = []
        super().__init__("New Return Order", DialogType.CUSTOM, parent)
        self.setMinimumWidth(750)
        self.setMinimumHeight(600)
        self._build_content()

    def _create_button_area(self):
        return None

    def set_invoice_type(self, return_type):
        """Pre-select return type (SALE_RETURN or PURCHASE_RETURN)."""
        idx = 0 if return_type == "SALE_RETURN" else 1
        self.return_type_cb.setCurrentIndex(idx)

    def prefill_from_invoice(self, invoice_id):
        """Load invoice data and pre-fill return items."""
        if not self.api_client:
            return
        try:
            is_sale = self.return_type_cb.currentText() == "Sale Return"
            endpoint = f"/api/sales/invoices/{invoice_id}/" if is_sale else f"/api/purchases/invoices/{invoice_id}/"
            resp = self.api_client.get(endpoint)
            if resp and isinstance(resp, dict):
                data = resp.get("data", resp)
                self._invoice_data = data
                self._items = data.get("items", [])
                self._populate_items()
        except Exception:
            pass

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        title = QLabel("Create Return Order")
        title.setFont(QFont(FONT_NAME_PRIMARY, TEXT_SECTION_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_TITLE};")
        layout.addWidget(title)

        section = FormSection("Return Header", primary=True)

        self.return_type_cb = QComboBox()
        self.return_type_cb.addItems(["Sale Return", "Purchase Return"])
        self.return_type_cb.currentIndexChanged.connect(self._on_type_change)
        section.add_field(self.return_type_cb, "Return Type*:")

        self.invoice_search = QLineEdit()
        self.invoice_search.setPlaceholderText("Search invoice by number, customer, or supplier...")
        self.invoice_search.setMinimumHeight(30)
        self.invoice_search.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: 1px solid {COLOR_BORDER_INPUT}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.invoice_search.returnPressed.connect(self._load_invoice)
        section.add_field(self.invoice_search, "Invoice:")

        self.party_label = QLabel("Party: —")
        self.party_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        section.add_field(self.party_label, "")

        self.invoice_total_label = QLabel("Invoice Total: —")
        self.invoice_total_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        section.add_field(self.invoice_total_label, "")

        self.reason = QTextEdit()
        self.reason.setPlaceholderText("Enter reason for return...")
        self.reason.setMaximumHeight(60)
        section.add_field(self.reason, "Reason*:")

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Additional internal notes...")
        self.notes.setMaximumHeight(60)
        section.add_field(self.notes, "Notes:")

        layout.addWidget(section)

        items_group = QGroupBox("Return Items")
        items_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {COLOR_BORDER_DIALOG}; "
            f"border-radius: {BORDER_RADIUS_LG}; margin-top: {SPACING_LG}px; padding-top: {SPACING_LG}px; }}"
        )
        items_layout = QVBoxLayout(items_group)

        self.items_table = DataEntryGrid(
            ["Product", "Sold Qty", "To Return", "Unit Price", "Discount", "Tax", "Total"]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 7):
            self.items_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setMinimumHeight(150)
        self.items_table.cell_value_changed.connect(self._on_cell_changed)
        items_layout.addWidget(self.items_table)

        self.summary_label = QLabel("Refund Preview: 0.00 AFN")
        self.summary_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; font-size: {TEXT_BODY}pt;")
        items_layout.addWidget(self.summary_label)

        layout.addWidget(items_group)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)

        save_btn = EnterpriseButton(text="Save Return", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.save)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        self.set_content(widget)
        return widget

    def _on_type_change(self):
        self._invoice_data = None
        self._items = []
        self.items_table.clear_all_rows()
        self.party_label.setText("Party: —")
        self.invoice_total_label.setText("Invoice Total: —")
        self.summary_label.setText("Refund Preview: 0.00 AFN")

    def _load_invoice(self):
        query = self.invoice_search.text().strip()
        if not query or not self.api_client:
            return
        try:
            is_sale = self.return_type_cb.currentIndex() == 0
            endpoint = "/api/sales/invoices/" if is_sale else "/api/purchases/invoices/"
            response = self.api_client.get(endpoint, params={"search": query})
            if response and isinstance(response, dict):
                invoices = response.get("results", [])
                if not invoices:
                    invoices = [response] if response.get("id") else []
                if invoices:
                    self._invoice_data = invoices[0]
                    self._populate_items()
                else:
                    AlertDialog.warning("Not Found", f"No invoice found matching '{query}'", self)
        except Exception:
            pass

    def _populate_items(self):
        inv = self._invoice_data
        if not inv:
            return

        self.party_label.setText(f"Party: {inv.get('customer_name', inv.get('supplier_name', 'N/A'))}")
        self.invoice_total_label.setText(f"Invoice Total: {inv.get('total_amount', 0):.2f} AFN")

        items = inv.get("items", [])
        self._items = []
        self.items_table.clear_all_rows()

        for i, item in enumerate(items):
            product_name = item.get("product_name", "Unknown")
            sold_qty = float(item.get("quantity", 0))
            unit_price = float(item.get("unit_price", 0))
            discount = float(item.get("discount", 0))
            tax = float(item.get("tax", 0))

            self._items.append({
                "product": item.get("product"),
                "product_name": product_name,
                "quantity": 0,
                "unit_price": unit_price,
                "discount_amount": discount,
                "tax_amount": tax,
                "max_qty": sold_qty,
            })

            self.items_table.add_row([
                product_name,
                str(int(sold_qty)),
                "0",
                f"{unit_price:.2f}",
                f"{discount:.2f}",
                f"{tax:.2f}",
                "0.00",
            ])

    def _on_cell_changed(self, row, col, value):
        if col != 2 or row >= len(self._items):
            return
        try:
            qty = int(value or "0")
            max_qty = int(self._items[row]["max_qty"])
            if qty < 0:
                qty = 0
            if qty > max_qty:
                qty = max_qty
            self._items[row]["quantity"] = qty

            up = self._items[row]["unit_price"]
            disc = self._items[row]["discount_amount"]
            tax = self._items[row]["tax_amount"]
            ratio = qty / max_qty if max_qty > 0 else 0
            total = (qty * up) - (disc * ratio) + (tax * ratio)

            current = list(self.items_table.get_row_values(row))
            current[6] = f"{total:.2f}"
            self.items_table.set_row_values(row, current)

            refund_total = sum(
                (it["quantity"] * it["unit_price"])
                - (it["discount_amount"] * (it["quantity"] / it["max_qty"] if it["max_qty"] > 0 else 0))
                + (it["tax_amount"] * (it["quantity"] / it["max_qty"] if it["max_qty"] > 0 else 0))
                for it in self._items
            )
            self.summary_label.setText(f"Refund Preview: {refund_total:.2f} AFN")
        except (ValueError, ZeroDivisionError):
            pass

    def save(self):
        if not self.reason.toPlainText().strip():
            AlertDialog.warning("Validation Error", "Reason is required.", self)
            return

        items_to_return = [it for it in self._items if it["quantity"] > 0]
        if not items_to_return:
            AlertDialog.warning("Validation Error", "At least one item must have a return quantity > 0.", self)
            return

        is_sale = self.return_type_cb.currentIndex() == 0
        data = {
            "return_type": "SALE_RETURN" if is_sale else "PURCHASE_RETURN",
            "reason": self.reason.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
            "status": "PENDING",
            "items": [],
        }

        if self._invoice_data:
            data["invoice"] = self._invoice_data.get("id") if is_sale else None
            data["purchase_invoice"] = self._invoice_data.get("id") if not is_sale else None
            data["party"] = self._invoice_data.get("customer", self._invoice_data.get("customer_id"))
            data["supplier"] = self._invoice_data.get("supplier", self._invoice_data.get("supplier_id"))

        total_amount = 0.0
        for it in items_to_return:
            max_qty = it["max_qty"]
            ratio = it["quantity"] / max_qty if max_qty > 0 else 0
            prorated_discount = it["discount_amount"] * ratio
            prorated_tax = it["tax_amount"] * ratio
            item_total = (it["quantity"] * it["unit_price"]) - prorated_discount + prorated_tax
            total_amount += item_total

            data["items"].append({
                "product": it["product"],
                "return_quantity": it["quantity"],
                "unit_price": it["unit_price"],
                "discount_amount": prorated_discount,
                "tax_amount": prorated_tax,
            })

        data["total_amount"] = round(total_amount, 2)

        try:
            if self.api_client:
                response = self.api_client.post("/api/returns/return-orders/", data)
            else:
                import uuid
                response = {
                    "success": True,
                    "data": {
                        "return_number": f"RET-{uuid.uuid4().hex[:8].upper()}",
                        "items_count": len(data["items"]),
                    }
                }

            if response and (response.get("success") or "id" in response):
                AlertDialog.info("Success",
                    f"Return created with {len(data['items'])} item(s)\n"
                    f"Total: {data['total_amount']:.2f} AFN",
                    self
                )
                self.accept()
            else:
                err = response.get("error", "Unknown error") if response else "No response"
                AlertDialog.error("Error", f"Failed to create return: {err}", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to create return: {e}", self)
