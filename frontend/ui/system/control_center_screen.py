from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""
Control Center Screen - Real-time ERP Monitoring Dashboard.
Provides centralized operational visibility and system intelligence.
"""

import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QProgressBar,
                               QListWidget, QListWidgetItem, QHeaderView,
                               QTableWidget, QTableWidgetItem, QPushButton,
                               QSizePolicy, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient

from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL,
                          FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
                          COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                          COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                          COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
                          COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_STATUS_VALID, COLOR_STATUS_WARNING,
                          MARGIN_PAGE, PADDING_CARD)
from api.control_center_service import ControlCenterService
from runtime.timer_registry import register_timer, unregister_owner


class DataFetchThread(QThread):
    """Worker thread for fetching dashboard data asynchronously using the Service Layer."""
    data_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, service: ControlCenterService):
        super().__init__()
        self.service = service
        self._is_running = True

    def run(self):
        """Fetch all dashboard data through the service layer."""
        try:
            results = self.service.get_dashboard_data()
            if results:
                self.data_received.emit(results)
            else:
                self.error_occurred.emit("No data received from service")
        except Exception as e:
            self.error_occurred.emit(f"Fetch failed: {str(e)}")

    def stop(self):
        self._is_running = False


class SparklineWidget(QWidget):
    """Lightweight trend indicator using a line chart."""
    def __init__(self, color=COLOR_PRIMARY):
        super().__init__()
        self.setFixedHeight(30)
        self.setMinimumWidth(80)
        self.color = color
        self.data = []

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw trend line
        painter.setPen(QColor(self.color))
        
        max_val = max(self.data) if self.data else 1
        min_val = min(self.data) if self.data else 0
        range_val = max_val - min_val if max_val != min_val else 1
        
        points = []
        w = self.width()
        h = self.height()
        step = w / (len(self.data) - 1) if len(self.data) > 1 else w
        
        for i, val in enumerate(self.data):
            x = i * step
            y = h - ((val - min_val) / range_val * (h - 4)) - 2
            points.append((x, y))
            
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])


class KPICard(QFrame):
    """A stylized card for displaying a single KPI metric with trend."""
    def __init__(self, title, value, subtitle="", color=COLOR_PRIMARY, icon=None):
        super().__init__()
        self.setObjectName("kpiCard")
        self.setMinimumSize(180, 110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.default_color = color
        
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {COLOR_BG_MAIN};
                border: 1px solid {COLOR_BG_ELEVATED};
                border-radius: 12px;
                border-left: 4px solid {color};
            }}
            QLabel#title {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            QLabel#value {{
                color: {color};
                font-size: 22px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: {COLOR_TEXT_MUTED};
                font-size: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("title")
        
        value_row = QHBoxLayout()
        self.value_label = QLabel(value)
        self.value_label.setObjectName("value")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.value_label.setWordWrap(True)
        
        self.sparkline = SparklineWidget(color)
        value_row.addWidget(self.value_label)
        value_row.addStretch()
        value_row.addWidget(self.sparkline)
        
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("subtitle")
        
        layout.addWidget(self.title_label)
        layout.addLayout(value_row)
        layout.addWidget(self.subtitle_label)

    def update_value(self, value, subtitle=None, trend_data=None, severity=None):
        self.value_label.setText(str(value))
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)
        if trend_data:
            self.sparkline.set_data(trend_data)
        
        if severity:
            color = severity
            self.value_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
            self.setStyleSheet(self.styleSheet().replace(f"border-left: 4px solid {self.default_color}", f"border-left: 4px solid {color}"))
            self.default_color = color
            self.sparkline.color = color
            self.sparkline.update()


class ControlCenterScreen(BaseScreen):
    """Enterprise Control Center - Real-time monitoring dashboard."""
    
    def __init__(self, parent=None, screen_id="control_center", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._service = ControlCenterService()
        self._fetch_thread = None
        self._is_fetching = False  # Lock flag to prevent overlapping requests
        self._history = {} # Store history for sparklines
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._fetch_data)
        
        # Initialize UI components
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the dashboard UI structure."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # Zero spacing for special layout
        
        # Scroll Area for the whole dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background-color: transparent;")
        
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {COLOR_BG_INPUT};")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        self.content_layout.setSpacing(SPACING_XL + SPACING_SM)  # ~25

        # Header with Refresh Info
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Enterprise Control Center")
        self.title_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        self.health_bar = QFrame()
        self.health_bar.setFixedHeight(30)
        self.health_bar.setMinimumWidth(200)
        self.health_bar.setStyleSheet(f"""
            background-color: {COLOR_BG_ELEVATED};
            border-radius: 15px;
            border: 1px solid {COLOR_BORDER};
        """)
        health_layout = QHBoxLayout(self.health_bar)
        health_layout.setContentsMargins(SPACING_SM, 0, SPACING_SM, 0)
        self.health_status_label = QLabel("SYSTEM HEALTH: OPTIMAL")
        self.health_status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: bold; font-size: 11px;")
        health_layout.addStretch()
        health_layout.addWidget(self.health_status_label)
        health_layout.addStretch()

        self.status_badge = QLabel("LIVE MONITORING")
        self.status_badge.setStyleSheet(f"""
            background-color: {COLOR_BG_ELEVATED};
            color: {COLOR_STATUS_VALID};
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        
        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        
        self.refresh_btn = QPushButton("Manual Refresh")
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self._fetch_data)
        
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.health_bar)
        header_layout.addWidget(self.status_badge)
        header_layout.addStretch()
        header_layout.addWidget(self.last_update_label)
        header_layout.addWidget(self.refresh_btn)
        
        self.content_layout.addLayout(header_layout)

        # Active Alerts Panel
        self.alerts_panel = QFrame()
        self.alerts_panel.setVisible(False)
        self.alerts_panel.setStyleSheet(f"""
            background-color: {COLOR_BORDER};
            border-radius: 8px;
            border: 1px solid {COLOR_DANGER};
        """)
        alerts_layout = QHBoxLayout(self.alerts_panel)
        self.alerts_label = QLabel("CRITICAL ALERTS: ")
        self.alerts_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold;")
        alerts_layout.addWidget(self.alerts_label)
        self.content_layout.addWidget(self.alerts_panel)

        # Section 1: System Health (Top Cards)
        self._setup_kpi_section()

        # Grid for middle sections
        grid_layout = QGridLayout()
        grid_layout.setSpacing(SPACING_LG + SPACING_XS)  # ~20

        # Section 2: Real-time Activity Stream (Left)
        self.activity_group = self._create_section_group("Activity Stream", 400)
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: none; border-radius: 8px;")
        self.activity_group.layout().addWidget(self.activity_list)
        grid_layout.addWidget(self.activity_group, 0, 0)

        # Section 3: Operational Intelligence (Right)
        self.intelligence_group = self._create_section_group("Intelligence & Signals", 400)
        self.intelligence_list = QListWidget()
        self.intelligence_list.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border: none; border-radius: 8px;")
        self.intelligence_group.layout().addWidget(self.intelligence_list)
        grid_layout.addWidget(self.intelligence_group, 0, 1)
        
        # Section 4: Workflow Monitor (Bottom Left)
        self.workflow_group = self._create_section_group("Workflow Status", 300)
        self.workflow_table = self._create_styled_table(["Workflow", "Status", "Owner", "Age"])
        self.workflow_group.layout().addWidget(self.workflow_table)
        grid_layout.addWidget(self.workflow_group, 1, 0)
        
        # Section 5: Background Jobs (Bottom Right)
        self.jobs_group = self._create_section_group("Job Monitor", 300)
        self.jobs_table = self._create_styled_table(["Job ID", "Type", "Status", "Runtime"])
        self.jobs_group.layout().addWidget(self.jobs_table)
        grid_layout.addWidget(self.jobs_group, 1, 1)
        
        self.content_layout.addLayout(grid_layout)
        
        # Section 6: Financial Health (Bottom Strip)
        self._setup_financial_section()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _setup_kpi_section(self):
        """Setup the top KPI cards section with System and Business metrics."""
        # System Metrics Row
        system_label = QLabel("SYSTEM PERFORMANCE")
        system_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        self.content_layout.addWidget(system_label)

        self.system_kpi_layout = QHBoxLayout()
        self.system_kpi_layout.setSpacing(SPACING_MD + SPACING_XS)  # ~15

        self.kpis = {
            'api_status': KPICard("API Status", "UP", "All services active", COLOR_STATUS_VALID),
            'db_health': KPICard("DB Health", "STABLE", "PostgreSQL Connected", COLOR_PRIMARY),
            'error_rate': KPICard("Error Rate", "0.0%", "Last 60 minutes", COLOR_WARNING),
            'latency': KPICard("Avg Latency", "45ms", "SLA: < 200ms", COLOR_WARNING),
            'active_jobs': KPICard("Active Jobs", "0", "Processing queue", COLOR_INFO),
            'stability': KPICard("Stability", "100%", "System Reliability", COLOR_PRIMARY)
        }

        for card in self.kpis.values():
            self.system_kpi_layout.addWidget(card)

        self.content_layout.addLayout(self.system_kpi_layout)

        # Business Metrics Row
        business_label = QLabel("BUSINESS OPERATIONS")
        business_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        self.content_layout.addWidget(business_label)

        self.business_kpi_layout = QHBoxLayout()
        self.business_kpi_layout.setSpacing(SPACING_MD + SPACING_XS)  # ~15

        self.biz_kpis = {
            'daily_invoices': KPICard("Daily Invoices", "0", "Sales generated", COLOR_PRIMARY),
            'payments': KPICard("Payments", "0", "Processed today", COLOR_STATUS_VALID),
            'stock_movements': KPICard("Stock Movements", "0", "Inventory activity", COLOR_WARNING),
            'revenue_snap': KPICard("Revenue (Today)", "0 AFN", "Cash inflow", COLOR_INFO)
        }

        for card in self.biz_kpis.values():
            self.business_kpi_layout.addWidget(card)
        
        self.content_layout.addLayout(self.business_kpi_layout)

    def _setup_financial_section(self):
        """Setup the bottom financial health section."""
        self.finance_group = self._create_section_group("Financial Health Snapshot", 150)
        layout = QHBoxLayout()
        layout.setSpacing(SPACING_LG + SPACING_XS)  # ~20
        
        self.fin_cards = {
            'revenue': self._create_fin_metric("Total Revenue (Today)", "0.00 AFN", COLOR_STATUS_VALID),
            'liabilities': self._create_fin_metric("Total Liabilities", "0.00 AFN", COLOR_DANGER),
            'assets': self._create_fin_metric("Total Assets", "0.00 AFN", COLOR_PRIMARY),
            'liquidity': self._create_fin_metric("Liquidity Status", "OPTIMAL", COLOR_INFO)
        }

        for widget in self.fin_cards.values():
            layout.addWidget(widget)

        self.finance_group.layout().addLayout(layout)
        self.content_layout.addWidget(self.finance_group)

    def _create_section_group(self, title, min_height):
        """Create a stylized group box for a section."""
        group = QGroupBox(title)
        group.setMinimumHeight(min_height)
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLOR_PRIMARY};
                font-size: 14px;
                font-weight: bold;
                border: 1px solid {COLOR_BG_ELEVATED};
                border-radius: 12px;
                margin-top: 15px;
                background-color: {COLOR_BG_SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 15px;
            }}
        """)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(SPACING_MD, SPACING_XL + SPACING_SM, SPACING_MD, SPACING_MD)  # 15, 25, 15, 15
        return group

    def _create_styled_table(self, headers):
        """Create a stylized table widget."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: none;
                gridline-color: {COLOR_TABLE_BORDER_LIGHT};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLOR_BG_ELEVATED};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {COLOR_TABLE_HEADER_BG_LIGHT};
                color: {COLOR_PRIMARY};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        return table

    def _create_fin_metric(self, title, value, color):
        """Create a simple financial metric widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_XS)  # 2
        
        t_label = QLabel(title)
        t_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        
        v_label = QLabel(value)
        v_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        v_label.setWordWrap(True)
        
        layout.addWidget(t_label)
        layout.addWidget(v_label)
        return widget

    def _on_screen_shown(self):
        """Called when screen is shown."""
        self._fetch_data()
        self._refresh_timer.start(15000)
        register_timer("control_center", self._refresh_timer)

    def _on_screen_hidden(self):
        """Called when screen is hidden."""
        self._refresh_timer.stop()

    def _fetch_data(self):
        """Initiate data fetch thread with overlap protection."""
        if self._is_fetching:
            print("[Control Center] Skip fetch: previous request still running")
            return
            
        self._is_fetching = True
        self.status_badge.setText("UPDATING...")
        self.status_badge.setStyleSheet(self.status_badge.styleSheet().replace("#a6e3a1", "#f9e2af"))
        
        self._fetch_thread = DataFetchThread(self._service)
        self._fetch_thread.data_received.connect(self._handle_data)
        self._fetch_thread.error_occurred.connect(self._handle_error)
        self._fetch_thread.finished.connect(self._on_fetch_finished)
        self._fetch_thread.start()

    def _on_fetch_finished(self):
        """Unlock fetching when thread completes."""
        self._is_fetching = False

    def _handle_data(self, results):
        """Update UI with fetched data, supporting partial rendering and fallback states."""
        self.last_update_label.setText(f"Last update: {time.strftime('%H:%M:%S')}")
        self.status_badge.setText("LIVE MONITORING")
        self.status_badge.setStyleSheet(self.status_badge.styleSheet().replace("#f9e2af", "#a6e3a1"))
        
        active_alerts = []
        
        # 1. Update Health KPIs
        health_res = results.get('health', {})
        if health_res.get('status') == 'ok':
            health = health_res.get('data', {})
            self.kpis['api_status'].update_value("UP", "All services active")
            db_status = health.get('database', {}).get('status', 'UNKNOWN')
            self.kpis['db_health'].update_value(db_status.upper(), "PostgreSQL Connected")
            if db_status.upper() != 'STABLE':
                active_alerts.append(f"DATABASE: {db_status}")
        else:
            self.kpis['api_status'].update_value("ERR", "Service unreachable", severity=COLOR_DANGER)
            self.kpis['db_health'].update_value("UNAVAILABLE", "Connection failed", severity=COLOR_DANGER)
            active_alerts.append("SYSTEM: API Services Unreachable")
            
        # 2. Update Intelligence & Signals
        intel_res = results.get('intelligence', {})
        signals_res = results.get('signals', {})
        self._update_intelligence(intel_res, signals_res)
        if signals_res.get('status') == 'ok' and len(signals_res.get('data', [])) > 0:
            active_alerts.append(f"SIGNALS: {len(signals_res.get('data'))} active intelligence signals")
        
        # 3. Update Activity Stream
        ops_res = results.get('ops', {})
        self._update_activity_stream(ops_res)
        
        # 4. Update Jobs
        jobs_res = results.get('jobs', {})
        self._update_jobs(jobs_res)
        if jobs_res.get('status') == 'ok':
            stuck_count = len(jobs_res.get('data', {}).get('stuck_jobs', []))
            if stuck_count > 0:
                active_alerts.append(f"JOBS: {stuck_count} stuck background jobs")

        # 5. Update Workflows
        workflows_res = results.get('workflows', {})
        self._update_workflows(workflows_res)
        if workflows_res.get('status') == 'ok':
            data = workflows_res.get('data', [])
            pending_count = len(data.get('results', data) if isinstance(data, dict) else data)
            if pending_count > 5:
                active_alerts.append(f"WORKFLOW: {pending_count} pending approvals (Threshold exceeded)")
        
        # 6. Update Financials
        financial_res = results.get('financial', {})
        self._update_financials(financial_res)
        
        # 7. Update Stats & Business KPIs
        stats_res = results.get('stats', {})
        if stats_res.get('status') == 'ok':
            stats = stats_res.get('data', {})
            self.biz_kpis['daily_invoices'].update_value(stats.get('total_invoices', 0), trend_data=self._update_history('invoices', stats.get('total_invoices', 0)))
            self.biz_kpis['payments'].update_value(stats.get('total_payments', 0), trend_data=self._update_history('payments', stats.get('total_payments', 0)))
            
            # Update latency & error rate from ops
            if ops_res.get('status') == 'ok':
                ops_data = ops_res.get('data', {}).get('api_health', {})
                errs = ops_data.get('errors_last_hour', 0)
                self.kpis['error_rate'].update_value(f"{errs}", "Errors last hour", 
                                                   trend_data=self._update_history('errors', errs),
                                                   severity=COLOR_DANGER if errs > 5 else None)
                if errs > 5: active_alerts.append(f"STABILITY: High error rate ({errs} errors/hr)")
                
                slows = ops_data.get('slow_requests_last_hour', 0)
                self.kpis['latency'].update_value(f"{slows}", "Slow requests (>500ms)", 
                                                 trend_data=self._update_history('latency', slows),
                                                 severity=COLOR_WARNING if slows > 10 else None)
                if slows > 10: active_alerts.append(f"PERFORMANCE: Degraded latency ({slows} slow requests)")

        # 8. Update Inventory Snapshot
        inventory_res = results.get('inventory', {})
        if inventory_res.get('status') == 'ok':
            inv_data = inventory_res.get('data', {})
            movements = inv_data.get('activity', {}).get('movements_today', 0)
            self.biz_kpis['stock_movements'].update_value(movements, trend_data=self._update_history('movements', movements))

        # 9. Final UI Polish: Health Bar & Alert Panel
        self._update_system_health_ui(active_alerts)

    def _update_history(self, key, value):
        """Track historical values for sparklines (max 20 points)."""
        if key not in self._history:
            self._history[key] = [0] * 20
        self._history[key].append(float(value) if value else 0)
        self._history[key] = self._history[key][-20:]
        return self._history[key]

    def _update_system_health_ui(self, active_alerts):
        """Update the top health bar and alert panel based on active issues."""
        if not active_alerts:
            self.health_status_label.setText("SYSTEM HEALTH: OPTIMAL")
            self.health_status_label.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 11px;")
            self.health_bar.setStyleSheet(self.health_bar.styleSheet().replace("#f38ba8", "#313244").replace("#f9e2af", "#313244"))
            self.alerts_panel.setVisible(False)
        else:
            is_critical = any("CRITICAL" in a or "SYSTEM" in a or "DATABASE" in a for a in active_alerts)
            if is_critical:
                self.health_status_label.setText("SYSTEM HEALTH: CRITICAL FAILURE")
                self.health_status_label.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 11px;")
                self.health_bar.setStyleSheet("background-color: #313244; border-radius: 15px; border: 1px solid #f38ba8;")
            else:
                self.health_status_label.setText("SYSTEM HEALTH: DEGRADED PERFORMANCE")
                self.health_status_label.setStyleSheet("color: #f9e2af; font-weight: bold; font-size: 11px;")
                self.health_bar.setStyleSheet("background-color: #313244; border-radius: 15px; border: 1px solid #f9e2af;")
            
            self.alerts_label.setText("ACTIVE ALERTS: " + " | ".join(active_alerts))
            self.alerts_panel.setVisible(True)

    def _update_intelligence(self, intel_res, signals_res):
        """Update the intelligence list with anomalies and signals, handling failure states."""
        self.intelligence_list.clear()
        
        # 1. Handle Signals (Active Signals)
        if signals_res.get('status') == 'ok':
            signals = signals_res.get('data', [])
            for signal in signals:
                item = QListWidgetItem()
                severity = signal.get('severity', 'INFO')
                color = self._get_severity_color(severity)
                text = f"[{severity}] {signal.get('category', 'SYS')}: {signal.get('message', 'Signal detected')}"
                item.setText(text)
                item.setForeground(QColor(color))
                self.intelligence_list.addItem(item)
        elif signals_res.get('status') == 'unavailable':
            item = QListWidgetItem("[SIGNAL SERVICE UNAVAILABLE]")
            item.setForeground(QColor(COLOR_DANGER))
            self.intelligence_list.addItem(item)

        # 2. Handle Intelligence (Anomalies)
        if intel_res.get('status') == 'ok':
            intel = intel_res.get('data', {})
            anomalies = intel.get('anomalies', [])
            for anomaly in anomalies:
                item = QListWidgetItem()
                item.setText(f"[ANOMALY] {anomaly.get('rule_id', 'RULE')}: {anomaly.get('message', '')}")
                item.setForeground(QColor(COLOR_WARNING))
                self.intelligence_list.addItem(item)
        elif intel_res.get('status') == 'unavailable':
            item = QListWidgetItem("[INTEL SERVICE UNAVAILABLE]")
            item.setForeground(QColor(COLOR_DANGER))
            self.intelligence_list.addItem(item)
                
        if self.intelligence_list.count() == 0:
            self.intelligence_list.addItem("System stable - no anomalies detected")

    def _update_activity_stream(self, ops_res):
        """Update the activity stream (Event Timeline) with severity icons and correlation."""
        self.activity_list.clear()
        
        if ops_res.get('status') == 'ok':
            ops = ops_res.get('data', {})
            alerts = ops.get('alerts', {}).get('recent', [])
            
            # Group events by minute for simple correlation
            groups = {}
            for alert in alerts:
                ts = alert.get('timestamp', '')[11:16] # HH:MM
                if ts not in groups: groups[ts] = []
                groups[ts].append(alert)
                
            for ts, group in sorted(groups.items(), reverse=True):
                # Header for correlated group
                if len(group) > 1:
                    header = QListWidgetItem(f"--- Grouped Events at {ts} ---")
                    header.setForeground(QColor(COLOR_TEXT_MUTED))
                    header.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    self.activity_list.addItem(header)
                
                for alert in group:
                    item = QListWidgetItem()
                    severity = alert.get('severity', 'INFO')
                    color = self._get_severity_color(severity)
                    icon = "ℹ️"
                    if severity == 'CRITICAL': icon = "🚨"
                    elif severity == 'WARNING': icon = "⚠️"
                    
                    text = f"{icon} [{ts}] {alert.get('message', '')}"
                    item.setText(text)
                    item.setForeground(QColor(color))
                    self.activity_list.addItem(item)
        else:
            item = QListWidgetItem("🚨 [OPS SERVICE UNAVAILABLE - STREAM PAUSED]")
            item.setForeground(QColor(COLOR_DANGER))
            self.activity_list.addItem(item)
            
        if self.activity_list.count() == 0 and ops_res.get('status') == 'ok':
            self.activity_list.addItem("No recent activity recorded")

    def _update_jobs(self, jobs_res):
        """Update background jobs table with resilience."""
        if jobs_res.get('status') != 'ok':
            self.jobs_table.setRowCount(1)
            self.jobs_table.setItem(0, 0, QTableWidgetItem("SERVICE DOWN"))
            return

        jobs = jobs_res.get('data', {})
        summary = jobs.get('summary', {})
        self.kpis['active_jobs'].update_value(summary.get('running', 0), "Processing queue")
        
        recent = jobs.get('recent_jobs', [])
        self.jobs_table.setRowCount(len(recent))
        for i, job in enumerate(recent):
            self.jobs_table.setItem(i, 0, QTableWidgetItem(job.get('id', '')[:8]))
            self.jobs_table.setItem(i, 1, QTableWidgetItem(job.get('job_type', '')))
            
            status = job.get('status', '')
            status_item = QTableWidgetItem(status)
            if status == 'COMPLETED': status_item.setForeground(QColor(COLOR_SUCCESS))
            elif status == 'FAILED': status_item.setForeground(QColor(COLOR_DANGER))
            
            self.jobs_table.setItem(i, 2, status_item)
            duration = job.get('duration_seconds', 0)
            self.jobs_table.setItem(i, 3, QTableWidgetItem(f"{duration:.1f}s" if duration else "-"))

    def _update_workflows(self, workflows_res):
        """Update workflow status table with resilience."""
        if workflows_res.get('status') != 'ok':
            self.workflow_table.setRowCount(1)
            self.workflow_table.setItem(0, 0, QTableWidgetItem("SERVICE DOWN"))
            return

        workflows = workflows_res.get('data', [])
        data = workflows
        if isinstance(workflows, dict) and 'results' in workflows:
            data = workflows['results']
            
        self.workflow_table.setRowCount(len(data))
        for i, item in enumerate(data):
            title = f"Request: {item.get('entity_type', 'System')}"
            self.workflow_table.setItem(i, 0, QTableWidgetItem(title))
            
            status = item.get('status', 'PENDING')
            status_item = QTableWidgetItem(status)
            if status == 'PENDING': status_item.setForeground(QColor(COLOR_WARNING))
            elif status == 'APPROVED': status_item.setForeground(QColor(COLOR_SUCCESS))
            
            self.workflow_table.setItem(i, 1, status_item)
            self.workflow_table.setItem(i, 2, QTableWidgetItem(item.get('assigned_to_name', 'System')))
            self.workflow_table.setItem(i, 3, QTableWidgetItem(item.get('created_at', '')[:10]))

    def _update_financials(self, fin_res):
        """Update financial snapshot cards with resilience."""
        if fin_res.get('status') != 'ok':
            for card in self.fin_cards.values():
                card.layout().itemAt(1).widget().setText("UNAVAILABLE")
            return

        fin = fin_res.get('data', {})
        summary = fin.get('balance_summary', {})
        today = fin.get('today_activity', {})
        
        rev = today.get('sales', '0.00')
        self.fin_cards['revenue'].layout().itemAt(1).widget().setText(f"{rev} AFN")
        
        liab = summary.get('total_liabilities', '0.00')
        self.fin_cards['liabilities'].layout().itemAt(1).widget().setText(f"{liab} AFN")
        
        assets = summary.get('total_assets', '0.00')
        self.fin_cards['assets'].layout().itemAt(1).widget().setText(f"{assets} AFN")

    def _handle_error(self, message):
        """Handle fetch errors."""
        self.status_badge.setText("CONNECTION ERROR")
        self.status_badge.setStyleSheet(self.status_badge.styleSheet().replace("#f9e2af", "#f38ba8"))
        self.last_update_label.setText("Retrying connection...")

    def _get_severity_color(self, severity):
        """Map severity string to hex color."""
        s = severity.upper()
        if 'CRITICAL' in s or 'ERROR' in s: return COLOR_DANGER
        if 'WARNING' in s: return COLOR_WARNING
        if 'SUCCESS' in s: return COLOR_SUCCESS
        return COLOR_INFO
