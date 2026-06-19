import warnings
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                                 QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from theme.theme_engine import ThemeEngine
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.role_manager import UserRole, get_visible_navigation_items, is_navigation_item_visible
from ui.constants import (SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG, TEXT_CARD_TITLE, TEXT_LABEL, TEXT_BODY, COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_HOVER, COLOR_BG_FOCUS, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_DANGER, COLOR_DANGER_HOVER, COLOR_DANGER_ACTIVE, COLOR_SIDEBAR_ACTIVE_BG, COLOR_SIDEBAR_ACTIVE_BORDER)


class _LegacyNavItem:
    def __init__(self, text, selectable=True, selected=False):
        self._text = text
        self._selectable = selectable
        self._selected = selected

    def text(self):
        return self._text

    def flags(self):
        flags = Qt.ItemIsEnabled
        if self._selectable:
            flags |= Qt.ItemIsSelectable
        return flags

    def isSelected(self):
        return self._selected


class _LegacyNavListAdapter:
    """Compatibility adapter for older QListWidget-based tests."""
    _ITEMS = [
        ("Dashboard", 0, True),
        ("Inventory", 1, False),
        ("Products", 2, True),
        ("Categories", 3, True),
        ("Warehouses", 4, True),
        ("Batches", 5, True),
        ("Sales Invoice", 6, True),
        ("Purchases", 7, False),
        ("Purchase Invoice", 8, True),
        ("Customers", 9, True),
        ("Accounting", 10, False),
        ("Chart of Accounts", 11, True),
        ("Journal Entries", 12, True),
        ("Account Ledger", 13, True),
        ("Reports", 14, False),
        ("Trial Balance", 15, True),
        ("Profit & Loss", 16, True),
        ("Balance Sheet", 17, True),
        ("AR Ageing", 18, True),
        ("AP Ageing", 19, True),
        ("Settings", 20, True),
    ]

    def __init__(self, sidebar):
        self._sidebar = sidebar
        self._current_row = 0

    def count(self):
        return len(self._ITEMS)

    def item(self, index):
        if index < 0 or index >= len(self._ITEMS):
            return None
        text, _page_index, selectable = self._ITEMS[index]
        return _LegacyNavItem(text, selectable=selectable, selected=index == self._current_row)

    def currentRow(self):
        return self._current_row


class Sidebar(QWidget):
    """Sidebar navigation component with collapsible groups."""
    
    # Signals
    page_changed = Signal(int, str)  # index, page_title
    
    def __init__(self, role: UserRole = None):
        super().__init__()
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Expansion state - all groups collapsed by default
        self._expanded_groups = {
            "inventory": False,
            "sales": False,
            "purchases": False,
            "accounting": False,
            "reports": False,
            "finance": False,
            "hr": False,
            "system": False
        }
        
        # Group containers - stored for toggle
        self._group_widgets = {}  # group_name -> container widget
        
        self._role = role
        self._navigation_items = {}  # page_id -> button reference
        self._active_page_id: str = ""  # currently active navigation item
        self._role_renderer = None  # Set by main_window for delegated visibility
        
        # Setup UI
        self.setup_ui()
        
        # Apply role-based visibility if role is set
        if self._role:
            self.apply_role_filter(self._role)
        
        self.group_items = {1, 7, 10, 14}
        self.nav_list = _LegacyNavListAdapter(self)
        # Connect theme changes (unified ThemeEngine — single source of truth)
        ThemeEngine.instance().theme_changed.connect(self.update_theme)

    def cleanup(self):
        """Disconnect from ThemeEngine signals to prevent leaks on widget destruction."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                ThemeEngine.instance().theme_changed.disconnect(self.update_theme)
            except (RuntimeError, TypeError):
                pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
    
    def set_role(self, role: UserRole):
        """Set the role and update navigation visibility."""
        self._role = role
        self.apply_role_filter(role)

    @property
    def role_renderer(self):
        """Get the RoleRenderer instance."""
        return self._role_renderer

    @role_renderer.setter
    def role_renderer(self, renderer):
        """Set the RoleRenderer instance for delegated visibility control."""
        self._role_renderer = renderer

    def apply_demo_profile(self) -> None:
        """Apply a curated customer-demo navigation profile without removing screens."""
        demo_pages = {
            "dashboard", "products", "categories", "warehouses", "batches",
            "sales_invoice", "pos", "customers", "purchase_invoice", "suppliers",
            "returns", "chart_of_accounts", "journal_entries", "account_ledger",
            "trial_balance", "profit_loss", "balance_sheet", "payments", "expenses",
            "budgeting", "cashflow", "employees", "payroll", "backup", "settings",
            "company_profile",
        }
        for page_id, btn in self._navigation_items.items():
            btn.setVisible(page_id in demo_pages)
        for group_name, group_widget in self._group_widgets.items():
            has_visible = any(
                child.property("page_id") in demo_pages
                for child in group_widget.findChildren(EnterpriseButton)
                if child.property("page_id")
            )
            header_frame = getattr(self, f"_{group_name}_header", None)
            if header_frame:
                header_frame.setVisible(has_visible)
            group_widget.setVisible(has_visible)
        if hasattr(self, 'dashboard_btn'):
            self.dashboard_btn.setVisible(True)

    def set_module_visibility(self, module: str, visible: bool) -> None:
        """Show/hide a module group in the sidebar. Used by RoleRenderer."""
        group_widget = self._group_widgets.get(module)
        header_frame = getattr(self, f"_{module}_header", None)
        if group_widget:
            group_widget.setVisible(visible)
        if header_frame:
            header_frame.setVisible(visible)
    
    def apply_role_filter(self, role: UserRole):
        """Apply role-based visibility filter to navigation items.
        
        Delegates to RoleRenderer if available (single source of truth).
        Falls back to local ROLE_PERMISSIONS for backward compatibility.
        """
        if self._role_renderer and self._role_renderer.auth_manager.is_authenticated:
            self._role_renderer.apply_scopes()
            return
        
        visible_items = get_visible_navigation_items(role)
        
        # Update visibility of each navigation item
        for page_id, btn in self._navigation_items.items():
            is_visible = is_navigation_item_visible(role, page_id)
            btn.setVisible(is_visible)
        
        # Also hide group headers if no items in the group are visible
        for group_name, group_widget in self._group_widgets.items():
            # Get the items for this group
            group_items_map = {
                "inventory": {"products", "categories", "warehouses", "batches"},
                "sales": {"sales_invoice", "pos", "customers"},
                "purchases": {"purchase_invoice", "suppliers"},
                "returns": {"returns", "reconciliation"},
                "accounting": {"chart_of_accounts", "journal_entries", "account_ledger", "financial_integrity", "financial_audit"},
                "reports": {"trial_balance", "profit_loss", "balance_sheet", "ar_ageing", "ap_ageing"},
                "finance": {"payments", "expenses", "budgeting", "tax", "cost_centers", "cashflow", "customer_payments", "supplier_payments", "allocation_explorer", "returns_explainability", "journal_reversals", "operations_console"},
                "hr": {"employees", "attendance", "leave", "payroll"},
                "hr_reports": {"employee_summary", "attendance_report", "leave_report", "overtime_report"},
                "payroll_reports": {"payroll_summary", "payroll_trend", "payroll_dept_cost", "payroll_emp_history"},
                "cash_flow": {"cash_flow"},
                "system": {"control_center", "analytics", "observability", "decision_workspace", "intelligence_hub", "invoice_templates", "entities", "licensing", "fixed_assets", "backup", "audit", "user_management", "role_management", "company_profile"}
            }
            group_items = group_items_map.get(group_name, set())
            any_visible = any(item in visible_items for item in group_items)
            
            # Find and hide/show header
            header_frame = getattr(self, f"_{group_name}_header", None)
            if header_frame:
                header_frame.setVisible(any_visible)
            
            # Also hide the entire group if no items visible
            if group_widget:
                group_widget.setVisible(any_visible)
    
    def setup_ui(self):
        """Setup the sidebar UI."""
        # Use scroll area for scrolling support
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{ 
                border: none; 
                background-color: {COLOR_BG_MAIN}; 
            }}
            QScrollArea>QWidget>QScrollBar:vertical {{
                background: {COLOR_BG_MAIN};
                width: 8px;
            }}
            QScrollArea>QWidget>QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM}px;
            }}
            QScrollArea>QWidget>QScrollBar::add-line:vertical, 
            QScrollArea>QWidget>QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        self._scroll_content = scroll_content
        
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_NONE)
        
        # Brand/logo area
        brand_frame = QFrame()
        brand_frame.setFixedHeight(104)
        brand_frame.setObjectName("sidebarBrand")
        brand_frame.setStyleSheet(f"""
            QFrame#sidebarBrand {{
                background-color: {COLOR_BG_ELEVATED};
                border-bottom: 1px solid {COLOR_BORDER};
            }}
        """)
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(MARGIN_PAGE, SPACING_MD, MARGIN_PAGE, SPACING_MD)
        brand_layout.setSpacing(SPACING_XS)
        
        brand_label = QLabel("✦ ERP Afghanistan")
        brand_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE + 1, QFont.Weight.Bold))
        brand_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        brand_layout.addWidget(brand_label)

        brand_subtitle = QLabel("Enterprise Operations Suite")
        brand_subtitle.setFont(QFont("Segoe UI", TEXT_LABEL))
        brand_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        brand_layout.addWidget(brand_subtitle)

        brand_badge = QLabel("● SECURE LOCAL")
        brand_badge.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        brand_badge.setStyleSheet(f"color: {COLOR_PRIMARY};")
        brand_layout.addWidget(brand_badge)
        self._brand_frame = brand_frame
        self._brand_label = brand_label
        self._brand_subtitle = brand_subtitle
        self._brand_badge = brand_badge
        
        layout.addWidget(brand_frame)
        
        # Navigation section with proper spacing
        self._nav_section = QWidget()
        self._nav_section.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        nav_layout = QVBoxLayout(self._nav_section)
        nav_layout.setContentsMargins(SPACING_SM,  SPACING_MD,  SPACING_SM,  SPACING_MD)
        nav_layout.setSpacing(SPACING_SM)
        
        # Dashboard (always visible)
        self.dashboard_btn = self._create_nav_button("Dashboard", "dashboard", 0)
        nav_layout.addWidget(self.dashboard_btn)
        
        # Create collapsible groups with proper structure
        self._create_group(nav_layout, "Inventory", "inventory", [
            ("Products", "products", 1),
            ("Categories", "categories", 2),
            ("Warehouses", "warehouses", 3),
            ("Batches", "batches", 4),
        ])
        
        self._create_group(nav_layout, "Sales", "sales", [
            ("Sales Invoice", "sales_invoice", 5),
            ("POS Terminal", "pos", 37),
            ("Customers", "customers", 7),
        ])
        
        self._create_group(nav_layout, "Purchases", "purchases", [
            ("Purchase Invoice", "purchase_invoice", 6),
            ("Suppliers", "suppliers", 8),
        ])
        
        self._create_group(nav_layout, "Returns", "returns", [
            ("Return Orders", "returns", 9),
            ("Reconciliation", "reconciliation", 57),
        ])
        
        self._create_group(nav_layout, "Accounting", "accounting", [
            ("Chart of Accounts", "chart_of_accounts", 10),
            ("Journal Entries", "journal_entries", 11),
            ("Account Ledger", "account_ledger", 12),
            ("Financial Integrity", "financial_integrity", 58),
            ("Financial Audit Log", "financial_audit", 59),
        ])
        
        self._create_group(nav_layout, "Reports", "reports", [
            ("Trial Balance", "trial_balance", 13),
            ("Profit & Loss", "profit_loss", 14),
            ("Balance Sheet", "balance_sheet", 15),
            ("AR Ageing", "ar_ageing", 16),
            ("AP Ageing", "ap_ageing", 17),
        ])
        
        self._create_group(nav_layout, "Finance", "finance", [
            ("Payments", "payments", 18),
            ("Expenses", "expenses", 34),
            ("Budgeting", "budgeting", 19),
            ("Tax", "tax", 20),
            ("Cost Centers", "cost_centers", 21),
            ("Cash Flow", "cashflow", 22),
            ("Customer Payments", "customer_payments", 60),
            ("Supplier Payments", "supplier_payments", 61),
            ("Allocation Explorer", "allocation_explorer", 62),
            ("Returns Explainability", "returns_explainability", 63),
            ("Journal Reversals", "journal_reversals", 64),
            ("Operations Console", "operations_console", 65),
        ])
        
        self._create_group(nav_layout, "HR", "hr", [
            ("Employees", "employees", 23),
            ("Departments & Positions", "departments_positions", 67),
            ("Attendance", "attendance", 24),
            ("Leave", "leave", 25),
            ("Payroll", "payroll", 26),
        ])

        self._create_group(nav_layout, "HR Reports", "hr_reports", [
            ("Employee Summary", "employee_summary", 49),
            ("Attendance Report", "attendance_report", 50),
            ("Leave Report", "leave_report", 51),
            ("Overtime Report", "overtime_report", 52),
        ])

        self._create_group(nav_layout, "Payroll Reports", "payroll_reports", [
            ("Payroll Summary", "payroll_summary", 53),
            ("Payroll Trend", "payroll_trend", 54),
            ("Dept Cost", "payroll_dept_cost", 55),
            ("Employee History", "payroll_emp_history", 56),
        ])
        
        self._create_group(nav_layout, "System", "system", [
            ("Intelligence Hub", "intelligence_hub", 32),
            ("Control Center", "control_center", 38),
            ("Analytics", "analytics", 40),
            ("Observability Console", "observability", 39),
            ("Decision Support", "decision_workspace", 47),
            ("Invoice Templates", "invoice_templates", 33),
            ("Company Profile", "company_profile", 66),
            ("Business Entities", "entities", 35),
            ("Licensing", "licensing", 36),
            ("Fixed Assets", "fixed_assets", 29),
            ("Backup & Restore", "backup", 27),
            ("Audit Log", "audit", 30),
            ("User Management", "user_management", 31),
            ("Role Management", "role_management", 48),
        ])
        
        nav_layout.addWidget(self._create_nav_button("Settings", "settings", 28))
        
        # Add stretch to push content up
        nav_layout.addStretch()
        
        layout.addWidget(self._nav_section)
        
        # Bottom section
        self._bottom_frame = QFrame()
        self._bottom_frame.setFixedHeight(72)
        self._bottom_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE}; border-top: 1px solid {COLOR_BORDER};")
        bottom_layout = QVBoxLayout(self._bottom_frame)
        bottom_layout.setContentsMargins(MARGIN_PAGE,  SPACING_SM,  MARGIN_PAGE,  SPACING_SM)
        
        self.logout_btn = EnterpriseButton("⎋  Logout", variant=ButtonVariant.DANGER)
        bottom_layout.addWidget(self.logout_btn)
        
        layout.addWidget(self._bottom_frame)
        
        # Set scroll area content
        self._scroll_area.setWidget(scroll_content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(SPACING_NONE)
        main_layout.addWidget(self._scroll_area)
    
    @staticmethod
    def _nav_icon(page_id):
        icons = {
            "dashboard": "◆", "products": "▣", "categories": "▤", "warehouses": "▥", "batches": "◫",
            "sales_invoice": "↗", "pos": "▦", "customers": "◎", "purchase_invoice": "↙", "suppliers": "◉",
            "returns": "↺", "reconciliation": "≋", "chart_of_accounts": "☷", "journal_entries": "✎",
            "account_ledger": "▧", "financial_integrity": "✓", "financial_audit": "⌕", "trial_balance": "⚖",
            "profit_loss": "↕", "balance_sheet": "▥", "payments": "◈", "expenses": "−", "budgeting": "▨",
            "tax": "%", "cost_centers": "⌾", "cashflow": "≈", "employees": "♙", "settings": "⚙",
        }
        return icons.get(page_id, "•")

    def _create_nav_button(self, title, page_id, page_index):
        """Create a navigation button with enhanced hover/active states."""
        btn = EnterpriseButton(f"  {self._nav_icon(page_id)}  {title}")
        btn.setFont(QFont("Segoe UI", TEXT_LABEL))
        btn.setMinimumHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            EnterpriseButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: none;
                border-radius: {BORDER_RADIUS_LG}px;
                text-align: left;
                padding-left: {SPACING_MD}px;
                padding-top: {SPACING_XS}px;
                padding-bottom: {SPACING_XS}px;
                font-weight: 500;
                min-height: 20px;
            }}
            EnterpriseButton:hover {{
                background-color: {COLOR_BG_HOVER};
                color: {COLOR_TEXT_PRIMARY};
            }}
            EnterpriseButton:pressed {{
                background-color: {COLOR_BG_FOCUS};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        btn.setProperty("page_id", page_id)
        btn.setProperty("page_index", page_index)
        btn.clicked.connect(lambda: self._on_item_clicked(page_index, title))
        
        # Store reference for role-based filtering
        self._navigation_items[page_id] = btn
        
        return btn

    def _create_group(self, parent_layout, title, group_name, items):
        """Create a collapsible group with proper structure."""
        group_widget = QWidget()
        group_widget.setStyleSheet("background-color: transparent;")
        group_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(SPACING_NONE)

        header_style = f"""
            EnterpriseButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                padding-left: {SPACING_SM}px;
                padding-top: {SPACING_XS}px;
                padding-bottom: {SPACING_XS}px;
                color: {COLOR_PRIMARY};
                font-weight: bold;
                font-size: {TEXT_CARD_TITLE}pt;
                min-height: 24px;
            }}
            EnterpriseButton:hover {{
                background-color: {COLOR_BG_HOVER};
                color: {COLOR_PRIMARY_HOVER} /* Phase Recovery: hover deepens the color */
            }}
        """

        is_expanded = self._expanded_groups.get(group_name, False)
        arrow = "▼" if is_expanded else "▶"
        header_btn = EnterpriseButton(f"{arrow}  {title}")
        header_btn.setCursor(Qt.PointingHandCursor)
        header_btn.setFixedHeight(42)
        header_btn.setStyleSheet(header_style)
        header_btn.setProperty("group_name", group_name)
        header_btn.clicked.connect(lambda checked, g=group_name: self._toggle_group(g))

        group_layout.addWidget(header_btn)
        setattr(self, f"_{group_name}_header", header_btn)

        items_widget = QWidget()
        items_widget.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        items_layout = QVBoxLayout(items_widget)
        items_layout.setContentsMargins(SPACING_XL + SPACING_SM, SPACING_XS, SPACING_SM, SPACING_SM)
        items_layout.setSpacing(SPACING_XS)

        for item_title, page_id, page_index in items:
            btn = self._create_nav_button(item_title, page_id, page_index)
            items_layout.addWidget(btn)

        group_layout.addWidget(items_widget)
        self._group_widgets[group_name] = group_widget
        parent_layout.addWidget(group_widget)

        if not is_expanded:
            items_widget.setVisible(False)
            items_widget.setMaximumHeight(0)
            group_widget.setMaximumHeight(42)
        else:
            items_widget.setVisible(True)
            items_widget.setMaximumHeight(16777215)
            group_widget.setMaximumHeight(16777215)

    def _toggle_group(self, group_name):
        """Toggle a group's expanded/collapsed state."""
        current_state = self._expanded_groups.get(group_name, False)
        new_state = not current_state
        self._expanded_groups[group_name] = new_state

        group_widget = self._group_widgets.get(group_name)
        if not group_widget:
            return

        header_btn = getattr(self, f"_{group_name}_header", None)

        items_widget = None
        layout = group_widget.layout()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget != header_btn:
                items_widget = widget
                break

        # Get the title text from the button (strip arrow prefix)
        title_text = ""
        if header_btn:
            btn_text = header_btn.text()
            title_text = btn_text.replace("▶ ", "").replace("▼ ", "")

        if new_state:
            if items_widget:
                items_widget.setVisible(True)
                items_widget.setMaximumHeight(16777215)
            if header_btn:
                header_btn.setText(f"▼  {title_text}")
            group_widget.setMaximumHeight(16777215)
        else:
            if items_widget:
                items_widget.setVisible(False)
                items_widget.setMaximumHeight(0)
            if header_btn:
                header_btn.setText(f"▶  {title_text}")
            group_widget.setMaximumHeight(42)

        group_widget.layout().invalidate()
        group_widget.update()


    def _on_item_clicked(self, page_index, page_title):
        """Handle navigation item click."""
        # Emit page changed signal
        self.page_changed.emit(page_index, page_title)
        
        # Find the main window to show loading state in status bar
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'status_bar'):
                widget.status_bar.showMessage(f"Loading {page_title}...", 3000)
                break
    
    def _set_button_active(self, btn, active: bool):
        """Apply active or default style to a navigation button."""
        if active:
            btn.setStyleSheet(f"""
                EnterpriseButton {{
                    background-color: {COLOR_SIDEBAR_ACTIVE_BG};
                    color: {COLOR_TEXT_PRIMARY};
                    border: none;
                    border-left: 3px solid {COLOR_SIDEBAR_ACTIVE_BORDER};
                    border-radius: {BORDER_RADIUS_MD}px;
                    text-align: left;
                    padding-left: {SPACING_LG - 3}px;
                    font-weight: 600;
                }}
                EnterpriseButton:hover {{
                    background-color: {COLOR_SIDEBAR_ACTIVE_BG};
                    color: {COLOR_TEXT_PRIMARY};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                EnterpriseButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_SECONDARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_MD}px;
                    text-align: left;
                    padding-left: {SPACING_LG}px;
                    font-weight: 400;
                }}
                EnterpriseButton:hover {{
                    background-color: {COLOR_BG_HOVER};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                EnterpriseButton:pressed {{
                    background-color: {COLOR_BG_FOCUS};
                    color: {COLOR_TEXT_PRIMARY};
                }}
            """)

    def set_active_item(self, index: int, emit_signal: bool = True):
        """Set the active navigation item by index, updating visual state."""
        if hasattr(self, 'group_items') and index in self.group_items:
            if hasattr(self, 'nav_list'):
                self.nav_list._current_row = index
            return
        if index < 0:
            index = 0
        if hasattr(self, 'nav_list') and index >= self.nav_list.count():
            index = self.nav_list.count() - 1
        # Find the button matching this index
        for page_id, btn in self._navigation_items.items():
            btn_index = btn.property("page_index")
            if btn_index == index:
                # Deactivate previous active item
                if self._active_page_id and self._active_page_id in self._navigation_items:
                    prev_btn = self._navigation_items[self._active_page_id]
                    self._set_button_active(prev_btn, False)
                # Activate new item
                self._active_page_id = page_id
                self._set_button_active(btn, True)
                if hasattr(self, 'nav_list'):
                    self.nav_list._current_row = index
                # Auto-expand the group containing the active item (Phase Recovery)
                self._expand_group_for_item(btn)
                if emit_signal:
                    title = btn.text().strip()
                    self.page_changed.emit(index, title)
                break

    def _expand_group_for_item(self, btn):
        """Auto-expand the parent group of the given item if collapsed."""
        for group_name, group_widget in self._group_widgets.items():
            if not self._expanded_groups.get(group_name, False):
                layout = group_widget.layout()
                if layout:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() and btn in item.widget().findChildren(type(btn)):
                            self._expanded_groups[group_name] = True
                            self._toggle_group(group_name)
                            return

    def update_theme(self, theme_name):
        """Update sidebar styling based on theme."""
        self._refresh_all_styles()

    def _apply_theme_style(self):
        """Apply theme-specific sidebar styling."""
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {COLOR_BG_ELEVATED};
                border-right: 1px solid {COLOR_BORDER};
            }}
            QLabel#sidebar_header {{
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
                padding: {SPACING_SM}px;
            }}
        """)

    def _refresh_all_styles(self):
        """Re-apply all sidebar stylesheets with current theme colors."""
        self._apply_theme_style()
        # Scroll area (cached ref — no findChildren)
        if hasattr(self, '_scroll_area'):
            self._scroll_area.setStyleSheet(f"""
                QScrollArea {{ 
                    border: none; 
                    background-color: {COLOR_BG_MAIN}; 
                }}
                QScrollArea>QWidget>QScrollBar:vertical {{
                    background: {COLOR_BG_MAIN};
                    width: 8px;
                }}
                QScrollArea>QWidget>QScrollBar::handle:vertical {{
                    background: {COLOR_BORDER};
                    border-radius: {BORDER_RADIUS_SM}px;
                }}
                QScrollArea>QWidget>QScrollBar::add-line:vertical, 
                QScrollArea>QWidget>QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)
            if hasattr(self, '_scroll_content'):
                self._scroll_content.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        # Brand frame (cached ref)
        if hasattr(self, '_brand_frame'):
            self._brand_frame.setStyleSheet(f"""
                QFrame#sidebarBrand {{
                    background-color: {COLOR_BG_ELEVATED};
                    border-bottom: 1px solid {COLOR_BORDER};
                }}
            """)
        if hasattr(self, '_brand_label'):
            self._brand_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        if hasattr(self, '_brand_subtitle'):
            self._brand_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        if hasattr(self, '_brand_badge'):
            self._brand_badge.setStyleSheet(f"color: {COLOR_PRIMARY};")

        # Navigation section background (cached ref)
        if hasattr(self, '_nav_section'):
            self._nav_section.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        # All navigation buttons
        for page_id, btn in self._navigation_items.items():
            btn.setStyleSheet(f"""
                EnterpriseButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_SECONDARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_MD}px;
                    text-align: left;
                    padding-left: {SPACING_LG}px;
                    font-weight: 400;
                }}
                EnterpriseButton:hover {{
                    background-color: {COLOR_BG_HOVER};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                EnterpriseButton:pressed {{
                    background-color: {COLOR_BG_FOCUS};
                    color: {COLOR_TEXT_PRIMARY};
                }}
            """)

        # Group headers
        for group_name in self._expanded_groups:
            header_btn = getattr(self, f"_{group_name}_header", None)
            if header_btn:
                header_btn.setStyleSheet(f"""
                    EnterpriseButton {{
                        background-color: transparent;
                        border: none;
                        text-align: left;
                        padding-left: {SPACING_SM}px;
                        color: {COLOR_TEXT_PRIMARY};
                        font-weight: bold;
                        font-size: {TEXT_CARD_TITLE}pt;
                    }}
                    EnterpriseButton:hover {{
                        background-color: {COLOR_BG_HOVER};
                    }}
                """)
                arrow = getattr(header_btn, '_arrow', None)
                if arrow:
                    arrow.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: {TEXT_BODY}pt;")
                for c in header_btn.findChildren(QLabel):
                    if c is not arrow:
                        c.setStyleSheet(f"color: {COLOR_PRIMARY};")

        # Bottom frame with logout (cached ref)
        if hasattr(self, '_bottom_frame') and hasattr(self, 'logout_btn'):
            self.logout_btn.setStyleSheet(f"""
                EnterpriseButton {{
                    background-color: {COLOR_DANGER};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_LG}px;
                    padding: {SPACING_MD}px;
                }}
                EnterpriseButton:hover {{
                    background-color: {COLOR_DANGER_HOVER};
                }}
                EnterpriseButton:pressed {{
                    background-color: {COLOR_DANGER_ACTIVE};
                }}
            """)
            self._bottom_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE};")

