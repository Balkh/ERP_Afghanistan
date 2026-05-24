from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QMessageBox)
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from api.client import APIClient

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
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.add_btn = EnterpriseButton(text="+ Add Entity", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.add_btn.clicked.connect(self.show_add_entity_dialog)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)

        # Table
        columns = [
            TableColumn("code", "Code", width=80),
            TableColumn("name", "Name", width=200),
            TableColumn("type", "Type", width=100),
            TableColumn("phone", "Phone", width=120),
            TableColumn("status", "Status", width=80, align="center"),
            TableColumn("is_default", "Default", width=60, align="center"),
        ]
        self.table = EnterpriseTable(columns)
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
        data = []
        for ent in self.entities_data:
            data.append({
                "code": ent.get('code', ''),
                "name": ent.get('name', ''),
                "type": ent.get('entity_type', ''),
                "phone": ent.get('phone', ''),
                "status": "Active" if ent.get('is_active') else "Inactive",
                "is_default": "Yes" if ent.get('is_default') else "No",
            })
        self.table.set_data(data)

    def show_add_entity_dialog(self):
        QMessageBox.information(self, "Entity Management", "Entity creation is available in the admin panel.")
