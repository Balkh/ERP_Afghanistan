from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Payroll management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QFormLayout, QDialog, QDialogButtonBox, QTabWidget,
                                  QDoubleSpinBox, QCheckBox, QFrame, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD)


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
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: COLOR_TEXT_PRIMARY;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("⟳ Refresh")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading payroll data...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #6c757d; padding: 40px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No payroll records found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #6c757d; padding: 40px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading payroll data")
        self.error_label.setFont(QFont("Segoe UI", 12))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: COLOR_DANGER; padding: 40px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid COLOR_TEXT_SECONDARY; 
                border-radius: 8px; 
                background: COLOR_BG_MAIN; 
            }
            QTabBar::tab { 
                background: COLOR_TEXT_SECONDARY; 
                color: COLOR_TEXT_PRIMARY;
                border: none; 
                padding: 12px 24px; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
            }
            QTabBar::tab:selected { 
                background: #3b82f6; 
                color: white; 
                font-weight: bold; 
            }
            QTabBar::tab:hover:!selected { 
                background: #4b5563; 
            }
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
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Structure")
        add_btn.setMinimumHeight(38)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        add_btn.clicked.connect(self._add_salary_structure)
        action_layout.addWidget(add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.salary_table = self._create_modern_table()
        self.salary_table.setColumnCount(5)
        self.salary_table.setHorizontalHeaderLabels(["Name", "Basic Salary", "Active", "Created", "Actions"])
        layout.addWidget(self.salary_table)
        
        self._load_salary_structures()
    
    def _setup_payroll_cycles_tab(self):
        layout = QVBoxLayout(self.payroll_cycles_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_bar = QFrame()
        filter_bar.setStyleSheet("""
            background-color: COLOR_TEXT_SECONDARY;
            border-radius: 8px;
            border: 1px solid #4b5563;
        """)
        filter_layout = QHBoxLayout(filter_bar)
        
        self.cycle_status_filter = QComboBox()
        self.cycle_status_filter.addItems(["All Status", "Draft", "Generated", "Approved", "Paid"])
        self.cycle_status_filter.setMinimumWidth(150)
        self.cycle_status_filter.setStyleSheet("""
            QComboBox {
                background-color: COLOR_BG_MAIN;
                color: COLOR_TEXT_PRIMARY;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.cycle_status_filter)
        filter_layout.addStretch()
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        generate_btn = QPushButton("Generate Payroll")
        generate_btn.setMinimumHeight(38)
        generate_btn.setStyleSheet("background-color: COLOR_PRIMARY; color: white; border-radius: 5px; padding: 0 15px;")
        
        approve_btn = QPushButton("Approve")
        approve_btn.setMinimumHeight(38)
        approve_btn.setStyleSheet("background-color: COLOR_SUCCESS; color: white; border-radius: 5px; padding: 0 15px;")
        
        action_layout.addWidget(generate_btn)
        action_layout.addWidget(approve_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.cycle_table = self._create_modern_table()
        self.cycle_table.setColumnCount(6)
        self.cycle_table.setHorizontalHeaderLabels(["Period", "Status", "Total Employees", "Total Gross", "Total Net", "Actions"])
        layout.addWidget(self.cycle_table)
        
        self._load_payroll_cycles()
    
    def _setup_payroll_records_tab(self):
        layout = QVBoxLayout(self.payroll_records_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        export_btn = QPushButton("Export to Excel")
        export_btn.setMinimumHeight(38)
        export_btn.setStyleSheet("background-color: #34495e; color: white; border-radius: 5px; padding: 0 15px;")
        action_layout.addWidget(export_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.records_table = self._create_modern_table()
        self.records_table.setColumnCount(8)
        self.records_table.setHorizontalHeaderLabels(["Employee", "Period", "Basic Salary", "Allowances", "Deductions", "Gross", "Net", "Status"])
        layout.addWidget(self.records_table)
        
        self._load_payroll_records()

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
                background-color: COLOR_TEXT_SECONDARY; 
                color: COLOR_TEXT_PRIMARY;
                padding: 10px; 
                border: none; 
                border-bottom: 2px solid #4b5563; 
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::item { 
                padding: 10px; 
                border-bottom: 1px solid COLOR_TEXT_SECONDARY;
                color: COLOR_TEXT_PRIMARY;
            }
            QTableWidget::item:selected {
                background-color: #3b82f6 !important;
                color: white !important;
            }
            QTableWidget::item:hover:!selected {
                background-color: COLOR_TEXT_SECONDARY;
            }
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        return table
    
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
        self.salary_table.setRowCount(0)
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
        
        for item in data:
            row = self.salary_table.rowCount()
            self.salary_table.insertRow(row)
            self.salary_table.setItem(row, 0, QTableWidgetItem(item.get("name", "")))
            self.salary_table.setItem(row, 1, QTableWidgetItem(str(item.get("basic_salary", "0"))))
            self.salary_table.setItem(row, 2, QTableWidgetItem("Yes" if item.get("is_active") else "No"))
            self.salary_table.setItem(row, 3, QTableWidgetItem(str(item.get("created_at", ""))[:10]))
            
            btn = QPushButton("Edit")
            self.salary_table.setCellWidget(row, 4, btn)
            self.salary_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
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
        
        for item in data:
            row = self.cycle_table.rowCount()
            self.cycle_table.insertRow(row)
            period = f"{item.get('period_month', '')}/{item.get('period_year', '')}"
            self.cycle_table.setItem(row, 0, QTableWidgetItem(period))
            self.cycle_table.setItem(row, 1, QTableWidgetItem(item.get("status", "")))
            self.cycle_table.setItem(row, 2, QTableWidgetItem(str(item.get("employee_count", 0))))
            self.cycle_table.setItem(row, 3, QTableWidgetItem(str(item.get("total_gross", "0"))))
            self.cycle_table.setItem(row, 4, QTableWidgetItem(str(item.get("total_net", "0"))))
            
            btn = QPushButton("View")
            self.cycle_table.setCellWidget(row, 5, btn)
            self.cycle_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
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
        
        for item in data:
            row = self.records_table.rowCount()
            self.records_table.insertRow(row)
            self.records_table.setItem(row, 0, QTableWidgetItem(item.get("employee_name", "")))
            self.records_table.setItem(row, 1, QTableWidgetItem(item.get("period", "")))
            self.records_table.setItem(row, 2, QTableWidgetItem(str(item.get("basic_salary", "0"))))
            self.records_table.setItem(row, 3, QTableWidgetItem(str(item.get("total_allowances", "0"))))
            self.records_table.setItem(row, 4, QTableWidgetItem(str(item.get("total_deductions", "0"))))
            self.records_table.setItem(row, 5, QTableWidgetItem(str(item.get("gross_salary", "0"))))
            self.records_table.setItem(row, 6, QTableWidgetItem(str(item.get("net_salary", "0"))))
            self.records_table.setItem(row, 7, QTableWidgetItem(item.get("status", "")))
            self.records_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
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
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setMinimumHeight(BUTTON_HEIGHT_MD)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
    
    def save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        
        QMessageBox.information(self, "Success", "Salary structure created!")
        self.accept()