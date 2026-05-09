"""
Smoke tests for critical ERP flows.

Lightweight integration tests for core user workflows.
These tests verify the system doesn't crash on critical paths.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


pytestmark = pytest.mark.qt


class TestLoginFlow:
    """Test login flow smoke tests."""

    @pytest.fixture
    def login_screen(self, qtbot):
        """Create login screen with mocked backend."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.post = MagicMock(return_value={
                "success": True,
                "data": {"token": "test-token", "user": {"id": 1, "username": "admin"}}
            })
            mock_api.return_value = mock_client

            from ui.auth.login_screen import LoginScreen
            screen = LoginScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_login_screen_exists(self, login_screen):
        """Login screen should exist."""
        assert login_screen is not None

    def test_username_field_exists(self, login_screen):
        """Login should have username field."""
        from PySide6.QtWidgets import QLineEdit
        assert login_screen.findChild(QLineEdit) is not None

    def test_password_field_exists(self, login_screen):
        """Login should have password field."""
        from PySide6.QtWidgets import QLineEdit
        fields = login_screen.findChildren(QLineEdit)
        assert len(fields) >= 2

    def test_login_button_exists(self, login_screen):
        """Login should have login button."""
        from PySide6.QtWidgets import QPushButton
        buttons = login_screen.findChildren(QPushButton)
        assert any(b.text() for b in buttons)


class TestNavigationFlow:
    """Test navigation smoke tests."""

    @pytest.fixture
    def sidebar_fixture(self, qtbot):
        """Create sidebar for testing."""
        with patch('ui.sidebar.ThemeManager'):
            from ui.sidebar import Sidebar
            sidebar = Sidebar()
            qtbot.addWidget(sidebar)
            yield sidebar
            sidebar.close()

    def test_sidebar_exists(self, sidebar_fixture):
        """Sidebar should exist."""
        assert sidebar_fixture is not None

    def test_navigation_buttons_exist(self, sidebar_fixture):
        """Sidebar should have navigation buttons."""
        from PySide6.QtWidgets import QPushButton
        buttons = sidebar_fixture.findChildren(QPushButton)
        assert len(buttons) > 0

    def test_dashboard_button_exists(self, sidebar_fixture):
        """Should have dashboard button."""
        assert hasattr(sidebar_fixture, 'dashboard_btn')

    def test_group_expand_collapse_works(self, sidebar_fixture, qtbot):
        """Group expand/collapse should not crash."""
        sidebar_fixture._toggle_group("accounting")
        sidebar_fixture._toggle_group("accounting")


class TestInvoiceCreateFlow:
    """Test invoice creation smoke tests."""

    @pytest.fixture
    def sales_invoice_screen(self, qtbot):
        """Create sales invoice screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.post = MagicMock(return_value={"success": True, "id": 1})
            mock_api.return_value = mock_client

            from ui.sales.sales_invoice_screen import SalesInvoiceScreen
            screen = SalesInvoiceScreen(api_client=mock_client)
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_invoice_screen_exists(self, sales_invoice_screen):
        """Invoice screen should exist."""
        assert sales_invoice_screen is not None

    def test_has_customer_combo(self, sales_invoice_screen):
        """Invoice screen should have customer combo."""
        assert hasattr(sales_invoice_screen, 'customer_combo')

    def test_has_items_table(self, sales_invoice_screen):
        """Invoice screen should have items table."""
        assert hasattr(sales_invoice_screen, 'items_table')

    def test_has_save_method(self, sales_invoice_screen):
        """Invoice screen should have save method."""
        assert hasattr(sales_invoice_screen, 'save_invoice')


class TestPaymentCreateFlow:
    """Test payment creation smoke tests."""

    @pytest.fixture
    def payment_screen(self, qtbot):
        """Create payment screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.finance.payment_screen import PaymentScreen
            screen = PaymentScreen(api_client=mock_client)
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_payment_screen_exists(self, payment_screen):
        """Payment screen should exist."""
        assert payment_screen is not None

    def test_has_type_filter(self, payment_screen):
        """Payment screen should have type filter."""
        assert hasattr(payment_screen, 'type_combo')

    def test_has_table(self, payment_screen):
        """Payment screen should have table."""
        assert payment_screen.table is not None


class TestInventoryProductFlow:
    """Test inventory product flow smoke tests."""

    @pytest.fixture
    def product_screen(self, qtbot):
        """Create product screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.inventory.product_screen import ProductScreen
            screen = ProductScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_product_screen_exists(self, product_screen):
        """Product screen should exist."""
        assert product_screen is not None

    def test_has_table(self, product_screen):
        """Product screen should have table."""
        assert product_screen.table is not None

    def test_has_load_method(self, product_screen):
        """Product screen should have load method."""
        assert hasattr(product_screen, 'load_products')

    def test_has_add_button(self, product_screen):
        """Product screen should have add button."""
        assert hasattr(product_screen, 'add_new_btn')


class TestCustomerCreateFlow:
    """Test customer creation smoke tests."""

    @pytest.fixture
    def customer_screen(self, qtbot):
        """Create customer screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.sales.customer_screen import CustomerScreen
            screen = CustomerScreen(api_client=mock_client)
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_customer_screen_exists(self, customer_screen):
        """Customer screen should exist."""
        assert customer_screen is not None

    def test_has_table(self, customer_screen):
        """Customer screen should have table."""
        assert customer_screen.table is not None


class TestSupplierCreateFlow:
    """Test supplier creation smoke tests."""

    @pytest.fixture
    def supplier_screen(self, qtbot):
        """Create supplier screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.purchases.supplier_screen import SupplierScreen
            screen = SupplierScreen(api_client=mock_client)
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_supplier_screen_exists(self, supplier_screen):
        """Supplier screen should exist."""
        assert supplier_screen is not None


class TestReportScreensFlow:
    """Test report screen smoke tests."""

    @pytest.fixture
    def trial_balance_screen(self, qtbot):
        """Create trial balance screen."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={
                "accounts": [],
                "total_debit": 0,
                "total_credit": 0,
                "is_balanced": True
            })
            mock_api.return_value = mock_client

            from ui.accounting.trial_balance_screen import TrialBalanceScreen
            screen = TrialBalanceScreen()
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_trial_balance_screen_exists(self, trial_balance_screen):
        """Trial balance screen should exist."""
        assert trial_balance_screen is not None

    def test_has_run_button(self, trial_balance_screen):
        """Trial balance should have run button."""
        assert hasattr(trial_balance_screen, 'btn_run')


class TestWorkflowFlow:
    """Test workflow state smoke tests."""

    @pytest.fixture
    def sales_invoice_workflow(self, qtbot):
        """Create sales invoice screen with workflow."""
        with patch('api.client.APIClient') as mock_api:
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_client.get_workflow_status = MagicMock(return_value={
                "success": True,
                "data": {"has_workflow": False}
            })
            mock_api.return_value = mock_client

            from ui.sales.sales_invoice_screen import SalesInvoiceScreen
            screen = SalesInvoiceScreen(api_client=mock_client)
            qtbot.addWidget(screen)
            yield screen
            screen.close()

    def test_workflow_buttons_exist(self, sales_invoice_workflow):
        """Invoice should have workflow buttons."""
        assert hasattr(sales_invoice_workflow, 'submit_wf_btn')

    def test_workflow_status_label_exists(self, sales_invoice_workflow):
        """Invoice should have workflow status label."""
        assert hasattr(sales_invoice_workflow, 'workflow_status_label')


class TestLoadingStatesFlow:
    """Test loading state smoke tests."""

    def test_payment_screen_loading_states(self, qtbot):
        """Payment screen should handle loading states."""
        with patch('api.client.APIClient') as mock_api:
            from unittest.mock import MagicMock
            mock_client = MagicMock()
            mock_client.get = MagicMock(return_value={"results": []})
            mock_api.return_value = mock_client

            from ui.finance.payment_screen import PaymentScreen
            screen = PaymentScreen(api_client=mock_client)
            qtbot.addWidget(screen)

            assert hasattr(screen, '_show_loading')
            assert hasattr(screen, '_show_empty')
            assert hasattr(screen, '_show_data')

            screen.close()