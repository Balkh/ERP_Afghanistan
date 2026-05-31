"""
Phase 5B.7 — Event Investigation Screen.

Event → Detail → Trace → Timeline → Causation → Drift
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QTextEdit, QLineEdit, QSplitter)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.screens.base_screen import BaseScreen

from api.client import APIClient
from api.truth_client import TruthAPIClient
from api.observability_client import ObservabilityAPIClient
from api.intelligence_client import IntelligenceAPIClient
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_TEXT_PRIMARY,
                           COLOR_PRIMARY, COLOR_BORDER,
                           SPACING_LG, SPACING_SM, TEXT_SECTION_TITLE, MARGIN_PAGE,
                           BORDER_RADIUS_MD, BORDER_RADIUS_SM)


class EventInvestigationScreen(BaseScreen):
    """Full event investigation: Event → Detail → Trace → Timeline → Causation → Drift."""

    def __init__(self, api_client: APIClient = None):
        self._api = api_client or APIClient()
        self._truth = TruthAPIClient(self._api)
        self._obs = ObservabilityAPIClient(self._api)
        self._intel = IntelligenceAPIClient(self._api)
        self._router = get_router()
        super().__init__()
        self._setup_screen()

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Event Investigation")
        header.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        # Search
        search_layout = QHBoxLayout()
        self.event_id_input = QLineEdit()
        self.event_id_input.setPlaceholderText("Event ID...")
        self.event_id_input.setStyleSheet(f"""
            QLineEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px; }}
        """)
        search_layout.addWidget(self.event_id_input)

        search_btn = EnterpriseButton("🔍 Investigate", variant=ButtonVariant.PRIMARY)
        search_btn.clicked.connect(self._investigate)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Info splitter
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.event_detail = QTextEdit()
        self.event_detail.setReadOnly(True)
        self.event_detail.setPlaceholderText("Event detail will appear here...")
        self.event_detail.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; }}
        """)
        left_layout.addWidget(QLabel("Event Detail"))
        left_layout.addWidget(self.event_detail)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.trace_view = QTextEdit()
        self.trace_view.setReadOnly(True)
        self.trace_view.setPlaceholderText("Trace chain will appear here...")
        self.trace_view.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; }}
        """)
        right_layout.addWidget(QLabel("Trace & Causation"))
        right_layout.addWidget(self.trace_view)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        # Action buttons
        actions = QHBoxLayout()
        for label, cb in [
            ("⟳ Timeline", self._load_timeline),
            ("🔗 Causation", self._load_causation),
            ("📊 Drift Check", self._load_drift),
        ]:
            btn = EnterpriseButton(label, variant=ButtonVariant.SECONDARY)
            btn.clicked.connect(cb)
            actions.addWidget(btn)

        layout.addLayout(actions)

    def _on_screen_shown(self):
        pass

    def _investigate(self):
        eid = self.event_id_input.text().strip()
        if not eid:
            return
        try:
            ctx = self._router.get_context()
            ctx.set_event(eid)

            event = self._truth.get_event(eid)
            if event:
                import json
                self.event_detail.setPlainText(json.dumps(event, indent=2))
                ctx.selected_domain = event.get("domain", "")
                ctx.selected_aggregate_id = event.get("aggregate_id", "")
            else:
                self.event_detail.setPlainText(f"Event {eid} not found.")

            trace = self._obs.trace_by_event(eid)
            if trace:
                d = trace.get("data", trace) if isinstance(trace, dict) else trace
                self.trace_view.setPlainText(
                    f"Aggregate: {d.get('aggregate_id', 'N/A')}\n"
                    f"Event Count: {d.get('event_count', 0)}\n"
                    f"Hash: {d.get('integrity_hash', 'N/A')[:32]}..."
                )
        except Exception as e:
            self.event_detail.setPlainText(f"Error: {e}")

    def _load_timeline(self):
        ctx = self._router.get_context()
        try:
            tl = self._obs.get_aggregate_timeline(ctx.selected_domain or "inventory",
                                                    ctx.selected_aggregate_id)
            d = tl.get("data", tl) if isinstance(tl, dict) else tl
            entries = d.get("entries", [])
            text = f"Timeline ({len(entries)} events):\n"
            for e in entries[:20]:
                text += f"  [{e.get('timestamp','')[:19]}] {e.get('event_type','')}: {e.get('summary','')}\n"
            self.trace_view.setPlainText(text)
        except Exception as ex:
            self.trace_view.setPlainText(f"Timeline error: {ex}")

    def _load_causation(self):
        eid = self.event_id_input.text().strip()
        if not eid:
            return
        try:
            graph = self._obs.causation_graph(eid)
            d = graph.get("data", graph) if isinstance(graph, dict) else graph
            text = f"Causation Graph: {d.get('node_count', 0)} nodes, {d.get('edge_count', 0)} edges\n"
            for edge in d.get("edges", []):
                text += f"  {edge.get('cause','')[:12]} → {edge.get('effect','')[:12]} [{edge.get('relationship','')}]\n"
            self.trace_view.setPlainText(text)
        except Exception as ex:
            self.trace_view.setPlainText(f"Causation error: {ex}")

    def _load_drift(self):
        ctx = self._router.get_context()
        try:
            drift = self._intel.get_aggregate_drift(ctx.selected_domain or "inventory",
                                                     ctx.selected_aggregate_id)
            d = drift.get("data", drift) if isinstance(drift, dict) else drift
            text = f"Drift Score: {d.get('drift_score', 'N/A')}\n"
            text += f"Velocity: {d.get('drift_velocity', 'N/A')}\n"
            dev = d.get("deviation", {})
            if dev:
                text += f"Z-Score: {dev.get('z_score', 'N/A')}\n"
                text += f"Direction: {dev.get('direction', 'N/A')}"
            self.trace_view.setPlainText(text)
        except Exception as ex:
            self.trace_view.setPlainText(f"Drift error: {ex}")

    def set_api_client(self, client: APIClient):
        self._api = client
        self._truth = TruthAPIClient(client)
        self._obs = ObservabilityAPIClient(client)
        self._intel = IntelligenceAPIClient(client)
