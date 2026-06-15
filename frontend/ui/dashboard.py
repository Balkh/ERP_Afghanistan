from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
                                  QGridLayout, QApplication, QScrollArea)
from PySide6.QtCore import QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont
from ui.role_manager import UserRole
from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_6, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG, TEXT_BODY_SMALL, TEXT_CARD_TITLE, TEXT_HELPER, TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_TABLE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_INFO, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER)
from ui.components.kpi_cards import KPICard
from theme.theme_engine import ThemeEngine
from ui.screens.base_screen import BaseScreen
from ui.dashboard_colors import DashboardColorScheme


class Dashboard(BaseScreen):
    """Role-aware Dashboard widget fetching real data from /api/control-center/."""

    def __init__(self, role=None, api_client=None):
        self._role = role or UserRole.ADMIN
        self._api_client = api_client
        self._dashboard_data = {}
        self._extra_counts = {}
        self._kpi_labels = {}
        self._refresh_worker = None   # F20: active worker reference
        self._refresh_thread = None   # F20: active thread reference
        super().__init__()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_data)
        self._refresh_timer.start(120000)

        if self._api_client:
            QTimer.singleShot(3500, self.refresh_data)

    def set_api_client(self, client):
        self._api_client = client
        self.refresh_data()

    def set_role(self, role):
        self._role = role
        self._rebuild_role_section()
        self.refresh_data()

    def refresh_theme(self):
        """Re-apply dashboard stylesheets with current theme colors."""
        self.setStyleSheet(f"""
            QWidget#dashboard {{ background-color: {COLOR_BG_MAIN}; }}
        """)
        for child in self.findChildren(QScrollArea):
            child.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_MAIN}; }}")
            break
        self._subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")

        # Re-apply role + alert card backgrounds
        for name in ('roleCard', 'alertCard', 'actionsCard'):
            for child in self.findChildren(QFrame):
                if child.objectName() == name:
                    child.setStyleSheet(f"QFrame#{name} {{ background: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}px; }}")
        self._rebuild_alerts()

    def cleanup(self):
        if self._refresh_timer:
            self._refresh_timer.stop()
        self._cancel_refresh_worker()
        ThemeEngine.instance().unregister(self._theme_token)

    def _cancel_refresh_worker(self):
        """F20: Stop and clean up the background refresh worker if running."""
        if self._refresh_worker is not None:
            self._refresh_worker.cancel()
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            self._refresh_thread.quit()
            self._refresh_thread.wait(2000)
        self._refresh_worker = None
        self._refresh_thread = None

    def _on_screen_shown(self):
        if self._refresh_timer and not self._refresh_timer.isActive():
            self._refresh_timer.start(120000)

    def _on_screen_hidden(self):
        if self._refresh_timer and self._refresh_timer.isActive():
            self._refresh_timer.stop()

    # ------------------------------------------------------------------
    # Static UI  (built once, never fully rebuilt)
    # ------------------------------------------------------------------
    def _setup_screen(self):
        super()._setup_screen()
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        self.setObjectName("dashboard")
        self.setStyleSheet(f"""
            QWidget#dashboard {{ background-color: {COLOR_BG_MAIN}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_NONE)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_MAIN}; }}")

        content = QWidget()
        content.setObjectName("dashboardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACING_XXL, SPACING_XL, SPACING_XXL, SPACING_XL)
        layout.setSpacing(SPACING_LG)

        # -- Header row --
        hdr = QHBoxLayout()
        title = QLabel("Dashboard")
        title_font = QFont("Segoe UI", TEXT_PAGE_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        hdr.addWidget(title)
        hdr.addStretch()
        from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
        refresh_btn = EnterpriseButton("Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self.refresh_data)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        self._subtitle = QLabel("Loading…")
        self._subtitle.setFont(QFont("Segoe UI", TEXT_BODY_SMALL))
        self._subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        layout.addWidget(self._subtitle)

        # -- KPI grid (2 × 3) --
        kg = QGridLayout()
        kg.setSpacing(SPACING_MD)

        specs = [
            (0, 0, "Products",       'info',    'kpi_products'),
            (0, 1, "Customers",      'success', 'kpi_customers'),
            (0, 2, "Suppliers",      'primary', 'kpi_suppliers'),
            (1, 0, "Cash Balance",   'success', 'kpi_cash'),
            (1, 1, "Revenue (MTD)",  'primary', 'kpi_revenue'),
            (1, 2, "Working Capital",'warning', 'kpi_wc'),
        ]
        for r, c, t, sev, key in specs:
            card = KPICard(t, "\u2014", severity=sev)
            kg.addWidget(card, r, c)
            self._kpi_labels[key] = (card.title_label, card.value_label)

        layout.addLayout(kg)

        # -- Middle: role section (left) + alerts (right) --
        mid = QHBoxLayout()
        mid.setSpacing(SPACING_LG)

        self._role_frame = QFrame()
        self._role_frame.setObjectName("roleCard")
        self._role_frame.setStyleSheet(f"QFrame#roleCard {{ background: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}px; }}")
        self._role_stack = QVBoxLayout(self._role_frame)
        self._role_stack.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        self._role_stack.setSpacing(SPACING_SM + SPACING_XS)
        mid.addWidget(self._role_frame, 3)

        self._alert_frame = QFrame()
        self._alert_frame.setObjectName("alertCard")
        self._alert_frame.setStyleSheet(f"QFrame#alertCard {{ background: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}px; }}")
        self._alert_stack = QVBoxLayout(self._alert_frame)
        self._alert_stack.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        self._alert_stack.setSpacing(SPACING_SM)
        mid.addWidget(self._alert_frame, 2)

        layout.addLayout(mid, 1)

        # -- Quick actions --
        af = QFrame()
        af.setObjectName("actionsCard")
        af.setStyleSheet(f"QFrame#actionsCard {{ background: {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_LG}px; }}")
        al = QHBoxLayout(af)
        al.setContentsMargins(SPACING_XL, SPACING_MD, SPACING_XL, SPACING_MD)
        al.setSpacing(SPACING_MD)

        al_title = QLabel("Quick Actions")
        al_title.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        al_title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        al.addWidget(al_title)

        for text, idx in [("New Sale", 5), ("New Purchase", 6),
                          ("Products", 1), ("Reports", 13)]:
            al.addWidget(self._mk_action_btn(text, idx))
        al.addStretch()
        layout.addWidget(af)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _mk_action_btn(self, text, page_index):
        from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
        btn = EnterpriseButton(text, variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        btn.clicked.connect(lambda checked, x=page_index: self._navigate_to(x))
        return btn

    # ------------------------------------------------------------------
    # Data refresh  (F20/F21: non-blocking via background QThread)
    # ------------------------------------------------------------------
    def refresh_data(self):
        """Trigger a non-blocking background refresh.

        F20/F21: All three API calls are executed in a QThread worker
        so the UI thread is never blocked.
        """
        if not self._api_client:
            return
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return
        self._subtitle.setText("Refreshing…")
        self._refresh_worker = _DashboardRefreshWorker(self._api_client)
        self._refresh_thread = QThread(self)
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.finished.connect(self._on_refresh_done)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.error.connect(self._on_refresh_error)
        self._refresh_thread.finished.connect(self._on_thread_finished)
        self._refresh_thread.start()

    def _on_refresh_done(self, dashboard_data: dict, extra_counts: dict):
        """Receive results from background worker and update UI (UI thread)."""
        self._dashboard_data = dashboard_data
        self._extra_counts = extra_counts
        self._sync_ui()
        self._subtitle.setText("Up to date")

    def _on_refresh_error(self, message: str):
        """Handle background worker error (UI thread)."""
        self._subtitle.setText("Refresh failed")

    def _on_thread_finished(self):
        """Clean up thread/worker references after completion."""
        self._refresh_worker = None
        self._refresh_thread = None

    def _fetch_extra_counts(self):
        """Kept for internal use by _DashboardRefreshWorker only."""
        for key, url in [('customers', '/api/sales/customers/?limit=1'),
                         ('suppliers', '/api/purchases/suppliers/?limit=1')]:
            try:
                r = self._api_client.get(url, background=True)
                if r and isinstance(r, dict):
                    d = r.get('data', r)
                    if isinstance(d, dict):
                        self._extra_counts[key] = d.get('count', 0)
                    elif isinstance(d, list):
                        self._extra_counts[key] = len(d)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Sync UI with data  (label updates only)
    # ------------------------------------------------------------------
    def _sync_ui(self):
        data = self._dashboard_data
        fin = data.get('financial', {}) or {}
        inv = data.get('inventory', {}) or {}
        # KPI labels
        inv_ov = inv.get('overview', {}) or {}
        bal = fin.get('balance_summary', {}) or {}
        today = fin.get('today_activity', {}) or {}

        self._set_kpi('kpi_products', inv_ov.get('total_products', '—'))
        self._set_kpi('kpi_customers', self._extra_counts.get('customers', '—'))
        self._set_kpi('kpi_suppliers', self._extra_counts.get('suppliers', '—'))

        assets = bal.get('total_assets', 0)
        self._set_kpi('kpi_cash', float(assets or 0), currency=True)

        sales = today.get('sales', 0)
        self._set_kpi('kpi_revenue', float(sales or 0), currency=True)

        liab = bal.get('total_liabilities', 0)
        wc = float(assets or 0) - float(liab or 0)
        self._set_kpi('kpi_wc', wc, currency=True)

        self._rebuild_role_section(data)
        self._rebuild_alerts(data)

    def _set_kpi(self, key, value, currency=False):
        pair = self._kpi_labels.get(key)
        if not pair:
            return
        _, v_lbl = pair
        if currency:
            try:
                v_lbl.setText(f"AFN {float(value):,.2f}")
            except (ValueError, TypeError):
                v_lbl.setText("AFN 0.00")
        else:
            v_lbl.setText(str(value))

    # ------------------------------------------------------------------
    # Role section
    # ------------------------------------------------------------------
    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                Dashboard._clear_layout(item.layout())

    def _rebuild_role_section(self, data=None):
        self._clear_layout(self._role_stack)

        data = data or self._dashboard_data
        fin = data.get('financial', {}) or {}
        inv = data.get('inventory', {}) or {}
        hr = data.get('hr', {}) or {}

        titles = {
            UserRole.ADMIN: "Financial Overview",
            UserRole.ACCOUNTANT: "Accounting Overview",
            UserRole.WAREHOUSE: "Inventory Overview",
            UserRole.HR: "HR Overview",
        }
        t = QLabel(titles.get(self._role, "Overview"))
        t.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {COLOR_PRIMARY};")
        self._role_stack.addWidget(t)

        if self._role in (UserRole.ADMIN, UserRole.ACCOUNTANT):
            self._build_financial_section(fin)
        elif self._role == UserRole.WAREHOUSE:
            self._build_inventory_section(inv)
        elif self._role == UserRole.HR:
            self._build_hr_section(hr)
        else:
            self._build_inventory_section(inv)

        self._role_stack.addStretch()

    def _build_financial_section(self, fin):
        bal = fin.get('balance_summary', {}) or {}
        pend = fin.get('pending_counts', {}) or {}
        jour = fin.get('journal_status', {}) or {}
        today = fin.get('today_activity', {}) or {}

        items = [
            ("Total Assets",     bal.get('total_assets', 0),     'green',  True),
            ("Total Liabilities", bal.get('total_liabilities', 0),'red',    True),
            ("Equity",           bal.get('total_equity', 0),     'blue',   True),
            ("Sales Today",      today.get('sales', 0),          'green',  True),
            ("Purchases Today",  today.get('purchases', 0),      'red',    True),
            ("Pending Sales",    pend.get('sales_invoices', 0),  'peach',  False),
            ("Pending Purchases",pend.get('purchase_bills', 0),  'peach',  False),
            ("Posted JE",        jour.get('posted', 0),          'teal',   False),
            ("Unposted JE",      jour.get('unposted', 0),        'red',    False),
        ]
        grid = QGridLayout()
        grid.setSpacing(SPACING_SM)
        for i, (lbl, val, ck, is_cur) in enumerate(items):
            grid.addWidget(self._mini_card(lbl, val, ck, is_cur), i // 3, i % 3)
        self._role_stack.addLayout(grid)

    def _build_inventory_section(self, inv):
        ov = inv.get('overview', {}) or {}
        al = inv.get('stock_alerts', {}) or {}
        act = inv.get('activity', {}) or {}

        items = [
            ("Products",    ov.get('total_products', 0),     'blue',   False),
            ("Batches",     ov.get('total_batches', 0),      'mauve',  False),
            ("Warehouses",  ov.get('active_warehouses', 0),  'teal',   False),
            ("Out of Stock",al.get('out_of_stock', 0),       'red',    False),
            ("Low Stock",   al.get('low_stock', 0),          'peach',  False),
            ("Expiring",    al.get('expiring_soon', 0),      'yellow', False),
            ("Movements Today", act.get('movements_today', 0), 'green', False),
        ]
        grid = QGridLayout()
        grid.setSpacing(SPACING_SM)
        for i, (lbl, val, ck, _) in enumerate(items):
            grid.addWidget(self._mini_card(lbl, val, ck, False), i // 3, i % 3)
        self._role_stack.addLayout(grid)

    def _build_hr_section(self, hr):
        ov = hr.get('overview', {}) or {}
        att = hr.get('today_attendance', {}) or {}

        items = [
            ("Active Employees", ov.get('active_employees', 0),'blue',  False),
            ("Departments",      ov.get('departments', 0),     'mauve', False),
            ("Present Today",    att.get('present', 0),        'green', False),
            ("Absent Today",     att.get('absent', 0),         'red',   False),
            ("On Leave",         att.get('on_leave', 0),       'peach', False),
        ]
        grid = QGridLayout()
        grid.setSpacing(SPACING_SM)
        for i, (lbl, val, ck, _) in enumerate(items):
            grid.addWidget(self._mini_card(lbl, val, ck, False), i // 3, i % 3)
        self._role_stack.addLayout(grid)

    def _mini_card(self, label, value, color_key, is_currency):
        c = DashboardColorScheme.get(color_key)
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background: {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; }}")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        lay.setSpacing(SPACING_XS)

        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", TEXT_HELPER))
        lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        lay.addWidget(lbl)

        if is_currency:
            try:
                display = f"AFN {float(value):,.2f}"
            except (ValueError, TypeError):
                display = "AFN 0.00"
        else:
            display = str(value)

        v = QLabel(display)
        v.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {c};")
        v.setWordWrap(True)
        lay.addWidget(v)

        return f

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _rebuild_alerts(self, data=None):
        if data is None:
            data = {}
        self._clear_layout(self._alert_stack)

        t = QLabel("Alerts")
        t.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {COLOR_WARNING};")
        self._alert_stack.addWidget(t)

        ops = data.get('operations', {}) or {}
        al_data = ops.get('alerts', {}) or {}
        recent = al_data.get('recent', []) if isinstance(al_data, dict) else []
        rcount = al_data.get('recent_count', 0) if isinstance(al_data, dict) else 0

        health = data.get('health', {}) or {}
        db = health.get('database', {}) or {}
        db_ok = db.get('status', '') == 'ok'

        self._alert_stack.addWidget(self._alert_line("API", "Connected", 'green'))
        self._alert_stack.addWidget(
            self._alert_line("Database", "Healthy" if db_ok else "Issue", 'green' if db_ok else 'red'))

        if rcount > 0 and isinstance(recent, list):
            for a in recent[:3]:
                msg = a.get('message', '') if isinstance(a, dict) else str(a)
                sev = a.get('severity', 'info') if isinstance(a, dict) else 'info'
                ck = DashboardColorScheme.for_severity(sev)
                self._alert_stack.addWidget(self._alert_line("", msg, ck))
        else:
            self._alert_stack.addWidget(self._alert_line("System", "No current alerts", 'blue'))

        self._alert_stack.addStretch()

    def _alert_line(self, label, status, color_key):
        c = DashboardColorScheme.get(color_key)
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BORDER};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-left: 3px solid {c};
                border-radius: {BORDER_RADIUS_SM}px;
            }}
        """)
        row = QHBoxLayout(box)
        row.setContentsMargins(SPACING_SM, SPACING_6, SPACING_SM, SPACING_6)
        row.setSpacing(SPACING_SM)

        dot = QLabel("●")
        dot.setFont(QFont("Segoe UI", TEXT_TABLE))
        dot.setStyleSheet(f"color: {c};")
        row.addWidget(dot)

        txt = f"{label}: {status}" if label else status
        lbl = QLabel(txt)
        lbl.setFont(QFont("Segoe UI", TEXT_TABLE))
        lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        row.addWidget(lbl)
        row.addStretch()
        return box

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _navigate_to(self, index):
        from ui.main_window import MainWindow
        app = QApplication.instance()
        if not app:
            return
        titles = {1: "Products", 5: "Sales Invoice", 6: "Purchase Invoice", 13: "Trial Balance"}
        for w in app.topLevelWidgets():
            if isinstance(w, MainWindow):
                w.change_page(index, titles.get(index, "Dashboard"))
                break


# ---------------------------------------------------------------------------
# F20/F21 — Background worker for Dashboard data fetching
# ---------------------------------------------------------------------------

class _DashboardRefreshWorker(QObject):
    """Worker that fetches all dashboard data in a background thread.

    Emits:
        finished(dashboard_data, extra_counts) — on success
        error(message)                         — on failure
    """

    finished = Signal(dict, dict)
    error = Signal(str)

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client
        self._cancelled = False

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True

    def run(self):
        """Execute all API calls sequentially in the background thread."""
        try:
            if self._cancelled:
                return
            raw = self._api_client.get("/api/control-center/", background=True)
            if isinstance(raw, dict):
                d = raw.get('data', {})
                dashboard_data = d if isinstance(d, dict) else raw
            else:
                dashboard_data = raw if isinstance(raw, dict) else {}

            extra_counts = {}
            for key, url in [
                ('customers', '/api/sales/customers/?limit=1'),
                ('suppliers', '/api/purchases/suppliers/?limit=1'),
            ]:
                if self._cancelled:
                    return
                try:
                    r = self._api_client.get(url, background=True)
                    if r and isinstance(r, dict):
                        d = r.get('data', r)
                        if isinstance(d, dict):
                            extra_counts[key] = d.get('count', 0)
                        elif isinstance(d, list):
                            extra_counts[key] = len(d)
                except Exception:
                    pass

            if not self._cancelled:
                self.finished.emit(dashboard_data, extra_counts)

        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))


