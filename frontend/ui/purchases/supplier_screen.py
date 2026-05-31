"""Suppliers screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit, QSpinBox,
                                   QFormLayout, QComboBox,
                                   QTextEdit, QFrame, QWidget, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection


class SupplierScreen(BaseScreen):
    """Suppliers management screen."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="supplier_screen")
        self.api_client = api_client
        self.suppliers = []
        self.setup_ui()
        self.load_suppliers()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, SPACING_SM)
        title = QLabel("Suppliers")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        add_btn = EnterpriseButton(text="Add Supplier", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        add_btn.clicked.connect(self.add_supplier)
        header.addWidget(add_btn)

        edit_btn = EnterpriseButton(text="Edit", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        edit_btn.clicked.connect(self.edit_supplier)
        header.addWidget(edit_btn)

        delete_btn = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        delete_btn.clicked.connect(self.delete_supplier)
        header.addWidget(delete_btn)

        refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self.load_suppliers)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(SPACING_SM)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search suppliers...")
        self.search_box.setMinimumHeight(INPUT_HEIGHT_MD)
        self.search_box.textChanged.connect(self.filter_suppliers)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Loading indicator
        self.loading_label = QLabel("Loading suppliers...")
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
        self.empty_label = QLabel("No suppliers found")
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

    def load_suppliers(self):
        """Load suppliers from API."""
        # Check if we're in development mode
        import os
        dev_mode = os.path.exists('DEVELOPMENT') or os.environ.get('PHARMACY_ERP_DEVELOPMENT', '').lower() in ('true', '1', 'yes')
        
        self.set_state(ScreenState.LOADING)
        endpoint = get_endpoint("suppliers")
        
        # Return mock data in development mode or if no API client
        if dev_mode or not self.api_client:
            # Mock data for development
            self.suppliers = [
                {"id": "1", "name": "Test Supplier", "phone": "1234567890", "email": "supplier@example.com", "address": "Supplier Address"},
                {"id": "2", "name": "ABC Pharmaceuticals", "phone": "5551234567", "email": "abc@pharma.com", "address": "123 Pharma St"},
                {"id": "3", "name": "XYZ Medical", "phone": "5559876543", "email": "xyz@medical.com", "address": "456 Medical Ave"},
                {"id": "4", "name": "Global Health Inc", "phone": "5555555555", "email": "global@health.com", "address": "789 Health Blvd"},
            ]
            self.set_state(ScreenState.READY)
        else:
            try:
                response = self.api_client.get(endpoint)
                self.suppliers = []
                if isinstance(response, dict):
                    if response.get('success'):
                        data = response.get('data', [])
                        if isinstance(data, list):
                            self.suppliers = [s for s in data if isinstance(s, dict)]
                        elif isinstance(data, dict):
                            if 'results' in data:
                                self.suppliers = [s for s in data.get('results', []) if isinstance(s, dict)]
                            elif 'id' in data:
                                self.suppliers = [data]
                    else:
                        self.error_label.setText(f"API error: {response.get('error', {})}")
                        self.set_state(ScreenState.ERROR)
                elif isinstance(response, list):
                    self.suppliers = [s for s in response if isinstance(s, dict)]
                
                # Update state based on data
                if len(self.suppliers) == 0:
                    self.set_state(ScreenState.EMPTY)
                else:
                    self.set_state(ScreenState.READY)
            except Exception as e:
                self.suppliers = []
                self.error_label.setText(f"Failed to load suppliers: {e}")
                self.set_state(ScreenState.ERROR)
        
        self.update_table()

    def update_table(self):
        """Update table with supplier data and show appropriate state indicators."""
        valid_suppliers = [s for s in self.suppliers if isinstance(s, dict)]

        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(valid_suppliers) == 0)
        self.table.setVisible(state == ScreenState.READY and len(valid_suppliers) > 0)

        data = []
        for supplier in valid_suppliers:
            data.append({
                "id": str(supplier.get('id', '')),
                "name": supplier.get('name', ''),
                "phone": supplier.get('phone', ''),
                "email": supplier.get('email', ''),
                "address": supplier.get('address', ''),
            })
        self.table.set_data(data)

    def filter_suppliers(self, text):
        """Filter suppliers by search text."""
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match and text != "")

    def add_supplier(self):
        """Add new supplier dialog."""
        dialog = SupplierDialog(self.api_client)
        if dialog.exec():
            self.load_suppliers()

    def edit_supplier(self):
        """Edit selected supplier."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        supplier = self.suppliers[row] if row < len(self.suppliers) else None
        if not supplier:
            return
        dialog = SupplierDialog(self.api_client, supplier=supplier)
        if dialog.exec():
            self.load_suppliers()

    def delete_supplier(self):
        """Delete selected supplier."""
        from ui.components.dialogs import ConfirmDialog
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        supplier = self.suppliers[row] if row < len(self.suppliers) else None
        if not supplier:
            return
        reply = ConfirmDialog.confirm(
            "Delete Supplier",
            f"Are you sure you want to delete supplier '{supplier.get('name', '')}'?",
            self
        )
        if reply:
            try:
                endpoint = get_endpoint("suppliers")
                self.api_client.delete(f"{endpoint}{supplier['id']}/")
                self.load_suppliers()
            except Exception as e:
                AlertDialog.error("Error", f"Failed to delete supplier: {e}", self)


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
        from PySide6.QtWidgets import QScrollArea

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
        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("First Name")
        self.first_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Last Name")
        self.last_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Company fields
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("Company Name")
        self.company_name.setMinimumHeight(INPUT_HEIGHT_MD)
        self.company_name.setVisible(False)
        
        self.registration_number = QLineEdit()
        self.registration_number.setPlaceholderText("Registration Number")
        self.registration_number.setMinimumHeight(INPUT_HEIGHT_MD)
        self.registration_number.setVisible(False)
        
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
        
        # Supply categories (important!)
        self.supply_categories = QLineEdit()
        self.supply_categories.setPlaceholderText("Supply Categories (e.g., Medicines, Medical Devices)")
        self.supply_categories.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Contact person
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
        
        # Bank details
        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("Bank Name")
        self.bank_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.bank_account = QLineEdit()
        self.bank_account.setPlaceholderText("Bank Account Number")
        self.bank_account.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.iban = QLineEdit()
        self.iban.setPlaceholderText("IBAN")
        self.iban.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.swift_code = QLineEdit()
        self.swift_code.setPlaceholderText("SWIFT Code")
        self.swift_code.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Business terms
        self.delivery_terms = QLineEdit()
        self.delivery_terms.setPlaceholderText("Delivery Terms (e.g., FOB, CIF)")
        self.delivery_terms.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.lead_time = QLineEdit()
        self.lead_time.setPlaceholderText("Lead Time (days)")
        self.lead_time.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.minimum_order = QLineEdit()
        self.minimum_order.setPlaceholderText("Minimum Order Value")
        self.minimum_order.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Quality rating
        self.quality_rating = QSpinBox()
        self.quality_rating.setMinimum(0)
        self.quality_rating.setMaximum(5)
        self.quality_rating.setMinimumHeight(INPUT_HEIGHT_MD)
        
        # Financial
        self.credit_limit = QLineEdit()
        self.credit_limit.setPlaceholderText("Credit Limit")
        self.credit_limit.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.payment_terms = QLineEdit()
        self.payment_terms.setPlaceholderText("Payment Terms (days)")
        self.payment_terms.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.tax_number = QLineEdit()
        self.tax_number.setPlaceholderText("Tax Number")
        self.tax_number.setMinimumHeight(INPUT_HEIGHT_MD)
        
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
        
        # Add scroll area
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
    
    def save(self):
        """Save supplier with validation."""
        import uuid
        
        # Prevent duplicate submissions
        if self._is_submitting:
            return
        self._is_submitting = True
        self.btn_save.setEnabled(False)
        self.btn_save.setText("Saving...")
        
        subtype = "INDIVIDUAL" if self.subtype_combo.currentText() == "Individual" else "COMPANY"
        
        # Validate
        validation_errors = []
        if subtype == "INDIVIDUAL":
            if not self.first_name.text().strip():
                validation_errors.append("First name is required for individual suppliers")
            if not self.last_name.text().strip():
                validation_errors.append("Last name is required for individual suppliers")
        else:
            if not self.company_name.text().strip():
                validation_errors.append("Company name is required for company suppliers")
        
        if not self.supply_categories.text().strip():
            validation_errors.append("Supply categories are required")
        
        if not self.phone.text().strip():
            validation_errors.append("Phone number is required")
        
        if validation_errors:
            self._is_submitting = False
            self.btn_save.setEnabled(True)
            self.btn_save.setText("Save Supplier")
            AlertDialog.warning("Validation Error", "\n".join(validation_errors), self)
            return
        
        if not self.phone.text().strip():
            AlertDialog.warning("Validation Error", "Phone number is required.", self)
            return
        
        # Build data
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