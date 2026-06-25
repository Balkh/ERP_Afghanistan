"""Departments and Positions management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                                QComboBox, QFormLayout, QWidget, QTabWidget)
from PySide6.QtCore import Qt
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_BODY, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
                           COLOR_DANGER, COLOR_BG_SURFACE, COLOR_BORDER, BORDER_RADIUS_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog, ConfirmDialog
from theme.style_builder import UIStyleBuilder


class DepartmentsScreen(BaseScreen):
    """Screen for managing departments and positions."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="departments")
        self.api_client = api_client or APIClient()
        self.departments = []
        self.positions = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QHBoxLayout()
        title = QLabel("Departments & Positions")
        title.setStyleSheet(UIStyleBuilder.get_page_header_style())
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.refresh_btn.clicked.connect(self.load_data)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(UIStyleBuilder.get_tab_style())

        self.dept_tab = QWidget()
        self._setup_dept_tab()
        self.tabs.addTab(self.dept_tab, "Departments")

        self.pos_tab = QWidget()
        self._setup_pos_tab()
        self.tabs.addTab(self.pos_tab, "Positions")

        layout.addWidget(self.tabs)

    def _setup_dept_tab(self):
        layout = QVBoxLayout(self.dept_tab)
        layout.setSpacing(SPACING_MD)

        btn_layout = QHBoxLayout()
        add_btn = EnterpriseButton("+ Add Department", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        add_btn.clicked.connect(self._add_department)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.dept_table = EnterpriseTable([
            TableColumn("code", "Code", width=80),
            TableColumn("name", "Name", width=200),
            TableColumn("parent", "Parent", width=150),
            TableColumn("manager", "Manager", width=150),
            TableColumn("status", "Status", width=80, align="center"),
        ])
        layout.addWidget(self.dept_table)

    def _setup_pos_tab(self):
        layout = QVBoxLayout(self.pos_tab)
        layout.setSpacing(SPACING_MD)

        btn_layout = QHBoxLayout()
        add_btn = EnterpriseButton("+ Add Position", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        add_btn.clicked.connect(self._add_position)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.pos_table = EnterpriseTable([
            TableColumn("code", "Code", width=80),
            TableColumn("title", "Title", width=200),
            TableColumn("department", "Department", width=150),
            TableColumn("status", "Status", width=80, align="center"),
        ])
        layout.addWidget(self.pos_table)

    def load_data(self):
        self._load_departments()
        self._load_positions()

    def _load_departments(self):
        def update_table():
            data = [{"code": d.get("code", ""), "name": d.get("name", ""),
                     "parent": d.get("parent_name", ""), "manager": d.get("manager_name", ""),
                     "status": "Active" if d.get("is_active") else "Inactive"} for d in self.departments]
            self.dept_table.set_data(data)

        def on_success(response):
            if response and isinstance(response, dict) and response.get("success"):
                raw = response.get("data", [])
                self.departments = raw.get("results", []) if isinstance(raw, dict) else raw
            else:
                self.departments = []
            update_table()

        def on_error(_message):
            self.departments = []
            update_table()

        self.run_api_request(
            key="departments_load",
            method="GET",
            endpoint="/api/hr/departments/",
            on_success=on_success,
            on_error=on_error,
        )

    def _load_positions(self):
        def update_table():
            data = [{"code": p.get("code", ""), "title": p.get("title", ""),
                     "department": p.get("department_name", ""),
                     "status": "Active" if p.get("is_active") else "Inactive"} for p in self.positions]
            self.pos_table.set_data(data)

        def on_success(response):
            if response and isinstance(response, dict) and response.get("success"):
                raw = response.get("data", [])
                self.positions = raw.get("results", []) if isinstance(raw, dict) else raw
            else:
                self.positions = []
            update_table()

        def on_error(_message):
            self.positions = []
            update_table()

        self.run_api_request(
            key="positions_load",
            method="GET",
            endpoint="/api/hr/positions/",
            on_success=on_success,
            on_error=on_error,
        )

    def _add_department(self):
        dialog = DepartmentDialog(api_client=self.api_client, parent=self)
        if dialog.exec():
            self._load_departments()

    def _add_position(self):
        dialog = PositionDialog(api_client=self.api_client, departments=self.departments, parent=self)
        if dialog.exec():
            self._load_positions()


class DepartmentDialog(EnterpriseDialog):
    def __init__(self, api_client=None, department=None, parent=None):
        self._api_client = api_client
        self._dept = department
        self._submitting = False
        super().__init__("Edit Department" if department else "Add Department", DialogType.CUSTOM, parent)
        self.setMinimumWidth(400)
        self.set_content(self._build_content())

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText("DEPT")
        self.name = QLineEdit()
        self.name.setPlaceholderText("Department name")
        if self._dept:
            self.code.setText(self._dept.get("code", ""))
            self.name.setText(self._dept.get("name", ""))
        form.addRow("Code:", self.code)
        form.addRow("Name:", self.name)
        layout.addLayout(form)
        layout.addStretch()
        btn = QHBoxLayout()
        btn.addStretch()
        cancel = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel.clicked.connect(self.reject)
        save = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save.clicked.connect(self._save)
        btn.addWidget(cancel)
        btn.addWidget(save)
        layout.addLayout(btn)
        return widget

    def _save(self):
        if self._submitting:
            return
        self._submitting = True
        code = self.code.text().strip()
        name = self.name.text().strip()
        if not code or not name:
            AlertDialog.warning("Validation Error", "Code and Name are required.", self)
            self._submitting = False
            return
        data = {"code": code, "name": name}

        def on_success(resp):
            self._submitting = False
            if resp and isinstance(resp, dict) and (resp.get("success") or resp.get("id")):
                self.accept()
            else:
                err = resp.get("error", "Save failed") if isinstance(resp, dict) else "Save failed"
                AlertDialog.error("Error", str(err), self)

        def on_error(message):
            self._submitting = False
            AlertDialog.error("Error", str(message), self)

        started = self.run_api_request(
            key="department_save",
            method="PUT" if self._dept else "POST",
            endpoint=f"/api/hr/departments/{self._dept['id']}/" if self._dept else "/api/hr/departments/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self._submitting = False


class PositionDialog(EnterpriseDialog):
    def __init__(self, api_client=None, departments=None, parent=None):
        self._api_client = api_client
        self._departments = departments or []
        self._submitting = False
        super().__init__("Add Position", DialogType.CUSTOM, parent)
        self.setMinimumWidth(400)
        self.set_content(self._build_content())

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText("POS")
        self.title = QLineEdit()
        self.title.setPlaceholderText("Position title")
        self.dept_combo = QComboBox()
        for d in self._departments:
            self.dept_combo.addItem(d.get("name", ""), d.get("id"))
        form.addRow("Code:", self.code)
        form.addRow("Title:", self.title)
        form.addRow("Department:", self.dept_combo)
        layout.addLayout(form)
        layout.addStretch()
        btn = QHBoxLayout()
        btn.addStretch()
        cancel = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel.clicked.connect(self.reject)
        save = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        save.clicked.connect(self._save)
        btn.addWidget(cancel)
        btn.addWidget(save)
        layout.addLayout(btn)
        return widget

    def _save(self):
        if self._submitting:
            return
        self._submitting = True
        code = self.code.text().strip()
        title = self.title.text().strip()
        dept_id = self.dept_combo.currentData()
        if not code or not title:
            AlertDialog.warning("Validation Error", "Code and Title are required.", self)
            self._submitting = False
            return
        data = {"code": code, "title": title, "department": dept_id}

        def on_success(resp):
            self._submitting = False
            if resp and isinstance(resp, dict) and (resp.get("success") or resp.get("id")):
                self.accept()
            else:
                err = resp.get("error", "Save failed") if isinstance(resp, dict) else "Save failed"
                AlertDialog.error("Error", str(err), self)

        def on_error(message):
            self._submitting = False
            AlertDialog.error("Error", str(message), self)

        started = self.run_api_request(
            key="position_save",
            method="POST",
            endpoint="/api/hr/positions/",
            data=data,
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self._submitting = False
