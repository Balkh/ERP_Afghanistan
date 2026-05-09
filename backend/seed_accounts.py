import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, 'D:\\Projects\\Pharmacy_ERP\\backend')
django.setup()

from accounting.models import Account

accounts = [
    ('1100', 'Cash', 'ASSET', 'CURRENT_ASSET'),
    ('1200', 'Accounts Receivable', 'ASSET', 'CURRENT_ASSET'),
    ('1400', 'Inventory', 'ASSET', 'CURRENT_ASSET'),
    ('2100', 'Accounts Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
    ('4000', 'Sales Revenue', 'REVENUE', 'OPERATING_REVENUE'),
    ('4200', 'Sales Returns', 'REVENUE', 'OPERATING_REVENUE'),
    ('5000', 'Purchases', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
    ('5200', 'Purchase Returns', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
]

for code, name, atype, cat in accounts:
    obj, created = Account.objects.get_or_create(
        code=code,
        defaults={'name': name, 'account_type': atype, 'account_category': cat, 'is_active': True}
    )
    print(f"{'Created' if created else 'Exists'}: {code} - {name}")

print(f"\nTotal accounts: {Account.objects.count()}")