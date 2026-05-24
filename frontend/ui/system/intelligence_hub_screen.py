from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QLabel, QFrame, QListWidget, QListWidgetItem,
                                QGroupBox, QGridLayout)
from PySide6.QtGui import QFont, QColor
from ui.screens.base_screen import BaseScreen
from ui.constants import (
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
    COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY,
    COLOR_BG_ELEVATED, SPACING_NONE, SPACING_XS, SPACING_MD,
    SPACING_LG, TEXT_LABEL, TEXT_SECTION_TITLE,
    TEXT_TABLE, MARGIN_PAGE, SPACING_6, BORDER_RADIUS_PILL)
from theme.style_builder import UIStyleBuilder
from ui.system.control_center_screen import ControlCenterScreen
from ui.system.workflow_intelligence_screen import WorkflowIntelligenceScreen
from ui.system.integrity_screen import SystemIntegrityScreen
from ui.system.drift_intelligence_screen import DriftIntelligenceScreen
from ui.system.correlation_screen import SystemCorrelationScreen
from utils.logger import (
    generate_operational_dashboard_data,
    get_event_summary,
    evaluate_decisions,
)
from ui.components.kpi_cards import KPICard


class IntelligenceHubScreen(BaseScreen):
    def __init__(self, parent=None, screen_id="intelligence_hub", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._kpi_value_labels = {}
        self._risk_value_labels = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(SPACING_NONE)

        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        content_layout.setSpacing(SPACING_MD)

        from theme.style_builder import UIStyleBuilder
        self.title_label = QLabel("ERP Intelligence Hub")
        self.title_label.setStyleSheet(UIStyleBuilder.get_label_style("title"))

        self.health_indicator = QLabel("ERP HEALTH: 100%")
        self.health_indicator.setStyleSheet(
            f"background: {COLOR_BG_ELEVATED}; color: {COLOR_STATUS_VALID}; "
            f"padding: {SPACING_6}px {SPACING_MD}px; border-radius: {BORDER_RADIUS_PILL}px; font-weight: bold; font-size: {TEXT_LABEL}px; "
            f"border: 1px solid {COLOR_STATUS_VALID};"
        )

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.health_indicator)
        content_layout.addLayout(header_layout)

        self.alert_banner = QFrame()
        self.alert_banner.setFixedHeight(40)
        self.alert_banner.setStyleSheet(UIStyleBuilder.get_warning_banner_style('critical'))
        ab_layout = QHBoxLayout(self.alert_banner)
        self.alert_text = QLabel("NO CRITICAL INCIDENTS DETECTED")
        self.alert_text.setStyleSheet(UIStyleBuilder.get_colored_label_style(COLOR_DANGER, TEXT_LABEL, 700))
        ab_layout.addWidget(self.alert_text)
        content_layout.addWidget(self.alert_banner)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(UIStyleBuilder.get_tab_style())

        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        self.tab_instances = {
            1: {"class": ControlCenterScreen, "instance": None, "label": "Observability"},
            2: {"class": WorkflowIntelligenceScreen, "instance": None, "label": "Workflows"},
            3: {"class": SystemIntegrityScreen, "instance": None, "label": "Integrity"},
            4: {"class": DriftIntelligenceScreen, "instance": None, "label": "Drift Intel"},
            5: {"class": SystemCorrelationScreen, "instance": None, "label": "Correlation"},
            6: {"class": None, "instance": None, "label": "Decisions"},
        }

        for i in range(1, 6):
            placeholder = QWidget()
            QVBoxLayout(placeholder).addWidget(QLabel(f"Loading {self.tab_instances[i]['label']}..."))
            self.tabs.addTab(placeholder, self.tab_instances[i]['label'])

        self.decisions_tab = QWidget()
        self._setup_decisions_tab()
        self.tabs.addTab(self.decisions_tab, "Decisions")

        content_layout.addWidget(self.tabs)
        main_layout.addWidget(content_frame, 3)

    def _setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG + SPACING_XS)

        kpi_layout = QHBoxLayout()
        self._kpi_value_labels = {}
        kpi_specs = [
            ("health", "ERP Health", "100%", "success"),
            ("workflows", "Active Workflows", "0", "warning"),
            ("drift", "Drift Score", "0%", "info"),
            ("revenue", "Revenue (Today)", "0 AFN", "success"),
        ]
        for key, title, val, severity in kpi_specs:
            card = KPICard(title, val, severity=severity)
            self._kpi_value_labels[key] = card.value_label
            kpi_layout.addWidget(card)
        layout.addLayout(kpi_layout)

        grid = QGridLayout()
        grid.setSpacing(SPACING_MD + SPACING_XS)

        status_box = QGroupBox("Operational Status")
        status_box.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=True))
        self.status_label = QLabel("Loading system status...")
        QVBoxLayout(status_box).addWidget(self.status_label)
        grid.addWidget(status_box, 0, 0)

        anomaly_box = QGroupBox("Recent Intelligence Signals")
        anomaly_box.setStyleSheet(status_box.styleSheet())
        self.event_list = QListWidget()
        self.event_list.setStyleSheet("background: transparent; border: none;")
        self.event_list.addItem("Checking for signals...")
        QVBoxLayout(anomaly_box).addWidget(self.event_list)
        grid.addWidget(anomaly_box, 0, 1)

        error_box = QGroupBox("Error Overview")
        error_box.setStyleSheet(status_box.styleSheet())
        self.error_label = QLabel("Loading error data...")
        self.error_label.setWordWrap(True)
        QVBoxLayout(error_box).addWidget(self.error_label)
        grid.addWidget(error_box, 1, 0)

        perf_box = QGroupBox("Performance Overview")
        perf_box.setStyleSheet(status_box.styleSheet())
        self.perf_label = QLabel("Loading performance data...")
        self.perf_label.setWordWrap(True)
        QVBoxLayout(perf_box).addWidget(self.perf_label)
        grid.addWidget(perf_box, 1, 1)

        layout.addLayout(grid)

        self.decisions_box = QGroupBox("Active Decisions")
        self.decisions_box.setStyleSheet(status_box.styleSheet())
        self.decisions_list = QListWidget()
        self.decisions_list.setStyleSheet("background: transparent; border: none;")
        self.decisions_list.addItem("Loading decisions...")
        QVBoxLayout(self.decisions_box).addWidget(self.decisions_list)
        layout.addWidget(self.decisions_box)
        layout.addStretch()

    def _setup_decisions_tab(self):
        layout = QVBoxLayout(self.decisions_tab)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Decision Intelligence Engine")
        header.setStyleSheet(UIStyleBuilder.get_label_style("section"))
        layout.addWidget(header)

        risk_layout = QHBoxLayout()
        self._risk_value_labels = {}
        risk_configs = [
            ("low", "success"),
            ("medium", "warning"),
            ("high", "danger"),
            ("critical", "danger"),
        ]
        for level, severity in risk_configs:
            card = KPICard(f"{level.upper()} Risk", "0", severity=severity)
            self._risk_value_labels[level] = card.value_label
            risk_layout.addWidget(card)
        layout.addLayout(risk_layout)

        decisions_group = QGroupBox("System Decisions")
        decisions_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=True))
        self.decisions_list_detail = QListWidget()
        self.decisions_list_detail.setStyleSheet("background: transparent; border: none;")
        self.decisions_list_detail.addItem("Pulling live decisions...")
        vbox = QVBoxLayout(decisions_group)
        vbox.addWidget(self.decisions_list_detail)
        layout.addWidget(decisions_group)

        actions_group = QGroupBox("Recommended Actions")
        actions_group.setStyleSheet(decisions_group.styleSheet())
        self.actions_label = QLabel("No active decisions requiring action.")
        self.actions_label.setWordWrap(True)
        self.actions_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        vbox2 = QVBoxLayout(actions_group)
        vbox2.addWidget(self.actions_label)
        layout.addWidget(actions_group)
        layout.addStretch()

    def _refresh_decisions_tab(self):
        try:
            decisions = evaluate_decisions()
            active = decisions.get("active_decisions", [])
            critical_count = sum(1 for d in active if d.get("risk_level") == "critical")
            high_count = sum(1 for d in active if d.get("risk_level") == "high")
            medium_count = sum(1 for d in active if d.get("risk_level") == "medium")
            low_count = sum(1 for d in active if d.get("risk_level") == "low")
            if "critical" in self._risk_value_labels:
                self._risk_value_labels["critical"].setText(str(critical_count))
            if "high" in self._risk_value_labels:
                self._risk_value_labels["high"].setText(str(high_count))
            if "medium" in self._risk_value_labels:
                self._risk_value_labels["medium"].setText(str(medium_count))
            if "low" in self._risk_value_labels:
                self._risk_value_labels["low"].setText(str(low_count))

            self.decisions_list_detail.setUpdatesEnabled(False)
            self.decisions_list_detail.clear()
            if not active:
                self.decisions_list_detail.addItem("No active decisions. System is healthy.")
                self.actions_label.setText("No active decisions requiring action.")
                self.decisions_list_detail.setUpdatesEnabled(True)
                return

            for d in active:
                rid = d.get("decision_id", "?")
                cat = d.get("category", "?").upper()
                risk = d.get("risk_level", "?").upper()
                decision_text = d.get("decision", "")
                confidence = d.get("confidence", 0)
                color = (
                    COLOR_DANGER if risk == "CRITICAL" else
                    COLOR_DANGER if risk == "HIGH" else
                    COLOR_WARNING if risk == "MEDIUM" else
                    COLOR_SUCCESS
                )
                item = QListWidgetItem(f"[{rid}] [{cat}] [{risk}] {decision_text} (conf: {confidence:.0%})")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", TEXT_TABLE))
                self.decisions_list_detail.addItem(item)

            self.decisions_list_detail.setUpdatesEnabled(True)
            actions_text = ""
            for d in active[:5]:
                for action in d.get("recommended_actions", []):
                    actions_text += f"  [{d.get('decision_id', '?')}]: {action}\n"
            self.actions_label.setText(actions_text if actions_text else "No active decisions requiring action.")
        except Exception:
            self.decisions_list_detail.setUpdatesEnabled(False)
            self.decisions_list_detail.clear()
            self.decisions_list_detail.addItem("Decision engine temporarily unavailable.")
            self.decisions_list_detail.setUpdatesEnabled(True)

    def _on_tab_changed(self, index):
        if index == 0:
            return
        if index == 6:
            self._refresh_decisions_tab()
            return
        tab_info = self.tab_instances.get(index)
        if tab_info and tab_info["instance"] is None:
            screen_class = tab_info["class"]
            instance = screen_class(api_client=self._api_client)
            tab_info["instance"] = instance
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, instance, tab_info["label"])
            self.tabs.setCurrentIndex(index)
            if hasattr(instance, "_on_screen_shown"):
                instance._on_screen_shown()

    def _on_screen_shown(self):
        self._refresh_overview_dashboard()

    def _refresh_overview_dashboard(self):
        try:
            dashboard = generate_operational_dashboard_data()
        except Exception:
            dashboard = {}

        health = dashboard.get("system_health", {})
        stability = health.get("stability_score", 0)
        color = (
            COLOR_SUCCESS if stability >= 80 else
            COLOR_WARNING if stability >= 50 else
            COLOR_DANGER
        )
        if "health" in self._kpi_value_labels:
            self._kpi_value_labels["health"].setText(f"{stability}%")
            from theme.style_builder import UIStyleBuilder
            self._kpi_value_labels["health"].setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_SECTION_TITLE, 700))

        self.health_indicator.setText(f"ERP HEALTH: {stability}%")
        self.health_indicator.setStyleSheet(UIStyleBuilder.get_badge_style(color))

        anomalies = health.get("anomalies", [])
        if anomalies:
            anomaly_types = ", ".join(a.get("type", "unknown") for a in anomalies[:3])
            self.alert_text.setText(f"ANOMALIES DETECTED: {anomaly_types}")
            self.alert_text.setStyleSheet(UIStyleBuilder.get_colored_label_style(COLOR_STATUS_WARNING, TEXT_LABEL, 700))
            self.alert_banner.setStyleSheet(UIStyleBuilder.get_warning_banner_style('warning'))
        else:
            self.alert_text.setText("NO CRITICAL INCIDENTS DETECTED")
            self.alert_text.setStyleSheet(UIStyleBuilder.get_colored_label_style(COLOR_DANGER, TEXT_LABEL, 700))
            self.alert_banner.setStyleSheet(UIStyleBuilder.get_warning_banner_style('critical'))

        error_overview = dashboard.get("error_overview", {})
        top_errors = error_overview.get("top_errors", [])
        total = error_overview.get("total_tracked_errors", 0)
        error_text = f"Total tracked errors: {total}\n\n" if top_errors else ""
        for exc_type, count in top_errors[:5]:
            error_text += f"  * {exc_type}: {count} occurrences\n"
        failing_module = error_overview.get("most_failing_module", {})
        if failing_module.get("module"):
            error_text += f"\nMost failing module: {failing_module['module']} ({failing_module['count']} events)"
        self.error_label.setText(error_text if top_errors else "No errors tracked yet.")

        perf_overview = dashboard.get("performance_overview", {})
        avg_latency = perf_overview.get("avg_api_latency", 0)
        perf_text = f"Average API latency: {avg_latency}ms\n\n"
        slow_api = perf_overview.get("slow_operations", [])
        if slow_api:
            perf_text += f"Slow API calls (>3s): {len(slow_api)}\n"
            for endpoint, duration in slow_api[:5]:
                perf_text += f"  * {endpoint}: {duration:.0f}ms\n"
        else:
            perf_text += "No slow API calls detected.\n"
        slow_ui = perf_overview.get("slow_ui_operations", [])
        if slow_ui:
            perf_text += f"\nSlow screen loads (>3s): {len(slow_ui)}\n"
            for screen, duration in slow_ui[:5]:
                perf_text += f"  * {screen}: {duration:.0f}ms\n"
        self.perf_label.setText(perf_text)

        self._refresh_event_stream()
        self._refresh_decisions_overview()

    def _refresh_event_stream(self):
        self.event_list.setUpdatesEnabled(False)
        self.event_list.clear()
        try:
            events_summary = get_event_summary(limit=30)
            recent = events_summary.get("recent_events", [])
            if not recent:
                self.event_list.addItem("No events captured yet.")
                self.event_list.setUpdatesEnabled(True)
                return
            type_colors = {
                "api_request": COLOR_INFO, "api_response": COLOR_SUCCESS,
                "ui_action": COLOR_INFO, "navigation_event": COLOR_INFO,
                "auth_event": COLOR_WARNING, "error_event": COLOR_DANGER,
                "system_event": COLOR_WARNING,
            }
            for e in recent:
                ts = e.get("timestamp", "")
                etype = e.get("type", "unknown")
                action = e.get("action", "")
                module = e.get("module", "")
                color = type_colors.get(etype, COLOR_TEXT_MUTED)
                item = QListWidgetItem(f"[{ts}] [{module}] {action}")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", TEXT_TABLE))
                self.event_list.addItem(item)

            distribution = events_summary.get("distribution", {})
            if distribution and "workflows" in self._kpi_value_labels:
                total = sum(distribution.values())
                self._kpi_value_labels["workflows"].setText(str(total))
            self.event_list.setUpdatesEnabled(True)
        except Exception:
            self.event_list.addItem("Event stream temporarily unavailable")
            self.event_list.setUpdatesEnabled(True)

    def _refresh_decisions_overview(self):
        self.decisions_list.setUpdatesEnabled(False)
        try:
            decisions = evaluate_decisions()
            active = decisions.get("active_decisions", [])
            self.decisions_list.clear()
            if not active:
                self.decisions_list.addItem("No active decisions. System is healthy.")
                self.decisions_list.setUpdatesEnabled(True)
                return
            for d in active[:10]:
                risk = d.get("risk_level", "?").upper()
                color = (
                    COLOR_DANGER if risk == "CRITICAL" else
                    COLOR_DANGER if risk == "HIGH" else
                    COLOR_WARNING if risk == "MEDIUM" else
                    COLOR_SUCCESS
                )
                item = QListWidgetItem(f"[{d.get('decision_id', '?')}] [{risk}] {d.get('decision', '')}")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", TEXT_TABLE))
                self.decisions_list.addItem(item)
            self.decisions_list.setUpdatesEnabled(True)
        except Exception:
            self.decisions_list.clear()
            self.decisions_list.addItem("Decision engine unavailable.")
            self.decisions_list.setUpdatesEnabled(True)
