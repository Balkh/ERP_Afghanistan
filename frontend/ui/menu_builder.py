"""Menu bar factory for MainWindow.

Extracted from ui/main_window.py to reduce God Object responsibilities.
Provides a single ``create_menu_bar()`` function that populates a QMenuBar
with all application menus and actions, wiring signals to the given
``main_window`` instance.

This is a **pure extraction** -- zero new abstractions, zero behavior changes.
"""

from PySide6.QtGui import QAction


def create_menu_bar(menubar, main_window):
    """Populate *menubar* with all application menus and actions.

    Parameters
    ----------
    menubar : QMenuBar
        The menu bar to populate (typically ``main_window.menuBar()``).
    main_window : MainWindow
        The application main window.  Menu actions are connected to its
        public methods (``refresh_current_view``, ``logout``, etc.).
    """
    # File menu
    file_menu = menubar.addMenu('File')

    refresh_action = QAction('Refresh', main_window)
    refresh_action.setStatusTip('Refresh current view')
    refresh_action.triggered.connect(main_window.refresh_current_view)
    file_menu.addAction(refresh_action)

    file_menu.addSeparator()

    logout_action = QAction('Logout', main_window)
    logout_action.setStatusTip('Logout and return to login')
    logout_action.triggered.connect(main_window.logout)
    file_menu.addAction(logout_action)

    # Edit menu
    edit_menu = menubar.addMenu('Edit')

    preferences_action = QAction('Preferences', main_window)
    preferences_action.setStatusTip('Open application preferences')
    preferences_action.triggered.connect(main_window.show_preferences)
    edit_menu.addAction(preferences_action)

    # View menu
    view_menu = menubar.addMenu('View')

    fullscreen_action = QAction('Toggle Fullscreen', main_window)
    fullscreen_action.setStatusTip('Toggle fullscreen mode')
    fullscreen_action.setShortcut('F11')
    fullscreen_action.triggered.connect(main_window.toggle_fullscreen)
    view_menu.addAction(fullscreen_action)

    view_menu.addSeparator()

    nav_dashboard = QAction('Go to Dashboard', main_window)
    nav_dashboard.setShortcut('Ctrl+1')
    nav_dashboard.triggered.connect(lambda: main_window.navigate_to("dashboard"))
    view_menu.addAction(nav_dashboard)

    nav_products = QAction('Go to Products', main_window)
    nav_products.setShortcut('Ctrl+2')
    nav_products.triggered.connect(lambda: main_window.navigate_to("products"))
    view_menu.addAction(nav_products)

    nav_customers = QAction('Go to Customers', main_window)
    nav_customers.setShortcut('Ctrl+3')
    nav_customers.triggered.connect(lambda: main_window.navigate_to("customers"))
    view_menu.addAction(nav_customers)

    # Operations menu
    operations_menu = menubar.addMenu('Operations')

    new_product_action = QAction('New Product', main_window)
    new_product_action.setStatusTip('Create a new product')
    new_product_action.setShortcut('Ctrl+N')
    new_product_action.triggered.connect(main_window.new_product)
    operations_menu.addAction(new_product_action)

    new_invoice_action = QAction('New Sales Invoice', main_window)
    new_invoice_action.setStatusTip('Create a new sales invoice')
    new_invoice_action.setShortcut('Ctrl+Shift+S')
    new_invoice_action.triggered.connect(lambda: main_window.navigate_to("sales_invoice"))
    operations_menu.addAction(new_invoice_action)

    operations_menu.addSeparator()

    inventory_check_action = QAction('Stock Alert Report', main_window)
    inventory_check_action.setStatusTip('View low stock items')
    inventory_check_action.triggered.connect(main_window.show_stock_alerts)
    operations_menu.addAction(inventory_check_action)

    # Reports menu
    reports_menu = menubar.addMenu('Reports')

    trial_balance_action = QAction('Trial Balance', main_window)
    trial_balance_action.triggered.connect(lambda: main_window.navigate_to("trial_balance"))
    reports_menu.addAction(trial_balance_action)

    profit_loss_action = QAction('Profit & Loss', main_window)
    profit_loss_action.triggered.connect(lambda: main_window.navigate_to("profit_loss"))
    reports_menu.addAction(profit_loss_action)

    balance_sheet_action = QAction('Balance Sheet', main_window)
    balance_sheet_action.triggered.connect(lambda: main_window.navigate_to("balance_sheet"))
    reports_menu.addAction(balance_sheet_action)

    reports_menu.addSeparator()

    ar_aging_action = QAction('AR Ageing Report', main_window)
    ar_aging_action.triggered.connect(lambda: main_window.navigate_to("ar_ageing"))
    reports_menu.addAction(ar_aging_action)

    ap_aging_action = QAction('AP Ageing Report', main_window)
    ap_aging_action.triggered.connect(lambda: main_window.navigate_to("ap_ageing"))
    reports_menu.addAction(ap_aging_action)

    # Tools menu
    tools_menu = menubar.addMenu('Tools')

    calc_action = QAction('Calculator', main_window)
    calc_action.setStatusTip('Open calculator')
    calc_action.triggered.connect(main_window.open_calculator)
    tools_menu.addAction(calc_action)

    calendar_action = QAction('Calendar', main_window)
    calendar_action.setStatusTip('Open calendar')
    calendar_action.triggered.connect(main_window.open_calendar)
    tools_menu.addAction(calendar_action)

    tools_menu.addSeparator()

    backup_action = QAction('Backup Database', main_window)
    backup_action.setStatusTip('Create database backup')
    backup_action.triggered.connect(lambda: main_window.navigate_to("backup"))
    tools_menu.addAction(backup_action)

    # Help menu
    help_menu = menubar.addMenu('Help')

    license_action = QAction('License Manager', main_window)
    license_action.setStatusTip('Manage Pharmacy ERP license')
    license_action.triggered.connect(main_window.show_license_manager)
    help_menu.addAction(license_action)

    help_menu.addSeparator()

    about_action = QAction('About', main_window)
    about_action.setStatusTip('About Pharmacy ERP')
    about_action.triggered.connect(main_window.show_about)
    help_menu.addAction(about_action)

    # Theme toggle on menu bar
    theme_toggle = QAction('Dark/Light', main_window)
    theme_toggle.setStatusTip('Switch between light and dark themes')
    theme_toggle.triggered.connect(main_window.toggle_theme)
    menubar.addAction(theme_toggle)
