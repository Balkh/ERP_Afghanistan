"""Customer add/edit dialog with Individual/Company support."""

import uuid

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QComboBox, QTextEdit, QFrame,
                                QFormLayout, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection
from ui.components.form_helpers import make_field as _make_field


class CustomerDialog(EnterpriseDialog):
    """Customer add/edit dialog with Individual/Company support."""

    def __init__(self, api_client=None, customer=None):
        self.api_client = api_client
        self.customer = customer
        self._is_submitting = False
        title = "Add Customer" if not customer else "Edit Customer"
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
        subtype_layout.addWidget(QLabel("Customer Type:"))
        self.subtype_combo = QComboBox()
        self.subtype_combo.addItems(["Individual", "Company"])
        self.subtype_combo.setMinimumWidth(180)
        subtype_layout.addWidget(self.subtype_combo)
        subtype_layout.addStretch()
        layout.addLayout(subtype_layout)
        self.subtype_combo.currentIndexChanged.connect(
            lambda: self.on_subtype_changed(self.subtype_combo.currentText()))

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
        self.national_id = _make_field("National ID")

        # Company fields
        self.company_name = _make_field("Company Name")
        self.company_name.setVisible(False)
        self.registration_number = _make_field("Registration Number")
        self.registration_number.setVisible(False)
        self.business_license = _make_field("Business License (جواز فعالیت)")
        self.business_license.setVisible(False)

        # Common fields
        self.phone = _make_field("Phone Number")
        self.email = _make_field("Email Address")

        self.address = QTextEdit()
        self.address.setPlaceholderText("Address")
        self.address.setMinimumHeight(INPUT_HEIGHT_MD)
        self.address.setMaximumHeight(120)

        self.city = _make_field("City")

        # Contact person (for companies)
        self.contact_person = _make_field("Contact Person Name")
        self.contact_role = _make_field("Contact Person Role")
        self.contact_phone = _make_field("Contact Person Phone")
        self.contact_email = _make_field("Contact Person Email")

        # Financial fields
        self.credit_limit = _make_field("Credit Limit")
        self.payment_terms = _make_field("Payment Terms (days)")
        self.tax_number = _make_field("Tax Number")

        # Individual section
        form_layout.addRow("First Name*:", self.first_name)
        form_layout.addRow("Last Name*:", self.last_name)
        form_layout.addRow("National ID:", self.national_id)

        # Company section
        form_layout.addRow("Company Name*:", self.company_name)
        form_layout.addRow("Registration #:", self.registration_number)
        form_layout.addRow("Business License*:", self.business_license)

        # Common
        form_layout.addRow("Phone*:", self.phone)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Address:", self.address)
        form_layout.addRow("City:", self.city)

        # Contact person section
        contact_section = FormSection("Contact Person (for companies)")
        contact_section.add_field(self.contact_person, "Name:")
        contact_section.add_field(self.contact_role, "Role:")
        contact_section.add_field(self.contact_phone, "Phone:")
        contact_section.add_field(self.contact_email, "Email:")
        form_layout.addRow(contact_section)

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

        self.btn_cancel = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_cancel.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = EnterpriseButton("Save Customer", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.btn_save.clicked.connect(self.save)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)

        layout.addLayout(buttons_layout)

        # Load existing data if editing
        if self.customer:
            self._load_customer_data()

        return widget

    def on_subtype_changed(self, subtype):
        """Show/hide fields based on subtype."""
        is_individual = subtype == "Individual"
        self.first_name.setVisible(True)
        self.last_name.setVisible(True)
        self.national_id.setVisible(True)
        self.company_name.setVisible(not is_individual)
        self.registration_number.setVisible(not is_individual)
        self.business_license.setVisible(not is_individual)

    def _load_customer_data(self):
        """Load existing customer data into form fields."""
        if not self.customer:
            return
        self.subtype_combo.setCurrentText(self.customer.get('subtype', 'Individual'))
        if self.customer.get('subtype') == 'INDIVIDUAL':
            self.first_name.setText(self.customer.get('first_name', ''))
            self.last_name.setText(self.customer.get('last_name', ''))
            self.national_id.setText(self.customer.get('national_id', ''))
        else:
            self.company_name.setText(self.customer.get('company_name', ''))
            self.registration_number.setText(self.customer.get('registration_number', ''))
            self.business_license.setText(self.customer.get('business_license', ''))
        self.phone.setText(self.customer.get('phone', ''))
        self.email.setText(self.customer.get('email', ''))
        self.address.setText(self.customer.get('address', ''))
        self.city.setText(self.customer.get('city', ''))
        self.contact_person.setText(self.customer.get('contact_person', ''))
        self.contact_role.setText(self.customer.get('contact_role', ''))
        self.contact_phone.setText(self.customer.get('contact_phone', ''))
        self.contact_email.setText(self.customer.get('contact_email', ''))
        self.credit_limit.setText(str(self.customer.get('credit_limit', '0')))
        self.payment_terms.setText(str(self.customer.get('payment_terms_days', '0')))
        self.tax_number.setText(self.customer.get('tax_number', ''))

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
                "national_id": self.national_id.text().strip(),
            }
        else:
            data = {
                "subtype": subtype,
                "company_name": self.company_name.text().strip(),
                "name": self.company_name.text().strip(),
                "registration_number": self.registration_number.text().strip(),
                "business_license": self.business_license.text().strip(),
            }
        data.update({
            "code": f"CUST-{uuid.uuid4().hex[:8].upper()}",
            "phone": self.phone.text().strip(),
            "email": self.email.text().strip(),
            "address": self.address.toPlainText().strip(),
            "city": self.city.text().strip(),
            "contact_person": self.contact_person.text().strip(),
            "contact_role": self.contact_role.text().strip(),
            "contact_phone": self.contact_phone.text().strip(),
            "contact_email": self.contact_email.text().strip(),
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
                errors.append("First name is required for individual customers")
            if not self.last_name.text().strip():
                errors.append("Last name is required for individual customers")
        else:
            if not self.company_name.text().strip():
                errors.append("Company name is required for company customers")
            if not self.business_license.text().strip():
                errors.append("Business license is required for company customers")
        if not self.phone.text().strip():
            errors.append("Phone number is required")
        return errors

    def save(self):
        """Save customer with validation."""
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
            self.btn_save.setText("Save Customer")
            AlertDialog.warning("Validation Error", "\n".join(validation_errors), self)
            return

        endpoint = get_endpoint("customers")
        if self.api_client:
            try:
                response = self.api_client.post(endpoint, data)
                if response and isinstance(response, dict):
                    if response.get("success") or response.get("id"):
                        AlertDialog.info("Success", "Customer saved successfully.", self)
                        self.accept()
                        return
                    error_msg = response.get("error", {}).get("message", "Failed to save customer") if isinstance(response, dict) else "Failed to save customer"
                    AlertDialog.warning("Error", error_msg, self)
                else:
                    AlertDialog.warning("Error", "Failed to save customer", self)
            except Exception as e:
                AlertDialog.warning("Error", f"Failed to save: {e}", self)
        else:
            AlertDialog.info("Success", "Customer saved successfully (offline mode).", self)
            self.accept()

        # Reset button state on failure
        self._is_submitting = False
        self.btn_save.setEnabled(True)
        self.btn_save.setText("Save Customer")
