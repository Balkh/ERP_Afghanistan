import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFrame, QWidget,
                                QLineEdit, QSpinBox, QLabel, QComboBox)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_XL, SPACING_XXL, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_BG_DIALOG, COLOR_BORDER_INPUT,
                           COLOR_BORDER_INPUT_HOVER, COLOR_FORM_FOOTER_BORDER, BORDER_RADIUS_MD,
                           DIALOG_WIDTH_FORM_MIN, DIALOG_WIDTH_FORM_PREFERRED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from theme.style_builder import UIStyleBuilder


class WarehouseFormDialog(EnterpriseDialog):
    """Enterprise warehouse form with enhanced visual hierarchy."""

    def __init__(self, parent=None, warehouse_id=None, api_client=None):
        title = "Add Warehouse" if warehouse_id is None else "Edit Warehouse"
        super().__init__(title, DialogType.CUSTOM, parent)
        self.warehouse_id = warehouse_id
        self.api_client = api_client
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.accept)
        if warehouse_id:
            self.load_warehouse_data()

    def _build_content(self):
        content = QWidget()
        # Removed hardcoded CSS to rely on UIStyleBuilder and Global Styles
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_MD)

        subtitle = QLabel("Configure warehouse properties")
        subtitle.setStyleSheet(UIStyleBuilder.get_subtitle_style())
        layout.addWidget(subtitle)

        sec = FormSection("Warehouse Details", columns=2, primary=True)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Main Warehouse")
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g., Floor 2, Building A")
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(0, 999999)
        self.capacity_input.setValue(1000)
        self.active_check = QComboBox()
        self.active_check.addItems(["No", "Yes"])
        self.active_check.setCurrentIndex(1)
        
        sec.add_field_pair("Name*", self.name_input, "Location", self.location_input, required1=True,
                           helper2="e.g., Floor 2, Building A, Main Campus")
        sec.add_field_pair("Capacity", self.capacity_input, "Is Active", self.active_check,
                           helper1="Max storage units for this warehouse")
        layout.addWidget(sec)

        return content

    def _create_button_area(self):
        button_area = QFrame()
        button_area.setFixedHeight(60)

        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(SPACING_XXL, SPACING_SM, SPACING_XXL, SPACING_SM)

        layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        button_area.setObjectName("card")
        button_area.setStyleSheet(UIStyleBuilder.get_card_style())
        return button_area

    def load_warehouse_data(self):
        def on_success(response):
            warehouse = response.get('data', {}) if isinstance(response, dict) and response.get('success') else response
            if warehouse:
                self.name_input.setText(warehouse.get("name") or "")
                self.location_input.setText(warehouse.get("location") or "")
                self.capacity_input.setValue(warehouse.get("capacity") or 0)
                self.active_check.setCurrentIndex(1 if warehouse.get("is_active") else 0)

        def on_error(message):
            logging.getLogger(__name__).warning(f"Error loading warehouse data: {message}")

        self.run_api_request(
            key=f"warehouse_form_load_{self.warehouse_id}",
            method="GET",
            endpoint=f"/api/inventory/warehouses/{self.warehouse_id}/",
            on_success=on_success,
            on_error=on_error,
        )

    def get_form_data(self):
        return {
            "name": self.name_input.text().strip(),
            "location": self.location_input.text().strip(),
            "capacity": self.capacity_input.value(),
            "is_active": self.active_check.currentText() == "Yes",
        }

    def accept(self):
        name = self.name_input.text().strip()
        if not name:
            AlertDialog.warning("Validation Error", "Warehouse name is required.", self)
            return
        data = self.get_form_data()

        def on_success(response):
            if isinstance(response, dict) and (response.get('success') or 'id' in response):
                super(WarehouseFormDialog, self).accept()
            else:
                error_msg = response.get('error', {}).get('message', "Unknown error occurred.") if isinstance(response, dict) else "Unknown error occurred."
                AlertDialog.error("Error", f"Failed to save warehouse: {error_msg}", self)

        def on_error(message):
            AlertDialog.error("Error", f"Server communication error: {message}", self)

        self.run_api_request(
            key="warehouse_form_save",
            method="PUT" if self.warehouse_id else "POST",
            endpoint=f"/api/inventory/warehouses/{self.warehouse_id}/" if self.warehouse_id else "/api/inventory/warehouses/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
