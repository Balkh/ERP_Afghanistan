"""
Sales and Purchases model behavior tests - simplified.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase

from sales.models import Customer
from purchases.models import Supplier


class CustomerModelTest(TestCase):
    """Test Customer model."""

    def test_create_customer(self):
        """Test creating a customer."""
        customer = Customer.objects.create(
            name='John Doe',
            phone='1234567890',
            address='123 Main St'
        )
        self.assertEqual(customer.name, 'John Doe')

    def test_customer_str(self):
        """Test customer string representation."""
        customer = Customer.objects.create(name='Jane Smith', phone='123')
        self.assertIn('Jane', str(customer))

    def test_customer_is_active_default(self):
        """Test customer is_active defaults to True."""
        customer = Customer.objects.create(name='Test', phone='123')
        self.assertTrue(customer.is_active)


class SupplierModelTest(TestCase):
    """Test Supplier model."""

    def test_create_supplier(self):
        """Test creating a supplier."""
        supplier = Supplier.objects.create(
            name='ABC Pharma',
            phone='9876543210',
            address='456 Pharma Ave'
        )
        self.assertEqual(supplier.name, 'ABC Pharma')

    def test_supplier_str(self):
        """Test supplier string representation."""
        supplier = Supplier.objects.create(name='XYZ Medical', phone='123')
        self.assertIn('XYZ', str(supplier))

    def test_supplier_is_active_default(self):
        """Test supplier is_active defaults to True."""
        supplier = Supplier.objects.create(name='Test', phone='123')
        self.assertTrue(supplier.is_active)