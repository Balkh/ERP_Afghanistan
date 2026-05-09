"""
Account Hierarchy Service Tests
"""

from django.test import TestCase
from accounting.models import Account
from accounting.services.account_hierarchy import AccountHierarchyService


class AccountHierarchyBasicTests(TestCase):
    """Basic AccountHierarchy tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.root = Account.objects.create(
            code='1000', name='Assets', account_type='ASSET', is_active=True
        )
        cls.child = Account.objects.create(
            code='1100', name='Cash', account_type='ASSET', parent=cls.root, is_active=True
        )
        
    def test_get_account_tree_exists(self):
        """Test get_account_tree method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_account_tree'))
        
    def test_get_account_tree_returns_list(self):
        """Test get_account_tree returns list."""
        result = AccountHierarchyService.get_account_tree()
        self.assertIsInstance(result, list)
        
    def test_get_accounts_by_type_exists(self):
        """Test get_accounts_by_type method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_accounts_by_type'))
        
    def test_get_accounts_by_type_returns_queryset(self):
        """Test get_accounts_by_type returns queryset."""
        result = AccountHierarchyService.get_accounts_by_type('ASSET')
        self.assertTrue(hasattr(result, '__iter__'))
        
    def test_get_leaf_accounts_exists(self):
        """Test get_leaf_accounts method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_leaf_accounts'))
        
    def test_get_leaf_accounts_returns_list(self):
        """Test get_leaf_accounts returns list."""
        result = AccountHierarchyService.get_leaf_accounts()
        self.assertIsInstance(result, list)
        
    def test_get_children_exists(self):
        """Test get_children method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_children'))
        
    def test_get_children_returns_queryset(self):
        """Test get_children returns queryset."""
        result = AccountHierarchyService.get_children(self.root.id)
        self.assertTrue(hasattr(result, '__iter__'))
        
    def test_get_descendants_exists(self):
        """Test get_descendants method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_descendants'))
        
    def test_get_ancestors_exists(self):
        """Test get_ancestors method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_ancestors'))
        
    def test_get_account_balance_exists(self):
        """Test get_account_balance method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_account_balance'))


class AccountHierarchyReportTests(TestCase):
    """Test report methods in AccountHierarchy."""
    
    def test_get_trial_balance_exists(self):
        """Test get_trial_balance method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_trial_balance'))
        
    def test_get_balance_sheet_exists(self):
        """Test get_balance_sheet method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_balance_sheet'))
        
    def test_get_income_statement_exists(self):
        """Test get_income_statement method exists."""
        self.assertTrue(hasattr(AccountHierarchyService, 'get_income_statement'))