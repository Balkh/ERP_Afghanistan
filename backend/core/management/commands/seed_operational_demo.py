"""Management command to seed ERP with operational demo data."""
import time
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed ERP with operational demo data for visual validation'

    def add_arguments(self, parser):
        parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
        parser.add_argument('--clear', action='store_true', help='Clear operational data only')
        parser.add_argument('--company-id', type=int, help='Company ID for scoped execution')

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Pharmacy ERP - Operational Demo Seeder'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        company = self.get_company(options)
        self.stdout.write(f"Company: {company.name}")

        try:
            with transaction.atomic():
                self.seed_hr()
                self.seed_sales()
                self.seed_purchases()
                self.seed_journal()
                self.seed_assets()
                self.seed_budgets()
                self.validation_summary()

            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f'\nCompleted in {elapsed:.2f} seconds'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            import traceback
            traceback.print_exc()

    def get_company(self, options):
        from core.models import Company
        if options.get('company_id'):
            return Company.objects.get(id=options['company_id'])
        return Company.objects.first()

    def seed_hr(self):
        self.stdout.write('\n--- HR Structure ---')
        from hr.models import Department, Position, Employee

        depts = [('Sales', 'SAL'), ('Accounting', 'ACC'), ('Warehouse', 'WAR'), ('HR', 'HR'), ('Procurement', 'PRO')]
        created_depts = []
        for name, code in depts:
            dept, _ = Department.objects.get_or_create(name=name, defaults={'code': code})
            created_depts.append(dept)
            self.stdout.write(f'  Dept: {name}')

        created_positions = []
        for dept in created_depts:
            pos, _ = Position.objects.get_or_create(title=f'{dept.name} Manager', department=dept, defaults={'code': f'MGR-{dept.code}'})
            created_positions.append(pos)

        names = [('Ahmad', 'Ahmadi'), ('Mohammad', 'Mohammadi'), ('Ali', 'Rahimi'), ('Rahim', 'Karimi'), ('Faris', 'Safi')]
        for i, (fname, lname) in enumerate(names * 4):
            emp, created = Employee.objects.get_or_create(
                employee_number=f'EMP{str(i+1).zfill(4)}',
                defaults={
                    'first_name': fname, 'last_name': lname, 'gender': 'MALE',
                    'department': random.choice(created_depts),
                    'position': random.choice(created_positions),
                    'phone': f'070{random.randint(1000000, 9999999)}',
                    'hire_date': timezone.now().date() - timedelta(days=random.randint(30, 365)),
                    'employment_status': 'ACTIVE', 'employment_type': 'FULL_TIME',
                    'basic_salary': Decimal(str(random.randint(15000, 60000))),
                }
            )

        self.stdout.write(self.style.SUCCESS(f'  Created {Employee.objects.count()} employees'))

    def seed_sales(self):
        self.stdout.write('\n--- Sales Invoices ---')
        from sales.models import SalesInvoice, SalesItem, Customer
        from inventory.models import Product, Batch

        customers = list(Customer.objects.all()[:30])
        products = list(Product.objects.all()[:20])
        statuses = ['DRAFT', 'CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID']

        for i in range(60):
            customer = random.choice(customers)
            inv_date = (timezone.now() - timedelta(days=random.randint(1, 120))).date()
            status = random.choice(statuses)

            try:
                invoice = SalesInvoice.objects.create(
                    customer=customer,
                    invoice_number=f'SINV{str(i+1).zfill(5)}',
                    order_date=inv_date,
                    invoice_date=inv_date,
                    due_date=inv_date + timedelta(days=30),
                    status=status,
                )

                subtotal = Decimal('0')
                for _ in range(random.randint(1, 5)):
                    product = random.choice(products)
                    batch = Batch.objects.filter(product=product, remaining_quantity__gt=0).first()
                    if batch:
                        qty = random.randint(1, 20)
                        line_total = product.sale_price * qty
                        SalesItem.objects.create(
                            invoice=invoice, product=product, batch=batch,
                            quantity=qty, unit_price=product.sale_price,
                        )
                        subtotal += line_total

                invoice.subtotal = subtotal
                invoice.discount = subtotal * Decimal(str(random.choice([0, 0, 0.05, 0.10])))
                invoice.tax = (subtotal - invoice.discount) * Decimal('0.10')
                invoice.total_amount = subtotal - invoice.discount + invoice.tax
                invoice.save()
            except Exception as e:
                pass

        self.stdout.write(self.style.SUCCESS(f'  Created {SalesInvoice.objects.count()} sales invoices'))

    def seed_purchases(self):
        self.stdout.write('\n--- Purchase Invoices ---')
        from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
        from inventory.models import Product

        suppliers = list(Supplier.objects.all()[:15])
        products = list(Product.objects.all()[:20])
        statuses = ['DRAFT', 'CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID']

        for i in range(40):
            supplier = random.choice(suppliers)
            inv_date = (timezone.now() - timedelta(days=random.randint(1, 120))).date()
            status = random.choice(statuses)

            try:
                invoice = PurchaseInvoice.objects.create(
                    supplier=supplier,
                    invoice_number=f'PINV{str(i+1).zfill(5)}',
                    invoice_date=inv_date,
                    expected_date=inv_date + timedelta(days=30),
                    status=status,
                )

                subtotal = Decimal('0')
                for _ in range(random.randint(1, 8)):
                    product = random.choice(products)
                    qty = random.randint(10, 100)
                    cost = product.cost_price * Decimal('0.85')
                    line_total = cost * qty
                    PurchaseItem.objects.create(
                        invoice=invoice, product=product,
                        quantity=qty, unit_price=cost,
                        received_quantity=qty if status in ['RECEIVED', 'PARTIAL_PAID', 'PAID'] else 0,
                    )
                    subtotal += line_total

                invoice.total_amount = subtotal
                invoice.save()
            except Exception as e:
                pass

        self.stdout.write(self.style.SUCCESS(f'  Created {PurchaseInvoice.objects.count()} purchase invoices'))

    def seed_journal(self):
        self.stdout.write('\n--- Journal Entries ---')
        from accounting.models import Account, JournalEntry, JournalEntryLine

        cash_acc = Account.objects.filter(code='1000').first()
        revenue_acc = Account.objects.filter(code='4000').first()
        expense_acc = Account.objects.filter(code='5000').first()

        if not all([cash_acc, revenue_acc, expense_acc]):
            self.stdout.write(self.style.WARNING('  Missing accounts'))
            return

        for i in range(20):
            try:
                je = JournalEntry.objects.create(
                    entry_number=f'JE{str(i+1).zfill(5)}',
                    date=timezone.now().date() - timedelta(days=random.randint(1, 90)),
                    description=f'Expense {i+1}',
                    status='posted',
                )
                amount = Decimal(str(random.randint(500, 10000)))
                JournalEntryLine.objects.create(entry=je, account=expense_acc, debit=amount, credit=Decimal('0'))
                JournalEntryLine.objects.create(entry=je, account=cash_acc, debit=Decimal('0'), credit=amount)
            except:
                pass

        self.stdout.write(self.style.SUCCESS(f'  Created {JournalEntry.objects.count()} journal entries'))

    def seed_assets(self):
        self.stdout.write('\n--- Fixed Assets ---')
        from fixed_assets.models import FixedAsset, AssetCategory

        cat, _ = AssetCategory.objects.get_or_create(name='Equipment', defaults={'code': 'EQP'})
        cat2, _ = AssetCategory.objects.get_or_create(name='Vehicle', defaults={'code': 'VEH'})

        assets = [
            ('DELVAN001', 'Delivery Van', cat2, 450000, 60),
            ('OFFCOM001', 'Office Computer', cat, 45000, 36),
            ('PHAFRI001', 'Pharmacy Fridge', cat, 85000, 48),
            ('WARFOR001', 'Warehouse Forklift', cat, 250000, 60),
        ]
        for code, name, category, value, months in assets:
            try:
                FixedAsset.objects.get_or_create(
                    asset_code=code,
                    defaults={
                        'asset_name': name,
                        'category': category,
                        'purchase_date': timezone.now().date() - timedelta(days=random.randint(180, 730)),
                        'purchase_cost': Decimal(value),
                        'salvage_value': Decimal(value) * Decimal('0.1'),
                        'useful_life_months': months,
                        'depreciation_method': 'STRAIGHT_LINE',
                        'status': 'ACTIVE',
                        'current_book_value': Decimal(value),
                    }
                )
            except Exception as e:
                pass

        self.stdout.write(self.style.SUCCESS(f'  Created {FixedAsset.objects.count()} fixed assets'))

    def seed_budgets(self):
        self.stdout.write('\n--- Budgets ---')
        from budgeting.models import Budget

        year = timezone.now().year
        for dept in ['Sales', 'Warehouse', 'Procurement', 'HR']:
            try:
                Budget.objects.get_or_create(
                    department=dept, fiscal_year=year,
                    defaults={
                        'total_budget': Decimal(str(random.randint(500000, 2000000))),
                        'spent': Decimal(str(random.randint(200000, 800000))),
                        'status': 'active',
                    }
                )
            except:
                pass

        self.stdout.write(self.style.SUCCESS(f'  Created {Budget.objects.count()} budgets'))

    def validation_summary(self):
        self.stdout.write('\n--- Validation ---')
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        from accounting.models import JournalEntry
        from hr.models import Employee

        self.stdout.write(f'  Employees: {Employee.objects.count()}')
        self.stdout.write(f'  Sales: {SalesInvoice.objects.count()}')
        self.stdout.write(f'  Purchases: {PurchaseInvoice.objects.count()}')
        self.stdout.write(f'  Journal: {JournalEntry.objects.count()}')
        self.stdout.write(self.style.SUCCESS('  Done'))