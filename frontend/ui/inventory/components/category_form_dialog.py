import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFrame, QWidget,
                                QLineEdit, QTextEdit, QComboBox, QLabel)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_BORDER_INPUT,
                           COLOR_BORDER_INPUT_HOVER, COLOR_FORM_DESCRIPTION_BG, COLOR_FORM_FOOTER_BORDER,
                           BORDER_RADIUS_MD, INPUT_HEIGHT_MD, INPUT_HEIGHT_LG, DIALOG_WIDTH_FORM_MIN,
                           DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from theme.style_builder import UIStyleBuilder


class CategoryFormDialog(EnterpriseDialog):
    """Enterprise category form with enhanced visual hierarchy."""

    def __init__(self, parent=None, category_id=None, api_client=None):
        title = "Add Category" if category_id is None else "Edit Category"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.category_id = category_id
        self.api_client = api_client
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.accept)
        if category_id:
            self.load_category_data()

    def _build_content(self):
        content = QWidget()
        # Removed hardcoded CSS to rely on UIStyleBuilder and Global Styles
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Configure category properties")
        subtitle.setStyleSheet(UIStyleBuilder.get_subtitle_style())
        layout.addWidget(subtitle)

        sec = FormSection("Category Details", columns=2, primary=True)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Antibiotics")
        self.active_check = QComboBox()
        self.active_check.addItems(["No", "Yes"])
        self.active_check.setCurrentIndex(1)
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter category description (optional)")
        self.description_input.setMaximumHeight(120)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_LG)
        
        sec.add_field_pair("Name*", self.name_input, "Is Active", self.active_check, required1=True)
        sec.add_full_width("Description", self.description_input,
                           helper="e.g., Antibiotics, Pain Relief, Vitamins — used for product classification")
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

    def load_category_data(self):
        def on_success(response):
            category = response.get('data', {}) if isinstance(response, dict) and response.get('success') else response
            if category:
                self.name_input.setText(category.get("name") or "")
                self.description_input.setPlainText(category.get("description") or "")
                self.active_check.setCurrentIndex(1 if category.get("is_active") else 0)

        def on_error(message):
            logging.getLogger(__name__).warning(f"Error loading category data: {message}")

        self.run_api_request(
            key=f"category_form_load_{self.category_id}",
            method="GET",
            endpoint=f"/api/inventory/categories/{self.category_id}/",
            on_success=on_success,
            on_error=on_error,
        )

    def get_form_data(self):
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "is_active": self.active_check.currentText() == "Yes",
        }

    def accept(self):
        name = self.name_input.text().strip()
        if not name:
            AlertDialog.warning("Validation Error", "Category name is required.", self)
            return
        data = self.get_form_data()

        def on_success(response):
            if isinstance(response, dict) and (response.get('success') or 'id' in response):
                super(CategoryFormDialog, self).accept()
            else:
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.") if isinstance(response, dict) else "Unknown error occurred."
                AlertDialog.error("Error", f"Failed to save category: {error_msg}", self)

        def on_error(message):
            AlertDialog.error("Error", f"Server communication error: {message}", self)

        self.run_api_request(
            key="category_form_save",
            method="PUT" if self.category_id else "POST",
            endpoint=f"/api/inventory/categories/{self.category_id}/" if self.category_id else "/api/inventory/categories/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
