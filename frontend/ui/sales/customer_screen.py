"""Customers screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QMessageBox, QFormLayout, QGroupBox, QDialog,
                                   QTextEdit, QComboBox, QFrame)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from utils.cache import cached
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


class CustomerScreen(BaseScreen):
    """Customers management screen."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="customer_screen")
        self.api_client = api_client
        self.customers = []
        self.setup_ui()
        self.load_customers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, SPACING_SM)
        title = QLabel("Customers")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        add_btn = EnterpriseButton(text="Add Customer", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        add_btn.clicked.connect(self.add_customer)
        header.addWidget(add_btn)

        refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self.load_customers)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search customers...")
        self.search_box.setMinimumHeight(INPUT_HEIGHT_MD)
        self.search_box.textChanged.connect(self.filter_customers)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Loading indicator
        self.loading_label = QLabel("Loading customers...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic; font-size: {TEXT_BODY}pt; padding: {SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Error indicator
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_MD}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Empty state indicator
        self.empty_label = QLabel("No customers found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic; font-size: {TEXT_BODY}pt; padding: {SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("name", "Name", width=200),
            TableColumn("phone", "Phone", width=120),
            TableColumn("email", "Email", width=200),
            TableColumn("address", "Address", width=250),
        ]
        self.table = EnterpriseTable(columns)
        self.table.setMinimumHeight(TABLE_ROW_HEIGHT_MD * 5)
        self.table.setVisible(False)
        layout.addWidget(self.table)

    @cached(ttl=30.0)  # Cache for 30 seconds
    def _fetch_customers(self):
        """Fetch customers from API (cached)."""
        # Check if we're in development mode (no auth token)
        import os
        dev_mode = os.path.exists('DEVELOPMENT') or os.environ.get('PHARMACY_ERP_DEVELOPMENT', '').lower() in ('true', '1', 'yes')
        
        endpoint = get_endpoint("customers")
        
        # Return mock data in development mode or if no API client
        if dev_mode or not self.api_client:
            # Mock data for development
            return [
                {"id": "1", "name": "Test Customer", "phone": "1234567890", "email": "test@example.com", "address": "Test Address"},
                {"id": "2", "name": "John Smith", "phone": "9876543210", "email": "john@example.com", "address": "123 Main St"},
                {"id": "3", "name": "Alice Johnson", "phone": "5551234567", "email": "alice@example.com", "address": "456 Oak Ave"},
                {"id": "4", "name": "Bob Williams", "phone": "5559876543", "email": "bob@example.com", "address": "789 Pine Rd"},
            ]
        
        try:
            response = self.api_client.get(endpoint)
            customers = []
            if isinstance(response, dict):
                if response.get('success'):
                    data = response.get('data', [])
                    if isinstance(data, list):
                        customers = [c for c in data if isinstance(c, dict)]
                    elif isinstance(data, dict):
                        if 'results' in data:
                            customers = [c for c in data.get('results', []) if isinstance(c, dict)]
                        elif 'id' in data:
                            customers = [data]
            elif isinstance(response, list):
                customers = [c for c in response if isinstance(c, dict)]
            return customers
        except Exception as e:
            print(f"Failed to load customers: {e}")
            return []

    def load_customers(self):
        """Load customers from API."""
        self.set_state(ScreenState.LOADING)
        self.customers = self._fetch_customers()
        
        # Update state based on data
        if len(self.customers) == 0:
            self.set_state(ScreenState.EMPTY)
        else:
            self.set_state(ScreenState.READY)
        
        self.update_table()

    def update_table(self):
        """Update table with customer data and show appropriate state indicators."""
        valid_customers = [c for c in self.customers if isinstance(c, dict)]

        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(valid_customers) == 0)
        self.table.setVisible(state == ScreenState.READY and len(valid_customers) > 0)

        data = []
        for customer in valid_customers:
            data.append({
                "id": str(customer.get('id') or ''),
                "name": customer.get('name') or '',
                "phone": customer.get('phone') or '',
                "email": customer.get('email') or '',
                "address": customer.get('address') or '',
            })
        self.table.set_data(data)

    def filter_customers(self, text):
        """Filter customers by search text."""
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match and text != "")

    def add_customer(self):
        """Add new customer dialog."""
        dialog = CustomerDialog(self.api_client)
        if dialog.exec():
            self.load_customers()


class CustomerDialog(QDialog):
    """Customer add/edit dialog with Individual/Company support."""

    @staticmethod
    def _submit_style():
        from ui.constants import COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_TEXT_MUTED, COLOR_TEXT_ON_PRIMARY, TEXT_CARD_TITLE
        return """
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_MD}px 24px;
                font-weight: bold;
                font-size: {TEXT_CARD_TITLE}px;
            }}
            QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {COLOR_PRIMARY_ACTIVE}; }}
            QPushButton:disabled {{ background-color: {COLOR_TEXT_MUTED}; color: {COLOR_TEXT_MUTED}; }}
        """

    @staticmethod
    def _input_style():
        from ui.constants import (COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, COLOR_BORDER, COLOR_BORDER_FOCUS, COLOR_DANGER, TEXT_BODY, PADDING_INPUT_H)
        return """
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {PADDING_INPUT_H}px;
                font-size: {TEXT_BODY}px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {COLOR_BORDER_FOCUS};
            }}
            QLineEdit:invalid, QTextEdit:invalid {{
                border: 1px solid {COLOR_DANGER};
            }}
        """

    def __init__(self, api_client=None, customer=None):
        super().__init__()
        self.api_client = api_client
        self.customer = customer
        self._is_submitting = False
        self.setWindowTitle("Add Customer" if not customer else "Edit Customer")
        self.resize(550, 650)
        self.setMinimumHeight(650)
        self.setMaximumHeight(750)
        self.setStyleSheet(self._input_style())
        self.setup_ui()

    def setup_ui(self):
        from PySide6.QtWidgets import QScrollArea
        
        layout = QVBoxLayout(self)
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
        self.subtype_combo.currentIndexChanged.connect(lambda: self.on_subtype_changed(self.subtype_combo.currentText()))
        
        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Form container
        form = QFrame()
        form.setStyleSheet("QFrame { background-color: transparent; }")
        form_layout = QFormLayout(form)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setSpacing(SPACING_SM)
        
        # Individual fields
        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("First Name")
        self.first_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Last Name")
        self.last_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.national_id = QLineEdit()
        self.national_id.setPlaceholderText("National ID")
        self.national_id.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Company fields
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Company Name")
        self.company_name.setMinimumHeight(INPUT_HEIGHT_MD)
        self.company_name.setVisible(False)
        
        self.registration_number = QLineEdit()
        self.registration_number.setPlaceholderText("Registration Number")
        self.registration_number.setMinimumHeight(INPUT_HEIGHT_MD)
        self.registration_number.setVisible(False)
        
        self.business_license = QLineEdit()
        self.business_license.setPlaceholderText("Business License (جواز فعالیت)")
        self.business_license.setMinimumHeight(INPUT_HEIGHT_MD)
        self.business_license.setVisible(False)
        
        # Common fields
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Phone Number")
        self.phone.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.email = QLineEdit()
        self.email.setPlaceholderText("Email Address")
        self.email.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.address = QTextEdit()
        self.address.setPlaceholderText("Address")
        self.address.setMinimumHeight(INPUT_HEIGHT_MD)
        self.address.setMaximumHeight(120)
        
        self.city = QLineEdit()
        self.city.setPlaceholderText("City")
        self.city.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Contact person (for companies)
        self.contact_person = QLineEdit()
        self.contact_person.setPlaceholderText("Contact Person Name")
        self.contact_person.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.contact_role = QLineEdit()
        self.contact_role.setPlaceholderText("Contact Person Role")
        self.contact_role.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.contact_phone = QLineEdit()
        self.contact_phone.setPlaceholderText("Contact Person Phone")
        self.contact_phone.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.contact_email = QLineEdit()
        self.contact_email.setPlaceholderText("Contact Person Email")
        self.contact_email.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Financial fields
        self.credit_limit = QLineEdit()
        self.credit_limit.setPlaceholderText("Credit Limit")
        self.credit_limit.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.payment_terms = QLineEdit()
        self.payment_terms.setPlaceholderText("Payment Terms (days)")
        self.payment_terms.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.tax_number = QLineEdit()
        self.tax_number.setPlaceholderText("Tax Number")
        self.tax_number.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Add fields to form
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
        
        # Contact person
        contact_group = QGroupBox("Contact Person (for companies)")
        contact_layout = QFormLayout()
        contact_layout.addRow("Name:", self.contact_person)
        contact_layout.addRow("Role:", self.contact_role)
        contact_layout.addRow("Phone:", self.contact_phone)
        contact_layout.addRow("Email:", self.contact_email)
        contact_group.setLayout(contact_layout)
        form_layout.addRow(contact_group)
        
        # Financial
        financial_group = QGroupBox("Financial Details")
        financial_layout = QFormLayout()
        financial_layout.addRow("Credit Limit:", self.credit_limit)
        financial_layout.addRow("Payment Terms (days):", self.payment_terms)
        financial_layout.addRow("Tax Number:", self.tax_number)
        financial_group.setLayout(financial_layout)
        form_layout.addRow(financial_group)
        
        # Add form to scroll area
        scroll.setWidget(form)
        layout.addWidget(scroll)
        
# Buttons at bottom (fixed)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACING_SM + SPACING_XS)
        
        self.btn_cancel = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_cancel.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.btn_cancel.setStyleSheet("""
            QPushButton {{
                background-color: {COLOR_TEXT_MUTED};
                color: white;
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_MD}px 24px;
                font-size: {TEXT_CARD_TITLE}px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_TEXT_MUTED};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = EnterpriseButton("Save Customer", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.btn_save.clicked.connect(self.save)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)
        
        layout.addLayout(buttons_layout)
        
        # Load existing data if editing
        if self.customer:
            self.load_customer_data()
    
    def on_subtype_changed(self, subtype):
        """Show/hide fields based on subtype."""
        is_individual = subtype == "Individual"
        
        self.first_name.setVisible(True)
        self.last_name.setVisible(True)
        self.national_id.setVisible(True)
        
        self.company_name.setVisible(not is_individual)
        self.registration_number.setVisible(not is_individual)
        self.business_license.setVisible(not is_individual)
    
    def load_customer_data(self):
        """Load existing customer data."""
        if not self.customer:
            return
        
        # Set fields from customer data
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

    def save(self):
        """Save customer with validation."""
        import uuid
        
        # Prevent duplicate submissions
        if self._is_submitting:
            return
        self._is_submitting = True
        self.btn_save.setEnabled(False)
        self.btn_save.setText("Saving...")
        
        subtype = "INDIVIDUAL" if self.subtype_combo.currentText() == "Individual" else "COMPANY"
        
        # Validate based on subtype
        validation_errors = []
        if subtype == "INDIVIDUAL":
            if not self.first_name.text().strip():
                validation_errors.append("First name is required for individual customers")
            if not self.last_name.text().strip():
                validation_errors.append("Last name is required for individual customers")
        else:
            if not self.company_name.text().strip():
                validation_errors.append("Company name is required for company customers")
            if not self.business_license.text().strip():
                validation_errors.append("Business license is required for company customers")
        
        if not self.phone.text().strip():
            validation_errors.append("Phone number is required")
        
        if validation_errors:
            self._is_submitting = False
            self.btn_save.setEnabled(True)
            self.btn_save.setText("Save Customer")
            QMessageBox.warning(self, "Validation Error", "\n".join(validation_errors))
            return
        
        # Build data based on subtype
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
        
        # Common fields
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
        
        endpoint = get_endpoint("customers")
        if self.api_client:
            try:
                response = self.api_client.post(endpoint, data)
                if response and isinstance(response, dict):
                    if response.get("success") or response.get("id"):
                        QMessageBox.information(self, "Success", "Customer saved successfully.")
                        self.accept()
                        return
                    error_msg = response.get("error", {}).get("message", "Failed to save customer") if isinstance(response, dict) else "Failed to save customer"
                    QMessageBox.warning(self, "Error", error_msg)
                else:
                    QMessageBox.warning(self, "Error", "Failed to save customer")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save: {e}")
        else:
            QMessageBox.information(self, "Success", "Customer saved successfully (offline mode).")
            self.accept()
        
        # Reset button state on failure
        self._is_submitting = False
        self.btn_save.setEnabled(True)
        self.btn_save.setText("Save Customer")