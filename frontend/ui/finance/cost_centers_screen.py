"""Cost Centers management screen."""
import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit,
                                  QComboBox, QGroupBox,
                                  QTextEdit, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from theme.style_builder import UIStyleBuilder
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           TEXT_LABEL, BORDER_RADIUS_LG, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.forms import FormSection
from ui.components.state_helper import StateHelper


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

        # Enterprise header
        header = PageHeader(
            "Cost Centers Management",
            "Structure departments, projects and locations for controlled financial allocation.",
            "COST GOVERNANCE",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        filter_bar = QGroupBox("Filters")
        filter_font = QFont("Segoe UI", TEXT_LABEL)
        filter_font.setWeight(QFont.Weight.Bold)
        filter_bar.setFont(filter_font)
        filter_bar.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=True))
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
        if show:
            self.state_helper.show_loading("Loading cost centers...")
            self.table.setVisible(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.state_helper.hide()
            self.table.setVisible(True)
            self.btn_refresh.setEnabled(True)

    def _show_empty(self, message="No cost centers found"):
        """Show empty state."""
        self.state_helper.show_empty(title=message)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_error(self, message="Error loading cost centers"):
        """Show error state."""
        self.state_helper.show_error(message, on_retry=self.load_data)
        self.table.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.state_helper.hide()
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_data(self):
        self._load_cost_centers()
    
    def _load_cost_centers(self):
        self.table.setRowCount(0)
        self._show_loading()
        
        try:
            endpoint = get_endpoint("cost_centers")
            if not hasattr(self, "_async_cost_centers_response"):
                self.run_api_request(
                    "cost_centers:list", "GET", endpoint,
                    on_success=lambda r: self._resume_api_request("_async_cost_centers_response", self._load_cost_centers, r),
                    on_error=lambda m: self._resume_api_request("_async_cost_centers_response", self._load_cost_centers, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_cost_centers_response")
            
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
            logging.getLogger(__name__).warning(f"Error loading cost centers: {e}")
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
        dialog = CostCenterDialog(self, api_client=self.api_client)
        dialog.exec()
    
    def on_show(self):
        self._load_cost_centers()


class CostCenterDialog(EnterpriseDialog):
    """Dialog for adding/editing cost centers."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__("Add Cost Center", DialogType.CUSTOM, parent)
        self.setMinimumSize(500, 400)
        self._submitting = False
        self._center_id = None
        self.api_client = api_client
        self._build_content()
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        section = FormSection("Cost Center Details", primary=True)
        
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
        
        section.add_field(self.name, "Name:")
        section.add_field(self.code, "Code:")
        section.add_field(self.cost_type, "Type:")
        section.add_field(self.manager, "Manager:")
        section.add_field(self.budget, "Budget:")
        section.add_field(self.description, "Description:")
        
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

        self.set_content(widget)
    
    def save(self):
        if self._submitting:
            return
        self._submitting = True
        name = self.name.text().strip()
        if not name:
            AlertDialog.warning("Validation Error", "Name is required.", self)
            self._submitting = False
            return
        data = {
            "name": name,
            "code": self.code.text().strip(),
            "cost_type": self.cost_type.currentText(),
            "manager": self.manager.text().strip(),
            "budget": self.budget.text().strip() or "0",
            "description": self.description.toPlainText().strip(),
        }
        if not hasattr(self, "_async_save_response"):
            method = "PUT" if self._center_id else "POST"
            endpoint = f"/api/cost-centers/centers/{self._center_id}/" if self._center_id else "/api/cost-centers/centers/"
            self.run_api_request(
                "cost_center_dialog:save", method, endpoint, data=data,
                on_success=lambda r: self._resume_api_request("_async_save_response", self.save, r),
                on_error=lambda m: self._resume_api_request("_async_save_response", self.save, {"success": False, "error": m}),
            )
            return
        response = self._take_api_response("_async_save_response")
        if response and (response.get("success") or response.get("id")):
            AlertDialog.info("Success", "Cost center saved.", self)
            self.accept()
        else:
            errors = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed"
            AlertDialog.error("Error", str(errors), self)
        self._submitting = False
