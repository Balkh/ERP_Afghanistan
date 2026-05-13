"""
Phase 5B.11 — Causal Reasoning Dashboard.

Main screen tying together WHY Analysis, Dependency Graph,
and What-If Explorer into one unified cognitive reasoning experience.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTabWidget, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from ui.cognitive_reasoning.why_analysis_panel import WhyAnalysisPanel
from ui.cognitive_reasoning.dependency_graph_view import DependencyGraphView
from ui.cognitive_reasoning.what_if_impact_panel import WhatIfImpactPanel
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)


class CausalReasoningDashboard(QWidget):
    """Main cognitive reasoning screen with 3 panels in tabs."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api_client = api_client or APIClient()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tabs for the 3 panels
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {COLOR_BG_MAIN}; }}
            QTabBar::tab {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            padding: 10px 20px; border: 1px solid {COLOR_BORDER};
            border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px;
            margin-right: 2px; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_ELEVATED}; }}
        """)

        self.why_panel = WhyAnalysisPanel(self._api_client)
        tabs.addTab(self.why_panel, "🔍 WHY Analysis")

        self.dep_panel = DependencyGraphView(self._api_client)
        tabs.addTab(self.dep_panel, "🔗 Dependency Map")

        self.what_if_panel = WhatIfImpactPanel(self._api_client)
        tabs.addTab(self.what_if_panel, "🔮 What-If Explorer")

        layout.addWidget(tabs)

    def analyze_anomaly(self, anomaly_type: str = "anomaly", domain: str = ""):
        """External entry point for cross-screen linking."""
        self.why_panel.analyze_entity(anomaly_type, domain)
        why_idx = 0
        parent_tabs = self.findParent(QTabWidget)
        if parent_tabs:
            parent_tabs.setCurrentIndex(why_idx)

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self.why_panel.set_api_client(client)
        self.dep_panel.set_api_client(client)
        self.what_if_panel.set_api_client(client)
