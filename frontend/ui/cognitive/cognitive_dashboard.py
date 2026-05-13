"""
Phase 5B.10 — Enterprise Cognitive Dashboard.

Single unified "brain view" aggregating all intelligence sources
into one cognitive experience. Read-only, API-driven, deterministic.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QGridLayout, QTextEdit,
                                 QScrollArea, QTableWidget, QTableWidgetItem,
                                 QHeaderView, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from ui.cognitive.fusion_engine import CognitiveFusionEngine
from ui.cognitive.global_bar import GlobalIntelligenceBar
from ui.control_tower.workflow_engine import get_router
from runtime.timer_registry import register_timer, unregister_owner
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)


class _SectionCard(QFrame):
    """A cognitive section in the dashboard grid."""
    def __init__(self, title: str, color: str = COLOR_BORDER):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {color};
            border-radius: 8px; padding: 12px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_SM)

        header = QLabel(title)
        header.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        self.content = QVBoxLayout()
        self.content.setSpacing(4)
        layout.addLayout(self.content)
        layout.addStretch()

    def add_row(self, label: str, value: str, value_color: str = COLOR_TEXT_PRIMARY):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        row.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet(f"color: {value_color}; font-size: 11px; font-weight: bold;")
        row.addWidget(val)
        row.addStretch()
        self.content.addLayout(row)

    def clear(self):
        while self.content.count():
            item = self.content.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()


class _ClickableCard(QFrame):
    """A card that supports click-to-navigate."""
    clicked = None

    def __init__(self, title: str, value: str, color: str, navigate_to: str = ""):
        super().__init__()
        self.navigate_to = navigate_to
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {color};
            border-radius: 8px; padding: 12px; }}
            QFrame:hover {{ border: 2px solid {color}; }}
        """)
        if navigate_to:
            self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(t)

        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(v)

    def mousePressEvent(self, e):
        if self.navigate_to:
            parent = self.window()
            if hasattr(parent, 'navigate_to'):
                parent.navigate_to(self.navigate_to)
        super().mousePressEvent(e)


class EnterpriseCognitiveDashboard(QWidget):
    """Primary unified brain view of the entire enterprise system."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api_client = api_client or APIClient()
        self._fusion = CognitiveFusionEngine(self._api_client)
        self._router = get_router()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(45000)
        register_timer("cognitive_dashboard", self._timer)
        QTimer.singleShot(500, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Header
        header = QHBoxLayout()
        title = QLabel("Enterprise Cognitive Dashboard")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.status_label = QLabel("● Initializing...")
        self.status_label.setStyleSheet(f"color: {COLOR_INFO}; font-size: 12px;")
        header.addWidget(self.status_label, alignment=Qt.AlignRight)

        refresh_btn = QPushButton("⟳ Refresh All")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # KPI row (clickable)
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(SPACING_MD)
        self._kpi_cards = []
        kpi_layout.addWidget(self._make_kpi("Risk Score", "—", COLOR_DANGER, "master_dashboard"), 0, 0)
        kpi_layout.addWidget(self._make_kpi("Anomalies", "—", COLOR_WARNING, "anomaly_warning_center"), 0, 1)
        kpi_layout.addWidget(self._make_kpi("Forecasts", "—", COLOR_INFO, "forecast_dashboard"), 0, 2)
        kpi_layout.addWidget(self._make_kpi("Decisions", "—", COLOR_PRIMARY, "decision_options"), 0, 3)
        layout.addLayout(kpi_layout)

        # Content grid (2x3 cognitive sections)
        content_grid = QGridLayout()
        content_grid.setSpacing(SPACING_MD)

        self.health_card = _SectionCard("System Health", COLOR_SUCCESS)
        content_grid.addWidget(self.health_card, 0, 0)

        self.risk_card = _SectionCard("Risk Overview", COLOR_DANGER)
        content_grid.addWidget(self.risk_card, 0, 1)

        self.forecast_card = _SectionCard("Forecast Summary", COLOR_INFO)
        content_grid.addWidget(self.forecast_card, 1, 0)

        self.anomaly_card = _SectionCard("Active Anomalies", COLOR_WARNING)
        content_grid.addWidget(self.anomaly_card, 1, 1)

        self.decision_card = _SectionCard("Decision Suggestions", COLOR_PRIMARY)
        content_grid.addWidget(self.decision_card, 2, 0)

        self.domain_card = _SectionCard("Domain Distribution", COLOR_BORDER)
        content_grid.addWidget(self.domain_card, 2, 1)

        layout.addLayout(content_grid)

        # Timestamp
        self.ts_label = QLabel("")
        self.ts_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(self.ts_label)

    def _make_kpi(self, title: str, value: str, color: str, nav: str) -> _ClickableCard:
        card = _ClickableCard(title, value, color, nav)
        self._kpi_cards.append(card)
        return card

    def _refresh(self):
        try:
            state = self._fusion.fuse()

            # Update KPIs
            risk_color = COLOR_SUCCESS if state.risk_score < 30 else (
                COLOR_WARNING if state.risk_score < 60 else COLOR_DANGER
            )
            self._kpi_cards[0].layout().itemAt(1).widget().setText(f"{state.risk_score:.0f}/100")
            self._kpi_cards[0].layout().itemAt(1).widget().setStyleSheet(
                f"color: {risk_color}; font-size: 22px; font-weight: bold;"
            )
            self._kpi_cards[1].layout().itemAt(1).widget().setText(str(state.anomaly_count))
            self._kpi_cards[1].layout().itemAt(1).widget().setStyleSheet(
                f"color: {COLOR_DANGER if state.anomaly_count > 0 else COLOR_SUCCESS}; font-size: 22px; font-weight: bold;"
            )
            self._kpi_cards[2].layout().itemAt(1).widget().setText(str(state.forecast_count))
            self._kpi_cards[3].layout().itemAt(1).widget().setText(str(state.decision_count))

            # Health card
            self.health_card.clear()
            health_color = COLOR_SUCCESS if state.system_health == "PASS" else (
                COLOR_WARNING if state.system_health == "DEGRADED" else COLOR_DANGER
            )
            self.health_card.add_row("Integrity", state.system_health, health_color)
            self.health_card.add_row("Stream", state.stream_health, COLOR_INFO)
            self.health_card.add_row("Total Events", str(state.total_events), COLOR_PRIMARY)

            # Risk card
            self.risk_card.clear()
            self.risk_card.add_row("Score", f"{state.risk_score:.1f}/100", risk_color)
            self.risk_card.add_row("Trend", state.risk_trend,
                                    COLOR_SUCCESS if state.risk_trend == "STABLE" else COLOR_WARNING)
            self.risk_card.add_row("Confidence", f"{state.confidence:.0%}", COLOR_INFO)

            # Forecast card
            self.forecast_card.clear()
            for fc in state.forecast_summaries:
                d = fc.get("direction", "")
                fc_color = COLOR_SUCCESS if d in ("STABLE", "DECREASING") else (
                    COLOR_WARNING if d == "INCREASING" else COLOR_INFO
                )
                self.forecast_card.add_row(
                    f"{fc.get('domain', '')}",
                    f"{fc.get('direction', '')} ({fc.get('value', 0):.1f})",
                    fc_color,
                )

            # Anomaly card
            self.anomaly_card.clear()
            for a in state.top_anomalies:
                sev = a.get("severity", "INFO")
                sev_color = COLOR_DANGER if sev == "CRITICAL" else (
                    COLOR_WARNING if sev == "WARNING" else COLOR_INFO
                )
                self.anomaly_card.add_row(
                    f"[{sev}] {a.get('signal_type', '')}",
                    a.get("description", "")[:50],
                    sev_color,
                )

            # Decision card
            self.decision_card.clear()
            for d in state.decision_summaries:
                self.decision_card.add_row(
                    d.get("type", "").replace("_", " ").title(),
                    f"{d.get('options', 0)} options available",
                    COLOR_PRIMARY,
                )

            # Domain card
            self.domain_card.clear()
            for domain, count in state.domain_event_counts.items():
                self.domain_card.add_row(domain, str(count), COLOR_TEXT_SECONDARY)

            self.ts_label.setText(f"Last refreshed: {state.generated_at[:19]} UTC")
            self.status_label.setText("● Online")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 12px;")

        except Exception as e:
            self.status_label.setText(f"● Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 12px;")

    def showEvent(self, event):
        super().showEvent(event)
        if event.isVisible() and not self._timer.isActive():
            self._timer.start(45000)
            self._refresh()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self._fusion = CognitiveFusionEngine(client)
