"""Pytest configuration for frontend UI tests."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from unittest.mock import MagicMock, patch


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "qt: tests requiring PySide6"
    )
    config.addinivalue_line(
        "markers", "navigation: sidebar and page navigation tests"
    )
    config.addinivalue_line(
        "markers", "theme: theme system tests"
    )
    config.addinivalue_line(
        "markers", "widgets: reusable widget tests"
    )
    config.addinivalue_line(
        "markers", "validation: form validation tests"
    )
    config.addinivalue_line(
        "markers", "integration: live backend integration tests"
    )
    config.addinivalue_line(
        "markers", "auth: authentication integration tests"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )


@pytest.fixture(scope="session")
def frontend_path():
    """Get frontend path."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture(scope="session")
def backend_path():
    """Get backend path for integration tests."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


@pytest.fixture(scope="session")
def api_base_url():
    """Get API base URL from environment."""
    return os.environ.get("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="function")
def mock_api_client():
    """Create a mock API client for testing."""
    client = MagicMock()
    client.get = MagicMock(return_value={"results": []})
    client.post = MagicMock(return_value={"id": 1, "success": True})
    client.put = MagicMock(return_value={"id": 1, "success": True})
    client.delete = MagicMock(return_value={"success": True})
    return client


@pytest.fixture(scope="function")
def mock_license_validator():
    """Create a mock license validator."""
    validator = MagicMock()
    validator.get_license_status.return_value = {
        "is_valid": True,
        "message": "Valid",
        "expiry_date": "2026-12-31"
    }
    validator.check_license.return_value = True
    return validator


@pytest.fixture(scope="function")
def sidebar_widget(qtbot):
    """Create a sidebar widget for testing."""
    from ui.sidebar import Sidebar
    widget = Sidebar()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture(scope="function")
def main_window_widget(qtbot, mock_license_validator):
    """Create a main window widget for testing."""
    from ui.main_window import MainWindow
    from unittest.mock import patch, MagicMock

    with patch('ui.main_window.LicenseManagerDialog'):
        with patch('ui.main_window.QApplication.instance'):
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


@pytest.fixture(scope="function")
def theme_engine(qtbot):
    """Create a theme engine for testing (SSOT)."""
    from theme.theme_engine import ThemeEngine
    return ThemeEngine.instance()


@pytest.fixture(scope="function")
def theme_manager(qtbot):
    """DEPRECATED — Use theme_engine instead."""
    from theme.theme_engine import ThemeEngine
    return ThemeEngine.instance()


@pytest.fixture(scope="function")
def product_form_dialog(qtbot, mock_api_client):
    """Create a product form dialog for testing."""
    from ui.inventory.components.product_form import ProductFormDialog
    dialog = ProductFormDialog(api_client=mock_api_client)
    qtbot.addWidget(dialog)
    return dialog


@pytest.fixture(scope="function")
def barcode_search_widget(qtbot, mock_api_client):
    """Create a barcode search widget for testing."""
    from ui.common.barcode_search import BarcodeSearchLineEdit
    widget = BarcodeSearchLineEdit(api_client=mock_api_client)
    qtbot.addWidget(widget)
    return widget


# New UI Component Fixtures

@pytest.fixture
def enterprise_button(qtbot):
    """Create enterprise button for testing."""
    pytest.importorskip("PySide6")
    from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
    button = EnterpriseButton(
        text="Test Button",
        variant=ButtonVariant.PRIMARY,
        size=ButtonSize.MEDIUM
    )
    qtbot.addWidget(button)
    return button
    
@pytest.fixture
def enterprise_table(qtbot):
    """Create enterprise table for testing."""
    pytest.importorskip("PySide6")
    from ui.components.tables import EnterpriseTable, TableColumn
    columns = [
        TableColumn("id", "ID", 50),
        TableColumn("name", "Name", 200),
        TableColumn("price", "Price", 100)
    ]
    table = EnterpriseTable(columns)
    qtbot.addWidget(table)
    return table
    
@pytest.fixture
def form_field(qtbot):
    """Create form field for testing."""
    pytest.importorskip("PySide6")
    from ui.components.forms import FormField, FieldType
    field = FormField(
        field_type=FieldType.TEXT,
        label="Test Field",
        name="test_field",
        required=True
    )
    qtbot.addWidget(field)
    return field
    
@pytest.fixture
def notification_manager(qtbot):
    """Create notification manager for testing."""
    pytest.importorskip("PySide6")
    from ui.components.notifications import NotificationManager
    manager = NotificationManager()
    return manager
    
@pytest.fixture
def locale_manager():
    """Create locale manager for testing."""
    from i18n.localization import LocaleManager
    manager = LocaleManager()
    return manager
    
@pytest.fixture
def date_formatter():
    """Create date formatter for testing."""
    from i18n.localization import DateFormatter
    return DateFormatter
    
@pytest.fixture
def currency_formatter():
    """Create currency formatter for testing."""
    from i18n.localization import CurrencyFormatter
    return CurrencyFormatter