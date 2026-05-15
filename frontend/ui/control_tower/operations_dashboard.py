"""
OperationsDashboard — consolidated system operations + health monitoring.
Hosts: ControlCenter, SystemHealth, FinancialTower, WorkflowExecution.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from ui.constants import (MARGIN_PAGE, SPACING_MD,
                           TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.system.control_center_screen import ControlCenterScreen
from ui.control_tower.system_health_screen import SystemHealthOverviewScreen
from ui.control_tower.financial_control_tower_screen import FinancialControlTowerScreen
from ui.control_tower.workflow_execution_screen import WorkflowExecutionScreen
from ui.governance.approval_screen import ApprovalWorkflowScreen


class OperationsDashboard(QWidget):
    """Consolidated operations dashboard — control center + health + tower + approvals."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Operations Dashboard")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(ControlCenterScreen(api_client=api_client), "Control Center")
        tabs.addTab(SystemHealthOverviewScreen(api_client=api_client), "System Health")
        tabs.addTab(FinancialControlTowerScreen(api_client=api_client), "Financial Tower")
        tabs.addTab(WorkflowExecutionScreen(api_client=api_client), "Workflow Execution")
        tabs.addTab(ApprovalWorkflowScreen(api_client=api_client), "Approvals")
        layout.addWidget(tabs)
