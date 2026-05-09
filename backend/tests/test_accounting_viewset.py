"""
Tests for Accounting ViewSet report endpoints and AccountViewSet detail actions.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from tests.factories import (
    AccountFactory, JournalEntryFactory, JournalEntryLineFactory,
    CustomerFactory, SupplierFactory, SalesInvoiceFactory, PurchaseInvoiceFactory,
)


class AccountingViewSetTests(APITestCase):
    """Tests for accounting viewset report endpoints."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user = User.objects.create_user(username='testuser', password='testpass123', is_superuser=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.account = AccountFactory.create(code='9400', name='Test Asset', account_type='ASSET')

    def test_account_tree(self):
        url = '/api/accounting/accounts/tree/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accounts_by_type(self):
        url = '/api/accounting/accounts/by_type/?type=ASSET'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accounts_by_type_missing_param(self):
        url = '/api/accounting/accounts/by_type/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_leaf_accounts(self):
        url = '/api/accounting/accounts/leaf_accounts/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_account_children(self):
        child = AccountFactory.create(code='9401', name='Child', parent=self.account)
        url = f'/api/accounting/accounts/{self.account.id}/children/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_account_descendants(self):
        child = AccountFactory.create(code='9402', name='Child', parent=self.account)
        url = f'/api/accounting/accounts/{self.account.id}/descendants/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_account_ancestors(self):
        child = AccountFactory.create(code='9403', name='Child', parent=self.account)
        url = f'/api/accounting/accounts/{child.id}/ancestors/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_account_balance(self):
        url = f'/api/accounting/accounts/{self.account.id}/balance/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trial_balance(self):
        url = '/api/accounting/accounts/trial_balance/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_income_statement(self):
        start = (timezone.now().date() - timedelta(days=30)).isoformat()
        end = timezone.now().date().isoformat()
        url = f'/api/accounting/accounts/income_statement/?start_date={start}&end_date={end}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_income_statement_missing_dates(self):
        url = '/api/accounting/accounts/income_statement/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_balance_sheet(self):
        as_of = timezone.now().date().isoformat()
        url = f'/api/accounting/accounts/balance_sheet/?as_of_date={as_of}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_account_ledger(self):
        url = f'/api/accounting/accounts/ledger/?account_id={self.account.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cash_flow(self):
        start = (timezone.now().date() - timedelta(days=30)).isoformat()
        end = timezone.now().date().isoformat()
        url = f'/api/accounting/accounts/cash_flow/?start_date={start}&end_date={end}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ar_aging(self):
        url = '/api/accounting/accounts/ar_aging/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ap_aging(self):
        url = '/api/accounting/accounts/ap_aging/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_journal_entry_list(self):
        JournalEntryFactory.create()
        url = '/api/accounting/journal-entries/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_journal_entry_create(self):
        cash = AccountFactory.create(code='9410', account_type='ASSET')
        revenue = AccountFactory.create(code='9420', account_type='REVENUE')
        url = '/api/accounting/journal-entries/'
        data = {
            'entry_number': 'JE-20260501-0099-ADJ',
            'entry_date': timezone.now().date().isoformat(),
            'entry_type': 'ADJUSTMENT',
            'description': 'Test Entry',
            'writable_lines': [
                {'account': str(cash.id), 'debit': '100.00', 'credit': '0.00'},
                {'account': str(revenue.id), 'debit': '0.00', 'credit': '100.00'},
            ],
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_journal_entry_post(self):
        cash = AccountFactory.create(code='9430', account_type='ASSET')
        revenue = AccountFactory.create(code='9440', account_type='REVENUE')
        entry = JournalEntryFactory.create(is_posted=False)
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('100.00'))
        JournalEntryLineFactory.create(entry=entry, account=revenue, credit=Decimal('100.00'))
        url = f'/api/accounting/journal-entries/{entry.id}/post_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_journal_entry_unpost(self):
        entry = JournalEntryFactory.create(is_posted=True)
        url = f'/api/accounting/journal-entries/{entry.id}/unpost_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_journal_entry_reverse(self):
        cash = AccountFactory.create(code='9450', account_type='ASSET')
        revenue = AccountFactory.create(code='9460', account_type='REVENUE')
        entry = JournalEntryFactory.create(is_posted=True)
        JournalEntryLineFactory.create(entry=entry, account=cash, debit=Decimal('100.00'))
        JournalEntryLineFactory.create(entry=entry, account=revenue, credit=Decimal('100.00'))
        url = f'/api/accounting/journal-entries/{entry.id}/reverse_entry/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
