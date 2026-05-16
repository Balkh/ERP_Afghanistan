"""User Management Screen for ERP."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel, QHeaderView, QAbstractItemView,
                                  QComboBox, QLineEdit, QGroupBox, QFormLayout,
                                   QMessageBox, QDialog, QSpinBox,
                                  QCheckBox, QDateEdit, QTabWidget, QWidget)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.components.dialogs import confirm_dialog
from datetime import date
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER,
                           BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                           COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)

# Design tokens
from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER
)


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

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("User & Role Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_users)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}; background: {COLOR_BG_MAIN}; }}
            QTabBar::tab {{ background: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; border: none; padding: {SPACING_MD}px 24px; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
            QTabBar::tab:selected {{ background: {COLOR_PRIMARY}; color: white; font-weight: bold; }}
            QTabBar::tab:hover {{ background: {COLOR_BORDER}; }}
        """)
        # Replace remaining hex colors
        ss = self.tabs.styleSheet()
        ss = ss.replace("#374151", COLOR_BG_ELEVATED)
        ss = ss.replace("#1f2937", COLOR_BG_MAIN)
        ss = ss.replace("#4b5563", COLOR_BORDER)
        ss = ss.replace("#e5e7eb", COLOR_TEXT_PRIMARY)
        ss = ss.replace("#3b82f6", COLOR_PRIMARY)
        ss = ss.replace("#10b981", COLOR_SUCCESS)
        ss = ss.replace("#059669", COLOR_SUCCESS)
        ss = ss.replace("#ef4444", COLOR_DANGER)
        ss = ss.replace("#f59e0b", COLOR_WARNING)
        ss = ss.replace("#6b7280", COLOR_TEXT_MUTED)
        ss = ss.replace("#9ca3af", COLOR_TEXT_MUTED)
        self.tabs.setStyleSheet(ss)
        
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
        
        info_label = QLabel("System Roles are predefined based on organizational functions. You can view permissions for each role below.")
        info_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-style: italic;")
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
        
        self.permissions_table.setRowCount(len(permissions))
        for i, perm in enumerate(permissions):
            # Split "app.permission" string
            parts = perm.split('.')
            module = parts[0].title() if len(parts) > 0 else ""
            action = parts[1].replace('_', ' ').title() if len(parts) > 1 else ""
            
            self.permissions_table.setItem(i, 0, QTableWidgetItem(module))
            self.permissions_table.setItem(i, 1, QTableWidgetItem(action))
            self.permissions_table.setItem(i, 2, QTableWidgetItem("Full Access" if 'admin' in perm else "Standard"))
    
    def load_roles(self):
        """Load roles from API."""
        if not self._api_client:
            return
        try:
            result = self._api_client.get_roles()
            if result.get('success'):
                self._roles = result.get('data', [])
        except Exception as e:
            print(f"Error loading roles: {e}")
    
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
            print(f"Error loading users: {e}")
    
    def populate_table(self):
        """Populate the users table."""
        self.table.setRowCount(0)
        
        search = self.search_input.text().lower()
        
        for user in self._users:
            if search and search not in user.get('username', '').lower() and search not in user.get('email', '').lower():
                continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(user.get('id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(user.get('username', '')))
            self.table.setItem(row, 2, QTableWidgetItem(user.get('email', '')))
            self.table.setItem(row, 3, QTableWidgetItem(user.get('first_name', '')))
            self.table.setItem(row, 4, QTableWidgetItem(user.get('last_name', '')))
            
            roles = user.get('roles', [])
            role_str = ", ".join(roles) if roles else "General"
            self.table.setItem(row, 5, QTableWidgetItem(role_str))
            
            active = "Yes" if user.get('is_active', True) else "No"
            self.table.setItem(row, 6, QTableWidgetItem(active))
    
    def filter_users(self):
        """Filter users based on search."""
        self.populate_table()
    
    def on_selection_changed(self):
        """Handle selection change."""
        selected = len(self.table.selectionModel().selectedRows()) > 0
        self.edit_btn.setEnabled(selected)
        self.delete_btn.setEnabled(selected)
    
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
        
        reply = QMessageBox.question(
            self, "Delete User",
            f"Are you sure you want to delete user '{user_data.get('username')}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self._api_client.delete(f"/api/auth/users/{user_data['id']}/")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {e}")


class UserDialog(QDialog):
    """Dialog for creating/editing users."""
    
    def __init__(self, api_client=None, parent=None, user_data=None):
        super().__init__(parent)
        self.api_client = api_client
        self.user_data = user_data
        self.setWindowTitle("User Account")
        self.setMinimumWidth(450)
        self._setup_ui()
        if user_data:
            self._load_user_data()

    def _setup_ui(self):
        self.setMinimumWidth(500)
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLOR_BG_MAIN}; 
            }}
            QGroupBox {{ 
                font-weight: bold; 
                font-size: {TEXT_CARD_TITLE}px;
                border: 1px solid {COLOR_BG_ELEVATED}; 
                border-radius: {BORDER_RADIUS_LG}; 
                margin-top: {SPACING_MD}; 
                padding-top: {SPACING_MD}; 
                padding-bottom: {SPACING_MD};
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}px;
                padding: {SPACING_SM} 4px;
            }}
            QLineEdit {{
                background-color: {COLOR_BG_MAIN};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM};
                font-size: {TEXT_BODY}px;
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
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM};
                font-size: {TEXT_BODY}px;
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
                font-size: {TEXT_BODY}px;
                spacing: {SPACING_SM};
                padding: {SPACING_SM} 0;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: {BORDER_RADIUS_SM};
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
        layout = QVBoxLayout(self)
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
        
        form_group = QGroupBox("")
        form_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {COLOR_BG_ELEVATED};
                border-radius: {BORDER_RADIUS_LG};
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                padding: {SPACING_SM};
            }}
        """)
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(12)
        
        self.username = QLineEdit()
        self.username.setMinimumHeight(40)
        self.username.setPlaceholderText("Enter username")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
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
        
        form_layout.addRow("Username:", self.username)
        if not self.user_data:
            form_layout.addRow("Password:", self.password)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("First Name:", self.first_name)
        form_layout.addRow("Last Name:", self.last_name)
        form_layout.addRow("Role:", self.role_combo)
        form_layout.addRow("", self.is_active)
        
        layout.addWidget(form_group)
        
        # Spacer
        layout.addSpacing(15)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(SPACING_MD + SPACING_XS)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setMinimumWidth(130)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BORDER};
                color: white;
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                font-size: {TEXT_BODY}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_TEXT_MUTED};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save User")
        save_btn.setMinimumHeight(38)
        save_btn.setMinimumWidth(130)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                font-weight: bold;
                padding: {SPACING_SM} 20px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SUCCESS};
            }}
        """)
        save_btn.clicked.connect(self.accept)
        
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)
    
    def save(self):
        """Save user data."""
        if not self.username.text():
            QMessageBox.warning(self, "Error", "Username is required")
            return
        
        # Get role id from selected role name
        role_name = self.role.currentText()
        role_id = None
        for r in self._roles:
            if r.get('name') == role_name:
                role_id = r.get('id')
                break
        
        data = {
            "username": self.username.text(),
            "email": self.email.text(),
            "first_name": self.first_name.text(),
            "last_name": self.last_name.text(),
            "is_active": self.is_active.isChecked(),
            "role_ids": [role_id] if role_id else []
        }
        
        if not self._user:
            data["password"] = "changeme123"
        
        try:
            if self._user:
                result = self._api_client.update_user(self._user['id'], data)
            else:
                result = self._api_client.create_user(data)
            
            if result.get('success'):
                self.accept()
            else:
                QMessageBox.warning(self, "Error", result.get('error', {}).get('message', 'Failed to save'))
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))