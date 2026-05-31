"""
ObservabilityConsole — consolidated observability + replay + dashboards.
"""

from PySide6.QtWidgets import QVBoxLayout, QTabWidget, QLabel
from ui.constants import (MARGIN_PAGE, SPACING_MD,
                           TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY)
from ui.observability.dashboards import (
    ObservabilityMainScreen, ControlCenterDashboard,
    UnifiedTimelineView, IncidentIntelligenceView,
    PredictiveDriftDashboard, ReplayTimeTravelView, DigitalTwinTelemetryView,
)
from ui.screens.base_screen import BaseScreen


class ObservabilityConsole(BaseScreen):
    """Consolidated observability workspace."""

    def __init__(self, parent=None, api_client=None):
        self._init_api_client = api_client
        super().__init__(parent)

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Observability Console")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(ObservabilityMainScreen(api_client=self._init_api_client), "Main Dashboard")
        tabs.addTab(ControlCenterDashboard(api_client=self._init_api_client), "Control Center")
        tabs.addTab(UnifiedTimelineView(api_client=self._init_api_client), "Timeline")
        tabs.addTab(IncidentIntelligenceView(api_client=self._init_api_client), "Incidents")
        tabs.addTab(PredictiveDriftDashboard(api_client=self._init_api_client), "Predictive Drift")
        tabs.addTab(ReplayTimeTravelView(api_client=self._init_api_client), "Time Travel")
        tabs.addTab(DigitalTwinTelemetryView(api_client=self._init_api_client), "Digital Twin")
        layout.addWidget(tabs)

    def _on_screen_shown(self):
        pass
