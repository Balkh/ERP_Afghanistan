"""Sales seeder."""
import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from sales.models import SalesInvoice, SalesItem, CustomerPayment
from inventory.models import Batch, StockMovement
from core.seeders.utils import SeederUtils


class SalesSeeder:
    """Seed sales invoices with various statuses - idempotent."""

    def __init__(self, company=None):
        self.created_invoices = 0
        self.created_items = 0
        self.created_payments = 0
        self.skipped_invoices = 0
        self.skipped_items = 0
        self.skipped_payments = 0

    def seed(self, customer_count=50, invoice_count=200):
        """Create sales invoices with items and payments - idempotent."""

        from sales.models import Customer
        customers = list(Customer.objects.filter(status='ACTIVE')[:customer_count])

        if not customers:
            print("[!] No customers found. Run customer seeder first.")
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
            invoice_number = f"INV-{i+1:05d}"

            # Idempotent: check if invoice already exists
            if SalesInvoice.objects.filter(invoice_number=invoice_number).exists():
                self.skipped_invoices += 1
                continue

            customer = random.choice(customers)
            invoice_date = SeederUtils.random_date(180, 1)
            due_date = invoice_date + timedelta(days=customer.payment_terms_days or 30)

            # Determine invoice status
            days_since_invoice = (timezone.now() - invoice_date).days

            if days_since_invoice < 30:
                status = SeederUtils.pick_by_weight({
                    'DRAFT': 0.10,
                    'CONFIRMED': 0.30,
                    'PAID': 0.40,
                    'PARTIAL': 0.20,
                })
            elif days_since_invoice < 90:
                status = SeederUtils.pick_by_weight({
                    'PAID': 0.40,
                    'PARTIAL': 0.30,
                    'OVERDUE': 0.30,
                })
            else:
                status = SeederUtils.pick_by_weight({
                    'PAID': 0.30,
                    'OVERDUE': 0.50,
                    'PARTIAL': 0.20,
                })

            invoice = SalesInvoice.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                order_date=invoice_date,
                invoice_date=invoice_date,
                due_date=due_date,
                status=status,
                notes=f"Sales invoice for customer {customer.name}",
            )
            invoices_created.append(invoice)
            self.created_invoices += 1

        print(f"[OK] Created {self.created_invoices} sales invoices, skipped {self.skipped_invoices} (already exists)")

        # Now create items for each invoice
        self.created_items = 0
        self.skipped_items = 0
        items_created = []

        for invoice in invoices_created:
            num_items = random.randint(1, 5)
            total_amount = Decimal('0.00')

            for _ in range(num_items):
                product = random.choice(products)

                # Get available batch with stock
                batch = Batch.objects.filter(
                    product=product,
                    remaining_quantity__gt=0,
                    is_active=True
                ).first()

                if not batch:
                    continue

                quantity = random.randint(1, min(int(batch.remaining_quantity), 10))
                unit_price = batch.sale_price or Decimal('100.00')
                line_total = unit_price * Decimal(quantity)

                # Check if item already exists (idempotent)
                existing_item = SalesItem.objects.filter(
                    invoice=invoice,
                    product=product,
                    batch=batch
                ).first()

                if existing_item:
                    self.skipped_items += 1
                    continue

                item = SalesItem.objects.create(
                    invoice=invoice,
                    product=product,
                    batch=batch,
                    quantity=quantity,
                    unit_price=unit_price,
                    total=line_total,
                )
                items_created.append(item)
                total_amount += line_total
                self.created_items += 1

                # Update batch remaining quantity
                batch.remaining_quantity -= quantity
                batch.save()

        print(f"[OK] Created {self.created_items} sales items, skipped {self.skipped_items}")

        # Create payments for paid/partial invoices
        self.created_payments = 0
        self.skipped_payments = 0

        for invoice in invoices_created:
            if invoice.status in ['PAID', 'PARTIAL']:
                # Check if payment already exists (idempotent)
                existing_payment = CustomerPayment.objects.filter(
                    customer=invoice.customer,
                    invoice=invoice
                ).first()

                if existing_payment:
                    self.skipped_payments += 1
                    continue

                # Calculate payment amount
                items_total = sum(item.total for item in invoice.items.all())
                tax_amount = items_total * Decimal('0.10')
                total = items_total + tax_amount

                if invoice.status == 'PARTIAL':
                    payment_amount = total * Decimal(str(random.uniform(0.3, 0.7)))
                else:
                    payment_amount = total

                payment = CustomerPayment.objects.create(
                    customer=invoice.customer,
                    invoice=invoice,
                    payment_date=invoice.invoice_date + timedelta(days=random.randint(1, 30)),
                    amount=payment_amount,
                    payment_method=random.choice(['CASH', 'BANK_TRANSFER', 'CHEQUE']),
                    reference_number=f"PAY-{invoice.invoice_number}",
                    notes=f"Payment for {invoice.invoice_number}",
                )
                self.created_payments += 1

        print(f"[OK] Created {self.created_payments} sales payments, skipped {self.skipped_payments}")

        if not invoices_created:
            invoices_created = list(SalesInvoice.objects.all()[:invoice_count])

        return {
            'invoices': invoices_created,
            'items': items_created,
            'payments': CustomerPayment.objects.all(),
        }
