"""
Enterprise Lifecycle Integration Tests.
Tests complete business flows: Purchase→Inventory→Accounting→Reports.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase

from inventory.models import Product, Category, Unit, Warehouse, Batch, StockMovement
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from inventory.service.stock_integration import StockIntegrationService
from inventory.service import StockSelectionMode


class PurchaseToInventoryToAccountingTest(TransactionTestCase):
    """Test Purchase → Inventory → Accounting lifecycle."""

    def setUp(self):
        # Setup accounts
        self.inventory = Account.objects.create(code='1200', name='Inventory', account_type='ASSET', is_active=True)
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ap = Account.objects.create(code='2000', name='Accounts Payable', account_type='LIABILITY', is_active=True)
        self.purchase = Account.objects.create(code='5100', name='Purchase Expense', account_type='EXPENSE', is_active=True)

        # Setup inventory
        self.cat = Category.objects.create(name='Medicines', is_active=True)
        self.unit = Unit.objects.create(name='Box', symbol='BX', is_active=True)
        self.prod = Product.objects.create(name='Panadol', sku='PAN500', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Main Warehouse', code='WH01', is_active=True)

    def test_purchase_creates_stock_movement_and_journal_entry(self):
        """Purchase should create both stock movement and journal entry."""
        # Create stock movement for purchase
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='PO-001',
            quantity=Decimal('100'),
            unit_cost=Decimal('5.00'),
            notes='Purchase order #PO-001'
        )
        self.assertIsNotNone(movement.id)
        self.assertEqual(movement.movement_type, 'IN')

        # Create journal entry for purchase
        lines = [
            {'account_id': str(self.inventory.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.ap.id), 'debit': '0', 'credit': '500'},
        ]
        result = JournalEngine.create_entry('PURCHASE', 'PO-001', lines)
        self.assertTrue(result['success'])
        JournalEngine.post_entry(result['entry_id'])

        # Verify journal entry is posted
        entry = JournalEntry.objects.get(id=result['entry_id'])
        self.assertTrue(entry.is_posted)

    def test_purchase_increases_inventory_valuation(self):
        """Purchase should increase inventory valuation."""
        Batch.objects.create(
            product=self.prod, batch_number='B-PO-001', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('5.00'), sale_price=Decimal('8.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location=str(self.wh.id), is_active=True
        )

        total = StockIntegrationService.get_total_available_stock(self.prod, self.wh)
        self.assertEqual(total, Decimal('100'))

        # Calculate inventory value
        batches = Batch.objects.filter(product=self.prod, location=str(self.wh.id), is_active=True)
        total_value = sum(b.remaining_quantity * b.purchase_price for b in batches)
        self.assertEqual(total_value, Decimal('500'))

    def test_no_orphan_stock_movements(self):
        """All stock movements must have valid references."""
        movement = StockIntegrationService.create_stock_movement(
            product=self.prod,
            warehouse=self.wh,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='LIFE-001',
            quantity=Decimal('50'),
            unit_cost=Decimal('10.00'),
            notes='Lifecycle test'
        )

        # Verify movement has reference
        self.assertEqual(movement.reference_type, 'PURCHASE')
        self.assertEqual(movement.reference_id, 'LIFE-001')


class InventoryToSalesToCOGSTest(TransactionTestCase):
    """Test Inventory → Sales → COGS → Reporting lifecycle."""

    def setUp(self):
        # Setup accounts
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='Accounts Receivable', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE', is_active=True)
        self.cogs = Account.objects.create(code='5000', name='COGS', account_type='EXPENSE', is_active=True)
        self.inventory = Account.objects.create(code='1200', name='Inventory', account_type='ASSET', is_active=True)

        # Setup inventory
        self.cat = Category.objects.create(name='Pharma', is_active=True)
        self.unit = Unit.objects.create(name='Unit', symbol='U', is_active=True)
        self.prod = Product.objects.create(name='Drug A', sku='DRUGA', category=self.cat, unit=self.unit, is_active=True)
        self.wh = Warehouse.objects.create(name='Pharmacy', code='PH01', is_active=True)

    def test_sale_reduces_inventory_and_creates_cogs_entry(self):
        """Sale should reduce inventory and create COGS journal entry."""
        # Create inventory
        Batch.objects.create(
            product=self.prod, batch_number='B-SALE-001', quantity=100, remaining_quantity=100,
            purchase_price=Decimal('5.00'), sale_price=Decimal('10.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today(), location=str(self.wh.id), is_active=True
        )

        # Verify initial stock
        initial_stock = StockIntegrationService.get_total_available_stock(self.prod, self.wh)
        self.assertEqual(initial_stock, Decimal('100'))

        # Allocate stock for sale
        allocation = StockIntegrationService.allocate_stock(
            self.prod, Decimal('30'), self.wh, StockSelectionMode.FEFO
        )
        self.assertTrue(allocation.success)

        # Create stock movement (OUT)
        for alloc in allocation.allocations:
            StockIntegrationService.create_stock_movement(
                product=self.prod,
                warehouse=self.wh,
                movement_type='OUT',
                reference_type='SALE',
                reference_id='INV-001',
                quantity=-alloc.quantity,
                unit_cost=alloc.unit_cost,
                notes='Sales invoice #INV-001'
            )

        # Create COGS journal entry
        lines = [
            {'account_id': str(self.cogs.id), 'debit': '150', 'credit': '0'},
            {'account_id': str(self.inventory.id), 'debit': '0', 'credit': '150'},
        ]
        result = JournalEngine.create_entry('COGS', 'INV-001', lines)
        JournalEngine.post_entry(result['entry_id'])

        # Verify remaining stock
        remaining = StockIntegrationService.get_total_available_stock(self.prod, self.wh)
        self.assertEqual(remaining, Decimal('70'))

    def test_journal_entry_reflects_sale_transaction(self):
        """Journal entry must accurately reflect sale transaction."""
        # Create sale journal entry
        lines = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result = JournalEngine.create_entry('SALE', 'INV-002', lines)
        JournalEngine.post_entry(result['entry_id'])

        # Verify in trial balance
        tb = FinancialReportEngine.get_trial_balance(date.today())
        cash_row = next((a for a in tb['accounts'] if a['account_code'] == '1000'), None)
        sales_row = next((a for a in tb['accounts'] if a['account_code'] == '4000'), None)

        self.assertIsNotNone(cash_row)
        self.assertIsNotNone(sales_row)
        self.assertEqual(cash_row['debit'], Decimal('1000'))
        self.assertEqual(sales_row['credit'], Decimal('1000'))


class PaymentToLedgerToCashFlowTest(TransactionTestCase):
    """Test Payment → Ledger → Cash Flow lifecycle."""

    def setUp(self        ):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.bank = Account.objects.create(code='1010', name='Bank', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='Accounts Receivable', account_type='ASSET', is_active=True)

    def test_payment_reduces_ar_and_increases_cash(self):
        """Payment should reduce AR and increase Cash in ledger."""
        # Create invoice (AR)
        lines1 = [
            {'account_id': str(self.ar.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '1000'},
        ]
        result1 = JournalEngine.create_entry('INVOICE', 'INV-001', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        # Create payment (Receipt)
        lines2 = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '1000'},
        ]
        result2 = JournalEngine.create_entry('RECEIPT', 'RCT-001', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Verify ledger
        cash_ledger = FinancialReportEngine.get_account_ledger(str(self.cash.id), date.today(), date.today())
        ar_ledger = FinancialReportEngine.get_account_ledger(str(self.ar.id), date.today(), date.today())

        self.assertEqual(cash_ledger['total_debit'], Decimal('1000'))
        self.assertEqual(ar_ledger['total_credit'], Decimal('1000'))


class InvoiceToJournalToTrialBalanceTest(TransactionTestCase):
    """Test Invoice → Journal → Trial Balance lifecycle."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.expense = Account.objects.create(code='5000', name='Expense', account_type='EXPENSE', is_active=True)
        self.cogs = Account.objects.create(code='5100', name='COGS', account_type='EXPENSE', is_active=True)

    def test_trial_balance_reflects_all_journal_entries(self):
        """Trial balance must accurately reflect all posted journal entries."""
        # Create multiple entries
        entries = [
            ('SALE', 'INV-001', [(self.cash.id, '1000', '0'), (self.sales.id, '0', '1000')]),
            ('EXPENSE', 'EXP-001', [(self.expense.id, '300', '0'), (self.cash.id, '0', '300')]),
            ('SALE', 'INV-002', [(self.cash.id, '500', '0'), (self.sales.id, '0', '500')]),
        ]

        for entry_type, ref, lines_data in entries:
            lines = [
                {'account_id': str(acc_id), 'debit': dr, 'credit': cr}
                for acc_id, dr, cr in lines_data
            ]
            result = JournalEngine.create_entry(entry_type, ref, lines)
            JournalEngine.post_entry(result['entry_id'])

        # Verify trial balance
        tb = FinancialReportEngine.get_trial_balance(date.today())
        self.assertEqual(tb['total_debit'], tb['total_credit'])
        # Total: 1000 + 300 + 500 = 1800 debit, 1000 + 300 + 500 = 1800 credit

    def test_no_orphan_journal_entries(self):
        """All journal entries must have balanced debits and credits."""
        lines = [
            {'account_id': str(self.cash.id), 'debit': '500', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '500'},
        ]
        result = JournalEngine.create_entry('SALE', 'ORPHAN-TEST', lines)
        JournalEngine.post_entry(result['entry_id'])

        entry = JournalEntry.objects.get(entry_number='ORPHAN-TEST')
        lines_qs = JournalEntryLine.objects.filter(entry=entry)

        total_debit = sum(l.debit for l in lines_qs)
        total_credit = sum(l.credit for l in lines_qs)
        self.assertEqual(total_debit, total_credit)


class FinancialReportsReflectTransactionsTest(TransactionTestCase):
    """Test financial reports correctly reflect all transactions."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)
        self.cogs = Account.objects.create(code='5000', name='COGS', account_type='EXPENSE', is_active=True)
        self.expense = Account.objects.create(code='5100', name='Rent', account_type='EXPENSE', is_active=True)

    def test_pnl_reflects_revenue_and_expenses(self):
        """P&L must correctly reflect revenue and expenses."""
        # Create revenue
        lines1 = [
            {'account_id': str(self.cash.id), 'debit': '5000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '5000'},
        ]
        JournalEngine.create_entry('SALE', 'PL-TEST-1', lines1)['entry_id']
        JournalEngine.post_entry(JournalEngine.create_entry('SALE', 'PL-TEST-1', lines1)['entry_id'])

        # Create expenses
        lines2 = [
            {'account_id': str(self.cogs.id), 'debit': '2000', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '2000'},
        ]
        result2 = JournalEngine.create_entry('COGS', 'PL-TEST-2', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        lines3 = [
            {'account_id': str(self.expense.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.cash.id), 'debit': '0', 'credit': '1000'},
        ]
        result3 = JournalEngine.create_entry('EXPENSE', 'PL-TEST-3', lines3)
        JournalEngine.post_entry(result3['entry_id'])

        pl = FinancialReportEngine.get_profit_and_loss(date.today(), date.today())
        self.assertEqual(pl['total_revenue'], Decimal('5000'))
        self.assertEqual(pl['total_expenses'], Decimal('3000'))
        self.assertEqual(pl['net_income'], Decimal('2000'))