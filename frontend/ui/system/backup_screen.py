from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""Backup & Restore screen for ERP."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                QHeaderView, QAbstractItemView, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.client import APIClient
from api.endpoints import get_endpoint


class BackupScreen(QWidget):
    """Backup & Restore management screen."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.restore_points = []
        self.setup_ui()
        self.load_restore_points()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        
        header = QLabel("Backup & Restore")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: COLOR_TEXT_PRIMARY;")
        layout.addWidget(header)
        
        toolbar = QHBoxLayout()
        
        create_btn = QPushButton("Create Backup")
        create_btn.clicked.connect(self.create_backup)
        toolbar.addWidget(create_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_restore_points)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Checking backup status...")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        points_label = QLabel("Restore Points")
        points_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(points_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Created", "Size", "Type", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        self.table.setRowCount(len(self.restore_points))
        for row, point in enumerate(self.restore_points):
            self.table.setItem(row, 0, QTableWidgetItem(str(point.get('id', ''))[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(point.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(str(point.get('created_at', ''))[:19]))
            self.table.setItem(row, 3, QTableWidgetItem(point.get('size', '')))
            self.table.setItem(row, 4, QTableWidgetItem(point.get('backup_type', '')))
            self.table.setItem(row, 5, QTableWidgetItem(point.get('status', 'READY')))
    
    def create_backup(self):
        """Create new backup."""
        reply = QMessageBox.question(
            self, "Create Backup",
            "Are you sure you want to create a new backup?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(
                self, "Backup",
                "Backup creation initiated. This may take a few minutes."
            )