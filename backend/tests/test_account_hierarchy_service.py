"""
Tests for AccountHierarchyService.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from tests.factories import AccountFactory, JournalEntryFactory, JournalEntryLineFactory


class AccountHierarchyServiceTests(TestCase):
    """Tests for AccountHierarchyService methods."""

    def test_calculate_account_balances(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        cash = AccountFactory.create(code='1010', account_type='ASSET')
        revenue = AccountFactory.create(code='4100', account_type='REVENUE')
        entry = JournalEntryFactory.create(is_posted=True, is_active=True)
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('500.00'))
        JournalEntryLineFactory.create(entry=entry, account=revenue, credit=Decimal('500.00'))
        
        # Clear cached balances
        AccountHierarchyService.calculate_account_balances()
        
        cash.refresh_from_db()
        revenue.refresh_from_db()
        self.assertEqual(cash.balance, Decimal('500.00'))
        self.assertEqual(revenue.balance, Decimal('500.00'))

    def test_create_account(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        parent = AccountFactory.create(code='1000', account_type='ASSET')
        child = AccountHierarchyService.create_account('1010', 'Child Account', 'ASSET', parent_code='1000')
        self.assertEqual(child.code, '1010')
        self.assertEqual(child.parent, parent)

    def test_create_account_parent_not_found(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        with self.assertRaises(ValidationError):
            AccountHierarchyService.create_account('1010', 'Child', 'ASSET', parent_code='9999')

    def test_delete_account(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        from accounting.models import Account
        account = AccountFactory.create(code='9900', account_type='EXPENSE', is_system=False)
        result = AccountHierarchyService.delete_account(account.id)
        self.assertTrue(result)
        self.assertFalse(Account.objects.filter(id=account.id).exists())

    def test_delete_account_not_found(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        with self.assertRaises(ValidationError):
            AccountHierarchyService.delete_account('non-existent-id')

    def test_delete_system_account(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        system_acc = AccountFactory.create(code='9901', account_type='ASSET', is_system=True)
        with self.assertRaises(ValidationError):
            AccountHierarchyService.delete_account(system_acc.id)

    def test_delete_account_with_children(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        parent = AccountFactory.create(code='9902', account_type='ASSET', is_system=False)
        AccountFactory.create(code='9903', account_type='ASSET', parent=parent, is_system=False)
        with self.assertRaises(ValidationError):
            AccountHierarchyService.delete_account(parent.id)

    def test_delete_account_with_journal_entries(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        account = AccountFactory.create(code='9904', account_type='EXPENSE', is_system=False)
        entry = JournalEntryFactory.create(is_posted=True)
        JournalEntryLineFactory.create(entry=entry, account=account, debit=Decimal('100.00'))
        with self.assertRaises(ValidationError):
            AccountHierarchyService.delete_account(account.id)

    def test_initialize_default_chart(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        # Clear existing accounts first
        from accounting.models import Account
        Account.objects.all().delete()
        
        created = AccountHierarchyService.initialize_default_chart()
        self.assertGreater(len(created), 0)
        
        # Verify parent relationships
        assets = Account.objects.get(code='1000')
        current_assets = Account.objects.get(code='1100')
        self.assertEqual(current_assets.parent, assets)

    def test_initialize_default_chart_existing(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        from accounting.models import Account
        AccountFactory.create(code='1000', account_type='ASSET', name='Assets')
        created = AccountHierarchyService.initialize_default_chart()
        # Should not duplicate existing accounts
        self.assertEqual(Account.objects.filter(code='1000').count(), 1)

    def test_get_trial_balance(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        cash = AccountFactory.create(code='1050', account_type='ASSET')
        revenue = AccountFactory.create(code='4150', account_type='REVENUE')
        entry = JournalEntryFactory.create(is_posted=True, is_active=True)
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('1000.00'))
        JournalEntryLineFactory.create(entry=entry, account=revenue, credit=Decimal('1000.00'))
        
        AccountHierarchyService.calculate_account_balances()
        result = AccountHierarchyService.get_trial_balance()
        self.assertTrue(result['is_balanced'])
        self.assertEqual(result['total_debit'], Decimal('1000.00'))

    def test_get_balance_sheet(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        cash = AccountFactory.create(code='1060', account_type='ASSET')
        equity = AccountFactory.create(code='3150', account_type='EQUITY')
        entry = JournalEntryFactory.create(is_posted=True, is_active=True)
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('5000.00'))
        JournalEntryLineFactory.create(entry=entry, account=equity, credit=Decimal('5000.00'))
        
        AccountHierarchyService.calculate_account_balances()
        result = AccountHierarchyService.get_balance_sheet()
        self.assertTrue(result['is_balanced'])

    def test_get_income_statement(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        revenue = AccountFactory.create(code='4160', account_type='REVENUE')
        expense = AccountFactory.create(code='5160', account_type='EXPENSE')
        entry = JournalEntryFactory.create(is_posted=True, is_active=True)
        JournalEntryLineFactory.create(entry=entry, account=revenue, credit=Decimal('2000.00'))
        JournalEntryLineFactory.create(entry=entry, account=expense, debit=Decimal('1500.00'))
        
        AccountHierarchyService.calculate_account_balances()
        result = AccountHierarchyService.get_income_statement()
        self.assertEqual(result['net_income'], Decimal('500.00'))

    def test_get_section_balance(self):
        from accounting.services.account_hierarchy import AccountHierarchyService
        asset1 = AccountFactory.create(code='1070', account_type='ASSET')
        asset2 = AccountFactory.create(code='1071', account_type='ASSET')
        entry = JournalEntryFactory.create(is_posted=True, is_active=True)
        JournalEntryLineFactory.create(entry=entry, account=asset1, debit=Decimal('300.00'))
        JournalEntryLineFactory.create(entry=entry, account=asset2, debit=Decimal('200.00'))
        
        AccountHierarchyService.calculate_account_balances()
        result = AccountHierarchyService._get_section_balance('ASSET')
        self.assertEqual(result['total'], Decimal('500.00'))
        self.assertEqual(len(result['accounts']), 2)
