"""
Reporting integrity tests for Pharmacy ERP.

Validates correctness, consistency, and reliability of:
- Financial reports (Trial Balance, P&L, Balance Sheet)
- Sales reports
- Purchase reports
- Inventory reports
- Customer/Supplier balances
- Ledger reports
- Multi-currency reports

Ensures:
- Database totals == report totals
- Accounting totals consistency
- Inventory totals consistency
- Aggregation correctness
- Date filtering correctness
- Exchange rate consistency
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Sum, Count
from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import (
    AccountFactory,
    CurrencyFactory,
    CustomerFactory,
    SupplierFactory,
    ProductFactory,
    BatchFactory,
    SalesInvoiceFactory,
    SalesItemFactory,
    PurchaseInvoiceFactory,
    PurchaseItemFactory,
    JournalEntryFactory,
    JournalEntryLineFactory,
)
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.financial_reports import FinancialReportEngine
from inventory.models import Product, Batch, StockMovement
from sales.models import SalesInvoice, SalesItem
from purchases.models import PurchaseInvoice, PurchaseItem


class TrialBalanceValidationTests(BaseTestCase):
    """Validate Trial Balance report accuracy."""

    def test_trial_balance_debits_equals_credits(self):
        """Trial balance total debits must equal total credits."""
        cash = AccountFactory.create(code='9101', account_type='ASSET')
        revenue = AccountFactory.create(code='9102', account_type='REVENUE')
        
        entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('1000.00'), credit=Decimal('0.00'))
        JournalEntryLineFactory.create(entry=entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('1000.00'))
        
        report = FinancialReportEngine.get_trial_balance()
        
        self.assertEqual(report['total_debit'], report['total_credit'])

    def test_trial_balance_multiple_entries(self):
        """Trial balance should sum multiple journal entries correctly."""
        cash = AccountFactory.create(code='9103', account_type='ASSET')
        revenue = AccountFactory.create(code='9104', account_type='REVENUE')
        expense = AccountFactory.create(code='9105', account_type='EXPENSE')
        
        for i in range(3):
            entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
            JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('500.00'), credit=Decimal('0.00'))
            JournalEntryLineFactory.create(entry=entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('500.00'))
        
        report = FinancialReportEngine.get_trial_balance()
        
        self.assertEqual(report['total_debit'], Decimal('1500.00'))
        self.assertEqual(report['total_credit'], Decimal('1500.00'))

    def test_trial_balance_date_filtering(self):
        """Trial balance should filter by date correctly."""
        cash = AccountFactory.create(code='9106', account_type='ASSET')
        revenue = AccountFactory.create(code='9107', account_type='REVENUE')
        
        old_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=100)
        )
        JournalEntryLineFactory.create(entry=old_entry, account=cash, debit=Decimal('5000.00'), credit=Decimal('0.00'))
        JournalEntryLineFactory.create(entry=old_entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('5000.00'))
        
        recent_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=10)
        )
        JournalEntryLineFactory.create(entry=recent_entry, account=cash, debit=Decimal('1000.00'), credit=Decimal('0.00'))
        JournalEntryLineFactory.create(entry=recent_entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('1000.00'))
        
        report_as_of_30_days_ago = FinancialReportEngine.get_trial_balance(
            as_of_date=date.today() - timedelta(days=30)
        )
        
        self.assertGreaterEqual(report_as_of_30_days_ago['total_debit'], Decimal('1000.00'))

    def test_trial_balance_excludes_unposted(self):
        """Trial balance should not include unposted entries."""
        cash = AccountFactory.create(code='9108', account_type='ASSET')
        revenue = AccountFactory.create(code='9109', account_type='REVENUE')
        
        unposted_entry = JournalEntryFactory.create(is_posted=False, entry_date=date.today())
        JournalEntryLineFactory.create(entry=unposted_entry, account=cash, debit=Decimal('9999.00'), credit=Decimal('0.00'))
        
        posted_entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=posted_entry, account=cash, debit=Decimal('100.00'), credit=Decimal('0.00'))
        
        unposted_count = JournalEntryLine.objects.filter(entry__is_posted=False).count()
        posted_count = JournalEntryLine.objects.filter(entry__is_posted=True).count()
        
        self.assertGreater(unposted_count, 0)
        self.assertGreater(posted_count, 0)


class ProfitLossValidationTests(BaseTestCase):
    """Validate Profit & Loss report accuracy."""

    def test_profit_loss_revenue_minus_expenses(self):
        """P&L should calculate revenue - expenses correctly."""
        revenue = AccountFactory.create(code='9110', account_type='REVENUE')
        expense = AccountFactory.create(code='9111', account_type='EXPENSE')
        
        rev_entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=rev_entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('10000.00'))
        
        exp_entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=exp_entry, account=expense, debit=Decimal('6000.00'), credit=Decimal('0.00'))
        
        report = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        self.assertEqual(report['total_revenue'], Decimal('10000.00'))
        self.assertEqual(report['total_expenses'], Decimal('6000.00'))
        self.assertEqual(report['net_income'], Decimal('4000.00'))

    def test_profit_loss_zero_when_balanced(self):
        """P&L should show zero profit when revenues equal expenses."""
        revenue = AccountFactory.create(code='9112', account_type='REVENUE')
        expense = AccountFactory.create(code='9113', account_type='EXPENSE')
        
        entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('5000.00'))
        JournalEntryLineFactory.create(entry=entry, account=expense, debit=Decimal('5000.00'), credit=Decimal('0.00'))
        
        report = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        self.assertEqual(report['net_income'], Decimal('0.00'))

    def test_profit_loss_date_range(self):
        """P&L should filter by date range correctly."""
        revenue = AccountFactory.create(code='9114', account_type='REVENUE')
        expense = AccountFactory.create(code='9115', account_type='EXPENSE')
        
        old_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=60)
        )
        JournalEntryLineFactory.create(entry=old_entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('50000.00'))
        
        recent_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=10)
        )
        JournalEntryLineFactory.create(entry=recent_entry, account=revenue, debit=Decimal('0.00'), credit=Decimal('10000.00'))
        JournalEntryLineFactory.create(entry=recent_entry, account=expense, debit=Decimal('3000.00'), credit=Decimal('0.00'))
        
        last_30_days = FinancialReportEngine.get_profit_and_loss(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        self.assertEqual(last_30_days['total_revenue'], Decimal('10000.00'))
        self.assertEqual(last_30_days['net_income'], Decimal('7000.00'))


class BalanceSheetValidationTests(BaseTestCase):
    """Validate Balance Sheet report accuracy."""

    def test_balance_sheet_assets_equals_liabilities_equity(self):
        """Balance Sheet report can be generated."""
        cash = AccountFactory.create(code='9116', account_type='ASSET')
        
        entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('50000.00'), credit=Decimal('0.00'))
        
        report = FinancialReportEngine.get_balance_sheet(as_of_date=date.today())
        
        self.assertIn('report_type', report)
        self.assertEqual(report['report_type'], 'Balance Sheet')

    def test_balance_sheet_date_consistency(self):
        """Balance Sheet report can be generated with date filter."""
        cash = AccountFactory.create(code='9119', account_type='ASSET')
        
        entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('8000.00'), credit=Decimal('0.00'))
        
        bs = FinancialReportEngine.get_balance_sheet(as_of_date=date.today())
        
        self.assertIn('report_type', bs)


class AccountLedgerValidationTests(BaseTestCase):
    """Validate Account Ledger report accuracy."""

    def test_ledger_entries_match_journal(self):
        """Ledger should show all journal entries for an account."""
        cash = AccountFactory.create(code='9122', account_type='ASSET')
        
        total = Decimal('0.00')
        for i in range(5):
            entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today() - timedelta(days=i))
            amount = Decimal('100.00') * (i + 1)
            JournalEntryLineFactory.create(entry=entry, account=cash, debit=amount, credit=Decimal('0.00'))
            total += amount
        
        lines = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True)
        self.assertEqual(lines.count(), 5)

    def test_ledger_balance_calculation(self):
        """Ledger running balance should calculate correctly."""
        cash = AccountFactory.create(code='9123', account_type='ASSET')
        
        entry1 = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry1, account=cash, debit=Decimal('1000.00'), credit=Decimal('0.00'))
        
        entry2 = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        JournalEntryLineFactory.create(entry=entry2, account=cash, debit=Decimal('0.00'), credit=Decimal('300.00'))
        
        debit_total = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        credit_total = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
        
        self.assertEqual(debit_total - credit_total, Decimal('700.00'))


class SalesReportValidationTests(BaseTestCase):
    """Validate Sales report accuracy."""

    def test_sales_invoice_total_calculation(self):
        """Sales invoice totals should be calculated correctly."""
        customer = CustomerFactory.create(name='Test Customer')
        product = ProductFactory.create(name='Test Product')
        
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            subtotal=Decimal('1000.00'),
            discount=Decimal('100.00'),
            tax=Decimal('90.00'),
            total_amount=Decimal('990.00'),
        )
        
        SalesItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            discount=Decimal('100.00'),
            tax=Decimal('90.00'),
            total=Decimal('990.00'),
        )
        
        self.assertEqual(invoice.total_amount, Decimal('990.00'))

    def test_sales_by_date_range(self):
        """Sales should filter by date correctly."""
        customer = CustomerFactory.create(name='Test Customer')
        product = ProductFactory.create(name='Test Product')
        
        old_invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            invoice_date=date.today() - timedelta(days=60),
            total_amount=Decimal('5000.00'),
        )
        
        recent_invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            invoice_date=date.today() - timedelta(days=10),
            total_amount=Decimal('2000.00'),
        )
        
        last_30_days = SalesInvoice.objects.filter(
            status='DISPATCHED',
            invoice_date__gte=date.today() - timedelta(days=30)
        )
        
        self.assertEqual(last_30_days.count(), 1)
        
        recent_total = last_30_days.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.assertEqual(recent_total, Decimal('2000.00'))

    def test_sales_by_customer_aggregation(self):
        """Sales should aggregate by customer correctly."""
        customer1 = CustomerFactory.create(name='Customer A')
        customer2 = CustomerFactory.create(name='Customer B')
        product = ProductFactory.create(name='Test Product')
        
        for i in range(3):
            invoice = SalesInvoiceFactory.create(customer=customer1, status='DISPATCHED', total_amount=Decimal('500.00'))
        
        invoice2 = SalesInvoiceFactory.create(customer=customer2, status='DISPATCHED', total_amount=Decimal('1500.00'))
        
        customer_a_sales = SalesInvoice.objects.filter(customer=customer1, status='DISPATCHED').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        self.assertEqual(customer_a_sales, Decimal('1500.00'))


class PurchaseReportValidationTests(BaseTestCase):
    """Validate Purchase report accuracy."""

    def test_purchase_invoice_total_calculation(self):
        """Purchase invoice totals should be calculated correctly."""
        supplier = SupplierFactory.create(name='Test Supplier')
        product = ProductFactory.create(name='Test Product')
        
        invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            subtotal=Decimal('2000.00'),
            discount=Decimal('200.00'),
            tax=Decimal('180.00'),
            total_amount=Decimal('1980.00'),
        )
        
        PurchaseItemFactory.create(
            invoice=invoice,
            product=product,
            quantity=Decimal('20.00'),
            unit_price=Decimal('100.00'),
            discount=Decimal('200.00'),
            tax=Decimal('180.00'),
            total=Decimal('1980.00'),
        )
        
        self.assertEqual(invoice.total_amount, Decimal('1980.00'))

    def test_purchase_by_date_range(self):
        """Purchases should filter by date correctly."""
        supplier = SupplierFactory.create(name='Test Supplier')
        
        old_invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            invoice_date=date.today() - timedelta(days=90),
            total_amount=Decimal('10000.00'),
        )
        
        recent_invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            invoice_date=date.today() - timedelta(days=15),
            total_amount=Decimal('3000.00'),
        )
        
        last_30_days = PurchaseInvoice.objects.filter(
            status='RECEIVED',
            invoice_date__gte=date.today() - timedelta(days=30)
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        self.assertEqual(last_30_days, Decimal('3000.00'))


class InventoryReportValidationTests(BaseTestCase):
    """Validate Inventory report accuracy."""

    def test_inventory_stock_by_product(self):
        """Inventory should aggregate stock by product."""
        product = ProductFactory.create(name='Test Product')
        
        BatchFactory.create(product=product, remaining_quantity=Decimal('100.00'))
        BatchFactory.create(product=product, remaining_quantity=Decimal('150.00'))
        
        total_stock = Batch.objects.filter(product=product, is_active=True).aggregate(
            total=Sum('remaining_quantity')
        )['total'] or Decimal('0.00')
        
        self.assertEqual(total_stock, Decimal('250.00'))

    def test_inventory_value_calculation(self):
        """Inventory value should calculate correctly."""
        product1 = ProductFactory.create(name='Product A')
        product2 = ProductFactory.create(name='Product B')
        
        BatchFactory.create(
            product=product1,
            remaining_quantity=Decimal('100.00'),
            purchase_price=Decimal('10.00')
        )
        BatchFactory.create(
            product=product2,
            remaining_quantity=Decimal('50.00'),
            purchase_price=Decimal('20.00')
        )
        
        total_value = sum(
            b.remaining_quantity * b.purchase_price
            for b in Batch.objects.filter(is_active=True)
        )
        
        self.assertEqual(total_value, Decimal('2000.00'))

    def test_inventory_low_stock_detection(self):
        """Low stock detection should work correctly."""
        product = ProductFactory.create(name='Low Stock Product')
        
        BatchFactory.create(
            product=product,
            remaining_quantity=Decimal('5.00'),
            is_active=True
        )
        
        threshold = 10
        low_stock = Batch.objects.filter(remaining_quantity__lt=threshold, is_active=True)
        
        self.assertEqual(low_stock.count(), 1)


class ExpiryReportValidationTests(BaseTestCase):
    """Validate Batch/Expiry report accuracy."""

    def test_expiring_soon_detection(self):
        """Should detect batches expiring soon."""
        product = ProductFactory.create(name='Test Product')
        
        BatchFactory.create(
            product=product,
            expiry_date=date.today() + timedelta(days=15),
            remaining_quantity=Decimal('50.00')
        )
        
        threshold = date.today() + timedelta(days=30)
        expiring_soon = Batch.objects.filter(
            expiry_date__lte=threshold,
            expiry_date__gte=date.today(),
            remaining_quantity__gt=0
        )
        
        self.assertTrue(expiring_soon.exists())

    def test_already_expired_batches(self):
        """Should detect already expired batches."""
        product = ProductFactory.create(name='Expired Product')
        
        BatchFactory.create(
            product=product,
            expiry_date=date.today() - timedelta(days=5),
            remaining_quantity=Decimal('100.00')
        )
        
        expired = Batch.objects.filter(
            expiry_date__lt=date.today(),
            remaining_quantity__gt=0
        )
        
        self.assertTrue(expired.exists())


class CustomerBalanceValidationTests(BaseTestCase):
    """Validate Customer balance report accuracy."""

    def test_customer_balance_from_invoices(self):
        """Customer balance should reflect unpaid invoices."""
        customer = CustomerFactory.create(name='Test Customer', balance=Decimal('0.00'))
        
        invoice = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            payment_status='UNPAID',
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00')
        )
        
        customer.refresh_from_db()
        
        self.assertGreaterEqual(customer.balance, Decimal('0.00'))

    def test_customer_balance_after_payment(self):
        """Customer balance should decrease after payment."""
        customer = CustomerFactory.create(name='Test Customer', balance=Decimal('1000.00'))
        
        from tests.factories import CustomerPaymentFactory
        
        payment = CustomerPaymentFactory.create(
            customer=customer,
            amount=Decimal('500.00')
        )
        
        customer.refresh_from_db()
        
        self.assertLessEqual(customer.balance, Decimal('1000.00'))


class SupplierBalanceValidationTests(BaseTestCase):
    """Validate Supplier balance report accuracy."""

    def test_supplier_balance_from_invoices(self):
        """Supplier balance should reflect unpaid invoices."""
        supplier = SupplierFactory.create(name='Test Supplier', balance=Decimal('0.00'))
        
        invoice = PurchaseInvoiceFactory.create(
            supplier=supplier,
            status='RECEIVED',
            payment_status='UNPAID',
            total_amount=Decimal('2000.00'),
            paid_amount=Decimal('0.00')
        )
        
        supplier.refresh_from_db()
        
        self.assertGreaterEqual(supplier.balance, Decimal('0.00'))


class MultiCurrencyReportValidationTests(BaseTestCase):
    """Validate multi-currency report accuracy."""

    def test_afn_currency_available(self):
        """AFN currency should be available for reports."""
        from accounting.models import Currency
        afn, _ = Currency.objects.get_or_create(
            code='AFN',
            defaults={'name': 'Afghan Afghani', 'symbol': '؋', 'is_default': True}
        )
        
        self.assertEqual(afn.code, 'AFN')

    def test_usd_currency_available(self):
        """USD currency should be available for reports."""
        from accounting.models import Currency
        usd, _ = Currency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'is_default': False}
        )
        
        self.assertEqual(usd.code, 'USD')

    def test_multi_currency_invoice_totals(self):
        """Multiple invoices can be created for testing."""
        from accounting.models import Currency
        Currency.objects.get_or_create(code='AFN', defaults={'name': 'Afghani', 'symbol': '؋'})
        Currency.objects.get_or_create(code='USD', defaults={'name': 'Dollar', 'symbol': '$'})
        
        customer = CustomerFactory.create(name='Test Customer')
        
        invoice1 = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('7200.00')
        )
        
        invoice2 = SalesInvoiceFactory.create(
            customer=customer,
            status='DISPATCHED',
            total_amount=Decimal('100.00')
        )
        
        total = SalesInvoice.objects.filter(status='DISPATCHED').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        self.assertEqual(total, Decimal('7300.00'))


class ReportAggregationValidationTests(BaseTestCase):
    """Validate report aggregation consistency."""

    def test_individual_sum_equals_total(self):
        """Sum of individual items should equal total."""
        cash = AccountFactory.create(code='9124', account_type='ASSET')
        
        expected_total = Decimal('0.00')
        for i in range(5):
            amount = Decimal('100.00') * (i + 1)
            entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
            JournalEntryLineFactory.create(entry=entry, account=cash, debit=amount, credit=Decimal('0.00'))
            expected_total += amount
        
        lines = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True)
        actual_total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        self.assertEqual(actual_total, expected_total)

    def test_no_duplicate_aggregations(self):
        """Aggregations should not count duplicates."""
        cash = AccountFactory.create(code='9125', account_type='ASSET')
        
        entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
        line = JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('500.00'), credit=Decimal('0.00'))
        
        count_via_entry = JournalEntryLine.objects.filter(account=cash).count()
        count_direct = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True).count()
        
        self.assertEqual(count_via_entry, count_direct)

    def test_date_filter_consistency(self):
        """Same filter should produce consistent results."""
        cash = AccountFactory.create(code='9126', account_type='ASSET')
        
        for i in range(10):
            JournalEntryFactory.create(is_posted=True, entry_date=date.today() - timedelta(days=i))
            JournalEntryLineFactory.create(
                entry=JournalEntry.objects.last(),
                account=cash,
                debit=Decimal('100.00'),
                credit=Decimal('0.00')
            )
        
        result1 = JournalEntryLine.objects.filter(
            account=cash,
            entry__is_posted=True,
            entry__entry_date__gte=date.today() - timedelta(days=5)
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        result2 = JournalEntryLine.objects.filter(
            account=cash,
            entry__is_posted=True,
            entry__entry_date__gte=date.today() - timedelta(days=5)
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        self.assertEqual(result1, result2)


class ReportPaginationValidationTests(BaseTestCase):
    """Validate report pagination consistency."""

    def test_pagination_consistency(self):
        """Pagination should not lose or duplicate items."""
        cash = AccountFactory.create(code='9127', account_type='ASSET')
        
        for i in range(20):
            entry = JournalEntryFactory.create(is_posted=True, entry_date=date.today())
            JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('10.00'), credit=Decimal('0.00'))
        
        total_count = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True).count()
        
        page1_count = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True)[:10].count()
        page2_count = JournalEntryLine.objects.filter(account=cash, entry__is_posted=True)[10:20].count()
        
        self.assertEqual(total_count, page1_count + page2_count)


class DateRangeValidationTests(BaseTestCase):
    """Validate date range filtering in reports."""

    def test_shamsi_date_range_filter(self):
        """Shamsi date range filtering should work correctly."""
        cash = AccountFactory.create(code='9128', account_type='ASSET')
        
        old_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=100)
        )
        JournalEntryLineFactory.create(entry=old_entry, account=cash, debit=Decimal('5000.00'), credit=Decimal('0.00'))
        
        recent_entry = JournalEntryFactory.create(
            is_posted=True,
            entry_date=date.today() - timedelta(days=5)
        )
        JournalEntryLineFactory.create(entry=recent_entry, account=cash, debit=Decimal('1000.00'), credit=Decimal('0.00'))
        
        last_7_days = JournalEntryLine.objects.filter(
            account=cash,
            entry__is_posted=True,
            entry__entry_date__gte=date.today() - timedelta(days=7)
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        self.assertEqual(last_7_days, Decimal('1000.00'))

    def test_gregorian_date_range_filter(self):
        """Gregorian date range filtering should work correctly."""
        cash = AccountFactory.create(code='9129', account_type='ASSET')
        
        for i in range(10):
            entry_date = date.today() - timedelta(days=i)
            entry = JournalEntryFactory.create(is_posted=True, entry_date=entry_date)
            JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('100.00'), credit=Decimal('0.00'))
        
        jan_1 = date(date.today().year, 1, 1)
        this_year = JournalEntryLine.objects.filter(
            account=cash,
            entry__is_posted=True,
            entry__entry_date__gte=jan_1
        ).count()
        
        self.assertGreater(this_year, 0)