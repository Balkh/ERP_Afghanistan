"""Accounting seeder for intentional mismatches and test scenarios - idempotent."""
import random
from decimal import Decimal
from django.utils import timezone
from accounting.models import Account, JournalEntry, JournalEntryLine
from sales.models import SalesInvoice
from purchases.models import PurchaseInvoice
from returns.models import ReturnOrder
from core.seeders.utils import SeederUtils


class AccountingSeeder:
    """Create accounting entries with intentional mismatches for testing - idempotent."""

    def __init__(self, company=None):
        self.created_entries = 0
        self.created_lines = 0
        self.skipped_entries = 0
        self.skipped_lines = 0
        self.intentional_mismatches = 0

    def seed(self, sales_invoice_count=50, purchase_invoice_count=30):
        """Create accounting entries including intentional mismatches - idempotent."""

        sales_invoices = list(SalesInvoice.objects.filter(
            status__in=['PAID', 'PARTIAL']
        )[:sales_invoice_count])

        purchase_invoices = list(PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PAID']
        )[:purchase_invoice_count])

        try:
            ar_account = Account.objects.filter(code='1200').first()
            sales_account = Account.objects.filter(code='4000').first()
            cash_account = Account.objects.filter(code='1100').first()
            ap_account = Account.objects.filter(code='2100').first()
            inventory_account = Account.objects.filter(code='1400').first()
            purchase_account = Account.objects.filter(code='5000').first()
            sales_return_account = Account.objects.filter(code='4200').first()
            purchase_return_account = Account.objects.filter(code='5200').first()

            if not all([ar_account, sales_account, cash_account, ap_account]):
                print("[!] Missing key accounts. Run accounting setup first.")
                return
        except Exception as e:
            print(f"[!] Error getting accounts: {e}. Run accounting setup first.")
            return

        self.created_entries = 0
        self.created_lines = 0
        self.skipped_entries = 0

        # Create journal entries for sales invoices - idempotent
        for invoice in sales_invoices:
            if invoice.status in ['PAID', 'PARTIAL']:
                # Sales journal entry
                entry_number = f"JE-SALES-{invoice.invoice_number}"
                if not JournalEntry.objects.filter(entry_number=entry_number).exists():
                    je = JournalEntry(
                        entry_number=entry_number,
                        entry_date=invoice.invoice_date,
                        entry_type='SALES',
                        description=f"Sales invoice {invoice.invoice_number}",
                        is_posted=True,
                    )
                    je.save()
                    self.created_entries += 1

                    # Line 1: Accounts Receivable
                    JournalEntryLine.objects.create(
                        entry=je,
                        account=ar_account,
                        debit=invoice.total_amount,
                        credit=Decimal('0.00'),
                        description=f"Sales to {invoice.customer.name}",
                    )
                    self.created_lines += 1

                    # Line 2: Sales Revenue
                    JournalEntryLine.objects.create(
                        entry=je,
                        account=sales_account,
                        debit=Decimal('0.00'),
                        credit=invoice.total_amount,
                        description=f"Sales revenue",
                    )
                    self.created_lines += 1
                else:
                    self.skipped_entries += 1

                # Cash receipt for PAID invoices - idempotent
                if invoice.status == 'PAID':
                    entry_number = f"JE-PAYMENT-{invoice.invoice_number}"
                    if not JournalEntry.objects.filter(entry_number=entry_number).exists():
                        je2 = JournalEntry(
                            entry_number=entry_number,
                            entry_date=invoice.invoice_date + timezone.timedelta(days=random.randint(1, 30)),
                            entry_type='RECEIPT',
                            description=f"Payment received for {invoice.invoice_number}",
                            is_posted=True,
                        )
                        je2.save()
                        self.created_entries += 1

                        JournalEntryLine.objects.create(
                            entry=je2,
                            account=cash_account,
                            debit=invoice.total_amount,
                            credit=Decimal('0.00'),
                            description=f"Cash received",
                        )
                        self.created_lines += 1

                        JournalEntryLine.objects.create(
                            entry=je2,
                            account=ar_account,
                            debit=Decimal('0.00'),
                            credit=invoice.total_amount,
                            description=f"Payment applied",
                        )
                        self.created_lines += 1
                    else:
                        self.skipped_entries += 1

        # Create journal entries for purchase invoices - idempotent
        for invoice in purchase_invoices:
            if invoice.status in ['RECEIVED', 'PAID']:
                # Purchase journal entry
                entry_number = f"JE-PURCH-{invoice.invoice_number}"
                if not JournalEntry.objects.filter(entry_number=entry_number).exists():
                    je = JournalEntry(
                        entry_number=entry_number,
                        entry_date=invoice.invoice_date,
                        entry_type='PURCHASE',
                        description=f"Purchase invoice {invoice.invoice_number}",
                        is_posted=True,
                    )
                    je.save()
                    self.created_entries += 1

                    JournalEntryLine.objects.create(
                        entry=je,
                        account=inventory_account,
                        debit=invoice.total_amount,
                        credit=Decimal('0.00'),
                        description=f"Inventory purchase",
                    )
                    self.created_lines += 1

                    JournalEntryLine.objects.create(
                        entry=je,
                        account=ap_account,
                        debit=Decimal('0.00'),
                        credit=invoice.total_amount,
                        description=f"Purchase from {invoice.supplier.name}",
                    )
                    self.created_lines += 1
                else:
                    self.skipped_entries += 1

                # Payment for PAID invoices - idempotent
                if invoice.status == 'PAID':
                    entry_number = f"JE-PAY-PURCH-{invoice.invoice_number}"
                    if not JournalEntry.objects.filter(entry_number=entry_number).exists():
                        je2 = JournalEntry(
                            entry_number=entry_number,
                            entry_date=invoice.invoice_date + timezone.timedelta(days=random.randint(1, 30)),
                            entry_type='PAYMENT',
                            description=f"Payment made for {invoice.invoice_number}",
                            is_posted=True,
                        )
                        je2.save()
                        self.created_entries += 1

                        JournalEntryLine.objects.create(
                            entry=je2,
                            account=ap_account,
                            debit=invoice.total_amount,
                            credit=Decimal('0.00'),
                            description=f"Payment made",
                        )
                        self.created_lines += 1

                        JournalEntryLine.objects.create(
                            entry=je2,
                            account=cash_account,
                            debit=Decimal('0.00'),
                            credit=invoice.total_amount,
                            description=f"Cash paid",
                        )
                        self.created_lines += 1
                    else:
                        self.skipped_entries += 1

        # Create intentional mismatches for testing anomaly detection - idempotent
        date_prefix = timezone.now().strftime('%Y%m%d')

        # 1. Unbalanced journal entry (with unique date suffix)
        entry_number = f"JE-MISMATCH-{date_prefix}"
        if not JournalEntry.objects.filter(entry_number=entry_number).exists():
            mismatch_je = JournalEntry(
                entry_number=entry_number,
                entry_date=timezone.now(),
                entry_type='MANUAL',
                description="Intentional mismatch for testing",
                is_posted=False,
            )
            mismatch_je.save()
            self.created_entries += 1

            JournalEntryLine.objects.create(
                entry=mismatch_je,
                account=ar_account,
                debit=Decimal('1000.00'),
                credit=Decimal('0.00'),
                description="Debit only",
            )
            self.created_lines += 1
            self.intentional_mismatches += 1

        # 2. Orphan journal entry (not linked to any transaction)
        entry_number = f"JE-ORPHAN-{date_prefix}"
        if not JournalEntry.objects.filter(entry_number=entry_number).exists():
            orphan_je = JournalEntry(
                entry_number=entry_number,
                entry_date=timezone.now() - timezone.timedelta(days=365),
                entry_type='MANUAL',
                description="Orphan entry for testing",
                is_posted=True,
            )
            orphan_je.save()
            self.created_entries += 1

            JournalEntryLine.objects.create(
                entry=orphan_je,
                account=sales_account,
                debit=Decimal('500.00'),
                credit=Decimal('0.00'),
                description="Orphan debit",
            )
            self.created_lines += 1

            JournalEntryLine.objects.create(
                entry=orphan_je,
                account=cash_account,
                debit=Decimal('0.00'),
                credit=Decimal('500.00'),
                description="Orphan credit",
            )
            self.created_lines += 1

        # 3. Future dated entry
        entry_number = f"JE-FUTURE-{date_prefix}"
        if not JournalEntry.objects.filter(entry_number=entry_number).exists():
            future_je = JournalEntry(
                entry_number=entry_number,
                entry_date=timezone.now() + timezone.timedelta(days=30),
                entry_type='MANUAL',
                description="Future dated entry",
                is_posted=False,
            )
            future_je.save()
            self.created_entries += 1

            JournalEntryLine.objects.create(
                entry=future_je,
                account=ar_account,
                debit=Decimal('300.00'),
                credit=Decimal('0.00'),
                description="Future debit",
            )
            self.created_lines += 1

            JournalEntryLine.objects.create(
                entry=future_je,
                account=sales_account,
                debit=Decimal('0.00'),
                credit=Decimal('300.00'),
                description="Future credit",
            )
            self.created_lines += 1

        print(f"[OK] Created {self.created_entries} journal entries, skipped {self.skipped_entries} (already exists)")
        print(f"[OK] Created {self.created_lines} journal lines")
        print(f"[OK] Created {self.intentional_mismatches} intentional mismatches for testing")

        return {
            'journal_entries': JournalEntry.objects.all(),
            'journal_lines': JournalEntryLine.objects.all(),
            'intentional_mismatches': self.intentional_mismatches,
        }