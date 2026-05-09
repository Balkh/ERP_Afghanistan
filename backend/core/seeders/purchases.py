"""Purchases seeder."""
import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from purchases.models import PurchaseInvoice, PurchaseItem, SupplierPayment
from inventory.models import Batch, StockMovement
from core.seeders.utils import SeederUtils


class PurchasesSeeder:
    """Seed purchase invoices with various statuses - idempotent."""

    def __init__(self, company=None):
        self.created_invoices = 0
        self.created_items = 0
        self.created_payments = 0
        self.skipped_invoices = 0
        self.skipped_items = 0
        self.skipped_payments = 0

    def seed(self, supplier_count=20, invoice_count=100):
        """Create purchase invoices with items and payments - idempotent."""

        from purchases.models import Supplier
        suppliers = list(Supplier.objects.filter(status='ACTIVE')[:supplier_count])

        if not suppliers:
            print("[!] No suppliers found. Run supplier seeder first.")
            return

        from inventory.models import Product, Warehouse
        products = list(Product.objects.filter(is_active=True))
        warehouses = list(Warehouse.objects.filter(is_active=True))

        if not products or not warehouses:
            print("[!] No products/warehouses found. Run inventory seeder first.")
            return

        self.created_invoices = 0
        self.skipped_invoices = 0
        invoices_created = []

        for i in range(invoice_count):
            invoice_number = f"PI-{i+1:04d}"

            # Idempotent: check if invoice already exists
            if PurchaseInvoice.objects.filter(invoice_number=invoice_number).exists():
                self.skipped_invoices += 1
                continue

            supplier = random.choice(suppliers)
            invoice_date = SeederUtils.random_date(180, 1)
            due_date = invoice_date + timedelta(days=supplier.payment_terms_days or 30)

            # Determine status
            days_since_invoice = (timezone.now() - invoice_date).days

            if days_since_invoice < 30:
                status = SeederUtils.pick_by_weight({
                    'RECEIVED': 0.40,
                    'PARTIAL': 0.30,
                    'PAID': 0.30,
                })
            elif days_since_invoice < 90:
                status = SeederUtils.pick_by_weight({
                    'PAID': 0.50,
                    'PARTIAL': 0.30,
                    'OVERDUE': 0.20,
                })
            else:
                status = SeederUtils.pick_by_weight({
                    'PAID': 0.30,
                    'OVERDUE': 0.50,
                    'PARTIAL': 0.20,
                })

            invoice = PurchaseInvoice.objects.create(
                invoice_number=invoice_number,
                supplier=supplier,
                order_date=invoice_date,
                invoice_date=invoice_date,
                due_date=due_date,
                status=status,
                notes=f"Purchase invoice from supplier {supplier.name}",
            )
            invoices_created.append(invoice)
            self.created_invoices += 1

        print(f"[OK] Created {self.created_invoices} purchase invoices, skipped {self.skipped_invoices} (already exists)")

        # Now create items for each invoice
        self.created_items = 0
        self.skipped_items = 0

        for invoice in invoices_created:
            num_items = random.randint(1, 5)
            total_amount = Decimal('0.00')

            for _ in range(num_items):
                product = random.choice(products)

                quantity = random.randint(10, 100)
                unit_cost = SeederUtils.random_decimal(50, 500)
                line_total = unit_cost * Decimal(quantity)

                # Check if item already exists (idempotent)
                existing_item = PurchaseItem.objects.filter(
                    invoice=invoice,
                    product=product
                ).first()

                if existing_item:
                    self.skipped_items += 1
                    continue

                item = PurchaseItem.objects.create(
                    invoice=invoice,
                    product=product,
                    batch_number=f"BATCH-{invoice.invoice_number}-{product.sku}",
                    expiry_date=invoice.invoice_date + timedelta(days=365),
                    quantity=quantity,
                    unit_price=unit_cost,
                    total=line_total,
                    received_quantity=quantity,
                )
                total_amount += line_total
                self.created_items += 1

        print(f"[OK] Created {self.created_items} purchase items, skipped {self.skipped_items}")

        # Create payments for paid/partial invoices
        self.created_payments = 0
        self.skipped_payments = 0

        for invoice in invoices_created:
            if invoice.status in ['PAID', 'PARTIAL']:
                # Check if payment already exists (idempotent)
                existing_payment = SupplierPayment.objects.filter(
                    supplier=invoice.supplier,
                    invoice=invoice
                ).first()

                if existing_payment:
                    self.skipped_payments += 1
                    continue

                items_total = sum(item.total for item in invoice.items.all())
                tax_amount = items_total * Decimal('0.10')
                total = items_total + tax_amount

                if invoice.status == 'PARTIAL':
                    payment_amount = total * Decimal(str(random.uniform(0.3, 0.7)))
                else:
                    payment_amount = total

                payment = SupplierPayment.objects.create(
                    supplier=invoice.supplier,
                    invoice=invoice,
                    payment_date=invoice.invoice_date + timedelta(days=random.randint(1, 30)),
                    amount=payment_amount,
                    payment_method=random.choice(['CASH', 'BANK_TRANSFER', 'CHEQUE']),
                    reference_number=f"PAY-{invoice.invoice_number}",
                    notes=f"Payment for {invoice.invoice_number}",
                )
                self.created_payments += 1

        print(f"[OK] Created {self.created_payments} purchase payments, skipped {self.skipped_payments}")

        if not invoices_created:
            invoices_created = list(PurchaseInvoice.objects.all()[:invoice_count])

        return {
            'invoices': invoices_created,
            'items': PurchaseItem.objects.all(),
            'payments': SupplierPayment.objects.all(),
        }
