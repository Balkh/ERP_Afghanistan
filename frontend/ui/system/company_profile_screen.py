"""Company Profile screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLabel, QLineEdit, QTextEdit, QGroupBox,
                                QComboBox, QFileDialog, QScrollArea, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_MD, SPACING_LG, TEXT_PAGE_TITLE, INPUT_HEIGHT_MD, COLOR_BG_SURFACE, COLOR_BORDER,
                          BORDER_RADIUS_MD, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.forms import FormSection


class CompanyProfileScreen(BaseScreen):
    """Company profile screen — edit company details via API."""

    def __init__(self, parent=None, screen_id="company_profile", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._company_id = None
        self._logo_path = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)

        title = QLabel("Company Profile")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(0)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(SPACING_LG)

        # Identity section
        identity_section = FormSection("Company Identity", primary=True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Company name")
        self.name_edit.setMinimumHeight(INPUT_HEIGHT_MD)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Short code (e.g., PHARMA)")
        self.code_edit.setMinimumHeight(INPUT_HEIGHT_MD)

        self.tax_edit = QLineEdit()
        self.tax_edit.setPlaceholderText("Tax registration number")
        self.tax_edit.setMinimumHeight(INPUT_HEIGHT_MD)

        identity_section.add_field(self.name_edit, "Company Name:")
        identity_section.add_field(self.code_edit, "Company Code:")
        identity_section.add_field(self.tax_edit, "Tax Number:")
        container_layout.addWidget(identity_section)

        # Contact section
        contact_section = FormSection("Contact Information")

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("contact@company.com")
        self.email_edit.setMinimumHeight(INPUT_HEIGHT_MD)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+93 XX XXX XXXX")
        self.phone_edit.setMinimumHeight(INPUT_HEIGHT_MD)

        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Full address")
        self.address_edit.setMaximumHeight(80)

        contact_section.add_field(self.email_edit, "Email:")
        contact_section.add_field(self.phone_edit, "Phone:")
        contact_section.add_field(self.address_edit, "Address:")
        container_layout.addWidget(contact_section)

        # Currency section
        currency_section = FormSection("Currency Settings")

        self.default_currency = QComboBox()
        self.default_currency.addItems(["AFN", "USD", "EUR", "PKR", "IRR"])

        self.secondary_currency = QComboBox()
        self.secondary_currency.addItems(["USD", "AFN", "EUR", "PKR", "IRR"])

        currency_section.add_field(self.default_currency, "Default Currency:")
        currency_section.add_field(self.secondary_currency, "Secondary Currency:")
        container_layout.addWidget(currency_section)

        # Logo section
        logo_group = QGroupBox("Company Logo")
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(SPACING_MD)

        self.logo_label = QLabel("No logo uploaded")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; background: {COLOR_BG_SURFACE}; "
            f"border: 1px dashed {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_LG}px;"
        )
        self.logo_label.setMinimumHeight(120)
        logo_layout.addWidget(self.logo_label)

        logo_buttons = QHBoxLayout()
        upload_btn = EnterpriseButton(text="Upload Logo", variant=ButtonVariant.SECONDARY, size=ButtonSize.SMALL)
        upload_btn.clicked.connect(self._upload_logo)
        remove_btn = EnterpriseButton(text="Remove Logo", variant=ButtonVariant.DANGER, size=ButtonSize.SMALL)
        remove_btn.clicked.connect(self._remove_logo)
        logo_buttons.addWidget(upload_btn)
        logo_buttons.addWidget(remove_btn)
        logo_buttons.addStretch()
        logo_layout.addLayout(logo_buttons)
        logo_group.setLayout(logo_layout)
        container_layout.addWidget(logo_group)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Action buttons
        btn_layout = QHBoxLayout()
        save_btn = EnterpriseButton(text="Save Profile", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self._save_profile)
        load_btn = EnterpriseButton(text="Load from Server", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        load_btn.clicked.connect(self._load_profile)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(load_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _load_profile(self):
        """Load company profile from API."""
        if not self._api_client:
            AlertDialog.warning("Company Profile", "API client not available.", self)
            return

        def on_success(resp):
            if resp and resp.get("success"):
                data = resp["data"]
                self._company_id = data.get("id")
                self.name_edit.setText(data.get("name", ""))
                self.code_edit.setText(data.get("code", ""))
                self.tax_edit.setText(data.get("tax_number", ""))
                self.email_edit.setText(data.get("email", ""))
                self.phone_edit.setText(data.get("phone", ""))
                self.address_edit.setPlainText(data.get("address", ""))

                dc = data.get("default_currency", "AFN")
                sc = data.get("secondary_currency", "USD")
                idx = self.default_currency.findText(dc)
                if idx >= 0:
                    self.default_currency.setCurrentIndex(idx)
                idx2 = self.secondary_currency.findText(sc)
                if idx2 >= 0:
                    self.secondary_currency.setCurrentIndex(idx2)

                logo = data.get("logo")
                if logo:
                    self._logo_path = logo
                    self.logo_label.setText(f"Logo: {logo}")
                else:
                    self.logo_label.setText("No logo uploaded")

                AlertDialog.info("Company Profile", "Profile loaded successfully.", self)
            else:
                AlertDialog.warning("Company Profile", f"Failed to load profile: {resp}", self)

        self.run_api_request(
            key="company_profile_load",
            method="GET",
            endpoint="/api/core/companies/default/",
            on_success=on_success,
            on_error=lambda message: AlertDialog.error("Company Profile", f"Error loading profile: {message}", self),
        )

    def _save_profile(self):
        """Save company profile to API."""
        if not self._api_client:
            AlertDialog.warning("Company Profile", "API client not available.", self)
            return

        payload = {
            "name": self.name_edit.text().strip(),
            "code": self.code_edit.text().strip(),
            "tax_number": self.tax_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "address": self.address_edit.toPlainText().strip(),
            "default_currency": self.default_currency.currentText(),
            "secondary_currency": self.secondary_currency.currentText(),
            "is_active": True,
        }

        if not payload["name"]:
            AlertDialog.warning("Company Profile", "Company name is required.", self)
            return
        if not payload["code"]:
            AlertDialog.warning("Company Profile", "Company code is required.", self)
            return

        def on_success(resp):
            if resp and resp.get("success"):
                data = resp["data"]
                self._company_id = data.get("id")
                AlertDialog.info("Company Profile", "Profile saved successfully.", self)
            else:
                AlertDialog.warning("Company Profile", f"Failed to save: {resp}", self)

        self.run_api_request(
            key="company_profile_save",
            method="PUT" if self._company_id else "POST",
            endpoint=f"/api/core/companies/{self._company_id}/" if self._company_id else "/api/core/companies/",
            data=payload,
            on_success=on_success,
            on_error=lambda message: AlertDialog.error("Company Profile", f"Error saving profile: {message}", self),
        )

    def _upload_logo(self):
        """Upload company logo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Upload Logo", "", "Images (*.png *.jpg *.jpeg *.gif)"
        )
        if file_path:
            self._logo_path = file_path
            pixmap = QPixmap(file_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setText("")

    def _remove_logo(self):
        """Remove company logo."""
        self._logo_path = None
        self.logo_label.setPixmap(QPixmap())
        self.logo_label.setText("No logo uploaded")

    def on_show(self):
        """Load profile when screen is shown."""
        self._load_profile()
