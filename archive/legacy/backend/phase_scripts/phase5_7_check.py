"""Phase 5.7 - System & DB check"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as c:
    c.execute("SELECT version()")
    print('DB:', c.fetchone()[0][:80])
    c.execute("SELECT current_database()")
    print('Database:', c.fetchone()[0])
    c.execute("SELECT count(*) FROM pg_database WHERE datistemplate=false")
    print('Databases:', c.fetchone()[0])

from django.contrib.auth import get_user_model
from accounting.models import Account
from payments.models import PaymentMethod, PaymentAccount
from inventory.models import Product, Batch
from sales.models import Customer, SalesInvoice
from purchases.models import Supplier, PurchaseInvoice
from returns.models import ReturnOrder

User = get_user_model()
print()
print('=== Current live data (before scale dataset) ===')
print(f'  Users: {User.objects.count()}')
print(f'  Accounts: {Account.objects.count()}')
print(f'  PaymentMethods: {PaymentMethod.objects.count()}')
print(f'  PaymentAccounts: {PaymentAccount.objects.count()}')
print(f'  Products: {Product.objects.count()}')
print(f'  Batches: {Batch.objects.count()}')
print(f'  Customers: {Customer.objects.count()}')
print(f'  SalesInvoices: {SalesInvoice.objects.count()}')
print(f'  Suppliers: {Supplier.objects.count()}')
print(f'  PurchaseInvoices: {PurchaseInvoice.objects.count()}')
print(f'  ReturnOrders: {ReturnOrder.objects.count()}')

# Check available settings
from django.conf import settings
print()
print('=== DB connection settings ===')
db = settings.DATABASES['default']
for k, v in db.items():
    if k != 'OPTIONS':
        print(f'  {k}: {v}')
print(f'  OPTIONS: {db.get("OPTIONS", {})}')
print()
print('=== Disk space ===')
import shutil
total, used, free = shutil.disk_usage('/')
print(f'  Total: {total // (2**30)} GB')
print(f'  Used: {used // (2**30)} GB')
print(f'  Free: {free // (2**30)} GB')
