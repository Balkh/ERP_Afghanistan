"""Backup & Restore screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                QLabel, QLineEdit,
                                QHeaderView, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER,
                           BORDER_RADIUS_MD,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                           COLOR_BORDER, COLOR_BORDER_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen


class BackupScreen(BaseScreen):
    """Backup & Restore management screen."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="backup")
        self.api_client = api_client or APIClient()
        self.restore_points = []
        self.setup_ui()
        self.load_restore_points()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        
        header = QLabel("Backup & Restore")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)
        
        toolbar = QHBoxLayout()
        
        create_btn = EnterpriseButton(text="Create Backup", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        create_btn.clicked.connect(self.create_backup)
        toolbar.addWidget(create_btn)
        
        refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self.load_restore_points)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        status_group = QGroupBox("System Status")
        status_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {TEXT_CARD_TITLE}pt;
                font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
        """)
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Checking backup status...")
        self.status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        points_label = QLabel("Restore Points")
        points_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_SECTION_TITLE}pt; font-weight: 700;")
        layout.addWidget(points_label)
        
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("name", "Name", width=200),
            TableColumn("created", "Created", width=150),
            TableColumn("size", "Size", width=80, align="right"),
            TableColumn("type", "Type", width=100),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.table = EnterpriseTable(columns)
        layout.addWidget(self.table)
    
    def load_restore_points(self):
        """Load restore points from API."""
        try:
            endpoint = get_endpoint("restore_points")
            if not endpoint:
                endpoint = "/api/backup/restore-points/"
            
            response = self.api_client.get(endpoint)
            self.restore_points = self._parse_response(response)
            self.update_table()
            self.status_label.setText(f"Last backup: {len(self.restore_points)} restore points available")
        except Exception as e:
            print(f"Error loading restore points: {e}")
            self.restore_points = []
            self.update_table()
            self.status_label.setText("Status: Unable to connect to backup service")
    
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
        """Update table with restore points."""
        data = []
        for point in self.restore_points:
            data.append({
                "id": str(point.get('id', ''))[:8],
                "name": point.get('name', ''),
                "created": str(point.get('created_at', ''))[:19],
                "size": point.get('size', ''),
                "type": point.get('backup_type', ''),
                "status": point.get('status', 'READY'),
            })
        self.table.set_data(data)
    
    def create_backup(self):
        """Create new backup via API."""
        reply = QMessageBox.question(
            self, "Create Backup",
            "Are you sure you want to create a new backup?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                response = self.api_client.post("/api/backup/records/create_backup/", {
                    "description": "Manual backup from UI",
                    "encrypted": True,
                    "compressed": True,
                })
                if isinstance(response, dict) and response.get("success"):
                    QMessageBox.information(
                        self, "Backup",
                        "Backup creation started. This may take a few minutes."
                    )
                    self.load_restore_points()
                else:
                    err_msg = "Unknown error"
                    if isinstance(response, dict):
                        err_info = response.get("error", {})
                        if isinstance(err_info, dict):
                            err_msg = err_info.get("message", err_msg)
                    QMessageBox.warning(self, "Backup Failed", f"Failed to create backup: {err_msg}")
            except Exception as e:
                QMessageBox.warning(self, "Backup Failed", f"Failed to create backup: {e}")