"""
Phase 5B.10 — Global Intelligence Context Bar.

Persistent enterprise-level awareness widget displayed
at the top of the application across all screens.

Displays:
- Risk score (color-coded)
- Active anomaly count
- Forecast warning indicator
- System health status
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QFrame,
                                 QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.observability_client import ObservabilityAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XS, TEXT_TABLE, TEXT_BODY, BORDER_RADIUS_SM)
from runtime.timer_registry import register_timer, unregister_owner


class _IntelBadge(QFrame):
    def __init__(self, label: str, value: str, color: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {color};
            border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_XS}px {SPACING_SM}px; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_TABLE}px;")
        layout.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: {TEXT_BODY}px; font-weight: bold;")
        layout.addWidget(val)


class GlobalIntelligenceBar(QFrame):
    """Persistent intelligence awareness bar at top of application."""

    anomaly_clicked = Signal()
    cognitive_dashboard_clicked = Signal()

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._auto = AutonomousAPIClient(self._api)
        self._obs = ObservabilityAPIClient(self._api)

        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QFrame {{ background-color: {COLOR_BG_ELEVATED};
            border-bottom: 1px solid {COLOR_BORDER}; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, 2, SPACING_MD, 2)
        layout.setSpacing(SPACING_MD)

        # Label
        title = QLabel("🧠 Cognitive Status:")
        title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}px; font-weight: bold;")
        title.setCursor(Qt.PointingHandCursor)
        title.mousePressEvent = lambda e: self.cognitive_dashboard_clicked.emit()
        layout.addWidget(title)

        # Badges (created on refresh)
        self._badges: list = []
        self._badge_container = QHBoxLayout()
        self._badge_container.setSpacing(SPACING_SM)
        layout.addLayout(self._badge_container)

        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60000)
        register_timer("global_intel_bar", self._timer)
        QTimer.singleShot(2000, self._refresh)

    def _refresh(self):
        try:
            risk = 0
            anomaly_count = 0
            health = "UNKNOWN"

            try:
                risk_resp = self._auto.get_risk_summary()
                rd = risk_resp.get("data", risk_resp) if isinstance(risk_resp, dict) else {}
                risk = rd.get("overall_risk", 0)
            except Exception:
                pass

            try:
                warn_resp = self._auto.get_anomaly_warnings()
                wd = warn_resp.get("data", warn_resp) if isinstance(warn_resp, dict) else {}
                anomaly_count = len(wd.get("warnings", []))
            except Exception:
                pass

            try:
                snap = self._obs.get_snapshot()
                sd = snap.get("data", snap) if isinstance(snap, dict) else {}
                health = sd.get("integrity_status", "UNKNOWN")
            except Exception:
                pass

            # Rebuild badges
            self._clear_badges()

            risk_color = COLOR_SUCCESS if risk < 30 else (
                COLOR_WARNING if risk < 60 else COLOR_DANGER
            )
            health_color = COLOR_SUCCESS if health == "PASS" else (
                COLOR_WARNING if health == "DEGRADED" else COLOR_DANGER
            )
            anomaly_color = COLOR_DANGER if anomaly_count > 0 else COLOR_SUCCESS

            badges = [
                _IntelBadge("Risk", f"{risk:.0f}/100", risk_color),
                _IntelBadge("Anomalies", str(anomaly_count), anomaly_color),
                _IntelBadge("Health", health, health_color),
            ]

            for badge in badges:
                self._badge_container.addWidget(badge)
                self._badges.append(badge)

        except Exception:
            pass

    def _clear_badges(self):
        for b in self._badges:
            self._badge_container.removeWidget(b)
            b.deleteLater()
        self._badges.clear()

    
    def cleanup(self):
        unregister_owner("global_intel_bar")
    def set_api_client(self, client: APIClient):
        self._api = client
        self._auto = AutonomousAPIClient(client)
        self._obs = ObservabilityAPIClient(client)
