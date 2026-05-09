from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, 
                                  QGroupBox, QFormLayout, QDialog, QDialogButtonBox,
                                  QTextEdit, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD)
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)

class EntityManagementScreen(BaseScreen):
    """Screen for managing business entities and branches."""
    
    def __init__(self, parent=None, screen_id="entities", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client or APIClient()
        self.entities_data = []
        self._setup_ui()
        self.load_entities()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Business Entities & Branches")
        title_label.setFont(QFont("Segoe UI", FONT_SIZE_XL, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("+ Add Entity")
        self.add_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.add_btn.setStyleSheet("background-color: COLOR_SUCCESS; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.show_add_entity_dialog)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Code", "Name", "Type", "Phone", "Status", "Default"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_entities(self):
        try:
            response = self._api_client.get("/api/entities/entities/")
            if response and response.get('success'):
                self.entities_data = response['data'].get('results', [])
                self._populate_table()
        except Exception as e:
            print(f"Failed to load entities: {e}")

    def _populate_table(self):
        self.table.setRowCount(0)
        for ent in self.entities_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(ent.get('code', '')))
            self.table.setItem(row, 1, QTableWidgetItem(ent.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(ent.get('entity_type', '')))
            self.table.setItem(row, 3, QTableWidgetItem(ent.get('phone', '')))
            
            status = "Active" if ent.get('is_active') else "Inactive"
            status_item = QTableWidgetItem(status)
            if not ent.get('is_active'):
                status_item.setForeground(QColor("COLOR_DANGER"))
            self.table.setItem(row, 4, status_item)
            
            default_item = QTableWidgetItem("Yes" if ent.get('is_default') else "No")
            self.table.setItem(row, 5, default_item)

    def show_add_entity_dialog(self):
        QMessageBox.information(self, "Entity Management", "Entity creation is available in the admin panel.")
