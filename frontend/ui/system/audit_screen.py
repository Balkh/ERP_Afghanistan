"""Audit log screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout,
                                  QLabel, QLineEdit,
                                  QComboBox, QGroupBox, QDateEdit)
from PySide6.QtCore import Qt
from datetime import datetime
from ui.screens.base_screen import BaseScreen
from ui.components.dialogs import AlertDialog
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_MD, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_LABEL, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


class AuditScreen(BaseScreen):
    """Screen for viewing audit logs."""
    
    def __init__(self, parent=None, screen_id="audit", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("System Audit Logs")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self._load_audit_logs)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        filter_bar = QGroupBox("Filter Logs")
        filter_bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; font-size: {TEXT_LABEL}pt; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; }}")
        filter_layout = QGridLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.module_filter = QComboBox()
        self.module_filter.addItems(["All Modules", "sales", "purchases", "inventory", "accounting", "hr", "payroll", "payments", "security", "audit", "workflows"])
        self.module_filter.setMinimumWidth(150)
        
        self.action_filter = QComboBox()
        self.action_filter.addItems(["All Actions", "CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "APPROVE", "REJECT"])
        self.action_filter.setMinimumWidth(150)
        
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Username...")
        self.user_filter.setMinimumHeight(30)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(datetime.now().date().addDays(-7))
        self.date_from.setMinimumHeight(30)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(datetime.now().date())
        self.date_to.setMinimumHeight(30)
        
        filter_layout.addWidget(QLabel("Module:"), 0, 0)
        filter_layout.addWidget(self.module_filter, 0, 1)
        filter_layout.addWidget(QLabel("Action:"), 0, 2)
        filter_layout.addWidget(self.action_filter, 0, 3)
        filter_layout.addWidget(QLabel("User:"), 0, 4)
        filter_layout.addWidget(self.user_filter, 0, 5)
        
        filter_layout.addWidget(QLabel("From:"), 1, 0)
        filter_layout.addWidget(self.date_from, 1, 1)
        filter_layout.addWidget(QLabel("To:"), 1, 2)
        filter_layout.addWidget(self.date_to, 1, 3)
        
        self.clear_btn = EnterpriseButton("Clear Filters", variant=ButtonVariant.SECONDARY)
        self.clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.clear_btn, 1, 5)
        
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        self.export_btn = EnterpriseButton("Export CSV", variant=ButtonVariant.PRIMARY)
        action_layout.addWidget(self.export_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("timestamp", "Timestamp", width=160),
            TableColumn("user", "User", width=120),
            TableColumn("module", "Module", width=100),
            TableColumn("action", "Action", width=100),
            TableColumn("model", "Model", width=100),
            TableColumn("object_id", "Object ID", width=80),
            TableColumn("ip_address", "IP Address", width=120),
            TableColumn("details", "Details", width=250),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)

    def _clear_filters(self):
        self.module_filter.setCurrentIndex(0)
        self.action_filter.setCurrentIndex(0)
        self.user_filter.clear()
        self.date_from.setDate(datetime.now().date().addDays(-7))
        self.date_to.setDate(datetime.now().date())
        self._load_audit_logs()

    def _load_audit_logs(self):
        self.status_label.setText("Loading...")
        self.table.setRowCount(0)
        
        # Build query parameters
        params = {}
        
        module = self.module_filter.currentText()
        if module != "All Modules":
            params['app_label'] = module
            
        action = self.action_filter.currentText()
        if action != "All Actions":
            params['action'] = action
            
        username = self.user_filter.text().strip()
        if username:
            params['search'] = username
            
        try:
            response = self._api_client.get('/api/audit/logs/', params=params)
            
            if response and 'data' in response:
                data = response['data']
                logs = data.get('results', data) if isinstance(data, dict) else data
                
                log_data = []
                for log in logs:
                    ts = log.get('created_at', '')[:19].replace('T', ' ')
                    log_data.append({
                        "timestamp": ts,
                        "user": log.get('user_username', 'System'),
                        "module": log.get('app_label', ''),
                        "action": log.get('action_display', log.get('action', '')),
                        "model": log.get('model_name', ''),
                        "object_id": str(log.get('object_id', '')),
                        "ip_address": log.get('ip_address', ''),
                        "details": log.get('object_repr', ''),
                        "is_error": log.get('is_error', False),
                    })
                self.table.set_data(log_data)
                for row, item in enumerate(log_data):
                    if item.get('is_error'):
                        action_cell = self.table.item(row, 3)
                        if action_cell:
                            from PySide6.QtGui import QColor; action_cell.setForeground(QColor(COLOR_DANGER))
                
                self.status_label.setText(f"Loaded {len(logs)} logs")
            else:
                self.status_label.setText("Error loading data")
                
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Audit log load error: {e}")

    def _show_details(self, item):
        row = item.row()
        # In a real app, we might want to fetch full details by ID or use cached data
        # For now, let's show what we have in a more structured way
        
        timestamp = self.table.item(row, 0).text()
        user = self.table.item(row, 1).text()
        module = self.table.item(row, 2).text()
        action = self.table.item(row, 3).text()
        entity = self.table.item(row, 4).text()
        entity_id = self.table.item(row, 5).text()
        details = self.table.item(row, 7).text()
        
        msg = "<b>Audit Event Details</b><br><br>"
        msg += f"<b>Time:</b> {timestamp}<br>"
        msg += f"<b>User:</b> {user}<br>"
        msg += f"<b>Module:</b> {module}<br>"
        msg += f"<b>Action:</b> {action}<br>"
        msg += f"<b>Entity:</b> {entity} (ID: {entity_id})<br><br>"
        msg += f"<b>Summary:</b> {details}<br>"

        AlertDialog.info("Audit Detail View", msg, self)
    
    def on_show(self):
        self._load_audit_logs()