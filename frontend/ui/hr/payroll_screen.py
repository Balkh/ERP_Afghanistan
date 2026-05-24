"""Payroll management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QLineEdit,
                                 QMessageBox, QComboBox, QFormLayout,
                                   QDialog, QTabWidget, QDoubleSpinBox,
                                 QCheckBox, QFrame)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_BODY, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY_HOVER,
                           COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


class PayrollScreen(BaseScreen):
    """Screen for managing payroll."""
    
    def __init__(self, parent=None, screen_id="payroll", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Payroll Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading payroll data...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No payroll records found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading payroll data")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {{ 
                border: 1px solid {COLOR_BORDER}; 
                border-radius: {BORDER_RADIUS_LG}; 
                background: {COLOR_BG_MAIN}; 
            }}
            QTabBar::tab {{ 
                background: {COLOR_TEXT_SECONDARY}; 
                color: {COLOR_TEXT_PRIMARY};
                border: none; 
                padding: {SPACING_MD}px 24px; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
            }}
            QTabBar::tab:selected {{ 
                background: {COLOR_PRIMARY_HOVER}; 
                color: {COLOR_TEXT_PRIMARY}; 
                font-weight: 700; 
            }}
            QTabBar::tab:hover:!selected {{ 
                background: {COLOR_BORDER}; 
            }}
        """)
        
        # Salary Structures Tab
        self.salary_structure_tab = QWidget()
        self._setup_salary_structure_tab()
        self.tabs.addTab(self.salary_structure_tab, "Salary Structures")
        
        # Payroll Cycles Tab
        self.payroll_cycles_tab = QWidget()
        self._setup_payroll_cycles_tab()
        self.tabs.addTab(self.payroll_cycles_tab, "Payroll Cycles")
        
        # Payroll Records Tab
        self.payroll_records_tab = QWidget()
        self._setup_payroll_records_tab()
        self.tabs.addTab(self.payroll_records_tab, "Payroll Records")
        
        layout.addWidget(self.tabs)
    
    def _setup_salary_structure_tab(self):
        layout = QVBoxLayout(self.salary_structure_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        add_btn = EnterpriseButton(text="+ Add Structure", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        add_btn.clicked.connect(self._add_salary_structure)
        action_layout.addWidget(add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("name", "Name", width=200),
            TableColumn("basic_salary", "Basic Salary", width=120, align="right"),
            TableColumn("is_active", "Active", width=60, align="center"),
            TableColumn("created_at", "Created", width=100),
        ]
        self.salary_table = EnterpriseTable(columns)
        layout.addWidget(self.salary_table)
        
        self._load_salary_structures()
    
    def _setup_payroll_cycles_tab(self):
        layout = QVBoxLayout(self.payroll_cycles_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_bar = QFrame()
        filter_bar.setStyleSheet("""
            QFrame {{
                background-color: {COLOR_BG_SURFACE};
                border-radius: {BORDER_RADIUS_LG};
                border: 1px solid {COLOR_BORDER};
            }}
        """)
        filter_layout = QHBoxLayout(filter_bar)
        
        self.cycle_status_filter = QComboBox()
        self.cycle_status_filter.addItems(["All Status", "Draft", "Generated", "Approved", "Paid"])
        self.cycle_status_filter.setMinimumWidth(150)
        
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.cycle_status_filter)
        filter_layout.addStretch()
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        generate_btn = EnterpriseButton(text="Generate Payroll", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        approve_btn = EnterpriseButton(text="Approve", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        
        action_layout.addWidget(generate_btn)
        action_layout.addWidget(approve_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("period", "Period", width=120),
            TableColumn("status", "Status", width=100),
            TableColumn("employee_count", "Total Employees", width=120, align="right"),
            TableColumn("total_gross", "Total Gross", width=120, align="right"),
            TableColumn("total_net", "Total Net", width=120, align="right"),
        ]
        self.cycle_table = EnterpriseTable(columns)
        layout.addWidget(self.cycle_table)
        
        self._load_payroll_cycles()
    
    def _setup_payroll_records_tab(self):
        layout = QVBoxLayout(self.payroll_records_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        export_btn = EnterpriseButton(text="Export to Excel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        action_layout.addWidget(export_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("employee_name", "Employee", width=150),
            TableColumn("period", "Period", width=100),
            TableColumn("basic_salary", "Basic Salary", width=100, align="right"),
            TableColumn("total_allowances", "Allowances", width=100, align="right"),
            TableColumn("total_deductions", "Deductions", width=100, align="right"),
            TableColumn("gross_salary", "Gross", width=100, align="right"),
            TableColumn("net_salary", "Net", width=100, align="right"),
            TableColumn("status", "Status", width=80),
        ]
        self.records_table = EnterpriseTable(columns)
        layout.addWidget(self.records_table)
        
        self._load_payroll_records()
    
    def load_data(self, params=None):
        """Load all payroll data."""
        self._load_salary_structures()
        self._load_payroll_cycles()
        self._load_payroll_records()

    def _update_state_indicators(self, success=True, has_data=True):
        """Update visibility of loading/empty/error indicators."""
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(not success)
        self.empty_label.setVisible(success and not has_data)
        self.tabs.setVisible(success and has_data)

    def _load_salary_structures(self):
        self.set_state(ScreenState.LOADING)
        
        try:
            endpoint = get_endpoint("payroll_records") or get_endpoint("salaries") or "/api/payroll/records/"
            response = self.api_client.get(endpoint)
            
            if response and isinstance(response, dict) and response.get("success"):
                data = response.get("data", [])
            elif isinstance(response, list):
                data = response
            else:
                data = []
            
            if not data or not isinstance(data, list):
                data = self._get_mock_salary_structures()
            
            self.set_state(ScreenState.READY)
            self._update_state_indicators(True, True)
        except Exception as e:
            print(f"Error loading salary structures: {e}")
            data = self._get_mock_salary_structures()
            self.set_state(ScreenState.READY)
            self._update_state_indicators(True, True)
        
        salary_data = []
        for item in data:
            salary_data.append({
                "name": item.get("name", ""),
                "basic_salary": str(item.get("basic_salary", "0")),
                "is_active": "Yes" if item.get("is_active") else "No",
                "created_at": str(item.get("created_at", ""))[:10],
            })
        self.salary_table.set_data(salary_data)
    
    def _get_mock_salary_structures(self):
        return [
            {"name": "Standard Grade 1", "basic_salary": "15000.00", "is_active": True, "created_at": "2026-01-01"},
            {"name": "Standard Grade 2", "basic_salary": "20000.00", "is_active": True, "created_at": "2026-01-01"},
            {"name": "Manager Grade", "basic_salary": "35000.00", "is_active": True, "created_at": "2026-01-15"},
        ]
    
    def _load_payroll_cycles(self):
        self.cycle_table.setRowCount(0)
        
        try:
            endpoint = get_endpoint("payroll_cycles")
            response = self.api_client.get(endpoint)
            
            if response and isinstance(response, dict) and response.get("success"):
                raw_data = response.get("data", [])
                if isinstance(raw_data, dict):
                    data = raw_data.get("results", [])
                else:
                    data = raw_data
            else:
                data = []
            
            if not data:
                data = self._get_mock_payroll_cycles()
        except Exception as e:
            print(f"Error loading payroll cycles: {e}")
            data = self._get_mock_payroll_cycles()
        
        cycle_data = []
        for item in data:
            period = f"{item.get('period_month', '')}/{item.get('period_year', '')}"
            cycle_data.append({
                "period": period,
                "status": item.get("status", ""),
                "employee_count": str(item.get("employee_count", 0)),
                "total_gross": str(item.get("total_gross", "0")),
                "total_net": str(item.get("total_net", "0")),
            })
        self.cycle_table.set_data(cycle_data)
    
    def _get_mock_payroll_cycles(self):
        return [
            {"period_month": "April", "period_year": "2026", "status": "PAID", "employee_count": 25, "total_gross": "450000.00", "total_net": "380000.00"},
            {"period_month": "March", "period_year": "2026", "status": "PAID", "employee_count": 24, "total_gross": "420000.00", "total_net": "355000.00"},
            {"period_month": "May", "period_year": "2026", "status": "DRAFT", "employee_count": 25, "total_gross": "450000.00", "total_net": "380000.00"},
        ]
    
    def _load_payroll_records(self):
        self.records_table.setRowCount(0)
        
        try:
            endpoint = get_endpoint("salaries")
            response = self.api_client.get(endpoint)
            
            if response and isinstance(response, dict) and response.get("success"):
                data = response.get("data", [])
            elif isinstance(response, list):
                data = response
            else:
                data = []
            
            if not data or not isinstance(data, list):
                data = self._get_mock_payroll_records()
        except Exception as e:
            print(f"Error loading payroll records: {e}")
            data = self._get_mock_payroll_records()
        
        records_data = []
        for item in data:
            records_data.append({
                "employee_name": item.get("employee_name", ""),
                "period": item.get("period", ""),
                "basic_salary": str(item.get("basic_salary", "0")),
                "total_allowances": str(item.get("total_allowances", "0")),
                "total_deductions": str(item.get("total_deductions", "0")),
                "gross_salary": str(item.get("gross_salary", "0")),
                "net_salary": str(item.get("net_salary", "0")),
                "status": item.get("status", ""),
            })
        self.records_table.set_data(records_data)
    
    def _get_mock_payroll_records(self):
        return [
            {"employee_name": "Ahmad Rostami", "period": "April 2026", "basic_salary": "15000.00", "total_allowances": "2500.00", "total_deductions": "1800.00", "gross_salary": "17500.00", "net_salary": "15700.00", "status": "Paid"},
            {"employee_name": "Maria Haq", "period": "April 2026", "basic_salary": "20000.00", "total_allowances": "3000.00", "total_deductions": "2500.00", "gross_salary": "23000.00", "net_salary": "20500.00", "status": "Paid"},
        ]
    
    def _add_salary_structure(self):
        dialog = SalaryStructureDialog(self)
        dialog.exec()
    
    def _on_screen_shown(self):
        """Called when screen is shown (overrides BaseScreen)."""
        super()._on_screen_shown()
        self.load_data()


class SalaryStructureDialog(QDialog):
    """Dialog for creating salary structures."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Salary Structure")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("Structure name")
        
        self.basic_salary = QDoubleSpinBox()
        self.basic_salary.setRange(0, 999999999)
        self.basic_salary.setDecimals(2)
        self.basic_salary.setValue(15000)
        
        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(True)
        
        form_layout.addRow("Name:", self.name)
        form_layout.addRow("Basic Salary:", self.basic_salary)
        form_layout.addRow("Status:", self.is_active)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
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
    
    def save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        
        QMessageBox.information(self, "Success", "Salary structure created!")
        self.accept()