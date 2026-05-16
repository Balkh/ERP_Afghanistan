"""
Phase 5B.12 — Decision Intelligence Dashboard.

4 sections:
1. Ranked Decisions Table
2. Causal Strength Paths
3. Risk vs Impact Matrix
4. Decision Comparison Panel
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QTabWidget,
                                 QTableWidget, QTableWidgetItem, QHeaderView,
                                 QComboBox, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from ui.causal_scoring.causal_scoring_engine import CausalScoringEngine
from ui.causal_scoring.decision_impact_engine import DecisionImpactEngine
from ui.components.tables import build_table_stylesheet
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM, SPACING_XL,
    TEXT_BODY, TEXT_PAGE_TITLE,
                           MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD)
from ui.constants import TEXT_PAGE_TITLE, TEXT_BODY


class DecisionIntelligenceDashboard(QWidget):
    """Main decision intelligence screen with 4 analysis sections."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api_client = api_client or APIClient()
        self._scoring = CausalScoringEngine(self._api_client)
        self._ranking = DecisionImpactEngine(self._api_client)
        self._build_ui()
        QTimer.singleShot(500, self._refresh_all)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("🎯 Decision Intelligence Dashboard")
        title_font = QFont("Segoe UI", TEXT_PAGE_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.refresh_btn = QPushButton("⟳ Refresh All")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px {SPACING_LG}px; font-weight: bold; }}
        """)
        self.refresh_btn.clicked.connect(self._refresh_all)
        header.addWidget(self.refresh_btn, alignment=Qt.AlignRight)

        layout.addLayout(header)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {COLOR_BG_MAIN}; }}
            QTabBar::tab {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            padding: {SPACING_MD}px {SPACING_XL}px; border: 1px solid {COLOR_BORDER};
            border-bottom: none; border-top-left-radius: {BORDER_RADIUS_MD}px; border-top-right-radius: {BORDER_RADIUS_MD}px;
            margin-right: 2px; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_ELEVATED}; }}
        """)

        # Tab 1: Ranked Decisions
        tab1 = QWidget()
        t1l = QVBoxLayout(tab1)
        self.ranked_table = QTableWidget()
        self.ranked_table.setColumnCount(6)
        self.ranked_table.setHorizontalHeaderLabels(
            ["Rank", "Decision Type", "Action", "Impact", "Risk", "Overall Score"])
        self.ranked_table.horizontalHeader().setStretchLastSection(True)
        self.ranked_table.setAlternatingRowColors(True)
        self.ranked_table.setStyleSheet(build_table_stylesheet())
        t1l.addWidget(self.ranked_table)
        tabs.addTab(tab1, "① Ranked Decisions")

        # Tab 2: Causal Strength
        tab2 = QWidget()
        t2l = QVBoxLayout(tab2)
        self.causal_text = QTextEdit()
        self.causal_text.setReadOnly(True)
        self.causal_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        t2l.addWidget(self.causal_text)
        tabs.addTab(tab2, "② Causal Strength Paths")

        # Tab 3: Risk vs Impact Matrix
        tab3 = QWidget()
        t3l = QVBoxLayout(tab3)
        self.matrix_text = QTextEdit()
        self.matrix_text.setReadOnly(True)
        self.matrix_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        t3l.addWidget(self.matrix_text)
        tabs.addTab(tab3, "③ Risk vs Impact Matrix")

        # Tab 4: Comparison
        tab4 = QWidget()
        t4l = QVBoxLayout(tab4)
        self.compare_text = QTextEdit()
        self.compare_text.setReadOnly(True)
        self.compare_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        t4l.addWidget(self.compare_text)
        tabs.addTab(tab4, "④ Decision Comparison")

        layout.addWidget(tabs)

    def _refresh_all(self):
        self._refresh_ranked()
        self._refresh_causal()
        self._refresh_matrix()
        self._refresh_comparison()

    def _refresh_ranked(self):
        try:
            result = self._ranking.rank_decisions()
            self.ranked_table.setRowCount(len(result.scores))
            for i, s in enumerate(result.scores):
                self.ranked_table.setItem(i, 0, QTableWidgetItem(str(s.overall_rank)))
                self.ranked_table.setItem(i, 1, QTableWidgetItem(s.decision_type.replace("_", " ").title()))
                self.ranked_table.setItem(i, 2, QTableWidgetItem(s.action_summary[:40]))
                self.ranked_table.setItem(i, 3, QTableWidgetItem(f"{s.impact_score:.0f}"))
                self.ranked_table.setItem(i, 4, QTableWidgetItem(f"{s.risk_score:.0f}"))
                self.ranked_table.setItem(i, 5, QTableWidgetItem(f"{s.overall_score:.1f}"))
        except Exception as e:
            self.ranked_table.setRowCount(0)

    def _refresh_causal(self):
        try:
            graph = self._scoring.score_anomaly_graph("inventory")
            lines = [f"Overall Impact Score: {graph.overall_impact_score:.0f}/100", ""]
            lines.append("Strongest Paths:")
            for i, path in enumerate(graph.strongest_paths[:3]):
                score = sum(
                    n.impact_score for n in graph.nodes
                    if n.id in path
                ) / max(len(path), 1)
                lines.append(f"  Path #{i + 1}: {score:.0f} avg impact")
                for nid in path:
                    node = next((n for n in graph.nodes if n.id == nid), None)
                    if node:
                        lines.append(f"    ↳ {node.label} [{node.impact_score:.0f}]")
            lines.append("")
            lines.append(f"Bottleneck Nodes: {', '.join(graph.bottleneck_nodes)}")
            self.causal_text.setPlainText("\n".join(lines))
        except Exception as e:
            self.causal_text.setPlainText(f"Causal scoring unavailable: {e}")

    def _refresh_matrix(self):
        try:
            result = self._ranking.rank_decisions()
            matrix = self._ranking.get_risk_vs_impact_matrix(result.scores)
            lines = ["Risk vs Impact Matrix (top 10 decisions):\n"]
            lines.append(f"{'Rank':<6} {'Action':<35} {'Risk':<8} {'Impact':<8}")
            lines.append("-" * 60)
            for m in matrix:
                lines.append(
                    f"{m['rank']:<6} {m['label']:<35} {m['risk']:<8.0f} {m['impact']:<8.0f}"
                )
            self.matrix_text.setPlainText("\n".join(lines))
        except Exception as e:
            self.matrix_text.setPlainText(f"Matrix unavailable: {e}")

    def _refresh_comparison(self):
        try:
            result = self._ranking.rank_decisions()
            if not result.scores:
                self.compare_text.setPlainText("No decisions to compare.")
                return
            lines = ["Decision Comparison (Top 5):\n"]
            for s in result.scores[:5]:
                lines.append(f"  Rank #{s.overall_rank}: {s.action_summary[:40]}")
                lines.append(f"    Impact={s.impact_score:.0f}  Risk={s.risk_score:.0f}  "
                              f"Feasibility={s.feasibility_score:.0f}  Confidence={s.confidence_score:.0%}")
                lines.append(f"    Overall Score: {s.overall_score:.1f}")
                lines.append(f"    Formula: ({s.impact_score}×0.4) + "
                              f"({100 - s.risk_score}×0.3) + "
                              f"({s.feasibility_score}×0.2) + ({s.confidence_score * 100}×0.1)")
                lines.append("")
            self.compare_text.setPlainText("\n".join(lines))
        except Exception as e:
            self.compare_text.setPlainText(f"Comparison unavailable: {e}")

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self._scoring = CausalScoringEngine(client)
        self._ranking = DecisionImpactEngine(client)
