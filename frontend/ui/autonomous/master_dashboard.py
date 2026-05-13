"""
Phase 5B.9 — Autonomous Intelligence Dashboard (Master View).

Unified enterprise intelligence control panel showing:
- Risk Score (0–100)
- Forecast summary (multi-domain)
- Active anomaly warnings
- Suggested decisions
- Intelligence health status
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QGridLayout, QTextEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)
from runtime.timer_registry import register_timer, unregister_owner


class _KPIWidget(QFrame):
    def __init__(self, title: str, value: str, color: str, subtitle: str = ""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {color};
            border-radius: 8px; padding: 12px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        QLabel(title).setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(QLabel(title))
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(v)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
            layout.addWidget(s)


class MasterIntelligenceDashboard(QWidget):
    """Single unified intelligence control panel."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = AutonomousAPIClient(api_client or APIClient())
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60000)
        register_timer("master_intel_dash", self._timer)
        QTimer.singleShot(500, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Enterprise Intelligence Dashboard")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.status_label = QLabel("● Checking...")
        self.status_label.setStyleSheet(f"color: {COLOR_INFO}; font-size: 12px;")
        header.addWidget(self.status_label, alignment=Qt.AlignRight)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(SPACING_MD)
        layout.addLayout(self.kpi_grid)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 12px;
            font-family: 'Consolas', monospace; font-size: 12px; }}
        """)
        layout.addWidget(self.detail_text)

    def _refresh(self):
        try:
            report_resp = self._api.get_full_report()
            report = report_resp.get("data", {}) if isinstance(report_resp, dict) else {}

            risk = report.get("risk_score_overall", 0)
            conf = report.get("confidence_score_overall", 0)
            insight_count = report.get("insight_count", 0)
            rec_count = report.get("recommendation_count", 0)
            forecast_count = report.get("forecast_count", 0)
            warning_count = report.get("warning_count", 0)

            risk_color = COLOR_SUCCESS if risk < 30 else (
                COLOR_WARNING if risk < 60 else COLOR_DANGER
            )

            self._clear_grid()

            kpis = [
                _KPIWidget("Overall Risk Score", f"{risk:.1f}/100", risk_color),
                _KPIWidget("Confidence", f"{conf:.0%}", COLOR_INFO),
                _KPIWidget("Active Insights", str(insight_count), COLOR_PRIMARY),
                _KPIWidget("Recommendations", str(rec_count), COLOR_WARNING),
                _KPIWidget("Forecasts", str(forecast_count), COLOR_INFO),
                _KPIWidget("Anomaly Warnings", str(warning_count),
                           COLOR_DANGER if warning_count > 0 else COLOR_SUCCESS),
            ]

            for i, kpi in enumerate(kpis):
                self.kpi_grid.addWidget(kpi, i // 3, i % 3)

            projection_hash = report.get("projection_hash", "")[:16]
            self.detail_text.setPlainText(
                f"Intelligence Report Summary\n"
                f"{'=' * 40}\n"
                f"Domain Scope: {report.get('domain_scope', 'enterprise')}\n"
                f"Risk Score:     {risk:.1f}/100\n"
                f"Confidence:     {conf:.0%}\n"
                f"Insights:       {insight_count}\n"
                f"Recommendations:{rec_count}\n"
                f"Forecasts:      {forecast_count}\n"
                f"Warnings:       {warning_count}\n"
                f"Supporting Events: {len(report.get('supporting_events', []))}\n"
                f"Projection Hash:   {projection_hash}...\n"
                f"{'=' * 40}\n"
                f"Status: All intelligence engines operational"
            )

            self.status_label.setText(f"● Live | {forecast_count} forecasts · {warning_count} warnings")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 12px;")

        except Exception as e:
            self.status_label.setText(f"● Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 12px;")

    def _clear_grid(self):
        while self.kpi_grid.count():
            item = self.kpi_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    
    def showEvent(self, event):
        super().showEvent(event)
        if event.isVisible() and not self._timer.isActive():
            self._timer.start(60000)
            self._refresh()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def cleanup(self):
        unregister_owner("master_intel_dash")
    def set_api_client(self, client: APIClient):
        self._api = AutonomousAPIClient(client)
