"""
DecisionWorkspace — consolidated causal + decision-support workspace.
Hosts: CausalStrength, WhatIf, WhyAnalysis, DecisionRanking.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from ui.constants import (MARGIN_PAGE, SPACING_MD)
# from ui.cognitive_reasoning.what_if_impact_panel import WhatIfImpactPanel
# from ui.cognitive_reasoning.why_analysis_panel import WhyAnalysisPanel
from ui.causal_scoring.causal_strength_panel import CausalStrengthPanel
from ui.causal_scoring.decision_ranking_dashboard import DecisionIntelligenceDashboard


class DecisionWorkspace(QWidget):
    """Consolidated decision-support workspace."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        from theme.style_builder import UIStyleBuilder
        header = QLabel("Decision Support")
        header.setStyleSheet(UIStyleBuilder.get_label_style("title"))
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setStyleSheet(UIStyleBuilder.get_tab_style())
        tabs.addTab(DecisionIntelligenceDashboard(api_client=api_client), "Decision Ranking")
        tabs.addTab(CausalStrengthPanel(api_client=api_client), "Causal Strength")
        # tabs.addTab(WhatIfImpactPanel(api_client=api_client), "What-If Analysis")
        # tabs.addTab(WhyAnalysisPanel(api_client=api_client), "Why Analysis")
        layout.addWidget(tabs)
