"""
Sales and Purchases View Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User

from accounting.models import Account
from sales.models import Customer
from purchases.models import Supplier


class SalesViewTests(TestCase):
    """Test sales API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('salestest', 'sales@test.com', 'testpass')
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(
            name='Test Customer', phone='123456', address='Test Address'
        )
        
    def test_customer_list_view_exists(self):
        """Test customer list endpoint exists."""
        response = self.client.get('/api/sales/customers/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_invoice_list_view_exists(self):
        """Test invoice list endpoint exists."""
        response = self.client.get('/api/sales/invoices/')
        self.assertIn(response.status_code, [200, 301, 302, 403])


class PurchaseViewTests(TestCase):
    """Test purchase API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('purchasetest', 'purchase@test.com', 'testpass')
        self.client.force_login(self.user)
        self.supplier = Supplier.objects.create(
            name='Test Supplier', phone='123456', address='Test Address'
        )
        
    def test_supplier_list_view_exists(self):
        """Test supplier list endpoint exists."""
        response = self.client.get('/api/purchases/suppliers/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_invoice_list_view_exists(self):
        """Test invoice list endpoint exists."""
        response = self.client.get('/api/purchases/invoices/')
        self.assertIn(response.status_code, [200, 301, 302, 403])


class InventoryViewTests(TestCase):
    """Test inventory API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('inventorytest', 'inv@test.com', 'testpass')
        self.client.force_login(self.user)
        
    def test_product_list_view_exists(self):
        """Test product list endpoint exists."""
        response = self.client.get('/api/inventory/products/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_warehouse_list_view_exists(self):
        """Test warehouse list endpoint exists."""
        response = self.client.get('/api/inventory/warehouses/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_batch_list_view_exists(self):
        """Test batch list endpoint exists."""
        response = self.client.get('/api/inventory/batches/')
        self.assertIn(response.status_code, [200, 301, 302, 403])