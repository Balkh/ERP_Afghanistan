"""Role Management Screen for ERP — CRUD for roles + permission assignment."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QAbstractItemView,
                               QLineEdit, QGroupBox, QFormLayout, QMessageBox,
                               QDialog, QCheckBox, QScrollArea, QWidget,
                               QSplitter, QTableWidgetItem, QTextEdit)
from PySide6.QtCore import Qt
from ui.screens.base_screen import BaseScreen
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, MARGIN_PAGE, TEXT_PAGE_TITLE,
                          TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, BORDER_RADIUS_SM,
                          BORDER_RADIUS_MD, COLOR_BG_MAIN, COLOR_BG_SURFACE,
                          COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                          COLOR_TEXT_SECONDARY, COLOR_SUCCESS)


class RoleManagementScreen(BaseScreen):
    """Role management screen with CRUD and permission assignment."""

    def __init__(self, parent=None, screen_id="role_management", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._roles = []
        self._permissions = []
        self._selected_role = None
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header_layout = QHBoxLayout()
        header = QLabel("Role Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.btn_create = EnterpriseButton(text="+ Create Role", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.btn_create.clicked.connect(self.create_role)
        header_layout.addWidget(self.btn_create)

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        splitter = QSplitter(Qt.Horizontal)
        left_widget = self._build_role_list()
        right_widget = self._build_permission_panel()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def _build_role_list(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        search_label = QLabel("Roles")
        search_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; font-weight: 600;")
        layout.addWidget(search_label)

        columns = [
            TableColumn("name", "Role Name", width=140),
            TableColumn("description", "Description", width=160),
            TableColumn("user_count", "Users", width=60, align="center"),
            TableColumn("perm_count", "Permissions", width=80, align="center"),
            TableColumn("active", "Active", width=60, align="center"),
        ]
        self.role_table = EnterpriseTable(columns)
        self.role_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.role_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.role_table.selectionModel().selectionChanged.connect(self._on_role_selected)
        layout.addWidget(self.role_table)

        btn_layout = QHBoxLayout()
        self.btn_edit = EnterpriseButton(text="Edit", variant=ButtonVariant.PRIMARY, size=ButtonSize.SMALL)
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self.edit_role)
        btn_layout.addWidget(self.btn_edit)

        self.btn_delete = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.SMALL)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_role)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return container

    def _build_permission_panel(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self.perm_title = QLabel("Select a role to manage permissions")
        self.perm_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; font-weight: 600;")
        layout.addWidget(self.perm_title)

        self.perm_desc = QTextEdit()
        self.perm_desc.setReadOnly(True)
        self.perm_desc.setMaximumHeight(60)
        self.perm_desc.setStyleSheet("""
            QTextEdit {{ background: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_SECONDARY};
                        border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};
                        padding: {SPACING_SM}; font-size: {TEXT_BODY_SMALL}pt; }}
        """)
        layout.addWidget(self.perm_desc)

        self.perm_scroll = QScrollArea()
        self.perm_scroll.setWidgetResizable(True)
        self.perm_scroll.setMinimumHeight(300)
        self.perm_content = QWidget()
        self.perm_layout = QVBoxLayout(self.perm_content)
        self.perm_layout.setSpacing(SPACING_MD)
        self.perm_scroll.setWidget(self.perm_content)
        layout.addWidget(self.perm_scroll)

        self._perm_checkboxes = {}
        self.btn_save_perms = EnterpriseButton(text="Save Permissions", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_save_perms.setEnabled(False)
        self.btn_save_perms.clicked.connect(self.save_permissions)
        layout.addWidget(self.btn_save_perms)

        return container

    def load_data(self):
        if not self._api_client:
            return
        try:
            result = self._api_client.get_roles()
            if result.get("success"):
                self._roles = result.get("data", [])
                self._populate_role_table()
        except Exception as e:
            print(f"Error loading roles: {e}")
        try:
            result = self._api_client.get_permissions()
            if result.get("success"):
                self._permissions = result.get("data", [])
        except Exception as e:
            print(f"Error loading permissions: {e}")

    def _populate_role_table(self):
        self.role_table.setRowCount(0)
        for role in self._roles:
            row = self.role_table.rowCount()
            self.role_table.insertRow(row)
            self.role_table.setItem(row, 0, QTableWidgetItem(role.get("name", "")))
            self.role_table.setItem(row, 1, QTableWidgetItem(role.get("description", "")))
            self.role_table.setItem(row, 2, QTableWidgetItem(str(role.get("user_count", 0))))
            self.role_table.setItem(row, 3, QTableWidgetItem(str(role.get("permission_count", 0))))
            active = "Yes" if role.get("is_active", True) else "No"
            self.role_table.setItem(row, 4, QTableWidgetItem(active))

    def _on_role_selected(self, selected, deselected):
        indexes = self.role_table.selectionModel().selectedRows()
        if not indexes:
            self.btn_edit.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_save_perms.setEnabled(False)
            self._selected_role = None
            self.perm_title.setText("Select a role to manage permissions")
            return
        row = indexes[0].row()
        self._selected_role = self._roles[row]
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_save_perms.setEnabled(True)
        self.perm_title.setText(f"Permissions: {self._selected_role['name']}")
        self.perm_desc.setText(self._selected_role.get("description", ""))
        self._load_role_permissions()

    def _load_role_permissions(self):
        for i in reversed(range(self.perm_layout.count())):
            w = self.perm_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._perm_checkboxes = {}

        if not self._selected_role:
            return

        role_id = self._selected_role.get("id")
        try:
            result = self._api_client.get_role(role_id)
            if result.get("success"):
                role_data = result.get("data", {})
                assigned_perms = set(role_data.get("permissions", []))
            else:
                assigned_perms = set()
        except Exception:
            assigned_perms = set()

        modules = {}
        for perm in self._permissions:
            module = perm.get("module", "Other")
            if module not in modules:
                modules[module] = []
            modules[module].append(perm)

        for module_name in sorted(modules.keys()):
            group = QGroupBox(f"{module_name} ({len(modules[module_name])})")
            group.setStyleSheet("""
                QGroupBox {{ font-weight: bold; font-size: {TEXT_BODY}pt;
                    border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};
                    margin-top: {SPACING_SM}; padding-top: {SPACING_MD}; padding-left: {SPACING_MD};
                    color: {COLOR_TEXT_PRIMARY}; }}
                QGroupBox::title {{ subcontrol-origin: margin; left: {SPACING_SM}px;
                    padding: 0 {SPACING_XS}px; }}
            """)
            grid = QVBoxLayout()
            grid.setSpacing(SPACING_XS)
            for perm in sorted(modules[module_name], key=lambda p: p.get("name", "")):
                cb = QCheckBox(perm.get("name", ""))
                cb.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY_SMALL}pt;")
                codename = perm.get("codename", "")
                cb.setChecked(codename in assigned_perms)
                cb.setProperty("codename", codename)
                self._perm_checkboxes[codename] = cb
                grid.addWidget(cb)
            group.setLayout(grid)
            self.perm_layout.addWidget(group)
        self.perm_layout.addStretch()

    def create_role(self):
        dialog = RoleDialog(self._api_client, parent=self)
        if dialog.exec():
            self.load_data()

    def edit_role(self):
        if not self._selected_role:
            return
        dialog = RoleDialog(self._api_client, role_data=self._selected_role, parent=self)
        if dialog.exec():
            self.load_data()
            self._on_role_selected(
                self.role_table.selectionModel().selection(),
                None
            )

    def delete_role(self):
        if not self._selected_role:
            return
        name = self._selected_role.get("name", "")
        user_count = self._selected_role.get("user_count", 0)
        if user_count > 0:
            QMessageBox.warning(self, "Cannot Delete",
                                f"Role '{name}' has {user_count} user(s) assigned. Remove them first.")
            return
        reply = QMessageBox.question(
            self, "Delete Role",
            f"Are you sure you want to delete role '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                result = self._api_client.delete_role(self._selected_role["id"])
                if result.get("success"):
                    QMessageBox.information(self, "Deleted", f"Role '{name}' deleted.")
                    self.load_data()
                    self._selected_role = None
                    self.perm_title.setText("Select a role to manage permissions")
                    self.btn_save_perms.setEnabled(False)
                else:
                    QMessageBox.warning(self, "Error", result.get("error", {}).get("message", "Failed to delete"))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete role: {e}")

    def save_permissions(self):
        if not self._selected_role:
            return
        selected = [cb.property("codename") for cb in self._perm_checkboxes.values() if cb.isChecked()]
        data = {"permission_ids": []}
        perm_id_map = {p.get("codename"): p.get("id") for p in self._permissions}
        for codename in selected:
            if codename in perm_id_map:
                data["permission_ids"].append(perm_id_map[codename])
        try:
            result = self._api_client.update_role(self._selected_role["id"], data)
            if result.get("success"):
                QMessageBox.information(self, "Saved", "Permissions updated successfully.")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", result.get("error", {}).get("message", "Failed to save"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save permissions: {e}")

    def on_show(self):
        self.load_data()


class RoleDialog(QDialog):
    """Dialog for creating/editing roles."""

    def __init__(self, api_client=None, role_data=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.role_data = role_data
        self.setWindowTitle("Create Role" if not role_data else "Edit Role")
        self.setMinimumWidth(450)
        self._setup_ui()
        if role_data:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)

        self.setStyleSheet("""
            QDialog {{ background-color: {COLOR_BG_MAIN}; }}
            QLabel {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt; }}
            QLineEdit, QTextEdit {{
                background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM}; font-size: {TEXT_BODY}pt;
            }}
            QCheckBox {{ color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt; spacing: {SPACING_SM}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: {BORDER_RADIUS_SM};
                border: 2px solid {COLOR_BORDER}; background-color: {COLOR_BG_SURFACE}; }}
            QCheckBox::indicator:checked {{ background-color: {COLOR_SUCCESS}; border-color: {COLOR_SUCCESS}; }}
        """)

        form = QGroupBox("")
        form.setStyleSheet("""
            QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_MD}; }}
        """)
        form_layout = QFormLayout(form)
        form_layout.setSpacing(SPACING_MD)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Warehouse Manager")
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setPlaceholderText("Description of this role...")
        self.active_cb = QCheckBox("Role is active")
        self.active_cb.setChecked(True)
        self.require_2fa = QCheckBox("Require 2FA for users with this role")

        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Description:", self.desc_input)
        form_layout.addRow("", self.active_cb)
        form_layout.addRow("", self.require_2fa)
        layout.addWidget(form)

        btn_layout = QHBoxLayout()
        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = EnterpriseButton(text="Save Role", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.role_data.get("name", ""))
        self.desc_input.setText(self.role_data.get("description", ""))
        self.active_cb.setChecked(self.role_data.get("is_active", True))
        self.require_2fa.setChecked(self.role_data.get("require_2fa", False))

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Role name is required.")
            return
        data = {
            "name": name,
            "description": self.desc_input.toPlainText().strip(),
            "is_active": self.active_cb.isChecked(),
            "require_2fa": self.require_2fa.isChecked(),
        }
        try:
            if self.role_data:
                result = self.api_client.update_role(self.role_data["id"], data)
            else:
                result = self.api_client.create_role(data)
            if result.get("success"):
                self.accept()
            else:
                QMessageBox.warning(self, "Error", result.get("error", {}).get("message", "Failed to save"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save role: {e}")
