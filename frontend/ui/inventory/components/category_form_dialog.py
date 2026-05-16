from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFrame,
                               QLineEdit, QTextEdit, QComboBox, QLabel)
from PySide6.QtCore import Qt
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_BODY_SMALL, TEXT_LABEL,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY,
                           COLOR_BG_DIALOG, COLOR_BORDER_INPUT, COLOR_BORDER_INPUT_HOVER,
                           COLOR_FORM_DESCRIPTION_BG, COLOR_FORM_FOOTER_BORDER,
    BORDER_RADIUS_SM,
    BORDER_RADIUS_MD,
                           INPUT_HEIGHT_MD, DIALOG_WIDTH_FORM_MIN, DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection


class CategoryFormDialog(QDialog):
    """Enterprise category form with enhanced visual hierarchy."""

    def __init__(self, parent=None, category_id=None, api_client=None):
        super().__init__(parent)
        self.category_id = category_id
        self.api_client = api_client
        self.setWindowTitle("Add Category" if category_id is None else "Edit Category")
        self.setModal(True)
        self.setMinimumWidth(DIALOG_WIDTH_FORM_MIN)
        self.resize(DIALOG_WIDTH_FORM_PREFERRED, 450)
        self.setup_ui()
        if category_id:
            self.load_category_data()

    def setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_DIALOG};
            }}
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XXL, SPACING_XL, SPACING_XXL, SPACING_XL)
        layout.setSpacing(SPACING_MD)

        title = QLabel(self.windowTitle())
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 600; border: none; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("Configure category properties")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt; border: none; background: transparent; margin-bottom: {SPACING_SM}px;")
        layout.addWidget(subtitle)

        sec = FormSection("Category Details", columns=2, primary=True)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Antibiotics")
        self.active_check = QComboBox()
        self.active_check.addItems(["No", "Yes"])
        self.active_check.setCurrentIndex(1)
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter category description (optional)")
        self.description_input.setMaximumHeight(100)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_MD)
        sec.add_field_pair("Name*", self.name_input, "Is Active", self.active_check, required1=True)
        sec.add_full_width("Description", self.description_input,
                           helper="e.g., Antibiotics, Pain Relief, Vitamins — used for product classification")
        layout.addWidget(sec)

        # ── Footer with separation ──
        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.HLine)
        footer_line.setStyleSheet(f"background-color: {COLOR_FORM_FOOTER_BORDER}; border: none; max-height: 1px; margin-top: {SPACING_SM}px;")
        layout.addWidget(footer_line)

        footer = QHBoxLayout()
        footer.setSpacing(SPACING_SM)
        footer.setContentsMargins(0, SPACING_SM, 0, 0)
        footer.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.accept)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        layout.addLayout(footer)

    def load_category_data(self):
        try:
            response = self.api_client.get(f"/api/inventory/categories/{self.category_id}/")
            category = {}
            if response.get('success'):
                category = response.get('data', {})
            else:
                category = response
            if category:
                self.name_input.setText(category.get("name") or "")
                self.description_input.setPlainText(category.get("description") or "")
                self.active_check.setCurrentIndex(1 if category.get("is_active") else 0)
        except Exception as e:
            print(f"Error loading category data: {e}")

    def get_form_data(self):
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "is_active": self.active_check.currentText() == "Yes",
        }

    def accept(self):
        name = self.name_input.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Category name is required.")
            return
        data = self.get_form_data()
        try:
            if self.category_id:
                response = self.api_client.put(f"/api/inventory/categories/{self.category_id}/", data=data)
            else:
                response = self.api_client.post("/api/inventory/categories/", data=data)
            if response.get('success') or 'id' in response:
                super().accept()
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.")
                QMessageBox.critical(self, "Error", f"Failed to save category: {error_msg}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Server communication error: {e}")
