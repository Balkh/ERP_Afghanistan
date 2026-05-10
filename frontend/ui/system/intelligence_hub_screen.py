from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""
ERP Intelligence Hub - Unified Command Center.
Unifies all ERP intelligence layers (Control Center, Workflows, Integrity, Correlation) 
into a single, high-performance cockpit.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QLabel, QFrame, QScrollArea, QListWidget,
                                QListWidgetItem, QSizePolicy, QPushButton, QStackedWidget, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from ui.screens.base_screen import BaseScreen
from ui.constants import (COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                          SPACING_MD, SPACING_LG, FONT_SIZE_LG, FONT_SIZE_XL)

# Import existing modules
from ui.system.control_center_screen import ControlCenterScreen
from ui.system.workflow_intelligence_screen import WorkflowIntelligenceScreen
from ui.system.integrity_screen import SystemIntegrityScreen
from ui.system.drift_intelligence_screen import DriftIntelligenceScreen
from ui.system.correlation_screen import SystemCorrelationScreen

# Import observability layer
from utils.logger import (
    generate_operational_dashboard_data,
    get_event_summary,
    detect_anomalies,
    get_trace,
    generate_correlation_id,
    emit_event,
    evaluate_decisions,
)


class IntelligenceHubScreen(BaseScreen):
    """Unified ERP Intelligence Cockpit - Single Command Center."""
    
    def __init__(self, parent=None, screen_id="intelligence_hub", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the Command Center layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Section: Main Content (Tabs)
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        content_layout.setSpacing(SPACING_MD)
        
        # Global Header & Alert Center
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("ERP Intelligence Hub")
        self.title_label.setFont(QFont("Segoe UI", FONT_SIZE_XL, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        
        self.health_indicator = QLabel("ERP HEALTH: 100%")
        self.health_indicator.setStyleSheet(f"background: {COLOR_BG_ELEVATED}; color: {COLOR_STATUS_VALID}; padding: 6px 15px; border-radius: 15px; font-weight: bold; font-size: 11px; border: 1px solid {COLOR_STATUS_VALID};")
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.health_indicator)
        content_layout.addLayout(self.header_layout)

        # Alert Banner (Global)
        self.alert_banner = QFrame()
        self.alert_banner.setFixedHeight(40)
        self.alert_banner.setStyleSheet(f"background: {COLOR_BG_MAIN}; border: 1px solid #f38ba8; border-radius: 8px;")
        ab_layout = QHBoxLayout(self.alert_banner)
        self.alert_text = QLabel("🚨 NO CRITICAL INCIDENTS DETECTED")
        self.alert_text.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 11px;")
        ab_layout.addWidget(self.alert_text)
        content_layout.addWidget(self.alert_banner)
        
        # Tabs for Intelligence Layers
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BG_ELEVATED}; border-radius: 12px; background: {COLOR_BG_MAIN}; top: -1px; }}
            QTabBar::tab {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_SECONDARY}; padding: 12px 25px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 5px; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {COLOR_BG_MAIN}; color: {COLOR_PRIMARY}; border-bottom: 2px solid {COLOR_PRIMARY}; }}
            QTabBar::tab:hover {{ background: {COLOR_BG_ELEVATED}; }}
        """)
        
        # 1. Overview Tab (Aggregated)
        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")
        
        # Placeholder for other tabs (Lazy Loaded)
        self.tab_instances = {
            1: {"class": ControlCenterScreen, "instance": None, "label": "Observability"},
            2: {"class": WorkflowIntelligenceScreen, "instance": None, "label": "Workflows"},
            3: {"class": SystemIntegrityScreen, "instance": None, "label": "Integrity"},
            4: {"class": DriftIntelligenceScreen, "instance": None, "label": "Drift Intel"},
            5: {"class": SystemCorrelationScreen, "instance": None, "label": "Correlation"},
            6: {"class": None, "instance": None, "label": "Decisions"},  # Built-in, not lazy-loaded
        }

        for i in range(1, 6):
            placeholder = QWidget()
            QVBoxLayout(placeholder).addWidget(QLabel(f"Loading {self.tab_instances[i]['label']}..."))
            self.tabs.addTab(placeholder, self.tab_instances[i]['label'])

        # Add Decisions tab (built-in, always available)
        self.decisions_tab = QWidget()
        self._setup_decisions_tab()
        self.tabs.addTab(self.decisions_tab, "Decisions")
        
        content_layout.addWidget(self.tabs)
        main_layout.addWidget(content_frame, 3)

    def _setup_overview_tab(self):
        """Build the aggregated overview dashboard."""
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG + SPACING_XS)

        # KPI Row
        kpi_layout = QHBoxLayout()
        self.kpis = {
            "health": self._create_mini_card("ERP Health", "100%", COLOR_SUCCESS),
            "workflows": self._create_mini_card("Active Workflows", "0", COLOR_WARNING),
            "drift": self._create_mini_card("Drift Score", "0%", COLOR_INFO),
            "revenue": self._create_mini_card("Revenue (Today)", "0 AFN", COLOR_SUCCESS)
        }
        for card in self.kpis.values(): kpi_layout.addWidget(card)
        layout.addLayout(kpi_layout)

        # Summary Grid
        grid = QGridLayout()
        grid.setSpacing(SPACING_MD + SPACING_XS)

        # System Status
        status_box = QGroupBox("Operational Status")
        status_box.setStyleSheet(f"QGroupBox {{ color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_BG_ELEVATED}; border-radius: 12px; margin-top: 10px; }}")
        self.status_label = QLabel("Loading system status...")
        QVBoxLayout(status_box).addWidget(self.status_label)
        grid.addWidget(status_box, 0, 0)

        # Recent Anomalies
        anomaly_box = QGroupBox("Recent Intelligence Signals")
        anomaly_box.setStyleSheet(status_box.styleSheet())
        self.event_list = QListWidget() # Renamed to event_list to match _refresh_event_stream
        self.event_list.setStyleSheet("background: transparent; border: none;")
        self.event_list.addItem("Checking for signals...")
        QVBoxLayout(anomaly_box).addWidget(self.event_list)
        grid.addWidget(anomaly_box, 0, 1)

        # Error Overview
        error_box = QGroupBox("Error Overview")
        error_box.setStyleSheet(status_box.styleSheet())
        self.error_label = QLabel("Loading error data...")
        self.error_label.setWordWrap(True)
        QVBoxLayout(error_box).addWidget(self.error_label)
        grid.addWidget(error_box, 1, 0)

        # Performance Overview
        perf_box = QGroupBox("Performance Overview")
        perf_box.setStyleSheet(status_box.styleSheet())
        self.perf_label = QLabel("Loading performance data...")
        self.perf_label.setWordWrap(True)
        QVBoxLayout(perf_box).addWidget(self.perf_label)
        grid.addWidget(perf_box, 1, 1)

        layout.addLayout(grid)

        # Active Decisions section (in overview tab)
        self.decisions_box = QGroupBox("Active Decisions")
        self.decisions_box.setStyleSheet(status_box.styleSheet())
        self.decisions_list = QListWidget()
        self.decisions_list.setStyleSheet("background: transparent; border: none;")
        self.decisions_list.addItem("Loading decisions...")
        QVBoxLayout(self.decisions_box).addWidget(self.decisions_list)
        layout.addWidget(self.decisions_box)

        layout.addStretch()

    def _setup_decisions_tab(self):
        """Build the Decisions Intelligence tab."""
        layout = QVBoxLayout(self.decisions_tab)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Decision Intelligence Engine")
        header.setFont(QFont("Segoe UI", FONT_SIZE_LG, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        # Risk overview cards
        risk_layout = QHBoxLayout()
        self.risk_cards = {}
        for level, color in [('low', COLOR_SUCCESS), ('medium', COLOR_WARNING), ('high', '#fab729'), ('critical', COLOR_DANGER)]:
            card = self._create_mini_card(f"{level.upper()} Risk", "0", color)
            self.risk_cards[level] = card
            risk_layout.addWidget(card)
        layout.addLayout(risk_layout)

        # Active decisions list
        decisions_group = QGroupBox("System Decisions")
        decisions_group.setStyleSheet(f"QGroupBox {{ color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_BG_ELEVATED}; border-radius: 12px; margin-top: 10px; }}")
        self.decisions_list_detail = QListWidget()
        self.decisions_list_detail.setStyleSheet("background: transparent; border: none;")
        self.decisions_list_detail.addItem("Pulling live decisions...")
        vbox = QVBoxLayout(decisions_group)
        vbox.addWidget(self.decisions_list_detail)
        layout.addWidget(decisions_group)

        # Actions section
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
        """Refresh decisions tab with live data."""
        try:
            decisions = evaluate_decisions()
            active = decisions.get('active_decisions', [])
            summary = decisions.get('summary', {})

            # Update risk cards
            by_cat = summary.get('by_category', {})
            risk_order = {'security': 'critical', 'system': 'critical', 'performance': 'high', 'ui': 'high', 'financial': 'critical', 'inventory': 'medium'}

            # Count by risk level
            critical_count = sum(1 for d in active if d.get('risk_level') == 'critical')
            high_count = sum(1 for d in active if d.get('risk_level') == 'high')
            medium_count = sum(1 for d in active if d.get('risk_level') == 'medium')
            low_count = sum(1 for d in active if d.get('risk_level') == 'low')

            self.risk_cards['critical'].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(critical_count))
            self.risk_cards['high'].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(high_count))
            self.risk_cards['medium'].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(medium_count))
            self.risk_cards['low'].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(low_count))

            # Update decisions list
            self.decisions_list_detail.clear()
            if not active:
                self.decisions_list_detail.addItem("No active decisions. System is healthy.")
                self.actions_label.setText("No active decisions requiring action.")
                return

            for d in active:
                rid = d.get('decision_id', '?')
                cat = d.get('category', '?').upper()
                risk = d.get('risk_level', '?').upper()
                decision_text = d.get('decision', '')
                confidence = d.get('confidence', 0)
                color = COLOR_DANGER if risk == 'CRITICAL' else ('#fab729' if risk == 'HIGH' else (COLOR_WARNING if risk == 'MEDIUM' else COLOR_SUCCESS))
                item = QListWidgetItem(f"[{rid}] [{cat}] [{risk}] {decision_text} (conf: {confidence:.0%})")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", 9))
                self.decisions_list_detail.addItem(item)

            # Build actions text
            actions_text = ""
            for d in active[:5]:
                for action in d.get('recommended_actions', []):
                    actions_text += f"  [{d.get('decision_id', '?')}]: {action}\n"
            self.actions_label.setText(actions_text if actions_text else "No active decisions requiring action.")

        except Exception:
            self.decisions_list_detail.clear()
            self.decisions_list_detail.addItem("Decision engine temporarily unavailable.")

    def _create_mini_card(self, title, val, color):
        card = QFrame()
        card.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border-radius: 10px; border-left: 3px solid {color};")
        l = QVBoxLayout(card)
        l.addWidget(QLabel(title))
        v = QLabel(val)
        v.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        l.addWidget(v)
        return card

    def _on_tab_changed(self, index):
        """Lazy load the selected tab if not already instantiated."""
        if index == 0: return # Overview always loaded

        # Decisions tab (index 6) is built-in, just refresh it
        if index == 6:
            self._refresh_decisions_tab()
            return

        tab_info = self.tab_instances.get(index)
        if tab_info and tab_info["instance"] is None:
            # Instantiate the screen
            screen_class = tab_info["class"]
            instance = screen_class(api_client=self._api_client)
            tab_info["instance"] = instance
            
            # Replace placeholder
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, instance, tab_info["label"])
            self.tabs.setCurrentIndex(index)
            
            # Trigger initial load
            if hasattr(instance, '_on_screen_shown'):
                instance._on_screen_shown()

    def _on_screen_shown(self):
        """Initialize overview data with real observability metrics."""
        self._refresh_overview_dashboard()

    def _refresh_overview_dashboard(self):
        """Pull live data from the observability layer."""
        try:
            dashboard = generate_operational_dashboard_data()
        except Exception:
            dashboard = {}

        # Update KPIs
        health = dashboard.get('system_health', {})
        stability = str(health.get('stability_score', 0))
        self.kpis["health"].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(
            f"{stability}%")
        color = COLOR_SUCCESS if health.get('stability_score', 0) >= 80 else (
            COLOR_WARNING if health.get('stability_score', 0) >= 50 else COLOR_DANGER)
        self.kpis["health"].setStyleSheet(
            f"background: {COLOR_BG_SURFACE}; border-radius: 10px; border-left: 3px solid {color};")
        self.kpis["health"].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold;")

        # Update health indicator in header
        self.health_indicator.setText(f"ERP HEALTH: {stability}%")
        self.health_indicator.setStyleSheet(
            f"background: {COLOR_BG_ELEVATED}; color: {color}; padding: 6px 15px; "
            f"border-radius: 15px; font-weight: bold; font-size: 11px; border: 1px solid {color};")

        # Check for anomalies and update alert banner
        anomalies = health.get('anomalies', [])
        if anomalies:
            anomaly_types = ', '.join(a.get('type', 'unknown') for a in anomalies[:3])
            self.alert_text.setText(f"⚠ ANOMALIES DETECTED: {anomaly_types}")
            self.alert_text.setStyleSheet("color: #fab729; font-weight: bold; font-size: 11px;")
            self.alert_banner.setStyleSheet(
                f"background: {COLOR_BG_MAIN}; border: 1px solid #fab729; border-radius: 8px;")
        else:
            self.alert_text.setText("🚨 NO CRITICAL INCIDENTS DETECTED")
            self.alert_text.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 11px;")
            self.alert_banner.setStyleSheet(
                f"background: {COLOR_BG_MAIN}; border: 1px solid #f38ba8; border-radius: 8px;")

        # Update error overview
        error_overview = dashboard.get('error_overview', {})
        top_errors = error_overview.get('top_errors', [])
        total = error_overview.get('total_tracked_errors', 0)
        error_text = f"Total tracked errors: {total}\n\n"
        for exc_type, count in top_errors[:5]:
            error_text += f"  • {exc_type}: {count} occurrences\n"
        failing_module = error_overview.get('most_failing_module', {})
        if failing_module.get('module'):
            error_text += f"\nMost failing module: {failing_module['module']} ({failing_module['count']} events)"
        self.error_label.setText(error_text if top_errors else "No errors tracked yet.")

        # Update performance overview
        perf_overview = dashboard.get('performance_overview', {})
        avg_latency = perf_overview.get('avg_api_latency', 0)
        perf_text = f"Average API latency: {avg_latency}ms\n\n"
        slow_api = perf_overview.get('slow_operations', [])
        if slow_api:
            perf_text += f"Slow API calls (>3s): {len(slow_api)}\n"
            for endpoint, duration in slow_api[:5]:
                perf_text += f"  • {endpoint}: {duration:.0f}ms\n"
        else:
            perf_text += "No slow API calls detected.\n"
        slow_ui = perf_overview.get('slow_ui_operations', [])
        if slow_ui:
            perf_text += f"\nSlow screen loads (>3s): {len(slow_ui)}\n"
            for screen, duration in slow_ui[:5]:
                perf_text += f"  • {screen}: {duration:.0f}ms\n"
        self.perf_label.setText(perf_text)

        # Update event list from real event store
        self._refresh_event_stream()

        # Update decisions section in overview
        self._refresh_decisions_overview()

    def _refresh_event_stream(self):
        """Stream live events from the in-memory event store."""
        self.event_list.clear()
        try:
            events_summary = get_event_summary(limit=30)
            recent = events_summary.get('recent_events', [])
            if not recent:
                self.event_list.addItem("No events captured yet.")
                return
            type_colors = {
                'api_request': COLOR_INFO,
                'api_response': COLOR_SUCCESS,
                'ui_action': COLOR_INFO,
                'navigation_event': COLOR_INFO,
                'auth_event': COLOR_WARNING,
                'error_event': COLOR_DANGER,
                'system_event': COLOR_WARNING,
            }
            for e in recent:
                ts = e.get('timestamp', '')
                etype = e.get('type', 'unknown')
                action = e.get('action', '')
                module = e.get('module', '')
                color = type_colors.get(etype, COLOR_TEXT_MUTED)
                item = QListWidgetItem(f"[{ts}] [{module}] {action}")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", 9))
                self.event_list.addItem(item)

            # Update distribution card
            distribution = events_summary.get('distribution', {})
            if distribution:
                total = sum(distribution.values())
                top_types = sorted(distribution.items(), key=lambda x: -x[1])[:3]
                summary = ", ".join(f"{t}: {c}" for t, c in top_types)
                self.kpis["workflows"].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText(str(total))
        except Exception:
            self.event_list.addItem("Event stream temporarily unavailable")

    def _refresh_decisions_overview(self):
        """Update the decisions section in the overview tab."""
        try:
            decisions = evaluate_decisions()
            active = decisions.get('active_decisions', [])
            if not active:
                self.decisions_list.clear()
                self.decisions_list.addItem("No active decisions. System is healthy.")
                return
            self.decisions_list.clear()
            for d in active[:10]:
                risk = d.get('risk_level', '?').upper()
                color = COLOR_DANGER if risk == 'CRITICAL' else ('#fab729' if risk == 'HIGH' else (COLOR_WARNING if risk == 'MEDIUM' else COLOR_SUCCESS))
                item = QListWidgetItem(f"[{d.get('decision_id', '?')}] [{risk}] {d.get('decision', '')}")
                item.setForeground(QColor(color))
                item.setFont(QFont("Segoe UI", 9))
                self.decisions_list.addItem(item)
        except Exception:
            self.decisions_list.clear()
            self.decisions_list.addItem("Decision engine unavailable.")
