"""
Tests for Service Utilities not covered by other test files.

Covers:
- Account hierarchy service (tree, balances, ancestors, descendants)
- Report exporter (CSV, text, JSON exports)
"""
import uuid
from decimal import Decimal

from tests.base import BaseTestCase
from tests.factories import AccountFactory
from accounting.services.account_hierarchy import AccountHierarchyService
from accounting.services.report_exporter import ReportExporter


class AccountHierarchyServiceTests(BaseTestCase):
    """Tests for AccountHierarchyService."""

    def test_get_account_tree(self):
        parent = AccountFactory.create(code='7000', name='Test Assets')
        child = AccountFactory.create(code='7001', name='Test Cash', parent=parent)
        tree = AccountHierarchyService.get_account_tree()
        root = next((a for a in tree if a['code'] == '7000'), None)
        self.assertIsNotNone(root)
        self.assertEqual(len(root['children']), 1)
        self.assertEqual(root['children'][0]['code'], '7001')

    def test_get_accounts_by_type(self):
        AccountFactory.create(code='7002', account_type='ASSET')
        AccountFactory.create(code='7003', account_type='LIABILITY')
        assets = AccountHierarchyService.get_accounts_by_type('ASSET')
        self.assertGreaterEqual(len(assets), 1)
        self.assertTrue(all(a.account_type == 'ASSET' for a in assets))

    def test_get_leaf_accounts(self):
        parent = AccountFactory.create(code='7004', name='Test Parent')
        AccountFactory.create(code='7005', name='Test Leaf', parent=parent)
        leaves = AccountHierarchyService.get_leaf_accounts()
        leaf_codes = [a.code for a in leaves]
        self.assertIn('7005', leaf_codes)

    def test_get_children(self):
        parent = AccountFactory.create(code='7006', name='Test Parent')
        AccountFactory.create(code='7007', name='Child 1', parent=parent)
        AccountFactory.create(code='7008', name='Child 2', parent=parent)
        children = AccountHierarchyService.get_children(parent.id)
        self.assertEqual(len(children), 2)

    def test_get_children_no_children(self):
        account = AccountFactory.create(code='7009', name='Standalone')
        children = AccountHierarchyService.get_children(account.id)
        self.assertEqual(len(children), 0)

    def test_get_descendants(self):
        grandparent = AccountFactory.create(code='7010', name='Grandparent')
        parent = AccountFactory.create(code='7011', name='Parent', parent=grandparent)
        AccountFactory.create(code='7012', name='Child', parent=parent)
        descendants = AccountHierarchyService.get_descendants(grandparent.id)
        self.assertEqual(len(descendants), 2)

    def test_get_descendants_no_descendants(self):
        account = AccountFactory.create(code='7013', name='Leaf')
        descendants = AccountHierarchyService.get_descendants(account.id)
        self.assertEqual(descendants, [])

    def test_get_ancestors(self):
        grandparent = AccountFactory.create(code='7014', name='Grandparent')
        parent = AccountFactory.create(code='7015', name='Parent', parent=grandparent)
        child = AccountFactory.create(code='7016', name='Child', parent=parent)
        ancestors = AccountHierarchyService.get_ancestors(child.id)
        self.assertEqual(len(ancestors), 2)
        ancestor_codes = [a.code for a in ancestors]
        self.assertIn('7015', ancestor_codes)
        self.assertIn('7014', ancestor_codes)

    def test_get_ancestors_no_parent(self):
        account = AccountFactory.create(code='7017', name='Root')
        ancestors = AccountHierarchyService.get_ancestors(account.id)
        self.assertEqual(ancestors, [])

    def test_get_ancestors_nonexistent_account(self):
        ancestors = AccountHierarchyService.get_ancestors(uuid.uuid4())
        self.assertEqual(ancestors, [])

    def test_get_account_balance_with_children(self):
        parent = AccountFactory.create(code='7018', name='Parent')
        child = AccountFactory.create(code='7019', name='Child', parent=parent, balance=Decimal('500.00'))
        balance = AccountHierarchyService.get_account_balance(parent.id, include_children=True)
        self.assertEqual(balance, Decimal('500.00'))

    def test_get_account_balance_no_children(self):
        account = AccountFactory.create(code='7020', name='Solo')
        balance = AccountHierarchyService.get_account_balance(account.id, include_children=False)
        self.assertEqual(balance, Decimal('0.00'))

    def test_get_account_balance_nonexistent(self):
        balance = AccountHierarchyService.get_account_balance(uuid.uuid4())
        self.assertEqual(balance, Decimal('0.00'))

    def test_create_account_ok(self):
        account = AccountHierarchyService.create_account(code='7021', name='Test Account', account_type='ASSET')
        self.assertEqual(account.code, '7021')
        self.assertEqual(account.account_type, 'ASSET')

    def test_create_account_with_parent(self):
        parent = AccountFactory.create(code='7022', name='Parent Asset', account_type='ASSET')
        child = AccountHierarchyService.create_account(code='7023', name='Child Asset', account_type='ASSET', parent_code='7022')
        self.assertEqual(child.parent, parent)

    def test_create_account_parent_not_found(self):
        with self.assertRaises(Exception):
            AccountHierarchyService.create_account(code='7024', name='Orphan', account_type='ASSET', parent_code='NONEXISTENT')


class ReportExporterTests(BaseTestCase):
    """Tests for ReportExporter."""

    def test_export_trial_balance_csv(self):
        tb_data = {
            'report_type': 'trial_balance',
            'accounts': [
                {'account_code': '1000', 'account_name': 'Cash', 'account_type': 'ASSET', 'total_debit': Decimal('1000.00'), 'total_credit': Decimal('0.00'), 'net_balance': Decimal('1000.00'), 'balance_type': 'DEBIT'},
            ],
            'total_debit': Decimal('1000.00'),
            'total_credit': Decimal('0.00'),
            'is_balanced': False,
        }
        output = ReportExporter.to_csv(tb_data, 'trial_balance')
        self.assertIn('1000', output)
        self.assertIn('Cash', output)

    def test_export_trial_balance_text(self):
        tb_data = {
            'report_type': 'trial_balance',
            'accounts': [
                {'account_code': '1000', 'account_name': 'Cash', 'account_type': 'ASSET', 'total_debit': Decimal('1000.00'), 'total_credit': Decimal('0.00'), 'net_balance': Decimal('1000.00'), 'balance_type': 'DEBIT'},
            ],
            'total_debit': Decimal('1000.00'),
            'total_credit': Decimal('0.00'),
            'is_balanced': False,
        }
        output = ReportExporter.to_text(tb_data, 'trial_balance')
        self.assertIn('1000', output)
        self.assertIn('Cash', output)

    def test_export_profit_loss_csv(self):
        pl_data = {
            'report_type': 'profit_loss',
            'revenue': [{'account_code': '4000', 'account_name': 'Revenue', 'amount': Decimal('5000.00')}],
            'cogs': [],
            'expenses': [{'account_code': '6000', 'account_name': 'Expense', 'amount': Decimal('2000.00')}],
            'total_revenue': Decimal('5000.00'),
            'total_cogs': Decimal('0.00'),
            'total_expenses': Decimal('2000.00'),
            'gross_profit': Decimal('5000.00'),
            'net_income': Decimal('3000.00'),
        }
        output = ReportExporter.to_csv(pl_data, 'profit_loss')
        self.assertIn('4000', output)
        self.assertIn('Revenue', output)

    def test_export_profit_loss_text(self):
        pl_data = {
            'report_type': 'profit_loss',
            'revenue': [{'account_code': '4000', 'account_name': 'Revenue', 'amount': Decimal('5000.00')}],
            'cogs': [],
            'expenses': [],
            'total_revenue': Decimal('5000.00'),
            'total_cogs': Decimal('0.00'),
            'total_expenses': Decimal('0.00'),
            'gross_profit': Decimal('5000.00'),
            'net_income': Decimal('5000.00'),
        }
        output = ReportExporter.to_text(pl_data, 'profit_loss', company_name='Test Pharmacy')
        self.assertIn('Test Pharmacy', output)

    def test_export_balance_sheet_csv(self):
        bs_data = {
            'report_type': 'balance_sheet',
            'assets': {'sections': [{'category': 'CURRENT_ASSET', 'total': Decimal('10000.00'), 'accounts': [{'account_code': '1000', 'account_name': 'Cash', 'amount': Decimal('10000.00')}]}], 'total': Decimal('10000.00')},
            'liabilities': {'sections': [], 'total': Decimal('4000.00')},
            'equity': {'sections': [], 'total': Decimal('6000.00')},
            'total_liabilities_equity': Decimal('10000.00'),
            'is_balanced': True,
        }
        output = ReportExporter.to_csv(bs_data, 'balance_sheet')
        self.assertIn('1000', output)

    def test_export_balance_sheet_text(self):
        bs_data = {
            'report_type': 'balance_sheet',
            'assets': {'sections': [], 'total': Decimal('10000.00')},
            'liabilities': {'sections': [], 'total': Decimal('4000.00')},
            'equity': {'sections': [], 'total': Decimal('6000.00')},
            'total_liabilities_equity': Decimal('10000.00'),
            'is_balanced': True,
        }
        output = ReportExporter.to_text(bs_data, 'balance_sheet')
        self.assertIn('10,000.00', output)

    def test_export_ledger_csv(self):
        ledger_data = {
            'report_type': 'ledger',
            'account_code': '1000',
            'account_name': 'Cash',
            'entries': [
                {'entry_number': 'JE-001', 'entry_date': '2025-01-15', 'entry_type': 'SALE', 'description': 'Test sale', 'reference': 'REF-001', 'debit': Decimal('500.00'), 'credit': Decimal('0.00'), 'running_balance': Decimal('500.00')},
            ],
            'opening_balance': Decimal('0.00'),
            'closing_balance': Decimal('500.00'),
        }
        output = ReportExporter.to_csv(ledger_data, 'ledger')
        self.assertIn('JE-001', output)

    def test_export_ledger_text(self):
        ledger_data = {
            'report_type': 'ledger',
            'account_code': '1000',
            'account_name': 'Cash',
            'entries': [
                {'entry_number': 'JE-001', 'entry_date': '2025-01-15', 'entry_type': 'SALE', 'description': 'Test sale', 'reference': 'REF-001', 'debit': Decimal('500.00'), 'credit': Decimal('0.00'), 'running_balance': Decimal('500.00')},
            ],
            'opening_balance': Decimal('0.00'),
            'closing_balance': Decimal('500.00'),
        }
        output = ReportExporter.to_text(ledger_data, 'ledger')
        self.assertIn('JE-001', output)

    def test_export_cash_flow_csv(self):
        cf_data = {
            'report_type': 'cash_flow',
            'operating_activities': {'net_income': Decimal('5000.00'), 'working_capital_changes': [], 'total': Decimal('5000.00')},
            'investing_activities': {'total': Decimal('0.00')},
            'financing_activities': {'total': Decimal('0.00')},
            'net_change_in_cash': Decimal('5000.00'),
            'opening_cash_balance': Decimal('1000.00'),
            'closing_cash_balance': Decimal('6000.00'),
        }
        output = ReportExporter.to_csv(cf_data, 'cash_flow')
        self.assertIn('5,000.00', output)

    def test_export_cash_flow_text(self):
        cf_data = {
            'report_type': 'cash_flow',
            'operating_activities': {'net_income': Decimal('5000.00'), 'working_capital_changes': [], 'total': Decimal('5000.00')},
            'investing_activities': {'total': Decimal('0.00')},
            'financing_activities': {'total': Decimal('0.00')},
            'net_change_in_cash': Decimal('5000.00'),
            'opening_cash_balance': Decimal('1000.00'),
            'closing_cash_balance': Decimal('6000.00'),
        }
        output = ReportExporter.to_text(cf_data, 'cash_flow')
        self.assertIn('5,000.00', output)

    def test_export_ar_aging_csv(self):
        ar_data = {
            'report_type': 'ar_aging',
            'aging_rows': [
                {'customer_name': 'Test Customer', 'customer_code': 'C001', 'current': Decimal('1000.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'over_90': Decimal('0.00'), 'total': Decimal('1000.00')},
            ],
            'totals': {'current': Decimal('1000.00'), 'total': Decimal('1000.00')},
        }
        output = ReportExporter.to_csv(ar_data, 'ar_aging')
        self.assertIn('1,000.00', output)

    def test_export_ar_aging_text(self):
        ar_data = {
            'report_type': 'ar_aging',
            'aging_rows': [
                {'customer_name': 'Test Customer', 'customer_code': 'C001', 'current': Decimal('1000.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'over_90': Decimal('0.00'), 'total': Decimal('1000.00')},
            ],
            'totals': {'current': Decimal('1000.00'), 'total': Decimal('1000.00')},
        }
        output = ReportExporter.to_text(ar_data, 'ar_aging')
        self.assertIn('1,000.00', output)

    def test_export_ap_aging_csv(self):
        ap_data = {
            'report_type': 'ap_aging',
            'aging_rows': [
                {'supplier_name': 'Test Supplier', 'supplier_code': 'S001', 'current': Decimal('2000.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'over_90': Decimal('0.00'), 'total': Decimal('2000.00')},
            ],
            'totals': {'current': Decimal('2000.00'), 'total': Decimal('2000.00')},
        }
        output = ReportExporter.to_csv(ap_data, 'ap_aging')
        self.assertIn('2,000.00', output)

    def test_export_ap_aging_text(self):
        ap_data = {
            'report_type': 'ap_aging',
            'aging_rows': [
                {'supplier_name': 'Test Supplier', 'supplier_code': 'S001', 'current': Decimal('2000.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'over_90': Decimal('0.00'), 'total': Decimal('2000.00')},
            ],
            'totals': {'current': Decimal('2000.00'), 'total': Decimal('2000.00')},
        }
        output = ReportExporter.to_text(ap_data, 'ap_aging')
        self.assertIn('2,000.00', output)

    def test_export_generic_csv(self):
        generic_data = {
            'report_type': 'generic',
            'headers': ['Account', 'Balance'],
            'rows': [
                ['Cash', '1000.00'],
                ['Revenue', '5000.00'],
            ],
        }
        output = ReportExporter.to_csv(generic_data, 'generic')
        self.assertIn('Cash', output)

    def test_export_generic_text(self):
        generic_data = {
            'report_type': 'generic',
            'headers': ['Account', 'Balance'],
            'rows': [
                ['Cash', '1000.00'],
                ['Revenue', '5000.00'],
            ],
        }
        output = ReportExporter.to_text(generic_data, 'generic')
        self.assertIn('Pharmacy ERP', output)
        self.assertIn('generic', output)
