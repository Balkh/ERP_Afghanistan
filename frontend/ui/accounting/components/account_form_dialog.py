from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QComboBox, QTextEdit, QPushButton,
                                QLabel, QMessageBox, QCheckBox, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from ui.utils.validation import FormValidator
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, BORDER_RADIUS_MD)
import re
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)


class AccountFormDialog(QDialog):
    """Dialog for creating or editing a chart of accounts entry."""

    def __init__(self, parent=None, account_id=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.account_id = account_id
        self.is_editing = account_id is not None
        self.parent_accounts = []
        self.setup_ui()
        self.load_parent_accounts()
        if self.is_editing:
            self.load_account()
            self.setWindowTitle("Edit Account")
        else:
            self.setWindowTitle("New Account")

    def setup_ui(self):
        self.setMinimumWidth(500)
        self.setMinimumHeight(550)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        title = QLabel("Edit Account" if self.is_editing else "New Account")
        title.setFont(QFont("Segoe UI", FONT_SIZE_TITLE, QFont.Bold))
        layout.addWidget(title)

        form_group = QGroupBox("Account Details")
        form_layout = QFormLayout(form_group)
        form_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        form_layout.setSpacing(SPACING_SM)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., 1010")
        self.code_input.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Code*:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Cash in Hand")
        self.name_input.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Name*:", self.name_input)

        self.type_combo = QComboBox()
        for acc_type in ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]:
            self.type_combo.addItem(acc_type, acc_type)
        self.type_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Type*:", self.type_combo)

        self.category_combo = QComboBox()
        self.category_combo.addItem("", "")
        categories = [
            ("CURRENT_ASSET", "Current Asset"),
            ("FIXED_ASSET", "Fixed Asset"),
            ("INTANGIBLE_ASSET", "Intangible Asset"),
            ("CURRENT_LIABILITY", "Current Liability"),
            ("LONG_TERM_LIABILITY", "Long Term Liability"),
            ("OWNER_EQUITY", "Owner Equity"),
            ("OPERATING_REVENUE", "Operating Revenue"),
            ("NON_OPERATING_REVENUE", "Non Operating Revenue"),
            ("COST_OF_GOODS_SOLD", "Cost of Goods Sold"),
            ("OPERATING_EXPENSE", "Operating Expense"),
            ("NON_OPERATING_EXPENSE", "Non Operating Expense"),
        ]
        for val, label in categories:
            self.category_combo.addItem(label, val)
        self.category_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Category:", self.category_combo)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (Top Level)", None)
        self.parent_combo.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Parent Account:", self.parent_combo)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(INPUT_HEIGHT_LG)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_MD)
        form_layout.addRow("Description:", self.description_input)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        form_layout.addRow("Status:", self.active_checkbox)

        layout.addWidget(form_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACING_SM)
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        save_btn.clicked.connect(self.save)

        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def load_parent_accounts(self):
        try:
            self.parent_accounts = self.api_client.get("/api/accounting/accounts/")
            if isinstance(self.parent_accounts, list):
                self.parent_combo.clear()
                self.parent_combo.addItem("None (Top Level)", None)
                for acc in sorted(self.parent_accounts, key=lambda x: x.get("code", "")):
                    self.parent_combo.addItem(f"{acc['code']} - {acc['name']}", acc["id"])
        except Exception:
            pass

    def load_account(self):
        try:
            account = self.api_client.get(f"/api/accounting/accounts/{self.account_id}/")
            self.code_input.setText(account.get("code", ""))
            self.name_input.setText(account.get("name", ""))
            self.description_input.setPlainText(account.get("description", ""))
            self.active_checkbox.setChecked(account.get("is_active", True))

            acc_type = account.get("account_type", "")
            idx = self.type_combo.findData(acc_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

            category = account.get("account_category", "") or ""
            idx = self.category_combo.findData(category)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

            parent_id = account.get("parent")
            if parent_id:
                idx = self.parent_combo.findData(parent_id)
                if idx >= 0:
                    self.parent_combo.setCurrentIndex(idx)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load account: {e}")

    def get_form_data(self):
        parent_data = self.parent_combo.currentData()
        return {
            "code": self.code_input.text().strip(),
            "name": self.name_input.text().strip(),
            "account_type": self.type_combo.currentData(),
            "account_category": self.category_combo.currentData() or None,
            "parent": parent_data if parent_data else None,
            "description": self.description_input.toPlainText().strip(),
            "is_active": self.active_checkbox.isChecked(),
        }

    def save(self):
        """Save account with validation."""
        data = self.get_form_data()
        
        # Validate form
        validator = FormValidator()
        validator.validate_required("Account Code", data["code"], "Account code is required")
        validator.validate_required("Account Name", data["name"], "Account name is required")
        validator.validate_required("Account Type", data["account_type"], "Account type is required")
        
        # Additional validation for code format (uppercase, numbers, hyphens, underscores only)
        if data["code"] and not re.match(r'^[A-Z0-9\-_]+$', data["code"]):
            validator.validate_error("Account Code", "Account code must contain only uppercase letters, numbers, hyphens, and underscores")
        
        if validator.has_errors():
            # Show all validation errors
            error_messages = "\n".join([f"• {msg}" for msg in validator.get_errors().values()])
            QMessageBox.warning(self, "Validation Error", f"Please fix the following errors:\n\n{error_messages}")
            return

        try:
            if self.is_editing:
                self.api_client.put(f"/api/accounting/accounts/{self.account_id}/", data=data)
            else:
                self.api_client.post("/api/accounting/accounts/", data=data)
            QMessageBox.information(self, "Success", "Account saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save account: {e}")
