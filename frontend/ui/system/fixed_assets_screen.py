from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Fixed Assets management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QFormLayout, QDialog, QDialogButtonBox, QTabWidget,
                                  QDoubleSpinBox, QDateEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD)


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
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 5px 15px;
                color: #495057;
            }}
            QPushButton:hover {{
                background-color: #e9ecef;
            }}
        """)
        self.btn_refresh.clicked.connect(self.on_show)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: 5px; background: white; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER}; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
            QTabBar::tab:selected {{ background: white; border-bottom-color: white; font-weight: bold; }}
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
        filter_bar.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: 8px; border: 1px solid #dee2e6;")
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
        add_btn = QPushButton("+ Add Asset")
        add_btn.setMinimumHeight(38)
        add_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; border-radius: 5px; font-weight: bold; padding: 0 15px;")
        add_btn.clicked.connect(self._add_asset)
        
        dispose_btn = QPushButton("Dispose")
        dispose_btn.setMinimumHeight(38)
        dispose_btn.setStyleSheet(f"background-color: {COLOR_DANGER}; color: white; border-radius: 5px; padding: 0 15px;")
        
        action_layout.addWidget(add_btn)
        action_layout.addWidget(dispose_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.assets_table = self._create_modern_table()
        self.assets_table.setColumnCount(9)
        self.assets_table.setHorizontalHeaderLabels(["Asset Code", "Name", "Category", "Purchase Date", "Cost", "Depreciation", "Book Value", "Status", "Actions"])
        layout.addWidget(self.assets_table)
        
        self._load_assets()

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ border: none; gridline-color: #f1f2f6; }}
            QHeaderView::section {{ background-color: {COLOR_TABLE_HEADER_BG_LIGHT}; padding: 8px; border: none; border-bottom: 2px solid {COLOR_TABLE_BORDER_LIGHT}; font-weight: bold; }}
            QTableWidget::item {{ padding: 10px; }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table
    
    def _setup_categories_tab(self):
        layout = QVBoxLayout(self.categories_tab)
        layout.setSpacing(SPACING_MD)
        
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Category")
        add_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        
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
        
        calculate_btn = QPushButton("Calculate Depreciation")
        calculate_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        
        report_btn = QPushButton("Depreciation Report")
        report_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        
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
            
            btn = QPushButton("View")
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
            
            btn = QPushButton("Edit")
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
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setMinimumHeight(BUTTON_HEIGHT_MD)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
    
    def save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Asset name is required.")
            return
        
        QMessageBox.information(self, "Success", "Asset created!")
        self.accept()