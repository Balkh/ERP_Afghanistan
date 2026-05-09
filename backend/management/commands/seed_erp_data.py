"""Management command to seed ERP with realistic dummy data."""
import time
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from core.seeders import (
    CustomerSeeder,
    SupplierSeeder,
    InventorySeeder,
    SalesSeeder,
    PurchasesSeeder,
    ReturnsSeeder,
    AccountingSeeder,
    SeederUtils
)


class Command(BaseCommand):
    help = 'Seed ERP with realistic dummy data for testing and development'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--customers',
            type=int,
            default=50,
            help='Number of customers to create (default: 50)'
        )
        parser.add_argument(
            '--suppliers',
            type=int,
            default=20,
            help='Number of suppliers to create (default: 20)'
        )
        parser.add_argument(
            '--products',
            type=int,
            default=100,
            help='Number of products to create (default: 100)'
        )
        parser.add_argument(
            '--warehouses',
            type=int,
            default=10,
            help='Number of warehouses to create (default: 10)'
        )
        parser.add_argument(
            '--sales-invoices',
            type=int,
            default=200,
            help='Number of sales invoices to create (default: 200)'
        )
        parser.add_argument(
            '--purchase-invoices',
            type=int,
            default=100,
            help='Number of purchase invoices to create (default: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding (USE WITH CAUTION)'
        )
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Skip some validations for faster seeding'
        )
    
    def handle(self, *args, **options):
        start_time = time.time()
        
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('Pharmacy ERP - Dummy Data Seeder')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        
        if options['clear']:
            self.stdout.write(
                self.style.WARNING('Clearing existing data...')
            )
            self.clear_data()
        
        # Get or create company
        company = SeederUtils.get_or_create_company()
        self.stdout.write(f"Using company: {company.name}")
        
        # Seed data in order
        try:
            with transaction.atomic():
                # 1. Parties
                self.stdout.write('\nSeeding parties...')
                customer_seeder = CustomerSeeder(company)
                customers = customer_seeder.seed(options['customers'])
                
                supplier_seeder = SupplierSeeder(company)
                suppliers = supplier_seeder.seed(options['suppliers'])
                
                # 2. Inventory
                self.stdout.write('\nSeeding inventory...')
                inventory_seeder = InventorySeeder(company)
                inventory_data = inventory_seeder.seed(
                    product_count=options['products'],
                    warehouse_count=options['warehouses']
                )
                
                # 3. Sales
                self.stdout.write('\nSeeding sales...')
                sales_seeder = SalesSeeder(company)
                sales_data = sales_seeder.seed(
                    customer_count=len(customers),
                    invoice_count=options['sales_invoices']
                )
                
                # 4. Purchases
                self.stdout.write('\nSeeding purchases...')
                purchases_seeder = PurchasesSeeder(company)
                purchases_data = purchases_seeder.seed(
                    supplier_count=len(suppliers),
                    invoice_count=options['purchase_invoices']
                )
                
                # 5. Returns
                self.stdout.write('\nSeeding returns...')
                returns_seeder = ReturnsSeeder(company)
                returns_data = returns_seeder.seed(
                    sales_invoice_count=len(sales_data.get('invoices', [])),
                    purchase_invoice_count=len(purchases_data.get('invoices', []))
                )
                
                # 6. Accounting (with intentional mismatches)
                self.stdout.write('\nSeeding accounting...')
                accounting_seeder = AccountingSeeder(company)
                accounting_data = accounting_seeder.seed(
                    sales_invoice_count=len(sales_data.get('invoices', [])) // 4,
                    purchase_invoice_count=len(purchases_data.get('invoices', [])) // 4
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Seeding failed: {str(e)}')
            )
            raise
        
        # Summary
        elapsed_time = time.time() - start_time
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('SEEDING COMPLETE'))
        self.stdout.write('=' * 60)
        self.stdout.write(f"Elapsed time: {elapsed_time:.2f} seconds")
        self.stdout.write(f"Company: {company.name}")
        self.stdout.write(f"Customers: {len(customers)}")
        self.stdout.write(f"Suppliers: {len(suppliers)}")
        self.stdout.write(f"Products: {len(inventory_data.get('products', []))}")
        self.stdout.write(f"Warehouses: {len(inventory_data.get('warehouses', []))}")
        self.stdout.write(f"Batches: {len(inventory_data.get('batches', []))}")
        self.stdout.write(f"Sales Invoices: {len(sales_data.get('invoices', []))}")
        self.stdout.write(f"Purchase Invoices: {len(purchases_data.get('invoices', []))}")
        self.stdout.write(f"Sales Items: {len(sales_data.get('items', []))}")
        self.stdout.write(f"Purchase Items: {len(purchases_data.get('items', []))}")
        self.stdout.write(f"Returns: {len(returns_data.get('returns', []))}")
        self.stdout.write(f"Return Items: {len(returns_data.get('return_items', []))}")
        self.stdout.write(f"Accounting Entries: {accounting_data.get('journal_entries', 0)}")
        self.stdout.write(f"Intentional Mismatches: {accounting_data.get('intentional_mismatches', 0)}")
        self.stdout.write('=' * 60)
        self.stdout.write(
            self.style.SUCCESS('Next steps:')
        )
        self.stdout.write("1. Run tests: python manage.py test")
        self.stdout.write("2. Access admin: http://localhost:8000/admin/")
        self.stdout.write("3. API endpoint: http://localhost:8000/api/")
        self.stdout.write('=' * 60)
    
    def clear_data(self):
        """Clear existing data (use with extreme caution)."""
        from django.apps import apps
        
        # Order matters due to foreign key constraints
        models_to_clear = [
            'returns.ReconciliationEntry',
            'returns.ReturnItem',
            'returns.ReturnOrder',
            'accounting.JournalEntryLine',
            'accounting.JournalEntry',
            'sales.SalesPayment',
            'sales.SalesItem',
            'sales.SalesInvoice',
            'purchases.PurchasePayment',
            'purchases.PurchaseItem',
            'purchases.PurchaseInvoice',
            'inventory.StockMovement',
            'inventory.Batch',
            'inventory.Product',
            'inventory.Warehouse',
            'inventory.Category',
            'hr.Employee',
            'payroll.PayrollRecord',
            'payroll.PayrollCycle',
            'core.Company',
        ]
        
        for model_path in models_to_clear:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                model.objects.all().delete()
                self.stdout.write(f"  Cleared {count} {model_name}")
            except Exception as e:
                self.stdout.write(f"  Warning: Could not clear {model_path}: {e}")