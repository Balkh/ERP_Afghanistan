"""
Base test case with common setup for all ERP tests.

Provides standardized test data setup including:
- Default currency
- Chart of accounts (essential accounts)
- Default warehouse
- Common units and categories
"""
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from tests.factories import (
    CurrencyFactory,
    AccountFactory,
    WarehouseFactory,
    UnitFactory,
    CategoryFactory,
)


class BaseTestCase(TestCase):
    """
    Base test case with common ERP test fixtures.
    Sets up essential data required for most tests.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        super().setUpTestData()
        cls._setup_currency()
        cls._setup_accounts()
        cls._setup_warehouse()
        cls._setup_units()
        cls._setup_categories()
        cls._setup_payment_infrastructure()

    @classmethod
    def _setup_currency(cls):
        """Create default currency."""
        cls.currency = CurrencyFactory.create(
            code='AFN',
            name='Afghan Afghani',
            symbol='\u060b',
            is_default=True
        )
        cls.currency_usd = CurrencyFactory.create(
            code='USD',
            name='US Dollar',
            symbol='$'
        )

    @classmethod
    def _setup_accounts(cls):
        """Create essential chart of accounts."""
        # Asset accounts
        cls.account_cash = AccountFactory.create(
            code='1000',
            name='Cash',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )
        cls.account_bank = AccountFactory.create(
            code='1100',
            name='Bank Account',
            account_type='ASSET',
            account_category='CURRENT_ASSET'
        )
        cls.account_ar = AccountFactory.create(
            code='1200',
            name='Accounts Receivable',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )
        cls.account_inventory = AccountFactory.create(
            code='1300',
            name='Inventory',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )

        # Liability accounts
        cls.account_ap = AccountFactory.create(
            code='2000',
            name='Accounts Payable',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY',
            is_system=True
        )
        cls.account_tax_payable = AccountFactory.create(
            code='2100',
            name='Tax Payable',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY',
            is_system=True
        )
        cls.account_unearned_revenue = AccountFactory.create(
            code='2200',
            name='Unearned Revenue',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY'
        )

        # Equity accounts
        cls.account_equity = AccountFactory.create(
            code='3000',
            name='Owner Equity',
            account_type='EQUITY',
            account_category='OWNER_EQUITY'
        )

        # Revenue accounts
        cls.account_revenue = AccountFactory.create(
            code='4000',
            name='Sales Revenue',
            account_type='REVENUE',
            account_category='OPERATING_REVENUE',
            is_system=True
        )
        cls.account_tax_revenue = AccountFactory.create(
            code='4100',
            name='Tax Payable',
            account_type='REVENUE',
            account_category='OPERATING_REVENUE'
        )

        # Expense accounts
        cls.account_cogs = AccountFactory.create(
            code='5000',
            name='Cost of Goods Sold',
            account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD',
            is_system=True
        )
        cls.account_cogs_5100 = AccountFactory.create(
            code='5100',
            name='Cost of Goods Sold (5100)',
            account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD'
        )
        cls.account_expense = AccountFactory.create(
            code='6000',
            name='Operating Expense',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE'
        )
        cls.account_expense_6100 = AccountFactory.create(
            code='6100',
            name='Operating Expenses (6100)',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE'
        )

    @classmethod
    def _setup_warehouse(cls):
        """Create default warehouse."""
        cls.warehouse = WarehouseFactory.create(
            name='Main Warehouse',
            code='MAIN',
            is_default=True
        )

    @classmethod
    def _setup_units(cls):
        """Create common units of measurement."""
        cls.unit_tablet = UnitFactory.create(
            name='Tablet',
            symbol='TAB'
        )
        cls.unit_bottle = UnitFactory.create(
            name='Bottle',
            symbol='BTL'
        )
        cls.unit_box = UnitFactory.create(
            name='Box',
            symbol='BOX'
        )

    @classmethod
    def _setup_categories(cls):
        """Create common product categories."""
        cls.category_tablets = CategoryFactory.create(
            name='Tablets'
        )
        cls.category_syrups = CategoryFactory.create(
            name='Syrups'
        )
        cls.category_injections = CategoryFactory.create(
            name='Injections'
        )

    @classmethod
    def _setup_payment_infrastructure(cls, include_extra_codes=False):
        """
        Create payment infrastructure (methods + accounts) required by PaymentEngine.
        
        Uses get_or_create to safely coexist with test classes that create their own
        PaymentMethod/PaymentAccount records.
        """
        from payments.models import PaymentMethod, PaymentAccount

        # Always create INS and OTHER when requested, regardless of whether
        # CASH already exists from a prior test class
        if include_extra_codes:
            pm_ins, _ = PaymentMethod.objects.get_or_create(
                code='INS',
                defaults={
                    'name': 'Insurance',
                    'method_type': 'MIXED',
                    'is_active': True,
                }
            )
            cls.pm_ins = pm_ins
            pm_other, _ = PaymentMethod.objects.get_or_create(
                code='OTHER',
                defaults={
                    'name': 'Other',
                    'method_type': 'MIXED',
                    'is_active': True,
                }
            )
            cls.pm_other = pm_other

        # Create standard payment methods (get_or_create to avoid duplicate key errors)
        pm_cash, _ = PaymentMethod.objects.get_or_create(
            code='CASH',
            defaults={
                'name': 'Cash',
                'method_type': 'CASH',
                'is_active': True,
                'is_default': True,
            }
        )
        cls.pm_cash = pm_cash

        pm_bank, _ = PaymentMethod.objects.get_or_create(
            code='BANK',
            defaults={
                'name': 'Bank Transfer',
                'method_type': 'BANK_TRANSFER',
                'is_active': True,
            }
        )
        cls.pm_bank = pm_bank

        pm_cheque, _ = PaymentMethod.objects.get_or_create(
            code='CHEQUE',
            defaults={
                'name': 'Cheque',
                'method_type': 'CHEQUE',
                'is_active': True,
            }
        )
        cls.pm_cheque = pm_cheque

        pm_cc, _ = PaymentMethod.objects.get_or_create(
            code='CC',
            defaults={
                'name': 'Credit Card',
                'method_type': 'CREDIT_CARD',
                'is_active': True,
            }
        )
        cls.pm_cc = pm_cc

        # Create default payment account linked to cash account
        payment_account, created = PaymentAccount.objects.get_or_create(
            code='CASH-MAIN',
            defaults={
                'name': 'Main Cash Account',
                'account_type': 'CASH',
                'accounting_account': cls.account_cash,
                'is_active': True,
                'is_default': True,
                'current_balance': Decimal('1000000.00'),
                'currency': 'AFN',
            }
        )
        cls.payment_account = payment_account


class TransactionBaseTestCase(TransactionTestCase):
    """
    Base test case for tests requiring real transactions.
    Use this for testing atomic operations and concurrent access.
    """

    def setUp(self):
        """Set up test data before each test (TransactionTestCase flushes between tests)."""
        super().setUp()
        self._setup_currency()
        self._setup_accounts()
        self._setup_warehouse()
        self._setup_units()
        self._setup_categories()

    def _setup_currency(self):
        """Create default currency."""
        self.currency = CurrencyFactory.create(
            code='AFN',
            name='Afghan Afghani',
            symbol='\u060b',
            is_default=True
        )

    def _setup_accounts(self):
        """Create essential chart of accounts."""
        self.account_cash = AccountFactory.create(
            code='1000',
            name='Cash',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )
        self.account_ar = AccountFactory.create(
            code='1200',
            name='Accounts Receivable',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )
        self.account_inventory = AccountFactory.create(
            code='1300',
            name='Inventory',
            account_type='ASSET',
            account_category='CURRENT_ASSET',
            is_system=True
        )
        self.account_ap = AccountFactory.create(
            code='2000',
            name='Accounts Payable',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY',
            is_system=True
        )
        self.account_tax_payable = AccountFactory.create(
            code='2100',
            name='Tax Payable',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY',
            is_system=True
        )
        self.account_unearned_revenue = AccountFactory.create(
            code='2200',
            name='Unearned Revenue',
            account_type='LIABILITY',
            account_category='CURRENT_LIABILITY'
        )
        self.account_revenue = AccountFactory.create(
            code='4000',
            name='Sales Revenue',
            account_type='REVENUE',
            account_category='OPERATING_REVENUE',
            is_system=True
        )
        self.account_revenue_4100 = AccountFactory.create(
            code='4100',
            name='Sales Revenue (4100)',
            account_type='REVENUE',
            account_category='OPERATING_REVENUE'
        )
        self.account_cogs = AccountFactory.create(
            code='5000',
            name='Cost of Goods Sold',
            account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD',
            is_system=True
        )
        self.account_cogs_5100 = AccountFactory.create(
            code='5100',
            name='Cost of Goods Sold (5100)',
            account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD'
        )
        self.account_expense_6100 = AccountFactory.create(
            code='6100',
            name='Operating Expenses (6100)',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE'
        )

    def _setup_warehouse(self):
        """Create default warehouse."""
        self.warehouse = WarehouseFactory.create(
            name='Main Warehouse',
            code='MAIN',
            is_default=True
        )

    def _setup_units(self):
        """Create common units."""
        self.unit_tablet = UnitFactory.create(name='Tablet', symbol='TAB')
        self.unit_bottle = UnitFactory.create(name='Bottle', symbol='BTL')

    def _setup_categories(self):
        """Create common categories."""
        self.category_tablets = CategoryFactory.create(name='Tablets')
        self.category_syrups = CategoryFactory.create(name='Syrups')

    def _setup_payment_infrastructure(self):
        """Create payment infrastructure (methods + accounts) required by PaymentEngine."""
        from payments.models import PaymentMethod, PaymentAccount

        # Create standard payment methods
        self.pm_cash, _ = PaymentMethod.objects.get_or_create(
            code='CASH',
            defaults={
                'name': 'Cash',
                'method_type': 'CASH',
                'is_active': True,
                'is_default': True,
            }
        )
        self.pm_bank, _ = PaymentMethod.objects.get_or_create(
            code='BANK',
            defaults={
                'name': 'Bank Transfer',
                'method_type': 'BANK_TRANSFER',
                'is_active': True,
            }
        )
        self.pm_cheque, _ = PaymentMethod.objects.get_or_create(
            code='CHEQUE',
            defaults={
                'name': 'Cheque',
                'method_type': 'CHEQUE',
                'is_active': True,
            }
        )
        self.pm_cc, _ = PaymentMethod.objects.get_or_create(
            code='CC',
            defaults={
                'name': 'Credit Card',
                'method_type': 'CREDIT_CARD',
                'is_active': True,
            }
        )

        # Create default payment account linked to cash account
        self.payment_account, _ = PaymentAccount.objects.get_or_create(
            code='CASH-MAIN',
            defaults={
                'name': 'Main Cash Account',
                'account_type': 'CASH',
                'accounting_account': self.account_cash,
                'is_active': True,
                'is_default': True,
                'current_balance': Decimal('1000000.00'),
                'currency': 'AFN',
            }
        )
