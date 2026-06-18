"""Supplier add/edit dialog with full form features."""

import uuid

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QSpinBox, QFormLayout, QComboBox,
                                QTextEdit, QFrame, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD,
                           INPUT_HEIGHT_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection
from ui.components.form_helpers import make_field as _make_field


class SupplierDialog(EnterpriseDialog):
    """Supplier add/edit dialog with full features."""

    def __init__(self, api_client=None, supplier=None):
        self.api_client = api_client
        self.supplier = supplier
        self._is_submitting = False
        title = "Add Supplier" if not supplier else "Edit Supplier"
        super().__init__(title, DialogType.CUSTOM, None)
        self.resize(550, 650)
        self.setMinimumHeight(650)
        self.setMaximumHeight(750)
        self._build_content()
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        # Subtype selection
        subtype_layout = QHBoxLayout()
        subtype_layout.addWidget(QLabel("Supplier Type:"))
        self.subtype_combo = QComboBox()
        self.subtype_combo.addItems(["Individual", "Company"])
        self.subtype_combo.setMinimumWidth(180)
        subtype_layout.addWidget(self.subtype_combo)
        subtype_layout.addStretch()
        layout.addLayout(subtype_layout)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        form = QFrame()
        form.setStyleSheet("QFrame { background-color: transparent; }")
        form_layout = QFormLayout(form)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setSpacing(SPACING_SM)

        # Individual fields
        self.first_name = _make_field("First Name")
        self.last_name = _make_field("Last Name")

        # Company fields
        self.company_name = _make_field("Company Name")
        self.company_name.setVisible(False)
        self.registration_number = _make_field("Registration Number")
        self.registration_number.setVisible(False)

        # Common fields
        self.phone = _make_field("Phone Number")
        self.email = _make_field("Email Address")

        self.address = QTextEdit()
        self.address.setPlaceholderText("Address")
        self.address.setMinimumHeight(INPUT_HEIGHT_MD)
        self.address.setMaximumHeight(120)

        self.city = _make_field("City")
        self.supply_categories = _make_field("Supply Categories (e.g., Medicines, Medical Devices)")

        # Contact person
        self.contact_person = _make_field("Contact Person Name")
        self.contact_role = _make_field("Contact Person Role")
        self.contact_phone = _make_field("Contact Person Phone")
        self.contact_email = _make_field("Contact Person Email")

        # Bank details
        self.bank_name = _make_field("Bank Name")
        self.bank_account = _make_field("Bank Account Number")
        self.iban = _make_field("IBAN")
        self.swift_code = _make_field("SWIFT Code")

        # Business terms
        self.delivery_terms = _make_field("Delivery Terms (e.g., FOB, CIF)")
        self.lead_time = _make_field("Lead Time (days)")
        self.minimum_order = _make_field("Minimum Order Value")

        # Quality rating
        self.quality_rating = QSpinBox()
        self.quality_rating.setMinimum(0)
        self.quality_rating.setMaximum(5)
        self.quality_rating.setMinimumHeight(INPUT_HEIGHT_MD)

        # Financial
        self.credit_limit = _make_field("Credit Limit")
        self.payment_terms = _make_field("Payment Terms (days)")
        self.tax_number = _make_field("Tax Number")

        # Add to form layout
        form_layout.addRow("First Name*:", self.first_name)
        form_layout.addRow("Last Name*:", self.last_name)
        form_layout.addRow("Company Name*:", self.company_name)
        form_layout.addRow("Registration #: ", self.registration_number)
        form_layout.addRow("Phone*:", self.phone)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Address:", self.address)
        form_layout.addRow("City:", self.city)
        form_layout.addRow("Supply Categories*:", self.supply_categories)

        # Bank details section
        bank_section = FormSection("Bank Details")
        bank_section.add_field(self.bank_name, "Bank Name:")
        bank_section.add_field(self.bank_account, "Account #:")
        bank_section.add_field(self.iban, "IBAN:")
        bank_section.add_field(self.swift_code, "SWIFT:")
        form_layout.addRow(bank_section)

        # Contact section
        contact_section = FormSection("Contact Person")
        contact_section.add_field(self.contact_person, "Name:")
        contact_section.add_field(self.contact_role, "Role:")
        contact_section.add_field(self.contact_phone, "Phone:")
        contact_section.add_field(self.contact_email, "Email:")
        form_layout.addRow(contact_section)

        # Business terms section
        terms_section = FormSection("Business Terms")
        terms_section.add_field(self.delivery_terms, "Delivery Terms:")
        terms_section.add_field(self.lead_time, "Lead Time (days):")
        terms_section.add_field(self.minimum_order, "Min Order Value:")
        terms_section.add_field(self.quality_rating, "Quality Rating (0-5):")
        form_layout.addRow(terms_section)

        # Financial section
        financial_section = FormSection("Financial Details")
        financial_section.add_field(self.credit_limit, "Credit Limit:")
        financial_section.add_field(self.payment_terms, "Payment Terms (days):")
        financial_section.add_field(self.tax_number, "Tax Number:")
        form_layout.addRow(financial_section)

        scroll.setWidget(form)
        layout.addWidget(scroll)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACING_SM + SPACING_XS)

        self.btn_cancel = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.LARGE)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = EnterpriseButton("Save Supplier", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.btn_save.clicked.connect(self.save)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)

        layout.addLayout(buttons_layout)

        self.subtype_combo.currentTextChanged.connect(self.on_subtype_changed)

        return widget

    def on_subtype_changed(self, subtype):
        """Show/hide fields based on subtype."""
        is_individual = subtype == "Individual"
        self.first_name.setVisible(True)
        self.last_name.setVisible(True)
        self.company_name.setVisible(not is_individual)
        self.registration_number.setVisible(not is_individual)

    def _collect_data(self):
        """Collect form data into a dict."""
        subtype = "INDIVIDUAL" if self.subtype_combo.currentText() == "Individual" else "COMPANY"

        if subtype == "INDIVIDUAL":
            name = f"{self.first_name.text().strip()} {self.last_name.text().strip()}"
            data = {
                "subtype": subtype,
                "first_name": self.first_name.text().strip(),
                "last_name": self.last_name.text().strip(),
                "name": name,
            }
        else:
            data = {
                "subtype": subtype,
                "company_name": self.company_name.text().strip(),
                "name": self.company_name.text().strip(),
                "registration_number": self.registration_number.text().strip(),
            }

        data.update({
            "code": f"SUP-{uuid.uuid4().hex[:8].upper()}",
            "phone": self.phone.text().strip(),
            "email": self.email.text().strip(),
            "address": self.address.toPlainText().strip(),
            "city": self.city.text().strip(),
            "supply_categories": self.supply_categories.text().strip(),
            "contact_person": self.contact_person.text().strip(),
            "contact_role": self.contact_role.text().strip(),
            "contact_phone": self.contact_phone.text().strip(),
            "contact_email": self.contact_email.text().strip(),
            "bank_name": self.bank_name.text().strip(),
            "bank_account": self.bank_account.text().strip(),
            "iban": self.iban.text().strip(),
            "swift_code": self.swift_code.text().strip(),
            "delivery_terms": self.delivery_terms.text().strip(),
            "lead_time_days": self.lead_time.text().strip() or "0",
            "minimum_order_value": self.minimum_order.text().strip() or "0",
            "quality_rating": str(self.quality_rating.value()),
            "credit_limit": self.credit_limit.text().strip() or "0",
            "payment_terms_days": self.payment_terms.text().strip() or "0",
            "tax_number": self.tax_number.text().strip(),
            "status": "ACTIVE",
        })
        return subtype, data

    def _validate(self, subtype):
        """Validate form fields. Returns list of error messages."""
        errors = []
        if subtype == "INDIVIDUAL":
            if not self.first_name.text().strip():
                errors.append("First name is required for individual suppliers")
            if not self.last_name.text().strip():
                errors.append("Last name is required for individual suppliers")
        else:
            if not self.company_name.text().strip():
                errors.append("Company name is required for company suppliers")
        if not self.supply_categories.text().strip():
            errors.append("Supply categories are required")
        if not self.phone.text().strip():
            errors.append("Phone number is required")
        return errors

    def save(self):
        """Save supplier with validation."""
        if self._is_submitting:
            return
        self._is_submitting = True
        self.btn_save.setEnabled(False)
        self.btn_save.setText("Saving...")

        subtype, data = self._collect_data()

        validation_errors = self._validate(subtype)
        if validation_errors:
            self._is_submitting = False
            self.btn_save.setEnabled(True)
            self.btn_save.setText("Save Supplier")
            AlertDialog.warning("Validation Error", "\n".join(validation_errors), self)
            return

        endpoint = get_endpoint("suppliers")
        if self.api_client:
            try:
                response = self.api_client.post(endpoint, data)
                if response and isinstance(response, dict):
                    if response.get("success") or response.get("id"):
                        AlertDialog.info("Success", "Supplier saved successfully.", self)
                        self.accept()
                        return
                    error_msg = response.get("error", {}).get("message", "Failed to save supplier") if isinstance(response, dict) else "Failed to save supplier"
                    AlertDialog.warning("Error", error_msg, self)
                else:
                    AlertDialog.warning("Error", "Failed to save supplier", self)
            except Exception as e:
                AlertDialog.warning("Error", f"Failed to save: {e}", self)
        else:
            AlertDialog.info("Success", "Supplier saved successfully (offline mode).", self)
            self.accept()

        # Reset button state on failure
        self._is_submitting = False
        self.btn_save.setEnabled(True)
        self.btn_save.setText("Save Supplier")
