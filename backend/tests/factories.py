"""
Test factories for creating test data.

Provides factory classes for all major models to ensure consistent
test data creation and avoid repetitive object creation in tests.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

# Import models
from core.models import Company
from inventory.models import Category, Unit, Product, Batch, Warehouse, StockMovement
from sales.models import Customer, SalesInvoice, SalesItem, CustomerPayment
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem, SupplierPayment
from accounting.models import Account, JournalEntry, JournalEntryLine, Currency, ExchangeRate
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction, TransactionSettlement, SettlementTransaction


class CompanyFactory:
    """Factory for creating Company test data."""

    @staticmethod
    def create(name=None, **kwargs):
        defaults = {
            'name': name or f'Test Company {uuid.uuid4().hex[:6]}',
            'registration_number': f'REG-{uuid.uuid4().hex[:8]}',
            'address': '123 Test Street, Test City',
            'contact_person': 'Test Contact',
            'phone_number': '+1234567890',
            'email': f'test{uuid.uuid4().hex[:6]}@test.com',
            'is_active': True,
        }
        defaults.update(kwargs)
        return Company.objects.create(**defaults)


class CategoryFactory:
    """Factory for creating Category test data."""

    @staticmethod
    def create(name=None, parent=None, **kwargs):
        defaults = {
            'name': name or f'Category {uuid.uuid4().hex[:6]}',
            'description': 'Test category description',
            'parent': parent,
            'is_active': True,
        }
        defaults.update(kwargs)
        category = Category(**defaults)
        category.full_clean()
        category.save()
        return category


class UnitFactory:
    """Factory for creating Unit test data."""

    @staticmethod
    def create(name=None, symbol=None, **kwargs):
        defaults = {
            'name': name or f'Unit {uuid.uuid4().hex[:6]}',
            'symbol': symbol or 'UNT',
            'description': 'Test unit description',
            'is_active': True,
        }
        defaults.update(kwargs)
        return Unit.objects.create(**defaults)


class ProductFactory:
    """Factory for creating Product test data."""

    @staticmethod
    def create(name=None, category=None, unit=None, **kwargs):
        defaults = {
            'name': name or f'Product {uuid.uuid4().hex[:6]}',
            'generic_name': f'Generic {uuid.uuid4().hex[:6]}',
            'brand_name': f'Brand {uuid.uuid4().hex[:6]}',
            'category': category or CategoryFactory.create(),
            'unit': unit or UnitFactory.create(),
            'strength': '100mg',
            'form': 'Tablet',
            'manufacturer': 'Test Manufacturer',
            'barcode': f'BC{uuid.uuid4().hex[:10]}',
            'sku': f'SKU{uuid.uuid4().hex[:8]}',
            'description': 'Test product description',
            'is_active': True,
            'requires_prescription': False,
            'is_controlled_substance': False,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)


class BatchFactory:
    """Factory for creating Batch test data."""

    @staticmethod
    def build(**kwargs):
        """Build a Batch instance without saving to DB (for validation testing)."""
        today = timezone.now().date()
        defaults = {
            'product': kwargs.get('product'),
            'batch_number': kwargs.get('batch_number', f'BATCH{uuid.uuid4().hex[:8]}'),
            'manufacturing_date': kwargs.get('manufacturing_date', today - timedelta(days=180)),
            'expiry_date': kwargs.get('expiry_date', today + timedelta(days=365)),
            'purchase_price': kwargs.get('purchase_price', Decimal('10.00')),
            'sale_price': kwargs.get('sale_price', Decimal('15.00')),
            'quantity': kwargs.get('quantity', Decimal('1000.00')),
            'remaining_quantity': kwargs.get('remaining_quantity', kwargs.get('quantity', Decimal('1000.00'))),
            'location': kwargs.get('location', 'Shelf A-1'),
            'is_active': kwargs.get('is_active', True),
        }
        # Only set product if not provided, to avoid creating one during build
        if defaults['product'] is None:
            defaults['product'] = ProductFactory.create()
        return Batch(**defaults)

    @staticmethod
    def create(product=None, batch_number=None, quantity=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'product': product or ProductFactory.create(),
            'batch_number': batch_number or f'BATCH{uuid.uuid4().hex[:8]}',
            'manufacturing_date': today - timedelta(days=180),
            'expiry_date': today + timedelta(days=365),
            'purchase_price': Decimal('10.00'),
            'sale_price': Decimal('15.00'),
            'quantity': quantity or Decimal('1000.00'),
            'remaining_quantity': quantity or Decimal('1000.00'),
            'location': 'Shelf A-1',
            'is_active': True,
        }
        defaults.update(kwargs)
        batch = Batch(**defaults)
        batch.full_clean()
        batch.save()
        return batch


class WarehouseFactory:
    """Factory for creating Warehouse test data."""

    @staticmethod
    def create(name=None, code=None, **kwargs):
        defaults = {
            'name': name or f'Warehouse {uuid.uuid4().hex[:6]}',
            'code': code or f'WH{uuid.uuid4().hex[:6]}'.upper(),
            'address': '123 Warehouse Street',
            'contact_person': 'Warehouse Manager',
            'contact_phone': '+1234567890',
            'is_active': True,
            'is_default': kwargs.get('is_default', False),
        }
        defaults.update(kwargs)
        
        # Ensure only one default warehouse
        if defaults['is_default']:
            Warehouse.objects.update(is_default=False)
        
        warehouse = Warehouse(**defaults)
        warehouse.full_clean()
        warehouse.save()
        return warehouse


class StockMovementFactory:
    """Factory for creating StockMovement test data."""

    @staticmethod
    def build(**kwargs):
        """Build a StockMovement instance without saving (for validation testing)."""
        defaults = {
            'product': kwargs.get('product'),
            'batch': kwargs.get('batch'),
            'warehouse': kwargs.get('warehouse'),
            'movement_type': kwargs.get('movement_type', 'IN'),
            'reference_type': kwargs.get('reference_type', 'MANUAL'),
            'reference_id': kwargs.get('reference_id', ''),
            'quantity': kwargs.get('quantity', Decimal('100.00')),
            'unit_cost': kwargs.get('unit_cost', Decimal('10.00')),
            'notes': kwargs.get('notes', 'Test stock movement'),
            'is_active': kwargs.get('is_active', True),
        }
        return StockMovement(**defaults)

    @staticmethod
    def create(product=None, batch=None, warehouse=None, **kwargs):
        defaults = {
            'product': product or ProductFactory.create(),
            'batch': batch or BatchFactory.create(),
            'warehouse': warehouse or WarehouseFactory.create(),
            'movement_type': kwargs.get('movement_type', 'IN'),
            'reference_type': kwargs.get('reference_type', 'MANUAL'),
            'reference_id': kwargs.get('reference_id', ''),
            'quantity': kwargs.get('quantity', Decimal('100.00')),
            'unit_cost': kwargs.get('unit_cost', Decimal('10.00')),
            'notes': 'Test stock movement',
            'is_active': True,
        }
        defaults.update(kwargs)
        # Calculate total_cost with proper rounding
        defaults['total_cost'] = (abs(defaults['quantity']) * defaults['unit_cost']).quantize(Decimal('0.01'))
        movement = StockMovement(**defaults)
        movement.full_clean()
        movement.save()
        return movement


class CustomerFactory:
    """Factory for creating Customer test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'name': kwargs.get('name', f'Customer {uuid.uuid4().hex[:6]}'),
            'code': kwargs.get('code', f'CUST{uuid.uuid4().hex[:6]}'),
            'customer_type': kwargs.get('customer_type', 'INDIVIDUAL'),
            'contact_person': kwargs.get('contact_person', 'Test Contact'),
            'email': kwargs.get('email', f'customer{uuid.uuid4().hex[:6]}@test.com'),
            'phone': kwargs.get('phone', '+1234567890'),
            'address': kwargs.get('address', '123 Customer Street'),
            'city': kwargs.get('city', 'Test City'),
            'country': kwargs.get('country', 'Test Country'),
            'tax_number': kwargs.get('tax_number', ''),
            'credit_limit': kwargs.get('credit_limit', Decimal('10000.00')),
            'balance': kwargs.get('balance', Decimal('0.00')),
            'payment_terms': kwargs.get('payment_terms', 'Net 30'),
            'notes': kwargs.get('notes', ''),
            'is_active': kwargs.get('is_active', True),
        }
        return Customer(**defaults)

    @staticmethod
    def create(name=None, code=None, **kwargs):
        defaults = {
            'name': name or f'Customer {uuid.uuid4().hex[:6]}',
            'code': code or f'CUST{uuid.uuid4().hex[:6]}',
            'customer_type': 'INDIVIDUAL',
            'contact_person': 'Test Contact',
            'email': f'customer{uuid.uuid4().hex[:6]}@test.com',
            'phone': '+1234567890',
            'address': '123 Customer Street',
            'city': 'Test City',
            'country': 'Test Country',
            'tax_number': '',
            'credit_limit': Decimal('10000.00'),
            'balance': Decimal('0.00'),
            'payment_terms': 'Net 30',
            'notes': '',
            'is_active': True,
        }
        defaults.update(kwargs)
        customer = Customer(**defaults)
        customer.full_clean()
        customer.save()
        return customer


class SalesInvoiceFactory:
    """Factory for creating SalesInvoice test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'customer': kwargs.get('customer'),
            'invoice_number': kwargs.get('invoice_number', f'SI-{uuid.uuid4().hex[:8]}'),
            'order_date': kwargs.get('order_date', today),
            'invoice_date': kwargs.get('invoice_date', today),
            'due_date': kwargs.get('due_date', today + timedelta(days=30)),
            'subtotal': kwargs.get('subtotal', Decimal('0.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total_amount': kwargs.get('total_amount', Decimal('0.00')),
            'paid_amount': kwargs.get('paid_amount', Decimal('0.00')),
            'status': kwargs.get('status', 'DRAFT'),
            'payment_status': kwargs.get('payment_status', 'UNPAID'),
            'notes': kwargs.get('notes', ''),
            'is_active': kwargs.get('is_active', True),
        }
        if defaults['customer'] is None:
            defaults['customer'] = CustomerFactory.create()
        return SalesInvoice(**defaults)

    @staticmethod
    def create(customer=None, invoice_number=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'customer': customer or CustomerFactory.create(),
            'invoice_number': invoice_number or f'SI-{uuid.uuid4().hex[:8]}',
            'order_date': today,
            'invoice_date': today,
            'due_date': today + timedelta(days=30),
            'subtotal': Decimal('0.00'),
            'discount': Decimal('0.00'),
            'tax': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'paid_amount': Decimal('0.00'),
            'status': 'DRAFT',
            'payment_status': 'UNPAID',
            'notes': '',
            'is_active': True,
        }
        defaults.update(kwargs)
        invoice = SalesInvoice(**defaults)
        invoice.full_clean()
        invoice.save()
        return invoice


class SalesItemFactory:
    """Factory for creating SalesItem test data."""

    @staticmethod
    def build(**kwargs):
        defaults = {
            'invoice': kwargs.get('invoice'),
            'product': kwargs.get('product'),
            'batch': kwargs.get('batch'),
            'quantity': kwargs.get('quantity', Decimal('10.00')),
            'unit_price': kwargs.get('unit_price', Decimal('15.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total': kwargs.get('total'),
            'dispensed_quantity': kwargs.get('dispensed_quantity', Decimal('0.00')),
        }
        if defaults['invoice'] is None:
            defaults['invoice'] = SalesInvoiceFactory.create()
        if defaults['product'] is None:
            defaults['product'] = ProductFactory.create()
        if defaults['total'] is None:
            defaults['total'] = (
                defaults['quantity'] * defaults['unit_price']
                - defaults['discount'] + defaults['tax']
            )
        return SalesItem(**defaults)

    @staticmethod
    def create(invoice=None, product=None, **kwargs):
        defaults = {
            'invoice': invoice or SalesInvoiceFactory.create(),
            'product': product or ProductFactory.create(),
            'batch': kwargs.get('batch'),
            'quantity': kwargs.get('quantity', Decimal('10.00')),
            'unit_price': kwargs.get('unit_price', Decimal('15.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total': kwargs.get('total'),
            'dispensed_quantity': kwargs.get('dispensed_quantity', Decimal('0.00')),
        }
        defaults.update(kwargs)
        
        # Calculate total if not provided
        if defaults['total'] is None:
            defaults['total'] = (
                defaults['quantity'] * defaults['unit_price']
                - defaults['discount'] + defaults['tax']
            ).quantize(Decimal('0.01'))
        
        item = SalesItem(**defaults)
        item.full_clean()
        item.save()
        return item


class CustomerPaymentFactory:
    """Factory for creating CustomerPayment test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'customer': kwargs.get('customer'),
            'invoice': kwargs.get('invoice'),
            'amount': kwargs.get('amount', Decimal('100.00')),
            'payment_date': kwargs.get('payment_date', today),
            'payment_method': kwargs.get('payment_method', 'CASH'),
            'reference_number': kwargs.get('reference_number', f'REF-{uuid.uuid4().hex[:8]}'),
            'notes': kwargs.get('notes', 'Test payment'),
        }
        if defaults['customer'] is None:
            defaults['customer'] = CustomerFactory.create()
        return CustomerPayment(**defaults)

    @staticmethod
    def create(customer=None, invoice=None, amount=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'customer': customer or CustomerFactory.create(),
            'invoice': invoice,
            'amount': amount or Decimal('100.00'),
            'payment_date': today,
            'payment_method': 'CASH',
            'reference_number': f'REF-{uuid.uuid4().hex[:8]}',
            'notes': 'Test payment',
        }
        defaults.update(kwargs)
        payment = CustomerPayment(**defaults)
        payment.full_clean()
        payment.save()
        return payment


class SupplierFactory:
    """Factory for creating Supplier test data."""

    @staticmethod
    def build(**kwargs):
        defaults = {
            'name': kwargs.get('name', f'Supplier {uuid.uuid4().hex[:6]}'),
            'code': kwargs.get('code', f'SUP{uuid.uuid4().hex[:6]}'),
            'contact_person': kwargs.get('contact_person', 'Test Contact'),
            'email': kwargs.get('email', f'supplier{uuid.uuid4().hex[:6]}@test.com'),
            'phone': kwargs.get('phone', '+1234567890'),
            'address': kwargs.get('address', '123 Supplier Street'),
            'city': kwargs.get('city', 'Test City'),
            'country': kwargs.get('country', 'Test Country'),
            'tax_number': kwargs.get('tax_number', ''),
            'credit_limit': kwargs.get('credit_limit', Decimal('50000.00')),
            'balance': kwargs.get('balance', Decimal('0.00')),
            'payment_terms': kwargs.get('payment_terms', 'Net 30'),
            'notes': kwargs.get('notes', ''),
            'is_active': kwargs.get('is_active', True),
        }
        return Supplier(**defaults)

    @staticmethod
    def create(name=None, code=None, **kwargs):
        defaults = {
            'name': name or f'Supplier {uuid.uuid4().hex[:6]}',
            'code': code or f'SUP{uuid.uuid4().hex[:6]}',
            'contact_person': 'Test Contact',
            'email': f'supplier{uuid.uuid4().hex[:6]}@test.com',
            'phone': '+1234567890',
            'address': '123 Supplier Street',
            'city': 'Test City',
            'country': 'Test Country',
            'tax_number': '',
            'credit_limit': Decimal('50000.00'),
            'balance': Decimal('0.00'),
            'payment_terms': 'Net 30',
            'notes': '',
            'is_active': True,
        }
        defaults.update(kwargs)
        supplier = Supplier(**defaults)
        supplier.full_clean()
        supplier.save()
        return supplier


class PurchaseInvoiceFactory:
    """Factory for creating PurchaseInvoice test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'supplier': kwargs.get('supplier'),
            'invoice_number': kwargs.get('invoice_number', f'PI-{uuid.uuid4().hex[:8]}'),
            'order_date': kwargs.get('order_date', today),
            'invoice_date': kwargs.get('invoice_date', today),
            'due_date': kwargs.get('due_date', today + timedelta(days=30)),
            'subtotal': kwargs.get('subtotal', Decimal('0.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total_amount': kwargs.get('total_amount', Decimal('0.00')),
            'paid_amount': kwargs.get('paid_amount', Decimal('0.00')),
            'status': kwargs.get('status', 'DRAFT'),
            'payment_status': kwargs.get('payment_status', 'UNPAID'),
            'notes': kwargs.get('notes', ''),
            'is_active': kwargs.get('is_active', True),
        }
        if defaults['supplier'] is None:
            defaults['supplier'] = SupplierFactory.create()
        return PurchaseInvoice(**defaults)

    @staticmethod
    def create(supplier=None, invoice_number=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'supplier': supplier or SupplierFactory.create(),
            'invoice_number': invoice_number or f'PI-{uuid.uuid4().hex[:8]}',
            'order_date': today,
            'invoice_date': today,
            'due_date': today + timedelta(days=30),
            'subtotal': Decimal('0.00'),
            'discount': Decimal('0.00'),
            'tax': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'paid_amount': Decimal('0.00'),
            'status': 'DRAFT',
            'payment_status': 'UNPAID',
            'notes': '',
            'is_active': True,
        }
        defaults.update(kwargs)
        invoice = PurchaseInvoice(**defaults)
        invoice.full_clean()
        invoice.save()
        return invoice


class PurchaseItemFactory:
    """Factory for creating PurchaseItem test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'invoice': kwargs.get('invoice'),
            'product': kwargs.get('product'),
            'batch_number': kwargs.get('batch_number', f'BATCH{uuid.uuid4().hex[:8]}'),
            'expiry_date': kwargs.get('expiry_date', today + timedelta(days=365)),
            'quantity': kwargs.get('quantity', Decimal('100.00')),
            'unit_price': kwargs.get('unit_price', Decimal('10.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total': kwargs.get('total'),
            'received_quantity': kwargs.get('received_quantity', Decimal('0.00')),
        }
        if defaults['invoice'] is None:
            defaults['invoice'] = PurchaseInvoiceFactory.create()
        if defaults['product'] is None:
            defaults['product'] = ProductFactory.create()
        if defaults['total'] is None:
            defaults['total'] = (
                defaults['quantity'] * defaults['unit_price']
                - defaults['discount'] + defaults['tax']
            ).quantize(Decimal('0.01'))
        return PurchaseItem(**defaults)

    @staticmethod
    def create(invoice=None, product=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'invoice': invoice or PurchaseInvoiceFactory.create(),
            'product': product or ProductFactory.create(),
            'batch_number': kwargs.get('batch_number', f'BATCH{uuid.uuid4().hex[:8]}'),
            'expiry_date': kwargs.get('expiry_date', today + timedelta(days=365)),
            'quantity': kwargs.get('quantity', Decimal('100.00')),
            'unit_price': kwargs.get('unit_price', Decimal('10.00')),
            'discount': kwargs.get('discount', Decimal('0.00')),
            'tax': kwargs.get('tax', Decimal('0.00')),
            'total': kwargs.get('total'),
            'received_quantity': kwargs.get('received_quantity', Decimal('0.00')),
        }
        defaults.update(kwargs)
        
        # Calculate total if not provided
        if defaults['total'] is None:
            defaults['total'] = (
                defaults['quantity'] * defaults['unit_price']
                - defaults['discount'] + defaults['tax']
            ).quantize(Decimal('0.01'))
        
        item = PurchaseItem(**defaults)
        item.full_clean()
        item.save()
        return item


class SupplierPaymentFactory:
    """Factory for creating SupplierPayment test data."""

    @staticmethod
    def build(**kwargs):
        today = timezone.now().date()
        defaults = {
            'supplier': kwargs.get('supplier'),
            'invoice': kwargs.get('invoice'),
            'amount': kwargs.get('amount', Decimal('100.00')),
            'payment_date': kwargs.get('payment_date', today),
            'payment_method': kwargs.get('payment_method', 'CASH'),
            'reference_number': kwargs.get('reference_number', f'REF-{uuid.uuid4().hex[:8]}'),
            'notes': kwargs.get('notes', 'Test payment'),
        }
        if defaults['supplier'] is None:
            defaults['supplier'] = SupplierFactory.create()
        return SupplierPayment(**defaults)

    @staticmethod
    def create(supplier=None, invoice=None, amount=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'supplier': supplier or SupplierFactory.create(),
            'invoice': invoice,
            'amount': amount or Decimal('100.00'),
            'payment_date': today,
            'payment_method': 'CASH',
            'reference_number': f'REF-{uuid.uuid4().hex[:8]}',
            'notes': 'Test payment',
        }
        defaults.update(kwargs)
        payment = SupplierPayment(**defaults)
        payment.full_clean()
        payment.save()
        return payment


class CurrencyFactory:
    """Factory for creating Currency test data."""

    @staticmethod
    def create(code=None, **kwargs):
        defaults = {
            'code': code or 'AFN',
            'name': kwargs.get('name', 'Afghan Afghani'),
            'symbol': kwargs.get('symbol', '\u060b'),
            'is_active': True,
            'is_default': kwargs.get('is_default', False),
        }
        defaults.update(kwargs)
        
        # Ensure only one default currency
        if defaults['is_default']:
            Currency.objects.update(is_default=False)
        
        currency = Currency(**defaults)
        currency.full_clean()
        currency.save()
        return currency


class ExchangeRateFactory:
    """Factory for creating ExchangeRate test data."""

    @staticmethod
    def create(from_currency=None, to_currency=None, **kwargs):
        if from_currency is None:
            from_currency = CurrencyFactory.create(code='USD')
        if to_currency is None:
            to_currency = CurrencyFactory.create(code='AFN')
        
        defaults = {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': kwargs.get('rate', Decimal('72.50')),
            'effective_date': kwargs.get('effective_date', timezone.now().date()),
            'is_active': kwargs.get('is_active', True),
        }
        defaults.update(kwargs)
        return ExchangeRate.objects.create(**defaults)


class AccountFactory:
    """Factory for creating Account test data."""

    @staticmethod
    def build(**kwargs):
        defaults = {
            'code': kwargs.get('code', f'{uuid.uuid4().int % 10000:04d}'),
            'name': kwargs.get('name', f'Account {uuid.uuid4().hex[:6]}'),
            'account_type': kwargs.get('account_type', 'ASSET'),
            'account_category': kwargs.get('account_category', 'CURRENT_ASSET'),
            'parent': kwargs.get('parent'),
            'description': kwargs.get('description', 'Test account'),
            'is_active': kwargs.get('is_active', True),
            'is_system': kwargs.get('is_system', False),
            'balance': kwargs.get('balance', Decimal('0.00')),
        }
        return Account(**defaults)

    @staticmethod
    def create(code=None, **kwargs):
        defaults = {
            'code': code or f'{uuid.uuid4().int % 10000:04d}',
            'name': kwargs.get('name', f'Account {uuid.uuid4().hex[:6]}'),
            'account_type': kwargs.get('account_type', 'ASSET'),
            'account_category': kwargs.get('account_category', 'CURRENT_ASSET'),
            'parent': kwargs.get('parent'),
            'description': kwargs.get('description', 'Test account'),
            'is_active': True,
            'is_system': kwargs.get('is_system', False),
            'balance': kwargs.get('balance', Decimal('0.00')),
        }
        defaults.update(kwargs)
        account = Account(**defaults)
        account.full_clean()
        account.save()
        return account


class JournalEntryFactory:
    """Factory for creating JournalEntry test data."""

    @staticmethod
    def create(entry_number=None, **kwargs):
        today = timezone.now().date()
        defaults = {
            'entry_number': entry_number or f'JE-{uuid.uuid4().hex[:8]}',
            'entry_date': today,
            'entry_type': kwargs.get('entry_type', 'ADJUSTMENT'),
            'description': kwargs.get('description', 'Test journal entry'),
            'reference': kwargs.get('reference', ''),
            'is_posted': kwargs.get('is_posted', False),
            'is_active': True,
        }
        defaults.update(kwargs)
        return JournalEntry.objects.create(**defaults)


class JournalEntryLineFactory:
    """Factory for creating JournalEntryLine test data."""

    @staticmethod
    def build(**kwargs):
        defaults = {
            'entry': kwargs.get('entry'),
            'account': kwargs.get('account'),
            'debit': kwargs.get('debit', Decimal('0.00')),
            'credit': kwargs.get('credit', Decimal('0.00')),
            'description': kwargs.get('description', 'Test line item'),
        }
        if defaults['entry'] is None:
            defaults['entry'] = JournalEntryFactory.create()
        if defaults['account'] is None:
            defaults['account'] = AccountFactory.create()
        return JournalEntryLine(**defaults)

    @staticmethod
    def create(entry=None, account=None, **kwargs):
        defaults = {
            'entry': entry or JournalEntryFactory.create(),
            'account': account or AccountFactory.create(),
            'debit': kwargs.get('debit', Decimal('0.00')),
            'credit': kwargs.get('credit', Decimal('0.00')),
            'description': kwargs.get('description', 'Test line item'),
        }
        defaults.update(kwargs)
        line = JournalEntryLine(**defaults)
        line.full_clean()
        line.save()
        return line


class PaymentMethodFactory:
    """Factory for creating PaymentMethod test data."""

    @staticmethod
    def create(**kwargs):
        defaults = {
            'name': kwargs.get('name', f'Payment Method {uuid.uuid4().hex[:6]}'),
            'code': kwargs.get('code', f'PM-{uuid.uuid4().hex[:6]}'),
            'method_type': kwargs.get('method_type', 'CASH'),
            'description': kwargs.get('description', 'Test payment method'),
            'is_active': kwargs.get('is_active', True),
            'fee_percentage': kwargs.get('fee_percentage', Decimal('0.00')),
            'fee_fixed': kwargs.get('fee_fixed', Decimal('0.00')),
        }
        defaults.update(kwargs)
        return PaymentMethod.objects.create(**defaults)


class PaymentAccountFactory:
    """Factory for creating PaymentAccount test data."""

    @staticmethod
    def create(**kwargs):
        if 'accounting_account' not in kwargs:
            kwargs['accounting_account'] = AccountFactory.create()
        
        defaults = {
            'name': kwargs.get('name', f'Payment Account {uuid.uuid4().hex[:6]}'),
            'code': kwargs.get('code', f'PA-{uuid.uuid4().hex[:6]}'),
            'account_type': kwargs.get('account_type', 'CASH'),
            'is_active': kwargs.get('is_active', True),
            'current_balance': kwargs.get('current_balance', Decimal('0.00')),
        }
        defaults.update(kwargs)
        return PaymentAccount.objects.create(**defaults)


class FinancialTransactionFactory:
    """Factory for creating FinancialTransaction test data."""

    @staticmethod
    def build(**kwargs):
        if 'payment_method' not in kwargs:
            kwargs['payment_method'] = PaymentMethodFactory.create()
        if 'destination_account' not in kwargs and 'source_account' not in kwargs:
            kwargs['destination_account'] = PaymentAccountFactory.create()
        
        defaults = {
            'transaction_type': kwargs.get('transaction_type', 'RECEIPT'),
            'amount': kwargs.get('amount', Decimal('100.00')),
            'currency': kwargs.get('currency', 'AFN'),
            'fee': kwargs.get('fee', Decimal('0.00')),
            'net_amount': kwargs.get('net_amount', Decimal('100.00')),
            'description': kwargs.get('description', 'Test transaction'),
            'transaction_date': kwargs.get('transaction_date', timezone.now().date()),
            'status': kwargs.get('status', 'COMPLETED'),
        }
        defaults.update(kwargs)
        return FinancialTransaction(**defaults)

    @staticmethod
    def create(**kwargs):
        if 'payment_method' not in kwargs:
            kwargs['payment_method'] = PaymentMethodFactory.create()
        if 'destination_account' not in kwargs and 'source_account' not in kwargs:
            kwargs['destination_account'] = PaymentAccountFactory.create()
        
        defaults = {
            'transaction_type': kwargs.get('transaction_type', 'RECEIPT'),
            'amount': kwargs.get('amount', Decimal('100.00')),
            'currency': kwargs.get('currency', 'AFN'),
            'fee': kwargs.get('fee', Decimal('0.00')),
            'net_amount': kwargs.get('net_amount', Decimal('100.00')),
            'description': kwargs.get('description', 'Test transaction'),
            'transaction_date': kwargs.get('transaction_date', timezone.now().date()),
            'status': kwargs.get('status', 'COMPLETED'),
        }
        defaults.update(kwargs)
        return FinancialTransaction.objects.create(**defaults)
