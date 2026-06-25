import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFrame, QWidget,
                                QLineEdit, QComboBox, QDateEdit, QSpinBox, QLabel)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QDate, Qt
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_BORDER_INPUT,
                           COLOR_BORDER_INPUT_HOVER, COLOR_FORM_FOOTER_BORDER, BORDER_RADIUS_MD,
                           DIALOG_WIDTH_FORM_MIN, DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from theme.style_builder import UIStyleBuilder


class BatchFormDialog(EnterpriseDialog):
    """Enterprise batch form with enhanced visual hierarchy."""

    def __init__(self, parent=None, batch_id=None, api_client=None):
        title = "Add Batch" if batch_id is None else "Edit Batch"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.batch_id = batch_id
        self.api_client = api_client
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.accept)
        if batch_id:
            self.load_batch_data()

    def _build_content(self):
        content = QWidget()

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Configure batch properties")
        subtitle.setStyleSheet(UIStyleBuilder.get_subtitle_style())
        layout.addWidget(subtitle)

        sec = FormSection("Batch Details", columns=2, primary=True)
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select product")
        self.populate_products()
        self.batch_number_input = QLineEdit()
        self.batch_number_input.setPlaceholderText("e.g., BATCH-2024-001")
        self.expiry_date_input = QDateEdit()
        self.expiry_date_input.setCalendarPopup(True)
        self.expiry_date_input.setDate(QDate.currentDate().addYears(1))
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 999999)
        self.quantity_input.setValue(0)
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setPlaceholderText("Select warehouse")
        self.populate_warehouses()
        sec.add_field_pair("Product*", self.product_combo, "Batch Number*", self.batch_number_input, required1=True, required2=True,
                           helper2="Supplier-assigned batch number or internal reference")
        sec.add_field_pair("Expiry Date*", self.expiry_date_input, "Quantity", self.quantity_input,
                           helper1="Used for shelf-life tracking and alerts")
        sec.add_full_width("Warehouse*", self.warehouse_combo, required=True)
        layout.addWidget(sec)

        return content

    def _create_button_area(self):
        button_area = QFrame()
        button_area.setFixedHeight(60)

        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(SPACING_XXL, SPACING_SM, SPACING_XXL, SPACING_SM)

        layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        button_area.setObjectName("card")
        button_area.setStyleSheet(UIStyleBuilder.get_card_style())
        return button_area

    def populate_products(self):
        self.product_combo.addItem("Select Product", None)

        def on_success(response):
            products = []
            if isinstance(response, list):
                products = response
            elif isinstance(response, dict):
                products = response.get('results', []) or response.get('data', [])
            for p in products:
                if isinstance(p, dict):
                    self.product_combo.addItem(p.get('name'), p.get('id'))

        def on_error(message):
            logging.getLogger(__name__).warning(f"Error fetching products: {message}")

        self.run_api_request(
            key="batch_form_products_load",
            method="GET",
            endpoint="/api/inventory/products/",
            on_success=on_success,
            on_error=on_error,
        )

    def populate_warehouses(self):
        self.warehouse_combo.addItem("Select Warehouse", None)

        def on_success(response):
            warehouses = []
            if isinstance(response, list):
                warehouses = response
            elif isinstance(response, dict):
                warehouses = response.get('results', []) or response.get('data', [])
            for w in warehouses:
                if isinstance(w, dict):
                    self.warehouse_combo.addItem(w.get('name'), w.get('id'))

        def on_error(message):
            logging.getLogger(__name__).warning(f"Error fetching warehouses: {message}")

        self.run_api_request(
            key="batch_form_warehouses_load",
            method="GET",
            endpoint="/api/inventory/warehouses/",
            on_success=on_success,
            on_error=on_error,
        )

    def load_batch_data(self):
        def on_success(response):
            if not response:
                return
            batch = response.get('data') if isinstance(response, dict) and response.get('success') else response
            if batch:
                self.batch_number_input.setText(batch.get("batch_number") or "")
                exp = batch.get("expiry_date")
                if exp:
                    self.expiry_date_input.setDate(QDate.fromString(exp, "yyyy-MM-dd"))
                self.quantity_input.setValue(int(batch.get("quantity", 0)))
                prod_id = batch.get("product")
                idx = self.product_combo.findData(prod_id)
                if idx >= 0:
                    self.product_combo.setCurrentIndex(idx)
                wh_id = batch.get("warehouse")
                idx = self.warehouse_combo.findData(wh_id)
                if idx >= 0:
                    self.warehouse_combo.setCurrentIndex(idx)

        def on_error(message):
            logging.getLogger(__name__).warning(f"Error loading batch data: {message}")

        self.run_api_request(
            key=f"batch_form_load_{self.batch_id}",
            method="GET",
            endpoint=f"/api/inventory/batches/{self.batch_id}/",
            on_success=on_success,
            on_error=on_error,
        )

    def get_form_data(self):
        return {
            "product": self.product_combo.currentData(),
            "batch_number": self.batch_number_input.text().strip(),
            "expiry_date": self.expiry_date_input.date().toString("yyyy-MM-dd"),
            "quantity": self.quantity_input.value(),
            "warehouse": self.warehouse_combo.currentData(),
        }

    def accept(self):
        if self.product_combo.currentData() is None:
            AlertDialog.warning("Validation Error", "Please select a product.", self)
            return
        if not self.batch_number_input.text().strip():
            AlertDialog.warning("Validation Error", "Batch number is required.", self)
            return
        if self.warehouse_combo.currentData() is None:
            AlertDialog.warning("Validation Error", "Please select a warehouse.", self)
            return
        data = self.get_form_data()

        def on_success(response):
            if isinstance(response, dict) and (response.get('success') or 'id' in response):
                super(BatchFormDialog, self).accept()
            else:
                AlertDialog.error("Error", "Failed to save batch.", self)

        def on_error(message):
            AlertDialog.error("Error", f"Server error: {message}", self)

        self.run_api_request(
            key="batch_form_save",
            method="PUT" if self.batch_id else "POST",
            endpoint=f"/api/inventory/batches/{self.batch_id}/" if self.batch_id else "/api/inventory/batches/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
