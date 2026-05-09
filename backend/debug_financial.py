import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from datetime import date
from django.db.models import Sum, Q
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine

# Delete test accounts if they exist
Account.objects.filter(code__startswith='T').delete()

# Set up accounts
cash = Account.objects.create(
    code='T1000', name='TestCash', account_type='ASSET', is_active=True
)
revenue = Account.objects.create(
    code='T4000', name='TestRevenue', account_type='REVENUE', is_active=True
)

print(f"Created cash: {cash.id}, revenue: {revenue.id}")

# Create entry
lines = [
    {'account_id': str(cash.id), 'debit': '1000.00', 'credit': '0.00'},
    {'account_id': str(revenue.id), 'debit': '0.00', 'credit': '1000.00'}
]
result = JournalEngine.create_entry(
    entry_type='SALE',
    description='Sale entry',
    lines=lines
)

if not result.get('success'):
    print(f"Failed to create entry: {result}")
else:
    entry_id = result['entry_id']
    print(f"Created entry: {entry_id}")
    
    # Post entry
    post_result = JournalEngine.post_entry(entry_id)
    print(f"Post result: {post_result}")
    
    # Check entry
    entry = JournalEntry.objects.get(id=entry_id)
    print(f"Entry posted: {entry.is_posted}, active: {entry.is_active}, date: {entry.entry_date}")
    
    # Check lines directly
    entry_lines = JournalEntryLine.objects.filter(entry_id=entry_id)
    print(f"Entry lines: {entry_lines.count()}")
    for line in entry_lines:
        print(f"  {line.account.code}: dr={line.debit}, cr={line.credit}")
    
    # Try trial balance
    tb_result = FinancialReportEngine.get_trial_balance(date.today())
    print(f"Trial balance accounts: {len(tb_result['accounts'])}")
    print(f"Total debit: {tb_result['total_debit']}")