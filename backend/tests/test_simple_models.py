"""
Simple Model and Service Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product, Category, Warehouse, Batch, StockMovement, Unit
from sales.models import Customer, SalesInvoice, SalesItem
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem


class SimpleModelTests(TestCase):
    """Simple model tests."""
    
    def test_account_model(self):
        """Test account model."""
        acc = Account.objects.create(code='9000', name='Test', account_type='ASSET', is_active=True)
        self.assertEqual(acc.name, 'Test')
        
    def test_category_model(self):
        """Test category model."""
        cat = Category.objects.create(name='Test Category')
        self.assertEqual(cat.name, 'Test Category')
        
    def test_unit_model(self):
        """Test unit model."""
        unit = Unit.objects.create(symbol='BOX', name='Box')
        self.assertEqual(unit.symbol, 'BOX')
        
    def test_warehouse_model(self):
        """Test warehouse model."""
        wh = Warehouse.objects.create(name='Test WH', code='TWH', address='Loc')
        self.assertEqual(wh.name, 'Test WH')
        
    def test_product_model(self):
        """Test product model."""
        unit = Unit.objects.create(symbol='PCS', name='Pieces')
        cat = Category.objects.create(name='Cat')
        prod = Product.objects.create(name='Test Prod', sku='TST', category=cat, unit=unit)
        self.assertEqual(prod.name, 'Test Prod')
        
    def test_batch_model(self):
        """Test batch model."""
        unit = Unit.objects.create(symbol='PCS', name='Pieces')
        cat = Category.objects.create(name='Cat2')
        prod = Product.objects.create(name='Prod2', sku='P2', category=cat, unit=unit)
        batch = Batch.objects.create(product=prod, batch_number='B001', quantity=Decimal('100'), remaining_quantity=Decimal('100'))
        self.assertEqual(batch.batch_number, 'B001')
        
    def test_customer_model(self):
        """Test customer model."""
        cust = Customer.objects.create(name='Cust', phone='123', address='Addr')
        self.assertEqual(cust.name, 'Cust')
        
    def test_supplier_model(self):
        """Test supplier model."""
        sup = Supplier.objects.create(name='Sup', phone='456', address='Addr')
        self.assertEqual(sup.name, 'Sup')
        
    def test_sales_invoice_model(self):
        """Test sales invoice model."""
        cust = Customer.objects.create(name='C2', phone='1', address='A')
        inv = SalesInvoice.objects.create(customer=cust, invoice_date=date.today(), order_date=date.today(), due_date=date.today())
        self.assertIsNotNone(inv.id)
        
    def test_purchase_invoice_model(self):
        """Test purchase invoice model."""
        sup = Supplier.objects.create(name='S2', phone='2', address='A')
        inv = PurchaseInvoice.objects.create(supplier=sup, invoice_date=date.today(), order_date=date.today(), due_date=date.today())
        self.assertIsNotNone(inv.id)


class ServiceExistenceTests(TestCase):
    """Test service existence."""
    
    def test_financial_reports_service(self):
        """Test financial reports service."""
        from accounting.services.financial_reports import FinancialReportEngine
        self.assertTrue(hasattr(FinancialReportEngine, 'get_trial_balance'))
        self.assertTrue(hasattr(FinancialReportEngine, 'get_profit_and_loss'))
        self.assertTrue(hasattr(FinancialReportEngine, 'get_balance_sheet'))
        self.assertTrue(hasattr(FinancialReportEngine, 'get_cash_flow_statement'))
        
    def test_journal_engine_service(self):
        """Test journal engine service."""
        from accounting.services.journal_engine import JournalEngine
        self.assertTrue(hasattr(JournalEngine, 'generate_entry_number'))
        self.assertTrue(hasattr(JournalEngine, 'validate_lines'))
        
    def test_account_hierarchy_service(self):
        """Test account hierarchy service."""
        from accounting.services.account_hierarchy import AccountHierarchyService
        self.assertTrue(hasattr(AccountHierarchyService, 'get_account_tree'))
        
    def test_invoice_calculator_service(self):
        """Test invoice calculator service."""
        from accounting.services.invoice_calculator import InvoiceCalculator
        self.assertTrue(hasattr(InvoiceCalculator, 'calculate'))
        
    def test_tax_calculator_service(self):
        """Test tax calculator service."""
        from accounting.services.tax_calculator import TaxCalculator
        self.assertTrue(hasattr(TaxCalculator, 'calculate_percentage_tax'))
        
    def test_discount_calculator_service(self):
        """Test discount calculator service."""
        from accounting.services.discount_calculator import DiscountCalculator
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_percentage_discount'))
        
    def test_currency_converter_service(self):
        """Test currency converter service."""
        from accounting.services.currency_converter import CurrencyConverter
        self.assertTrue(hasattr(CurrencyConverter, 'get_base_currency'))
        
    def test_report_exporter_service(self):
        """Test report exporter service."""
        from accounting.services.report_exporter import ReportExporter
        self.assertTrue(hasattr(ReportExporter, '_export_trial_balance_csv'))


class ViewEndpointTests(TestCase):
    """Test view endpoints."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('viewtest', 'vt@test.com', 'pass')
        self.client.force_login(self.user)
        
    def test_account_list_endpoint(self):
        """Test account list endpoint."""
        response = self.client.get('/api/accounting/accounts/')
        self.assertIn(response.status_code, [200, 403])
        
    def test_customer_list_endpoint(self):
        """Test customer list endpoint."""
        response = self.client.get('/api/sales/customers/')
        self.assertIn(response.status_code, [200, 403])
        
    def test_supplier_list_endpoint(self):
        """Test supplier list endpoint."""
        response = self.client.get('/api/purchases/suppliers/')
        self.assertIn(response.status_code, [200, 403])
        
    def test_product_list_endpoint(self):
        """Test product list endpoint."""
        response = self.client.get('/api/inventory/products/')
        self.assertIn(response.status_code, [200, 403])
        
    def test_warehouse_list_endpoint(self):
        """Test warehouse list endpoint."""
        response = self.client.get('/api/inventory/warehouses/')
        self.assertIn(response.status_code, [200, 403])


# Import Client and User for ViewEndpointTests
from django.test import Client
from django.contrib.auth.models import User