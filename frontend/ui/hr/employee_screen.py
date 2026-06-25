"""Employee screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                 QLabel, QLineEdit,
                                 QComboBox, QGroupBox,
                                  QFormLayout, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.utils.debounce import Debouncer
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_BODY, TEXT_LABEL, INPUT_HEIGHT_MD, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection
from ui.utils.validation import FormValidator
from theme.style_builder import UIStyleBuilder


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

        self.edit_btn = EnterpriseButton(text="Edit", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.edit_btn.clicked.connect(self.edit_employee)
        action_layout.addWidget(self.edit_btn)

        self.delete_btn = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.delete_btn.clicked.connect(self.delete_employee)
        action_layout.addWidget(self.delete_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Filters
        filter_bar = QGroupBox("Filter Employees")
        filter_bar.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG}px;
                margin-top: {SPACING_SM}px;
                padding-top: {SPACING_SM}px;
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
        self.loading_label.setStyleSheet(UIStyleBuilder.get_state_label_style("loading"))
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No employees found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(UIStyleBuilder.get_state_label_style("empty"))
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading employees")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(UIStyleBuilder.get_state_label_style("error"))
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
        """Load employees from API asynchronously to prevent UI freeze."""
        self.set_state(ScreenState.LOADING)
        
        endpoint = get_endpoint("employees") or "/api/hr/employees/"
        
        def on_success(response):
            try:
                self.employees = extract_list(response)
                if len(self.employees) == 0:
                    self.set_state(ScreenState.EMPTY)
                else:
                    self.set_state(ScreenState.READY)
            except Exception as e:
                logger.error(f"Error processing employees: {e}")
                self.employees = []
                self.set_state(ScreenState.ERROR)
            self.update_table()

        def on_error(error_msg):
            self.error_label.setText(f"Error loading employees: {error_msg}")
            self.employees = []
            self.set_state(ScreenState.ERROR)
            self.update_table()

        self.run_api_request(
            key="employee_load",
            method="GET",
            endpoint=endpoint,
            on_success=on_success,
            on_error=on_error
        )

    
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
            AlertDialog.error("Error", f"Failed to open dialog: {str(e)}", self)

    def edit_employee(self):
        """Edit selected employee."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        employee = self.employees[row] if row < len(self.employees) else None
        if not employee:
            return
        try:
            dialog = EmployeeDialog(parent=self, api_client=self.api_client, employee=employee)
            dialog.setWindowTitle("Edit Employee")
            if dialog.exec():
                self.load_employees()
        except Exception as e:
            import traceback
            traceback.print_exc()
            AlertDialog.error("Error", f"Failed to open dialog: {str(e)}", self)

    def delete_employee(self):
        """Delete selected employee."""
        from ui.components.dialogs import ConfirmDialog
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        employee = self.employees[row] if row < len(self.employees) else None
        if not employee:
            return
        first_name = employee.get('first_name', '')
        last_name = employee.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or "this employee"
        reply = ConfirmDialog.confirm(
            "Delete Employee",
            f"Are you sure you want to delete employee '{full_name}'?",
            self
        )
        if reply:
            endpoint = get_endpoint("employees") or "/api/hr/employees/"
            
            def on_success(response):
                self.load_employees()
                AlertDialog.info("Success", "Employee deleted successfully.", self)

            def on_error(error_msg):
                AlertDialog.error("Error", f"Failed to delete employee: {error_msg}", self)

            self.run_api_request(
                key=f"employee_delete_{employee['id']}",
                method="DELETE",
                endpoint=f"{endpoint}{employee['id']}/",
                on_success=on_success,
                on_error=on_error
            )


class EmployeeDialog(EnterpriseDialog):
    """Employee add/edit dialog."""
    
    def __init__(self, parent=None, api_client=None, employee=None):
        self.api_client = api_client or APIClient()
        self.employee = employee
        title = "Add Employee" if not employee else "Edit Employee"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.setMinimumWidth(500)
        self._build_content()
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)
        if employee:
            self._load_employee_data()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)
        
        section = FormSection("Employee Information", primary=True)
        
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
        
        section.add_field(self.first_name, "First Name*:")
        section.add_field(self.last_name, "Last Name*:")
        section.add_field(self.email, "Email:")
        section.add_field(self.phone, "Phone:")
        section.add_field(self.department, "Department:")
        section.add_field(self.position, "Position:")
        
        layout.addWidget(section)
        
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

        return widget
        
    def _load_departments(self):
        self.department.addItem("Select Department", None)
        def on_success(res):
            try:
                if res and res.get('success'):
                    data = res.get('data', {})
                    results = data.get('results', []) if isinstance(data, dict) else []
                    for d in results:
                        if isinstance(d, dict):
                            self.department.addItem(d.get('name', ''), d.get('id'))
            except Exception:
                pass

        def on_error(error_msg):
            pass

        self.run_api_request(
            key="dialog_load_depts",
            method="GET",
            endpoint="/api/hr/departments/",
            on_success=on_success,
            on_error=on_error
        )

    def _load_positions(self):
        self.position.addItem("Select Position", None)
        def on_success(res):
            try:
                if res and res.get('success'):
                    data = res.get('data', {})
                    results = data.get('results', []) if isinstance(data, dict) else []
                    for p in results:
                        if isinstance(p, dict):
                            self.position.addItem(p.get('title', ''), p.get('id'))
            except Exception:
                pass

        def on_error(error_msg):
            pass

        self.run_api_request(
            key="dialog_load_positions",
            method="GET",
            endpoint="/api/hr/positions/",
            on_success=on_success,
            on_error=on_error
        )

    def _load_employee_data(self):
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
            AlertDialog.warning("Validation Error", f"Please fix the following errors:\n\n{error_messages}", self)
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
        method = "PUT" if self.employee else "POST"
        url = f"{endpoint}{self.employee['id']}/" if self.employee else endpoint

        def on_success(response):
            if response and (response.get("success") or response.get("id")):
                AlertDialog.info("Success", "Employee saved successfully.", self)
                self.accept()
            else:
                msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to save"
                AlertDialog.error("Error", f"Failed to save: {msg}", self)

        def on_error(error_msg):
            AlertDialog.error("Error", f"API Error: {error_msg}", self)

        self.run_api_request(
            key="employee_save",
            method=method,
            endpoint=url,
            params=data,
            on_success=on_success,
            on_error=on_error
        )
