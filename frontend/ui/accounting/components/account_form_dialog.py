import logging

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QFrame,
                                QLineEdit, QComboBox, QTextEdit, QLabel, QCheckBox)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from api.client import APIClient
from api.endpoints import extract_list
from ui.utils.validation import FormValidator
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_BORDER_INPUT,
                           COLOR_BORDER_INPUT_HOVER, COLOR_FORM_DESCRIPTION_BG, COLOR_FORM_FOOTER_BORDER,
                           INPUT_HEIGHT_MD, INPUT_HEIGHT_LG, BORDER_RADIUS_MD, DIALOG_WIDTH_FORM_MIN,
                           DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog, ConfirmDialog
from theme.style_builder import UIStyleBuilder
import re


class AccountFormDialog(EnterpriseDialog):
    """Enterprise account form with enhanced visual hierarchy."""

    def __init__(self, parent=None, account_id=None, api_client=None):
        title = "Edit Account" if account_id is not None else "New Account"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.api_client = api_client or APIClient()
        self.account_id = account_id
        self.is_editing = account_id is not None
        self.parent_accounts = []
        self._submitting = False
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)
        self.load_parent_accounts()
        if self.is_editing:
            self.load_account()

    def _build_content(self):
        content = QWidget()
        # Removed hardcoded CSS to rely on UIStyleBuilder and Global Styles
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Configure account properties")
        subtitle.setStyleSheet(UIStyleBuilder.get_subtitle_style())
        layout.addWidget(subtitle)

        # ── Section 1: Account Identity (primary) ──
        sec1 = FormSection("Account Details", columns=2, primary=True)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., 1010")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Cash in Hand")
        self.type_combo = QComboBox()
        for acc_type in ["ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"]:
            self.type_combo.addItem(acc_type, acc_type)
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
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (Top Level)", None)
        
        sec1.add_field_pair("Code*", self.code_input, "Name*", self.name_input, required1=True, required2=True,
                           helper1="Numeric code, e.g., 1010 for Cash, 4010 for Revenue")
        sec1.add_field_pair("Type*", self.type_combo, "Category", self.category_combo,
                           helper1="Determines financial statement placement")
        sec1.add_full_width("Parent Account", self.parent_combo,
                           helper="Select a parent to create a sub-account hierarchy")
        layout.addWidget(sec1)

        # ── Section 2: Additional Info (secondary) ──
        sec2 = FormSection("Additional Info", columns=2, primary=False)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(120)
        self.description_input.setMinimumHeight(INPUT_HEIGHT_LG)
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        self.active_checkbox.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        
        sec2.add_full_width("Description", self.description_input)
        
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.active_checkbox)
        status_layout.addStretch()
        
        sec2.add_full_width("Status", status_widget)
        layout.addWidget(sec2)

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
        save_btn.clicked.connect(self.save)
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        button_area.setStyleSheet(f"background-color: {COLOR_BG_DIALOG}; border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};")
        return button_area

    def load_parent_accounts(self):
        """Load parent accounts asynchronously."""
        def on_success(response):
            try:
                parents = extract_list(response)
                self.parent_accounts = parents
                self.parent_combo.clear()
                self.parent_combo.addItem("None (Top Level)", None)
                for acc in sorted(self.parent_accounts, key=lambda x: x.get("code", "")):
                    self.parent_combo.addItem(f"{acc.get('code', '')} - {acc.get('name', '')}", acc.get("id"))
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error processing parent accounts: {e}")

        def on_error(error_msg):
            logging.getLogger(__name__).warning(f"Error loading parent accounts: {error_msg}")

        self.run_api_request(
            key="parent_accounts_load",
            method="GET",
            endpoint="/api/accounting/accounts/",
            on_success=on_success,
            on_error=on_error
        )

    def load_account(self):
        """Load account data asynchronously."""
        def on_success(response):
            try:
                account = {}
                if response.get('success'):
                    account = response.get('data', {})
                else:
                    account = response
                
                if account:
                    self.name_input.setText(account.get("name", ""))
                    self.code_input.setText(account.get("code", ""))
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
                AlertDialog.error("Error", f"Error processing account data: {e}")

        def on_error(error_msg):
            AlertDialog.error("Error", f"Failed to load account: {error_msg}")

        self.run_api_request(
            key="account_detail_load",
            method="GET",
            endpoint=f"/api/accounting/accounts/{self.account_id}/",
            on_success=on_success,
            on_error=on_error
        )

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
        if self._submitting:
            return
        self._submitting = True
        data = self.get_form_data()
        validator = FormValidator()
        validator.validate_required("Account Code", data["code"], "Account code is required")
        validator.validate_required("Account Name", data["name"], "Account name is required")
        validator.validate_required("Account Type", data["account_type"], "Account type is required")
        if data["code"] and not re.match(r'^[A-Z0-9\-_]+$', data["code"]):
            validator.validate_error("Account Code", "Account code must contain only uppercase letters, numbers, hyphens, and underscores")
        if validator.has_errors():
            error_messages = "\n".join([f"\u2022 {msg}" for msg in validator.get_errors().values()])
            AlertDialog.warning("Validation Error", f"Please fix the following errors:\n\n{error_messages}", self)
            self._submitting = False
            return
        def on_success(_response):
            AlertDialog.info("Success", "Account saved successfully.", self)
            self.accept()
            self._submitting = False

        def on_error(message):
            AlertDialog.error("Error", f"Failed to save account: {message}", self)
            self._submitting = False

        endpoint = f"/api/accounting/accounts/{self.account_id}/" if self.is_editing else "/api/accounting/accounts/"
        started = self.run_api_request(
            key="account_save",
            method="PUT" if self.is_editing else "POST",
            endpoint=endpoint,
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self._submitting = False
