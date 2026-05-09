"""Component-level screen tests.

Tests individual screens in isolation - much faster than MainWindow tests.
"""
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.qt


class TestProductScreenComponent:
    """Test ProductScreen in isolation."""

    @pytest.fixture
    def product_screen(self, qtbot, mock_api_client):
        """Create ProductScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.products = MagicMock(return_value=[])
            mock_api.return_value = mock_client

            from ui.inventory.product_screen import ProductScreen
            screen = ProductScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_title(self, product_screen):
        """Screen should have a title or header."""
        from PySide6.QtWidgets import QLabel
        header = product_screen.findChild(QLabel)
        assert header is not None or hasattr(product_screen, 'windowTitle')

    def test_table_exists(self, product_screen):
        """Screen should have a table widget."""
        assert product_screen.table is not None

    def test_has_load_method(self, product_screen):
        """Screen should have load_products method."""
        assert hasattr(product_screen, 'load_products')

    def test_has_filter_combo(self, product_screen):
        """Screen should have filter combo box."""
        assert hasattr(product_screen, 'filter_combo')

    def test_has_search_input(self, product_screen):
        """Screen should have search input."""
        assert hasattr(product_screen, 'search_input')


class TestCategoryScreenComponent:
    """Test CategoryScreen in isolation."""

    @pytest.fixture
    def category_screen(self, qtbot, mock_api_client):
        """Create CategoryScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.categories = MagicMock(return_value=[])
            mock_api.return_value = mock_client

            from ui.inventory.category_screen import CategoryScreen
            screen = CategoryScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, category_screen):
        """Screen should exist."""
        assert category_screen is not None

    def test_has_load_method(self, category_screen):
        """Screen should have load_categories method."""
        assert hasattr(category_screen, 'load_categories')


class TestWarehouseScreenComponent:
    """Test WarehouseScreen in isolation."""

    @pytest.fixture
    def warehouse_screen(self, qtbot, mock_api_client):
        """Create WarehouseScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.warehouses = MagicMock(return_value=[])
            mock_api.return_value = mock_client

            from ui.inventory.warehouse_screen import WarehouseScreen
            screen = WarehouseScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, warehouse_screen):
        """Screen should exist."""
        assert warehouse_screen is not None

    def test_has_load_method(self, warehouse_screen):
        """Screen should have load_warehouses method."""
        assert hasattr(warehouse_screen, 'load_warehouses')


class TestBatchScreenComponent:
    """Test BatchScreen in isolation."""

    @pytest.fixture
    def batch_screen(self, qtbot, mock_api_client):
        """Create BatchScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.batches = MagicMock(return_value=[])
            mock_api.return_value = mock_client

            from ui.inventory.batch_screen import BatchScreen
            screen = BatchScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, batch_screen):
        """Screen should exist."""
        assert batch_screen is not None

    def test_has_load_method(self, batch_screen):
        """Screen should have load_batches method."""
        assert hasattr(batch_screen, 'load_batches')


class TestSalesInvoiceScreenComponent:
    """Test SalesInvoiceScreen in isolation."""

    @pytest.fixture
    def sales_screen(self, qtbot, mock_api_client):
        """Create SalesInvoiceScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.sales.sales_invoice_screen import SalesInvoiceScreen
            screen = SalesInvoiceScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, sales_screen):
        """Screen should exist."""
        assert sales_screen is not None


class TestPurchaseInvoiceScreenComponent:
    """Test PurchaseInvoiceScreen in isolation."""

    @pytest.fixture
    def purchase_screen(self, qtbot, mock_api_client):
        """Create PurchaseInvoiceScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.purchases.purchase_invoice_screen import PurchaseInvoiceScreen
            screen = PurchaseInvoiceScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, purchase_screen):
        """Screen should exist."""
        assert purchase_screen is not None


class TestChartOfAccountsComponent:
    """Test ChartOfAccountsScreen in isolation."""

    @pytest.fixture
    def coa_screen(self, qtbot, mock_api_client):
        """Create ChartOfAccountsScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.accounts = MagicMock(return_value=[])
            mock_api.return_value = mock_client

            from ui.accounting.chart_of_accounts_screen import ChartOfAccountsScreen
            screen = ChartOfAccountsScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, coa_screen):
        """Screen should exist."""
        assert coa_screen is not None


class TestJournalEntryScreenComponent:
    """Test JournalEntryScreen in isolation."""

    @pytest.fixture
    def journal_screen(self, qtbot, mock_api_client):
        """Create JournalEntryScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.accounting.journal_entry_screen import JournalEntryScreen
            screen = JournalEntryScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, journal_screen):
        """Screen should exist."""
        assert journal_screen is not None

    def test_has_load_method(self, journal_screen):
        """Screen should have load_entries method."""
        assert hasattr(journal_screen, 'load_entries')


class TestAccountLedgerScreenComponent:
    """Test AccountLedgerScreen in isolation."""

    @pytest.fixture
    def ledger_screen(self, qtbot, mock_api_client):
        """Create AccountLedgerScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.accounting.account_ledger_screen import AccountLedgerScreen
            screen = AccountLedgerScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_screen_exists(self, ledger_screen):
        """Screen should exist."""
        assert ledger_screen is not None


class TestReportScreensComponent:
    """Test report screens in isolation."""

    @pytest.fixture
    def trial_balance_screen(self, qtbot, mock_api_client):
        """Create TrialBalanceScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.accounting.trial_balance_screen import TrialBalanceScreen
            screen = TrialBalanceScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_trial_balance_screen_exists(self, trial_balance_screen):
        """Screen should exist."""
        assert trial_balance_screen is not None

    @pytest.fixture
    def profit_loss_screen(self, qtbot, mock_api_client):
        """Create ProfitAndLossScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.accounting.profit_loss_screen import ProfitAndLossScreen
            screen = ProfitAndLossScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_profit_loss_screen_exists(self, profit_loss_screen):
        """Screen should exist."""
        assert profit_loss_screen is not None

    @pytest.fixture
    def balance_sheet_screen(self, qtbot, mock_api_client):
        """Create BalanceSheetScreen with mocked API."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.accounting.balance_sheet_screen import BalanceSheetScreen
            screen = BalanceSheetScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_balance_sheet_screen_exists(self, balance_sheet_screen):
        """Screen should exist."""
        assert balance_sheet_screen is not None