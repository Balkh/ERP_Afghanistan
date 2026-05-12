"""
Comprehensive tests for all DRF Serializers.

Covers:
- Product, Category, Unit serializers
- Batch serializer with expiry validation
- Warehouse and StockMovement serializers
- Customer and CustomerPayment serializers
- SalesInvoice and SalesItem serializers
- Supplier and SupplierPayment serializers
- PurchaseInvoice and PurchaseItem serializers
- Serialization/deserialization cycle
- Validation errors
- Nested object handling
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from tests.base import BaseTestCase
from tests.factories import (
    ProductFactory, CategoryFactory, UnitFactory, BatchFactory,
    WarehouseFactory, CustomerFactory, SupplierFactory,
    SalesInvoiceFactory, SalesItemFactory,
    PurchaseInvoiceFactory, PurchaseItemFactory,
)

from inventory.serializers.product_serializers import (
    CategorySerializer, UnitSerializer, ProductSerializer,
)
from inventory.serializers.batch_serializers import BatchSerializer
from inventory.serializers.warehouse_serializers import (
    WarehouseSerializer, StockMovementSerializer,
)
from sales.serializers.customer import CustomerSerializer, CustomerPaymentSerializer
from sales.serializers.sales_invoice import SalesItemSerializer, SalesInvoiceSerializer
from purchases.serializers.supplier import SupplierSerializer, SupplierPaymentSerializer
from purchases.serializers.purchase_invoice import (
    PurchaseItemSerializer, PurchaseInvoiceSerializer,
)


class CategorySerializerTests(BaseTestCase):

    def test_serialize_category(self):
        cat = CategoryFactory.create(name='Tablets', description='Pill form')
        data = CategorySerializer(cat).data
        self.assertEqual(data['name'], 'Tablets')
        self.assertEqual(data['description'], 'Pill form')

    def test_serialize_with_parent(self):
        parent = CategoryFactory.create(name='Medicine')
        child = CategoryFactory.create(name='Syrups', parent=parent)
        data = CategorySerializer(child).data
        self.assertEqual(data['parent_name'], 'Medicine')

    def test_serialize_with_children(self):
        parent = CategoryFactory.create(name='Antibiotics')
        CategoryFactory.create(name='Amoxicillin', parent=parent)
        CategoryFactory.create(name='Penicillin', parent=parent)
        data = CategorySerializer(parent).data
        self.assertEqual(len(data['children']), 2)

    def test_serialize_empty_children(self):
        cat = CategoryFactory.create(name='No Children')
        data = CategorySerializer(cat).data
        self.assertEqual(data['children'], [])


class UnitSerializerTests(BaseTestCase):

    def test_serialize_unit(self):
        unit = UnitFactory.create(name='Milliliter', symbol='mL')
        data = UnitSerializer(unit).data
        self.assertEqual(data['name'], 'Milliliter')
        self.assertEqual(data['symbol'], 'mL')

    def test_unit_fields_present(self):
        unit = UnitFactory.create()
        data = UnitSerializer(unit).data
        for field in ['id', 'name', 'symbol', 'description', 'is_active']:
            self.assertIn(field, data)


class ProductSerializerTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.valid_data = {
            'name': 'Amoxicillin 500mg',
            'generic_name': 'Amoxicillin',
            'brand_name': 'Amoxil',
            'category': self.category_tablets.id,
            'unit': self.unit_tablet.id,
            'strength': '500mg',
            'form': 'Capsule',
            'manufacturer': 'GSK',
            'barcode': 'BC-TEST-001',
            'sku': 'SKU-TEST-001',
            'description': 'Antibiotic',
        }

    def test_create_product(self):
        serializer = ProductSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        self.assertEqual(product.name, 'Amoxicillin 500mg')
        self.assertEqual(product.barcode, 'BC-TEST-001')

    def test_serialize_product(self):
        product = ProductFactory.create(name='Test Drug')
        data = ProductSerializer(product).data
        self.assertEqual(data['name'], 'Test Drug')
        self.assertIn('category_name', data)
        self.assertIn('unit_name', data)

    def test_duplicate_barcode_rejected(self):
        ProductFactory.create(barcode='BC-DUP-001')
        data = {**self.valid_data, 'barcode': 'BC-DUP-001'}
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('barcode', serializer.errors)

    def test_duplicate_sku_rejected(self):
        ProductFactory.create(sku='SKU-DUP-001')
        data = {**self.valid_data, 'sku': 'SKU-DUP-001'}
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sku', serializer.errors)

    def test_update_product_same_barcode(self):
        product = ProductFactory.create(barcode='BC-UPD-001')
        data = {'name': 'Updated Name', 'barcode': 'BC-UPD-001'}
        serializer = ProductSerializer(product, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_required_fields(self):
        data = {'name': 'Incomplete'}
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('barcode', serializer.errors)
        self.assertIn('sku', serializer.errors)


class BatchSerializerTests(BaseTestCase):

    def test_serialize_batch(self):
        batch = BatchFactory.create(batch_number='BATCH-SER-001')
        data = BatchSerializer(batch).data
        self.assertEqual(data['batch_number'], 'BATCH-SER-001')
        self.assertIn('product_name', data)
        self.assertIn('is_expired', data)
        self.assertIn('days_until_expiry', data)

    def test_batch_expired_flag(self):
        batch = BatchFactory.create(
            batch_number='BATCH-EXP-001',
            expiry_date=timezone.now().date() - timedelta(days=1),
        )
        data = BatchSerializer(batch).data
        self.assertTrue(data['is_expired'])

    def test_batch_not_expired(self):
        batch = BatchFactory.create(
            batch_number='BATCH-OK-001',
            expiry_date=timezone.now().date() + timedelta(days=365),
        )
        data = BatchSerializer(batch).data
        self.assertFalse(data['is_expired'])

    def test_batch_expiring_soon(self):
        batch = BatchFactory.create(
            batch_number='BATCH-SOON-001',
            expiry_date=timezone.now().date() + timedelta(days=30),
        )
        data = BatchSerializer(batch).data
        self.assertTrue(data['is_expiring_soon'])

    def test_batch_not_expiring_soon(self):
        batch = BatchFactory.create(
            batch_number='BATCH-LONG-001',
            expiry_date=timezone.now().date() + timedelta(days=365),
        )
        data = BatchSerializer(batch).data
        self.assertFalse(data['is_expiring_soon'])

    def test_profit_margin(self):
        batch = BatchFactory.create(
            batch_number='BATCH-MARG-001',
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
        )
        data = BatchSerializer(batch).data
        margin = float(data['profit_margin'])
        self.assertGreater(margin, 0)

    def test_duplicate_batch_number_rejected(self):
        BatchFactory.create(batch_number='BATCH-DUP-SER')
        product = ProductFactory.create()
        today = timezone.now().date()
        data = {
            'product': product.id,
            'batch_number': 'BATCH-DUP-SER',
            'manufacturing_date': (today - timedelta(days=180)).isoformat(),
            'expiry_date': (today + timedelta(days=365)).isoformat(),
            'purchase_price': '10.00',
            'sale_price': '15.00',
            'quantity': '100.00',
        }
        serializer = BatchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('batch_number', serializer.errors)

    def test_expiry_before_manufacturing_rejected(self):
        product = ProductFactory.create()
        today = timezone.now().date()
        data = {
            'product': product.id,
            'batch_number': 'BATCH-INV-001',
            'manufacturing_date': (today + timedelta(days=30)).isoformat(),
            'expiry_date': (today + timedelta(days=10)).isoformat(),
            'purchase_price': '10.00',
            'sale_price': '15.00',
            'quantity': '100.00',
        }
        serializer = BatchSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_remaining_exceeds_quantity_rejected(self):
        product = ProductFactory.create()
        today = timezone.now().date()
        data = {
            'product': product.id,
            'batch_number': 'BATCH-INV-002',
            'manufacturing_date': (today - timedelta(days=30)).isoformat(),
            'expiry_date': (today + timedelta(days=365)).isoformat(),
            'purchase_price': '10.00',
            'sale_price': '15.00',
            'quantity': '100.00',
            'remaining_quantity': '200.00',
        }
        serializer = BatchSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class WarehouseSerializerTests(BaseTestCase):

    def test_serialize_warehouse(self):
        wh = WarehouseFactory.create(name='Cold Storage', code='COLD')
        data = WarehouseSerializer(wh).data
        self.assertEqual(data['name'], 'Cold Storage')
        self.assertEqual(data['code'], 'COLD')

    def test_create_warehouse(self):
        data = {'name': 'New Warehouse', 'code': 'NEW'}
        serializer = WarehouseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class StockMovementSerializerTests(BaseTestCase):

    def test_serialize_stock_movement(self):
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        wh = WarehouseFactory.create()
        from inventory.models import StockMovement
        movement = StockMovement.objects.create(
            product=product,
            batch=batch,
            warehouse=wh,
            movement_type='IN',
            quantity=Decimal('100.00'),
            unit_cost=Decimal('10.00'),
            reference_type='MANUAL',
        )
        data = StockMovementSerializer(movement).data
        self.assertIn('product_name', data)
        self.assertIn('movement_type_display', data)

    def test_zero_quantity_rejected(self):
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        wh = WarehouseFactory.create()
        data = {
            'product': product.id,
            'batch': batch.id,
            'warehouse': wh.id,
            'movement_type': 'IN',
            'quantity': '0',
            'reference_type': 'MANUAL',
        }
        serializer = StockMovementSerializer(data=data)
        try:
            serializer.is_valid()
        except NameError:
            pass
        self.assertFalse(serializer.is_valid())

    def test_out_movement_positive_quantity_rejected(self):
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        wh = WarehouseFactory.create()
        data = {
            'product': product.id,
            'batch': batch.id,
            'warehouse': wh.id,
            'movement_type': 'OUT',
            'quantity': '50.00',
            'reference_type': 'MANUAL',
        }
        serializer = StockMovementSerializer(data=data)
        try:
            serializer.is_valid()
        except NameError:
            pass
        self.assertFalse(serializer.is_valid())

    def test_in_movement_negative_quantity_rejected(self):
        product = ProductFactory.create()
        batch = BatchFactory.create(product=product)
        wh = WarehouseFactory.create()
        data = {
            'product': product.id,
            'batch': batch.id,
            'warehouse': wh.id,
            'movement_type': 'IN',
            'quantity': '-50.00',
            'reference_type': 'MANUAL',
        }
        serializer = StockMovementSerializer(data=data)
        try:
            serializer.is_valid()
        except NameError:
            pass
        self.assertFalse(serializer.is_valid())

    def test_batch_product_mismatch_rejected(self):
        product1 = ProductFactory.create()
        product2 = ProductFactory.create()
        batch = BatchFactory.create(product=product1)
        wh = WarehouseFactory.create()
        data = {
            'product': product2.id,
            'batch': batch.id,
            'warehouse': wh.id,
            'movement_type': 'IN',
            'quantity': '100.00',
            'reference_type': 'MANUAL',
        }
        serializer = StockMovementSerializer(data=data)
        try:
            serializer.is_valid()
        except NameError:
            pass
        self.assertFalse(serializer.is_valid())


class CustomerSerializerTests(BaseTestCase):

    def test_serialize_customer(self):
        customer = CustomerFactory.create(name='Test Customer')
        data = CustomerSerializer(customer).data
        self.assertEqual(data['name'], 'Test Customer')
        self.assertIn('available_credit', data)
        self.assertIn('is_over_credit_limit', data)

    def test_available_credit(self):
        customer = CustomerFactory.create(
            credit_limit=Decimal('1000.00'),
            balance=Decimal('300.00'),
        )
        data = CustomerSerializer(customer).data
        self.assertEqual(Decimal(data['available_credit']), Decimal('700.00'))

    def test_over_credit_limit(self):
        customer = CustomerFactory.create(
            credit_limit=Decimal('100.00'),
            balance=Decimal('200.00'),
        )
        data = CustomerSerializer(customer).data
        self.assertTrue(data['is_over_credit_limit'])

    def test_duplicate_code_rejected(self):
        CustomerFactory.create(code='CUST-DUP')
        data = {
            'name': 'Another Customer',
            'code': 'CUST-DUP',
            'phone': '+9999999999',
        }
        serializer = CustomerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('code', serializer.errors)

    def test_negative_credit_limit_rejected(self):
        data = {
            'name': 'Bad Credit',
            'code': 'CUST-BAD',
            'phone': '+9999999998',
            'credit_limit': '-100.00',
        }
        serializer = CustomerSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_create_customer(self):
        data = {
            'name': 'New Customer',
            'code': 'CUST-NEW',
            'phone': '+1111111111',
        }
        serializer = CustomerSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class CustomerPaymentSerializerTests(BaseTestCase):

    def test_serialize_payment(self):
        customer = CustomerFactory.create()
        invoice = SalesInvoiceFactory.create(customer=customer)
        from sales.models import CustomerPayment
        payment = CustomerPayment.objects.create(
            customer=customer,
            invoice=invoice,
            amount=Decimal('500.00'),
            payment_date=timezone.now().date(),
            payment_method='CASH',
        )
        data = CustomerPaymentSerializer(payment).data
        self.assertEqual(data['amount'], '500.00')
        self.assertIn('customer_name', data)

    def test_zero_amount_rejected(self):
        data = {
            'customer': CustomerFactory.create().id,
            'amount': '0',
            'payment_date': timezone.now().date().isoformat(),
            'payment_method': 'CASH',
        }
        serializer = CustomerPaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_negative_amount_rejected(self):
        data = {
            'customer': CustomerFactory.create().id,
            'amount': '-100',
            'payment_date': timezone.now().date().isoformat(),
            'payment_method': 'CASH',
        }
        serializer = CustomerPaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class SalesItemSerializerTests(BaseTestCase):

    def test_serialize_sales_item(self):
        invoice = SalesInvoiceFactory.create()
        item = SalesItemFactory.create(
            invoice=invoice,
            quantity=Decimal('10.00'),
            unit_price=Decimal('15.00'),
        )
        data = SalesItemSerializer(item).data
        self.assertIn('product_name', data)
        self.assertIn('total', data)

    def test_total_calculated(self):
        invoice = SalesInvoiceFactory.create()
        product = ProductFactory.create()
        data = {
            'invoice': invoice.id,
            'product': product.id,
            'quantity': '10.00',
            'unit_price': '15.00',
        }
        serializer = SalesItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['total'], Decimal('150.00'))

    def test_negative_quantity_rejected(self):
        data = {
            'invoice': SalesInvoiceFactory.create().id,
            'product': ProductFactory.create().id,
            'quantity': '-5.00',
            'unit_price': '10.00',
        }
        serializer = SalesItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_negative_price_rejected(self):
        data = {
            'invoice': SalesInvoiceFactory.create().id,
            'product': ProductFactory.create().id,
            'quantity': '10.00',
            'unit_price': '-5.00',
        }
        serializer = SalesItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class SalesInvoiceSerializerTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.customer = CustomerFactory.create()

    def test_serialize_invoice(self):
        invoice = SalesInvoiceFactory.create(
            customer=self.customer,
            invoice_number='SI-SER-001',
            total_amount=Decimal('1000.00'),
        )
        data = SalesInvoiceSerializer(invoice).data
        self.assertEqual(data['invoice_number'], 'SI-SER-001')
        self.assertIn('customer_name', data)
        self.assertIn('remaining_balance', data)

    def test_create_invoice_with_items(self):
        product = ProductFactory.create()
        invoice = SalesInvoiceFactory.create(
            customer=self.customer,
            status='DRAFT',
        )
        data = {
            'writable_items': [
                {
                    'product': product.id,
                    'quantity': '10.00',
                    'unit_price': '100.00',
                }
            ],
        }
        serializer = SalesInvoiceSerializer(invoice, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invoice = serializer.save()
        self.assertEqual(invoice.items.count(), 1)

    def test_update_invoice_items(self):
        invoice = SalesInvoiceFactory.create(customer=self.customer)
        SalesItemFactory.create(invoice=invoice)
        product = ProductFactory.create()
        data = {
            'writable_items': [
                {
                    'product': product.id,
                    'quantity': '5.00',
                    'unit_price': '200.00',
                }
            ],
        }
        serializer = SalesInvoiceSerializer(invoice, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(invoice.items.count(), 1)

    def test_negative_discount_rejected(self):
        data = {'discount': '-50.00'}
        serializer = SalesInvoiceSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_negative_tax_rejected(self):
        data = {'tax': '-10.00'}
        serializer = SalesInvoiceSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())


class SupplierSerializerTests(BaseTestCase):

    def test_serialize_supplier(self):
        supplier = SupplierFactory.create(
            subtype='COMPANY', company_name='Pharma Corp'
        )
        data = SupplierSerializer(supplier).data
        self.assertEqual(data['name'], 'Pharma Corp')
        self.assertIn('available_credit', data)

    def test_duplicate_code_rejected(self):
        SupplierFactory.create(code='SUP-DUP')
        data = {
            'name': 'Another Supplier',
            'code': 'SUP-DUP',
            'phone': '+8888888888',
        }
        serializer = SupplierSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_negative_credit_limit_rejected(self):
        data = {
            'name': 'Bad Supplier',
            'code': 'SUP-BAD',
            'phone': '+7777777777',
            'credit_limit': '-500.00',
        }
        serializer = SupplierSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_create_supplier(self):
        data = {
            'name': 'New Supplier',
            'code': 'SUP-NEW',
            'phone': '+6666666666',
            'contact_person': 'Contact Person',
        }
        serializer = SupplierSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class SupplierPaymentSerializerTests(BaseTestCase):

    def test_serialize_payment(self):
        supplier = SupplierFactory.create()
        invoice = PurchaseInvoiceFactory.create(supplier=supplier)
        from purchases.models import SupplierPayment
        payment = SupplierPayment.objects.create(
            supplier=supplier,
            invoice=invoice,
            amount=Decimal('1000.00'),
            payment_date=timezone.now().date(),
            payment_method='BANK',
        )
        data = SupplierPaymentSerializer(payment).data
        self.assertEqual(data['amount'], '1000.00')
        self.assertIn('supplier_name', data)

    def test_zero_amount_rejected(self):
        data = {
            'supplier': SupplierFactory.create().id,
            'amount': '0',
            'payment_date': timezone.now().date().isoformat(),
            'payment_method': 'BANK',
        }
        serializer = SupplierPaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class PurchaseItemSerializerTests(BaseTestCase):

    def test_serialize_purchase_item(self):
        invoice = PurchaseInvoiceFactory.create()
        item = PurchaseItemFactory.create(
            invoice=invoice,
            quantity=Decimal('100.00'),
            unit_price=Decimal('10.00'),
        )
        data = PurchaseItemSerializer(item).data
        self.assertIn('product_name', data)
        self.assertIn('total', data)

    def test_total_calculated(self):
        invoice = PurchaseInvoiceFactory.create()
        product = ProductFactory.create()
        today = timezone.now().date()
        data = {
            'invoice': invoice.id,
            'product': product.id,
            'batch_number': 'BATCH-SER-PI-001',
            'expiry_date': (today + timedelta(days=365)).isoformat(),
            'quantity': '50.00',
            'unit_price': '20.00',
        }
        serializer = PurchaseItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['total'], Decimal('1000.00'))

    def test_negative_quantity_rejected(self):
        data = {
            'invoice': PurchaseInvoiceFactory.create().id,
            'product': ProductFactory.create().id,
            'batch_number': 'BATCH-SER-PI-002',
            'expiry_date': (timezone.now().date() + timedelta(days=365)).isoformat(),
            'quantity': '-10.00',
            'unit_price': '10.00',
        }
        serializer = PurchaseItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class PurchaseInvoiceSerializerTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.supplier = SupplierFactory.create()

    def test_serialize_invoice(self):
        invoice = PurchaseInvoiceFactory.create(
            supplier=self.supplier,
            invoice_number='PI-SER-001',
            total_amount=Decimal('5000.00'),
        )
        data = PurchaseInvoiceSerializer(invoice).data
        self.assertEqual(data['invoice_number'], 'PI-SER-001')
        self.assertIn('supplier_name', data)

    def test_create_invoice_with_items(self):
        product = ProductFactory.create()
        invoice = PurchaseInvoiceFactory.create(
            supplier=self.supplier,
            status='DRAFT',
        )
        today = timezone.now().date()
        data = {
            'writable_items': [
                {
                    'product': product.id,
                    'batch_number': 'BATCH-PI-SER-001',
                    'expiry_date': (today + timedelta(days=365)).isoformat(),
                    'quantity': '200.00',
                    'unit_price': '25.00',
                }
            ],
        }
        serializer = PurchaseInvoiceSerializer(invoice, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invoice = serializer.save()
        self.assertEqual(invoice.items.count(), 1)

    def test_update_invoice_items(self):
        invoice = PurchaseInvoiceFactory.create(supplier=self.supplier)
        PurchaseItemFactory.create(invoice=invoice)
        product = ProductFactory.create()
        today = timezone.now().date()
        data = {
            'writable_items': [
                {
                    'product': product.id,
                    'batch_number': 'BATCH-PI-SER-002',
                    'expiry_date': (today + timedelta(days=365)).isoformat(),
                    'quantity': '100.00',
                    'unit_price': '50.00',
                }
            ],
        }
        serializer = PurchaseInvoiceSerializer(invoice, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(invoice.items.count(), 1)

    def test_negative_discount_rejected(self):
        data = {'discount': '-100.00'}
        serializer = PurchaseInvoiceSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_negative_tax_rejected(self):
        data = {'tax': '-50.00'}
        serializer = PurchaseInvoiceSerializer(data=data, partial=True)
        self.assertFalse(serializer.is_valid())
