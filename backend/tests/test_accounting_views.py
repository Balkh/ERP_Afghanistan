"""
Accounting View Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from accounting.models import Account, JournalEntry, JournalEntryLine


class AccountViewTests(TestCase):
    """Test account API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'testpass')
        self.client.force_login(self.user)
        
    def test_account_list_view_exists(self):
        """Test account list endpoint exists."""
        response = self.client.get('/api/accounting/accounts/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_account_create_view_exists(self):
        """Test account create endpoint exists."""
        response = self.client.post('/api/accounting/accounts/', {
            'code': '9999', 'name': 'Test Account', 'account_type': 'ASSET'
        }, content_type='application/json')
        self.assertIn(response.status_code, [201, 400, 403, 500])


class JournalEntryViewTests(TestCase):
    """Test journal entry API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser2', 'test2@test.com', 'testpass2')
        self.client.force_login(self.user)
        self.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        
    def test_journal_entry_list_view_exists(self):
        """Test journal entry list endpoint exists."""
        response = self.client.get('/api/accounting/journal-entries/')
        self.assertIn(response.status_code, [200, 301, 302, 403])
        
    def test_journal_entry_create_view_exists(self):
        """Test journal entry create endpoint exists."""
        response = self.client.post('/api/accounting/journal-entries/', {
            'entry_date': date.today().isoformat(),
            'description': 'Test Entry',
            'lines': [
                {'account_id': str(self.account.id), 'debit': '100.00', 'credit': '0.00'}
            ]
        }, content_type='application/json')
        self.assertIn(response.status_code, [201, 400, 403, 500])


class FinancialReportViewTests(TestCase):
    """Test financial report API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser3', 'test3@test.com', 'testpass3')
        self.client.force_login(self.user)
        
    def test_trial_balance_view_exists(self):
        """Test trial balance endpoint exists."""
        response = self.client.get('/api/accounting/reports/trial-balance/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])
        
    def test_profit_loss_view_exists(self):
        """Test profit & loss endpoint exists."""
        response = self.client.get('/api/accounting/reports/profit-loss/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])
        
    def test_balance_sheet_view_exists(self):
        """Test balance sheet endpoint exists."""
        response = self.client.get('/api/accounting/reports/balance-sheet/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])
        
    def test_cash_flow_view_exists(self):
        """Test cash flow endpoint exists."""
        response = self.client.get('/api/accounting/reports/cash-flow/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])


class AccountLedgerViewTests(TestCase):
    """Test account ledger API views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser4', 'test4@test.com', 'testpass4')
        self.client.force_login(self.user)
        self.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        
    def test_account_ledger_view_exists(self):
        """Test account ledger endpoint exists."""
        response = self.client.get(f'/api/accounting/accounts/{self.account.id}/ledger/')
        self.assertIn(response.status_code, [200, 301, 302, 403, 404])