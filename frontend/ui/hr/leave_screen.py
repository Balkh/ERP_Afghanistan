from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_BG_BUTTON_LIGHT, COLOR_SECONDARY_BG)
"""Leave management screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                 QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                 QHeaderView, QAbstractItemView, QComboBox, QGroupBox,
                                 QDateEdit, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                          BORDER_RADIUS_MD)


class LeaveScreen(BaseScreen):
    """Leave management screen."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="leave_screen")
        self.api_client = api_client or APIClient()
        self.leave_records = []
        self.setup_ui()
        self.load_leave()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)
         
        header = QLabel("Leave Management")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: COLOR_TEXT_PRIMARY;")
        header.setContentsMargins(0, 0, 0, SPACING_SM)
        layout.addWidget(header)
         
        toolbar = QHBoxLayout()
        toolbar.setSpacing(SPACING_SM)
         
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BG_BUTTON_LIGHT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SECONDARY_BG};
            }}
        """)
        refresh_btn.clicked.connect(self.load_leave)
        toolbar.addWidget(refresh_btn)
         
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setMinimumHeight(35)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: COLOR_TEXT_SECONDARY;
                color: COLOR_TEXT_PRIMARY;
                border: 1px solid COLOR_BORDER;
                border-radius: 6px;
                padding: 8px;
            }
            QLineEdit:focus {
                border-color: COLOR_PRIMARY;
            }
        """)
        self.search_input.textChanged.connect(self.filter_leave)
        toolbar.addWidget(self.search_input)
         
        layout.addLayout(toolbar)
        
        # Loading indicator
        self.loading_label = QLabel("Loading leave records...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-style: italic;
                padding: 12px;
            }
        """)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)
        
        # Error indicator
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                padding: 12px;
            }
        """)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Empty state indicator
        self.empty_label = QLabel("No leave records found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 12px;
            }
        """)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)
         
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Employee", "Type", "Start Date", "End Date", "Days", "Status"
        ])
        self.table.setStyleSheet("""
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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setMinimumHeight(TABLE_ROW_HEIGHT_MD * 5)
        self.table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)
        self.table.setVisible(False)
        layout.addWidget(self.table)
    
    def load_leave(self):
        """Load leave from API."""
        self.set_state(ScreenState.LOADING)
        try:
            endpoint = get_endpoint("leave")
            if not endpoint:
                endpoint = "/api/hr/reports/leave-summary/"
             
            response = self.api_client.get(endpoint)
            self.leave_records = self._parse_response(response)
            
            # Update state based on data
            if len(self.leave_records) == 0:
                self.set_state(ScreenState.EMPTY)
            else:
                self.set_state(ScreenState.READY)
        except Exception as e:
            print(f"Error loading leave: {e}")
            self.leave_records = []
            self.set_state(ScreenState.ERROR)
        
        self.update_table()
    
    def _parse_response(self, response):
        """Parse API response."""
        if isinstance(response, list):
            return [r for r in response if isinstance(r, dict)]
        elif isinstance(response, dict):
            if response.get('success'):
                data = response.get('data', [])
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)]
        return []
    
    def update_table(self):
        """Update table with leave data and show appropriate state indicators."""
        self.table.setRowCount(len(self.leave_records))
        for row, record in enumerate(self.leave_records):
            self.table.setItem(row, 0, QTableWidgetItem(str(record.get('id', ''))[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(record.get('employee_name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(record.get('leave_type', '')))
            self.table.setItem(row, 3, QTableWidgetItem(str(record.get('start_date', ''))[:10]))
            self.table.setItem(row, 4, QTableWidgetItem(str(record.get('end_date', ''))[:10]))
            self.table.setItem(row, 5, QTableWidgetItem(str(record.get('total_days', 0))))
            self.table.setItem(row, 6, QTableWidgetItem(record.get('status', '')))
        
        # Show/hide indicators based on state
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.leave_records) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.leave_records) > 0)
    
    def filter_leave(self, text):
        """Filter leave records by search text."""
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match and text != "")