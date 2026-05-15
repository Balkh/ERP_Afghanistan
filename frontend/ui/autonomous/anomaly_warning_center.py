"""
Phase 5B.9 — Anomaly Warning Center.

Exposes early warning intelligence signals:
- Inventory depletion alerts
- Financial reversal warnings
- HR attrition risks
- Burst anomaly detection
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTableWidget,
                                 QTableWidgetItem, QHeaderView, QComboBox,
                                 QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, SPACING_6, TEXT_PAGE_TITLE, BORDER_RADIUS_MD)


SEVERITY_COLORS = {
    "INFO": COLOR_INFO,
    "WARNING": COLOR_WARNING,
    "CRITICAL": COLOR_DANGER,
}


class AnomalyWarningCenterScreen(QWidget):
    """Early warning intelligence center."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = AutonomousAPIClient(api_client or APIClient())
        self._router = get_router()
        self._build_ui()
        QTimer.singleShot(200, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Anomaly Warning Center")
        title_font = QFont("Segoe UI", TEXT_PAGE_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "inventory", "accounting", "hr", "sales_purchase"])
        self.filter_combo.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE}; padding: {SPACING_6}px;")
        self.filter_combo.currentTextChanged.connect(self._refresh)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.filter_combo)

        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        self.refresh_btn.clicked.connect(self._refresh)
        header.addWidget(self.refresh_btn)


        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Severity", "Domain", "Signal Type", "Description", "Deviation %", "Confidence"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background: {COLOR_BG_MAIN}; color: {COLOR_TEXT_PRIMARY};
            gridline-color: {COLOR_BORDER}; }}
            QHeaderView::section {{ background: {COLOR_BG_SURFACE};
            color: {COLOR_TEXT_PRIMARY}; padding: {SPACING_6}px; font-weight: bold; }}
        """)
        self.table.itemDoubleClicked.connect(self._on_warning_clicked)
        layout.addWidget(self.table)

    def _refresh(self):
        try:
            resp = self._api.get_anomaly_warnings()
            data = resp.get("data", {}) if isinstance(resp, dict) else {}
            warnings = data.get("warnings", [])

            domain_filter = self.filter_combo.currentText()
            if domain_filter != "All":
                warnings = [w for w in warnings if w.get("domain") == domain_filter]

            self.table.setRowCount(len(warnings))
            for i, w in enumerate(warnings):
                sev = w.get("severity", "INFO")
                sev_item = QTableWidgetItem(sev)
                sev_item.setForeground(SEVERITY_COLORS.get(sev, COLOR_TEXT_PRIMARY))
                self.table.setItem(i, 0, sev_item)
                self.table.setItem(i, 1, QTableWidgetItem(w.get("domain", "")))
                self.table.setItem(i, 2, QTableWidgetItem(w.get("signal_type", "")))
                self.table.setItem(i, 3, QTableWidgetItem(w.get("description", "")[:80]))
                self.table.setItem(i, 4, QTableWidgetItem(f"{w.get('deviation_pct', 0):.1f}%"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{w.get('confidence_score', 0):.0%}"))

        except Exception as e:
            self.table.setRowCount(0)

    def _on_warning_clicked(self, item):
        row = item.row()
        domain = self.table.item(row, 1).text() if self.table.item(row, 1) else "inventory"
        ctx = self._router.get_context()
        ctx.selected_domain = domain
        parent = self.window()
        if hasattr(parent, 'navigate_to'):
            parent.navigate_to("anomaly_investigation")

    def set_api_client(self, client: APIClient):
        self._api = AutonomousAPIClient(client)
