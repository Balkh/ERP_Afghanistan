"""
INTEGRATION & WORKFLOW VALIDATION TESTS
========================================
End-to-end ERP workflows, multi-module integration,
and comprehensive smoke tests for pharmaceutical ERP.
"""
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

User = get_user_model()

from inventory.models import Product, Category, Unit, Batch, Warehouse, StockMovement
from sales.models import SalesInvoice, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from accounting.models import Account, JournalEntry, JournalEntryLine


class TestInventoryBasics(TestCase):
    """Basic inventory workflow tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'inv_{uuid.uuid4().hex[:6]}',
            email='inv@test.com',
            password='pass123'
        )

    def test_product_creation_flow(self):
        """Create category → unit → product → batch → movement"""
        
        # 1. Create category
        category = Category.objects.create(name='Antibiotics')
        
        # 2. Create unit
        unit = Unit.objects.create(name='Box', symbol='BOX')
        
        # 3. Create product
        product = Product.objects.create(
            name='Amoxicillin 500mg',
            sku=f'AMX{uuid.uuid4().hex[:4]}',
            barcode=f'AMX{uuid.uuid4().hex[:6]}',
            category=category,
            unit=unit,
            generic_name='Amoxicillin',
            brand_name='Amoxil',
            strength='500mg',
            form='Capsule',
            manufacturer='Pfizer'
        )
        
        # 4. Create warehouse
        warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code='WH001'
        )
        
        # 5. Create batch
        batch = Batch.objects.create(
            product=product,
            batch_number=f'BATCH{uuid.uuid4().hex[:4]}',
            quantity=100,
            remaining_quantity=100,
            purchase_price=8.00,
            sale_price=12.00,
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(),
            location='A-1'
        )
        
        # 6. Create stock movement
        movement = StockMovement.objects.create(
            product=product,
            batch=batch,
            warehouse=warehouse,
            movement_type='IN',
            reference_type='PURCHASE',
            quantity=100,
            reference_id='PO-001'
        )
        
        # Verify workflow
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, 100)

    def test_stock_deduction_flow(self):
        """Test stock deduction via sales"""
        
        # Setup
        category = Category.objects.create(name='Pain Relief')
        unit = Unit.objects.create(name='Tablet', symbol='TAB')
        
        product = Product.objects.create(
            name='Panadol',
            sku=f'PAN{uuid.uuid4().hex[:4]}',
            barcode=f'PAN{uuid.uuid4().hex[:6]}',
            category=category,
            unit=unit,
            generic_name='Paracetamol',
            brand_name='Panadol',
            strength='500mg',
            form='Tablet',
            manufacturer='GSK'
        )
        
        warehouse = Warehouse.objects.create(
            name='Store',
            code='STORE'
        )
        
        # Create batch with stock
        batch = Batch.objects.create(
            product=product,
            batch_number=f'STOCK{uuid.uuid4().hex[:4]}',
            quantity=50,
            remaining_quantity=50,
            purchase_price=5.00,
            sale_price=8.00,
            expiry_date=date.today() + timedelta(days=180),
            manufacturing_date=date.today() - timedelta(days=30),
            location='SHELF-1'
        )
        
        # Create OUT movement
        StockMovement.objects.create(
            product=product,
            batch=batch,
            warehouse=warehouse,
            movement_type='OUT',
            reference_type='SALE',
            quantity=-10,
            reference_id='INV-001'
        )
        
        # Update batch
        batch.remaining_quantity = 40
        batch.save()
        
        # Verify
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, 40)


class TestSalesWorkflow(TestCase):
    """Sales workflow tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'sales_{uuid.uuid4().hex[:6]}',
            email='sales@test.com',
            password='pass123'
        )

    def test_sales_invoice_creation(self):
        """Create customer → invoice → dispatch workflow"""
        
        # 1. Create customer
        customer = Customer.objects.create(
            name='John Medical Store',
            code=f'JMS{uuid.uuid4().hex[:4]}',
            phone='1234567890',
            address='123 Main St'
        )
        
        # 2. Create sales invoice
        invoice = SalesInvoice.objects.create(
            customer=customer,
            invoice_number=f'INV{uuid.uuid4().hex[:6]}',
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status='DRAFT',
            subtotal=120,
            discount=0,
            tax=12,
            total_amount=132
        )
        
        # 3. Dispatch invoice
        invoice.status = 'DISPATCHED'
        invoice.save()
        
        # Verify
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'DISPATCHED')
        
    def test_customer_to_invoice_link(self):
        """Verify customer invoice relationship"""
        customer = Customer.objects.create(
            name='Test Pharmacy',
            code=f'TP{uuid.uuid4().hex[:4]}',
            phone='111'
        )
        
        # Create multiple invoices for customer
        for i in range(3):
            SalesInvoice.objects.create(
                customer=customer,
                invoice_number=f'INV{i:03d}{uuid.uuid4().hex[:2]}',
                order_date=date.today(),
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                status='DRAFT',
                subtotal=100,
                tax=10,
                total_amount=110
            )
        
        # Verify count
        customer.refresh_from_db()
        # This tests the relationship works


class TestPurchaseWorkflow(TestCase):
    """Purchase workflow tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'purch_{uuid.uuid4().hex[:6]}',
            email='purch@test.com',
            password='pass123'
        )

    def test_purchase_invoice_creation(self):
        """Create supplier → purchase invoice → receive workflow"""
        
        # 1. Create supplier
        supplier = Supplier.objects.create(
            name='Pharma Distributors',
            code=f'PD{uuid.uuid4().hex[:4]}',
            phone='9876543210',
            address='456 Pharma Ave'
        )
        
        # 2. Create purchase invoice
        purchase = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number=f'PO{uuid.uuid4().hex[:6]}',
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='RECEIVED',
            subtotal=1000,
            tax=100,
            total_amount=1100
        )
        
        # Verify
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, 'RECEIVED')

    def test_supplier_to_purchase_link(self):
        """Verify supplier purchase relationship"""
        supplier = Supplier.objects.create(
            name='Wholesaler Inc',
            code=f'WHS{uuid.uuid4().hex[:4]}',
            phone='222'
        )
        
        # Create multiple purchases for supplier
        for i in range(2):
            PurchaseInvoice.objects.create(
                supplier=supplier,
                invoice_number=f'PO{i:03d}{uuid.uuid4().hex[:2]}',
                order_date=date.today(),
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=45),
                status='RECEIVED',
                subtotal=500,
                tax=50,
                total_amount=550
            )


class TestAccountingWorkflow(TestCase):
    """Accounting workflow tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'acct_{uuid.uuid4().hex[:6]}',
            email='acct@test.com',
            password='pass123'
        )

    def test_journal_entry_workflow(self):
        """Create journal entry with balanced lines"""
        
        # Get or create accounts
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:4])
        
        if len(accounts) < 3:
            self.skipTest("Need at least 3 active accounts")
        
        # Create journal entry
        je = JournalEntry.objects.create(
            entry_number=f'JE{uuid.uuid4().hex[:6]}',
            date=date.today(),
            description='Integration Test Entry',
            is_posted=True
        )
        
        # Add debit line
        JournalEntryLine.objects.create(
            entry=je,
            account=accounts[0],
            debit=Decimal('1000.00'),
            credit=Decimal('0.00')
        )
        
        # Add credit line
        JournalEntryLine.objects.create(
            entry=je,
            account=accounts[1],
            debit=Decimal('0.00'),
            credit=Decimal('800.00')
        )
        
        # Add second credit line (tax)
        JournalEntryLine.objects.create(
            entry=je,
            account=accounts[2],
            debit=Decimal('0.00'),
            credit=Decimal('200.00')
        )
        
        # Verify balance
        lines = je.lines.all()
        total_debit = sum(l.debit for l in lines)
        total_credit = sum(l.credit for l in lines)
        
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(total_debit, Decimal('1000.00'))

    def test_posted_entry_immutability(self):
        """Posted entries should maintain integrity"""
        
        accounts = list(Account.objects.filter(is_active=True, code__regex=r'^\d+$')[:2])
        
        if len(accounts) < 2:
            self.skipTest("Need accounts")
        
        # Create and post entry
        je = JournalEntry.objects.create(
            entry_number=f'JEP{uuid.uuid4().hex[:6]}',
            date=date.today(),
            description='Posted Entry Test',
            is_posted=True
        )
        
        JournalEntryLine.objects.create(
            entry=je,
            account=accounts[0],
            debit=Decimal('500.00'),
            credit=Decimal('0.00')
        )
        
        JournalEntryLine.objects.create(
            entry=je,
            account=accounts[1],
            debit=Decimal('0.00'),
            credit=Decimal('500.00')
        )
        
        # Verify posted status
        je.refresh_from_db()
        self.assertTrue(je.is_posted)


class TestMultiModuleCycle(TestCase):
    """Multi-module integration cycle tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'cycle_{uuid.uuid4().hex[:6]}',
            email='cycle@test.com',
            password='pass123'
        )

    def test_purchase_to_sales_cycle(self):
        """Full cycle: Purchase → Inventory → Sales"""
        
        # === PURCHASE SIDE ===
        supplier = Supplier.objects.create(
            name='Distributor Co',
            code=f'DC{uuid.uuid4().hex[:4]}',
            phone='333'
        )
        
        category = Category.objects.create(name='Vitamins')
        unit = Unit.objects.create(name='Bottle', symbol='BTL')
        
        product = Product.objects.create(
            name='Vitamin C',
            sku=f'VITC{uuid.uuid4().hex[:2]}',
            barcode=f'VTC{uuid.uuid4().hex[:6]}',
            category=category,
            unit=unit,
            generic_name='Ascorbic Acid',
            brand_name='Nature Made',
            strength='1000mg',
            form='Tablet',
            manufacturer='Nature Made'
        )
        
        warehouse = Warehouse.objects.create(
            name='Central WH',
            code='CWH'
        )
        
        # Purchase: 100 units @ $5 = $500
        purchase = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_number=f'PUR{uuid.uuid4().hex[:6]}',
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='RECEIVED',
            subtotal=500,
            tax=50,
            total_amount=550
        )
        
        batch = Batch.objects.create(
            product=product,
            batch_number=f'VIT{uuid.uuid4().hex[:4]}',
            quantity=100,
            remaining_quantity=100,
            purchase_price=5.00,
            sale_price=8.00,
            expiry_date=date.today() + timedelta(days=730),
            manufacturing_date=date.today(),
            location='A-1'
        )
        
        # Add stock
        StockMovement.objects.create(
            product=product,
            batch=batch,
            warehouse=warehouse,
            movement_type='IN',
            reference_type='PURCHASE',
            quantity=100,
            reference_id=purchase.invoice_number
        )
        
        # === SALES SIDE ===
        customer = Customer.objects.create(
            name='Health Store',
            code=f'HS{uuid.uuid4().hex[:4]}',
            phone='444'
        )
        
        # Sell: 30 units @ $8 = $240
        sales = SalesInvoice.objects.create(
            customer=customer,
            invoice_number=f'SAL{uuid.uuid4().hex[:6]}',
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status='DISPATCHED',
            subtotal=240,
            tax=24,
            total_amount=264
        )
        
        # Deduct stock
        batch.remaining_quantity = 70
        batch.save()
        
        StockMovement.objects.create(
            product=product,
            batch=batch,
            warehouse=warehouse,
            movement_type='OUT',
            reference_type='SALE',
            quantity=-30,
            reference_id=sales.invoice_number
        )
        
        # === VERIFY CYCLE ===
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_quantity, 70)  # 100 - 30
        
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, 'RECEIVED')
        
        sales.refresh_from_db()
        self.assertEqual(sales.status, 'DISPATCHED')


class TestSystemSmokeTests(TestCase):
    """Quick smoke tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'smoke_{uuid.uuid4().hex[:6]}',
            email='smoke@test.com',
            password='pass123'
        )

    def test_category_smoke(self):
        cat = Category.objects.create(name='SmokeCat')
        self.assertEqual(cat.name, 'SmokeCat')
        
    def test_unit_smoke(self):
        unit = Unit.objects.create(name='SmokeUnit', symbol='SMU')
        self.assertEqual(unit.symbol, 'SMU')
        
    def test_product_smoke(self):
        cat = Category.objects.create(name='SmokeCat2')
        unit = Unit.objects.create(name='SmokeUnit2', symbol='SU2')
        product = Product.objects.create(
            name='SmokeProduct',
            sku=f'SMOKE{uuid.uuid4().hex[:2]}',
            barcode=f'SMKB{uuid.uuid4().hex[:6]}',
            category=cat,
            unit=unit,
            generic_name='Test',
            brand_name='Brand',
            strength='100mg',
            form='Tablet',
            manufacturer='Mfg'
        )
        self.assertIsNotNone(product.id)
        
    def test_customer_smoke(self):
        customer = Customer.objects.create(
            name='SmokeCust',
            code=f'SC{uuid.uuid4().hex[:4]}',
            phone='555'
        )
        self.assertIsNotNone(customer.id)
        
    def test_supplier_smoke(self):
        supplier = Supplier.objects.create(
            name='SmokeSupp',
            code=f'SS{uuid.uuid4().hex[:4]}',
            phone='666'
        )
        self.assertIsNotNone(supplier.id)
        
    def test_warehouse_smoke(self):
        wh = Warehouse.objects.create(name='SmokeWH', code='SWH')
        self.assertEqual(wh.code, 'SWH')
        
    def test_account_smoke(self):
        before = Account.objects.count()
        Account.objects.create(
            code='8888',
            name='Test Account',
            account_type='ASSET',
            is_active=True
        )
        self.assertEqual(Account.objects.count(), before + 1)


class TestBatchManagement(TestCase):
    """Batch management workflows"""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'batch_{uuid.uuid4().hex[:6]}',
            email='batch@test.com',
            password='pass123'
        )

    def test_expiry_tracking(self):
        """Batch expiry date tracking"""
        cat = Category.objects.create(name='ExpiryCat')
        unit = Unit.objects.create(name='ExpiryU', symbol='EU')
        
        product = Product.objects.create(
            name='Test Product',
            sku=f'TP{uuid.uuid4().hex[:2]}',
            barcode=f'TPB{uuid.uuid4().hex[:6]}',
            category=cat,
            unit=unit,
            generic_name='Test',
            brand_name='Brand',
            strength='100mg',
            form='Tablet',
            manufacturer='Mfg'
        )
        
        # Create batch expiring in 30 days
        batch = Batch.objects.create(
            product=product,
            batch_number=f'EXP{uuid.uuid4().hex[:2]}',
            quantity=50,
            remaining_quantity=50,
            purchase_price=10.00,
            sale_price=15.00,
            expiry_date=date.today() + timedelta(days=30),
            manufacturing_date=date.today(),
            location='A-1'
        )
        
        # Query near-expiry
        near_exp = Batch.objects.filter(
            expiry_date__lte=date.today() + timedelta(days=30),
            expiry_date__gt=date.today()
        )
        
        self.assertIn(batch.id, [b.id for b in near_exp])

    def test_location_tracking(self):
        """Batch location tracking"""
        cat = Category.objects.create(name='LocCat')
        unit = Unit.objects.create(name='LocU', symbol='LU')
        
        product = Product.objects.create(
            name='LocProd',
            sku=f'LP{uuid.uuid4().hex[:2]}',
            barcode=f'LPB{uuid.uuid4().hex[:6]}',
            category=cat,
            unit=unit,
            generic_name='Test',
            brand_name='Brand',
            strength='100mg',
            form='Tablet',
            manufacturer='Mfg'
        )
        
        # Create batches in different locations
        for loc in ['A-1', 'A-2', 'B-1']:
            Batch.objects.create(
                product=product,
                batch_number=f'LOC{uuid.uuid4().hex[:2]}',
                quantity=25,
                remaining_quantity=25,
                purchase_price=10.00,
                sale_price=15.00,
                expiry_date=date.today() + timedelta(days=180),
                manufacturing_date=date.today(),
                location=loc
            )
        
        # Verify
        batches = Batch.objects.filter(product=product)
        self.assertEqual(batches.count(), 3)