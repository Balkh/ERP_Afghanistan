"""Phase 18 — Financial Control Tower Screen (PySide6).

Unified dashboard for the Financial Operating System.
All data is on-demand (no polling, no background threads).
All UI state is ephemeral (no caching financial truth).

Panels:
1. Global Financial State Panel
2. Risk Matrix View
3. Operational Alerts Panel
4. Decision Queue Panel (read-only)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient


COLORS = {
    'bg_main': '#1a1a2e',
    'bg_surface': '#16213e',
    'bg_elevated': '#0f3460',
    'text_primary': '#e0e0e0',
    'text_secondary': '#a0a0a0',
    'success': '#4caf50',
    'warning': '#ff9800',
    'danger': '#f44336',
    'info': '#2196f3',
    'border': '#2a2a4a',
    'critical': '#d32f2f',
}

SPACING = {'sm': 8, 'md': 12, 'lg': 16, 'xl': 24}


class _Card(QFrame):
    """Reusable card widget."""
    def __init__(self, title='', parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            f'background: {COLORS["bg_surface"]}; border-radius: 8px; '
            f'border: 1px solid {COLORS["border"]};'
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACING['lg'], SPACING['md'], SPACING['lg'], SPACING['md'])
        self._layout.setSpacing(SPACING['sm'])
        if title:
            lbl = QLabel(title)
            f = QFont('Segoe UI', 11, QFont.Weight.Bold)
            lbl.setFont(f)
            lbl.setStyleSheet(f'color: {COLORS["text_primary"]};')
            self._layout.addWidget(lbl)

    def add_widget(self, w):
        self._layout.addWidget(w)


class _MetricRow(QWidget):
    """Single metric display row."""
    def __init__(self, label, value, color=None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet(f'color: {COLORS["text_secondary"]}; font-size: 12px;')
        val = QLabel(str(value))
        f = QFont('Segoe UI', 14, QFont.Weight.Bold)
        val.setFont(f)
        if color:
            val.setStyleSheet(f'color: {color};')
        else:
            val.setStyleSheet(f'color: {COLORS["text_primary"]};')
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(val)


class FinancialControlTowerScreen(QWidget):
    """Phase 18 Financial Control Tower — unified governance dashboard."""

    def __init__(self, api_client=None):
        super().__init__()
        self._api = api_client or APIClient()
        self._data_cache = {}
        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        main.setSpacing(SPACING['lg'])

        # Header
        header_layout = QHBoxLayout()
        title = QLabel('Financial Control Tower')
        f = QFont('Segoe UI', 18, QFont.Weight.Bold)
        title.setFont(f)
        title.setStyleSheet(f'color: {COLORS["text_primary"]};')
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._refresh_btn = QPushButton('Refresh')
        self._refresh_btn.setStyleSheet(
            f'background: {COLORS["info"]}; color: white; padding: 8px 16px; '
            f'border-radius: 4px; font-size: 12px;'
        )
        self._refresh_btn.clicked.connect(self._refresh_all)
        header_layout.addWidget(self._refresh_btn)
        main.addLayout(header_layout)

        # Status bar
        self._status_bar = QLabel('Click Refresh to load data')
        self._status_bar.setStyleSheet(f'color: {COLORS["text_secondary"]}; font-size: 11px;')
        main.addWidget(self._status_bar)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('border: none; background: transparent;')
        content = QWidget()
        content.setStyleSheet('background: transparent;')
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(SPACING['lg'])
        scroll.setWidget(content)
        main.addWidget(scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_all()

    def _refresh_all(self):
        """Fetch all data on-demand (no caching)."""
        self._status_bar.setText('Loading...')
        self._status_bar.setStyleSheet(f'color: {COLORS["info"]}; font-size: 11px;')

        try:
            summary = self._api.get('/api/financial/control-tower/summary/')
            alerts = self._api.get('/api/financial/control-tower/alerts/')
            decisions = self._api.get('/api/financial/control-tower/decisions/')

            self._data_cache = {
                'summary': summary.get('data', summary) if summary else {},
                'alerts': alerts.get('data', alerts) if alerts else {},
                'decisions': decisions.get('data', decisions) if decisions else {},
            }
            self._render()
            self._status_bar.setText(f'Updated: all systems operational')
            self._status_bar.setStyleSheet(f'color: {COLORS["success"]}; font-size: 11px;')
        except Exception as e:
            self._status_bar.setText(f'Error: {str(e)}')
            self._status_bar.setStyleSheet(f'color: {COLORS["danger"]}; font-size: 11px;')

    def _render(self):
        """Render all panels from cached data."""
        # Clear existing widgets
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        summary = self._data_cache.get('summary', {})
        alerts = self._data_cache.get('alerts', {})
        decisions = self._data_cache.get('decisions', {})

        # Row 1: Global Financial State + Risk Matrix
        row1 = QHBoxLayout()
        row1.addWidget(self._build_global_state_panel(summary))
        row1.addWidget(self._build_risk_matrix(summary))
        self._content_layout.addLayout(row1)

        # Row 2: Operational Alerts + Decision Queue
        row2 = QHBoxLayout()
        row2.addWidget(self._build_alerts_panel(alerts))
        row2.addWidget(self._build_decision_queue(decisions))
        self._content_layout.addLayout(row2)

        self._content_layout.addStretch()

    def _build_global_state_panel(self, summary):
        card = _Card('Global Financial State')

        safe_mode = summary.get('safe_mode', False)
        if safe_mode:
            lbl = QLabel('SAFE MODE — SSOT conflict detected')
            lbl.setStyleSheet(f'color: {COLORS["danger"]}; font-weight: bold;')
            card.add_widget(lbl)

        card.add_widget(_MetricRow('Health Score', f'{summary.get("health_score", 0)}/100',
                                   color=COLORS['success'] if summary.get('health_score', 0) >= 70 else COLORS['warning']))
        card.add_widget(_MetricRow('Health Status', summary.get('health_status', 'N/A')))
        card.add_widget(_MetricRow('Anomaly Index', summary.get('anomaly_index', 0),
                                   color=COLORS['warning'] if summary.get('anomaly_index', 0) > 5 else COLORS['success']))
        card.add_widget(_MetricRow('Reconciliation', summary.get('reconciliation_health', 'N/A')))
        card.add_widget(_MetricRow('Net Liquidity', summary.get('cashflow_status', '0.00')))
        card.add_widget(_MetricRow('Cashflow Trend', summary.get('cashflow_trend', 'STABLE')))
        card.add_widget(_MetricRow('Credit Exposure', summary.get('total_credit_exposure', '0.00')))
        card.add_widget(_MetricRow('SSOT Consistency', f'{summary.get("ssot_consistency_pct", 0)}%'))

        return card

    def _build_risk_matrix(self, summary):
        card = _Card('Risk Matrix')
        risk = summary.get('risk_distribution', {})

        levels = [
            ('CRITICAL', risk.get('CRITICAL', 0), COLORS['critical']),
            ('HIGH', risk.get('HIGH', 0), COLORS['danger']),
            ('MEDIUM', risk.get('MEDIUM', 0), COLORS['warning']),
            ('LOW', risk.get('LOW', 0), COLORS['info']),
            ('MINIMAL', risk.get('MINIMAL', 0), COLORS['success']),
        ]
        for level, count, color in levels:
            card.add_widget(_MetricRow(level, str(count), color=color))

        return card

    def _build_alerts_panel(self, alerts):
        card = _Card('Operational Alerts')
        alert_list = alerts.get('active_alerts', [])
        total = alerts.get('total_alerts', 0)

        card.add_widget(_MetricRow('Active Alerts', str(total),
                                   color=COLORS['danger'] if total > 0 else COLORS['success']))

        if alert_list:
            table = QTableWidget(len(alert_list), 4)
            table.setHorizontalHeaderLabels(['Type', 'Entity', 'Risk', 'Rule'])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setAlternatingRowColors(True)
            table.setStyleSheet(
                f'background: {COLORS["bg_main"]}; color: {COLORS["text_primary"]}; '
                f'gridline-color: {COLORS["border"]};'
            )
            for i, a in enumerate(alert_list[:20]):
                table.setItem(i, 0, QTableWidgetItem(a.get('decision_type', '')))
                table.setItem(i, 1, QTableWidgetItem(f'{a.get("entity_type", "")}'))
                table.setItem(i, 2, QTableWidgetItem(str(a.get('risk_score', 0))))
                rules = ', '.join(a.get('triggered_rules', [])[:2])
                table.setItem(i, 3, QTableWidgetItem(rules))
            card.add_widget(table)
        else:
            lbl = QLabel('No active alerts')
            lbl.setStyleSheet(f'color: {COLORS["success"]};')
            card.add_widget(lbl)

        return card

    def _build_decision_queue(self, decisions):
        card = _Card('Decision Queue (Read-Only)')
        decision_list = decisions.get('decisions', [])
        total = decisions.get('total', 0)

        card.add_widget(_MetricRow('Total Decisions', str(total)))

        if decision_list:
            table = QTableWidget(len(decision_list), 5)
            table.setHorizontalHeaderLabels(['Decision', 'Entity', 'State', 'Score', 'Time'])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setAlternatingRowColors(True)
            table.setStyleSheet(
                f'background: {COLORS["bg_main"]}; color: {COLORS["text_primary"]}; '
                f'gridline-color: {COLORS["border"]};'
            )
            for i, d in enumerate(decision_list[:50]):
                table.setItem(i, 0, QTableWidgetItem(d.get('decision_type', '')))
                table.setItem(i, 1, QTableWidgetItem(f'{d.get("entity_type", "")}'))
                table.setItem(i, 2, QTableWidgetItem(d.get('lifecycle_state', '')))
                table.setItem(i, 3, QTableWidgetItem(str(d.get('risk_score', 0))))
                ts = d.get('timestamp', '')[:19] if d.get('timestamp') else ''
                table.setItem(i, 4, QTableWidgetItem(ts))
            card.add_widget(table)
        else:
            lbl = QLabel('No decisions recorded')
            lbl.setStyleSheet(f'color: {COLORS["text_secondary"]};')
            card.add_widget(lbl)

        return card
