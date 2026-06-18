"""
Regression tests for Phase 6-7 forensic audit fixes.

Each test MUST fail before the fix and pass after.
Tests verify:
1. Balance signal uses correct normal-balance convention for CREDIT-normal accounts
2. eval() replaced with ast.literal_eval() in pattern mining
3. CustomerPayment/SupplierPayment do NOT create duplicate FinancialTransactions on update
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine


class BalanceSignalNormalBalanceTest(TransactionTestCase):
    """
    REGRESSION: _recalc_account_balance_on_line_change hardcoded `debit - credit`
    for ALL account types. This is wrong for CREDIT-normal accounts
    (LIABILITY, EQUITY, REVENUE) which should use `credit - debit`.
    """

    def setUp(self):
        import random
        base = random.randint(990000, 999999)
        self.asset_account = Account.objects.create(
            code=str(base + 1), name='Test Cash', account_type='ASSET',
            balance=Decimal('0.00'), is_active=True
        )
        self.liability_account = Account.objects.create(
            code=str(base + 2), name='Test AP', account_type='LIABILITY',
            balance=Decimal('0.00'), is_active=True
        )
        self.revenue_account = Account.objects.create(
            code=str(base + 3), name='Test Revenue', account_type='REVENUE',
            balance=Decimal('0.00'), is_active=True
        )
        self.expense_account = Account.objects.create(
            code=str(base + 4), name='Test Expense', account_type='EXPENSE',
            balance=Decimal('0.00'), is_active=True
        )

    def test_asset_balance_is_debit_minus_credit(self):
        """ASSET account: balance = debit - credit."""
        entry = JournalEntry.objects.create(
            entry_number='TEST-001', entry_date=timezone.now().date(),
            entry_type='GENERAL', description='Test', is_posted=False
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.asset_account,
            debit=Decimal('500.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.asset_account,
            debit=Decimal('0.00'), credit=Decimal('200.00')
        )
        self.asset_account.refresh_from_db()
        self.assertEqual(self.asset_account.balance, Decimal('300.00'))

    def test_liability_balance_is_credit_minus_debit(self):
        """REGRESSION: LIABILITY account must use credit - debit, NOT debit - credit."""
        entry = JournalEntry.objects.create(
            entry_number='TEST-002', entry_date=timezone.now().date(),
            entry_type='GENERAL', description='Test', is_posted=False
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.liability_account,
            debit=Decimal('100.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.liability_account,
            debit=Decimal('0.00'), credit=Decimal('500.00')
        )
        self.liability_account.refresh_from_db()
        # CORRECT: 500 credit - 100 debit = 400
        # BUG WAS: 100 debit - 500 credit = -400 (WRONG)
        self.assertEqual(self.liability_account.balance, Decimal('400.00'))

    def test_revenue_balance_is_credit_minus_debit(self):
        """REGRESSION: REVENUE account must use credit - debit."""
        entry = JournalEntry.objects.create(
            entry_number='TEST-003', entry_date=timezone.now().date(),
            entry_type='GENERAL', description='Test', is_posted=False
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.revenue_account,
            debit=Decimal('50.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.revenue_account,
            debit=Decimal('0.00'), credit=Decimal('1000.00')
        )
        self.revenue_account.refresh_from_db()
        self.assertEqual(self.revenue_account.balance, Decimal('950.00'))

    def test_expense_balance_is_debit_minus_credit(self):
        """EXPENSE account: balance = debit - credit."""
        entry = JournalEntry.objects.create(
            entry_number='TEST-004', entry_date=timezone.now().date(),
            entry_type='GENERAL', description='Test', is_posted=False
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.expense_account,
            debit=Decimal('300.00'), credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.expense_account,
            debit=Decimal('0.00'), credit=Decimal('50.00')
        )
        self.expense_account.refresh_from_db()
        self.assertEqual(self.expense_account.balance, Decimal('250.00'))

    def test_balance_signal_on_line_delete(self):
        """Balance signal fires on DELETE too — credit-normal account stays correct."""
        entry = JournalEntry.objects.create(
            entry_number='TEST-005', entry_date=timezone.now().date(),
            entry_type='GENERAL', description='Test', is_posted=False
        )
        line1 = JournalEntryLine.objects.create(
            entry=entry, account=self.liability_account,
            debit=Decimal('0.00'), credit=Decimal('1000.00')
        )
        line2 = JournalEntryLine.objects.create(
            entry=entry, account=self.liability_account,
            debit=Decimal('200.00'), credit=Decimal('0.00')
        )
        self.liability_account.refresh_from_db()
        self.assertEqual(self.liability_account.balance, Decimal('800.00'))

        # Delete the debit line — balance should increase to 1000
        line2.delete()
        self.liability_account.refresh_from_db()
        self.assertEqual(self.liability_account.balance, Decimal('1000.00'))


class EvalReplacementTest(TestCase):
    """
    REGRESSION: eval() was used in patterns.py to parse tuple strings.
    Replaced with ast.literal_eval() for safety.
    """

    def test_pattern_mining_no_exec(self):
        """Pattern mining engine should not use eval() — only ast.literal_eval()."""
        import re
        import inspect
        from core.operations.intelligence import patterns
        source = inspect.getsource(patterns)
        # Find bare eval( calls — not literal_eval( or other variants
        bare_eval_calls = re.findall(r'(?<![_a-zA-Z])eval\s*\(', source)
        self.assertEqual(len(bare_eval_calls), 0,
                         f'patterns.py still contains bare eval() calls: {bare_eval_calls}')
        self.assertIn('literal_eval', source,
                      'patterns.py should use ast.literal_eval()')


class PaymentDuplicatePreventionTest(TransactionTestCase):
    """
    REGRESSION: CustomerPayment.save() and SupplierPayment.save() called
    _create_payment_transaction() on every save(), including updates.
    This created duplicate FinancialTransaction records.
    """

    def setUp(self):
        from payments.models import PaymentMethod, PaymentAccount
        from sales.models import Customer
        from purchases.models import Supplier

        self.payment_method, _ = PaymentMethod.objects.get_or_create(
            code='CASH', defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True}
        )
        import random
        _uid = random.randint(980000, 989999)
        self.cash_account = Account.objects.create(
            code=str(_uid), name='Test Cash', account_type='ASSET', is_active=True
        )
        self.payment_account = PaymentAccount.objects.create(
            code=f'CASH{_uid}', name='Main Cash', account_type='CASH',
            accounting_account=self.cash_account,
            current_balance=Decimal('0.00'), is_active=True
        )
        self.customer = Customer.objects.create(
            name='Test Customer', phone='123', is_active=True
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier', phone='456', is_active=True
        )

    def test_customer_payment_no_duplicate_on_update(self):
        """Updating a CustomerPayment should NOT create a new FinancialTransaction."""
        from sales.models import CustomerPayment

        payment = CustomerPayment(
            customer=self.customer,
            amount=Decimal('100.00'),
            payment_date=timezone.now().date(),
            payment_method='CASH',
        )

        # Mock PaymentEngine to avoid needing full accounting setup
        with patch('payments.services.PaymentEngine') as mock_engine:
            mock_engine.process_receipt.return_value = {'success': True, 'txn_id': 'TXN001'}
            payment.save()

            # Verify first save created transaction
            self.assertEqual(mock_engine.process_receipt.call_count, 1)

            # Now update the payment (notes change)
            mock_engine.reset_mock()
            payment.notes = 'Updated notes'
            payment.save()

            # BUG WAS: process_receipt called again on update
            # FIX: should NOT be called on update
            self.assertEqual(mock_engine.process_receipt.call_count, 0,
                             'FinancialTransaction created on update — duplicate!')

    def test_supplier_payment_no_duplicate_on_update(self):
        """Updating a SupplierPayment should NOT create a new FinancialTransaction."""
        from purchases.models import SupplierPayment

        payment = SupplierPayment(
            supplier=self.supplier,
            amount=Decimal('200.00'),
            payment_date=timezone.now().date(),
            payment_method='CASH',
        )

        with patch('payments.services.PaymentEngine') as mock_engine:
            mock_engine.process_payment.return_value = {'success': True, 'txn_id': 'TXN002'}
            payment.save()

            self.assertEqual(mock_engine.process_payment.call_count, 1)

            mock_engine.reset_mock()
            payment.notes = 'Updated'
            payment.save()

            self.assertEqual(mock_engine.process_payment.call_count, 0,
                             'FinancialTransaction created on update — duplicate!')


# ============================================================
# Company scoping regression tests (Phase 8 viewset fixes)
# ============================================================

class SalesItemCompanyScopingTest(TestCase):
    """
    Verify SalesItemViewSet returns only items belonging to the
    current tenant's company via invoice__company.
    """
    def setUp(self):
        from core.models import Company
        from sales.models import Customer, SalesInvoice, SalesItem
        from inventory.models import Product, Category, Unit
        from django.contrib.auth import get_user_model
        from decimal import Decimal

        User = get_user_model()
        self.user = User.objects.create_user(
            username='scoper', password='test123', is_staff=True
        )
        self.company_a = Company.objects.create(name='Company A', code='SCOPEA')
        self.company_b = Company.objects.create(name='Company B', code='SCOPEB')

        cat = Category.objects.create(name='TestCat')
        unit = Unit.objects.create(name='Unit', symbol='U')

        for company in (self.company_a, self.company_b):
            prod = Product.objects.create(
                name=f'Product {company.code}',
                generic_name=f'prod_{company.code}',
                brand_name=f'Brand {company.code}',
                category=cat,
                unit=unit,
                company=company,
                strength='10mg',
                form='Tablet',
                manufacturer='TestMfg',
                barcode=f'BC{company.code}',
                sku=f'SKU{company.code}',
            )
            cust = Customer.objects.create(
                name=f'Customer {company.code}',
                code=f'CUST-{company.code}',
                company=company,
            )
            inv = SalesInvoice.objects.create(
                invoice_number=f'INV-{company.code}',
                customer=cust,
                company=company,
                order_date=timezone.now().date(),
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date(),
            )
            SalesItem.objects.create(
                invoice=inv,
                product=prod,
                quantity=Decimal('5.00'),
                unit_price=Decimal('15.00'),
                total=Decimal('75.00'),
            )

    def test_scoped_items_exclude_other_company(self):
        from sales.models import SalesItem
        from core.multitenant.context import TenantContext

        TenantContext.set_company_id(str(self.company_a.id))
        try:
            from django.test import RequestFactory
            from sales.views import SalesItemViewSet
            factory = RequestFactory()
            request = factory.get('/api/sales/items/')
            request.user = self.user
            view = SalesItemViewSet.as_view({'get': 'list'})
            response = view(request)
            items = response.data if isinstance(response.data, list) else response.data.get('results', [])
            returned_ids = {str(item.get('id', '')) for item in items}
            other_items = SalesItem.objects.filter(invoice__company=self.company_b)
            for item in other_items:
                self.assertNotIn(str(item.id), returned_ids,
                                 'SalesItem from another company leaked!')
        finally:
            TenantContext.set_company_id(None)
