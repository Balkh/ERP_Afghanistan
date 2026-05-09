"""
Tests for Inventory integration views (stock allocation, sale/purchase processing).
"""
from datetime import timedelta
from decimal import Decimal
import uuid
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from tests.factories import (
    ProductFactory, CategoryFactory, UnitFactory,
    BatchFactory, WarehouseFactory,
)


class InventoryIntegrationViewsTests(APITestCase):
    """Tests for inventory integration view endpoints."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)
        cls.category = CategoryFactory.create(name='Test Category')
        cls.unit = UnitFactory.create(name='Tablet', symbol='TAB')
        cls.warehouse = WarehouseFactory.create(name='Test WH', code='TWH')

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_allocate_stock_success(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        url = '/api/inventory/stock/allocate/'
        data = {
            'product_id': str(product.id),
            'quantity': '50.00',
            'warehouse_id': str(self.warehouse.id),
            'selection_mode': 'FEFO',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_allocate_stock_insufficient(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('10.00'), remaining_quantity=Decimal('10.00'), location=str(self.warehouse.id))
        url = '/api/inventory/stock/allocate/'
        data = {
            'product_id': str(product.id),
            'quantity': '999.00',
            'warehouse_id': str(self.warehouse.id),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['success'])

    def test_allocate_stock_product_not_found(self):
        url = '/api/inventory/stock/allocate/'
        data = {
            'product_id': str(uuid.uuid4()),
            'quantity': '10.00',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_allocate_stock_warehouse_not_found(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        url = '/api/inventory/stock/allocate/'
        data = {
            'product_id': str(product.id),
            'quantity': '10.00',
            'warehouse_id': str(uuid.uuid4()),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_allocate_stock_invalid_data(self):
        url = '/api/inventory/stock/allocate/'
        data = {'product_id': 'not-a-uuid'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_stock_availability_single(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        url = f'/api/inventory/stock/check-availability/?product_id={product.id}&quantity=50'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_check_stock_availability_multiple(self):
        p1 = ProductFactory.create(category=self.category, unit=self.unit)
        p2 = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=p1, quantity=Decimal('50.00'), remaining_quantity=Decimal('50.00'), location=str(self.warehouse.id))
        BatchFactory.create(product=p2, quantity=Decimal('30.00'), remaining_quantity=Decimal('30.00'), location=str(self.warehouse.id))
        url = f'/api/inventory/stock/check-availability/?product_ids={p1.id},{p2.id}&quantity=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_check_stock_availability_no_params(self):
        url = '/api/inventory/stock/check-availability/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_stock_availability_warehouse_not_found(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        url = f'/api/inventory/stock/check-availability/?product_id={product.id}&warehouse_id={uuid.uuid4()}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_stock_levels(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        url = f'/api/inventory/stock/levels/?product_id={product.id}&warehouse_id={self.warehouse.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_stock_levels_product_not_found(self):
        url = f'/api/inventory/stock/levels/?product_id={uuid.uuid4()}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_stock_levels_warehouse_not_found(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        url = f'/api/inventory/stock/levels/?product_id={product.id}&warehouse_id={uuid.uuid4()}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_available_batches(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        url = f'/api/inventory/stock/products/{product.id}/available-batches/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_available_batches_warehouse_filter(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=180)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), expiry_date=future, location=str(self.warehouse.id))
        url = f'/api/inventory/stock/products/{product.id}/available-batches/?warehouse_id={self.warehouse.id}&selection_mode=FEFO'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_available_batches_product_not_found(self):
        url = f'/api/inventory/stock/products/{uuid.uuid4()}/available-batches/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_available_batches_warehouse_not_found(self):
        product = ProductFactory.create(category=self.category, unit=self.unit)
        url = f'/api/inventory/stock/products/{product.id}/available-batches/?warehouse_id={uuid.uuid4()}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_purchase_stock(self):
        from purchases.models import Supplier
        product = ProductFactory.create(category=self.category, unit=self.unit)
        future = timezone.now().date() + timedelta(days=365)
        supplier = Supplier.objects.create(name='Test Supplier', code='SUPP-001')
        from purchases.models import PurchaseInvoice
        invoice = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number='PI-VIEWS-001',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='DRAFT',
        )
        url = '/api/inventory/stock/process-purchase/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{
                'product_id': str(product.id),
                'quantity': '50.00',
                'batch_number': 'VIEW-BATCH-001',
                'expiry_date': future.isoformat(),
                'manufacturing_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
                'unit_price': '10.00',
            }],
            'warehouse_id': str(self.warehouse.id),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_process_purchase_stock_invalid_data(self):
        url = '/api/inventory/stock/process-purchase/'
        data = {'items': []}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_purchase_stock_product_not_found(self):
        from purchases.models import Supplier, PurchaseInvoice
        supplier = Supplier.objects.create(name='Test Supplier 2', code='SUPP-002')
        invoice = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number='PI-VIEWS-002',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='DRAFT',
        )
        future = timezone.now().date() + timedelta(days=365)
        url = '/api/inventory/stock/process-purchase/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{
                'product_id': str(uuid.uuid4()),
                'quantity': '50.00',
                'batch_number': 'VIEW-BATCH-002',
                'expiry_date': future.isoformat(),
                'manufacturing_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
                'unit_price': '10.00',
            }],
            'warehouse_id': str(self.warehouse.id),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_purchase_stock_warehouse_not_found(self):
        from purchases.models import Supplier, PurchaseInvoice
        product = ProductFactory.create(category=self.category, unit=self.unit)
        supplier = Supplier.objects.create(name='Test Supplier 3', code='SUPP-003')
        future = timezone.now().date() + timedelta(days=365)
        invoice = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number='PI-VIEWS-003',
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='DRAFT',
        )
        url = '/api/inventory/stock/process-purchase/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{
                'product_id': str(product.id),
                'quantity': '50.00',
                'batch_number': 'VIEW-BATCH-003',
                'expiry_date': future.isoformat(),
                'manufacturing_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
                'unit_price': '10.00',
            }],
            'warehouse_id': str(uuid.uuid4()),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_sale_stock(self):
        from sales.models import Customer
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        customer = Customer.objects.create(name='Test Customer')
        from sales.models import SalesInvoice
        invoice = SalesInvoice.objects.create(
            invoice_number='SI-VIEWS-001',
            customer=customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='CONFIRMED',
        )
        url = '/api/inventory/stock/process-sale/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{'product_id': str(product.id), 'quantity': '10.00'}],
            'warehouse_id': str(self.warehouse.id),
            'selection_mode': 'FEFO',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_process_sale_stock_invalid_data(self):
        url = '/api/inventory/stock/process-sale/'
        data = {'items': 'not-a-list'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_process_sale_stock_product_not_found(self):
        from sales.models import Customer, SalesInvoice
        customer = Customer.objects.create(name='Test Customer 2')
        invoice = SalesInvoice.objects.create(
            invoice_number='SI-VIEWS-002',
            customer=customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='CONFIRMED',
        )
        url = '/api/inventory/stock/process-sale/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{'product_id': str(uuid.uuid4()), 'quantity': '10.00'}],
            'warehouse_id': str(self.warehouse.id),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_sale_stock_warehouse_not_found(self):
        from sales.models import Customer, SalesInvoice
        product = ProductFactory.create(category=self.category, unit=self.unit)
        BatchFactory.create(product=product, quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'), location=str(self.warehouse.id))
        customer = Customer.objects.create(name='Test Customer 3')
        invoice = SalesInvoice.objects.create(
            invoice_number='SI-VIEWS-003',
            customer=customer,
            order_date=timezone.now().date(),
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='CONFIRMED',
        )
        url = '/api/inventory/stock/process-sale/'
        data = {
            'invoice_id': str(invoice.id),
            'items': [{'product_id': str(product.id), 'quantity': '10.00'}],
            'warehouse_id': str(uuid.uuid4()),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
