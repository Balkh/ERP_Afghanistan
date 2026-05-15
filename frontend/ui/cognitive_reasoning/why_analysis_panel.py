"""
Phase 5B.11 — WHY Analysis Panel.

Root cause chain visualization for any selected entity.
Click anomaly → see: Root Cause Chain → Contributing Events → Impacts.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QComboBox,
                                 QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from ui.cognitive_reasoning.causal_engine import CausalReasoningEngine
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD, BORDER_RADIUS_SM)
from ui.constants import TEXT_SECTION_TITLE, TEXT_BODY


class WhyAnalysisPanel(QWidget):
    """Root cause chain investigation panel.

    Analyzes WHY an anomaly/risk/forecast/decision occurred.
    Shows cause chain, contributing events, and cross-domain impacts.
    """

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api_client = api_client or APIClient()
        self._engine = CausalReasoningEngine(self._api_client)
        self._router = get_router()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("🔍 WHY Analysis — Root Cause Investigation")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        layout.addLayout(header)

        # Target selector
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Analyze:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(["anomaly", "risk", "forecast", "decision"])
        self.target_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        sel_layout.addWidget(self.target_combo)

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["all", "inventory", "accounting", "hr", "sales_purchase"])
        self.domain_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        sel_layout.addWidget(QLabel("Domain:"))
        sel_layout.addWidget(self.domain_combo)

        analyze_btn = QPushButton("🔍 Analyze WHY")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_DANGER}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        analyze_btn.clicked.connect(self._analyze)
        sel_layout.addWidget(analyze_btn)

        layout.addLayout(sel_layout)

        # Root cause chain
        chain_group = QGroupBox("Root Cause Chain (↓ flows downward)")
        chain_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-weight: bold;
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}
        """)
        chain_layout = QVBoxLayout(chain_group)
        self.chain_text = QTextEdit()
        self.chain_text.setReadOnly(True)
        self.chain_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        self.chain_text.setMaximumHeight(200)
        chain_layout.addWidget(self.chain_text)
        layout.addWidget(chain_group)

        # Causal graph + impact split
        split_layout = QHBoxLayout()

        left_group = QGroupBox("Contributing Factors")
        left_group.setStyleSheet(f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}")
        left_layout = QVBoxLayout(left_group)
        self.contrib_text = QTextEdit()
        self.contrib_text.setReadOnly(True)
        self.contrib_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px; font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        left_layout.addWidget(self.contrib_text)
        split_layout.addWidget(left_group)

        right_group = QGroupBox("Cross-Domain Impacts")
        right_group.setStyleSheet(f"QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}")
        right_layout = QVBoxLayout(right_group)
        self.impact_text = QTextEdit()
        self.impact_text.setReadOnly(True)
        self.impact_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px; font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        right_layout.addWidget(self.impact_text)
        split_layout.addWidget(right_group)

        layout.addLayout(split_layout)

    def analyze_entity(self, entity_type: str, domain: str = ""):
        """Programmatically trigger analysis (called from other screens)."""
        idx = self.target_combo.findText(entity_type)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)
        if domain:
            didx = self.domain_combo.findText(domain)
            if didx >= 0:
                self.domain_combo.setCurrentIndex(didx)
        self._analyze()

    def _analyze(self):
        target = self.target_combo.currentText()
        domain = self.domain_combo.currentText()
        if domain == "all":
            domain = ""

        try:
            if target == "anomaly":
                graph = self._engine.analyze_anomaly("selected", domain or "inventory")
                chain = self._engine.get_root_cause_chain("anomaly", "anomaly")
            elif target == "risk":
                graph = self._engine.analyze_risk()
                chain = self._engine.get_root_cause_chain("risk", "risk")
            elif target == "forecast":
                graph = self._engine.analyze_forecast(domain)
                chain = self._engine.get_root_cause_chain("forecast", "forecast")
            elif target == "decision":
                graph = self._engine.analyze_decision_impact()
                chain = self._engine.get_root_cause_chain("decision", "decision")
            else:
                return

            # Render chain (reversed = root at top)
            chain_text = "ROOT CAUSE CHAIN:\n"
            chain_text += "  ↓\n".join(f"  {c.replace('_', ' ').title()}" for c in reversed(chain))
            chain_text += f"\n  ↓\n  ← {target.upper()} ←"
            self.chain_text.setPlainText(chain_text)

            # Contributing factors
            contrib = "Contributing Nodes:\n"
            for n in graph.nodes[:8]:
                contrib += f"  [{n.node_type.value}] {n.label} (conf: {n.confidence:.0%})\n"
            self.contrib_text.setPlainText(contrib)

            # Impacts
            impacts = "Impact Links:\n"
            for e in graph.edges[:8]:
                impacts += f"  {e.source_id[:20]} → {e.target_id[:20]} [{e.edge_type.value}]\n"
            self.impact_text.setPlainText(impacts)

        except Exception as ex:
            self.chain_text.setPlainText(f"Analysis error: {ex}")

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self._engine = CausalReasoningEngine(client)
