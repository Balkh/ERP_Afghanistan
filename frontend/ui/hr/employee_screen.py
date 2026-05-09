from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_BG_BUTTON_LIGHT, COLOR_SECONDARY_BG)
"""Employee screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                 QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                 QHeaderView, QAbstractItemView, QComboBox, QGroupBox,
                                 QDateEdit, QMessageBox, QDialog, QDialogButtonBox,
                                 QFormLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_MD, SPACING_LG, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, COLOR_PRIMARY,
                          COLOR_SUCCESS, COLOR_DANGER)
from ui.utils.validation import FormValidator
import uuid


class EmployeeScreen(BaseScreen):
    """Employees management screen."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="employee_screen")
        self.api_client = api_client or APIClient()
        self.employees = []
        self.setup_ui()
        self.load_employees()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Employee Directory")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: COLOR_TEXT_PRIMARY;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("⟳ Refresh")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: COLOR_BG_BUTTON_LIGHT;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: COLOR_SECONDARY_BG;
            }
        """)
        self.btn_refresh.clicked.connect(self.load_employees)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Action section
        action_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Employee")
        self.add_btn.setMinimumHeight(38)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {COLOR_SUCCESS};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_SUCCESS};
            }}
        """)
        self.add_btn.clicked.connect(self.add_employee)
        action_layout.addWidget(self.add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Filters
        filter_bar = QGroupBox("Filter Employees")
        filter_bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        filter_bar.setStyleSheet("""
            QGroupBox {
                border: 1px solid COLOR_TEXT_SECONDARY;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: COLOR_BG_MAIN;
                color: COLOR_TEXT_PRIMARY;
            }
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, position, or department...")
        self.search_input.setMinimumHeight(35)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: COLOR_TEXT_SECONDARY;
                color: COLOR_TEXT_PRIMARY;
                border: 1px solid COLOR_BORDER;
                border-radius: 6px;
                padding: 8px;
            }
            QLineEdit:focus {
                border-color: COLOR_PRIMARY;
            }
        """)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.load_employees)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading employees...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #6c757d; padding: 40px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No employees found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #6c757d; padding: 40px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading employees")
        self.error_label.setFont(QFont("Segoe UI", 12))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #e74c3c; padding: 40px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Table
        self.table = self._create_modern_table()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Full Name", "Department", "Position", "Phone", "Email", "Status"
        ])
        layout.addWidget(self.table)

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget { 
                background-color: COLOR_BG_MAIN; 
                color: COLOR_TEXT_PRIMARY; 
                border: none; 
                gridline-color: COLOR_TEXT_SECONDARY;
            }
            QHeaderView::section { 
                background-color: {COLOR_TEXT_SECONDARY}; 
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_SM}; 
                border: none; 
                border-bottom: 2px solid {COLOR_BORDER}; 
                font-weight: bold;
                font-size: 12px;
            }}
            QTableWidget::item {{ 
                padding: {SPACING_SM}; 
                border-bottom: 1px solid {COLOR_TEXT_SECONDARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY} !important;
                color: white !important;
                font-weight: bold;
            }}
            QTableWidget::item:hover:!selected {
                background-color: COLOR_TEXT_SECONDARY;
                color: white;
            }
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        return table
    
    def load_employees(self):
        """Load employees from API."""
        self.set_state(ScreenState.LOADING)
        try:
            endpoint = get_endpoint("employees")
            if not endpoint:
                endpoint = "/api/hr/employees/"
             
            response = self.api_client.get(endpoint)
            self.employees = self._parse_response(response)
            
            # Update state based on data
            if len(self.employees) == 0:
                self.set_state(ScreenState.EMPTY)
            else:
                self.set_state(ScreenState.READY)
        except Exception as e:
            print(f"Error loading employees: {e}")
            self.employees = []
            self.set_state(ScreenState.ERROR)
        
        self.update_table()
    
    def _parse_response(self, response):
        """Parse API response."""
        if isinstance(response, list):
            return [e for e in response if isinstance(e, dict)]
        elif isinstance(response, dict):
            if response.get('success'):
                data = response.get('data', [])
                if isinstance(data, list):
                    return [e for e in data if isinstance(e, dict)]
                elif isinstance(data, dict) and 'results' in data:
                    return [e for e in data.get('results', []) if isinstance(e, dict)]
        return []
    
    def update_table(self):
        """Update table with employee data and show appropriate state indicators."""
        if not self.employees:
            self.table.setRowCount(0)
        
        self.table.setRowCount(len(self.employees))
        for row, emp in enumerate(self.employees):
            if not isinstance(emp, dict):
                continue
            self.table.setItem(row, 0, QTableWidgetItem(str(emp.get('id') or '')[:8]))
            first_name = emp.get('first_name') or ''
            last_name = emp.get('last_name') or ''
            full_name = f"{first_name} {last_name}".strip() or "Unknown"
            self.table.setItem(row, 1, QTableWidgetItem(full_name))
            self.table.setItem(row, 2, QTableWidgetItem(emp.get('department_name') or ''))
            self.table.setItem(row, 3, QTableWidgetItem(emp.get('position_title') or ''))
            self.table.setItem(row, 4, QTableWidgetItem(emp.get('phone') or ''))
            self.table.setItem(row, 5, QTableWidgetItem(emp.get('email') or ''))
            status = "Active" if emp.get('is_active', True) else "Inactive"
            self.table.setItem(row, 6, QTableWidgetItem(status))
        
        # Show/hide indicators based on state
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.employees) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.employees) > 0)
    
    def add_employee(self):
        """Add new employee dialog."""
        try:
            dialog = EmployeeDialog(parent=self, api_client=self.api_client)
            dialog.setWindowTitle("Add Employee")
            if dialog.exec():
                self.load_employees()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open dialog: {str(e)}")


class EmployeeDialog(QDialog):
    """Employee add/edit dialog."""
    
    def __init__(self, parent=None, api_client=None, employee=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.employee = employee
        self.setWindowTitle("Add Employee" if not employee else "Edit Employee")
        self.setMinimumWidth(500)
        self.setup_ui()
        if employee:
            self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)
        
        form_group = QGroupBox("Employee Information")
        form = QFormLayout(form_group)
        form.setSpacing(SPACING_MD)
        
        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("Enter first name")
        self.first_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Enter last name")
        self.last_name.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.email = QLineEdit()
        self.email.setPlaceholderText("Enter email address")
        self.email.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Enter phone number")
        self.phone.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self.department = QComboBox()
        self.department.setMinimumHeight(INPUT_HEIGHT_MD)
        self._load_departments()
        
        self.position = QComboBox()
        self.position.setMinimumHeight(INPUT_HEIGHT_MD)
        self._load_positions()
        
        form.addRow("First Name*:", self.first_name)
        form.addRow("Last Name*:", self.last_name)
        form.addRow("Email:", self.email)
        form.addRow("Phone:", self.phone)
        form.addRow("Department:", self.department)
        form.addRow("Position:", self.position)
        
        layout.addWidget(form_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setMinimumHeight(BUTTON_HEIGHT_MD)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_departments(self):
        self.department.addItem("Select Department", None)
        try:
            res = self.api_client.get("/api/hr/departments/")
            if res and res.get('success'):
                for d in res['data'].get('results', []):
                    self.department.addItem(d['name'], d['id'])
        except: pass

    def _load_positions(self):
        self.position.addItem("Select Position", None)
        try:
            res = self.api_client.get("/api/hr/positions/")
            if res and res.get('success'):
                for p in res['data'].get('results', []):
                    self.position.addItem(p['title'], p['id'])
        except: pass

    def load_data(self):
        """Load existing employee data."""
        emp = self.employee
        self.first_name.setText(emp.get('first_name', ''))
        self.last_name.setText(emp.get('last_name', ''))
        self.email.setText(emp.get('email', ''))
        self.phone.setText(emp.get('phone', ''))
        
        idx = self.department.findData(emp.get('department'))
        if idx >= 0: self.department.setCurrentIndex(idx)
        
        idx = self.position.findData(emp.get('position'))
        if idx >= 0: self.position.setCurrentIndex(idx)
    
    def save(self):
        """Save employee with validation."""
        # Validate form
        validator = FormValidator()
        validator.validate_required("First Name", self.first_name.text(), "First name is required")
        validator.validate_required("Last Name", self.last_name.text(), "Last name is required")
        
        if self.email.text():
            validator.validate_email("Email", self.email.text(), "Please enter a valid email address")
        
        if validator.has_errors():
            error_messages = "\n".join([f"• {msg}" for msg in validator.get_errors().values()])
            QMessageBox.warning(self, "Validation Error", f"Please fix the following errors:\n\n{error_messages}")
            return
        
        data = {
            "first_name": self.first_name.text(),
            "last_name": self.last_name.text(),
            "email": self.email.text(),
            "phone": self.phone.text(),
            "department": self.department.currentData(),
            "position": self.position.currentData(),
        }
        
        endpoint = "/api/hr/employees/"
        try:
            if self.employee:
                response = self.api_client.put(f"{endpoint}{self.employee['id']}/", data)
            else:
                response = self.api_client.post(endpoint, data)
                
            if response and (response.get("success") or response.get("id")):
                QMessageBox.information(self, "Success", "Employee saved successfully.")
                self.accept()
            else:
                msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to save"
                QMessageBox.critical(self, "Error", f"Failed to save: {msg}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"API Error: {e}")