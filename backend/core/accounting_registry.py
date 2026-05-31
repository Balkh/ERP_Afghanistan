"""
Accounting Registry — single source of truth for all financial account codes.

ALL financial services MUST resolve account codes through this registry.
No module may hardcode account codes directly.

This is a regression barrier: if any service uses a different AR/AP/tax account
than the canonical definition, cross-service validation detects the drift.
"""
from typing import Dict, Optional


class _AccountingRegistry:
    """Centralized registry of canonical account codes for all financial domains.

    Usage:
        from core.accounting_registry import ACC
        ar_code = ACC['ar']  # Returns '1200'
        ap_code = ACC['ap']  # Returns '2100'
        code, name = ACC.resolve('ar')  # Returns ('1200', 'Accounts Receivable')
    """

    def __init__(self):
        self._accounts: Dict[str, Dict] = {}
        self._frozen = False

    def register(
        self,
        key: str,
        code: str,
        name: str,
        account_type: str = '',
        description: str = '',
    ):
        if self._frozen:
            raise RuntimeError(
                f"AccountingRegistry is frozen. Cannot register '{key}' after initialization."
            )
        if key in self._accounts:
            raise ValueError(f"Account key '{key}' is already registered.")
        self._accounts[key] = {
            'code': code,
            'name': name,
            'type': account_type,
            'description': description,
        }

    def freeze(self):
        """Lock registry — no further mutations allowed."""
        self._frozen = True

    def get(self, key: str) -> Optional[str]:
        """Return the account code for a given key."""
        entry = self._accounts.get(key)
        return entry['code'] if entry else None

    def resolve(self, key: str) -> tuple:
        """Return (code, name) for a given key."""
        entry = self._accounts.get(key)
        if not entry:
            raise KeyError(f"Unknown account key: '{key}'")
        return entry['code'], entry['name']

    def validate(self) -> list:
        """Cross-service consistency check. Returns list of issues found."""
        issues = []

        # These pairs MUST resolve to the SAME code across all domains
        consistency_pairs = [
            ('ar', 'accounts_receivable'),
            ('ap', 'accounts_payable'),
        ]
        for k1, k2 in consistency_pairs:
            c1 = self.get(k1)
            c2 = self.get(k2)
            if c1 and c2 and c1 != c2:
                issues.append(
                    f"INCONSISTENT: '{k1}' = '{c1}' vs '{k2}' = '{c2}'"
                )

        # Tax accounts have different semantics but must not collide
        tax_sale = self.get('tax_payable')
        tax_purchase = self.get('tax_receivable')
        if tax_sale and tax_purchase and tax_sale == tax_purchase:
            issues.append(
                f"WARNING: tax_payable ({tax_sale}) == tax_receivable ({tax_purchase})"
            )

        return issues

    def list_all(self) -> Dict[str, Dict]:
        return dict(self._accounts)

    def count(self) -> int:
        return len(self._accounts)

    def __getitem__(self, key: str) -> str:
        code = self.get(key)
        if code is None:
            raise KeyError(f"Unknown account key: '{key}'")
        return code


# Singleton — single source of truth
ACC = _AccountingRegistry()

# ---------------------------------------------------------------------------
# Default registrations (matching the 37-account Chart of Accounts)
# ---------------------------------------------------------------------------

# Assets
ACC.register('cash',                '1000', 'Main Cash',                    'ASSET')
ACC.register('cash_on_hand',        '1010', 'Cash on Hand',                'ASSET')
ACC.register('bank',                '1100', 'Bank Account',                 'ASSET')
ACC.register('accounts_receivable', '1200', 'Accounts Receivable',         'ASSET')
ACC.register('inventory',           '1300', 'Inventory',                   'ASSET')
ACC.register('tax_receivable',      '2110', 'Tax Receivable',              'ASSET')

# Liabilities
ACC.register('accounts_payable',    '2100', 'Accounts Payable',            'LIABILITY')
ACC.register('tax_payable',         '2100', 'Tax Payable',                 'LIABILITY')
ACC.register('salary_payable',      '7100', 'Salary Payable',             'LIABILITY')
ACC.register('payroll_tax_payable', '7200', 'Payroll Tax Payable',        'LIABILITY')
ACC.register('unearned_revenue',    '2200', 'Unearned Revenue',            'LIABILITY')

# Equity
ACC.register('equity',              '3000', 'Owner Equity',                'EQUITY')

# Revenue
ACC.register('revenue',             '4000', 'Sales Revenue',               'REVENUE')
ACC.register('sales_revenue',       '4100', 'Sales Revenue (4100)',        'REVENUE')
ACC.register('sales_returns',       '4200', 'Sales Returns',               'REVENUE')

# Expense
ACC.register('cogs',                '5000', 'Cost of Goods Sold',          'EXPENSE')
ACC.register('sales_cogs',          '5100', 'Cost of Goods Sold (5100)',   'EXPENSE')
ACC.register('operating_expense',   '6000', 'Operating Expenses',          'EXPENSE')
ACC.register('operating_expense_2', '6100', 'Operating Expenses (6100)',   'EXPENSE')
ACC.register('payroll_expense',     '7000', 'Payroll Expense',             'EXPENSE')
ACC.register('payroll_salary',      '7010', 'Payroll Salary Expense',      'EXPENSE')

# Convenience aliases
ACC.register('ar', '1200',  'Accounts Receivable (alias)',   'ASSET')
ACC.register('ap', '2100',  'Accounts Payable (alias)',      'LIABILITY')

# Lock the registry — no more changes
ACC.freeze()
