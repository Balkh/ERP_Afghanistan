import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit, QComboBox, QGroupBox,
                                  QFormLayout, QCheckBox, QColorDialog, 
                                  QFileDialog, QScrollArea, QFrame, QWidget)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, TEXT_PAGE_TITLE, BUTTON_HEIGHT_MD, COLOR_BG_SURFACE, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_SUCCESS, COLOR_TEXT_ON_PRIMARY)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.forms import FormSection
from utils.invoice_template_engine import InvoiceTemplateEngine
from api.client import APIClient

class InvoiceTemplateManager(BaseScreen):
    """Manager for dynamic invoice templates and branding."""
    
    def __init__(self, parent=None, screen_id="invoice_template_manager", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client or APIClient()
        self.template_engine = InvoiceTemplateEngine()
        self.current_template_id = None
        self.current_config = self.template_engine.DEFAULT_CONFIG.copy()
        self._setup_ui()
        self._load_active_template()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Invoice Template Manager")
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.save_btn = EnterpriseButton(text="Save Changes", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.save_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
        self.save_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: {COLOR_TEXT_ON_PRIMARY}; font-weight: bold;")
        self.save_btn.clicked.connect(self._save_template)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)

        # Main content with splitter/scroll
        content_layout = QHBoxLayout()
        
        # Left side: Settings
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.NoFrame)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # 1. Template Type
        type_section = FormSection("General")
        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("Template Name (e.g. My Pharmacy Standard)")
        self.layout_type = QComboBox()
        self.layout_type.addItems(["detailed", "compact"])
        
        type_section.add_field(self.template_name, "Template Name:")
        type_section.add_field(self.layout_type, "Layout Type:")
        settings_layout.addWidget(type_section)
        
        # 2. Branding (Colors & Logo)
        brand_section = FormSection("Branding")
        
        self.primary_color_btn = EnterpriseButton(text="Select Primary Color", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.primary_color_btn.clicked.connect(lambda: self._pick_color("primary"))
        
        self.accent_color_btn = EnterpriseButton(text="Select Accent Color", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.accent_color_btn.clicked.connect(lambda: self._pick_color("accent"))
        
        self.logo_path = QLineEdit()
        self.logo_path.setReadOnly(True)
        self.logo_btn = EnterpriseButton(text="Browse Logo", variant=ButtonVariant.GHOST, size=ButtonSize.SMALL)
        self.logo_btn.clicked.connect(self._browse_logo)
        
        logo_layout = QHBoxLayout()
        logo_layout.addWidget(self.logo_path)
        logo_layout.addWidget(self.logo_btn)
        
        logo_container = QWidget()
        logo_container.setLayout(logo_layout)
        
        brand_section.add_field(self.primary_color_btn, "Primary Color:")
        brand_section.add_field(self.accent_color_btn, "Accent Color:")
        brand_section.add_field(logo_container, "Logo Override:")
        settings_layout.addWidget(brand_section)
        
        # 3. Content Settings
        content_section = FormSection("Content & Visibility")
        
        self.footer_text = QLineEdit()
        self.footer_text.setPlaceholderText("Footer message...")
        
        self.show_qr = QCheckBox("Show QR Code in Footer")
        
        content_section.add_field(self.footer_text, "Footer Text:")
        content_section.add_field(self.show_qr, "Features:")
        
        # Visibility toggles
        self.vis_batch = QCheckBox("Show Batch Numbers")
        self.vis_discount = QCheckBox("Show Discounts")
        self.vis_tax = QCheckBox("Show Tax Column")
        
        content_section.add_field(self.vis_batch, "Visibility:")
        content_section.add_field(self.vis_discount, "")
        content_section.add_field(self.vis_tax, "")
        
        settings_layout.addWidget(content_section)
        settings_layout.addStretch()
        
        settings_scroll.setWidget(settings_widget)
        content_layout.addWidget(settings_scroll, 1)
        
        # Right side: Live Preview (Simplified)
        preview_group = QGroupBox("Live Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Preview will reflect your changes after saving.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border: 1px dashed {COLOR_BORDER};")
        preview_layout.addWidget(self.preview_label)
        
        content_layout.addWidget(preview_group, 1)
        
        layout.addLayout(content_layout)

    def _pick_color(self, key):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_config["color_theme"][key] = color.name()
            # Update button style to show color
            btn = self.primary_color_btn if key == "primary" else self.accent_color_btn
            btn.setStyleSheet(f"background-color: {color.name()}; color: {COLOR_TEXT_ON_PRIMARY};")

    def _browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.logo_path.setText(file_path)

    def _load_active_template(self):
        try:
            response = self._api_client.get("/api/core/invoice-templates/active/")
            if response:
                self.current_template_id = response.get("id")
                self.template_name.setText(response.get("name", "Standard"))
                config = response.get("config", {})
                self.current_config.update(config)
                self._update_ui_from_config()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load template: {e}")

    def _update_ui_from_config(self):
        c = self.current_config
        self.layout_type.setCurrentText(c.get("layout_type", "detailed"))
        self.footer_text.setText(c.get("footer_text", ""))
        self.show_qr.setChecked(c.get("show_qr", True))
        
        vis = c.get("field_visibility", {})
        self.vis_batch.setChecked(vis.get("batch", True))
        self.vis_discount.setChecked(vis.get("discount", True))
        self.vis_tax.setChecked(vis.get("tax", True))
        
        # Colors
        colors = c.get("color_theme", {})
        if "primary" in colors:
            self.primary_color_btn.setStyleSheet(f"background-color: {colors['primary']}; color: {COLOR_TEXT_ON_PRIMARY};")
        if "accent" in colors:
            self.accent_color_btn.setStyleSheet(f"background-color: {colors['accent']}; color: {COLOR_TEXT_ON_PRIMARY};")

    def _save_template(self):
        # Update config from UI
        self.current_config["layout_type"] = self.layout_type.currentText()
        self.current_config["footer_text"] = self.footer_text.text()
        self.current_config["show_qr"] = self.show_qr.isChecked()
        self.current_config["field_visibility"] = {
            "batch": self.vis_batch.isChecked(),
            "discount": self.vis_discount.isChecked(),
            "tax": self.vis_tax.isChecked(),
            "notes": True,
            "phone": True,
            "address": True
        }
        
        data = {
            "name": self.template_name.text(),
            "is_active": True,
            "config": self.current_config
        }
        
        try:
            if self.current_template_id:
                res = self._api_client.put(f"/api/core/invoice-templates/{self.current_template_id}/", data)
            else:
                res = self._api_client.post("/api/core/invoice-templates/", data)
            
            if res:
                AlertDialog.info("Success", "Invoice template saved successfully!", self)
                self.current_template_id = res.get("id")
        except Exception as e:
            AlertDialog.error("Error", f"Failed to save template: {e}", self)
