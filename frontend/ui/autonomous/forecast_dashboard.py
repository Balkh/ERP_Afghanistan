"""
Phase 5B.9 — Forecast Intelligence Dashboard.

Visualizes autonomous forecasting outputs for:
- Cashflow forecast
- Inventory depletion forecast
- HR workload forecast
- Sales/Purchase imbalance forecast
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTableWidget,
                                 QTableWidgetItem, QHeaderView, QComboBox,
                                 QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, SPACING_6, TEXT_PAGE_TITLE, TEXT_BODY_SMALL, TEXT_BODY, TEXT_CARD_TITLE, TEXT_DISPLAY, BORDER_RADIUS_MD, BORDER_RADIUS_LG)


class _ForecastCard(QFrame):
    def __init__(self, domain: str, metric: str, current: float, predicted: float,
                 direction: str, low: float, high: float):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_LG}; padding: {SPACING_MD}px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_SM)

        title = QLabel(f"{domain.upper()} — {metric.replace('_', ' ').title()}")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_DISPLAY}px; font-weight: bold;")
        layout.addWidget(title)

        color = COLOR_SUCCESS if direction in ("STABLE", "DECREASING") else (
            COLOR_WARNING if direction == "INCREASING" else COLOR_DANGER
        )

        arrow = {"INCREASING": "↑", "DECREASING": "↓", "STABLE": "→", "CYCLICAL": "↻"}

        val_row = QHBoxLayout()
        curr = QLabel(f"Current: {current:.2f}")
        curr.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_CARD_TITLE}px;")
        val_row.addWidget(curr)

        pred = QLabel(f"Predicted: {predicted:.2f}")
        pred.setStyleSheet(f"color: {color}; font-size: {TEXT_CARD_TITLE}px; font-weight: bold;")
        val_row.addWidget(pred)

        dr = QLabel(f"{arrow.get(direction, '?')} {direction}")
        dr.setStyleSheet(f"color: {color}; font-size: {TEXT_CARD_TITLE}px; font-weight: bold;")
        val_row.addWidget(dr)
        val_row.addStretch()
        layout.addLayout(val_row)

        ci = QLabel(f"95% CI: [{low:.2f}, {high:.2f}]")
        ci.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}px;")
        layout.addWidget(ci)


class ForecastDashboard(QWidget):
    """Unified forecast intelligence dashboard."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = AutonomousAPIClient(api_client or APIClient())
        self._build_ui()
        QTimer.singleShot(200, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Forecast Intelligence Dashboard")
        title_font = QFont("Segoe UI", TEXT_PAGE_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        self.refresh_btn.clicked.connect(self._refresh)
        header.addWidget(self.refresh_btn, alignment=Qt.AlignRight)

        layout.addLayout(header)

        self.grid = QGridLayout()
        self.grid.setSpacing(SPACING_MD)
        layout.addLayout(self.grid)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Domain", "Metric", "Current", "Predicted", "Direction", "Confidence"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background: {COLOR_BG_MAIN}; color: {COLOR_TEXT_PRIMARY};
            gridline-color: {COLOR_BORDER}; }}
            QHeaderView::section {{ background: {COLOR_BG_SURFACE};
            color: {COLOR_TEXT_PRIMARY}; padding: {SPACING_6}px; font-weight: bold; }}
        """)
        layout.addWidget(self.table)

    def _refresh(self):
        try:
            resp = self._api.get_forecasts()
            data = resp.get("data", {}) if isinstance(resp, dict) else {}
            forecasts = data.get("forecasts", [])

            # Clear grid
            self._clear_grid()

            for i, f in enumerate(forecasts[:4]):
                card = _ForecastCard(
                    f.get("domain", "?"), f.get("metric", "?"),
                    f.get("current_value", 0), f.get("predicted_value", 0),
                    f.get("direction", "STABLE"),
                    f.get("confidence_interval", [0, 0])[0] if f.get("confidence_interval") else 0,
                    f.get("confidence_interval", [0, 0])[1] if f.get("confidence_interval") else 0,
                )
                self.grid.addWidget(card, i // 2, i % 2)

            # Table
            self.table.setRowCount(len(forecasts))
            for i, f in enumerate(forecasts):
                self.table.setItem(i, 0, QTableWidgetItem(f.get("domain", "")))
                self.table.setItem(i, 1, QTableWidgetItem(f.get("metric", "")))
                self.table.setItem(i, 2, QTableWidgetItem(f"{f.get('current_value', 0):.2f}"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{f.get('predicted_value', 0):.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f.get("direction", "")))
                self.table.setItem(i, 5, QTableWidgetItem(str(f.get("confidence_interval", []))))

        except Exception as e:
            self.table.setRowCount(0)

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_api_client(self, client: APIClient):
        self._api = AutonomousAPIClient(client)
