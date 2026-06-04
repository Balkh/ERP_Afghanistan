"""
AnomalyInvestigationScreen — investigates detected anomalies in ERP events.

Created as a stub to resolve the broken import in
`ui.system.analytics_workspace.AnalyticsWorkspace`. The full anomaly
investigation workflow (event grouping, root cause surfacing, recommended
actions) is a follow-up deliverable; the stub renders a placeholder tab so
the Analytics workspace can load and the other wired screens remain
reachable.
"""
from PySide6.QtWidgets import QVBoxLayout, QLabel

from api.client import APIClient
from ui.constants import COLOR_TEXT_PRIMARY, MARGIN_PAGE, SPACING_MD
from ui.screens.base_screen import BaseScreen


class AnomalyInvestigationScreen(BaseScreen):
    """Placeholder for anomaly investigation workflow."""

    def __init__(self, api_client: APIClient = None, parent=None):
        self._api = api_client
        super().__init__(parent)

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QLabel("Anomaly Investigation")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(header)

        info = QLabel(
            "Anomaly investigation workflow is not yet implemented. "
            "Use Event Investigation for the underlying event trace."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(info)
        layout.addStretch()

    def _on_screen_shown(self):
        pass

    def _on_screen_hidden(self):
        pass
