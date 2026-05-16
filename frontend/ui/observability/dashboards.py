import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QFrame, QScrollArea, QTableWidget,
                                QTableWidgetItem, QHeaderView, QComboBox,
                                QPushButton, QListWidget, QListWidgetItem,
                                QSplitter, QTextEdit, QSizePolicy, QAbstractItemView,
                                QTabWidget)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QColor

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL,
                          MARGIN_PAGE, PADDING_CARD,
                          COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE,
                          COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                          COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                          COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                          COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BORDER_FOCUS,
                           COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_STATUS_PENDING,
    TABLE_ROW_HEIGHT_MD, TEXT_BODY, TEXT_BODY_SMALL, TEXT_CARD_TITLE, TEXT_HELPER, TEXT_LABEL, TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_TABLE,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG, SPACING_6, BORDER_RADIUS_SM)
from ui.constants import (COLOR_TABLE_HEADER, COLOR_TABLE_ALT, COLOR_TABLE_GRIDLINE,
                          TABLE_ROW_HEIGHT_MD)
from ui.constants import TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, TEXT_TABLE, TEXT_HELPER
from ui.observability.widgets import (StatusIndicator, MetricCard, SeverityBadge,
                                       HealthBar, LoadingOverlay, SectionHeader,
                                       VirtualTimelineWidget, TrendArrow, IncidentCard,
                                       TimelineEventWidget)
from ui.observability.base_view_model import AsyncDataLoader


def _make_styled_table(headers, parent=None):
    table = QTableWidget(parent)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    from ui.components.tables import build_table_stylesheet
    table.setStyleSheet(build_table_stylesheet())
    return table


def _table_item(text, color=None):
    item = QTableWidgetItem(str(text))
    if color:
        item.setForeground(QColor(color))
    return item


def diff_update_table(table, rows, col_count=None):
    scroll_bar = table.verticalScrollBar()
    scroll_pos = scroll_bar.value() if scroll_bar else 0
    sel_row = table.currentRow()
    sel_col = table.currentColumn()

    if col_count is None and rows:
        col_count = max(len(r) for r in rows) if isinstance(rows[0], (list, tuple)) else table.columnCount()
    elif col_count is None:
        col_count = table.columnCount()

    table.setUpdatesEnabled(False)
    old_count = table.rowCount()
    new_count = len(rows)

    if new_count != old_count:
        table.setRowCount(new_count)

    for i, row in enumerate(rows):
        for j in range(col_count):
            val = row[j] if j < len(row) else ""
            if isinstance(val, QTableWidgetItem):
                text = val.text()
                fg = val.foreground()
            else:
                text = str(val)
                fg = None
            item = table.item(i, j)
            if item is None:
                if isinstance(val, QTableWidgetItem):
                    new_item = QTableWidgetItem()
                    new_item.setText(val.text())
                    new_item.setForeground(val.foreground())
                    table.setItem(i, j, new_item)
                else:
                    table.setItem(i, j, QTableWidgetItem(text))
            elif item.text() != text:
                item.setText(text)
                if fg is not None and fg != item.foreground():
                    item.setForeground(fg)

    table.setUpdatesEnabled(True)
    if scroll_bar and scroll_pos > 0:
        scroll_bar.setValue(min(scroll_pos, scroll_bar.maximum()))
    if 0 <= sel_row < new_count:
        table.setCurrentCell(sel_row, max(0, sel_col))


def _severity_to_color(severity):
    s = severity.lower()
    if s in ("critical", "error", "high"):
        return COLOR_DANGER
    if s in ("warning", "medium"):
        return COLOR_WARNING
    if s in ("info", "low"):
        return COLOR_INFO
    return COLOR_TEXT_MUTED


class _BaseDashboard(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api_client = api_client
        self._data_loaders: list = []
        self._stale_data = False
        self._setup_dashboard()

    def _setup_dashboard(self):
        raise NotImplementedError

    def start_auto_refresh(self, interval_ms=5000):
        for loader in self._data_loaders:
            loader.resume()

    def stop_auto_refresh(self):
        for loader in self._data_loaders:
            loader.pause()

    def cleanup(self):
        for loader in self._data_loaders:
            loader.stop()

    def _show_stale_warning(self):
        self._stale_data = True


class ObservabilityMainScreen(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Observability Dashboard")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self.status_indicator = StatusIndicator("System", "unknown")
        header.addWidget(self.status_indicator)

        self.last_update_label = QLabel("Last update: --")
        self.last_update_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.last_update_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        header.addWidget(self.last_update_label)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(SPACING_LG)

        self.health_card = MetricCard("System Health", "Unknown", "Overall health status", COLOR_INFO)
        grid.addWidget(self.health_card, 0, 0)

        self.incident_card = MetricCard("Active Incidents", "--", "Unresolved incidents", COLOR_DANGER)
        grid.addWidget(self.incident_card, 0, 1)

        self.stability_card = MetricCard("Stability Score", "--", "System stability", COLOR_SUCCESS)
        grid.addWidget(self.stability_card, 0, 2)

        health_bar_frame = QFrame()
        health_bar_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        hb_layout = QVBoxLayout(health_bar_frame)
        hb_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        hb_label = QLabel("System Health Score")
        hb_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        hb_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        hb_layout.addWidget(hb_label)
        self.health_bar = HealthBar()
        hb_layout.addWidget(self.health_bar)
        grid.addWidget(health_bar_frame, 1, 0, 1, 2)

        links_frame = QFrame()
        links_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        links_layout = QVBoxLayout(links_frame)
        links_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        links_title = QLabel("Quick Navigation")
        links_title.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        links_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        links_layout.addWidget(links_title)
        nav_items = [
            ("Control Center", "control_center"),
            ("Timeline", "timeline"),
            ("Incidents", "incidents"),
            ("Drift", "drift"),
            ("Replay", "replay"),
            ("Telemetry", "telemetry"),
        ]
        for name, _ in nav_items:
            lbl = QLabel(f"  {name}")
            lbl.setFont(QFont("Segoe UI", TEXT_LABEL))
            lbl.setStyleSheet(f"color: {COLOR_INFO}; border: none; padding: {SPACING_XS}px 0px;")
            links_layout.addWidget(lbl)
        grid.addWidget(links_frame, 1, 2)
        layout.addLayout(grid)

        layout.addStretch()

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/summary/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        self.last_update_label.setText(f"Last update: {time.strftime('%H:%M:%S')}")
        if not isinstance(data, dict):
            return
        d = data.get("data", data)
        if not isinstance(d, dict):
            return
        health = d.get("health", {})
        self.health_card.update_value(
            health.get("status", "Unknown"),
            health.get("detail", "Overall health status"),
            _severity_to_color(health.get("status", "unknown"))
        )
        incidents = d.get("incidents", {})
        count = incidents.get("active_count", 0)
        self.incident_card.update_value(count, f"Active incidents")
        stability = d.get("stability", {})
        score = stability.get("score", 0)
        self.stability_card.update_value(f"{score}%", "System stability")
        self.health_bar.set_value(score if isinstance(score, (int, float)) else 0)

    def _on_error(self, error_msg):
        self.last_update_label.setText("Error loading data")
        self._show_stale_warning()


class ControlCenterDashboard(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Control Center")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self.status_indicator = StatusIndicator("System", "unknown")
        header.addWidget(self.status_indicator)

        self.last_update = QLabel("--")
        self.last_update.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.last_update.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        header.addWidget(self.last_update)
        layout.addLayout(header)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(SPACING_MD)

        self.health_kpi = MetricCard("Health Score", "--", "System health", COLOR_STATUS_VALID)
        kpi_grid.addWidget(self.health_kpi, 0, 0)

        self.stability_kpi = MetricCard("Stability", "--", "System stability", COLOR_INFO)
        kpi_grid.addWidget(self.stability_kpi, 0, 1)

        self.incident_kpi = MetricCard("Active Incidents", "--", "Active", COLOR_DANGER)
        kpi_grid.addWidget(self.incident_kpi, 0, 2)

        self.signal_kpi = MetricCard("Active Signals", "--", "Intelligence signals", COLOR_WARNING)
        kpi_grid.addWidget(self.signal_kpi, 0, 3)
        layout.addLayout(kpi_grid)

        data_frame = QFrame()
        data_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        data_layout = QVBoxLayout(data_frame)
        data_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        data_header = SectionHeader("Dashboard Snapshot")
        data_layout.addWidget(data_header)

        self.data_table = _make_styled_table(["Metric", "Value", "Status"])
        data_layout.addWidget(self.data_table)
        layout.addWidget(data_frame, 1)

        loader = AsyncDataLoader(self._api_client, "/api/control-center/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        self.last_update.setText(f"Updated: {time.strftime('%H:%M:%S')}")
        d = data.get("data", data)
        health = d.get("health", {})
        self.health_kpi.update_value(health.get("status", "--"))
        intel = d.get("intelligence", {})
        signals = d.get("signals", {})
        sig_count = 0
        if signals.get("status") == "ok":
            sig_count = len(signals.get("data", []))
        self.signal_kpi.update_value(sig_count)

        rows = [
            (_table_item("API Status"), _table_item(health.get("status", "N/A")),
             _table_item("OK" if health.get("status") == "ok" else "ERROR", COLOR_STATUS_VALID if health.get("status") == "ok" else COLOR_STATUS_WARNING)),
            (_table_item("DB Health"), _table_item(health.get("database", {}).get("status", "N/A")),
             _table_item("OK", COLOR_STATUS_VALID)),
            (_table_item("Active Signals"), _table_item(str(sig_count)),
             _table_item("OK", COLOR_STATUS_VALID)),
            (_table_item("Anomalies"), _table_item(str(len(intel.get("data", {}).get("anomalies", [])))),
             _table_item("WARNING", COLOR_STATUS_WARNING)),
        ]
        diff_update_table(self.data_table, rows, col_count=3)

    def _on_error(self, error_msg):
        self.last_update.setText("Connection error")


class UnifiedTimelineView(_BaseDashboard):
    PAGE_SIZE = 50

    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QHBoxLayout()
        title = QLabel("Unified Timeline")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Severity:"))
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Critical", "Warning", "Info", "Low"])
        self.severity_filter.currentTextChanged.connect(self._apply_filters)
        header.addWidget(self.severity_filter)

        header.addWidget(QLabel("Phase:"))
        self.phase_filter = QComboBox()
        self.phase_filter.addItems(["All", "System", "Inventory", "Sales", "Accounting", "HR"])
        self.phase_filter.currentTextChanged.connect(self._apply_filters)
        header.addWidget(self.phase_filter)

        header.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Event", "Alert", "Anomaly", "Signal", "Incident"])
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        header.addWidget(self.type_filter)
        layout.addLayout(header)

        self.timeline = VirtualTimelineWidget()
        layout.addWidget(self.timeline, 1)

        pagination = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self._prev_page)
        pagination.addWidget(self.prev_btn)
        pagination.addStretch()
        self.page_label = QLabel("Page 1")
        self.page_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.page_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        pagination.addWidget(self.page_label)
        pagination.addStretch()
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        pagination.addWidget(self.next_btn)
        layout.addLayout(pagination)

        self._page = 1
        self._all_events = []

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/timeline/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        d = data.get("data", data)
        events = d if isinstance(d, list) else d.get("events", d.get("results", []))
        self._all_events = events[:500]
        self._render_page()

    def _render_page(self):
        filtered = self._filter_events(self._all_events)
        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page = filtered[start:end]
        self.timeline.set_events(page)
        total = len(filtered)
        self.page_label.setText(f"Page {self._page} ({start + 1}-{min(end, total)} of {total})")
        self.prev_btn.setEnabled(self._page > 1)
        self.next_btn.setEnabled(end < total)

    def _filter_events(self, events):
        result = events
        sev = self.severity_filter.currentText().lower()
        if sev != "all":
            result = [e for e in result if e.get("severity", "").lower() == sev]
        phase = self.phase_filter.currentText().lower()
        if phase != "all":
            result = [e for e in result if e.get("phase", "").lower() == phase]
        etype = self.type_filter.currentText().lower()
        if etype != "all":
            result = [e for e in result if e.get("type", "").lower() == etype]
        return result

    def _apply_filters(self):
        self._page = 1
        self._render_page()

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        self._page += 1
        self._render_page()

    def _on_error(self, error_msg):
        pass


class IncidentIntelligenceView(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QHBoxLayout()
        title = QLabel("Incident Intelligence")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("Severity:"))
        self.severity_cb = QComboBox()
        self.severity_cb.addItems(["All", "Critical", "High", "Medium", "Low", "Info"])
        self.severity_cb.currentTextChanged.connect(self._apply_filters)
        header.addWidget(self.severity_cb)

        header.addWidget(QLabel("Status:"))
        self.status_cb = QComboBox()
        self.status_cb.addItems(["All", "Open", "In Progress", "Resolved", "Closed"])
        self.status_cb.currentTextChanged.connect(self._apply_filters)
        header.addWidget(self.status_cb)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        self.incident_table = _make_styled_table(
            ["ID", "Severity", "Status", "Escalation", "Tick", "Description"]
        )
        self.incident_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.incident_table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.incident_table)

        detail_panel = QFrame()
        detail_panel.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_MD}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        detail_layout = QVBoxLayout(detail_panel)
        self.detail_label = QLabel("Select an incident to view details")
        self.detail_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.detail_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        self.detail_label.setWordWrap(True)
        detail_layout.addWidget(self.detail_label)
        detail_layout.addStretch()
        splitter.addWidget(detail_panel)
        splitter.setSizes([600, 300])

        layout.addWidget(splitter, 1)

        self._all_incidents = []

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/incidents/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        d = data.get("data", data)
        incidents = d if isinstance(d, list) else d.get("incidents", d.get("results", []))
        self._all_incidents = incidents[:500]
        self._populate_table(self._all_incidents)

    def _populate_table(self, incidents):
        self.incident_table.setRowCount(len(incidents))
        for i, inc in enumerate(incidents):
            sev = inc.get("severity", "info")
            self.incident_table.setItem(i, 0, QTableWidgetItem(str(inc.get("id", ""))))
            sev_item = QTableWidgetItem(sev.upper())
            sev_item.setForeground(QColor(_severity_to_color(sev)))
            self.incident_table.setItem(i, 1, sev_item)
            self.incident_table.setItem(i, 2, QTableWidgetItem(inc.get("status", "")))
            self.incident_table.setItem(i, 3, QTableWidgetItem(f"L{inc.get('escalation', 0)}"))
            self.incident_table.setItem(i, 4, QTableWidgetItem(str(inc.get("tick", ""))))
            self.incident_table.setItem(i, 5, QTableWidgetItem(inc.get("description", "")))

    def _apply_filters(self):
        filtered = self._all_incidents
        sev = self.severity_cb.currentText().lower()
        if sev != "all":
            filtered = [i for i in filtered if i.get("severity", "").lower() == sev]
        status = self.status_cb.currentText().lower()
        if status != "all":
            filtered = [i for i in filtered if i.get("status", "").lower() == status]
        self._populate_table(filtered)

    def _on_selection_changed(self):
        rows = self.incident_table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        inc = {}
        for col in range(self.incident_table.columnCount()):
            item = self.incident_table.item(row, col)
            if item:
                inc[self.incident_table.horizontalHeaderItem(col).text()] = item.text()
        self.detail_label.setText(
            f"<b>ID:</b> {inc.get('ID', '')}<br>"
            f"<b>Severity:</b> {inc.get('Severity', '')}<br>"
            f"<b>Status:</b> {inc.get('Status', '')}<br>"
            f"<b>Escalation:</b> {inc.get('Escalation', '')}<br>"
            f"<b>Description:</b> {inc.get('Description', '')}"
        )

    def _on_error(self, error_msg):
        pass


class PredictiveDriftDashboard(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Predictive Drift")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(SPACING_MD)
        self.drift_prob_card = MetricCard("Drift Probability", "--", "Likelihood of system drift", COLOR_WARNING)
        cards.addWidget(self.drift_prob_card)

        self.instability_card = MetricCard("Workflow Instability", "--", "Workflow stability risk", COLOR_DANGER)
        cards.addWidget(self.instability_card)

        self.forecast_card = MetricCard("Forecasted Failures", "--", "Predicted failures (24h)", COLOR_INFO)
        cards.addWidget(self.forecast_card)
        layout.addLayout(cards)

        trend_frame = QFrame()
        trend_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        trend_layout = QVBoxLayout(trend_frame)
        trend_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        trend_layout.addWidget(SectionHeader("Drift Details"))

        self.drift_table = _make_styled_table(["Module", "Drift Score", "Trend", "Status", "Risk"])
        trend_layout.addWidget(self.drift_table)
        layout.addWidget(trend_frame, 1)

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/drift/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        d = data.get("data", data)
        prediction = d.get("prediction", d)
        self.drift_prob_card.update_value(
            f"{prediction.get('drift_probability', 0)}%",
            color=COLOR_WARNING
        )
        self.instability_card.update_value(
            f"{prediction.get('instability', 0)}%",
            color=COLOR_DANGER
        )
        self.forecast_card.update_value(
            prediction.get('forecasted_failures', 0),
            color=COLOR_INFO
        )
        details = prediction.get("details", d.get("details", []))
        self.drift_table.setRowCount(len(details))
        for i, det in enumerate(details):
            score = det.get("score", 0)
            trend = det.get("trend", "stable")
            arrow = "▲" if trend == "up" else ("▼" if trend == "down" else "◆")
            arrow_color = COLOR_DANGER if trend == "up" else (COLOR_SUCCESS if trend == "down" else COLOR_INFO)
            self.drift_table.setItem(i, 0, _table_item(det.get("module", "")))
            self.drift_table.setItem(i, 1, _table_item(f"{score}%"))
            trend_item = _table_item(arrow, arrow_color)
            self.drift_table.setItem(i, 2, trend_item)
            self.drift_table.setItem(i, 3, _table_item(det.get("status", "")))
            risk = det.get("risk", "low")
            self.drift_table.setItem(i, 4, _table_item(risk.upper(), _severity_to_color(risk)))

    def _on_error(self, error_msg):
        pass


class ReplayTimeTravelView(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        header = QHBoxLayout()
        title = QLabel("Replay / Time Travel")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()
        readonly_tag = QLabel("VIEW ONLY")
        readonly_tag.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_MUTED}; padding: {SPACING_XS}px {SPACING_SM}px; border-radius: {BORDER_RADIUS_SM}; font-size: {TEXT_TABLE}px; font-weight: bold;")
        header.addWidget(readonly_tag)

        self.last_update = QLabel("")
        self.last_update.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.last_update.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        header.addWidget(self.last_update)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        left_layout.addWidget(SectionHeader("Replay Sessions"))

        self.session_list = QListWidget()
        self.session_list.setStyleSheet(f"background-color: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; color: {COLOR_TEXT_PRIMARY};")
        self.session_list.itemClicked.connect(self._on_session_selected)
        left_layout.addWidget(self.session_list)

        bookmarks_title = QLabel("Bookmarks")
        bookmarks_title.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        bookmarks_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none; padding-top: 8px;")
        left_layout.addWidget(bookmarks_title)

        self.bookmark_list = QListWidget()
        self.bookmark_list.setStyleSheet(f"background-color: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; color: {COLOR_TEXT_PRIMARY};")
        left_layout.addWidget(self.bookmark_list)
        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}px; border: 1px solid {COLOR_BORDER_LIGHT};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        right_layout.addWidget(SectionHeader("Session Detail"))

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet(f"background-color: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; color: {COLOR_TEXT_PRIMARY};")
        right_layout.addWidget(self.detail_text, 1)

        cursor_frame = QFrame()
        cursor_frame.setStyleSheet(f"background-color: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_MD}px; border: none;")
        cursor_layout = QHBoxLayout(cursor_frame)
        cursor_layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        cursor_layout.addWidget(QLabel("Timeline Cursor:"))
        self.cursor_label = QLabel("--:--:--")
        self.cursor_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        self.cursor_label.setStyleSheet(f"color: {COLOR_PRIMARY}; border: none;")
        cursor_layout.addWidget(self.cursor_label)
        cursor_layout.addStretch()
        right_layout.addWidget(cursor_frame)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/replay/sessions/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        self.last_update.setText(f"Updated: {time.strftime('%H:%M:%S')}")
        d = data.get("data", data)
        sessions = d if isinstance(d, list) else d.get("sessions", d.get("results", []))
        self.session_list.clear()
        for s in sessions[:100]:
            item = QListWidgetItem(f"Session {s.get('id', '')} ({s.get('timestamp', '')})")
            item.setData(Qt.UserRole, s)
            self.session_list.addItem(item)

        bookmarks = d.get("bookmarks", [])
        self.bookmark_list.clear()
        for b in bookmarks[:50]:
            self.bookmark_list.addItem(f"{b.get('label', 'BM')} @ {b.get('position', '')}")

    def _on_session_selected(self, item):
        s = item.data(Qt.UserRole)
        if s:
            self.detail_text.setPlainText(
                f"Session ID: {s.get('id', '')}\n"
                f"Timestamp: {s.get('timestamp', '')}\n"
                f"State: {s.get('state', '')}\n"
                f"Duration: {s.get('duration', '')}\n"
                f"Events: {s.get('event_count', 0)}\n"
                f"Description: {s.get('description', '')}"
            )
            self.cursor_label.setText(s.get("cursor_position", "--:--:--"))

    def _on_error(self, error_msg):
        self.last_update.setText("Connection error")


class DigitalTwinTelemetryView(_BaseDashboard):
    def _setup_dashboard(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Digital Twin Telemetry")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self.last_update = QLabel("")
        self.last_update.setFont(QFont("Segoe UI", TEXT_TABLE))
        self.last_update.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        header.addWidget(self.last_update)
        layout.addLayout(header)

        summary_grid = QGridLayout()
        summary_grid.setSpacing(SPACING_MD)
        self.scenario_card = MetricCard("Scenarios", "--", "Total scenarios executed", COLOR_INFO)
        summary_grid.addWidget(self.scenario_card, 0, 0)

        self.pass_rate_card = MetricCard("Pass Rate", "--", "Scenario pass rate", COLOR_SUCCESS)
        summary_grid.addWidget(self.pass_rate_card, 0, 1)

        self.integrity_card = MetricCard("Integrity", "--", "Data integrity score", COLOR_PRIMARY)
        summary_grid.addWidget(self.integrity_card, 0, 2)
        layout.addLayout(summary_grid)

        tab = QTabWidget()
        tab.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
            }}
            QTabBar::tab {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_SECONDARY};
                padding: {SPACING_6}px 16px;
                border: none;
                font-size: {TEXT_LABEL}px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_PRIMARY};
                font-weight: bold;
            }}
        """)

        scenarios_tab = QWidget()
        scenarios_layout = QVBoxLayout(scenarios_tab)
        scenarios_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.scenario_table = _make_styled_table(["Scenario", "Status", "Duration", "Errors"])
        scenarios_layout.addWidget(self.scenario_table)
        tab.addTab(scenarios_tab, "Scenarios")

        integrity_tab = QWidget()
        integrity_layout = QVBoxLayout(integrity_tab)
        integrity_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.integrity_table = _make_styled_table(["Check", "Status", "Detail"])
        integrity_layout.addWidget(self.integrity_table)
        tab.addTab(integrity_tab, "Integrity Checks")

        sla_tab = QWidget()
        sla_layout = QVBoxLayout(sla_tab)
        sla_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.sla_table = _make_styled_table(["SLA", "Compliance", "Violations", "Trend"])
        sla_layout.addWidget(self.sla_table)
        tab.addTab(sla_tab, "SLA Violations")

        layout.addWidget(tab, 1)

        loader = AsyncDataLoader(self._api_client, "/api/observability/v1/telemetry/", 15000, self)
        loader.data_loaded.connect(self._on_data)
        loader.load_error.connect(self._on_error)
        self._data_loaders.append(loader)
        loader.start()

    def _on_data(self, data):
        self.last_update.setText(f"Updated: {time.strftime('%H:%M:%S')}")
        d = data.get("data", data)
        summary = d.get("summary", d)

        self.scenario_card.update_value(summary.get("total_scenarios", 0))
        pass_rate = summary.get("pass_rate", 0)
        self.pass_rate_card.update_value(f"{pass_rate}%", color=COLOR_SUCCESS if pass_rate >= 80 else COLOR_WARNING)
        integrity = summary.get("integrity_score", 0)
        self.integrity_card.update_value(f"{integrity}%", color=COLOR_INFO)

        scenarios = d.get("scenarios", summary.get("scenarios", []))
        self.scenario_table.setRowCount(len(scenarios))
        for i, s in enumerate(scenarios):
            self.scenario_table.setItem(i, 0, _table_item(s.get("name", "")))
            status = s.get("status", "")
            c = COLOR_SUCCESS if status == "passed" else COLOR_DANGER
            self.scenario_table.setItem(i, 1, _table_item(status.upper(), c))
            self.scenario_table.setItem(i, 2, _table_item(s.get("duration", "")))
            self.scenario_table.setItem(i, 3, _table_item(s.get("errors", 0)))

        checks = d.get("integrity_checks", summary.get("integrity_checks", []))
        self.integrity_table.setRowCount(len(checks))
        for i, c in enumerate(checks):
            self.integrity_table.setItem(i, 0, _table_item(c.get("check", "")))
            st = c.get("status", "")
            sc = COLOR_SUCCESS if st == "passed" else COLOR_DANGER
            self.integrity_table.setItem(i, 1, _table_item(st.upper(), sc))
            self.integrity_table.setItem(i, 2, _table_item(c.get("detail", "")))

        slas = d.get("sla_violations", summary.get("sla_violations", []))
        self.sla_table.setRowCount(len(slas))
        for i, sla in enumerate(slas):
            self.sla_table.setItem(i, 0, _table_item(sla.get("name", "")))
            comp = sla.get("compliance", 0)
            self.sla_table.setItem(i, 1, _table_item(f"{comp}%"))
            self.sla_table.setItem(i, 2, _table_item(sla.get("violations", 0)))
            trend = sla.get("trend", "stable")
            tc = COLOR_SUCCESS if trend == "improving" else (COLOR_DANGER if trend == "degrading" else COLOR_INFO)
            self.sla_table.setItem(i, 3, _table_item(trend.upper(), tc))

    def _on_error(self, error_msg):
        self.last_update.setText("Connection error")
