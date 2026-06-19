"""User Management Screen for ERP."""
import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QAbstractItemView, QComboBox,
                                  QLineEdit,
                                  QCheckBox, QTabWidget,
                                  QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from ui.screens.base_screen import BaseScreen
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.page_header import PageHeader
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog, ConfirmDialog
from ui.components.forms import FormSection
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_CARD_TITLE,
                           TEXT_BODY, BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS)




logger = logging.getLogger(__name__)


class UserManagementScreen(BaseScreen):
    """User management screen with CRUD operations."""
    
    def __init__(self, parent=None, screen_id="user_management", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._users = []
        self._roles = []
        self._setup_ui()
        self.load_users()
        self.load_roles()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Enterprise header
        from theme.style_builder import UIStyleBuilder
        header = PageHeader(
            "User & Role Management",
            "Manage users, role membership and permission visibility with governed access controls.",
            "IDENTITY CONTROL",
        )
        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_users)
        header.add_action(self.btn_refresh)
        layout.addWidget(header)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(UIStyleBuilder.get_tab_style())
        
        # Users Tab
        self.users_tab = QWidget()
        self._setup_users_tab()
        self.tabs.addTab(self.users_tab, "System Users")
        
        # Roles & Permissions Tab
        self.roles_tab = QWidget()
        self._setup_roles_tab()
        self.tabs.addTab(self.roles_tab, "Roles & Permissions")
        
        layout.addWidget(self.tabs)
    
    def _setup_users_tab(self):
        layout = QVBoxLayout(self.users_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        action_layout = QHBoxLayout()
        self.add_user_btn = EnterpriseButton(text="+ Create User", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.add_user_btn.clicked.connect(self.add_user)
        action_layout.addWidget(self.add_user_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("username", "Username", width=120),
            TableColumn("email", "Email", width=180),
            TableColumn("first_name", "First Name", width=100),
            TableColumn("last_name", "Last Name", width=100),
            TableColumn("role", "Role", width=100),
            TableColumn("active", "Active", width=60, align="center"),
        ]
        self.user_table = self._create_modern_table(columns)
        layout.addWidget(self.user_table)
        
        self.load_users()

    def _setup_roles_tab(self):
        layout = QVBoxLayout(self.roles_tab)
        layout.setContentsMargins(SPACING_LG,  SPACING_LG,  SPACING_LG,  SPACING_LG)
        layout.setSpacing(SPACING_MD + SPACING_XS)
        
        from theme.style_builder import UIStyleBuilder
        info_label = QLabel("System Roles are predefined based on organizational functions. You can view permissions for each role below.")
        info_label.setStyleSheet(UIStyleBuilder.get_label_style("muted") + " font-style: italic;")
        layout.addWidget(info_label)
        
        role_selector_layout = QHBoxLayout()
        role_selector_layout.addWidget(QLabel("Select Role to View:"))
        self.role_selector = QComboBox()
        # Pre-populate with roles from UserRole enum
        from ui.role_manager import UserRole
        for role in UserRole:
            self.role_selector.addItem(role.name.replace('_', ' ').title(), role)
        
        self.role_selector.setMinimumWidth(200)
        self.role_selector.currentIndexChanged.connect(self._on_role_selected)
        role_selector_layout.addWidget(self.role_selector)
        role_selector_layout.addStretch()
        layout.addLayout(role_selector_layout)
        
        perm_columns = [
            TableColumn("module", "Module", width=200),
            TableColumn("permission", "Permission", width=150),
            TableColumn("access", "Access Level", width=100),
        ]
        self.permissions_table = self._create_modern_table(perm_columns)
        layout.addWidget(self.permissions_table)
        
        # Initial role selection
        self._on_role_selected(0)

    def _create_modern_table(self, columns=None):
        """Create a modern dark-themed table."""
        if columns:
            table = EnterpriseTable(columns)
        else:
            table = EnterpriseTable([TableColumn(f"col{i}", "") for i in range(4)])
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setMinimumHeight(200)
        return table

    def _on_role_selected(self, index):
        role = self.role_selector.currentData()
        if not role: return
        
        from ui.role_manager import ROLE_PERMISSIONS
        permissions = ROLE_PERMISSIONS.get(role, [])
        
        rows = []
        for perm in permissions:
            parts = perm.split('.')
            module = parts[0].title() if len(parts) > 0 else ""
            action = parts[1].replace('_', ' ').title() if len(parts) > 1 else ""
            rows.append({
                "module": module,
                "permission": action,
                "access": "Full Access" if 'admin' in perm else "Standard",
            })
        self.permissions_table.set_data(rows)
    
    def load_roles(self):
        """Load roles from API."""
        if not self._api_client:
            return
        try:
            result = self._api_client.get_roles()
            if result.get('success'):
                self._roles = result.get('data', [])
        except Exception as e:
            logger.error(f"Error loading roles: {e}")
    
    def load_users(self):
        """Load users from API."""
        if not self._api_client:
            return
        
        try:
            result = self._api_client.get_users()
            if result.get('success'):
                self._users = result.get('data', {}).get('results', [])
                self.populate_table()
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    def populate_table(self):
        """Populate the users table."""
        rows = []
        for user in self._users:
            roles = user.get('roles', [])
            role_str = ", ".join(roles) if roles else "General"
            rows.append({
                "id": str(user.get('id', '')),
                "username": user.get('username', ''),
                "email": user.get('email', ''),
                "first_name": user.get('first_name', ''),
                "last_name": user.get('last_name', ''),
                "role": role_str,
                "active": "Yes" if user.get('is_active', True) else "No",
            })
        self.user_table.set_data(rows)
    
    def add_user(self):
        """Show add user dialog."""
        dialog = UserDialog(self._api_client, parent=self)
        if dialog.exec():
            self.load_users()

    def edit_user(self):
        """Show edit user dialog."""
        selected = self.user_table.selectedItems()
        if not selected: return
        row = selected[0].row()
        user_data = self._users[row] if row < len(self._users) else None
        
        if user_data:
            dialog = UserDialog(self._api_client, parent=self, user_data=user_data)
            if dialog.exec():
                self.load_users()

    def delete_user(self):
        """Delete selected user."""
        selected = self.user_table.selectedItems()
        if not selected: return
        row = selected[0].row()
        user_data = self._users[row]
        
        reply = ConfirmDialog.confirm(
            "Delete User",
            f"Are you sure you want to delete user '{user_data.get('username')}'?",
            self
        )
        
        if reply:
            try:
                self._api_client.delete(f"/api/auth/users/{user_data['id']}/")
                self.load_users()
            except Exception as e:
                AlertDialog.error("Error", f"Failed to delete user: {e}", self)


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

    def _build_content(self):
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{ 
                background-color: {COLOR_BG_MAIN}; 
            }}
            QGroupBox {{ 
                font-weight: bold; 
                font-size: {TEXT_CARD_TITLE}pt;
                border: 1px solid {COLOR_BG_ELEVATED}; 
                border-radius: {BORDER_RADIUS_LG}px; 
                margin-top: {SPACING_MD}; 
                padding-top: {SPACING_MD}; 
                padding-bottom: {SPACING_MD};
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}pt;
                padding: {SPACING_SM} 4px;
            }}
            QLineEdit {{
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM};
                font-size: {TEXT_BODY}pt;
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
                background-color: {COLOR_BG_MAIN};
            }}
            QLineEdit::placeholder {{
                color: {COLOR_TEXT_MUTED};
            }}
            QComboBox {{
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM};
                font-size: {TEXT_BODY}pt;
            }}
            QComboBox:focus {{
                border-color: {COLOR_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLOR_TEXT_MUTED};
                margin-right: {SPACING_SM};
            }}
            QCheckBox {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}pt;
                spacing: {SPACING_SM};
                padding: {SPACING_SM} 0;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: {BORDER_RADIUS_SM}px;
                border: 2px solid {COLOR_BORDER};
                background-color: {COLOR_BG_MAIN};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLOR_SUCCESS};
                border-color: {COLOR_SUCCESS};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_SM + SPACING_XS)
        
        # Title
        title = QLabel("Create New User" if not self.user_data else "Edit User")
        title_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; margin-bottom: {SPACING_MD};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        section = FormSection("User Details", primary=True)
        
        self.username = QLineEdit()
        self.username.setMinimumHeight(40)
        self.username.setPlaceholderText("Enter username")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(40)
        self.password.setPlaceholderText("Enter password")
        self.email = QLineEdit()
        self.email.setMinimumHeight(40)
        self.email.setPlaceholderText("Enter email address")
        self.first_name = QLineEdit()
        self.first_name.setMinimumHeight(40)
        self.first_name.setPlaceholderText("First name")
        self.last_name = QLineEdit()
        self.last_name.setMinimumHeight(40)
        self.last_name.setPlaceholderText("Last name")
        
        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(40)
        self.role_combo.setStyleSheet(f"QComboBox {{ padding: {SPACING_MD}px; }}")
        from ui.role_manager import UserRole
        for role in UserRole:
            self.role_combo.addItem(role.name.replace('_', ' ').title(), role.value)
            
        self.is_active = QCheckBox("User is Active")
        self.is_active.setChecked(True)
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
        layout.addSpacing(15)
        
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
        if not self.username.text().strip():
            AlertDialog.warning("Validation Error", "Username is required.", self)
            return
        
        role_value = self.role_combo.currentData()
        
        data = {
            "username": self.username.text().strip(),
            "email": self.email.text().strip(),
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "is_active": self.is_active.isChecked(),
            "role": role_value,
        }
        
        if not self.user_data:
            pwd = self.password.text().strip() if self.password.text() else "changeme123"
            data["password"] = pwd
        
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