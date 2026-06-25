"""User Dialog for ERP — extracted from user_management_screen.py."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit, QComboBox,
                                   QCheckBox, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.components.forms import FormSection
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                           TEXT_CARD_TITLE, TEXT_BODY,
                           BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER,
                           COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, FONT_NAME_PRIMARY)
from ui.components.form_helpers import make_field as _make_field


class UserDialog(EnterpriseDialog):
    """Dialog for creating/editing users."""

    def __init__(self, api_client=None, parent=None, user_data=None):
        self.api_client = api_client
        self.user_data = user_data
        super().__init__("User Account", DialogType.CUSTOM, parent)
        self.setMinimumWidth(450)
        content = self._build_content()
        self.set_content(content)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(self.save)
        if user_data:
            self._load_user_data()

    def _create_button_area(self):
        return None

    def _load_user_data(self):
        """Load existing user data into form fields."""
        if self.user_data:
            self.username.setText(self.user_data.get("username", ""))
            self.email.setText(self.user_data.get("email", ""))
            self.first_name.setText(self.user_data.get("first_name", ""))
            self.last_name.setText(self.user_data.get("last_name", ""))
            self.is_active.setChecked(self.user_data.get("is_active", True))
            role_name = self.user_data.get("role", "")
            idx = self.role_combo.findText(role_name)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)

    def _collect_data(self):
        """Collect form data into a dict."""
        data = {
            "username": self.username.text().strip(),
            "email": self.email.text().strip(),
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "is_active": self.is_active.isChecked(),
            "role": self.role_combo.currentData(),
        }
        if not self.user_data:
            pwd = self.password.text().strip() if self.password.text() else "changeme123"
            data["password"] = pwd
        return data

    def _validate(self):
        """Validate form fields. Returns True if valid."""
        if not self.username.text().strip():
            AlertDialog.warning("Validation Error", "Username is required.", self)
            return False
        return True

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM,
                                  SPACING_XL + SPACING_SM, SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        # Title
        title = QLabel("Create New User" if not self.user_data else "Edit User")
        title_font = QFont(FONT_NAME_PRIMARY, TEXT_CARD_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(UIStyleBuilder.get_label_style("title"))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        section = FormSection("User Details", primary=True)

        self.username = _make_field("Enter username")
        self.password = _make_field("Enter password", QLineEdit.EchoMode.Password)
        self.email = _make_field("Enter email address")
        self.first_name = _make_field("First name")
        self.last_name = _make_field("Last name")

        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(40)
        self.role_combo.setStyleSheet(UIStyleBuilder.get_input_style())
        from ui.role_manager import UserRole
        for role in UserRole:
            self.role_combo.addItem(role.name.replace('_', ' ').title(), role.value)

        self.is_active = QCheckBox("User is Active")
        self.is_active.setChecked(True)
        self.is_active.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self.is_active.setStyleSheet(f"margin-top: {SPACING_MD}px;")

        section.add_field(self.username, "Username:")
        if not self.user_data:
            section.add_field(self.password, "Password:")
        section.add_field(self.email, "Email:")
        section.add_field(self.first_name, "First Name:")
        section.add_field(self.last_name, "Last Name:")
        section.add_field(self.role_combo, "Role:")
        section.add_field(self.is_active)

        layout.addWidget(section)

        # Spacer
        layout.addSpacing(SPACING_LG)

        buttons = QHBoxLayout()
        buttons.setSpacing(SPACING_MD + SPACING_XS)

        cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.LARGE)
        cancel_btn.clicked.connect(self.reject)

        save_btn = EnterpriseButton("Save User", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        save_btn.setMinimumWidth(130)
        save_btn.clicked.connect(self.save)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        return widget

    def save(self):
        """Save user data."""
        if not self._validate():
            return

        data = self._collect_data()

        try:
            if self.user_data:
                result = self.api_client.update_user(self.user_data['id'], data)
            else:
                result = self.api_client.create_user(data)

            if result.get('success'):
                self.accept()
            else:
                error_msg = result.get('error', {})
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Failed to save')
                AlertDialog.warning("Error", str(error_msg), self)
        except Exception as e:
            AlertDialog.warning("Error", str(e), self)
