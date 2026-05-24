"""Employee screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                 QLabel, QLineEdit,
                                 QComboBox, QGroupBox,
                                  QMessageBox, QDialog,
                                  QFormLayout)
from PySide6.QtCore import Qt
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.utils.debounce import Debouncer
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_BODY, TEXT_LABEL, INPUT_HEIGHT_MD, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.utils.validation import FormValidator


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
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_employees)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Action section
        action_layout = QHBoxLayout()
        self.add_btn = EnterpriseButton(text="+ Add Employee", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.add_btn.clicked.connect(self.add_employee)
        action_layout.addWidget(self.add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Filters
        filter_bar = QGroupBox("Filter Employees")
        filter_bar.setStyleSheet("""
            QGroupBox {{
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                margin-top: 10px;
                padding-top: 10px;
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_LABEL}pt;
                font-weight: 700;
            }}
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, position, or department...")
        self.search_input.setMinimumHeight(35)
        self.search_input.setMinimumWidth(300)
        self._employee_search_debounce = Debouncer(self.load_employees, 300)
        self.search_input.textChanged.connect(self._employee_search_debounce)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading employees...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No employees found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading employees")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Table
        columns = [
            TableColumn("id", "ID", width=60),
            TableColumn("full_name", "Full Name", width=150),
            TableColumn("department_name", "Department", width=120),
            TableColumn("position_title", "Position", width=120),
            TableColumn("phone", "Phone", width=120),
            TableColumn("email", "Email", width=180),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)
    
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
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.employees) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.employees) > 0)

        if not self.employees:
            self.table.set_data([])
            return

        data = []
        for emp in self.employees:
            if not isinstance(emp, dict):
                continue
            first_name = emp.get('first_name') or ''
            last_name = emp.get('last_name') or ''
            full_name = f"{first_name} {last_name}".strip() or "Unknown"
            status = "Active" if emp.get('is_active', True) else "Inactive"
            data.append({
                "id": str(emp.get('id') or '')[:8],
                "full_name": full_name,
                "department_name": emp.get('department_name') or '',
                "position_title": emp.get('position_title') or '',
                "phone": emp.get('phone') or '',
                "email": emp.get('email') or '',
                "status": status,
            })
        self.table.set_data(data)
    
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
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING_SM)
        btn_layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        ok_btn.clicked.connect(self.save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
    def _load_departments(self):
        self.department.addItem("Select Department", None)
        try:
            res = self.api_client.get("/api/hr/departments/")
            if res and res.get('success'):
                for d in res['data'].get('results', []):
                    self.department.addItem(d['name'], d['id'])
        except Exception:
            pass

    def _load_positions(self):
        self.position.addItem("Select Position", None)
        try:
            res = self.api_client.get("/api/hr/positions/")
            if res and res.get('success'):
                for p in res['data'].get('results', []):
                    self.position.addItem(p['title'], p['id'])
        except Exception:
            pass

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