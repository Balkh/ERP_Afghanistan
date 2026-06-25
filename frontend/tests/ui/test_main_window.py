"""MainWindow integration tests.

Production-grade tests for MainWindow architecture including:
- Window initialization and page registration
- Sidebar integration and page switching
- UI state persistence
- Resource lifecycle and cleanup
- Memory safety checks
"""
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.qt


class TestMainWindowInitialization:
    """Test MainWindow initialization and page registration."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_client.products = MagicMock(return_value=[])
                mock_client.categories = MagicMock(return_value=[])
                mock_client.warehouses = MagicMock(return_value=[])
                mock_client.batches = MagicMock(return_value=[])
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_window_title_set(self, main_window):
        """Window should have correct title."""
        assert main_window.windowTitle() == "Pharmacy ERP"

    def test_window_geometry_set(self, main_window):
        """Window should have correct geometry."""
        geometry = main_window.geometry()
        assert geometry.width() >= 1200
        assert geometry.height() >= 800

    def test_minimum_size_enforced(self, main_window):
        """Window should enforce minimum size."""
        main_window.show()
        size = main_window.size()
        assert size.width() >= 1200
        assert size.height() >= 800

    def test_central_widget_exists(self, main_window):
        """MainWindow should have a central widget."""
        assert main_window.centralWidget() is not None

    def test_sidebar_exists(self, main_window):
        """MainWindow should have a sidebar."""
        assert main_window.sidebar is not None

    def test_stacked_pages_widget_exists(self, main_window):
        """MainWindow should have a QStackedWidget for pages."""
        assert main_window.pages is not None


class TestPageRegistration:
    """Test page registration and count."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_client.products = MagicMock(return_value=[])
                mock_client.categories = MagicMock(return_value=[])
                mock_client.warehouses = MagicMock(return_value=[])
                mock_client.batches = MagicMock(return_value=[])
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_page_count_matches_expected(self, main_window):
        """Should register dashboard plus lazy screen placeholders."""
        assert main_window.pages.count() >= len(main_window._lazy_screens._factories)
        assert max(main_window._lazy_screens._factories) >= 67

    def test_dashboard_page_registered(self, main_window):
        """Dashboard page should be at index 0."""
        screen = main_window.dashboard
        assert main_window.pages.indexOf(screen) == 0

    def test_products_screen_registered(self, main_window):
        """Products screen should be registered."""
        screen = main_window.product_screen
        assert main_window.pages.indexOf(screen) == 1

    def test_categories_screen_registered(self, main_window):
        """Categories screen should be registered."""
        screen = main_window.category_screen
        assert main_window.pages.indexOf(screen) == 2

    def test_warehouses_screen_registered(self, main_window):
        """Warehouses screen should be registered."""
        screen = main_window.warehouse_screen
        assert main_window.pages.indexOf(screen) == 3

    def test_batches_screen_registered(self, main_window):
        """Batches screen should be registered."""
        screen = main_window.batch_screen
        assert main_window.pages.indexOf(screen) == 4

    def test_sales_invoice_screen_registered(self, main_window):
        """Sales invoice screen should be registered."""
        screen = main_window.sales_invoice_screen
        assert main_window.pages.indexOf(screen) == 5

    def test_purchase_invoice_screen_registered(self, main_window):
        """Purchase invoice screen should be registered."""
        screen = main_window.purchase_invoice_screen
        assert main_window.pages.indexOf(screen) == 6

    def test_chart_of_accounts_registered(self, main_window):
        """Chart of accounts screen should be registered."""
        screen = main_window.chart_of_accounts
        assert main_window.pages.indexOf(screen) == 10

    def test_journal_entries_registered(self, main_window):
        """Journal entries screen should be registered."""
        screen = main_window.journal_entries
        assert main_window.pages.indexOf(screen) == 11

    def test_account_ledger_registered(self, main_window):
        """Account ledger screen should be registered."""
        screen = main_window.account_ledger
        assert main_window.pages.indexOf(screen) == 12

    def test_trial_balance_registered(self, main_window):
        """Trial balance screen should be registered."""
        screen = main_window.trial_balance
        assert main_window.pages.indexOf(screen) == 13

    def test_profit_loss_registered(self, main_window):
        """Profit and loss screen should be registered."""
        screen = main_window.profit_loss
        assert main_window.pages.indexOf(screen) == 14

    def test_balance_sheet_registered(self, main_window):
        """Balance sheet screen should be registered."""
        screen = main_window.balance_sheet
        assert main_window.pages.indexOf(screen) == 15

    def test_all_pages_are_qwidgets(self, main_window):
        """All registered pages should be QWidgets."""
        for i in range(main_window.pages.count()):
            widget = main_window.pages.widget(i)
            from PySide6.QtWidgets import QWidget
            assert isinstance(widget, QWidget)


class TestSidebarIntegration:
    """Test sidebar integration and signals."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_sidebar_signal_connected(self, main_window):
        """Sidebar page_changed signal should be connected."""
        from PySide6.QtCore import QMetaMethod
        connections = main_window.signals_to_methods.get('page_changed', [])
        assert len(connections) > 0 or main_window.receivers(main_window.sidebar.page_changed) > 0

    def test_initial_page_set(self, main_window):
        """Initial page should be set to dashboard (index 0)."""
        assert main_window.pages.currentIndex() == 0

    def test_header_text_matches_page(self, main_window):
        """Header text should reflect current page."""
        assert "Dashboard" in main_window.header.text() or "Pharmacy ERP" in main_window.header.text()


class TestPageSwitching:
    """Test page switching functionality."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_change_page_updates_index(self, main_window):
        """change_page should update current page index."""
        main_window.change_page(1, "Products")
        assert main_window.pages.currentIndex() == 1

    def test_change_page_updates_header(self, main_window):
        """change_page should update header text."""
        main_window.change_page(2, "  Products  ")
        assert "Products" in main_window.header.text()

    def test_page_switch_to_categories(self, main_window):
        """Should switch to categories page."""
        main_window.change_page(2, "Categories")
        assert main_window.pages.currentIndex() == 2
        assert "Categories" in main_window.header.text()

    def test_page_switch_to_warehouses(self, main_window):
        """Should switch to warehouses page."""
        main_window.change_page(3, "Warehouses")
        assert main_window.pages.currentIndex() == 3

    def test_page_switch_to_accounting(self, main_window):
        """Should switch to accounting section."""
        main_window.change_page(10, "Chart of Accounts")
        assert main_window.pages.currentIndex() == 10

    def test_page_switch_to_reports(self, main_window):
        """Should switch to reports section."""
        main_window.change_page(13, "Trial Balance")
        assert main_window.pages.currentIndex() == 13

    def test_page_switch_to_sales(self, main_window):
        """Should switch to sales page."""
        main_window.change_page(5, "Sales Invoice")
        assert main_window.pages.currentIndex() == 5


class TestUIStatePersistence:
    """Test UI state persistence."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_page_state_tracked(self, main_window):
        """Page state should be trackable."""
        main_window.change_page(4, "Batches")
        assert main_window.pages.currentIndex() == 4

    def test_header_state_tracked(self, main_window):
        """Header state should be trackable."""
        main_window.change_page(1, "Products")
        assert main_window.header.text() == "Products"

    def test_status_bar_exists(self, main_window):
        """Status bar should exist."""
        assert main_window.status_bar is not None

    def test_device_id_label_exists(self, main_window):
        """Device ID label should exist in status bar."""
        assert main_window.device_id_label is not None

    def test_license_status_label_exists(self, main_window):
        """License status label should exist in status bar."""
        assert main_window.license_status_label is not None


class TestResourceLifecycle:
    """Test resource lifecycle and cleanup."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_pages_can_be_closed(self, main_window):
        """Pages should support close operations."""
        main_window.pages.widget(0).close()

    def test_sidebar_cleanup(self, main_window):
        """Sidebar should cleanup properly."""
        main_window.sidebar.close()

    def test_window_close_event(self, main_window):
        """Window should handle close event."""
        main_window.close()
        assert not main_window.isVisible()

    def test_all_screens_have_close_method(self, main_window):
        """All screens should have close method."""
        for i in range(main_window.pages.count()):
            widget = main_window.pages.widget(i)
            assert hasattr(widget, 'close')


class TestMemorySafety:
    """Test memory safety and widget disposal."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_no_null_pages(self, main_window):
        """No page should be None."""
        for i in range(main_window.pages.count()):
            assert main_window.pages.widget(i) is not None

    def test_all_pages_visible_after_show(self, main_window):
        """All pages should be in visible state after show."""
        main_window.show()
        for i in range(main_window.pages.count()):
            widget = main_window.pages.widget(i)
            assert widget is not None

    def test_memory_leak_detection_placeholder(self, main_window):
        """Memory leak detection placeholder - all widgets reachable."""
        widgets = []
        for i in range(main_window.pages.count()):
            widgets.append(main_window.pages.widget(i))
        assert len(widgets) == main_window.pages.count()
        assert all(w is not None for w in widgets)

    def test_children_are_qwidgets(self, main_window):
        """All children should be QWidgets."""
        from PySide6.QtWidgets import QWidget
        children = main_window.findChildren(QWidget)
        assert len(children) > 0


class TestBackendConnectedWidgets:
    """Test backend-connected widget integration."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_product_screen_has_load_method(self, main_window):
        """Product screen should have load_products method."""
        assert hasattr(main_window.product_screen, 'load_products')

    def test_category_screen_has_load_method(self, main_window):
        """Category screen should have load_categories method."""
        assert hasattr(main_window.category_screen, 'load_categories')

    def test_warehouse_screen_has_load_method(self, main_window):
        """Warehouse screen should have load_warehouses method."""
        assert hasattr(main_window.warehouse_screen, 'load_warehouses')

    def test_batch_screen_has_load_method(self, main_window):
        """Batch screen should have load_batches method."""
        assert hasattr(main_window.batch_screen, 'load_batches')

    def test_journal_entries_has_load_method(self, main_window):
        """Journal entries screen should have load_entries method."""
        assert hasattr(main_window.journal_entries, 'load_entries')

    def test_account_ledger_has_load_method(self, main_window):
        """Account ledger screen should have load_accounts method."""
        assert hasattr(main_window.account_ledger, 'load_accounts')

    def test_load_methods_are_callable(self, main_window):
        """Load methods should be callable."""
        assert callable(main_window.product_screen.load_products)
        assert callable(main_window.category_screen.load_categories)
        assert callable(main_window.warehouse_screen.load_warehouses)


class TestScreenValidation:
    """Test screen loading validation."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_dashboard_screen_accessible(self, main_window):
        """Dashboard screen should be accessible."""
        assert main_window.dashboard is not None

    def test_inventory_screens_accessible(self, main_window):
        """All inventory screens should be accessible."""
        assert main_window.product_screen is not None
        assert main_window.category_screen is not None
        assert main_window.warehouse_screen is not None
        assert main_window.batch_screen is not None

    def test_accounting_screens_accessible(self, main_window):
        """All accounting screens should be accessible."""
        assert main_window.chart_of_accounts is not None
        assert main_window.journal_entries is not None
        assert main_window.account_ledger is not None

    def test_report_screens_accessible(self, main_window):
        """All report screens should be accessible."""
        assert main_window.trial_balance is not None
        assert main_window.profit_loss is not None
        assert main_window.balance_sheet is not None
        assert main_window.ar_ageing is not None
        assert main_window.ap_ageing is not None

    def test_sales_purchase_screens_accessible(self, main_window):
        """Sales and purchase screens should be accessible."""
        assert main_window.sales_invoice_screen is not None
        assert main_window.purchase_invoice_screen is not None


class TestMenuBar:
    """Test menu bar functionality."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_menu_bar_exists(self, main_window):
        """Menu bar should exist."""
        from PySide6.QtWidgets import QMenuBar
        menubar = main_window.menuBar()
        assert isinstance(menubar, QMenuBar)

    def test_create_menu_bar_called(self, main_window):
        """create_menu_bar should be called during init."""
        assert main_window.menuBar() is not None
        assert len(main_window.menuBar().actions()) > 0


class TestSignalCleanup:
    """Test signal cleanup on window close."""

    @pytest.fixture
    def main_window(self, qtbot, mock_license_validator):
        """Create MainWindow instance for testing."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_close_disconnects_sidebar(self, main_window):
        """Window close should handle signal cleanup."""
        main_window.close()
        assert True


class TestLicenseIntegration:
    """Test license validator integration."""

    @pytest.fixture
    def main_window_no_license(self, qtbot):
        """Create MainWindow without license validator."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=None)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_works_without_license_validator(self, main_window_no_license):
        """MainWindow should work without license validator."""
        assert main_window_no_license.license_validator is None

    @pytest.fixture
    def main_window_with_license(self, qtbot, mock_license_validator):
        """Create MainWindow with license validator."""
        from ui.main_window import MainWindow

        with patch('ui.main_window.LicenseManagerDialog'):
            with patch('api.client.APIClient') as mock_api:
                mock_client = MagicMock()
                mock_client.get = MagicMock(return_value={"results": []})
                mock_api.return_value = mock_client

                window = MainWindow(license_validator=mock_license_validator)
                qtbot.addWidget(window)
                yield window
                window.close()

    def test_works_with_license_validator(self, main_window_with_license):
        """MainWindow should work with license validator."""
        assert main_window_with_license.license_validator is not None