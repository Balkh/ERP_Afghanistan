from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Audit log screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QGroupBox,
                                  QTextEdit, QDateEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from datetime import datetime
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, FONT_SIZE_XL, BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD)


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
        self.btn_refresh.clicked.connect(self._load_audit_logs)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        filter_bar = QGroupBox("Filter Logs")
        filter_bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        filter_bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 10px; }}")
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
        
        self.clear_btn = QPushButton("Clear Filters")
        self.clear_btn.setStyleSheet(f"background-color: {COLOR_TEXT_SECONDARY}; color: white; border-radius: 5px; padding: 5px 15px;")
        self.clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.clear_btn, 1, 5)
        
        layout.addWidget(filter_bar)
        
        action_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setMinimumHeight(38)
        self.export_btn.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; padding: 0 15px;")
        action_layout.addWidget(self.export_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.table = self._create_modern_table()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Timestamp", "User", "Module", "Action", "Entity", "Entity ID", "IP Address", "Details"])
        layout.addWidget(self.table)
        
        # Connect filters to auto-refresh
        self.module_filter.currentIndexChanged.connect(self._load_audit_logs)
        self.action_filter.currentIndexChanged.connect(self._load_audit_logs)
        self.user_filter.returnPressed.connect(self._load_audit_logs)

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ border: none; gridline-color: #f1f2f6; }}
            QHeaderView::section {{ background-color: {COLOR_TABLE_HEADER_BG_LIGHT}; padding: 8px; border: none; border-bottom: 2px solid {COLOR_TABLE_BORDER_LIGHT}; font-weight: bold; }}
            QTableWidget::item {{ padding: 10px; }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.itemDoubleClicked.connect(self._show_details)
        return table

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
                
                self.table.setRowCount(len(logs))
                for i, log in enumerate(logs):
                    # Timestamp
                    ts = log.get('created_at', '')[:19].replace('T', ' ')
                    self.table.setItem(i, 0, QTableWidgetItem(ts))
                    
                    # User
                    self.table.setItem(i, 1, QTableWidgetItem(log.get('user_username', 'System')))
                    
                    # Module
                    self.table.setItem(i, 2, QTableWidgetItem(log.get('app_label', '')))
                    
                    # Action
                    action_item = QTableWidgetItem(log.get('action_display', log.get('action', '')))
                    if log.get('is_error'): action_item.setForeground(QColor("COLOR_DANGER"))
                    self.table.setItem(i, 3, action_item)
                    
                    # Entity
                    self.table.setItem(i, 4, QTableWidgetItem(log.get('model_name', '')))
                    
                    # ID
                    self.table.setItem(i, 5, QTableWidgetItem(str(log.get('object_id', ''))))
                    
                    # IP
                    self.table.setItem(i, 6, QTableWidgetItem(log.get('ip_address', '')))
                    
                    # Details (Object Repr)
                    self.table.setItem(i, 7, QTableWidgetItem(log.get('object_repr', '')))
                    
                    self.table.setRowHeight(i, TABLE_ROW_HEIGHT_MD)
                
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
        
        msg = f"<b>Audit Event Details</b><br><br>"
        msg += f"<b>Time:</b> {timestamp}<br>"
        msg += f"<b>User:</b> {user}<br>"
        msg += f"<b>Module:</b> {module}<br>"
        msg += f"<b>Action:</b> {action}<br>"
        msg += f"<b>Entity:</b> {entity} (ID: {entity_id})<br><br>"
        msg += f"<b>Summary:</b> {details}<br>"
        
        # Show in a custom dialog for better formatting if needed, 
        # but QMessageBox with RichText works for now
        detail_box = QMessageBox(self)
        detail_box.setWindowTitle("Audit Detail View")
        detail_box.setTextFormat(Qt.RichText)
        detail_box.setText(msg)
        detail_box.setStandardButtons(QMessageBox.Ok)
        detail_box.exec()
    
    def on_show(self):
        self._load_audit_logs()