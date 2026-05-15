"""
ObservabilityConsole — consolidated observability + replay + dashboards.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from ui.constants import (MARGIN_PAGE, SPACING_MD,
                           TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.observability.observability_screen import ObservabilityScreen
from ui.observability.replay_screen import ReplayTimeTravelScreen
from ui.observability.dashboards import (
    ObservabilityMainScreen, ControlCenterDashboard,
    UnifiedTimelineView, IncidentIntelligenceView,
    PredictiveDriftDashboard, ReplayTimeTravelView, DigitalTwinTelemetryView,
)


class ObservabilityConsole(QWidget):
    """Consolidated observability workspace."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Observability Console")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(ObservabilityScreen(api_client=api_client), "Overview")
        tabs.addTab(ObservabilityMainScreen(api_client=api_client), "Main Dashboard")
        tabs.addTab(ControlCenterDashboard(api_client=api_client), "Control Center")
        tabs.addTab(UnifiedTimelineView(api_client=api_client), "Timeline")
        tabs.addTab(IncidentIntelligenceView(api_client=api_client), "Incidents")
        tabs.addTab(PredictiveDriftDashboard(api_client=api_client), "Predictive Drift")
        tabs.addTab(ReplayTimeTravelScreen(api_client=api_client), "Replay")
        tabs.addTab(ReplayTimeTravelView(api_client=api_client), "Time Travel")
        tabs.addTab(DigitalTwinTelemetryView(api_client=api_client), "Digital Twin")
        layout.addWidget(tabs)
