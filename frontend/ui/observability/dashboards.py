import time
from ui.components.buttons import EnterpriseButton, ButtonVariant
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QFrame,
                                QComboBox,
                                QListWidget, QListWidgetItem, QSplitter,
                                QTextEdit, QAbstractItemView, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, COLOR_PRIMARY,
                          COLOR_SUCCESS, COLOR_WARNING,
                          COLOR_DANGER, COLOR_INFO, COLOR_TEXT_PRIMARY,
                          COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                          COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT,
                          COLOR_STATUS_VALID, COLOR_STATUS_WARNING, TEXT_LABEL, TEXT_PAGE_TITLE,
                          TEXT_TABLE, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
                           SPACING_6, BORDER_RADIUS_SM)
from ui.components.tables import EnterpriseTable, TableColumn
from ui.observability.widgets import (StatusIndicator, MetricCard, HealthBar,
                                       SectionHeader, VirtualTimelineWidget)
from ui.observability.base_view_model import AsyncDataLoader
from ui.screens.base_screen import BaseScreen


def _make_styled_table(headers, parent=None):
    columns = [TableColumn(str(header).lower().replace(" ", "_"), str(header), width=140) for header in headers]
    table = EnterpriseTable(columns, density="compact", parent=parent)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    return table


def _table_item(text, color=None):
    return str(text)


def diff_update_table(table, rows, col_count=None):
    """Update an EnterpriseTable from row tuples while preserving its column keys."""
    columns = getattr(table, "_columns", [])
    if col_count is None:
        col_count = len(columns)
    out = []
    for row in rows:
        data = {}
        for idx in range(col_count):
            key = columns[idx].key if idx < len(columns) else f"col_{idx}"
            data[key] = row[idx] if idx < len(row) else ""
        out.append(data)
    table.set_data(out)

def _severity_to_color(severity):
    s = severity.lower()
    if s in ("critical", "error", "high"):
        return COLOR_DANGER
    if s in ("warning", "medium"):
        return COLOR_WARNING
    if s in ("info", "low"):
        return COLOR_INFO
    return COLOR_TEXT_MUTED


class _BaseDashboard(BaseScreen):
    def __init__(self, api_client, parent=None):
        self._api_client = api_client
        self._data_loaders: list = []
        self._stale_data = False
        super().__init__(parent)
        self._setup_screen()

    def _setup_screen(self):
        super()._setup_screen()
        self._setup_dashboard()

    def _setup_dashboard(self):
        raise NotImplementedError

    def _on_screen_shown(self):
        pass

    def _on_screen_hidden(self):
        """Stop all AsyncDataLoader timers when the screen is hidden.

        Without this, each navigation cycle (open → close → reopen) leaves
        a QTimer running. After 6 cycles the process accumulates 6 orphan
        timers that keep firing against stale closures — the F-30 leak.
        """
        self.cleanup()

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
        self.incident_card.update_value(count, "Active incidents")
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
        self.prev_btn = EnterpriseButton("◀ Prev", variant=ButtonVariant.SECONDARY)
        self.prev_btn.clicked.connect(self._prev_page)
        pagination.addWidget(self.prev_btn)
        pagination.addStretch()
        self.page_label = QLabel("Page 1")
        self.page_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.page_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        pagination.addWidget(self.page_label)
        pagination.addStretch()
        self.next_btn = EnterpriseButton("Next ▶", variant=ButtonVariant.SECONDARY)
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
        rows = []
        for inc in incidents:
            sev = inc.get("severity", "info")
            rows.append({
                **inc,
                "id": str(inc.get("id", "")),
                "severity": sev.upper(),
                "status": inc.get("status", ""),
                "escalation": f"L{inc.get('escalation', 0)}",
                "tick": str(inc.get("tick", "")),
                "description": inc.get("description", ""),
            })
        self.incident_table.set_data(rows)

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
        selected = self.incident_table.get_selected_data()
        if not selected:
            return
        inc = selected[0]
        self.detail_label.setText(
            f"<b>ID:</b> {inc.get('id', '')}<br>"
            f"<b>Severity:</b> {inc.get('severity', '')}<br>"
            f"<b>Status:</b> {inc.get('status', '')}<br>"
            f"<b>Escalation:</b> {inc.get('escalation', '')}<br>"
            f"<b>Description:</b> {inc.get('description', '')}"
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
        rows = []
        for det in details:
            score = det.get("score", 0)
            trend = det.get("trend", "stable")
            arrow = "▲" if trend == "up" else ("▼" if trend == "down" else "◆")
            risk = det.get("risk", "low")
            rows.append({
                "module": det.get("module", ""),
                "drift_score": f"{score}%",
                "trend": arrow,
                "status": det.get("status", ""),
                "risk": risk.upper(),
            })
        self.drift_table.set_data(rows)

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
                padding: {SPACING_6}px {SPACING_LG}px;
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
        self.scenario_table.set_data([
            {
                "scenario": s.get("name", ""),
                "status": str(s.get("status", "")).upper(),
                "duration": s.get("duration", ""),
                "errors": str(s.get("errors", 0)),
            }
            for s in scenarios
        ])

        checks = d.get("integrity_checks", summary.get("integrity_checks", []))
        self.integrity_table.set_data([
            {
                "check": c.get("check", ""),
                "status": str(c.get("status", "")).upper(),
                "detail": c.get("detail", ""),
            }
            for c in checks
        ])

        slas = d.get("sla_violations", summary.get("sla_violations", []))
        self.sla_table.set_data([
            {
                "sla": sla.get("name", ""),
                "compliance": f"{sla.get('compliance', 0)}%",
                "violations": str(sla.get("violations", 0)),
                "trend": str(sla.get("trend", "stable")).upper(),
            }
            for sla in slas
        ])

    def _on_error(self, error_msg):
        self.last_update.setText("Connection error")
