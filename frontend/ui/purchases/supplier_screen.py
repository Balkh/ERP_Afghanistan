from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Suppliers screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QFormLayout, QDialog,
                                  QDialogButtonBox, QComboBox, QTextEdit, QSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                          BORDER_RADIUS_MD)


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
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, SPACING_SM)
        title = QLabel("Suppliers")
        title.setFont(QFont("Segoe UI", FONT_SIZE_TITLE, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("Add Supplier")
        add_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        add_btn.clicked.connect(self.add_supplier)
        header.addWidget(add_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
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
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 12px;
            }
        """)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Error indicator
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                padding: 12px;
            }
        """)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Empty state indicator
        self.empty_label = QLabel("No suppliers found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 12px;
            }
        """)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Email", "Address"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(TABLE_ROW_HEIGHT_MD * 5)  # Show about 5 rows
        self.table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)
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
                        print(f"API error: {response.get('error', {})}")
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
                print(f"Failed to load suppliers: {e}")
                self.set_state(ScreenState.ERROR)
        
        self.update_table()

    def update_table(self):
        """Update table with supplier data and show appropriate state indicators."""
        valid_suppliers = [s for s in self.suppliers if isinstance(s, dict)]
        self.table.setRowCount(len(valid_suppliers))
        for i, supplier in enumerate(valid_suppliers):
            self.table.setItem(i, 0, QTableWidgetItem(str(supplier.get('id', ''))))
            self.table.setItem(i, 1, QTableWidgetItem(supplier.get('name', '')))
            self.table.setItem(i, 2, QTableWidgetItem(supplier.get('phone', '')))
            self.table.setItem(i, 3, QTableWidgetItem(supplier.get('email', '')))
            self.table.setItem(i, 4, QTableWidgetItem(supplier.get('address', '')))
        
        # Show/hide indicators based on state
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(valid_suppliers) == 0)
        self.table.setVisible(state == ScreenState.READY and len(valid_suppliers) > 0)

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


class SupplierDialog(QDialog):
    """Supplier add/edit dialog with full features."""
    
    _SUBMIT_STYLESHEET = """
        QPushButton {
            background-color: COLOR_SUCCESS;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #219653;
        }
        QPushButton:pressed {
            background-color: #1e8449;
        }
        QPushButton:disabled {
            background-color: COLOR_TEXT_MUTED;
            color: #7f8c8d;
        }
    """
    
    _INPUT_STYLESHEET = """
        QLineEdit, QTextEdit, QComboBox {
            background-color: #2d2d3d;
            color: #e0e0e0;
            border: 1px solid COLOR_BORDER;
            border-radius: 6px;
            padding: 10px;
            font-size: 13px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 1px solid COLOR_PRIMARY;
        }
    """

    def __init__(self, api_client=None, supplier=None):
        super().__init__()
        self.api_client = api_client
        self.supplier = supplier
        self._is_submitting = False
        self.setWindowTitle("Add Supplier" if not supplier else "Edit Supplier")
        self.resize(550, 650)
        self.setMinimumHeight(650)
        self.setMaximumHeight(750)
        self.setStyleSheet(self._INPUT_STYLESHEET)
        self.setup_ui()

    def setup_ui(self):
        from PySide6.QtWidgets import QScrollArea, QGroupBox
        
        layout = QVBoxLayout(self)
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
        scroll.setStyleSheet(f"QScrollArea {{ border: none; }}")
        
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
        
        # Bank details group
        bank_group = QGroupBox("Bank Details")
        bank_layout = QFormLayout()
        bank_layout.addRow("Bank Name:", self.bank_name)
        bank_layout.addRow("Account #:", self.bank_account)
        bank_layout.addRow("IBAN:", self.iban)
        bank_layout.addRow("SWIFT:", self.swift_code)
        bank_group.setLayout(bank_layout)
        form_layout.addRow(bank_group)
        
        # Contact group
        contact_group = QGroupBox("Contact Person")
        contact_layout = QFormLayout()
        contact_layout.addRow("Name:", self.contact_person)
        contact_layout.addRow("Role:", self.contact_role)
        contact_layout.addRow("Phone:", self.contact_phone)
        contact_layout.addRow("Email:", self.contact_email)
        contact_group.setLayout(contact_layout)
        form_layout.addRow(contact_group)
        
        # Business terms group
        terms_group = QGroupBox("Business Terms")
        terms_layout = QFormLayout()
        terms_layout.addRow("Delivery Terms:", self.delivery_terms)
        terms_layout.addRow("Lead Time (days):", self.lead_time)
        terms_layout.addRow("Min Order Value:", self.minimum_order)
        terms_layout.addRow("Quality Rating (0-5):", self.quality_rating)
        terms_group.setLayout(terms_layout)
        form_layout.addRow(terms_group)
        
        # Financial group
        financial_group = QGroupBox("Financial Details")
        financial_layout = QFormLayout()
        financial_layout.addRow("Credit Limit:", self.credit_limit)
        financial_layout.addRow("Payment Terms (days):", self.payment_terms)
        financial_layout.addRow("Tax Number:", self.tax_number)
        financial_group.setLayout(financial_layout)
        form_layout.addRow(financial_group)
        
        # Add scroll area
        scroll.setWidget(form)
        layout.addWidget(scroll)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACING_SM + SPACING_XS)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_TEXT_MUTED};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #7f8c8d;
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Save Supplier")
        self.btn_save.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.btn_save.setStyleSheet(self._SUBMIT_STYLESHEET)
        self.btn_save.clicked.connect(self.save)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)
        
        layout.addLayout(buttons_layout)
        
        self.subtype_combo.currentTextChanged.connect(self.on_subtype_changed)
    
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
            QMessageBox.warning(self, "Validation Error", "\n".join(validation_errors))
            return
        
        if not self.phone.text().strip():
            QMessageBox.warning(self, "Validation Error", "Phone number is required.")
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
                        QMessageBox.information(self, "Success", "Supplier saved successfully.")
                        self.accept()
                        return
                    error_msg = response.get("error", {}).get("message", "Failed to save supplier") if isinstance(response, dict) else "Failed to save supplier"
                    QMessageBox.warning(self, "Error", error_msg)
                else:
                    QMessageBox.warning(self, "Error", "Failed to save supplier")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save: {e}")
        else:
            QMessageBox.information(self, "Success", "Supplier saved successfully (offline mode).")
            self.accept()
        
        # Reset button state on failure
        self._is_submitting = False
        self.btn_save.setEnabled(True)
        self.btn_save.setText("Save Supplier")