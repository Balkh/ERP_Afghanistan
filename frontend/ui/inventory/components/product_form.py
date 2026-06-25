from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFrame, QWidget,
                                QLineEdit, QComboBox, QTextEdit, QLabel)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_FORM_DESCRIPTION_BG, COLOR_FORM_FOOTER_BORDER,
                           COLOR_BORDER_INPUT, COLOR_BORDER_INPUT_HOVER, BORDER_RADIUS_MD,
                           INPUT_HEIGHT_MD, INPUT_HEIGHT_LG, DIALOG_WIDTH_FORM_MIN, DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from api.endpoints import get_endpoint, extract_list
from theme.style_builder import UIStyleBuilder


class ProductFormDialog(EnterpriseDialog):
    """Enterprise product form with enhanced visual hierarchy and progressive grouping."""

    def __init__(self, parent=None, product_id=None, api_client=None):
        title = "Add Product" if product_id is None else "Edit Product"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.setModal(True)
        self.product_id = product_id
        self.api_client = api_client
        self._submitting = False
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.accept)
        if product_id:
            self.load_product_data()

    def _build_content(self):
        content = QWidget()
        # Removed hardcoded CSS to rely on UIStyleBuilder and Global Styles
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Fill in the required product information")
        subtitle.setStyleSheet(UIStyleBuilder.get_subtitle_style())
        layout.addWidget(subtitle)

        # ── Section 1: Identity (primary) ──
        sec1 = FormSection("Identity", columns=2, primary=True)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Paracetamol 500mg")
        self.generic_name_input = QLineEdit()
        self.generic_name_input.setPlaceholderText("e.g., Paracetamol")
        self.brand_name_input = QLineEdit()
        self.brand_name_input.setPlaceholderText("e.g., Panadol")
        
        sec1.add_field_pair("Name*", self.name_input, "Generic Name", self.generic_name_input, required1=True)
        sec1.add_full_width("Brand Name", self.brand_name_input)
        layout.addWidget(sec1)

        # ── Section 2: Classification (primary) ──
        sec2 = FormSection("Classification", columns=2, primary=True)
        self.category_combo = QComboBox()
        self.category_combo.setPlaceholderText("Select category")
        self.populate_categories()
        self.unit_combo = QComboBox()
        self.unit_combo.setPlaceholderText("Select unit")
        self.populate_units()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("e.g., 123456789012")
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("e.g., PRD-001")
        
        sec2.add_field_pair("Category*", self.category_combo, "Unit*", self.unit_combo, required1=True, required2=True)
        sec2.add_field_pair("Barcode", self.barcode_input, "SKU", self.sku_input,
                            helper1="Standard formats: UPC (12-digit) or EAN-13", helper2="e.g., PRD-001, MED-042")
        layout.addWidget(sec2)

        # ── Section 3: Regulatory (secondary — visually softer) ──
        sec3 = FormSection("Regulatory", columns=2, primary=False)
        self.prescription_check = QComboBox()
        self.prescription_check.addItems(["No", "Yes"])
        self.controlled_check = QComboBox()
        self.controlled_check.addItems(["No", "Yes"])
        self.active_check = QComboBox()
        self.active_check.addItems(["No", "Yes"])
        self.active_check.setCurrentIndex(1)
        
        sec3.add_field_pair("Requires Prescription", self.prescription_check, "Controlled Substance", self.controlled_check)
        sec3.add_full_width("Is Active", self.active_check)
        layout.addWidget(sec3)

        # ── Description (organized as a section for consistency) ──
        sec_desc = FormSection("Additional Information", columns=1, primary=False)
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter product description (optional)")
        self.description_input.setMaximumHeight(120)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_LG)
        sec_desc.add_field(self.description_input, "Product Description")
        layout.addWidget(sec_desc)

        return content

    def populate_categories(self):
        if self.category_combo.count() == 0:
            self.category_combo.addItem("Select category", None)
        if not self.api_client:
            self.category_combo.addItem("General", 1)
            return

        def on_success(response):
            items = extract_list(response)
            if not items:
                items = [{"id": 1, "name": "General"}]
            for cat in items:
                name = cat.get("name", "")
                self.category_combo.addItem(name, cat.get("id"))

        def on_error(_message):
            self.category_combo.addItem("General", 1)

        self.run_api_request(
            key="product_form_categories_load",
            method="GET",
            endpoint=get_endpoint("categories"),
            on_success=on_success,
            on_error=on_error,
        )

    def populate_units(self):
        if self.unit_combo.count() == 0:
            self.unit_combo.addItem("Select unit", None)
        if not self.api_client:
            self.unit_combo.addItem("Unit", 1)
            return

        def on_success(response):
            items = extract_list(response)
            if not items:
                items = [{"id": 1, "name": "Unit"}]
            for unit in items:
                name = unit.get("name", "")
                self.unit_combo.addItem(name, unit.get("id"))

        def on_error(_message):
            self.unit_combo.addItem("Unit", 1)

        self.run_api_request(
            key="product_form_units_load",
            method="GET",
            endpoint=get_endpoint("units"),
            on_success=on_success,
            on_error=on_error,
        )

    def load_product_data(self):
        if not self.api_client or not self.product_id:
            return

        def on_success(response):
            if response and isinstance(response, dict):
                data = response.get("data", response)
            else:
                return
            self.name_input.setText(data.get("name", ""))
            self.generic_name_input.setText(data.get("generic_name", ""))
            self.brand_name_input.setText(data.get("brand_name", ""))
            self.barcode_input.setText(data.get("barcode", ""))
            self.sku_input.setText(data.get("sku", ""))
            self.description_input.setPlainText(data.get("description", ""))
            cat_id = data.get("category")
            if cat_id is not None:
                idx = self.category_combo.findData(cat_id)
                if idx >= 0:
                    self.category_combo.setCurrentIndex(idx)
            unit_id = data.get("unit")
            if unit_id is not None:
                idx = self.unit_combo.findData(unit_id)
                if idx >= 0:
                    self.unit_combo.setCurrentIndex(idx)
            self.prescription_check.setCurrentIndex(1 if data.get("requires_prescription") else 0)
            self.controlled_check.setCurrentIndex(1 if data.get("is_controlled") else 0)
            self.active_check.setCurrentIndex(1 if data.get("is_active", True) else 0)

        self.run_api_request(
            key=f"product_form_load_{self.product_id}",
            method="GET",
            endpoint=f"{get_endpoint('products')}{self.product_id}/",
            on_success=on_success,
        )

    def get_form_data(self):
        return {
            "name": self.name_input.text().strip(),
            "generic_name": self.generic_name_input.text().strip(),
            "brand_name": self.brand_name_input.text().strip(),
            "category_id": self.category_combo.currentData(),
            "unit_id": self.unit_combo.currentData(),
            "barcode": self.barcode_input.text().strip(),
            "sku": self.sku_input.text().strip(),
            "requires_prescription": self.prescription_check.currentIndex() == 1,
            "is_controlled": self.controlled_check.currentIndex() == 1,
            "is_active": self.active_check.currentIndex() == 1,
            "description": self.description_input.toPlainText().strip(),
        }

    def accept(self):
        if self._submitting:
            return
        self._submitting = True
        name = self.name_input.text().strip()
        if not name:
            AlertDialog.warning("Validation Error", "Product name is required.", self)
            self._submitting = False
            return
        data = {
            "name": name,
            "generic_name": self.generic_name_input.text().strip(),
            "brand_name": self.brand_name_input.text().strip(),
            "category": self.category_combo.currentData(),
            "unit": self.unit_combo.currentData(),
            "barcode": self.barcode_input.text().strip(),
            "sku": self.sku_input.text().strip(),
            "requires_prescription": self.prescription_check.currentIndex() == 1,
            "is_controlled": self.controlled_check.currentIndex() == 1,
            "is_active": self.active_check.currentIndex() == 1,
            "description": self.description_input.toPlainText().strip(),
        }
        endpoint = get_endpoint("products")

        def on_success(response):
            self._submitting = False
            if response and isinstance(response, dict) and (response.get("success") or response.get("id")):
                AlertDialog.info("Success", "Product saved.", self)
                super(ProductFormDialog, self).accept()
            else:
                errors = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed"
                AlertDialog.error("Error", str(errors), self)

        def on_error(message):
            self._submitting = False
            AlertDialog.error("Error", str(message), self)

        started = self.run_api_request(
            key="product_form_save",
            method="PUT" if self.product_id else "POST",
            endpoint=f"{endpoint}{self.product_id}/" if self.product_id else endpoint,
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self._submitting = False

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