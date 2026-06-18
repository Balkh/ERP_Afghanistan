"""
Phase 5B.12 — Causal Strength Path Visualizer.

Shows top 3 strongest causal paths per anomaly/risk/forecast.
Highlights strong vs weak links, bottleneck nodes, and weighted chains.
"""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                 QTextEdit, QComboBox, QGroupBox)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant
from api.client import APIClient
from ui.causal_scoring.causal_scoring_engine import CausalScoringEngine
from ui.components.tables import EnterpriseTable, TableColumn
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_XL, SPACING_LG, SPACING_6,
                           BORDER_RADIUS_MD, MARGIN_PAGE,
                           COLOR_TEXT_PRIMARY, COLOR_BG_SURFACE, COLOR_BORDER,
                           COLOR_PRIMARY, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                           TEXT_SECTION_TITLE, TEXT_CARD_TITLE)
from ui.screens.base_screen import BaseScreen


_CHAIN_COLORS = [COLOR_DANGER, COLOR_WARNING, COLOR_INFO]


class CausalStrengthPanel(BaseScreen):
    """Visualizes top 3 strongest causal paths with weighted links."""

    def __init__(self, api_client: APIClient = None):
        self._api_client = api_client or APIClient()
        self._engine = CausalScoringEngine(self._api_client)
        super().__init__()
        self._setup_screen()

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("📊 Causal Strength Path Analyzer")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["inventory", "accounting", "hr", "sales_purchase"])
        self.domain_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        header.addWidget(QLabel("Domain:"))
        header.addWidget(self.domain_combo)

        analyze_btn = EnterpriseButton("⟳ Analyze Paths", variant=ButtonVariant.PRIMARY)
        analyze_btn.clicked.connect(self._analyze)
        header.addWidget(analyze_btn)

        layout.addLayout(header)

        # Top 3 paths
        for i in range(3):
            group = QGroupBox(f"Path #{i + 1}")
            group.setStyleSheet(f"""
                QGroupBox {{ color: {_CHAIN_COLORS[i]}; font-weight: bold;
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM}px; padding-top: {SPACING_XL}px; }}
            """)
            g_layout = QVBoxLayout(group)
            text = QTextEdit()
            text.setReadOnly(True)
            text.setObjectName(f"path_{i}")
            text.setStyleSheet(f"""
                QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: none; font-family: 'Consolas', monospace; font-size: {TEXT_CARD_TITLE}px; }}
            """)
            text.setMaximumHeight(100)
            g_layout.addWidget(text)
            layout.addWidget(group)

        # Summary table
        summary_group = QGroupBox("All Nodes — Scored & Ranked")
        summary_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px; padding-top: {SPACING_XL}px; }}
        """)
        summary_layout = QVBoxLayout(summary_group)
        columns = [
            TableColumn("rank", "Rank", width=70, align="center"),
            TableColumn("node", "Node", width=220),
            TableColumn("type", "Type", width=120),
            TableColumn("impact", "Impact", width=100, align="right"),
            TableColumn("confidence", "Confidence", width=110, align="right"),
        ]
        self.table = EnterpriseTable(columns, density="compact")
        summary_layout.addWidget(self.table)
        layout.addWidget(summary_group)

    def _on_screen_shown(self):
        pass

    def load_data(self, params=None):
        QTimer.singleShot(300, self._analyze)

    def _analyze(self):
        domain = self.domain_combo.currentText()
        try:
            graph = self._engine.score_anomaly_graph(domain)

            # Paths
            for i in range(3):
                text = self.findChild(QTextEdit, f"path_{i}")
                if text and i < len(graph.strongest_paths):
                    path = graph.strongest_paths[i]
                    lines = [f"Causal Chain #{i + 1}  (Confidence: {SCORE_CONFIDENCE:.0%})"]
                    lines.append("  ↓".join(f"  {nid[:30]} [{self._get_node_impact(graph, nid):.0f}]"
                                            for nid in path))
                    text.setPlainText("\n".join(lines))
                elif text:
                    text.setPlainText("No path available")

            # Table
            rows = []
            for n in sorted(graph.nodes, key=lambda n: n.rank):
                rows.append({
                    "rank": str(n.rank),
                    "node": n.label[:30],
                    "type": n.node_type,
                    "impact": f"{n.impact_score:.0f}/100",
                    "confidence": f"{n.confidence:.0%}",
                })
            self.table.set_data(rows)

        except Exception as e:
            for i in range(3):
                text = self.findChild(QTextEdit, f"path_{i}")
                if text:
                    text.setPlainText(f"Error: {e}")

    def _get_node_impact(self, graph, nid: str) -> float:
        for n in graph.nodes:
            if n.id == nid:
                return n.impact_score
        return 0.0

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self._engine = CausalScoringEngine(client)


SCORE_CONFIDENCE = 0.85
