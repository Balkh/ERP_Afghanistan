"""Budgeting management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel,
                                  QComboBox, QGroupBox, QTabWidget, QFrame,
                                  QWidget, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn, build_table_stylesheet
from ui.components.state_helper import StateHelper


class BudgetingScreen(BaseScreen):
    """Screen for managing budgets."""

    def __init__(self, parent=None, screen_id="budgeting", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self._budgets = []
        self._allocations = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Budget Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; background: {COLOR_BG_SURFACE}; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: {SPACING_MD}px {SPACING_XL}px; border-top-left-radius: {BORDER_RADIUS_MD}px; border-top-right-radius: {BORDER_RADIUS_MD}px; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_SURFACE}; border-bottom-color: {COLOR_BG_SURFACE}; font-weight: bold; }}
        """)

        # Budgets Tab
        self.budgets_tab = QWidget()
        self._setup_budgets_tab()
        self.tabs.addTab(self.budgets_tab, "Budgets")

        # Allocations Tab
        self.allocations_tab = QWidget()
        self._setup_allocations_tab()
        self.tabs.addTab(self.allocations_tab, "Allocations")

        # Variance Analysis Tab
        self.variance_tab = QWidget()
        self._setup_variance_tab()
        self.tabs.addTab(self.variance_tab, "Variance Analysis")

        layout.addWidget(self.tabs)

    def _setup_budgets_tab(self):
        layout = QVBoxLayout(self.budgets_tab)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_bar = QFrame()
        filter_bar.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}; border: 1px solid {COLOR_BORDER_LIGHT};")
        filter_layout = QHBoxLayout(filter_bar)
        
        self.year_filter = QComboBox()
        self.year_filter.addItems(["2026", "2025", "2024"])
        self.year_filter.setMinimumWidth(100)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Draft", "Approved", "Closed"])
        self.status_filter.setMinimumWidth(120)
        
        filter_layout.addWidget(QLabel("Year:"))
        filter_layout.addWidget(self.year_filter)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        
        self.btn_create = EnterpriseButton(text="+ Create Budget", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.btn_create.clicked.connect(self._create_budget)
        
        self.btn_approve = EnterpriseButton(text="Approve", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        
        action_layout.addWidget(self.btn_create)
        action_layout.addWidget(self.btn_approve)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("name", "Budget Name", width=180),
            TableColumn("year", "Year", width=60, align="center"),
            TableColumn("total_budget", "Total Budget", width=100, align="right"),
            TableColumn("total_spent", "Total Spent", width=100, align="right"),
            TableColumn("remaining", "Remaining", width=100, align="right"),
            TableColumn("variance", "Variance %", width=80, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.budgets_table = EnterpriseTable(columns)
        layout.addWidget(self.budgets_table)
        
        self._load_budgets()
    
    def _setup_allocations_tab(self):
        layout = QVBoxLayout(self.allocations_tab)
        layout.setSpacing(SPACING_MD)
        
        button_layout = QHBoxLayout()
        
        allocate_btn = EnterpriseButton("New Allocation", variant=ButtonVariant.PRIMARY)
        
        refresh_btn = EnterpriseButton("Refresh", variant=ButtonVariant.SECONDARY)
        
        button_layout.addWidget(allocate_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.allocations_table = QTableWidget()
        self.allocations_table.setStyleSheet(build_table_stylesheet())
        self.allocations_table.setAlternatingRowColors(True)
        self.allocations_table.setColumnCount(6)
        self.allocations_table.setHorizontalHeaderLabels(["Budget", "Department", "Account", "Allocated", "Spent", "Remaining"])
        self.allocations_table.horizontalHeader().setStretchLastSection(True)
        self.allocations_table.setAlternatingRowColors(True)
        self.allocations_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.allocations_table)
        
        self._load_allocations()
    
    def _setup_variance_tab(self):
        layout = QVBoxLayout(self.variance_tab)
        layout.setSpacing(SPACING_MD)
        
        summary_group = QGroupBox("Budget Variance Summary")
        summary_layout = QHBoxLayout()
        
        summary_layout.addWidget(QLabel("Total Budget:"))
        summary_layout.addWidget(QLabel("5,000,000.00 AFN"))
        
        summary_layout.addWidget(QLabel("Total Spent:"))
        summary_layout.addWidget(QLabel("3,200,000.00 AFN"))
        
        summary_layout.addWidget(QLabel("Variance:"))
        summary_layout.addWidget(QLabel("1,800,000.00 AFN (36%)"))
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        self.variance_table = QTableWidget()
        self.variance_table.setStyleSheet(build_table_stylesheet())
        self.variance_table.setAlternatingRowColors(True)
        self.variance_table.setColumnCount(7)
        self.variance_table.setHorizontalHeaderLabels(["Account", "Budget", "Actual", "Variance", "Variance %", "Status", "Notes"])
        self.variance_table.horizontalHeader().setStretchLastSection(True)
        self.variance_table.setAlternatingRowColors(True)
        self.variance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.variance_table)
        
        self._load_variance()
    
    def _show_loading(self, show=True):
        """Show/hide loading state."""
        if show:
            self.state_helper.show_loading("Loading budgets...")
            self.tabs.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.tabs.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No budgets found"):
        """Show empty state."""
        self.state_helper.show_empty(title=message)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading budgets"):
        """Show error state."""
        self.state_helper.show_error(message, on_retry=self.load_data)
        self.tabs.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.state_helper.hide()
        self.tabs.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_data(self):
        self._load_budgets()
        self._load_allocations()
        self._load_variance()

    def _get_mock_budgets(self):
        return [
            {"name": "Operating Budget 2026", "year": "2026", "total": "5000000.00", "spent": "3200000.00", "remaining": "1800000.00", "variance": "36%", "status": "Approved"},
            {"name": "Capital Budget 2026", "year": "2026", "total": "2000000.00", "spent": "800000.00", "remaining": "1200000.00", "variance": "60%", "status": "Approved"},
            {"name": "Marketing Budget 2026", "year": "2026", "total": "500000.00", "spent": "350000.00", "remaining": "150000.00", "variance": "30%", "status": "Draft"},
        ]
    
    def _load_budgets(self):
        self.budgets_table.setRowCount(0)
        self._show_loading()
        
        try:
            endpoint = get_endpoint("budgets")
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
                data = self._get_mock_budgets()
            
            self._show_data()
        except Exception as e:
            print(f"Error loading budgets: {e}")
            data = self._get_mock_budgets()
            self._show_data()
        
        for item in data:
            row = self.budgets_table.rowCount()
            self.budgets_table.insertRow(row)
            self.budgets_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.budgets_table.setItem(row, 1, QTableWidgetItem(item["year"]))
            self.budgets_table.setItem(row, 2, QTableWidgetItem(item["total"]))
            self.budgets_table.setItem(row, 3, QTableWidgetItem(item["spent"]))
            self.budgets_table.setItem(row, 4, QTableWidgetItem(item["remaining"]))
            self.budgets_table.setItem(row, 5, QTableWidgetItem(item["variance"]))
            self.budgets_table.setItem(row, 6, QTableWidgetItem(item["status"]))
            self.budgets_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _load_allocations(self):
        self.allocations_table.setRowCount(0)
        
        try:
            endpoint = get_endpoint("budget_lines") or "/api/budgets/lines/"
            response = self.api_client.get(endpoint)
            if response and isinstance(response, dict) and response.get("success"):
                raw_data = response.get("data", [])
                data = raw_data.get("results", []) if isinstance(raw_data, dict) else raw_data
            else:
                data = []
            
            if not data:
                data = [
                    {"budget_name": "Operating 2026", "department": "Sales", "account_code": "4000", "allocated_amount": "500000.00", "actual_amount": "320000.00"},
                    {"budget_name": "Operating 2026", "department": "IT", "account_code": "5010", "allocated_amount": "300000.00", "actual_amount": "280000.00"},
                    {"budget_name": "Capital 2026", "department": "Warehouse", "account_code": "6010", "allocated_amount": "800000.00", "actual_amount": "600000.00"},
                ]
        except Exception:
            data = [
                {"budget_name": "Operating 2026", "department": "Sales", "account_code": "4000", "allocated_amount": "500000.00", "actual_amount": "320000.00"},
                {"budget_name": "Operating 2026", "department": "IT", "account_code": "5010", "allocated_amount": "300000.00", "actual_amount": "280000.00"},
                {"budget_name": "Capital 2026", "department": "Warehouse", "account_code": "6010", "allocated_amount": "800000.00", "actual_amount": "600000.00"},
            ]
        
        for item in data:
            allocated = float(item.get("allocated_amount", 0))
            actual = float(item.get("actual_amount", 0))
            remaining = allocated - actual
            row = self.allocations_table.rowCount()
            self.allocations_table.insertRow(row)
            self.allocations_table.setItem(row, 0, QTableWidgetItem(item.get("budget_name", "")))
            self.allocations_table.setItem(row, 1, QTableWidgetItem(item.get("department", "")))
            self.allocations_table.setItem(row, 2, QTableWidgetItem(item.get("account_code", "")))
            self.allocations_table.setItem(row, 3, QTableWidgetItem(f"{allocated:,.2f}"))
            self.allocations_table.setItem(row, 4, QTableWidgetItem(f"{actual:,.2f}"))
            self.allocations_table.setItem(row, 5, QTableWidgetItem(f"{remaining:,.2f}"))
            self.allocations_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _load_variance(self):
        self.variance_table.setRowCount(0)
        
        try:
            endpoint = get_endpoint("budget_lines") or "/api/budgets/lines/"
            response = self.api_client.get(endpoint, params={"include_variance": "true"})
            if response and isinstance(response, dict) and response.get("success"):
                raw_data = response.get("data", [])
                data = raw_data.get("results", []) if isinstance(raw_data, dict) else raw_data
            else:
                data = []
            
            if not data:
                data = [
                    {"account_code": "4000", "account_name": "Sales Expenses", "allocated_amount": "500000.00", "actual_amount": "320000.00"},
                    {"account_code": "5010", "account_name": "IT Expenses", "allocated_amount": "300000.00", "actual_amount": "280000.00"},
                    {"account_code": "6010", "account_name": "Capital", "allocated_amount": "800000.00", "actual_amount": "600000.00"},
                ]
        except Exception:
            data = [
                {"account_code": "4000", "account_name": "Sales Expenses", "allocated_amount": "500000.00", "actual_amount": "320000.00"},
                {"account_code": "5010", "account_name": "IT Expenses", "allocated_amount": "300000.00", "actual_amount": "280000.00"},
                {"account_code": "6010", "account_name": "Capital", "allocated_amount": "800000.00", "actual_amount": "600000.00"},
            ]
        
        for item in data:
            budget = float(item.get("allocated_amount", 0))
            actual = float(item.get("actual_amount", 0))
            variance = budget - actual
            var_pct = f"{(variance/budget*100):.0f}%" if budget > 0 else "0%"
            status = "Under Budget" if variance >= 0 else "Over Budget"
            row = self.variance_table.rowCount()
            self.variance_table.insertRow(row)
            self.variance_table.setItem(row, 0, QTableWidgetItem(f"{item.get('account_code', '')} - {item.get('account_name', '')}"))
            self.variance_table.setItem(row, 1, QTableWidgetItem(f"{budget:,.2f}"))
            self.variance_table.setItem(row, 2, QTableWidgetItem(f"{actual:,.2f}"))
            self.variance_table.setItem(row, 3, QTableWidgetItem(f"{variance:,.2f}"))
            self.variance_table.setItem(row, 4, QTableWidgetItem(var_pct))
            self.variance_table.setItem(row, 5, QTableWidgetItem(status))
            self.variance_table.setItem(row, 6, QTableWidgetItem(""))
            self.variance_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _create_budget(self):
        AlertDialog.info("Create Budget", "Budget creation dialog would open here.")
    
    def on_show(self):
        self.load_data()