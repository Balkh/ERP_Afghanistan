"""
Phase 5B.7 — Anomaly Investigation Screen.

Drift → Patterns → Related Events → Replay → Root Cause.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QTextEdit, QLineEdit, QSplitter,
                                 QTableWidget, QTableWidgetItem, QHeaderView, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from api.client import APIClient
from api.intelligence_client import IntelligenceAPIClient
from api.observability_client import ObservabilityAPIClient
from api.truth_client import TruthAPIClient
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
    TEXT_SECTION_TITLE,
                           MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD, BORDER_RADIUS_SM)
from ui.constants import TEXT_SECTION_TITLE


class AnomalyInvestigationScreen(QWidget):
    """Drift → Patterns → Related Events → Replay → Root Cause."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._intel = IntelligenceAPIClient(self._api)
        self._obs = ObservabilityAPIClient(self._api)
        self._truth = TruthAPIClient(self._api)
        self._router = get_router()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Anomaly Investigation")
        header.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        # Domain selector
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Domain:"))
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["inventory", "accounting", "hr", "sales_purchase"])
        self.domain_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        sel_layout.addWidget(self.domain_combo)

        refresh_btn = QPushButton("⟳ Analyze")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_WARNING}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        refresh_btn.clicked.connect(self._analyze)
        sel_layout.addWidget(refresh_btn)
        layout.addLayout(sel_layout)

        splitter = QSplitter(Qt.Horizontal)

        # Drift & Patterns panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.drift_text = QTextEdit()
        self.drift_text.setReadOnly(True)
        self.drift_text.setPlaceholderText("Drift & anomaly data...")
        self.drift_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; }}
        """)
        left_layout.addWidget(QLabel("Drift & Patterns"))
        left_layout.addWidget(self.drift_text)

        # Replay & Root Cause panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.replay_text = QTextEdit()
        self.replay_text.setReadOnly(True)
        self.replay_text.setPlaceholderText("Replay & root cause data...")
        self.replay_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; }}
        """)
        right_layout.addWidget(QLabel("Replay & Root Cause"))
        right_layout.addWidget(self.replay_text)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        actions = QHBoxLayout()
        for label, cb in [
            ("📊 Drift All", self._load_drift_all),
            ("🔍 Anomaly Graph", self._load_anomaly_graph),
            ("⏱ Temporal", self._load_temporal),
            ("📋 Consistency", self._load_consistency),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; }}
                QPushButton:hover {{ background: {COLOR_INFO}; color: white; }}
            """)
            btn.clicked.connect(cb)
            actions.addWidget(btn)
        layout.addLayout(actions)

    def _analyze(self):
        domain = self.domain_combo.currentText()
        try:
            patterns = self._intel.get_patterns(domain)
            d = patterns.get("data", patterns) if isinstance(patterns, dict) else patterns
            text = f"Pattern Analysis for {domain}:\n\n"
            for ptype, plist in d.get("patterns", {}).items():
                text += f"  {ptype}: {len(plist)} found\n"
                for p in plist[:5]:
                    text += f"    - {p.get('event_types', [])} (x{p.get('occurrence_count', 0)})\n"
            self.drift_text.setPlainText(text)
        except Exception as e:
            self.drift_text.setPlainText(f"Pattern error: {e}")

    def _load_drift_all(self):
        domain = self.domain_combo.currentText()
        try:
            drift = self._intel.get_all_drift(domain)
            d = drift.get("data", drift) if isinstance(drift, dict) else drift
            text = f"Drift for {domain}: {d.get('aggregate_count', 0)} aggregates\n\n"
            for r in d.get("reports", [])[:10]:
                text += f"  {r.get('entity_id','')}: score={r.get('drift_score','')} [{r.get('confidence_level','')}]\n"
            self.drift_text.setPlainText(text)
        except Exception as e:
            self.drift_text.setPlainText(f"Drift error: {e}")

    def _load_anomaly_graph(self):
        domain = self.domain_combo.currentText()
        try:
            graph = self._intel.get_anomaly_graph(domain)
            d = graph.get("data", graph) if isinstance(graph, dict) else graph
            text = f"Anomaly Graph: {d.get('node_count', 0)} nodes, {d.get('edge_count', 0)} edges\n"
            text += f"Domains: {d.get('domains_involved', [])}\n"
            text += f"Confidence: {d.get('confidence_level', 'N/A')}"
            self.drift_text.setPlainText(text)
        except Exception as e:
            self.drift_text.setPlainText(f"Graph error: {e}")

    def _load_temporal(self):
        domain = self.domain_combo.currentText()
        try:
            temp = self._intel.get_temporal_drift(domain)
            d = temp.get("data", temp) if isinstance(temp, dict) else temp
            text = f"Temporal Drift for {domain}:\n"
            text += f"  Trend: {d.get('overall_trend', 'N/A')}\n"
            text += f"  Acceleration: {d.get('acceleration', 'N/A')}\n"
            text += f"  Segments: {d.get('segment_count', 0)}\n"
            text += f"  Persistence: {d.get('persistence_score', 'N/A')}"
            self.drift_text.setPlainText(text)
        except Exception as e:
            self.drift_text.setPlainText(f"Temporal error: {e}")

    def _load_consistency(self):
        try:
            cons = self._intel.get_consistency()
            d = cons.get("data", cons) if isinstance(cons, dict) else cons
            text = f"Consistency Deviations: {d.get('total_deviations', 0)}\n\n"
            for dev in d.get("deviations", []):
                text += f"  [{dev.get('deviation_type','')}] {dev.get('affected_entities', [])}\n"
                text += f"    Score: {dev.get('deviation_score','')} [{dev.get('confidence_level','')}]\n"
            self.replay_text.setPlainText(text)
        except Exception as e:
            self.replay_text.setPlainText(f"Consistency error: {e}")

    def set_api_client(self, client: APIClient):
        self._api = client
        self._intel = IntelligenceAPIClient(client)
        self._obs = ObservabilityAPIClient(client)
        self._truth = TruthAPIClient(client)
