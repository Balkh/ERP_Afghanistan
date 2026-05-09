from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Attendance screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                 QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                 QHeaderView, QAbstractItemView, QComboBox, QGroupBox,
                                 QDateEdit, QMessageBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                          BORDER_RADIUS_MD)


class AttendanceScreen(BaseScreen):
    """Attendance management screen."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="attendance_screen")
        self.api_client = api_client or APIClient()
        self.records = []
        self.setup_ui()
        self.load_attendance()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Attendance Log")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("⟳ Refresh")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_TEXT_MUTED};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BORDER};
            }}
        """)
        self.btn_refresh.clicked.connect(self.load_attendance)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filters
        filter_bar = QGroupBox("Filter by Date")
        filter_bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        filter_bar.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLOR_TEXT_SECONDARY};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(35)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: {SPACING_SM};
            }}
        """)
        self.date_edit.dateChanged.connect(self.load_attendance)
        filter_layout.addWidget(self.date_edit)
        
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading attendance records...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: {SPACING_XL + SPACING_MD};")
        self.loading_label.setVisible(False)

        self.empty_label = QLabel("No attendance records found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding: {SPACING_XL + SPACING_MD};")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading attendance records")
        self.error_label.setFont(QFont("Segoe UI", 12))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; padding: 40px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Table
        self.table = self._create_modern_table()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Employee", "Date", "Check In", "Check Out", "Status"
        ])
        layout.addWidget(self.table)

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {COLOR_BG_MAIN}; 
                color: {COLOR_TEXT_PRIMARY}; 
                border: none; 
                gridline-color: {COLOR_TABLE_BORDER_LIGHT};
            }}
            QHeaderView::section {{ 
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT}; 
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_SM}; 
                border: none; 
                border-bottom: 2px solid {COLOR_BORDER}; 
                font-weight: bold;
                font-size: 12px;
            }}
            QTableWidget::item {{ 
                padding: {SPACING_SM}; 
                border-bottom: 1px solid {COLOR_TEXT_SECONDARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY} !important;
                color: white !important;
                font-weight: bold;
            }}
            QTableWidget::item:hover:!selected {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: white;
            }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        return table
    
    def load_attendance(self):
        """Load attendance from API."""
        self.set_state(ScreenState.LOADING)
        try:
            endpoint = get_endpoint("attendance")
            if not endpoint:
                endpoint = "/api/hr/reports/attendance-summary/"
             
            response = self.api_client.get(endpoint)
            self.records = self._parse_response(response)
            
            # Update state based on data
            if len(self.records) == 0:
                self.set_state(ScreenState.EMPTY)
            else:
                self.set_state(ScreenState.READY)
        except Exception as e:
            print(f"Error loading attendance: {e}")
            self.records = []
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
        """Update table with attendance data and show appropriate state indicators."""
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            self.table.setItem(row, 0, QTableWidgetItem(str(record.get('id', ''))[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(record.get('employee_name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(str(record.get('date', ''))[:10]))
            self.table.setItem(row, 3, QTableWidgetItem(record.get('check_in', '')))
            self.table.setItem(row, 4, QTableWidgetItem(record.get('check_out', '')))
            self.table.setItem(row, 5, QTableWidgetItem(record.get('status', '')))
        
        # Show/hide indicators based on state
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.records) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.records) > 0)