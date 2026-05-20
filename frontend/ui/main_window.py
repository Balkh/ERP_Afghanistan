import sys
import os
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                                 QFrame, QLabel, QStackedWidget, QStatusBar, QApplication, QMessageBox,
                                 QMenuBar, QMenu, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction, QPixmap
from ui.licensing.license_manager_dialog import LicenseManagerDialog
from ui.sidebar import Sidebar
from ui.dashboard import Dashboard
from api.client import APIClient
from security.session_store import clear_session as encrypted_clear_session
from security.auth_manager import AuthManager
from ui.role_renderer import RoleRenderer
from ui.components.notifications import show_warning
from ui.components.loading_spinner import LoadingOverlay
from ui.components.navigation_header import NavigationHeader
from theme.theme_engine import ThemeEngine
from ui.utils.lazy_loader import LazyScreenManager
from utils.logger import get_logger, set_active_screen, get_active_screen, safe_execute, SafeBoundary, capture_health_snapshot, DiagnosticContext, generate_correlation_id, record_screen_load, record_error, detect_error_bursts, generate_operational_insight_report, emit_event
from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG, TEXT_BODY, TEXT_LABEL, TEXT_PAGE_TITLE, TEXT_TABLE)
from ui.constants import TEXT_PAGE_TITLE, TEXT_LABEL, TEXT_TABLE

log = get_logger('ui')
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BORDER_FOCUS, COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
import ui.constants as _constants

from runtime.timer_registry import shutdown_all_timers

class MainWindow(QMainWindow):
    def __init__(self, license_validator=None, user_data: dict = None, api_client=None, auth_manager=None):
        super().__init__()
        self.setWindowTitle("Pharmacy ERP")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Store license validator
        self.license_validator = license_validator
        
        # Initialize AuthManager (primary auth state source)
        self.auth_manager = auth_manager or AuthManager(api_client)
        
        # Sync user_data into auth_manager if provided from login
        if user_data:
            self.auth_manager._user_data = user_data
            self.auth_manager._roles = user_data.get("roles", [])
            self.auth_manager._ui_scopes = user_data.get("ui_scopes", self.auth_manager._ui_scopes)
            self.auth_manager._is_authenticated = True
        
        # Store user_data for backward compatibility
        self.user_data = self.auth_manager.user or user_data or {}
        self.user_role = self._determine_role()
        
        # Initialize API client
        self.api_client = api_client if api_client else self.auth_manager.api_client
        
        # Initialize RoleRenderer (sidebar set after _build_ui)
        self.role_renderer = RoleRenderer(
            auth_manager=self.auth_manager,
            sidebar=None,  # Set after sidebar creation
            main_window=self,
        )
        
        # Initialize unified theme engine (single source of truth)
        self.theme_engine = ThemeEngine.instance()
        self.theme_engine.theme_changed.connect(self.on_theme_changed)
        
        # --- Navigation System (Phase 4-5) ---
        self.navigation_history = []  # Stack of visited pages
        self._max_history = 20      # Limit history size
        self._disable_history = False  # For history navigation itself
        
        # Connect license validator signals if validator is provided
        if self.license_validator:
            self.license_validator.license_valid.connect(self.on_license_validation_changed)
            self.license_validator.license_status_changed.connect(self.on_license_status_changed)
        
        log.debug(f"User role: {self.user_role}",
                   extra={'extra_fields': {'tags': ['auth', 'startup']}})
        
        # Build the UI
        self._build_ui()
        self._setup_status_bar()
        self._load_company_settings()
        try:
            hs = capture_health_snapshot()
            log.debug(f"MainWindow health snapshot: {hs}",
                       extra={'extra_fields': {'tags': ['ui', 'startup', 'diagnostic']}})
        except Exception:
            pass

    def _setup_status_bar(self):
        """Setup the professional status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connection status
        self.conn_label = QLabel("● Connected")
        self.conn_label.setStyleSheet(f"color: {COLOR_SUCCESS}; margin-right: 15px; font-weight: bold;")
        
        # User info
        user_name = self.user_data.get('full_name', self.user_data.get('username', 'User'))
        self.user_label = QLabel(f"👤 User: {user_name} ({self.user_role.name})")
        self.user_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; margin-right: 15px;")
        
        # System time
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; margin-right: 15px;")
        
        # Timer to update time
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_bar_time)
        self.status_timer.start(1000)
        self._update_status_bar_time()
        
        self.health_label = QLabel("● Checking...")
        self.health_label.setStyleSheet(f"color: {COLOR_WARNING}; margin-right: 15px; font-weight: bold;")
        self.health_label.setToolTip("Backend health status")

        self.status_bar.addPermanentWidget(self.user_label)
        self.status_bar.addPermanentWidget(self.health_label)
        self.status_bar.addPermanentWidget(self.conn_label)
        self.status_bar.addPermanentWidget(self.time_label)

        QTimer.singleShot(2000, self._check_startup_health)

    def _check_startup_health(self):
        """Run startup health check and update status bar."""
        try:
            is_reachable = self.api_client.health_check()
            if is_reachable:
                health_data = self.api_client.get("/api/health/")
                if isinstance(health_data, dict):
                    data = health_data.get('data', health_data)
                    db = data.get('database', {})
                    db_status = db.get('status', 'unknown')
                    if db_status == 'healthy':
                        self.health_label.setText("● DB OK")
                        self.health_label.setStyleSheet(f"color: {COLOR_SUCCESS}; margin-right: 15px; font-weight: bold;")
                        self.status_bar.showMessage("Startup: all systems healthy", 3000)
                        log.info("Startup health: all systems healthy",
                                 extra={'extra_fields': {'tags': ['system', 'startup']}})
                    else:
                        self.health_label.setText(f"● DB {db_status.upper()}")
                        self.health_label.setStyleSheet(f"color: {COLOR_DANGER}; margin-right: 15px; font-weight: bold;")
                        self.status_bar.showMessage(f"Startup: DB status {db_status}", 5000)
                        log.warning(f"Startup health: DB status {db_status}",
                                     extra={'extra_fields': {'tags': ['system', 'startup', 'warning']}})
                else:
                    self.health_label.setText("● Online")
                    self.health_label.setStyleSheet(f"color: {COLOR_SUCCESS}; margin-right: 15px; font-weight: bold;")
                    log.info("Startup health: backend online",
                             extra={'extra_fields': {'tags': ['system', 'startup']}})
            else:
                self.health_label.setText("● Offline")
                self.health_label.setStyleSheet(f"color: {COLOR_DANGER}; margin-right: 15px; font-weight: bold;")
                log.warning("Startup health: backend unreachable",
                             extra={'extra_fields': {'tags': ['system', 'startup', 'warning']}})
        except Exception as e:
            self.health_label.setText("● Error")
            self.health_label.setStyleSheet(f"color: {COLOR_DANGER}; margin-right: 15px; font-weight: bold;")
            _cid = generate_correlation_id("health")
            record_error(exc_type=type(e).__name__, module='startup_health', category='api')
            emit_event('system_event', module='main_window', action='health_check_error',
                       metadata={'error': str(e), 'screen': get_active_screen()},
                       correlation_id=_cid)
            log.warning(f"Startup health check error: {e}",
                         extra={'extra_fields': {'tags': ['system', 'startup', 'error']}})

    def _update_status_bar_time(self):
        from datetime import datetime
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _load_company_settings(self):
        """Load company name to window title."""
        from ui.system.settings_screen import SETTINGS_FILE
        import json
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    company = settings.get("company_name")
                    if company:
                        self.setWindowTitle(f"{company} - Pharmacy ERP")
            except Exception as e:
                log.debug(f"Could not load company settings: {e}",
                           extra={'extra_fields': {'tags': ['ui', 'startup']}})
    
    def _determine_role(self):
        """Determine user role from user_data."""
        from ui.role_manager import get_role_from_user_data, UserRole
        role = get_role_from_user_data(self.user_data)
        return role

    def _on_ui_scopes_changed(self, ui_scopes: dict) -> None:
        """Handle ui_scopes update from AuthManager (e.g., after login or role change)."""
        if hasattr(self, 'role_renderer'):
            self.role_renderer.apply_scopes()
        if hasattr(self, 'sidebar'):
            self._apply_sidebar_scopes(ui_scopes)
        self._update_status_bar_user_info()

    def _apply_sidebar_scopes(self, ui_scopes: dict) -> None:
        """Hide sidebar items the user cannot access based on ui_scopes."""
        visible_modules = set(ui_scopes.get("sidebar", []))
        hidden_modules = set(ui_scopes.get("hidden", []))

        group_items_map = {
            "inventory": {"inventory"},
            "sales": {"sales"},
            "purchases": {"purchases"},
            "returns": {"returns"},
            "accounting": {"accounting"},
            "reports": {"reports"},
            "finance": {"finance"},
            "hr": {"hr"},
            "hr_reports": {"hr"},
            "payroll_reports": {"hr"},
            "system": {"system"},
        }

        for group_name, group_widget in self.sidebar._group_widgets.items():
            group_modules = group_items_map.get(group_name, set())
            any_visible = any(mod in visible_modules for mod in group_modules)
            header_frame = getattr(self.sidebar, f"_{group_name}_header", None)
            if header_frame:
                header_frame.setVisible(any_visible)
            if group_widget:
                group_widget.setVisible(any_visible)

        # Dashboard button always visible
        if hasattr(self.sidebar, 'dashboard_btn'):
            self.sidebar.dashboard_btn.setVisible(True)

    def _update_status_bar_user_info(self) -> None:
        """Update status bar with current user info from auth_manager."""
        user = self.auth_manager.user or self.user_data
        user_name = user.get('username', user.get('full_name', 'User'))
        roles = self.auth_manager.roles or [self.user_role.name]
        role_display = roles[0] if roles else self.user_role.name
        if hasattr(self, 'user_label'):
            self.user_label.setText(f"👤 User: {user_name} ({role_display})")

    def _build_ui(self):
        """Build the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Outer vertical layout: global bar on top, content below
        self._outer_layout = QVBoxLayout(central_widget)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(SPACING_NONE)

        # Global Intelligence Bar
        from ui.cognitive.global_bar import GlobalIntelligenceBar
        self.cognitive_bar = GlobalIntelligenceBar(api_client=self.api_client)
        self.cognitive_bar.anomaly_clicked.connect(
            lambda: self.anomaly_warning_center.show() if hasattr(self, 'anomaly_warning_center') else None
        )
        self.cognitive_bar.anomaly_clicked.connect(
            lambda: self.navigate_to("anomaly_warning_center")
        )
        self._outer_layout.addWidget(self.cognitive_bar)

        # Inner horizontal layout: sidebar + content
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(SPACING_NONE)
        self._outer_layout.addLayout(main_layout)
        
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add device ID label to status bar
        self.device_id_label = QLabel()
        self.device_id_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_TEXT_MUTED};")
        self.status_bar.addPermanentWidget(self.device_id_label)

        # Add license status label to status bar
        self.license_status_label = QLabel()
        self.license_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_TEXT_MUTED}; margin-left: 10px;")
        self.status_bar.addPermanentWidget(self.license_status_label)
        
        # Add connection status label to status bar
        self.connection_status_label = QLabel()
        self.connection_status_label.setStyleSheet(f"font-size: {TEXT_TABLE}px; color: {COLOR_TEXT_MUTED}; margin-left: 10px;")
        self.status_bar.addPermanentWidget(self.connection_status_label)
        
        # Connection check timer (throttled to reduce UI thread pressure)
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(30000)

        self.check_connection()
        self.update_device_id_display()
        self.create_menu_bar()
        
        # Update license status display
        self.update_license_status_display()

        # Create sidebar with role-based navigation
        self.sidebar = Sidebar(role=self.user_role)
        main_layout.addWidget(self.sidebar)

        # Wire RoleRenderer to sidebar
        self.role_renderer.sidebar = self.sidebar
        self.role_renderer.apply_scopes()

        content_frame = QFrame()
        content_frame.setFrameStyle(QFrame.NoFrame)
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QGroupBox {{
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_LG};
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM}px {SPACING_XL}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
            QPushButton:focus {{
                border: 2px solid {COLOR_BORDER_FOCUS};
                outline: none;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_SM}px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {COLOR_BORDER_FOCUS};
            }}
            QScrollArea {{
                background-color: transparent;
            }}
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(MARGIN_PAGE, SPACING_SM, MARGIN_PAGE, SPACING_MD)
        content_layout.setSpacing(SPACING_MD + SPACING_XS)
        content_layout.addStretch(1)  # Make content expand to fill available space

        self.header = QLabel("Pharmacy ERP Dashboard")
        self.header.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setFixedHeight(60)
        self.header.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                padding-left: 10px;
            }}
        """)
        content_layout.addWidget(self.header)
        
        # --- Navigation Header Component (Phase 3) ---
        self.nav_header = NavigationHeader()
        self.nav_header.setVisible(False)  # Hidden on dashboard
        self.nav_header.back_clicked.connect(self._go_back)
        self.nav_header.home_clicked.connect(self._go_home)
        self.nav_header.close_clicked.connect(self._close_screen)
        content_layout.addWidget(self.nav_header)

        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.pages)

        # 0: Dashboard (always loaded first)
        self.dashboard = Dashboard(role=self.user_role, api_client=self.api_client)
        self.pages.addWidget(self.dashboard)

        # ── Lazy Screen Registration ─────────────────────────────────
        # Screens are registered with factory functions that are called
        # on first navigation. This avoids 57+ widget trees at startup.
        self._lazy_screens = LazyScreenManager(self.pages, self.api_client)

        def _register(index, builder, label="Loading..."):
            self._lazy_screens.register(index, builder, label)

        def _b(getter):
            return lambda api_client=None, **kw: getter(api_client=api_client)

        # Indices 1-9: Inventory & Sales
        from ui.inventory.product_screen import ProductScreen
        from ui.inventory.category_screen import CategoryScreen
        from ui.inventory.warehouse_screen import WarehouseScreen
        from ui.inventory.batch_screen import BatchScreen
        from ui.sales.sales_invoice_screen import SalesInvoiceScreen
        from ui.pos.pos_screen import POSScreen
        from ui.sales.customer_screen import CustomerScreen
        from ui.purchases.purchase_invoice_screen import PurchaseInvoiceScreen
        from ui.purchases.supplier_screen import SupplierScreen
        from ui.returns.returns_screen import ReturnsScreen
        from ui.returns.reconciliation_screen import ReconciliationScreen
        _register(1, _b(ProductScreen))
        _register(2, _b(CategoryScreen))
        _register(3, _b(WarehouseScreen))
        _register(4, _b(BatchScreen))
        _register(5, lambda api_client=None: SalesInvoiceScreen(api_client=api_client, auth_manager=self.auth_manager))
        _register(6, lambda api_client=None: PurchaseInvoiceScreen(api_client=api_client, auth_manager=self.auth_manager))
        _register(7, _b(CustomerScreen))
        _register(8, _b(SupplierScreen))
        _register(9, _b(ReturnsScreen))
        _register(10, lambda api_client=None: POSScreen(api_client=api_client, auth_manager=self.auth_manager))

        # Indices 10-17: Accounting
        from ui.accounting.chart_of_accounts_screen import ChartOfAccountsScreen
        from ui.accounting.journal_entry_screen import JournalEntryScreen
        from ui.accounting.account_ledger_screen import AccountLedgerScreen
        _register(10, lambda api_client=None: ChartOfAccountsScreen())
        _register(11, lambda api_client=None: JournalEntryScreen())
        _register(12, lambda api_client=None: AccountLedgerScreen())
        from ui.accounting.report_browser import ReportBrowser
        _register(13, lambda api_client=None: ReportBrowser(report_type="trial_balance"))
        _register(14, lambda api_client=None: ReportBrowser(report_type="profit_loss"))
        _register(15, lambda api_client=None: ReportBrowser(report_type="balance_sheet"))
        _register(16, lambda api_client=None: ReportBrowser(report_type="ar_aging"))
        _register(17, lambda api_client=None: ReportBrowser(report_type="ap_aging"))

        # Indices 18-22: Finance
        from ui.finance.payment_screen import PaymentScreen
        from ui.finance.expense_screen import ExpenseScreen
        from ui.finance.budgeting_screen import BudgetingScreen
        from ui.finance.tax_screen import TaxScreen
        from ui.finance.cost_centers_screen import CostCentersScreen
        from ui.finance.cashflow_screen import CashflowScreen
        _register(18, _b(PaymentScreen))
        _register(19, _b(BudgetingScreen))
        _register(20, _b(TaxScreen))
        _register(21, _b(CostCentersScreen))
        _register(22, _b(CashflowScreen))
        _register(34, _b(ExpenseScreen))

        # Indices 23-26: HR
        from ui.hr.employee_screen import EmployeeScreen
        from ui.hr.attendance_screen import AttendanceScreen
        from ui.hr.leave_screen import LeaveScreen
        from ui.hr.payroll_screen import PayrollScreen
        _register(23, _b(EmployeeScreen))
        _register(24, _b(AttendanceScreen))
        _register(25, _b(LeaveScreen))
        _register(26, _b(PayrollScreen))

        # Indices 27-39: System (consolidated)
        from ui.system.backup_screen import BackupScreen
        from ui.system.settings_screen import SettingsScreen
        from ui.system.fixed_assets_screen import FixedAssetsScreen
        from ui.system.audit_screen import AuditScreen
        from ui.system.user_management_screen import UserManagementScreen
        from ui.system.invoice_template_manager import InvoiceTemplateManager
        from ui.system.entity_management_screen import EntityManagementScreen
        from ui.system.licensing_screen import LicensingScreen
        from ui.system.production_screen import ProductionScreen
        from ui.system.analytics_workspace import AnalyticsWorkspace
        from ui.system.intelligence_hub_screen import IntelligenceHubScreen
        from ui.control_tower.operations_dashboard import OperationsDashboard
        from ui.observability.observability_console import ObservabilityConsole
        from ui.causal_scoring.decision_workspace import DecisionWorkspace
        _register(27, _b(BackupScreen))
        _register(28, _b(SettingsScreen))
        _register(29, _b(FixedAssetsScreen))
        _register(30, _b(AuditScreen))
        _register(31, _b(UserManagementScreen))
        _register(32, _b(IntelligenceHubScreen))
        _register(33, _b(InvoiceTemplateManager))
        _register(35, _b(EntityManagementScreen))
        _register(36, _b(LicensingScreen))
        _register(37, _b(ProductionScreen))
        _register(38, lambda api_client=None: OperationsDashboard(api_client=api_client))
        _register(39, lambda api_client=None: ObservabilityConsole(api_client=api_client))

        # Indices 40-47: Intelligence / Autonomous (consolidated into workspaces)
        _register(40, lambda api_client=None: AnalyticsWorkspace(api_client=api_client))
        _register(41, lambda api_client=None: AnalyticsWorkspace(api_client=api_client))
        _register(42, lambda api_client=None: AnalyticsWorkspace(api_client=api_client))
        _register(43, lambda api_client=None: OperationsDashboard(api_client=api_client))
        _register(44, lambda api_client=None: ObservabilityConsole(api_client=api_client))
        _register(45, lambda api_client=None: OperationsDashboard(api_client=api_client))
        _register(46, lambda api_client=None: DecisionWorkspace(api_client=api_client))
        _register(47, lambda api_client=None: DecisionWorkspace(api_client=api_client))

        # Indices 48-56: Reports (consolidated)
        from ui.accounting.report_browser import ReportBrowser
        _register(48, lambda api_client=None: ReportBrowser(report_type="cash_flow"))
        _register(49, lambda api_client=None: ReportBrowser(report_type="employee_summary"))
        _register(50, lambda api_client=None: ReportBrowser(report_type="attendance_report"))
        _register(51, lambda api_client=None: ReportBrowser(report_type="leave_report"))
        _register(52, lambda api_client=None: ReportBrowser(report_type="overtime_report"))
        _register(53, lambda api_client=None: ReportBrowser(report_type="payroll_summary"))
        _register(54, lambda api_client=None: ReportBrowser(report_type="payroll_trend"))
        _register(55, lambda api_client=None: ReportBrowser(report_type="payroll_dept_cost"))
        _register(56, lambda api_client=None: ReportBrowser(report_type="payroll_emp_history"))
        _register(57, _b(ReconciliationScreen))

        # Index 58: Financial Integrity
        from ui.accounting.financial_integrity_screen import FinancialIntegrityScreen
        _register(58, lambda api_client=None: FinancialIntegrityScreen())

        # Index 59: Financial Audit Log
        from ui.accounting.financial_audit_log_screen import FinancialAuditLogScreen
        _register(59, lambda api_client=None: FinancialAuditLogScreen())

        # Phase 20: Financial Operations Cohesion
        # Index 60: Customer Payment Workspace
        from ui.finance.customer_payment_workspace import CustomerPaymentWorkspace
        _register(60, _b(CustomerPaymentWorkspace))

        # Index 61: Supplier Payment Workspace
        from ui.finance.supplier_payment_workspace import SupplierPaymentWorkspace
        _register(61, _b(SupplierPaymentWorkspace))

        # Index 62: Payment Allocation Explorer
        from ui.finance.payment_allocation_explorer import PaymentAllocationExplorer
        _register(62, _b(PaymentAllocationExplorer))

        # Index 63: Returns Explainability
        from ui.finance.returns_explainability import ReturnsExplainabilityScreen
        _register(63, _b(ReturnsExplainabilityScreen))

        # Index 64: Journal Reversal Explorer
        from ui.finance.journal_reversal_explorer import JournalReversalExplorer
        _register(64, _b(JournalReversalExplorer))

        # Index 65: Financial Operations Console
        from ui.finance.financial_operations_console import FinancialOperationsConsole
        _register(65, lambda api_client=None: FinancialOperationsConsole(api_client=api_client))

        main_layout.addWidget(content_frame, 1)

        self.sidebar.page_changed.connect(self.change_page)
        self.sidebar.set_active_item(0)
        
        # Update device ID display in status bar
        self.update_device_id_display()
        self.update_license_status_display()

    def change_page(self, index, page_title):
        """Change the current page based on sidebar selection."""
        # Check ui_scopes — deny if user doesn't have access
        page_to_module = {
            0: "dashboard",
            1: "inventory", 2: "inventory", 3: "inventory", 4: "inventory",
            5: "sales", 6: "purchases", 7: "sales", 8: "purchases",
            9: "returns",
            10: "accounting", 11: "accounting", 12: "accounting", 58: "accounting", 59: "accounting",
            13: "reports", 14: "reports", 15: "reports", 16: "reports", 17: "reports",
            18: "finance", 19: "finance", 20: "finance", 21: "finance", 22: "finance", 34: "finance",
            60: "finance", 61: "finance", 62: "finance", 63: "finance", 64: "finance", 65: "finance",
            23: "hr", 24: "hr", 25: "hr", 26: "hr",
            49: "hr", 50: "hr", 51: "hr", 52: "hr",
            53: "hr", 54: "hr", 55: "hr", 56: "hr",
            27: "system", 28: "system", 29: "system", 30: "system", 31: "system",
            32: "system", 33: "system", 35: "system", 36: "system", 37: "system",
            38: "system", 39: "system", 47: "system",
            48: "reports",
        }
        module = page_to_module.get(index, "dashboard")
        if not self.auth_manager.has_access(module):
            show_warning(f"Access denied: you don't have permission to view {page_title.strip()}")
            return

        _start = time.time()
        _corr = generate_correlation_id("nav")
        log.debug(f"Navigate to page {index}: {page_title.strip()}",
                   extra={'extra_fields': {'tags': ['ui', 'navigation']}})
        set_active_screen(page_title.strip())
        emit_event('navigation_event', module='main_window',
                   action=page_title.strip(), correlation_id=_corr)
# --- Navigation History (Phase 4) ---
        if not self._disable_history:
            current = self.pages.currentIndex()
            if current != index:
                if not self.navigation_history or self.navigation_history[-1][0] != current:
                    self.navigation_history.append((current, page_title.strip()))
                    if len(self.navigation_history) > self._max_history:
                        self.navigation_history = self.navigation_history[-self._max_history:]

        # Lazy-load screen if not yet instantiated
        if index != 0 and hasattr(self, '_lazy_screens'):
            screen = self._lazy_screens.load(index)
            if screen is None and index == 0:
                pass

        self.header.setText(page_title.strip())
        self.header.setVisible(False)
        self.pages.setCurrentIndex(index)
        self._update_nav_header(index, page_title)

        corr_id = generate_correlation_id("nav")
        _load_map = {
            1: ("load_products", "products"),
            2: ("load_categories", "categories"),
            3: ("load_warehouses", "warehouses"),
            4: ("load_batches", "batches"),
            7: ("load_customers", "customers"),
            8: ("load_suppliers", "suppliers"),
            11: ("load_entries", "journal_entries"),
            12: ("load_accounts", "account_ledger"),
            34: ("load_expenses", "expenses"),
            35: ("load_entities", "entities"),
            36: ("load_license_info", "licensing"),
        }
        if index in _load_map:
            method_name, tag = _load_map[index]
            screen = self._lazy_screens.get(index) if hasattr(self, '_lazy_screens') else None
            if screen and hasattr(screen, method_name):
                safe_execute(getattr(screen, method_name),
                             log_context=f"change_page:{tag}", tags=['ui', 'navigation', corr_id])

        _duration = (time.time() - _start) * 1000
        record_screen_load(page_title.strip(), _duration)

    # --- Navigation Methods (Phase 5-6) ---
    def _update_nav_header(self, index: int, page_title: str):
        """Update navigation header visibility and state."""
        # Show nav header except on dashboard
        show_nav = (index != 0)
        self.nav_header.setVisible(show_nav)
        self.header.setVisible(not show_nav)  # Hide old header when nav header shown
        
        if show_nav:
            self.nav_header.set_title(page_title)
            # Enable back if history exists
            has_history = bool(self.navigation_history)
            self.nav_header.set_back_enabled(has_history)
            # Set breadcrumb
            breadcrumb = self._build_breadcrumb(index, page_title)
            self.nav_header.set_breadcrumb(breadcrumb)
    
    def _build_breadcrumb(self, index: int, page_title: str) -> list:
        """Build breadcrumb path from current screen."""
        page_map = {
            0: "Home",
            1: "Products", 2: "Categories", 3: "Warehouses", 4: "Batches",
            5: "Sales Invoice", 6: "Purchase Invoice", 7: "Customers", 8: "Suppliers",
            9: "Returns",
            10: "Chart of Accounts", 11: "Journal Entries", 12: "Account Ledger",
            13: "Trial Balance", 14: "Profit & Loss", 15: "Balance Sheet",
            16: "AR Ageing", 17: "AP Ageing",
            18: "Payments", 19: "Budgeting", 20: "Tax", 21: "Cost Centers", 22: "Cash Flow",
            23: "Employees", 24: "Attendance", 25: "Leave", 26: "Payroll",
            27: "Backup", 28: "Settings", 29: "Fixed Assets", 30: "Audit",
            31: "User Management", 32: "Intelligence Hub", 33: "Invoice Templates",
            34: "Expenses", 35: "Entities", 36: "Licensing", 37: "Production",
            38: "Control Center",
            39: "Observability",
            57: "Reconciliation",
        }
        
        # Build breadcrumb based on current page category
        if index in [1, 2, 3, 4]:
            return ["Home", "Inventory", page_map.get(index, page_title)]
        elif index in [5, 7]:
            return ["Home", "Sales", page_map.get(index, page_title)]
        elif index in [6, 8]:
            return ["Home", "Purchases", page_map.get(index, page_title)]
        elif index in [10, 11, 12]:
            return ["Home", "Accounting", page_map.get(index, page_title)]
        elif index in [13, 14, 15, 16, 17]:
            return ["Home", "Reports", page_map.get(index, page_title)]
        elif index in [18, 19, 20, 21, 22, 34]:
            return ["Home", "Finance", page_map.get(index, page_title)]
        elif index in [23, 24, 25, 26]:
            return ["Home", "HR", page_map.get(index, page_title)]
        elif index in [27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39]:
            return ["Home", "System", page_map.get(index, page_title)]
        elif index in [9, 57]:
            return ["Home", "Returns", page_map.get(index, page_title)]
        else:
            return ["Home", page_map.get(index, page_title)]
    
    def _go_back(self):
        """Navigate back in history."""
        with SafeBoundary(log_context="go_back", tags=['ui', 'navigation']):
            self._do_go_back()

    def _do_go_back(self):
        """Inner implementation of back navigation."""
        if self.navigation_history:
            prev_index, prev_title = self.navigation_history.pop()
            self._disable_history = True
            self.pages.setCurrentIndex(prev_index)
            self.header.setText(prev_title)
            self._disable_history = False
            current_idx = self.pages.currentIndex()
            self._update_nav_header(current_idx, prev_title)
    
    def _go_home(self):
        """Navigate to dashboard (home)."""
        with SafeBoundary(log_context="go_home", tags=['ui', 'navigation']):
            self._do_go_home()

    def _do_go_home(self):
        """Inner implementation of home navigation."""
        self._disable_history = True
        self.pages.setCurrentIndex(0)
        self.header.setText("Pharmacy ERP Dashboard")
        self._disable_history = False
        self._update_nav_header(0, "Pharmacy ERP Dashboard")
    
    def _close_screen(self):
        """Close current screen and return to previous or home."""
        # If history exists, go back
        if self.navigation_history:
            self._go_back()
        else:
            # Otherwise go home
            self._go_home()

    def update_device_id_display(self):
        """Update the device ID display in the status bar."""
        device_id = QApplication.instance().property("deviceId")
        if device_id:
            self.device_id_label.setText(f"Device ID: {device_id}")
        else:
            self.device_id_label.setText("Device ID: Not available")

    def update_license_status_display(self):
        """Update the license status display in the status bar."""
        if self.license_validator:
            status = self.license_validator.get_license_status()
            if status["is_valid"]:
                self.license_status_label.setText(f"License: Valid ({status['message']})")
                self.license_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_SUCCESS}; margin-left: 10px;")  # Green
            else:
                self.license_status_label.setText(f"License: Invalid ({status['message']})")
                self.license_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_DANGER}; margin-left: 10px;")  # Red

    def check_connection(self):
        """Check the connection to the backend and update the status bar."""
        try:
            if not self.connection_status_label or not self.connection_status_label.isVisible():
                return
            is_reachable = self.api_client.health_check()
            if is_reachable:
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_SUCCESS}; margin-left: 10px;")
            else:
                self.connection_status_label.setText("Disconnected")
                self.connection_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_DANGER}; margin-left: 10px;")
        except (RuntimeError, AttributeError) as e:
            log.debug(f"Connection check failed (expected during shutdown): {e}",
                       extra={'extra_fields': {'tags': ['ui', 'connection']}})

    def on_license_validation_changed(self, is_valid: bool, message: str):
        """Handle license validation change signals."""
        if is_valid:
            self.license_status_label.setText(f"License: Valid ({message})")
            self.license_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_SUCCESS}; margin-left: 10px;")  # Green
        else:
            self.license_status_label.setText(f"License: Invalid ({message})")
            self.license_status_label.setStyleSheet(f"font-size: {TEXT_LABEL}px; color: {COLOR_DANGER}; margin-left: 10px;")  # Red
            
            # Show critical error message if validation fails
            if not is_valid and "too many times" in message:
                QMessageBox.critical(
                    self,
                    "License Validation Failed",
                    f"The application license has failed validation too many times:\n\n{message}\n\n"
                    "The application will now exit.",
                    QMessageBox.Ok
                )
                # Close the application
                self.close()

    def on_license_status_changed(self, message: str):
        """Handle license status change signals."""
        # Update the status bar with the message
        self.status_bar.showMessage(message, 5000)  # Show for 5 seconds

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        engine = ThemeEngine.instance()
        engine.toggle()

    def on_theme_changed(self, theme_name):
        """Handle theme change — update constants and re-apply stylesheets."""
        _cid = generate_correlation_id("theme")
        engine = ThemeEngine.instance()
        if engine.current_theme() != theme_name:
            engine.apply_theme(theme_name)
        self._refresh_window_styles()
        self.status_bar.showMessage(f"Switched to {theme_name} mode", 2000)
        try:
            hs = capture_health_snapshot()
            log.info(f"Theme switched to {theme_name} | snapshot: {hs}",
                      extra={'extra_fields': {'tags': ['ui', 'theme', 'diagnostic']}})
        except Exception:
            log.info(f"Theme switched to {theme_name}",
                      extra={'extra_fields': {'tags': ['ui', 'theme']}})
        emit_event('ui_action', module='main_window',
                   action=f'theme_switch:{theme_name}',
                   metadata={'snapshot': hs if 'hs' in dir() else {}},
                   correlation_id=_cid)

    def _refresh_window_styles(self):
        """Re-apply the content-frame stylesheet after a theme switch."""
        with SafeBoundary(log_context="refresh_window_styles", tags=['ui', 'theme']):
            self._do_refresh_window_styles()

    def _do_refresh_window_styles(self):
        """Inner implementation of stylesheet refresh with safe boundary."""
        if not hasattr(self, 'pages'):
            return
        C = _constants
        content_frame = self.sidebar.parent() if hasattr(self, 'sidebar') else None
        for child in self.findChildren(QFrame):
            if child.parent() is self.centralWidget():
                content_frame = child
                break
        if content_frame:
            content_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {C.COLOR_BG_MAIN};
                }}
                QLabel {{
                    color: {C.COLOR_TEXT_PRIMARY};
                }}
                QGroupBox {{
                    color: {C.COLOR_TEXT_PRIMARY};
                    font-weight: bold;
                    border: 1px solid {C.COLOR_BORDER};
                    border-radius: {C.BORDER_RADIUS_LG};
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                }}
                QPushButton {{
                    background-color: {C.COLOR_PRIMARY};
                    color: {C.COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {C.BORDER_RADIUS_MD};
                    padding: {C.SPACING_SM}px {C.SPACING_XL}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {C.COLOR_PRIMARY_HOVER};
                }}
                QPushButton:focus {{
                    border: 2px solid {C.COLOR_BORDER_FOCUS};
                    outline: none;
                }}
                QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                    background-color: {C.COLOR_BG_SURFACE};
                    color: {C.COLOR_TEXT_PRIMARY};
                    border: 1px solid {C.COLOR_BORDER};
                    border-radius: {C.BORDER_RADIUS_MD};
                    padding: {C.SPACING_SM}px;
                }}
                QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                    border: 2px solid {C.COLOR_BORDER_FOCUS};
                }}
                QScrollArea {{
                    background-color: transparent;
                }}
            """)
        self._refresh_status_bar()

    def _refresh_status_bar(self):
        """Re-apply status bar label colors on theme change."""
        C = _constants
        for attr, ss in [
            ('user_label', f"color: {C.COLOR_TEXT_SECONDARY}; margin-right: 15px;"),
            ('conn_label', f"color: {C.COLOR_STATUS_VALID}; margin-right: 15px; font-weight: bold;"),
            ('time_label', f"color: {C.COLOR_TEXT_SECONDARY}; margin-right: 15px;"),
            ('device_id_label', f"font-size: {C.TEXT_LABEL}px; color: {C.COLOR_TEXT_MUTED};"),
            ('license_status_label', f"font-size: {C.TEXT_LABEL}px; color: {C.COLOR_TEXT_MUTED}; margin-left: 10px;"),
            ('connection_status_label', f"font-size: {C.TEXT_LABEL}px; color: {C.COLOR_TEXT_MUTED}; margin-left: 10px;"),
        ]:
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    widget.setStyleSheet(ss)
                except RuntimeError:
                    pass
        self.header.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                padding-left: 10px;
            }}
        """)
        self.nav_header.setStyleSheet(f"""
            QWidget {{ background-color: transparent; }}
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_6}px 10px;
                font-size: {TEXT_BODY}px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BORDER};
            }}
            QPushButton:disabled {{
                color: {COLOR_BORDER_LIGHT};
                border: 1px solid {COLOR_BG_ELEVATED};
            }}
            QLabel {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.nav_header.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.nav_header.breadcrumb_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Refresh action
        refresh_action = QAction('Refresh', self)
        refresh_action.setStatusTip('Refresh current view')
        refresh_action.triggered.connect(self.refresh_current_view)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # Logout action
        logout_action = QAction('Logout', self)
        logout_action.setStatusTip('Logout and return to login')
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        # Add Preferences action
        preferences_action = QAction('Preferences', self)
        preferences_action.setStatusTip('Open application preferences')
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Add fullscreen toggle
        fullscreen_action = QAction('Toggle Fullscreen', self)
        fullscreen_action.setStatusTip('Toggle fullscreen mode')
        fullscreen_action.setShortcut('F11')
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        view_menu.addSeparator()
        
        # Add navigation shortcuts
        nav_dashboard = QAction('Go to Dashboard', self)
        nav_dashboard.setShortcut('Ctrl+1')
        nav_dashboard.triggered.connect(lambda: self.navigate_to("dashboard"))
        view_menu.addAction(nav_dashboard)
        
        nav_products = QAction('Go to Products', self)
        nav_products.setShortcut('Ctrl+2')
        nav_products.triggered.connect(lambda: self.navigate_to("products"))
        view_menu.addAction(nav_products)
        
        nav_customers = QAction('Go to Customers', self)
        nav_customers.setShortcut('Ctrl+3')
        nav_customers.triggered.connect(lambda: self.navigate_to("customers"))
        view_menu.addAction(nav_customers)
        
        # Operations menu
        operations_menu = menubar.addMenu('Operations')
        
        # Add new product
        new_product_action = QAction('New Product', self)
        new_product_action.setStatusTip('Create a new product')
        new_product_action.setShortcut('Ctrl+N')
        new_product_action.triggered.connect(self.new_product)
        operations_menu.addAction(new_product_action)
        
        # Add new invoice
        new_invoice_action = QAction('New Sales Invoice', self)
        new_invoice_action.setStatusTip('Create a new sales invoice')
        new_invoice_action.setShortcut('Ctrl+Shift+S')
        new_invoice_action.triggered.connect(lambda: self.navigate_to("sales_invoice"))
        operations_menu.addAction(new_invoice_action)
        
        operations_menu.addSeparator()
        
        # Add inventory check
        inventory_check_action = QAction('Stock Alert Report', self)
        inventory_check_action.setStatusTip('View low stock items')
        inventory_check_action.triggered.connect(self.show_stock_alerts)
        operations_menu.addAction(inventory_check_action)
        
        # Reports menu
        reports_menu = menubar.addMenu('Reports')
        
        # Add quick report links
        trial_balance_action = QAction('Trial Balance', self)
        trial_balance_action.triggered.connect(lambda: self.navigate_to("trial_balance"))
        reports_menu.addAction(trial_balance_action)
        
        profit_loss_action = QAction('Profit & Loss', self)
        profit_loss_action.triggered.connect(lambda: self.navigate_to("profit_loss"))
        reports_menu.addAction(profit_loss_action)
        
        balance_sheet_action = QAction('Balance Sheet', self)
        balance_sheet_action.triggered.connect(lambda: self.navigate_to("balance_sheet"))
        reports_menu.addAction(balance_sheet_action)
        
        reports_menu.addSeparator()
        
        ar_aging_action = QAction('AR Ageing Report', self)
        ar_aging_action.triggered.connect(lambda: self.navigate_to("ar_ageing"))
        reports_menu.addAction(ar_aging_action)
        
        ap_aging_action = QAction('AP Ageing Report', self)
        ap_aging_action.triggered.connect(lambda: self.navigate_to("ap_ageing"))
        reports_menu.addAction(ap_aging_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        # Add calculator
        calc_action = QAction('Calculator', self)
        calc_action.setStatusTip('Open calculator')
        calc_action.triggered.connect(self.open_calculator)
        tools_menu.addAction(calc_action)
        
        # Add calendar
        calendar_action = QAction('Calendar', self)
        calendar_action.setStatusTip('Open calendar')
        calendar_action.triggered.connect(self.open_calendar)
        tools_menu.addAction(calendar_action)
        
        tools_menu.addSeparator()
        
        # Add database backup
        backup_action = QAction('Backup Database', self)
        backup_action.setStatusTip('Create database backup')
        backup_action.triggered.connect(lambda: self.navigate_to("backup"))
        tools_menu.addAction(backup_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # License Manager action
        license_action = QAction('License Manager', self)
        license_action.setStatusTip('Manage Pharmacy ERP license')
        license_action.triggered.connect(self.show_license_manager)
        help_menu.addAction(license_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction('About', self)
        about_action.setStatusTip('About Pharmacy ERP')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Theme toggle button on menu bar
        self.theme_toggle_action = QAction('Dark/Light', self)
        self.theme_toggle_action.setStatusTip('Switch between light and dark themes')
        self.theme_toggle_action.triggered.connect(self.toggle_theme)
        menubar.addAction(self.theme_toggle_action)

    def show_license_manager(self):
        """Show the license manager dialog."""
        dialog = LicenseManagerDialog(self)
        dialog.exec()

    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Pharmacy ERP",
            "Pharmacy ERP v1.0.0\n\n"
            "A comprehensive enterprise resource planning system\n"
            "for pharmaceutical distribution management.\n\n"
            "© 2026 Pharmacy ERP Solutions. All rights reserved."
        )
    
    def show_preferences(self):
        """Show preferences dialog."""
        QMessageBox.information(self, "Preferences", "Preferences panel would open here.")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def navigate_to(self, page_id):
        """Navigate to a specific page."""
        with SafeBoundary(log_context="navigate_to", tags=['ui', 'navigation']):
            self._do_navigate(page_id)

    def _do_navigate(self, page_id):
        # Check ui_scopes — deny if user doesn't have access
        if not self.auth_manager.has_access(page_id) and page_id not in ("dashboard", "settings"):
            show_warning(f"Access denied: you don't have permission to view {page_id}")
            return

        page_map = {
            "dashboard": 0,
            "products": 1,
            "categories": 2,
            "warehouses": 3,
            "batches": 4,
            "sales_invoice": 5,
            "purchase_invoice": 6,
            "customers": 7,
            "suppliers": 8,
            "returns": 9,
            "pos": 10,
            "chart_of_accounts": 11,
            "journal_entries": 12,
            "account_ledger": 13,
            "trial_balance": 14,
            "profit_loss": 15,
            "balance_sheet": 16,
            "ar_ageing": 17,
            "ap_ageing": 18,
            "payments": 19,
            "budgeting": 20,
            "tax": 21,
            "cost_centers": 22,
            "cashflow": 22,
            "employees": 23,
            "attendance": 24,
            "leave": 25,
            "payroll": 26,
            "backup": 27,
            "settings": 28,
            "fixed_assets": 29,
            "audit": 30,
            "user_management": 31,
            "intelligence_hub": 32,
            "invoice_templates": 33,
            "expenses": 34,
            "entities": 35,
            "licensing": 36,
            "production": 37,
            "control_center": 38,
            "operations": 38,
            "observability": 39,
            "decision_workspace": 48,
            "cash_flow": 49,
            "employee_summary": 50,
            "attendance_report": 51,
            "leave_report": 52,
            "overtime_report": 53,
            "payroll_summary": 54,
            "payroll_trend": 55,
            "payroll_dept_cost": 56,
            "payroll_emp_history": 57,
        }
        if page_id in page_map:
            index = page_map[page_id]
            if index != 0 and hasattr(self, '_lazy_screens'):
                self._lazy_screens.load(index)
            self.pages.setCurrentIndex(index)
            self._update_nav_header(index, page_id.replace('_', ' ').title())
            self.status_bar.showMessage(f"Navigated to {page_id.replace('_', ' ').title()}", 2000)
    
    def new_product(self):
        """Create new product."""
        QMessageBox.information(self, "New Product", "Navigate to Products and click Add New.")
        self.navigate_to("products")
    
    def show_stock_alerts(self):
        """Show low stock alerts."""
        QMessageBox.information(self, "Stock Alerts", "Showing low stock items...")
    
    def open_calculator(self):
        """Open system calculator."""
        import subprocess
        try:
            subprocess.Popen('calc.exe')
        except:
            QMessageBox.warning(self, "Error", "Could not open calculator.")
    
    def open_calendar(self):
        """Open system calendar."""
        import subprocess
        try:
            subprocess.Popen('outlook.exe')
        except:
            QMessageBox.information(self, "Calendar", "Calendar integration not available.")
    
    def logout(self):
        """Logout and return to login screen."""
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            username = self.auth_manager.user.get('username', 'unknown') if self.auth_manager.user else 'unknown'
            _cid = generate_correlation_id("auth")
            try:
                hs = capture_health_snapshot()
                log.info(f"User logout: {username} | snapshot: {hs}",
                          extra={'extra_fields': {'tags': ['auth', 'logout', 'diagnostic']}})
            except Exception:
                log.info(f"User logout: {username}",
                          extra={'extra_fields': {'tags': ['auth', 'logout']}})
            emit_event('auth_event', module='main_window', action='logout',
                       metadata={'username': username, 'screen': get_active_screen()},
                       correlation_id=_cid)
            
            # Logout via AuthManager
            self.auth_manager._clear_session()
            self.auth_manager._is_authenticated = False
            encrypted_clear_session()
            self.api_client.clear_auth_token()
            
            # Close main window and show login
            self.close()
            # Re-run main to show login
            import subprocess
            subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "..", "main.py")])
    
    def refresh_current_view(self):
        """Refresh the current view data."""
        with SafeBoundary(log_context="refresh_current_view", tags=['ui', 'navigation']):
            self._do_refresh_current_view()

    def _do_refresh_current_view(self):
        index = self.pages.currentIndex()
        if hasattr(self, 'product_screen') and index == 2:
            self.product_screen.load_products()
        elif hasattr(self, 'customer_screen') and index == 8:
            self.customer_screen.load_customers()
        elif hasattr(self, 'supplier_screen') and index == 9:
            self.supplier_screen.load_suppliers()
        self.status_bar.showMessage("Refreshed", 2000)
        
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Update loading overlay geometry
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
    
    def closeEvent(self, event):
        """Ensure all timers are stopped on application exit."""
        shutdown_all_timers()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts (Phase 12)."""
        from PySide6.QtGui import QKeySequence
        from PySide6.QtWidgets import QShortcut
        
        # Alt+Left: Go back
        if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_Left:
            self._go_back()
            return
        
        # Ctrl+Home: Go to dashboard
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Home:
            self._go_home()
            return
        
        # Escape: Close/return
        if event.key() == Qt.Key_Escape:
            # If not on dashboard, close screen
            if self.pages.currentIndex() != 0:
                self._close_screen()
            return
        
        super().keyPressEvent(event)
