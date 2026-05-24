from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFrame, QWidget,
                                QLineEdit, QComboBox, QTextEdit, QLabel)
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_FORM_DESCRIPTION_BG, COLOR_FORM_FOOTER_BORDER,
                           COLOR_BORDER_INPUT, COLOR_BORDER_INPUT_HOVER, BORDER_RADIUS_MD,
                           INPUT_HEIGHT_MD, DIALOG_WIDTH_FORM_MIN, DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType


class ProductFormDialog(EnterpriseDialog):
    """Enterprise product form with enhanced visual hierarchy and progressive grouping."""

    def __init__(self, parent=None, product_id=None, api_client=None):
        title = "Add Product" if product_id is None else "Edit Product"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.product_id = product_id
        self.api_client = api_client
        content = self._build_content()
        self.set_content(content)
        if product_id:
            self.load_product_data()

    def _build_content(self):
        content = QWidget()
        content.setStyleSheet("""
            QLineEdit, QComboBox {{
                background-color: {COLOR_BG_DIALOG};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER_INPUT};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM}px 10px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {COLOR_BORDER_INPUT_HOVER};
            }}
            QLineEdit:hover, QComboBox:hover {{
                border-color: {COLOR_BORDER_INPUT_HOVER};
            }}
            QTextEdit {{
                background-color: {COLOR_FORM_DESCRIPTION_BG};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER_INPUT};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM}px 10px;
            }}
            QTextEdit:focus {{
                border-color: {COLOR_BORDER_INPUT_HOVER};
            }}
        """)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Fill in the required product information")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt; border: none; background: transparent; margin-bottom: {SPACING_SM}px;")
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

        # ── Description (visually separated, full width) ──
        desc_header = QLabel("Description")
        desc_header.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt; font-weight: 600; border: none; background: transparent; margin-top: {SPACING_MD}px; margin-bottom: {SPACING_XS}px;")
        layout.addWidget(desc_header)
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter product description (optional)")
        self.description_input.setMaximumHeight(100)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_MD)
        layout.addWidget(self.description_input)

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

        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_DIALOG};
                border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
            }}
        """)
        return button_area