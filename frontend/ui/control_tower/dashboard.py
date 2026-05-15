"""
Phase 5B.7 — Control Tower Main Dashboard.

Unified enterprise overview showing:
- Real-time system health
- Pending approvals
- Active events
- Drift alerts
- Anomaly signals
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QGridLayout, QScrollArea,
                                 QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from datetime import datetime

from api.client import APIClient
from api.governance_client import GovernanceAPIClient
from api.truth_client import TruthAPIClient
from api.observability_client import ObservabilityAPIClient
from api.intelligence_client import IntelligenceAPIClient
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, TEXT_SECTION_TITLE, TEXT_BODY_SMALL, TEXT_BODY, TEXT_CARD_TITLE, TEXT_DISPLAY, BORDER_RADIUS_MD, BORDER_RADIUS_LG)
from ui.components.kpi_cards import KPICard
from runtime.timer_registry import register_timer, unregister_owner


class ControlTowerDashboard(QWidget):
    """Main Control Tower dashboard with unified enterprise overview."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._gov = GovernanceAPIClient(self._api)
        self._truth = TruthAPIClient(self._api)
        self._obs = ObservabilityAPIClient(self._api)
        self._intel = IntelligenceAPIClient(self._api)
        self._router = get_router()

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30000)
        register_timer("control_tower_dash", self._timer)

        QTimer.singleShot(500, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Header
        header = QHBoxLayout()
        title = QLabel("Enterprise Control Tower")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.status_label = QLabel("● Checking...")
        self.status_label.setStyleSheet(f"color: {COLOR_WARNING}; font-size: {TEXT_CARD_TITLE}px;")
        header.addWidget(self.status_label, alignment=Qt.AlignRight)

        refresh_btn = QPushButton("⟳ Refresh All")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Metrics grid
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(SPACING_MD)
        layout.addLayout(self.metrics_grid)

        # Workflow launcher buttons
        workflow_header = QLabel("Enterprise Workflows")
        wf_font = QFont("Segoe UI", TEXT_CARD_TITLE)
        wf_font.setWeight(QFont.Weight.Bold)
        workflow_header.setFont(wf_font)
        workflow_header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; padding-top: 8px;")
        layout.addWidget(workflow_header)

        wf_grid = QGridLayout()
        wf_grid.setSpacing(SPACING_MD)

        workflows = [
            ("Decision → Approval → Execute", "workflow_execution", COLOR_PRIMARY),
            ("Event Investigation", "event_investigation", COLOR_INFO),
            ("Anomaly Investigation", "anomaly_investigation", COLOR_WARNING),
            ("Financial Control Tower", "financial_control_tower", COLOR_SUCCESS),
            ("System Health Overview", "system_health", COLOR_DANGER),
            ("Approval Workflows", "approval_workflow", COLOR_INFO),
            ("Event Store Browser", "event_store", COLOR_TEXT_SECONDARY),
            ("Drift Dashboard", "drift_dashboard", COLOR_WARNING),
        ]

        for i, (label, screen_id, color) in enumerate(workflows):
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {color}; border-radius: {BORDER_RADIUS_LG}; padding: {SPACING_LG}px 20px;
                font-size: {TEXT_CARD_TITLE}px; font-weight: bold; text-align: left; }}
                QPushButton:hover {{ background-color: {COLOR_BG_ELEVATED}; }}
            """)
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda checked, sid=screen_id: self._launch_workflow(sid))
            wf_grid.addWidget(btn, i // 2, i % 2)

        layout.addLayout(wf_grid)
        layout.addStretch()

    def _launch_workflow(self, screen_id: str):
        ctx = self._router.start_workflow(f"workflow_{screen_id}", screen_id)
        parent = self.window()
        if hasattr(parent, 'navigate_to'):
            parent.navigate_to(screen_id)

    def _refresh(self):
        try:
            results = {}
            try:
                s = self._obs.get_snapshot()
                if isinstance(s, dict) and s.get("success"):
                    results = s.get("data", {})
            except Exception:
                pass

            # Clear and rebuild metrics
            self._clear_grid()
            metrics = [
                ("Total Events", str(results.get("total_events", "?")), "primary"),
                ("Health", results.get("integrity_status", "UNKNOWN"), "success" if results.get("integrity_status") == "PASS" else "warning"),
                ("Stream", results.get("stream_health", "UNKNOWN"), "info"),
            ]

            try:
                wf_count = len(self._gov.list_workflows())
                metrics.append(("Pending Approvals", str(wf_count), "warning"))
            except Exception:
                metrics.append(("Pending Approvals", "?", "info"))

            for i, (title, value, severity) in enumerate(metrics):
                card = KPICard(title, value, severity=severity)
                self.metrics_grid.addWidget(card, 0, i)

            self.status_label.setText(f"● Online | {datetime.utcnow().strftime('%H:%M:%S')} UTC")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_CARD_TITLE}px;")
        except Exception as e:
            self.status_label.setText(f"● Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_CARD_TITLE}px;")

    def _clear_grid(self):
        while self.metrics_grid.count():
            item = self.metrics_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    
    def showEvent(self, event):
        super().showEvent(event)
        if event.isVisible() and not self._timer.isActive():
            self._timer.start(30000)
            self._refresh()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def cleanup(self):
        unregister_owner("control_tower_dash")
    def set_api_client(self, client: APIClient):
        self._api = client
        self._gov = GovernanceAPIClient(client)
        self._truth = TruthAPIClient(client)
        self._obs = ObservabilityAPIClient(client)
        self._intel = IntelligenceAPIClient(client)
