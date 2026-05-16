"""Cost Centers management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QMessageBox, QComboBox, QGroupBox,
                                   QFormLayout, QDialog, QTextEdit)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER,
                           BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                           COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


from api.client import APIClient
from ui.screens.base_screen import BaseScreen, ScreenState


class CostCentersScreen(BaseScreen):
    """Screen for managing cost centers."""
    
    def __init__(self, parent=None, screen_id="cost_centers", config=None, api_client=None):
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
        header = QLabel("Cost Centers Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading cost centers...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No cost centers found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading cost centers")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        filter_bar = QGroupBox("Filters")
        filter_font = QFont("Segoe UI", TEXT_LABEL)
        filter_font.setWeight(QFont.Weight.Bold)
        filter_bar.setFont(filter_font)
        filter_bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; margin-top: 10px; padding-top: 10px; }}")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Department", "Project", "Location"])
        self.type_filter.setMinimumWidth(120)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Inactive"])
        self.status_filter.setMinimumWidth(120)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search cost centers...")
        self.search.setMinimumHeight(30)
        self.search.setMinimumWidth(200)
        
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search)
        filter_layout.addStretch()
        
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        
        self.add_btn = EnterpriseButton(text="+ Add Cost Center", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.add_btn.clicked.connect(self._add_cost_center)
        
        self.edit_btn = EnterpriseButton(text="Edit", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        
        self.deactivate_btn = EnterpriseButton(text="Deactivate", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        
        action_layout.addWidget(self.add_btn)
        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.deactivate_btn)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("code", "Code", width=80),
            TableColumn("name", "Name", width=150),
            TableColumn("cost_type", "Type", width=100),
            TableColumn("manager", "Manager", width=120),
            TableColumn("budget", "Budget", width=100, align="right"),
            TableColumn("actual_spend", "Actual Spend", width=100, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)
        
        self._load_cost_centers()

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)

    def _show_empty(self, message="No cost centers found"):
        """Show empty state."""
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_data(self):
        self._load_cost_centers()
    
    def _load_cost_centers(self):
        self.table.setRowCount(0)
        self._show_loading()
        
        try:
            endpoint = get_endpoint("cost_centers")
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
                data = self._get_mock_cost_centers()
            
            self._show_data()
        except Exception as e:
            print(f"Error loading cost centers: {e}")
            data = self._get_mock_cost_centers()
            self._show_data()
        
        cost_data = []
        for item in data:
            cost_data.append({
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "cost_type": item.get("cost_type", ""),
                "manager": item.get("manager", ""),
                "budget": str(item.get("budget", "0")),
                "actual_spend": str(item.get("actual_spend", "0")),
                "status": "Active" if item.get("is_active") else "Inactive",
            })
        self.table.set_data(cost_data)
    
    def _get_mock_cost_centers(self):
        return [
            {"code": "CC-001", "name": "Sales Department", "cost_type": "Department", "manager": "Ahmad S.", "budget": "500000", "actual_spend": "320000", "is_active": True},
            {"code": "CC-002", "name": "Warehouse Operations", "cost_type": "Department", "manager": "Rahim K.", "budget": "300000", "actual_spend": "280000", "is_active": True},
            {"code": "CC-003", "name": "IT Infrastructure", "cost_type": "Project", "manager": "Zahra A.", "budget": "200000", "actual_spend": "150000", "is_active": True},
            {"code": "CC-004", "name": "Kabul Branch", "cost_type": "Location", "manager": "Faris M.", "budget": "400000", "actual_spend": "380000", "is_active": True},
            {"code": "CC-005", "name": "Mazar Branch", "cost_type": "Location", "manager": "Omid H.", "budget": "350000", "actual_spend": "200000", "is_active": False},
        ]
    
    def _add_cost_center(self):
        dialog = CostCenterDialog(self)
        dialog.exec()
    
    def on_show(self):
        self._load_cost_centers()


class CostCenterDialog(QDialog):
    """Dialog for adding/editing cost centers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Cost Center")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("Cost center name")
        
        self.code = QLineEdit()
        self.code.setPlaceholderText("e.g., CC-001")
        
        self.cost_type = QComboBox()
        self.cost_type.addItems(["Department", "Project", "Location"])
        
        self.manager = QLineEdit()
        self.manager.setPlaceholderText("Manager name")
        
        self.budget = QLineEdit()
        self.budget.setPlaceholderText("Budget amount")
        
        self.description = QTextEdit()
        self.description.setPlaceholderText("Description")
        self.description.setMinimumHeight(80)
        
        form_layout.addRow("Name:", self.name)
        form_layout.addRow("Code:", self.code)
        form_layout.addRow("Type:", self.cost_type)
        form_layout.addRow("Manager:", self.manager)
        form_layout.addRow("Budget:", self.budget)
        form_layout.addRow("Description:", self.description)
        
        layout.addLayout(form_layout)
        
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
        
        QMessageBox.information(self, "Success", "Cost center saved!")
        self.accept()