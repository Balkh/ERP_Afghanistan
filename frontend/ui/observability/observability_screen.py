from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QLabel, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL,
                          FONT_SIZE_XS, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
                          FONT_SIZE_TITLE, FONT_SIZE_HEADER, MARGIN_PAGE,
                          COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
                          COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                          COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                          COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                          COLOR_BORDER, COLOR_BORDER_LIGHT,
                          BORDER_RADIUS_MD, BORDER_RADIUS_LG)
from ui.observability.widgets import LoadingOverlay
from ui.observability.dashboards import (ObservabilityMainScreen,
                                          ControlCenterDashboard,
                                          UnifiedTimelineView,
                                          IncidentIntelligenceView,
                                          PredictiveDriftDashboard,
                                          ReplayTimeTravelView,
                                          DigitalTwinTelemetryView)


class ObservabilityScreen(QWidget):
    REFRESH_INTERVAL_MS = 5000

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api_client = api_client
        self._tabs_loaded = set()
        self._dashboards = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header_bar = QFrame()
        header_bar.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-bottom: 1px solid {COLOR_BORDER};")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(MARGIN_PAGE, SPACING_SM, MARGIN_PAGE, SPACING_SM)

        title = QLabel("Observability")
        title.setFont(QFont("Segoe UI", FONT_SIZE_TITLE, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.status_label = QLabel("READ-ONLY MODE")
        self.status_label.setStyleSheet(f"""
            background-color: {COLOR_BG_ELEVATED};
            color: {COLOR_TEXT_MUTED};
            padding: 2px 10px;
            border-radius: 4px;
            font-size: {FONT_SIZE_XS}px;
            font-weight: bold;
            border: none;
        """)
        header_layout.addWidget(self.status_label)
        layout.addWidget(header_bar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLOR_BG_MAIN};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_SECONDARY};
                padding: 8px 18px;
                border: none;
                font-size: {FONT_SIZE_SM}px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_PRIMARY};
                border-bottom: 2px solid {COLOR_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget, 1)

        self._add_tab("Overview", "overview")
        self._add_tab("Control Center", "control_center")
        self._add_tab("Timeline", "timeline")
        self._add_tab("Incidents", "incidents")
        self._add_tab("Drift", "drift")
        self._add_tab("Replay", "replay")
        self._add_tab("Telemetry", "telemetry")

        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.show_overlay()
        QTimer.singleShot(500, self._initial_load)

    def _add_tab(self, label, key):
        placeholder = QWidget()
        placeholder.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)
        loading = QLabel("Loading...")
        loading.setFont(QFont("Segoe UI", FONT_SIZE_SM))
        loading.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        loading.setAlignment(Qt.AlignCenter)
        layout.addWidget(loading)
        idx = self.tab_widget.addTab(placeholder, label)
        self._dashboards[idx] = {"key": key, "loaded": False}

    def _on_tab_changed(self, index):
        if index < 0:
            return
        info = self._dashboards.get(index)
        if info and not info["loaded"]:
            self._load_tab(index, info["key"])

    def _load_tab(self, index, key):
        info = self._dashboards.get(index)
        if not info or info["loaded"]:
            return

        dashboard = self._create_dashboard(key)
        if dashboard:
            self.tab_widget.removeTab(index)
            new_idx = self.tab_widget.insertTab(index, dashboard, self.tab_widget.tabText(index))
            self._dashboards[new_idx] = {"key": key, "loaded": True}
            self._dashboards.pop(index, None)
            dashboard.start_auto_refresh(self.REFRESH_INTERVAL_MS)

    def _create_dashboard(self, key):
        creators = {
            "overview": ObservabilityMainScreen,
            "control_center": ControlCenterDashboard,
            "timeline": UnifiedTimelineView,
            "incidents": IncidentIntelligenceView,
            "drift": PredictiveDriftDashboard,
            "replay": ReplayTimeTravelView,
            "telemetry": DigitalTwinTelemetryView,
        }
        cls = creators.get(key)
        if cls:
            return cls(self._api_client, self)
        return None

    def _initial_load(self):
        self._load_tab(0, "overview")
        self.loading_overlay.hide_overlay()

    def showEvent(self, event):
        super().showEvent(event)
        if event.isVisible():
            for index, info in list(self._dashboards.items()):
                if info.get("loaded"):
                    tab = self.tab_widget.widget(index)
                    if hasattr(tab, "start_auto_refresh"):
                        tab.start_auto_refresh(self.REFRESH_INTERVAL_MS)

    def hideEvent(self, event):
        super().hideEvent(event)
        for index, info in list(self._dashboards.items()):
            if info.get("loaded"):
                tab = self.tab_widget.widget(index)
                if hasattr(tab, "stop_auto_refresh"):
                    tab.stop_auto_refresh()
