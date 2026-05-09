"""
Pytest configuration and fixtures for Pharmacy ERP backend tests.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from tests.factories import (
    CurrencyFactory,
    AccountFactory,
    WarehouseFactory,
    UnitFactory,
    CategoryFactory,
    ProductFactory,
    BatchFactory,
    CustomerFactory,
    SupplierFactory,
)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture
def default_currency():
    """Create default currency."""
    return CurrencyFactory.create(code='AFN', name='Afghan Afghani', symbol='\u060b', is_default=True)


@pytest.fixture
def base_accounts():
    """Create essential chart of accounts."""
    return {
        'cash': AccountFactory.create(code='1000', name='Cash', account_type='ASSET', is_system=True),
        'ar': AccountFactory.create(code='1200', name='Accounts Receivable', account_type='ASSET', is_system=True),
        'inventory': AccountFactory.create(code='1300', name='Inventory', account_type='ASSET', is_system=True),
        'ap': AccountFactory.create(code='2000', name='Accounts Payable', account_type='LIABILITY', is_system=True),
        'revenue': AccountFactory.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_system=True),
        'cogs': AccountFactory.create(code='5000', name='Cost of Goods Sold', account_type='EXPENSE', is_system=True),
    }


@pytest.fixture
def default_warehouse():
    """Create default warehouse."""
    return WarehouseFactory.create(name='Main Warehouse', code='MAIN', is_default=True)


@pytest.fixture
def tablet_unit():
    """Create tablet unit."""
    return UnitFactory.create(name='Tablet', symbol='TAB')


@pytest.fixture
def tablets_category():
    """Create tablets category."""
    return CategoryFactory.create(name='Tablets')


@pytest.fixture
def sample_product(tablets_category, tablet_unit):
    """Create a sample product."""
    return ProductFactory.create(
        name='Amoxicillin 500mg',
        category=tablets_category,
        unit=tablet_unit
    )


@pytest.fixture
def stocked_batch(sample_product):
    """Create a batch with stock."""
    return BatchFactory.create(
        product=sample_product,
        batch_number='BATCH-FIXTURE-001',
        quantity=Decimal('1000.00'),
        remaining_quantity=Decimal('1000.00')
    )


@pytest.fixture
def sample_customer():
    """Create a sample customer."""
    return CustomerFactory.create(name='Test Customer', code='CUST-FIXTURE')


@pytest.fixture
def sample_supplier():
    """Create a sample supplier."""
    return SupplierFactory.create(name='Test Supplier', code='SUP-FIXTURE')
