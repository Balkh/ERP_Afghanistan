from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                                 QLabel, QFrame, QPushButton, QSizePolicy, QToolButton, QScrollArea)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon
from theme.theme_engine import ThemeEngine
from ui.role_manager import UserRole, get_visible_navigation_items, is_navigation_item_visible
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, BORDER_RADIUS_MD, BORDER_RADIUS_SM, BORDER_RADIUS_LG)
from ui.constants import (TEXT_CARD_TITLE, TEXT_LABEL, TEXT_BODY_SMALL)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


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
        
        # Setup UI
        self.setup_ui()
        
        # Apply role-based visibility if role is set
        if self._role:
            self.apply_role_filter(self._role)
        
        # Connect theme changes (unified ThemeEngine — single source of truth)
        ThemeEngine.instance().theme_changed.connect(self.update_theme)
    
    def set_role(self, role: UserRole):
        """Set the role and update navigation visibility."""
        self._role = role
        self.apply_role_filter(role)

    def set_module_visibility(self, module: str, visible: bool) -> None:
        """Show/hide a module group in the sidebar. Used by RoleRenderer."""
        group_widget = self._group_widgets.get(module)
        header_frame = getattr(self, f"_{module}_header", None)
        if group_widget:
            group_widget.setVisible(visible)
        if header_frame:
            header_frame.setVisible(visible)
    
    def apply_role_filter(self, role: UserRole):
        """Apply role-based visibility filter to navigation items."""
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
                "returns": {"returns"},
                "accounting": {"chart_of_accounts", "journal_entries", "account_ledger"},
                "reports": {"trial_balance", "profit_loss", "balance_sheet", "ar_ageing", "ap_ageing"},
                "finance": {"payments", "expenses", "budgeting", "tax", "cost_centers", "cashflow"},
                "hr": {"employees", "attendance", "leave", "payroll"},
                "hr_reports": {"employee_summary", "attendance_report", "leave_report", "overtime_report"},
                "payroll_reports": {"payroll_summary", "payroll_trend", "payroll_dept_cost", "payroll_emp_history"},
                "cash_flow": {"cash_flow"},
                "system": {"analytics", "operations", "observability", "decision_workspace", "invoice_templates", "entities", "licensing", "production", "fixed_assets", "backup", "audit", "user_management"}
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
                border-radius: {BORDER_RADIUS_SM};
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
        layout.setSpacing(0)
        
        # Brand/logo area
        brand_frame = QFrame()
        brand_frame.setFixedHeight(80)
        brand_frame.setStyleSheet(f"background-color: {COLOR_PRIMARY};")
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        
        brand_label = QLabel("💊 Pharmacy ERP")
        brand_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        brand_label.setStyleSheet(f"color: {COLOR_BG_MAIN};")
        brand_layout.addWidget(brand_label)
        self._brand_frame = brand_frame
        self._brand_label = brand_label
        
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
            ("POS Terminal", "pos", 10),
            ("Customers", "customers", 7),
        ])
        
        self._create_group(nav_layout, "Purchases", "purchases", [
            ("Purchase Invoice", "purchase_invoice", 6),
            ("Suppliers", "suppliers", 8),
        ])
        
        self._create_group(nav_layout, "Returns", "returns", [
            ("Return Orders", "returns", 9),
        ])
        
        self._create_group(nav_layout, "Accounting", "accounting", [
            ("Chart of Accounts", "chart_of_accounts", 10),
            ("Journal Entries", "journal_entries", 11),
            ("Account Ledger", "account_ledger", 12),
        ])
        
        self._create_group(nav_layout, "Reports", "reports", [
            ("Trial Balance", "trial_balance", 13),
            ("Profit & Loss", "profit_loss", 14),
            ("Balance Sheet", "balance_sheet", 15),
            ("Cash Flow", "cash_flow", 48),
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
        ])
        
        self._create_group(nav_layout, "HR", "hr", [
            ("Employees", "employees", 23),
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
            ("Analytics Workspace", "analytics", 32),
            ("Operations Dashboard", "operations", 38),
            ("Observability Console", "observability", 39),
            ("Decision Support", "decision_workspace", 47),
            ("Invoice Templates", "invoice_templates", 33),
            ("Business Entities", "entities", 35),
            ("Licensing", "licensing", 36),
            ("Production", "production", 37),
            ("Fixed Assets", "fixed_assets", 29),
            ("Backup & Restore", "backup", 27),
            ("Audit Log", "audit", 30),
            ("User Management", "user_management", 31),
        ])
        
        nav_layout.addWidget(self._create_nav_button("Settings", "settings", 28))
        
        # Add stretch to push content up
        nav_layout.addStretch()
        
        layout.addWidget(self._nav_section)
        
        # Bottom section
        self._bottom_frame = QFrame()
        self._bottom_frame.setFixedHeight(60)
        self._bottom_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE};")
        bottom_layout = QVBoxLayout(self._bottom_frame)
        bottom_layout.setContentsMargins(MARGIN_PAGE,  SPACING_SM,  MARGIN_PAGE,  SPACING_SM)
        
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_DANGER};
                color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
                border-radius: {BORDER_RADIUS_LG};
                padding: {SPACING_MD}px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        bottom_layout.addWidget(self.logout_btn)
        
        layout.addWidget(self._bottom_frame)
        
        # Set scroll area content
        self._scroll_area.setWidget(scroll_content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._scroll_area)
    
    def _create_nav_button(self, title, page_id, page_index):
        """Create a navigation button."""
        btn = QPushButton(f"  {title}")
        btn.setFont(QFont("Segoe UI", TEXT_LABEL))
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                border: none;
                border-radius: {BORDER_RADIUS_MD};
                text-align: left;
                padding-left: 15px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BORDER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BORDER_LIGHT};
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
        # Group container widget
        group_widget = QWidget()
        group_widget.setStyleSheet("background-color: transparent;")
        group_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        # Group header (clickable for expand/collapse)
        header_btn = QPushButton()
        header_btn.setCursor(Qt.PointingHandCursor)
        header_btn.setFixedHeight(40)
        header_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                padding-left: 10px;
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
                font-size: {TEXT_CARD_TITLE}px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BG_ELEVATED};
            }}
        """)

        # Header layout
        header_layout = QHBoxLayout(header_btn)
        header_layout.setContentsMargins(SPACING_SM,  0,  SPACING_SM,  0)

        # Arrow indicator
        arrow_label = QLabel("▶")
        arrow_label.setFixedWidth(20)
        arrow_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: {TEXT_LABEL}px;")

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLOR_PRIMARY};")

        header_layout.addWidget(arrow_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Store arrow for state updates
        header_btn._arrow = arrow_label

        group_layout.addWidget(header_btn)

        # Store header reference
        setattr(self, f"_{group_name}_header", header_btn)

        # Child items container
        items_widget = QWidget()
        items_widget.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        items_layout = QVBoxLayout(items_widget)
        items_layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XS,  SPACING_SM,  SPACING_SM)
        items_layout.setSpacing(SPACING_XS)

        for item_title, page_id, page_index in items:
            btn = self._create_nav_button(item_title, page_id, page_index)
            items_layout.addWidget(btn)

        group_layout.addWidget(items_widget)

        # Store group container
        self._group_widgets[group_name] = group_widget
        parent_layout.addWidget(group_widget)

        # Connect toggle
        header_btn.clicked.connect(lambda checked, g=group_name: self._toggle_group(g))

        # Set initial state (collapsed by default)
        is_expanded = self._expanded_groups.get(group_name, False)
        if not is_expanded:
            items_widget.setVisible(False)
            items_widget.setMaximumHeight(0)
            arrow_label.setText("▶")
            if header_btn:
                header_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        text-align: left;
                        padding-left: 10px;
                        color: {COLOR_TEXT_PRIMARY};
                        font-weight: bold;
                        font-size: {TEXT_CARD_TITLE}px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLOR_BG_ELEVATED};
                    }}
                """)
            group_widget.setMaximumHeight(50)
        else:
            arrow_label.setText("▼")
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
        
        # Get the items widget 
        items_widget = None
        layout = group_widget.layout()
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget != header_btn:
                items_widget = widget
                break

        if new_state:  # Should be expanded
            if items_widget:
                items_widget.setVisible(True)
                items_widget.setMaximumHeight(16777215)
            if header_btn and hasattr(header_btn, '_arrow'):
                header_btn._arrow.setText("▼")
            group_widget.setMaximumHeight(16777215)
        else:  # Should be collapsed
            if items_widget:
                items_widget.setVisible(False)
                items_widget.setMaximumHeight(0)
            if header_btn and hasattr(header_btn, '_arrow'):
                header_btn._arrow.setText("▶")
            group_widget.setMaximumHeight(50)

        group_widget.layout().invalidate()
        group_widget.update()
        
        # Force layout update
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

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
    
    def set_active_item(self, index):
        """Set the active item programmatically."""
        pass

    def update_theme(self, theme_name):
        """Update sidebar styling based on theme."""
        self._refresh_all_styles()

    def _refresh_all_styles(self):
        """Re-apply all sidebar stylesheets with current theme colors."""
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
                    border-radius: {BORDER_RADIUS_SM};
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
            self._brand_frame.setStyleSheet(f"background-color: {COLOR_PRIMARY};")
        if hasattr(self, '_brand_label'):
            self._brand_label.setStyleSheet(f"color: {COLOR_BG_MAIN};")

        # Navigation section background (cached ref)
        if hasattr(self, '_nav_section'):
            self._nav_section.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        # All navigation buttons
        for page_id, btn in self._navigation_items.items():
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_PRIMARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_MD};
                    text-align: left;
                    padding-left: 15px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BORDER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_BORDER_LIGHT};
                }}
            """)

        # Group headers
        for group_name in self._expanded_groups:
            header_btn = getattr(self, f"_{group_name}_header", None)
            if header_btn:
                header_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        text-align: left;
                        padding-left: 10px;
                        color: {COLOR_TEXT_PRIMARY};
                        font-weight: bold;
                        font-size: {TEXT_CARD_TITLE}px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLOR_BG_ELEVATED};
                    }}
                """)
                arrow = getattr(header_btn, '_arrow', None)
                if arrow:
                    arrow.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: {TEXT_BODY}px;")
                for c in header_btn.findChildren(QLabel):
                    if c is not arrow:
                        c.setStyleSheet(f"color: {COLOR_PRIMARY};")

        # Bottom frame with logout (cached ref)
        if hasattr(self, '_bottom_frame') and hasattr(self, 'logout_btn'):
            self.logout_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_DANGER};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_LG};
                padding: {SPACING_MD}px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_HOVER};
                }}
            """)
            self._bottom_frame.setStyleSheet(f"background-color: {COLOR_BG_SURFACE};")

