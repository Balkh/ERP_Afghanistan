"""Returns seeder - idempotent."""
import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from sales.models import SalesInvoice, SalesItem
from purchases.models import PurchaseInvoice, PurchaseItem
from returns.models import ReturnOrder, ReturnItem
from inventory.models import Batch
from core.seeders.utils import SeederUtils


class ReturnsSeeder:
    """Seed returns with various scenarios - idempotent."""

    def __init__(self, company=None):
        self.created_returns = 0
        self.created_return_items = 0
        self.skipped_returns = 0

    def seed(self, sales_invoice_count=200, purchase_invoice_count=100):
        """Create returns based on invoices - idempotent."""

        sales_invoices = list(SalesInvoice.objects.filter(
            status__in=['PAID', 'PARTIAL', 'CONFIRMED']
        )[:sales_invoice_count])

        purchase_invoices = list(PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PAID', 'CONFIRMED', 'PARTIAL']
        )[:purchase_invoice_count])

        if not sales_invoices and not purchase_invoices:
            print("[!] No invoices found. Run sales/purchase seeders first.")
            return

        print(f"Found {len(sales_invoices)} eligible sales invoices")
        print(f"Found {len(purchase_invoices)} eligible purchase invoices")

        self.created_returns = 0
        self.skipped_returns = 0

        # Sales returns (customer returns items) - idempotent
        if sales_invoices:
            sales_with_items = [i for i in sales_invoices if SalesItem.objects.filter(invoice=i).exists()]
            print(f"Sales invoices with items: {len(sales_with_items)}")

            if sales_with_items:
                num_returns = max(1, len(sales_with_items) // 2)
                selected_sales = random.sample(sales_with_items, min(num_returns, len(sales_with_items)))

                for invoice in selected_sales:
                    # Idempotent: check if return already exists for this invoice
                    return_number = f"SR-{invoice.invoice_number}"
                    if ReturnOrder.objects.filter(return_number=return_number).exists():
                        self.skipped_returns += 1
                        continue

                    try:
                        return_type = random.choices(['FULL', 'PARTIAL'], weights=[0.4, 0.6])[0]

                        return_order = ReturnOrder(
                            return_number=return_number,
                            return_type='SALE_RETURN',
                            invoice=invoice,
                            party=invoice.customer,
                            status='DRAFT',
                            reason=random.choice([
                                'Expired items', 'Damaged goods', 'Wrong item delivered',
                                'Quality issues', 'Customer changed mind', 'Over delivery'
                            ]),
                            notes=f"Return for invoice {invoice.invoice_number}",
                        )

                        return_order.save()
                        self.created_returns += 1

                        items = list(SalesItem.objects.filter(invoice=invoice))

                        num_items = min(2, len(items))
                        selected_items = random.sample(items, num_items)
                        total_amount = Decimal('0.00')

                        for item in selected_items:
                            return_qty = random.randint(1, int(item.quantity)) if return_type == 'PARTIAL' else item.quantity
                            unit_price = item.unit_price
                            line_total = Decimal(return_qty) * unit_price
                            total_amount += line_total

                            ReturnItem.objects.create(
                                return_order=return_order,
                                product=item.product,
                                batch=item.batch,
                                return_quantity=return_qty,
                                unit_price=unit_price,
                                total_price=line_total,
                            )
                            self.created_return_items += 1

                        will_approve = random.random() > 0.3
                        return_order.status = 'APPROVED' if will_approve else 'PENDING'
                        return_order.save(update_fields=['total_amount', 'status'])
                        print(f"  Created return for invoice {invoice.invoice_number}: {return_order.status}")

                    except Exception as e:
                        print(f"  Error creating sales return: {e}")

        # Purchase returns - idempotent
        if purchase_invoices:
            purchase_with_items = [i for i in purchase_invoices if PurchaseItem.objects.filter(invoice=i).exists()]
            print(f"Purchase invoices with items: {len(purchase_with_items)}")

            if purchase_with_items:
                num_returns = max(1, len(purchase_with_items) // 2)
                selected_purchase = random.sample(purchase_with_items, min(num_returns, len(purchase_with_items)))

                for invoice in selected_purchase:
                    # Idempotent: check if return already exists for this invoice
                    return_number = f"PR-{invoice.invoice_number}"
                    if ReturnOrder.objects.filter(return_number=return_number).exists():
                        self.skipped_returns += 1
                        continue

                    try:
                        return_type = random.choices(['FULL', 'PARTIAL'], weights=[0.4, 0.6])[0]

                        return_order = ReturnOrder(
                            return_number=return_number,
                            return_type='PURCHASE_RETURN',
                            purchase_invoice=invoice,
                            supplier=invoice.supplier,
                            status='DRAFT',
                            reason=random.choice([
                                'Expired items', 'Damaged goods', 'Wrong item delivered',
                                'Quality issues', 'Over delivery', 'Non-conforming'
                            ]),
                            notes=f"Return for invoice {invoice.invoice_number}",
                        )

                        return_order.save()
                        self.created_returns += 1

                        items = list(PurchaseItem.objects.filter(invoice=invoice))

                        num_items = min(2, len(items))
                        selected_items = random.sample(items, num_items)
                        total_amount = Decimal('0.00')

                        for item in selected_items:
                            return_qty = random.randint(1, int(item.quantity)) if return_type == 'PARTIAL' else item.quantity
                            unit_price = item.unit_price
                            line_total = Decimal(return_qty) * unit_price
                            total_amount += line_total

                            ReturnItem.objects.create(
                                return_order=return_order,
                                product=item.product,
                                batch_number=item.batch_number,
                                return_quantity=return_qty,
                                unit_price=unit_price,
                                total_price=line_total,
                            )
                            self.created_return_items += 1

                        will_approve = random.random() > 0.3
                        return_order.status = 'APPROVED' if will_approve else 'PENDING'
                        return_order.save(update_fields=['total_amount', 'status'])
                        print(f"  Created return for invoice {invoice.invoice_number}: {return_order.status}")

                    except Exception as e:
                        print(f"  Error creating purchase return: {e}")

        print(f"[OK] Created {self.created_returns} return orders, skipped {self.skipped_returns} (already exists)")
        print(f"[OK] Created {self.created_return_items} return items")

        return {
            'returns': ReturnOrder.objects.all(),
        }