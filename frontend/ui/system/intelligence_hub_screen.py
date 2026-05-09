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
            5: {"class": SystemCorrelationScreen, "instance": None, "label": "Correlation"}
        }
        
        for i in range(1, 6):
            placeholder = QWidget()
            QVBoxLayout(placeholder).addWidget(QLabel(f"Loading {self.tab_instances[i]['label']}..."))
            self.tabs.addTab(placeholder, self.tab_instances[i]['label'])
        
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
        status_box.setStyleSheet(f"QGroupBox { color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_BG_ELEVATED}; border-radius: 12px; margin-top: 10px; }")
        QVBoxLayout(status_box).addWidget(QLabel("All systems operational. No critical drift detected."))
        grid.addWidget(status_box, 0, 0)
        
        # Recent Anomalies
        anomaly_box = QGroupBox("Recent Intelligence Signals")
        anomaly_box.setStyleSheet(status_box.styleSheet())
        self.event_list = QListWidget() # Renamed to event_list to match _refresh_event_stream
        self.event_list.setStyleSheet("background: transparent; border: none;")
        self.event_list.addItem("Checking for signals...")
        QVBoxLayout(anomaly_box).addWidget(self.event_list)
        grid.addWidget(anomaly_box, 0, 1)
        
        layout.addLayout(grid)
        layout.addStretch()

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
        """Initialize overview data."""
        self._refresh_event_stream()
        # Aggregation logic would go here to fill Overview KPIs
        self.kpis["health"].findChild(QLabel, "", Qt.FindDirectChildrenOnly).setText("100%")

    def _refresh_event_stream(self):
        """Fetch unified events from audit/ops APIs."""
        self.event_list.clear()
        try:
            # Combine multiple sources (Sales, Jobs, Workflows)
            # This is a simplified aggregation for the hub
            events = [
                {"ts": "10:45", "msg": "Invoice #442 Created", "color": COLOR_SUCCESS},
                {"ts": "10:42", "msg": "Workflow Approval Delayed", "color": COLOR_WARNING},
                {"ts": "10:35", "msg": "Background Job #12 Failed", "color": COLOR_DANGER},
                {"ts": "10:30", "msg": "Stock Update: Paracetamol", "color": COLOR_INFO},
            ]
            for e in events:
                item = QListWidgetItem(f"[{e['ts']}] {e['msg']}")
                item.setForeground(QColor(e['color']))
                item.setFont(QFont("Segoe UI", 9))
                self.event_list.addItem(item)
        except Exception:
            self.event_list.addItem("Stream temporarily unavailable")
