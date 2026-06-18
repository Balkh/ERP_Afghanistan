"""Fixed Assets management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QComboBox, QGroupBox,
                                  QTabWidget, QDoubleSpinBox,
                                  QDateEdit, QWidget, QFrame)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           BUTTON_HEIGHT_MD, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_SUCCESS,
                           COLOR_PRIMARY, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.forms import FormSection


class FixedAssetsScreen(BaseScreen):
    """Screen for managing fixed assets."""
    
    def __init__(self, parent=None, screen_id="fixed_assets", config=None, api_client=None):
        self._api_client = api_client
        super().__init__(parent, screen_id, config)

    def _setup_screen(self):
        super()._setup_screen()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Enterprise header
        header = PageHeader(
            "Fixed Assets Management",
            "Track asset cost, book value, depreciation and disposal status from one control workspace.",
            "ASSET CONTROL",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self._load_assets)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
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
        filter_bar.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER}; border-left: 4px solid {COLOR_PRIMARY};")
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
        
        category_columns = [
            TableColumn("name", "Name", width=150),
            TableColumn("description", "Description", width=220),
            TableColumn("method", "Depreciation Method", width=160),
            TableColumn("life", "Useful Life (Years)", width=140, align="right"),
            TableColumn("action", "Action", width=90, align="center"),
        ]
        self.categories_table = EnterpriseTable(category_columns, density="compact")
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
        
        depreciation_columns = [
            TableColumn("asset", "Asset", width=170),
            TableColumn("category", "Category", width=120),
            TableColumn("cost", "Cost", width=110, align="right"),
            TableColumn("accumulated", "Accumulated Depr.", width=140, align="right"),
            TableColumn("current", "Current Depr.", width=120, align="right"),
            TableColumn("book", "Book Value", width=120, align="right"),
            TableColumn("year", "Year", width=80, align="center"),
        ]
        self.depreciation_table = EnterpriseTable(depreciation_columns, density="compact")
        layout.addWidget(self.depreciation_table)
        
        self._load_depreciation()
    
    def _load_assets(self):
        self.assets_table.set_data([])
        
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
        rows = []
        for item in data:
            rows.append({
                "asset_code": item.get("asset_code", ""),
                "name": item.get("name", ""),
                "category": item.get("category_name", ""),
                "purchase_date": str(item.get("purchase_date", ""))[:10],
                "cost": str(item.get("purchase_cost", "0")),
                "depreciation": str(item.get("accumulated_depreciation", "0")),
                "book_value": str(item.get("book_value", "0")),
                "status": item.get("status", ""),
            })
        self.assets_table.set_data(rows)
    
    def _get_mock_assets(self):
        return [
            {"asset_code": "AST-001", "name": "Toyota Corolla", "category_name": "Vehicles", "purchase_date": "2024-01-15", "purchase_cost": "450000", "accumulated_depreciation": "90000", "book_value": "360000", "status": "Active"},
            {"asset_code": "AST-002", "name": "Dell Laptop", "category_name": "Computers", "purchase_date": "2025-03-10", "purchase_cost": "85000", "accumulated_depreciation": "8500", "book_value": "76500", "status": "Active"},
            {"asset_code": "AST-003", "name": "Office Desk Set", "category_name": "Furniture", "purchase_date": "2024-06-01", "purchase_cost": "120000", "accumulated_depreciation": "18000", "book_value": "102000", "status": "Active"},
        ]
    
    def _load_categories(self):
        mock_data = [
            {"name": "Vehicles", "description": "Company vehicles", "method": "Straight Line", "life": 5},
            {"name": "Equipment", "description": "Medical equipment", "method": "Straight Line", "life": 7},
            {"name": "Furniture", "description": "Office furniture", "method": "Straight Line", "life": 10},
            {"name": "Computers", "description": "IT equipment", "method": "Declining Balance", "life": 3},
        ]
        rows = [{**item, "life": str(item["life"]), "action": "Edit"} for item in mock_data]
        self.categories_table.set_data(rows)
    
    def _load_depreciation(self):
        mock_data = [
            {"asset": "Toyota Corolla", "category": "Vehicles", "cost": "450000.00", "accumulated": "90000.00", "current": "90000.00", "book": "360000.00", "year": "2025"},
            {"asset": "Dell Laptop", "category": "Computers", "cost": "85000.00", "accumulated": "8500.00", "current": "28333.00", "book": "56667.00", "year": "2025"},
            {"asset": "Office Desk Set", "category": "Furniture", "cost": "120000.00", "accumulated": "18000.00", "current": "12000.00", "book": "90000.00", "year": "2025"},
        ]
        self.depreciation_table.set_data(mock_data)
    
    def _add_asset(self):
        dialog = AssetDialog(self, api_client=self._api_client)
        dialog.exec()
    
    def on_show(self):
        """Called when screen is shown."""
        self._load_assets()
        self._load_categories()
        self._load_depreciation()


class AssetDialog(EnterpriseDialog):
    """Dialog for adding assets."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__("Add Asset", DialogType.CUSTOM, parent)
        self.setMinimumSize(500, 450)
        self._submitting = False
        self._asset_id = None
        self.api_client = api_client
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)
    
    def _create_button_area(self):
        return None
    
    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        section = FormSection("Asset Details", primary=True)
        
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
        
        section.add_field(self.name, "Name:")
        section.add_field(self.category, "Category:")
        section.add_field(self.purchase_date, "Purchase Date:")
        section.add_field(self.purchase_cost, "Purchase Cost:")
        section.add_field(self.useful_life, "Useful Life (Years):")
        section.add_field(self.depreciation_method, "Depreciation Method:")
        
        layout.addWidget(section)
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
        
        return widget
    
    def save(self):
        if self._submitting:
            return
        self._submitting = True
        name = self.name.text().strip()
        if not name:
            AlertDialog.warning("Validation Error", "Asset name is required.", self)
            self._submitting = False
            return
        data = {
            "name": name,
            "category": self.category.currentText(),
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "purchase_cost": str(self.purchase_cost.value()),
            "useful_life": str(int(self.useful_life.value())),
            "depreciation_method": self.depreciation_method.currentText(),
        }
        try:
            if self._asset_id:
                response = self.api_client.put(f"/api/assets/assets/{self._asset_id}/", data)
            else:
                response = self.api_client.post("/api/assets/assets/", data)
            if response and (response.get("success") or response.get("id")):
                AlertDialog.info("Success", "Asset saved.", self)
                self.accept()
            else:
                errors = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed"
                AlertDialog.error("Error", str(errors), self)
        except Exception as e:
            AlertDialog.error("Error", str(e), self)
        finally:
            self._submitting = False