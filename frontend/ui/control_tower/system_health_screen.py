"""
Phase 5B.7 — System Health Overview Screen.

Real-time health monitoring across all system layers.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QTextEdit, QGridLayout, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.observability_client import ObservabilityAPIClient
from api.intelligence_client import IntelligenceAPIClient
from api.truth_client import TruthAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)
from runtime.timer_registry import register_timer, unregister_owner


class _HealthCard(QFrame):
    def __init__(self, title: str, status: str, detail: str, color: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {color};
            border-radius: 8px; padding: 12px; }}
        """)
        layout = QVBoxLayout(self)
        QLabel(title).setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(QLabel(title))
        s = QLabel(status)
        s.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        layout.addWidget(s)
        d = QLabel(detail)
        d.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(d)


class SystemHealthOverviewScreen(QWidget):
    """System-wide health monitoring dashboard."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._obs = ObservabilityAPIClient(self._api)
        self._intel = IntelligenceAPIClient(self._api)
        self._truth = TruthAPIClient(self._api)
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(15000)
        register_timer("system_health", self._timer)
        QTimer.singleShot(500, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("System Health Overview")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        self.grid = QGridLayout()
        self.grid.setSpacing(SPACING_MD)
        layout.addLayout(self.grid)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 12px;
            font-family: 'Consolas', monospace; }}
        """)
        layout.addWidget(self.detail_text)

    def _refresh(self):
        if getattr(self, '_is_fetching', False):
            return
        self._is_fetching = True
        try:
            results = {}

            try:
                snap = self._obs.get_snapshot()
                if isinstance(snap, dict) and snap.get("success"):
                    results["snapshot"] = snap.get("data", {})
            except Exception:
                pass

            try:
                status = self._obs.get_status()
                if isinstance(status, dict) and status.get("success"):
                    results["status"] = status.get("data", {})
            except Exception:
                pass

            # Clear and rebuild cards
            self._clear_grid()

            s = results.get("snapshot", {})
            cards = [
                _HealthCard("System Integrity", s.get("integrity_status", "UNKNOWN"), "Event Store integrity check", COLOR_SUCCESS if s.get("integrity_status") == "PASS" else COLOR_DANGER),
                _HealthCard("Stream Health", s.get("stream_health", "UNKNOWN"), "Real-time event stream", COLOR_INFO),
                _HealthCard("Total Events", str(s.get("total_events", "?")), "Events in Event Store", COLOR_PRIMARY),
            ]

            st = results.get("status", {})
            if st.get("events_per_second") is not None:
                cards.append(_HealthCard("Event Rate", f"{st['events_per_second']}/s", "Events per second", COLOR_INFO))

            for i, card in enumerate(cards):
                self.grid.addWidget(card, i // 3, i % 3)

            # Show health
            self.detail_text.setPlainText(
                f"Observability Status:\n"
                f"  Version: {st.get('gateway_version', 'N/A')}\n"
                f"  Total Events: {st.get('total_events', 'N/A')}\n"
                f"  Integrity: {s.get('integrity_status', 'N/A')}\n"
                f"  Anomalies: {s.get('anomaly_count', 'N/A') if 'anomaly_count' in s else 'N/A'}\n"
                f"\nDomain Distribution:\n"
                + "\n".join(f"  {k}: {v}" for k, v in s.get("domain_event_counts", {}).items())
            )
        except Exception as e:
            self.detail_text.setPlainText(f"Health refresh error: {e}")
        finally:
            self._is_fetching = False

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    
    def showEvent(self, event):
        super().showEvent(event)
        if event.isVisible() and not self._timer.isActive():
            self._timer.start(15000)
            self._refresh()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def cleanup(self):
        unregister_owner("system_health")

    def set_api_client(self, client: APIClient):
        self._api = client
        self._obs = ObservabilityAPIClient(client)
        self._intel = IntelligenceAPIClient(client)
        self._truth = TruthAPIClient(client)
