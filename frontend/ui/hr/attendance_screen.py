"""Attendance screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                 QLabel, QGroupBox,
                                 QDateEdit)
from PySide6.QtCore import Qt, QDate
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, TEXT_PAGE_TITLE,
                           TEXT_BODY, TEXT_LABEL, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


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
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_attendance)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filters
        filter_bar = QGroupBox("Filter by Date")
        filter_bar.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                margin-top: {SPACING_SM}px;
                padding-top: {SPACING_SM}px;
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_LABEL}pt;
                font-weight: 700;
            }}
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        filter_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(35)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load_attendance)
        filter_layout.addWidget(self.date_edit)
        
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading attendance records...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)

        self.empty_label = QLabel("No attendance records found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading attendance records")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XXL + SPACING_LG}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Table
        columns = [
            TableColumn("id", "ID", width=60),
            TableColumn("employee_name", "Employee", width=150),
            TableColumn("date", "Date", width=100, align="center"),
            TableColumn("check_in", "Check In", width=80, align="center"),
            TableColumn("check_out", "Check Out", width=80, align="center"),
            TableColumn("status", "Status", width=80),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)
    
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
            self.error_label.setText(f"Error loading attendance: {e}")
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
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.records) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.records) > 0)

        data = []
        for record in self.records:
            data.append({
                "id": str(record.get('id', ''))[:8],
                "employee_name": record.get('employee_name', ''),
                "date": str(record.get('date', ''))[:10],
                "check_in": record.get('check_in', ''),
                "check_out": record.get('check_out', ''),
                "status": record.get('status', ''),
            })
        self.table.set_data(data)