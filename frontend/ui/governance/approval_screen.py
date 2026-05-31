"""
Phase 5B.6 — Approval Workflow Screen.
PySide6 UI for viewing and managing governance approval workflows.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QTableWidget, QTableWidgetItem,
                                 QTextEdit, QSplitter, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import AlertDialog
from ui.screens.base_screen import BaseScreen

from api.client import APIClient
from api.governance_client import GovernanceAPIClient
from ui.components.tables import build_table_stylesheet
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_SECONDARY, COLOR_PRIMARY, COLOR_SUCCESS,
                           COLOR_DANGER, COLOR_BORDER, SPACING_LG,
                           SPACING_SM, MARGIN_PAGE, TEXT_BODY, TEXT_CARD_TITLE, TEXT_PAGE_TITLE, BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG, SPACING_XS)


class ApprovalWorkflowScreen(BaseScreen):
    """Screen for viewing and managing governance approval workflows."""

    def __init__(self, api_client: APIClient = None):
        self._api = GovernanceAPIClient(api_client or APIClient())
        self._current_workflow_id = None
        super().__init__()
        self._setup_screen()

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Approval Workflows")
        header.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG};")

        # Left: Workflow list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        list_header = QLabel("Active Workflows")
        list_header.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        list_header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; padding: {SPACING_XS}px;")
        left_layout.addWidget(list_header)

        self.refresh_btn = EnterpriseButton("⟳ Refresh", variant=ButtonVariant.PRIMARY)
        self.refresh_btn.clicked.connect(self._refresh)
        left_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Action", "Risk", "State", "Signatures"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(build_table_stylesheet())
        self.table.itemClicked.connect(self._on_workflow_selected)
        left_layout.addWidget(self.table)

        # Right: Detail panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.detail_label = QLabel("Select a workflow to view details")
        self.detail_label.setFont(QFont("Segoe UI", TEXT_BODY))
        self.detail_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        right_layout.addWidget(self.detail_label)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{ background-color: {COLOR_BG_MAIN}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px; }}
        """)
        right_layout.addWidget(self.detail_text)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.approve_btn = EnterpriseButton("✓ Approve", variant=ButtonVariant.SUCCESS)
        self.approve_btn.clicked.connect(lambda: self._sign("APPROVED"))
        self.approve_btn.setEnabled(False)
        btn_layout.addWidget(self.approve_btn)

        self.reject_btn = EnterpriseButton("✗ Reject", variant=ButtonVariant.DANGER)
        self.reject_btn.clicked.connect(lambda: self._sign("REJECTED"))
        self.reject_btn.setEnabled(False)
        btn_layout.addWidget(self.reject_btn)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        self._refresh()

    def _refresh(self):
        try:
            workflows = self._api.list_workflows()
            self.table.setRowCount(len(workflows))
            for i, wf in enumerate(workflows):
                self.table.setItem(i, 0, QTableWidgetItem(wf.get("workflow_id", "")[:12]))
                self.table.setItem(i, 1, QTableWidgetItem(wf.get("action_type", "")))
                self.table.setItem(i, 2, QTableWidgetItem(wf.get("risk_level", "")))
                self.table.setItem(i, 3, QTableWidgetItem(wf.get("state", "")))
                sigs = f"{wf.get('signature_count', 0)}/{wf.get('required_signatures', 0)}"
                self.table.setItem(i, 4, QTableWidgetItem(sigs))
        except Exception as e:
            self.detail_text.setPlainText(f"Error loading workflows: {e}")

    def _on_workflow_selected(self, item):
        row = item.row()
        wid_item = self.table.item(row, 0)
        if not wid_item:
            return
        wid = self.table.item(row, 0).text()
        self._current_workflow_id = wid
        self.approve_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)
        try:
            # Try to get full details
            summary = self._api.get_workflow(wid)
            self.detail_label.setText(f"Workflow: {wid}")
            import json
            self.detail_text.setPlainText(
                json.dumps(summary.get("data", summary), indent=2)
            )
        except Exception:
            self.detail_text.setPlainText("Workflow selected (detail API pending)")

    def _sign(self, decision: str):
        if not self._current_workflow_id:
            return
        try:
            result = self._api.sign_workflow(
                self._current_workflow_id,
                approver_id="ui_user",
                authority_level="APPROVER",
                decision=decision,
                justification="Approved via UI",
            )
            AlertDialog.info(self, "Signature Submitted",
                                    f"Decision: {decision}\nNew State: {result.get('data', {}).get('state', 'unknown')}")
            self._refresh()
        except Exception as e:
            AlertDialog.warning(self, "Error", f"Signature failed: {e}")

    def set_api_client(self, client: APIClient):
        self._api = GovernanceAPIClient(client)
