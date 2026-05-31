"""
OperationsDashboard — consolidated system operations + health monitoring.
Hosts: Approvals.
"""

from PySide6.QtWidgets import QVBoxLayout, QTabWidget, QLabel
from ui.constants import (MARGIN_PAGE, SPACING_MD,
                           TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.governance.approval_screen import ApprovalWorkflowScreen
from ui.screens.base_screen import BaseScreen


class OperationsDashboard(BaseScreen):
    """Consolidated operations dashboard — control center + health + tower + approvals."""

    def __init__(self, parent=None, api_client=None):
        self._init_api_client = api_client
        super().__init__(parent)

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Operations Dashboard")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(ApprovalWorkflowScreen(api_client=self._init_api_client), "Approvals")
        layout.addWidget(tabs)

    def _on_screen_shown(self):
        pass
