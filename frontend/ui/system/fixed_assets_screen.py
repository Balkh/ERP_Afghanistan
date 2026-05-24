"""Fixed Assets management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QMessageBox, QComboBox, QGroupBox, QFormLayout,
                                  QDialog, QTabWidget, QDoubleSpinBox,
                                  QDateEdit, QWidget, QFrame, QPushButton,
                                  QTableWidget, QTableWidgetItem)
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_SUCCESS,
                           COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


class FixedAssetsScreen(BaseScreen):
    """Screen for managing fixed assets."""
    
    def __init__(self, parent=None, screen_id="fixed_assets", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Fixed Assets Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self._load_assets)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; background: {COLOR_BG_SURFACE}; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: {SPACING_MD}px {SPACING_XL}px; border-top-left-radius: {BORDER_RADIUS_MD}px; border-top-right-radius: {BORDER_RADIUS_MD}px; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_SURFACE}; border-bottom-color: {COLOR_BG_SURFACE}; font-weight: bold; }}
        """)
        
        # Assets Tab
        self.assets_tab = QWidget()
        self._setup_assets_tab()
        self.tabs.addTab(self.assets_tab, "Assets")
        
        # Categories Tab
        self.categories_tab = QWidget()
        self._setup_categories_tab()
        self.tabs.addTab(self.categories_tab, "Categories")
        
        # Depreciation Tab
        self.depreciation_tab = QWidget()
        self._setup_depreciation_tab()
        self.tabs.addTab(self.depreciation_tab, "Depreciation")
        
        layout.addWidget(self.tabs)
    
    def _setup_assets_tab(self):
        layout = QVBoxLayout(self.assets_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_bar = QFrame()
        filter_bar.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}; border: 1px solid {COLOR_BORDER};")
        filter_layout = QHBoxLayout(filter_bar)
        
        self.category_filter = QComboBox()
        self.category_filter.addItems(["All Categories", "Vehicles", "Equipment", "Furniture", "Computers"])
        self.category_filter.setMinimumWidth(150)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Disposed", "Under Maintenance"])
        self.status_filter.setMinimumWidth(150)
        
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        add_btn = EnterpriseButton("+ Add Asset", variant=ButtonVariant.SUCCESS)
        add_btn.clicked.connect(self._add_asset)
        
        dispose_btn = EnterpriseButton("Dispose", variant=ButtonVariant.DANGER)
        
        action_layout.addWidget(add_btn)
        action_layout.addWidget(dispose_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("asset_code", "Asset Code", width=100),
            TableColumn("name", "Name", width=200),
            TableColumn("category", "Category", width=100),
            TableColumn("purchase_date", "Purchase Date", width=100, align="center"),
            TableColumn("cost", "Cost", width=100, align="right"),
            TableColumn("depreciation", "Depreciation", width=100, align="right"),
            TableColumn("book_value", "Book Value", width=100, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.assets_table = EnterpriseTable(columns)
        layout.addWidget(self.assets_table)
        
        self._load_assets()
    
    def _setup_categories_tab(self):
        layout = QVBoxLayout(self.categories_tab)
        layout.setSpacing(SPACING_MD)
        
        button_layout = QHBoxLayout()
        
        add_btn = EnterpriseButton("Add Category", variant=ButtonVariant.PRIMARY)
        
        refresh_btn = EnterpriseButton("Refresh", variant=ButtonVariant.SECONDARY)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(5)
        self.categories_table.setHorizontalHeaderLabels(["Name", "Description", "Depreciation Method", "Useful Life (Years)", "Actions"])
        self.categories_table.horizontalHeader().setStretchLastSection(True)
        self.categories_table.setAlternatingRowColors(True)
        self.categories_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.categories_table)
        
        self._load_categories()
    
    def _setup_depreciation_tab(self):
        layout = QVBoxLayout(self.depreciation_tab)
        layout.setSpacing(SPACING_MD)
        
        summary_group = QGroupBox("Depreciation Summary")
        summary_layout = QHBoxLayout()
        
        summary_layout.addWidget(QLabel("Total Depreciation This Year:"))
        summary_layout.addWidget(QLabel("125,000.00 AFN"))
        
        summary_layout.addWidget(QLabel("Total Book Value:"))
        summary_layout.addWidget(QLabel("2,500,000.00 AFN"))
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        button_layout = QHBoxLayout()
        
        calculate_btn = EnterpriseButton("Calculate Depreciation", variant=ButtonVariant.PRIMARY)
        
        report_btn = EnterpriseButton("Depreciation Report", variant=ButtonVariant.SECONDARY)
        
        button_layout.addWidget(calculate_btn)
        button_layout.addWidget(report_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.depreciation_table = QTableWidget()
        self.depreciation_table.setColumnCount(7)
        self.depreciation_table.setHorizontalHeaderLabels(["Asset", "Category", "Cost", "Accumulated Depr.", "Current Depr.", "Book Value", "Year"])
        self.depreciation_table.horizontalHeader().setStretchLastSection(True)
        self.depreciation_table.setAlternatingRowColors(True)
        self.depreciation_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.depreciation_table)
        
        self._load_depreciation()
    
    def _load_assets(self):
        self.assets_table.setRowCount(0)
        
        if self._api_client:
            try:
                endpoint = get_endpoint("assets")
                response = self._api_client.get(endpoint)
                if response and isinstance(response, dict) and response.get("success"):
                    data = response.get("data", [])
                else:
                    data = []
            except Exception:
                data = []
        else:
            data = self._get_mock_assets()
        
        for item in data:
            row = self.assets_table.rowCount()
            self.assets_table.insertRow(row)
            self.assets_table.setItem(row, 0, QTableWidgetItem(item.get("asset_code", "")))
            self.assets_table.setItem(row, 1, QTableWidgetItem(item.get("name", "")))
            self.assets_table.setItem(row, 2, QTableWidgetItem(item.get("category_name", "")))
            self.assets_table.setItem(row, 3, QTableWidgetItem(str(item.get("purchase_date", ""))[:10]))
            self.assets_table.setItem(row, 4, QTableWidgetItem(str(item.get("purchase_cost", "0"))))
            self.assets_table.setItem(row, 5, QTableWidgetItem(str(item.get("accumulated_depreciation", "0"))))
            self.assets_table.setItem(row, 6, QTableWidgetItem(str(item.get("book_value", "0"))))
            self.assets_table.setItem(row, 7, QTableWidgetItem(item.get("status", "")))
            
            btn = EnterpriseButton("View", variant=ButtonVariant.SECONDARY)
            self.assets_table.setCellWidget(row, 8, btn)
            self.assets_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _get_mock_assets(self):
        return [
            {"asset_code": "AST-001", "name": "Toyota Corolla", "category_name": "Vehicles", "purchase_date": "2024-01-15", "purchase_cost": "450000", "accumulated_depreciation": "90000", "book_value": "360000", "status": "Active"},
            {"asset_code": "AST-002", "name": "Dell Laptop", "category_name": "Computers", "purchase_date": "2025-03-10", "purchase_cost": "85000", "accumulated_depreciation": "8500", "book_value": "76500", "status": "Active"},
            {"asset_code": "AST-003", "name": "Office Desk Set", "category_name": "Furniture", "purchase_date": "2024-06-01", "purchase_cost": "120000", "accumulated_depreciation": "18000", "book_value": "102000", "status": "Active"},
        ]
    
    def _load_categories(self):
        self.categories_table.setRowCount(0)
        
        mock_data = [
            {"name": "Vehicles", "description": "Company vehicles", "method": "Straight Line", "life": 5},
            {"name": "Equipment", "description": "Medical equipment", "method": "Straight Line", "life": 7},
            {"name": "Furniture", "description": "Office furniture", "method": "Straight Line", "life": 10},
            {"name": "Computers", "description": "IT equipment", "method": "Declining Balance", "life": 3},
        ]
        
        for item in mock_data:
            row = self.categories_table.rowCount()
            self.categories_table.insertRow(row)
            self.categories_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.categories_table.setItem(row, 1, QTableWidgetItem(item["description"]))
            self.categories_table.setItem(row, 2, QTableWidgetItem(item["method"]))
            self.categories_table.setItem(row, 3, QTableWidgetItem(str(item["life"])))
            
            btn = EnterpriseButton("Edit", variant=ButtonVariant.SECONDARY)
            self.categories_table.setCellWidget(row, 4, btn)
            self.categories_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _load_depreciation(self):
        self.depreciation_table.setRowCount(0)
        
        mock_data = [
            {"asset": "Toyota Corolla", "category": "Vehicles", "cost": "450000.00", "accumulated": "90000.00", "current": "90000.00", "book": "360000.00", "year": "2025"},
            {"asset": "Dell Laptop", "category": "Computers", "cost": "85000.00", "accumulated": "8500.00", "current": "28333.00", "book": "56667.00", "year": "2025"},
            {"asset": "Office Desk Set", "category": "Furniture", "cost": "120000.00", "accumulated": "18000.00", "current": "12000.00", "book": "90000.00", "year": "2025"},
        ]
        
        for item in mock_data:
            row = self.depreciation_table.rowCount()
            self.depreciation_table.insertRow(row)
            self.depreciation_table.setItem(row, 0, QTableWidgetItem(item["asset"]))
            self.depreciation_table.setItem(row, 1, QTableWidgetItem(item["category"]))
            self.depreciation_table.setItem(row, 2, QTableWidgetItem(item["cost"]))
            self.depreciation_table.setItem(row, 3, QTableWidgetItem(item["accumulated"]))
            self.depreciation_table.setItem(row, 4, QTableWidgetItem(item["current"]))
            self.depreciation_table.setItem(row, 5, QTableWidgetItem(item["book"]))
            self.depreciation_table.setItem(row, 6, QTableWidgetItem(item["year"]))
            self.depreciation_table.setRowHeight(row, TABLE_ROW_HEIGHT_MD)
    
    def _add_asset(self):
        dialog = AssetDialog(self)
        dialog.exec()
    
    def on_show(self):
        """Called when screen is shown."""
        self._load_assets()
        self._load_categories()
        self._load_depreciation()


class AssetDialog(QDialog):
    """Dialog for adding assets."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Asset")
        self.setMinimumSize(500, 450)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("Asset name")
        
        self.category = QComboBox()
        self.category.addItems(["Vehicles", "Equipment", "Furniture", "Computers", "Buildings"])
        
        self.purchase_date = QDateEdit()
        self.purchase_date.setCalendarPopup(True)
        
        self.purchase_cost = QDoubleSpinBox()
        self.purchase_cost.setRange(0, 999999999)
        self.purchase_cost.setDecimals(2)
        
        self.useful_life = QDoubleSpinBox()
        self.useful_life.setRange(1, 50)
        self.useful_life.setValue(5)
        
        self.depreciation_method = QComboBox()
        self.depreciation_method.addItems(["Straight Line", "Declining Balance", "Sum of Years"])
        
        form_layout.addRow("Name:", self.name)
        form_layout.addRow("Category:", self.category)
        form_layout.addRow("Purchase Date:", self.purchase_date)
        form_layout.addRow("Purchase Cost:", self.purchase_cost)
        form_layout.addRow("Useful Life (Years):", self.useful_life)
        form_layout.addRow("Depreciation Method:", self.depreciation_method)
        
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
            QMessageBox.warning(self, "Validation", "Asset name is required.")
            return
        
        QMessageBox.information(self, "Success", "Asset created!")
        self.accept()