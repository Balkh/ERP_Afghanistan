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
                           MARGIN_PAGE)
from runtime.timer_registry import register_timer, unregister_owner


class _MetricCard(QFrame):
    """Single metric card widget."""

    def __init__(self, title: str, value: str, color: str, status: str = ""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background-color: {COLOR_BG_ELEVATED}; border-radius: 8px;
            border: 1px solid {COLOR_BORDER}; padding: 12px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.value_label)

        if status:
            s = QLabel(status)
            s.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
            layout.addWidget(s)


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
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.status_label = QLabel("● Checking...")
        self.status_label.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 12px;")
        header.addWidget(self.status_label, alignment=Qt.AlignRight)

        refresh_btn = QPushButton("⟳ Refresh All")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
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
        workflow_header.setFont(QFont("Segoe UI", 16, QFont.Bold))
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
                border: 1px solid {color}; border-radius: 8px; padding: 16px 20px;
                font-size: 13px; font-weight: bold; text-align: left; }}
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
                ("Total Events", str(results.get("total_events", "?")), COLOR_PRIMARY),
                ("Health", results.get("integrity_status", "UNKNOWN"), COLOR_SUCCESS if results.get("integrity_status") == "PASS" else COLOR_WARNING),
                ("Stream", results.get("stream_health", "UNKNOWN"), COLOR_INFO),
            ]

            try:
                wf_count = len(self._gov.list_workflows())
                metrics.append(("Pending Approvals", str(wf_count), COLOR_WARNING))
            except Exception:
                metrics.append(("Pending Approvals", "?", COLOR_TEXT_MUTED))

            for i, (title, value, color) in enumerate(metrics):
                card = _MetricCard(title, value, color)
                self.metrics_grid.addWidget(card, 0, i)

            self.status_label.setText(f"● Online | {datetime.utcnow().strftime('%H:%M:%S')} UTC")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 12px;")
        except Exception as e:
            self.status_label.setText(f"● Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 12px;")

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
