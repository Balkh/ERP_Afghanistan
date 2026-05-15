"""
AnalyticsWorkspace — consolidated intelligence/analytics hub.
Hosts: Integrity, Workflow Intel, Drift, Correlation, Event Store, Investigations.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt
from ui.constants import (MARGIN_PAGE, SPACING_MD,
                           TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.system.integrity_screen import SystemIntegrityScreen
from ui.system.workflow_intelligence_screen import WorkflowIntelligenceScreen
from ui.system.drift_intelligence_screen import DriftIntelligenceScreen
from ui.system.correlation_screen import SystemCorrelationScreen
from ui.truth.event_store_screen import EventStoreScreen
from ui.investigation.anomaly_investigation_screen import AnomalyInvestigationScreen
from ui.investigation.event_investigation_screen import EventInvestigationScreen


class AnalyticsWorkspace(QWidget):
    """Single unified workspace for all ERP analytical views."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Analytics & Intelligence")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(SystemIntegrityScreen(api_client=api_client), "System Integrity")
        tabs.addTab(WorkflowIntelligenceScreen(api_client=api_client), "Workflow Intelligence")
        tabs.addTab(DriftIntelligenceScreen(api_client=api_client), "Drift Detection")
        tabs.addTab(SystemCorrelationScreen(api_client=api_client), "Correlation")
        tabs.addTab(EventStoreScreen(api_client=api_client), "Event Store")
        tabs.addTab(AnomalyInvestigationScreen(api_client=api_client), "Anomaly Investigation")
        tabs.addTab(EventInvestigationScreen(api_client=api_client), "Event Investigation")
        layout.addWidget(tabs)
