import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                                  QComboBox, QFormLayout, QWidget)
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, SPACING_SM, TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, EnterpriseDialog, DialogType
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
        self.add_btn.clicked.connect(self._show_add_dialog)
        header_layout.addWidget(self.add_btn)
        
        self.edit_btn = EnterpriseButton(text="Edit", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.edit_btn.clicked.connect(self._show_edit_dialog)
        self.edit_btn.setEnabled(False)
        header_layout.addWidget(self.edit_btn)
        
        self.delete_btn = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.delete_btn.clicked.connect(self._delete_entity)
        self.delete_btn.setEnabled(False)
        header_layout.addWidget(self.delete_btn)
        
        self.refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.refresh_btn.clicked.connect(self.load_entities)
        header_layout.addWidget(self.refresh_btn)
        
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
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        has_selection = bool(selected)
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def load_entities(self):
        def on_success(response):
            if response and response.get('success'):
                self.entities_data = response.get('data', {}).get('results', [])
                self._populate_table()

        self.run_api_request(
            key="entities_load",
            method="GET",
            endpoint="/api/entities/entities/",
            on_success=on_success,
            on_error=lambda message: logging.getLogger(__name__).warning(f"Failed to load entities: {message}"),
        )

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

    def _get_selected_entity(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        code = self.table.item(row, 0).text()
        return next((e for e in self.entities_data if e.get('code') == code), None)

    def _show_add_dialog(self):
        dialog = EntityDialog(api_client=self._api_client, parent=self)
        if dialog.exec():
            self.load_entities()

    def _show_edit_dialog(self):
        entity = self._get_selected_entity()
        if not entity:
            return
        dialog = EntityDialog(api_client=self._api_client, entity=entity, parent=self)
        if dialog.exec():
            self.load_entities()

    def _delete_entity(self):
        entity = self._get_selected_entity()
        if not entity:
            return
        from ui.components.dialogs import ConfirmDialog
        if ConfirmDialog.confirm("Delete Entity", f"Are you sure you want to delete '{entity.get('name')}'?", self):
            def on_success(response):
                if response and isinstance(response, dict) and response.get("success"):
                    AlertDialog.info("Success", "Entity deleted successfully.", self)
                    self.load_entities()
                else:
                    error = response.get("error", "Delete failed") if isinstance(response, dict) else "Delete failed"
                    AlertDialog.error("Error", str(error), self)

            self.run_api_request(
                key=f"entity_delete_{entity['id']}",
                method="DELETE",
                endpoint=f"/api/entities/entities/{entity['id']}/",
                on_success=on_success,
                on_error=lambda message: AlertDialog.error("Error", f"Failed to delete entity: {message}", self),
            )


class EntityDialog(EnterpriseDialog):
    """Dialog for creating/editing entities."""
    
    def __init__(self, api_client=None, entity=None, parent=None):
        self._api_client = api_client
        self._entity = entity
        self._submitting = False
        title = "Edit Entity" if entity else "Add Entity"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.setMinimumWidth(450)
        content = self._build_content()
        self.set_content(content)

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        form = QFormLayout()
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Entity code")
        if self._entity:
            self.code_input.setText(self._entity.get("code", ""))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Entity name")
        if self._entity:
            self.name_input.setText(self._entity.get("name", ""))
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["COMPANY", "BRANCH", "DEPARTMENT", "DIVISION"])
        if self._entity:
            idx = self.type_combo.findText(self._entity.get("entity_type", "COMPANY"))
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone number")
        if self._entity:
            self.phone_input.setText(self._entity.get("phone", ""))
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        if self._entity:
            self.email_input.setText(self._entity.get("email", ""))
        
        form.addRow("Code:", self.code_input)
        form.addRow("Name:", self.name_input)
        form.addRow("Type:", self.type_combo)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Email:", self.email_input)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        return widget

    def _save(self):
        if self._submitting:
            return
        self._submitting = True
        
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()
        
        if not code or not name:
            AlertDialog.warning("Validation Error", "Code and Name are required.", self)
            self._submitting = False
            return
        
        data = {
            "code": code,
            "name": name,
            "entity_type": self.type_combo.currentText(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
        }
        
        def on_success(response):
            self._submitting = False
            if response and isinstance(response, dict) and (response.get("success") or response.get("id")):
                self.accept()
            else:
                error = response.get("error", "Save failed") if isinstance(response, dict) else "Save failed"
                AlertDialog.error("Error", str(error), self)

        def on_error(message):
            self._submitting = False
            AlertDialog.error("Error", f"Failed to save entity: {message}", self)

        started = self.run_api_request(
            key="entity_save",
            method="PUT" if self._entity else "POST",
            endpoint=f"/api/entities/entities/{self._entity['id']}/" if self._entity else "/api/entities/entities/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self._submitting = False
