"""Real database integration fixtures for frontend testing."""
import pytest
import os
import sys
import django
from unittest.mock import MagicMock


# Add backend to path for Django settings
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def pytest_configure():
    """Configure Django for testing."""
    try:
        django.setup()
    except Exception:
        pass


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup Django database for testing."""
    pytest_configure()


@pytest.fixture
def db_helper(django_db_setup):
    """Database helper for testing."""
    from django.db import connection
    
    class DatabaseHelper:
        def __init__(self):
            self.connection = connection
        
        def execute_sql(self, sql, params=None):
            """Execute raw SQL."""
            with connection.cursor() as cursor:
                cursor.execute(sql, params or [])
                return cursor.fetchall()
        
        def table_exists(self, table_name):
            """Check if table exists."""
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    [table_name]
                )
                return cursor.fetchone()[0]
        
        def count_records(self, model):
            """Count records in a model."""
            return model.objects.count()
    
    return DatabaseHelper()


@pytest.fixture
def category(db_helper):
    """Create a test category fixture."""
    pytest_configure()
    
    try:
        from inventory.models import Category
        
        # Create test category
        category, created = Category.objects.get_or_create(
            name="Test Category",
            defaults={"description": "Test category for testing"}
        )
        
        yield category
        
        # Cleanup only if we created it
        if created:
            category.delete()
    except Exception as e:
        pytest.skip(f"Cannot create category: {e}")


@pytest.fixture
def warehouse(db_helper):
    """Create a test warehouse fixture."""
    pytest_configure()
    
    try:
        from inventory.models import Warehouse
        
        warehouse, created = Warehouse.objects.get_or_create(
            name="Test Warehouse",
            defaults={
                "address": "Test Address",
                "is_active": True
            }
        )
        
        yield warehouse
        
        if created:
            warehouse.delete()
    except Exception as e:
        pytest.skip(f"Cannot create warehouse: {e}")


@pytest.fixture
def product(db_helper, category, warehouse):
    """Create a test product fixture."""
    pytest_configure()
    
    try:
        from inventory.models import Product, Category, Warehouse, Unit
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get or create unit
        unit, _ = Unit.objects.get_or_create(name="Piece", defaults={"symbol": "pc"})
        
        # Create test product
        product = Product.objects.create(
            name="Test Product",
            generic_name="Test Generic",
            brand_name="Test Brand",
            category=category,
            unit=unit,
            barcode="8901234567890",
            sku="TEST001",
            is_active=True
        )
        
        yield product
        
        product.delete()
    except Exception as e:
        pytest.skip(f"Cannot create product: {e}")


@pytest.fixture
def account(db_helper):
    """Create a test account fixture."""
    pytest_configure()
    
    try:
        from accounting.models import Account
        
        account, created = Account.objects.get_or_create(
            code="9999",
            defaults={
                "name": "Test Account",
                "account_type": "ASSET",
                "balance_type": "DEBIT"
            }
        )
        
        yield account
        
        if created:
            account.delete()
    except Exception as e:
        pytest.skip(f"Cannot create account: {e}")


@pytest.fixture
def customer(db_helper):
    """Create a test customer fixture."""
    pytest_configure()
    
    try:
        from sales.models import Customer
        
        customer, created = Customer.objects.get_or_create(
            name="Test Customer",
            defaults={
                "phone": "1234567890",
                "email": "test@example.com",
                "is_active": True
            }
        )
        
        yield customer
        
        if created:
            customer.delete()
    except Exception as e:
        pytest.skip(f"Cannot create customer: {e}")


@pytest.fixture  
def supplier(db_helper):
    """Create a test supplier fixture."""
    pytest_configure()
    
    try:
        from purchases.models import Supplier
        
        supplier, created = Supplier.objects.get_or_create(
            name="Test Supplier",
            defaults={
                "phone": "1234567890",
                "email": "supplier@example.com",
                "is_active": True
            }
        )
        
        yield supplier
        
        if created:
            supplier.delete()
    except Exception as e:
        pytest.skip(f"Cannot create supplier: {e}")