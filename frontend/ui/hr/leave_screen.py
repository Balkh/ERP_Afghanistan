"""Leave management screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                 QLabel, QLineEdit)
from PySide6.QtCore import Qt
from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, MARGIN_PAGE, TEXT_PAGE_TITLE, TABLE_ROW_HEIGHT_MD, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
                           COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


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
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)
         
        header = QLabel("Leave Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header.setContentsMargins(0, 0, 0, SPACING_SM)
        layout.addWidget(header)
         
        toolbar = QHBoxLayout()
        toolbar.setSpacing(SPACING_SM)
         
        refresh_btn = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self.load_leave)
        toolbar.addWidget(refresh_btn)
         
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self.filter_leave)
        toolbar.addWidget(self.search_input)
         
        layout.addLayout(toolbar)
        
        # Loading indicator
        self.loading_label = QLabel("Loading leave records...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic; padding: {SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)
        
        # Error indicator
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {COLOR_DANGER}; padding: {SPACING_MD}px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Empty state indicator
        self.empty_label = QLabel("No leave records found")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic; padding: {SPACING_MD}px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)
         
        columns = [
            TableColumn("id", "ID", width=60),
            TableColumn("employee_name", "Employee", width=150),
            TableColumn("leave_type", "Type", width=100),
            TableColumn("start_date", "Start Date", width=100, align="center"),
            TableColumn("end_date", "End Date", width=100, align="center"),
            TableColumn("total_days", "Days", width=50, align="center"),
            TableColumn("status", "Status", width=80),
        ]
        self.table = EnterpriseTable(columns)
        self.table.setMinimumHeight(TABLE_ROW_HEIGHT_MD * 5)
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
            self.leave_records = extract_list(response)
            
            # Update state based on data
            if len(self.leave_records) == 0:
                self.set_state(ScreenState.EMPTY)
            else:
                self.set_state(ScreenState.READY)
        except Exception as e:
            self.error_label.setText(f"Error loading leave: {e}")
            self.leave_records = []
            self.set_state(ScreenState.ERROR)
        
        self.update_table()
    
    def update_table(self):
        """Update table with leave data and show appropriate state indicators."""
        state = self.state
        self.loading_label.setVisible(state == ScreenState.LOADING)
        self.error_label.setVisible(state == ScreenState.ERROR)
        self.empty_label.setVisible(state == ScreenState.EMPTY and len(self.leave_records) == 0)
        self.table.setVisible(state == ScreenState.READY and len(self.leave_records) > 0)

        data = []
        for record in self.leave_records:
            data.append({
                "id": str(record.get('id', ''))[:8],
                "employee_name": record.get('employee_name', ''),
                "leave_type": record.get('leave_type', ''),
                "start_date": str(record.get('start_date', ''))[:10],
                "end_date": str(record.get('end_date', ''))[:10],
                "total_days": str(record.get('total_days', 0)),
                "status": record.get('status', ''),
            })
        self.table.set_data(data)
    
    def filter_leave(self, text):
        """Filter leave records by search text."""
        all_data = []
        for record in self.leave_records:
            all_data.append({
                "id": str(record.get('id', ''))[:8],
                "employee_name": record.get('employee_name', ''),
                "leave_type": record.get('leave_type', ''),
                "start_date": str(record.get('start_date', ''))[:10],
                "end_date": str(record.get('end_date', ''))[:10],
                "total_days": str(record.get('total_days', 0)),
                "status": record.get('status', ''),
            })

        if not text:
            self.table.set_data(all_data)
            return

        filtered = [r for r in all_data if text.lower() in str(r.get('employee_name', '')).lower() or text.lower() in str(r.get('leave_type', '')).lower()]
        self.table.set_data(filtered)