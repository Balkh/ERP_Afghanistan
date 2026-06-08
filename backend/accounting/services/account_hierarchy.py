from decimal import Decimal
from typing import Optional
from django.db import models, transaction
from django.core.exceptions import ValidationError
from accounting.models import Account, JournalEntry, JournalEntryLine


class AccountHierarchyService:
    """
    Service for managing account hierarchy and chart of accounts operations.
    
    Handles:
    - Account tree building
    - Parent-child relationship validation
    - Account balance calculations
    - Hierarchical reporting
    - Default chart of accounts generation
    """

    # Standard chart of accounts structure
    DEFAULT_ACCOUNTS = [
        # Assets (1000-1999)
        {'code': '1000', 'name': 'Assets', 'type': 'ASSET', 'category': None, 'is_system': True},
        {'code': '1100', 'name': 'Current Assets', 'type': 'ASSET', 'category': 'CURRENT_ASSET', 'parent': '1000', 'is_system': True},
        {'code': '1110', 'name': 'Cash', 'type': 'ASSET', 'category': 'CURRENT_ASSET', 'parent': '1100', 'is_system': True},
        {'code': '1120', 'name': 'Bank Accounts', 'type': 'ASSET', 'category': 'CURRENT_ASSET', 'parent': '1100', 'is_system': True},
        {'code': '1200', 'name': 'Accounts Receivable', 'type': 'ASSET', 'category': 'CURRENT_ASSET', 'parent': '1100', 'is_system': True},
        {'code': '1140', 'name': 'Inventory', 'type': 'ASSET', 'category': 'CURRENT_ASSET', 'parent': '1100', 'is_system': True},
        {'code': '1200', 'name': 'Fixed Assets', 'type': 'ASSET', 'category': 'FIXED_ASSET', 'parent': '1000', 'is_system': True},
        {'code': '1210', 'name': 'Equipment', 'type': 'ASSET', 'category': 'FIXED_ASSET', 'parent': '1200', 'is_system': True},
        {'code': '1220', 'name': 'Furniture & Fixtures', 'type': 'ASSET', 'category': 'FIXED_ASSET', 'parent': '1200', 'is_system': True},
        {'code': '1230', 'name': 'Accumulated Depreciation', 'type': 'ASSET', 'category': 'FIXED_ASSET', 'parent': '1200', 'is_system': True},

        # Liabilities (2000-2999)
        {'code': '2000', 'name': 'Liabilities', 'type': 'LIABILITY', 'category': None, 'parent': None, 'is_system': True},
        {'code': '2100', 'name': 'Current Liabilities', 'type': 'LIABILITY', 'category': 'CURRENT_LIABILITY', 'parent': '2000', 'is_system': True},
        {'code': '2100', 'name': 'Accounts Payable', 'type': 'LIABILITY', 'category': 'CURRENT_LIABILITY', 'parent': '2100', 'is_system': True},
        {'code': '2120', 'name': 'Short-term Loans', 'type': 'LIABILITY', 'category': 'CURRENT_LIABILITY', 'parent': '2100', 'is_system': True},
        {'code': '2130', 'name': 'Accrued Expenses', 'type': 'LIABILITY', 'category': 'CURRENT_LIABILITY', 'parent': '2100', 'is_system': True},
        {'code': '2200', 'name': 'Long-term Liabilities', 'type': 'LIABILITY', 'category': 'LONG_TERM_LIABILITY', 'parent': '2000', 'is_system': True},
        {'code': '2210', 'name': 'Long-term Loans', 'type': 'LIABILITY', 'category': 'LONG_TERM_LIABILITY', 'parent': '2200', 'is_system': True},

        # Equity (3000-3999)
        {'code': '3000', 'name': 'Equity', 'type': 'EQUITY', 'category': None, 'parent': None, 'is_system': True},
        {'code': '3100', 'name': 'Owner Equity', 'type': 'EQUITY', 'category': 'OWNER_EQUITY', 'parent': '3000', 'is_system': True},
        {'code': '3110', 'name': 'Capital', 'type': 'EQUITY', 'category': 'OWNER_EQUITY', 'parent': '3100', 'is_system': True},
        {'code': '3120', 'name': 'Retained Earnings', 'type': 'EQUITY', 'category': 'OWNER_EQUITY', 'parent': '3100', 'is_system': True},

        # Revenue (4000-4999)
        {'code': '4000', 'name': 'Revenue', 'type': 'REVENUE', 'category': None, 'parent': None, 'is_system': True},
        {'code': '4100', 'name': 'Operating Revenue', 'type': 'REVENUE', 'category': 'OPERATING_REVENUE', 'parent': '4000', 'is_system': True},
        {'code': '4110', 'name': 'Sales Revenue', 'type': 'REVENUE', 'category': 'OPERATING_REVENUE', 'parent': '4100', 'is_system': True},
        {'code': '4120', 'name': 'Service Revenue', 'type': 'REVENUE', 'category': 'OPERATING_REVENUE', 'parent': '4100', 'is_system': True},
        {'code': '4200', 'name': 'Non-Operating Revenue', 'type': 'REVENUE', 'category': 'NON_OPERATING_REVENUE', 'parent': '4000', 'is_system': True},
        {'code': '4210', 'name': 'Interest Income', 'type': 'REVENUE', 'category': 'NON_OPERATING_REVENUE', 'parent': '4200', 'is_system': True},

        # Expenses (5000-5999)
        {'code': '5000', 'name': 'Expenses', 'type': 'EXPENSE', 'category': None, 'parent': None, 'is_system': True},
        {'code': '5100', 'name': 'Cost of Goods Sold', 'type': 'EXPENSE', 'category': 'COST_OF_GOODS_SOLD', 'parent': '5000', 'is_system': True},
        {'code': '5110', 'name': 'Purchase Cost', 'type': 'EXPENSE', 'category': 'COST_OF_GOODS_SOLD', 'parent': '5100', 'is_system': True},
        {'code': '5200', 'name': 'Operating Expenses', 'type': 'EXPENSE', 'category': 'OPERATING_EXPENSE', 'parent': '5000', 'is_system': True},
        {'code': '5210', 'name': 'Salaries & Wages', 'type': 'EXPENSE', 'category': 'OPERATING_EXPENSE', 'parent': '5200', 'is_system': True},
        {'code': '5220', 'name': 'Rent Expense', 'type': 'EXPENSE', 'category': 'OPERATING_EXPENSE', 'parent': '5200', 'is_system': True},
        {'code': '5230', 'name': 'Utilities', 'type': 'EXPENSE', 'category': 'OPERATING_EXPENSE', 'parent': '5200', 'is_system': True},
        {'code': '5240', 'name': 'Office Supplies', 'type': 'EXPENSE', 'category': 'OPERATING_EXPENSE', 'parent': '5200', 'is_system': True},
        {'code': '5300', 'name': 'Non-Operating Expenses', 'type': 'EXPENSE', 'category': 'NON_OPERATING_EXPENSE', 'parent': '5000', 'is_system': True},
        {'code': '5310', 'name': 'Interest Expense', 'type': 'EXPENSE', 'category': 'NON_OPERATING_EXPENSE', 'parent': '5300', 'is_system': True},
    ]

    @staticmethod
    def get_account_tree():
        """
        Get the complete account tree structure.
        
        Returns:
            List of account dicts with nested children
        """
        accounts = Account.objects.filter(is_active=True).order_by('code')
        return AccountHierarchyService._build_tree(accounts)

    @staticmethod
    def _build_tree(accounts, parent_id=None):
        """Build a hierarchical tree from flat account list."""
        tree = []
        for account in accounts:
            if account.parent_id == parent_id:
                node = {
                    'id': account.id,
                    'code': account.code,
                    'name': account.name,
                    'account_type': account.account_type,
                    'account_category': account.account_category,
                    'balance': account.balance,
                    'level': account.level,
                    'is_leaf': account.is_leaf,
                    'is_system': account.is_system,
                    'children': AccountHierarchyService._build_tree(accounts, account.id)
                }
                tree.append(node)
        return tree

    @staticmethod
    def get_accounts_by_type(account_type):
        """Get all accounts of a specific type."""
        return Account.objects.filter(
            account_type=account_type,
            is_active=True
        ).order_by('code')

    @staticmethod
    def get_leaf_accounts():
        """Get all leaf accounts (accounts that can have journal entries)."""
        accounts = Account.objects.filter(is_active=True)
        return [a for a in accounts if a.is_leaf]

    @staticmethod
    def get_children(account_id, include_inactive=False):
        """Get all direct children of an account."""
        qs = Account.objects.filter(parent_id=account_id)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by('code')

    @staticmethod
    def get_descendants(account_id, include_inactive=False):
        """Get all descendants (children, grandchildren, etc.) of an account."""
        descendants = []
        children = AccountHierarchyService.get_children(account_id, include_inactive)
        
        for child in children:
            descendants.append(child)
            descendants.extend(AccountHierarchyService.get_descendants(child.id, include_inactive))
        
        return descendants

    @staticmethod
    def get_ancestors(account_id):
        """Get all ancestors (parent, grandparent, etc.) of an account."""
        ancestors = []
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return ancestors
        
        current = account.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        
        return ancestors

    @staticmethod
    def get_account_balance(account_id, include_children=True):
        """
        Get account balance, optionally including all child accounts.
        
        Args:
            account_id: Account UUID
            include_children: Whether to include child account balances
            
        Returns:
            Decimal balance amount
        """
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Decimal('0.00')
        
        if include_children:
            return account.total_balance
        return account.balance

    @staticmethod
    def calculate_account_balances():
        """Recalculate all account balances from journal entries."""
        accounts = Account.objects.filter(is_active=True)
        
        for account in accounts:
            total_debit = JournalEntryLine.objects.filter(
                account=account,
                entry__is_posted=True,
                entry__is_active=True
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            
            total_credit = JournalEntryLine.objects.filter(
                account=account,
                entry__is_posted=True,
                entry__is_active=True
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
            
            # Calculate net balance based on account type
            if account.account_type in ['ASSET', 'EXPENSE']:
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit
            
            Account.objects.filter(id=account.id).update(balance=balance)

    @staticmethod
    @transaction.atomic
    def create_account(code, name, account_type, parent_code=None, **kwargs):
        """
        Create a new account with proper hierarchy validation.
        
        Args:
            code: Account code (digits only)
            name: Account name
            account_type: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
            parent_code: Optional parent account code
            **kwargs: Additional fields
            
        Returns:
            Created Account instance
        """
        parent = None
        if parent_code:
            try:
                parent = Account.objects.get(code=parent_code, is_active=True)
            except Account.DoesNotExist:
                raise ValidationError(f'Parent account with code {parent_code} not found.')
        
        account = Account(
            code=code,
            name=name,
            account_type=account_type,
            parent=parent,
            **kwargs
        )
        account.full_clean()
        account.save()
        return account

    @staticmethod
    @transaction.atomic
    def delete_account(account_id):
        """
        Delete an account if it has no children and no journal entries.
        
        Args:
            account_id: Account UUID
            
        Returns:
            True if deleted, raises ValidationError otherwise
        """
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            raise ValidationError('Account not found.')
        
        if account.is_system:
            raise ValidationError('System accounts cannot be deleted.')
        
        if account.has_children:
            raise ValidationError('Cannot delete account with child accounts.')
        
        if account.journal_lines.exists():
            raise ValidationError('Cannot delete account with journal entries.')
        
        account.delete()
        return True

    @staticmethod
    def initialize_default_chart():
        """
        Create the default chart of accounts.
        Only creates accounts that don't already exist.
        
        Returns:
            List of created accounts
        """
        created = []
        code_to_account = {}
        
        # First pass: create all accounts without parent references
        for acc_data in AccountHierarchyService.DEFAULT_ACCOUNTS:
            if not Account.objects.filter(code=acc_data['code']).exists():
                account = Account.objects.create(
                    code=acc_data['code'],
                    name=acc_data['name'],
                    account_type=acc_data['type'],
                    account_category=acc_data.get('category', ''),
                    is_system=acc_data.get('is_system', False),
                    parent=None
                )
                code_to_account[acc_data['code']] = account
                created.append(account)
            else:
                code_to_account[acc_data['code']] = Account.objects.get(code=acc_data['code'])
        
        # Second pass: set parent relationships
        for acc_data in AccountHierarchyService.DEFAULT_ACCOUNTS:
            if 'parent' in acc_data and acc_data['parent']:
                account = code_to_account.get(acc_data['code'])
                parent = code_to_account.get(acc_data['parent'])
                if account and parent and account.parent_id != parent.id:
                    account.parent = parent
                    account.save(update_fields=['parent'])
        
        return created

    @staticmethod
    def get_trial_balance():
        """
        Generate trial balance report.
        
        Returns:
            List of dicts with account info and debit/credit balances
        """
        leaf_accounts = AccountHierarchyService.get_leaf_accounts()
        trial_balance = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        for account in leaf_accounts:
            debit_lines = JournalEntryLine.objects.filter(
                account=account,
                entry__is_posted=True,
                entry__is_active=True
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            
            credit_lines = JournalEntryLine.objects.filter(
                account=account,
                entry__is_posted=True,
                entry__is_active=True
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
            
            net_debit = max(Decimal('0.00'), debit_lines - credit_lines)
            net_credit = max(Decimal('0.00'), credit_lines - debit_lines)
            
            total_debit += net_debit
            total_credit += net_credit
            
            if net_debit > 0 or net_credit > 0:
                trial_balance.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type,
                    'debit': net_debit,
                    'credit': net_credit,
                })
        
        return {
            'accounts': trial_balance,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'is_balanced': total_debit == total_credit,
        }

    @staticmethod
    def get_balance_sheet():
        """
        Generate balance sheet (Assets = Liabilities + Equity).
        
        Returns:
            Dict with assets, liabilities, equity sections
        """
        assets = AccountHierarchyService._get_section_balance('ASSET')
        liabilities = AccountHierarchyService._get_section_balance('LIABILITY')
        equity = AccountHierarchyService._get_section_balance('EQUITY')
        
        return {
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'total_assets': assets['total'],
            'total_liabilities_equity': liabilities['total'] + equity['total'],
            'is_balanced': assets['total'] == (liabilities['total'] + equity['total']),
        }

    @staticmethod
    def get_income_statement():
        """
        Generate income statement (Revenue - Expenses = Net Income).
        
        Returns:
            Dict with revenue, expenses, net income
        """
        revenue = AccountHierarchyService._get_section_balance('REVENUE')
        expenses = AccountHierarchyService._get_section_balance('EXPENSE')
        
        net_income = revenue['total'] - expenses['total']
        
        return {
            'revenue': revenue,
            'expenses': expenses,
            'net_income': net_income,
        }

    @staticmethod
    def _get_section_balance(account_type):
        """Get total balance for an account type section."""
        accounts = Account.objects.filter(
            account_type=account_type,
            is_active=True
        )
        
        total = Decimal('0.00')
        accounts_list = []
        
        for account in accounts:
            balance = account.total_balance
            if balance != 0:
                accounts_list.append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance,
                })
                total += balance
        
        return {
            'accounts': accounts_list,
            'total': total,
        }
