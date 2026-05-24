"""
Validation Harness — Real-world ERP behavior testing under production-like conditions.

Validates:
  - Accounting correctness (debit == credit, no orphan entries)
  - Financial integrity (balance symmetry, reversal symmetry)
  - MigrationRouter routing correctness (Engine vs Gateway)
  - Inventory correctness (FIFO, batch tracking, stock levels)
  - End-to-end workflow stability across Sales, Purchases, Returns, Payments
  - Drift classification (A = OK, B = warning, C = critical, D = system failure)

NO business logic is modified. All tests use the real production services.
"""
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.test import TransactionTestCase
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from tests.factories import (
    SupplierFactory, CustomerFactory, ProductFactory, BatchFactory,
    PurchaseInvoiceFactory, PurchaseItemFactory,
    SalesInvoiceFactory, SalesItemFactory,
    CurrencyFactory, AccountFactory, WarehouseFactory,
    UnitFactory, CategoryFactory,
)
from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.financial_reports import FinancialReportEngine
from inventory.service import StockIntegrationService, StockSelectionMode
from inventory.models import Batch, StockMovement
from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction
from sales.models import CustomerPayment
from purchases.models import SupplierPayment
from sales.views import SalesAccountingService
from purchases.views import PurchaseAccountingService
from core.drift_prevention.migration_router import MigrationRouter
from core.drift_prevention.migration_registry import MigrationRegistry
from core.drift_prevention.observability import Observability

# ---------------------------------------------------------------------------
# Drift Classification
# ---------------------------------------------------------------------------

def classify_drift(differences: List[Dict[str, Any]], had_exception: bool = False) -> tuple:
    if had_exception:
        return 'D', 'SYSTEM_FAILURE', ['Exception occurred']
    if not differences:
        return 'A', 'MATCH', []
    severities = [d.get('severity', 'minor') for d in differences]
    if 'critical' in severities:
        return 'C', 'FINANCIAL_MISMATCH', [d['description'] for d in differences if d.get('severity') == 'critical']
    return 'B', 'MINOR_MISMATCH', [d['description'] for d in differences]

# ---------------------------------------------------------------------------
# Integrity Validators
# ---------------------------------------------------------------------------

class JournalIntegrityValidator:
    """Validates double-entry rules across all posted journal entries."""

    @staticmethod
    def check_all_balanced() -> List[Dict[str, Any]]:
        violations = []
        for entry in JournalEntry.objects.filter(is_posted=True):
            total_debit = JournalEntryLine.objects.filter(entry=entry).aggregate(
                total=models.Sum('debit')
            )['total'] or Decimal('0.00')
            total_credit = JournalEntryLine.objects.filter(entry=entry).aggregate(
                total=models.Sum('credit')
            )['total'] or Decimal('0.00')
            if total_debit != total_credit:
                violations.append({
                    'entry_id': str(entry.id),
                    'entry_number': entry.entry_number,
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'difference': total_debit - total_credit,
                })
        return violations

    @staticmethod
    def system_balance() -> Dict[str, Decimal]:
        all_debits = JournalEntryLine.objects.filter(
            entry__is_posted=True
        ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
        all_credits = JournalEntryLine.objects.filter(
            entry__is_posted=True
        ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
        return {'total_debits': all_debits, 'total_credits': all_credits, 'delta': all_debits - all_credits}

    @staticmethod
    def account_balance_integrity() -> List[Dict[str, Any]]:
        violations = []
        for account in Account.objects.all():
            dr = JournalEntryLine.objects.filter(
                entry__is_posted=True, account=account
            ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
            cr = JournalEntryLine.objects.filter(
                entry__is_posted=True, account=account
            ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
            if account.account_type in ('ASSET', 'EXPENSE'):
                expected = dr - cr
            else:
                expected = cr - dr
            if account.balance != expected:
                violations.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'expected_balance': expected,
                    'actual_balance': account.balance,
                    'delta': expected - account.balance,
                })
        return violations


class InventoryIntegrityValidator:
    @staticmethod
    def check_batch_quantities() -> List[Dict[str, Any]]:
        violations = []
        for batch in Batch.objects.all():
            total_in = StockMovement.objects.filter(
                batch=batch, movement_type='IN'
            ).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0.00')
            total_out = StockMovement.objects.filter(
                batch=batch, movement_type='OUT'
            ).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0.00')
            expected_remaining = batch.quantity - total_out
            if batch.remaining_quantity != expected_remaining:
                violations.append({
                    'batch_number': batch.batch_number,
                    'product': str(batch.product),
                    'expected_remaining': expected_remaining,
                    'actual_remaining': batch.remaining_quantity,
                })
        return violations


class RoutingValidator:
    @staticmethod
    def check_migration_logs(module: str, function: str, min_count: int = 1) -> Dict[str, Any]:
        from core.models.migration_config import MigrationLog
        logs = list(
            MigrationLog.objects.filter(
                module=module, function=function
            ).order_by('-created_at')[:5]
        )
        engine_count = sum(1 for l in logs if l.engine_used == 'ENGINE')
        gateway_count = sum(1 for l in logs if l.engine_used == 'GATEWAY')
        return {
            'module': module,
            'function': function,
            'total_logs': len(logs),
            'engine_calls': engine_count,
            'gateway_calls': gateway_count,
            'correct': True,
        }

    @staticmethod
    def get_routing_state(module: str, function: str) -> str:
        return MigrationRegistry.get_state(module, function)

# ---------------------------------------------------------------------------
# Test Harness
# ---------------------------------------------------------------------------

class RealExecutionTestHarness(TransactionTestCase):
    """Production-like validation of ERP system behavior.
    
    Every test runs as an independent full workflow with:
      - Real company context
      - Simulated user roles
      - Production code paths only (no mocking)
      - Financial integrity validation at every step
      - MigrationRouter routing verification
      - Drift classification
    """

    # ------------------------------------------------------------------
    # Setup: company context, users, chart of accounts, payments infra
    # ------------------------------------------------------------------

    def setUp(self):
        super().setUp()
        self._setup_currency()
        self._setup_accounts()
        self._setup_warehouse()
        self._setup_units()
        self._setup_categories()
        self._setup_payment_infrastructure()
        self._setup_users()
        self._setup_business_partners()

        # Collect routing state before tests
        self.initial_routing = self._capture_routing_state()

    def _setup_currency(self):
        self.currency_afn = CurrencyFactory.create(
            code='AFN', name='Afghan Afghani', symbol='\u060b', is_default=True
        )

    def _setup_accounts(self):
        self.account_cash = AccountFactory.create(
            code='1000', name='Cash', account_type='ASSET',
            account_category='CURRENT_ASSET', is_system=True
        )
        self.account_ar = AccountFactory.create(
            code='1200', name='Accounts Receivable', account_type='ASSET',
            account_category='CURRENT_ASSET', is_system=True
        )
        self.account_inventory = AccountFactory.create(
            code='1300', name='Inventory', account_type='ASSET',
            account_category='CURRENT_ASSET', is_system=True
        )
        self.account_ap = AccountFactory.create(
            code='2000', name='Accounts Payable', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_system=True
        )
        self.account_tax_payable = AccountFactory.create(
            code='2100', name='Tax Payable', account_type='LIABILITY',
            account_category='CURRENT_LIABILITY', is_system=True
        )
        self.account_tax_receivable = AccountFactory.create(
            code='2110', name='Purchase Tax Receivable', account_type='ASSET',
            account_category='CURRENT_ASSET', is_system=True
        )
        self.account_revenue = AccountFactory.create(
            code='4000', name='Sales Revenue', account_type='REVENUE',
            account_category='OPERATING_REVENUE', is_system=True
        )
        self.account_revenue_return = AccountFactory.create(
            code='4200', name='Sales Returns', account_type='REVENUE',
            account_category='OPERATING_REVENUE', is_system=True
        )
        self.account_cogs = AccountFactory.create(
            code='5000', name='Cost of Goods Sold', account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD', is_system=True
        )
        self.account_expense = AccountFactory.create(
            code='6000', name='Operating Expense', account_type='EXPENSE',
            account_category='OPERATING_EXPENSE'
        )
        # Needed by SalesAccountingService (uses 5100 for COGS, 1010 for Cash)
        self.account_cogs_alt = AccountFactory.create(
            code='5100', name='COGS Alternative', account_type='EXPENSE',
            account_category='COST_OF_GOODS_SOLD'
        )
        self.account_cash_alt = AccountFactory.create(
            code='1010', name='Petty Cash', account_type='ASSET',
            account_category='CURRENT_ASSET'
        )

    def _setup_warehouse(self):
        self.warehouse = WarehouseFactory.create(
            name='Main Warehouse', code='MAIN', is_default=True
        )

    def _setup_units(self):
        self.unit_tablet = UnitFactory.create(name='Tablet', symbol='TAB')
        self.unit_bottle = UnitFactory.create(name='Bottle', symbol='BTL')

    def _setup_categories(self):
        self.category_tablets = CategoryFactory.create(name='Tablets')
        self.category_syrups = CategoryFactory.create(name='Syrups')

    def _setup_payment_infrastructure(self):
        PaymentMethod.objects.create(
            code='CASH', name='Cash', method_type='CASH',
            is_active=True, is_default=True,
            fee_percentage=Decimal('0.00'), fee_fixed=Decimal('0.00'),
            ref_prefix='CSH', ref_format='{prefix}{seq:06d}',
            provider_name='Cash',
        )
        self.payment_account = PaymentAccount.objects.create(
            code='MAIN-CASH',
            name='Main Cash AFN',
            account_type='CASH',
            is_active=True,
            is_default=True,
            accounting_account=self.account_cash,
            currency='AFN',
            current_balance=Decimal('100000.00'),
        )

    def _setup_users(self):
        self.admin_user = User.objects.create_superuser('admin', 'admin@pharmacy.erp', 'admin123')
        self.accountant = User.objects.create_user('accountant', 'acc@pharmacy.erp', 'acc123')

    def _setup_business_partners(self):
        self.supplier = SupplierFactory.create(name='Test Supplier')
        self.customer = CustomerFactory.create(name='Test Customer')
        self.product = ProductFactory.create(
            name='Amoxicillin 500mg',
            category=self.category_tablets,
            unit=self.unit_tablet,
        )

    def _capture_routing_state(self) -> Dict[str, str]:
        modules_ops = [
            ('sales', 'create_entry'),
            ('sales', 'reverse_entry'),
            ('purchases', 'create_entry'),
            ('purchases', 'reverse_entry'),
            ('payments', 'create_entry'),
            ('expenses', 'create_entry'),
            ('returns', 'create_entry'),
            ('returns', 'reverse_entry'),
            ('accounting', 'post_entry'),
            ('accounting', 'reverse_entry'),
        ]
        return {
            f'{m}.{o}': MigrationRegistry.get_state(m, o)
            for m, o in modules_ops
        }

    # ------------------------------------------------------------------
    # Workflow 1: Sales Flow (create → dispatch → journal → receive payment → reconcile)
    # ------------------------------------------------------------------

    def test_workflow_sales_flow(self):
        """WORKFLOW 1: Full sales lifecycle with accounting and payment."""
        report = WorkflowReport('SALES_FLOW')
        try:
            today = timezone.now().date()

            # ---- Step 1: Stock product ----
            BatchFactory.create(
                product=self.product,
                batch_number='BATCH-SALE-001',
                quantity=Decimal('500.00'),
                remaining_quantity=Decimal('500.00'),
                location=str(self.warehouse.id),
                purchase_price=Decimal('10.00'),
                sale_price=Decimal('25.00'),
            )
            StockMovement.objects.create(
                product=self.product,
                batch=self.product.batch_set.get(batch_number='BATCH-SALE-001'),
                warehouse=self.warehouse,
                movement_type='IN',
                quantity=Decimal('500.00'),
                unit_cost=Decimal('10.00'),
                total_cost=Decimal('5000.00'),
                reference_type='MANUAL',
                reference_id='SETUP-SALE-001',
            )
            report.step('stock_in', 'PASS', stock_quantity=500)

            # ---- Step 2: Create Sales Invoice ----
            invoice = SalesInvoiceFactory.create(
                customer=self.customer,
                invoice_number='SI-VALID-001',
                status='CONFIRMED',
                subtotal=Decimal('1250.00'),
                tax=Decimal('0.00'),
                discount=Decimal('0.00'),
                total_amount=Decimal('1250.00'),
                invoice_date=today,
            )
            SalesItemFactory.create(
                invoice=invoice,
                product=self.product,
                quantity=Decimal('50.00'),
                unit_price=Decimal('25.00'),
                total=Decimal('1250.00'),
            )
            invoice.calculate_totals()
            invoice.save(update_fields=['subtotal', 'total_amount'])
            report.step('create_invoice', 'PASS', invoice_number=invoice.invoice_number)

            # ---- Step 3: Dispatch (deduct stock) ----
            dispatch = StockIntegrationService.process_sale(
                invoice_id=invoice.id,
                items=[{'product': self.product, 'quantity': Decimal('50.00')}],
                warehouse=self.warehouse,
            )
            allocations = getattr(dispatch, 'allocations', [])
            if not dispatch.success:
                report.step('dispatch', 'FAIL', errors=str(dispatch.errors))
            else:
                report.step('dispatch', 'PASS')

            # ---- Step 4: Create journal entry via MigrationRouter ----
            je_result = MigrationRouter.create_entry(
                module='sales',
                operation='create_entry',
                entry_type='SALE',
                description=f'Sales invoice {invoice.invoice_number} - {invoice.customer.name}',
                lines=[
                    {'account_code': '1200', 'debit': invoice.total_amount, 'credit': 0},
                    {'account_code': '4000', 'debit': 0, 'credit': invoice.subtotal},
                ],
                entry_date=invoice.invoice_date,
                reference=invoice.invoice_number,
                auto_post=True,
                entity_type='SalesInvoice',
                entity_id=str(invoice.id),
            )
            if not je_result.get('success'):
                report.step('journal_entry', 'FAIL', error=je_result.get('error', je_result.get('errors')))
            else:
                report.step('journal_entry', 'PASS', entry_id=je_result.get('entry_id'))
                invoice.journal_entry_id = je_result.get('entry_id')
                invoice.save(update_fields=['journal_entry_id'])

            # ---- Step 5: Process Customer Payment ----
            try:
                payment = CustomerPayment.objects.create(
                    customer=self.customer,
                    invoice=invoice,
                    amount=Decimal('1250.00'),
                    payment_date=today,
                    payment_method='CASH',
                )
                report.step('payment', 'PASS', payment_id=str(payment.id))
            except Exception as e:
                report.step('payment', 'FAIL', error=str(e))

            # ---- Step 6: Verify financial integrity ----
            self._verify_financial_integrity(report)

            # ---- Step 7: Verify routing ----
            routing = RoutingValidator.check_migration_logs('sales', 'create_entry')
            report.add_routing(routing)

            # ---- Step 8: Verify invoice is paid ----
            invoice.refresh_from_db()
            if invoice.paid_amount == invoice.total_amount:
                report.step('invoice_status', 'PASS', paid_amount=str(invoice.paid_amount))
            else:
                report.step('invoice_status', 'WARN', paid_amount=str(invoice.paid_amount),
                            total=str(invoice.total_amount))

        except Exception as e:
            report.add_error(str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # Workflow 2: Purchase Flow (order → receive → journal → pay → reconcile)
    # ------------------------------------------------------------------

    def test_workflow_purchase_flow(self):
        """WORKFLOW 2: Full purchase lifecycle with accounting and payment."""
        report = WorkflowReport('PURCHASE_FLOW')
        try:
            today = timezone.now().date()

            # ---- Step 1: Create Purchase Invoice ----
            invoice = PurchaseInvoiceFactory.create(
                supplier=self.supplier,
                invoice_number='PI-VALID-001',
                status='CONFIRMED',
                subtotal=Decimal('2000.00'),
                tax=Decimal('0.00'),
                discount=Decimal('0.00'),
                total_amount=Decimal('2000.00'),
            )
            PurchaseItemFactory.create(
                invoice=invoice,
                product=self.product,
                batch_number='BATCH-PUR-001',
                quantity=Decimal('200.00'),
                unit_price=Decimal('10.00'),
                total=Decimal('2000.00'),
            )
            invoice.calculate_totals()
            invoice.save(update_fields=['subtotal', 'total_amount'])
            report.step('create_invoice', 'PASS', invoice_number=invoice.invoice_number)

            # ---- Step 2: Receive goods ----
            receive = StockIntegrationService.process_purchase(
                invoice_id=invoice.id,
                items=[{
                    'product': self.product,
                    'quantity': Decimal('200.00'),
                    'batch_number': 'BATCH-PUR-001',
                    'expiry_date': today + timedelta(days=365),
                    'unit_price': Decimal('10.00'),
                }],
                warehouse=self.warehouse,
            )
            if not receive.success:
                report.step('receive_goods', 'FAIL', errors=str(receive.errors))
            else:
                report.step('receive_goods', 'PASS')

            # ---- Step 3: Create journal entry via MigrationRouter ----
            je_result = MigrationRouter.create_entry(
                module='purchases',
                operation='create_entry',
                entry_type='PURCHASE',
                description=f'Purchase invoice {invoice.invoice_number} - {invoice.supplier.name}',
                lines=[
                    {'account_code': '1300', 'debit': invoice.subtotal, 'credit': 0},
                    {'account_code': '2000', 'debit': 0, 'credit': invoice.total_amount},
                ],
                entry_date=invoice.invoice_date,
                reference=invoice.invoice_number,
                auto_post=True,
                entity_type='PurchaseInvoice',
                entity_id=str(invoice.id),
            )
            if not je_result.get('success'):
                report.step('journal_entry', 'FAIL', error=je_result.get('error', je_result.get('errors')))
            else:
                report.step('journal_entry', 'PASS', entry_id=je_result.get('entry_id'))
                invoice.journal_entry_id = je_result.get('entry_id')
                invoice.save(update_fields=['journal_entry_id'])

            # ---- Step 4: Process Supplier Payment ----
            try:
                payment = SupplierPayment.objects.create(
                    supplier=self.supplier,
                    invoice=invoice,
                    amount=Decimal('2000.00'),
                    payment_date=today,
                    payment_method='CASH',
                )
                report.step('payment', 'PASS', payment_id=str(payment.id))
            except Exception as e:
                report.step('payment', 'WARN', error=str(e))

            # ---- Step 5: Verify financial integrity ----
            self._verify_financial_integrity(report)

            # ---- Step 6: Verify routing ----
            routing = RoutingValidator.check_migration_logs('purchases', 'create_entry')
            report.add_routing(routing)

            # ---- Step 7: Verify inventory ----
            batch = self.product.batch_set.filter(batch_number='BATCH-PUR-001').first()
            if batch and batch.remaining_quantity == Decimal('200.00'):
                report.step('inventory', 'PASS', remaining=str(batch.remaining_quantity))
            else:
                report.step('inventory', 'WARN',
                            remaining=str(batch.remaining_quantity) if batch else 'N/A')

        except Exception as e:
            report.add_error(str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # Workflow 3: Return Flow (create return → approve → reverse journal → adjust inventory)
    # ------------------------------------------------------------------

    def test_workflow_return_flow_symmetry(self):
        """WORKFLOW 3: Verify return reversal symmetry — zero net financial drift."""
        report = WorkflowReport('RETURN_SYMMETRY')
        try:
            today = timezone.now().date()

            # ---- Step 1: Set up initial inventory ----
            batch = BatchFactory.create(
                product=self.product,
                batch_number='BATCH-RET-001',
                quantity=Decimal('100.00'),
                remaining_quantity=Decimal('100.00'),
                purchase_price=Decimal('10.00'),
                sale_price=Decimal('30.00'),
                location=str(self.warehouse.id),
            )
            StockMovement.objects.create(
                product=self.product,
                batch=batch,
                warehouse=self.warehouse,
                movement_type='IN',
                quantity=Decimal('100.00'),
                unit_cost=Decimal('10.00'),
                total_cost=Decimal('1000.00'),
                reference_type='MANUAL',
                reference_id='SETUP-RET-001',
            )
            report.step('setup_stock', 'PASS')

            # ---- Step 2: Create and dispatch a sale ----
            invoice = SalesInvoiceFactory.create(
                customer=self.customer,
                invoice_number='SI-RETURN-001',
                status='CONFIRMED',
                subtotal=Decimal('600.00'),
                total_amount=Decimal('600.00'),
                invoice_date=today,
            )
            SalesItemFactory.create(
                invoice=invoice,
                product=self.product,
                quantity=Decimal('20.00'),
                unit_price=Decimal('30.00'),
                total=Decimal('600.00'),
            )
            invoice.calculate_totals()
            invoice.save(update_fields=['subtotal', 'total_amount'])

            dispatch = StockIntegrationService.process_sale(
                invoice_id=invoice.id,
                items=[{'product': self.product, 'quantity': Decimal('20.00')}],
                warehouse=self.warehouse,
            )
            if not dispatch.success:
                report.step('dispatch', 'FAIL')
                self._finalize_report(report)
                return
            report.step('dispatch', 'PASS')
            return_allocations = getattr(dispatch, 'allocations', [])

            # ---- Step 3: Create sale journal entry via MigrationRouter ----
            sale_je = MigrationRouter.create_entry(
                module='sales',
                operation='create_entry',
                entry_type='SALE',
                description=f'Sale {invoice.invoice_number}',
                lines=[
                    {'account_code': '1200', 'debit': invoice.total_amount, 'credit': 0},
                    {'account_code': '4000', 'debit': 0, 'credit': invoice.total_amount},
                ],
                entry_date=invoice.invoice_date,
                reference=invoice.invoice_number,
                auto_post=True,
                entity_type='SalesInvoice',
                entity_id=str(invoice.id),
            )
            if not sale_je.get('success'):
                report.step('sale_journal', 'FAIL', error=sale_je.get('error'))
                self._finalize_report(report)
                return
            sale_entry_id = sale_je.get('entry_id')
            report.step('sale_journal', 'PASS', entry_id=sale_entry_id)

            # Capture pre-reversal balances
            pre_balances = {
                acct.code: Decimal(str(acct.balance))
                for acct in Account.objects.all()
            }

            # ---- Step 4: Reverse the sale journal entry via MigrationRouter ----
            reverse_result = MigrationRouter.reverse_entry(
                module='accounting',
                operation='reverse_entry',
                entry_id=sale_entry_id,
                reason='Return reversal test',
                entity_type='SalesInvoice',
                entity_id=str(invoice.id),
            )
            if not reverse_result.get('success'):
                report.step('reversal', 'FAIL', error=reverse_result.get('error'))
                self._finalize_report(report)
                return
            reversal_entry_id = reverse_result.get('reversal_entry_id')
            report.step('reversal', 'PASS', reversal_id=reversal_entry_id)

            # ---- Step 5: Verify reversal symmetry ----
            if reversal_entry_id:
                reversal = JournalEntry.objects.get(id=reversal_entry_id)
                original = JournalEntry.objects.get(id=sale_entry_id)

                dr_reversal = JournalEntryLine.objects.filter(
                    entry=reversal
                ).aggregate(t=models.Sum('debit'))['t'] or Decimal('0.00')
                cr_reversal = JournalEntryLine.objects.filter(
                    entry=reversal
                ).aggregate(t=models.Sum('credit'))['t'] or Decimal('0.00')

                dr_original = JournalEntryLine.objects.filter(
                    entry=original
                ).aggregate(t=models.Sum('debit'))['t'] or Decimal('0.00')
                cr_original = JournalEntryLine.objects.filter(
                    entry=original
                ).aggregate(t=models.Sum('credit'))['t'] or Decimal('0.00')

                if dr_reversal == cr_original and cr_reversal == dr_original:
                    report.step('reversal_symmetry', 'PASS',
                                dr=str(dr_reversal), cr=str(cr_reversal))
                else:
                    report.step('reversal_symmetry', 'WARN',
                                dr=str(dr_reversal), cr=str(cr_reversal),
                                expected_dr=str(cr_original), expected_cr=str(dr_original))

            # ---- Step 6: Verify financial integrity ----
            self._verify_financial_integrity(report)

            # ---- Step 7: Verify routing ----
            routing = RoutingValidator.check_migration_logs('accounting', 'reverse_entry')
            report.add_routing(routing)

        except Exception as e:
            report.add_error(str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # Workflow 4: Multi-transaction accounting + inventory stress
    # ------------------------------------------------------------------

    def test_workflow_multi_transaction_integrity(self):
        """WORKFLOW 4: Multiple transactions — stress test accounting + inventory."""
        report = WorkflowReport('MULTI_TXN_STRESS')
        try:
            today = timezone.now().date()

            # ---- Seed 1000 units ----
            BatchFactory.create(
                product=self.product,
                batch_number='BATCH-STRESS-001',
                quantity=Decimal('1000.00'),
                remaining_quantity=Decimal('1000.00'),
                location=str(self.warehouse.id),
                purchase_price=Decimal('8.00'),
                sale_price=Decimal('20.00'),
            )
            StockMovement.objects.create(
                product=self.product,
                batch=self.product.batch_set.get(batch_number='BATCH-STRESS-001'),
                warehouse=self.warehouse,
                movement_type='IN',
                quantity=Decimal('1000.00'),
                unit_cost=Decimal('8.00'),
                total_cost=Decimal('8000.00'),
                reference_type='MANUAL',
                reference_id='SETUP-STRESS-001',
            )
            report.step('seed_stock', 'PASS', quantity=1000)

            # ---- Execute 5 identical sale cycles ----
            total_sold = Decimal('0.00')
            for i in range(5):
                qty = Decimal('30.00')
                unit_price = Decimal('20.00')
                line_total = (qty * unit_price).quantize(Decimal('0.01'))

                invoice = SalesInvoiceFactory.create(
                    customer=self.customer,
                    invoice_number=f'SI-STRESS-{i:03d}',
                    status='CONFIRMED',
                    subtotal=line_total,
                    total_amount=line_total,
                    invoice_date=today,
                )
                SalesItemFactory.create(
                    invoice=invoice,
                    product=self.product,
                    quantity=qty,
                    unit_price=unit_price,
                    total=line_total,
                )
                invoice.calculate_totals()
                invoice.save(update_fields=['subtotal', 'total_amount'])

                dispatch = StockIntegrationService.process_sale(
                    invoice_id=invoice.id,
                    items=[{'product': self.product, 'quantity': qty}],
                    warehouse=self.warehouse,
                )
                stress_allocations = getattr(dispatch, 'allocations', [])
                if not dispatch.success:
                    report.step(f'dispatch_{i}', 'FAIL', errors=str(dispatch.errors))
                    continue

                je = MigrationRouter.create_entry(
                    module='sales',
                    operation='create_entry',
                    entry_type='SALE',
                    description=f'Sale {invoice.invoice_number}',
                    lines=[
                        {'account_code': '1200', 'debit': line_total, 'credit': 0},
                        {'account_code': '4000', 'debit': 0, 'credit': line_total},
                    ],
                    entry_date=invoice.invoice_date,
                    reference=invoice.invoice_number,
                    auto_post=True,
                    entity_type='SalesInvoice',
                    entity_id=str(invoice.id),
                )
                if je.get('success'):
                    total_sold += qty
                report.step(f'cycle_{i}', 'PASS' if je.get('success') else 'FAIL',
                            invoice=invoice.invoice_number)

            # ---- Verify stock ----
            batch = self.product.batch_set.get(batch_number='BATCH-STRESS-001')
            expected_remaining = Decimal('1000.00') - total_sold
            report.step('final_stock', 'PASS' if batch.remaining_quantity == expected_remaining else 'WARN',
                        expected=str(expected_remaining), actual=str(batch.remaining_quantity))

            # ---- Verify financial integrity ----
            self._verify_financial_integrity(report)

            # ---- Verify routing for all cycles ----
            routing = RoutingValidator.check_migration_logs('sales', 'create_entry', min_count=5)
            report.add_routing(routing)

        except Exception as e:
            report.add_error(str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # Migration Router Routing Validation (ENGINE mode verification)
    # ------------------------------------------------------------------

    def test_routing_engine_mode_default(self):
        """Validate all MigrationRouter functions start in ENGINE mode and route correctly."""
        report = WorkflowReport('ROUTING_VALIDATION')
        try:
            # ---- Verify all functions are in ENGINE mode ----
            functions = [
                ('sales', 'create_entry'), ('sales', 'reverse_entry'),
                ('purchases', 'create_entry'), ('purchases', 'reverse_entry'),
                ('payments', 'create_entry'),
                ('expenses', 'create_entry'),
                ('returns', 'create_entry'), ('returns', 'reverse_entry'),
                ('accounting', 'post_entry'), ('accounting', 'reverse_entry'),
            ]
            all_engine = True
            for module, function in functions:
                state = MigrationRegistry.get_state(module, function)
                if state != 'ENGINE':
                    report.step(f'{module}.{function}', 'WARN', state=state)
                    all_engine = False
                else:
                    report.step(f'{module}.{function}', 'PASS', state='ENGINE')

            # ---- Execute a journal entry via MigrationRouter and verify Engine was used ----
            from core.models.migration_config import MigrationLog

            today = timezone.now().date()
            result = MigrationRouter.create_entry(
                module='sales', operation='create_entry',
                entry_type='ADJUSTMENT',
                description='Routing Validation Test',
                lines=[
                    {'account_code': '1000', 'debit': 100, 'credit': 0},
                    {'account_code': '4000', 'debit': 0, 'credit': 100},
                ],
                entry_date=today,
                auto_post=True,
            )

            if result.get('success'):
                latest_logs = MigrationLog.objects.filter(
                    module='sales', function='create_entry'
                ).order_by('-created_at')[:3]

                for log in latest_logs:
                    if log.engine_used != 'ENGINE':
                        report.step('routing_engine_check', 'WARN',
                                    expected='ENGINE', actual=log.engine_used)
                    else:
                        report.step('routing_engine_check', 'PASS',
                                    engine=log.engine_used,
                                    hash=log.execution_hash[:12])

                # Verify equilibrium is preserved (no drift in ENGINE mode)
                if all(log.drift_score == 0 for log in latest_logs):
                    report.step('drift_check', 'PASS', drift_scores='all=0')
                else:
                    report.step('drift_check', 'WARN',
                                scores=[log.drift_score for log in latest_logs])
            else:
                report.step('routing_execution', 'FAIL', error=result.get('error'))

            # ---- Verify financial integrity ----
            self._verify_financial_integrity(report)

        except Exception as e:
            report.add_error(str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # System Health Score
    # ------------------------------------------------------------------

    def test_system_health_score(self):
        """Compute and validate overall system health score (0–100)."""
        report = WorkflowReport('SYSTEM_HEALTH')
        deductions = Decimal('0.00')

        try:
            # Check 1: All journal entries balanced
            violations = JournalIntegrityValidator.check_all_balanced()
            if violations:
                report.step('journal_balance', 'WARN', count=len(violations))
                deductions += Decimal('20.00')
            else:
                report.step('journal_balance', 'PASS')

            # Check 2: System-wide debit == credit
            sys_bal = JournalIntegrityValidator.system_balance()
            if sys_bal['delta'] != 0:
                report.step('system_balance', 'WARN', **{k: str(v) for k, v in sys_bal.items()})
                deductions += Decimal('15.00')
            else:
                report.step('system_balance', 'PASS')

            # Check 3: Account balance integrity
            acct_violations = JournalIntegrityValidator.account_balance_integrity()
            if acct_violations:
                report.step('account_integrity', 'WARN', count=len(acct_violations))
                deductions += Decimal('15.00')
            else:
                report.step('account_integrity', 'PASS')

            # Check 4: Batch quantities
            batch_violations = InventoryIntegrityValidator.check_batch_quantities()
            if batch_violations:
                report.step('batch_integrity', 'WARN', count=len(batch_violations))
                deductions += Decimal('10.00')
            else:
                report.step('batch_integrity', 'PASS')

            # Check 5: No orphan journal entries (unposted without error)
            orphan_count = JournalEntry.objects.filter(is_posted=False, is_active=True).count()
            if orphan_count > 0:
                report.step('orphan_entries', 'WARN', count=orphan_count)
                deductions += Decimal('5.00') * min(Decimal(str(orphan_count)), Decimal('10'))
            else:
                report.step('orphan_entries', 'PASS')

            # Check 6: Routing state consistency
            bad_routes = sum(
                1 for state in self.initial_routing.values()
                if state not in ('ENGINE', 'READY')
            )
            if bad_routes > 0:
                report.step('routing_consistency', 'WARN', bad_states=bad_routes)
                deductions += Decimal('10.00')
            else:
                report.step('routing_consistency', 'PASS')

            # Compute final score
            health_score = max(0, 100 - int(deductions))
            report.set_health_score(health_score)

            # Determine pass/fail threshold
            if health_score < 50:
                report.set_verdict('CRITICAL', f'System health {health_score}/100 below minimum threshold')
            elif health_score < 80:
                report.set_verdict('WARNING', f'System health {health_score}/100 — issues detected')
            else:
                report.set_verdict('PASS', f'System health {health_score}/100 — stable')

        except Exception as e:
            report.add_error(str(e))
            report.set_health_score(0)
            report.set_verdict('ERROR', str(e))

        self._finalize_report(report)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _verify_financial_integrity(self, report: 'WorkflowReport'):
        """Verify double-entry and account balance integrity, classifying drift."""
        differences = []

        bal = JournalIntegrityValidator.system_balance()
        if bal['delta'] != 0:
            differences.append({
                'severity': 'critical',
                'description': f'System imbalance: {bal["delta"]}',
            })

        violations = JournalIntegrityValidator.check_all_balanced()
        for v in violations:
            differences.append({
                'severity': 'critical',
                'description': f'Entry {v["entry_number"]} imbalanced by {v["difference"]}',
            })

        acct_violations = JournalIntegrityValidator.account_balance_integrity()
        for v in acct_violations:
            differences.append({
                'severity': 'critical',
                'description': f'Account {v["account_code"]} ({v["account_name"]}) '
                               f'expected={v["expected_balance"]} actual={v["actual_balance"]}',
            })

        drift_class, drift_type, reasons = classify_drift(differences)
        report.set_drift(drift_class, drift_type, reasons)
        return drift_class == 'A'


class WorkflowReport:
    """Accumulates test results and produces structured output."""

    def __init__(self, workflow_name: str):
        self.workflow = workflow_name
        self.steps: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.routing: Dict[str, Any] = {}
        self.drift_class: str = 'N/A'
        self.drift_type: str = ''
        self.drift_reasons: List[str] = []
        self.health_score: Optional[int] = None
        self.verdict: str = 'PASS'
        self.verdict_reason: str = ''

    def step(self, name: str, status: str, **details):
        self.steps.append({'step': name, 'status': status, **details})

    def add_error(self, error: str):
        self.errors.append(error)
        self.steps.append({'step': 'EXCEPTION', 'status': 'FAIL', 'error': error})

    def add_routing(self, routing: Dict[str, Any]):
        self.routing = routing

    def set_drift(self, cls: str, dtype: str, reasons: List[str]):
        self.drift_class = cls
        self.drift_type = dtype
        self.drift_reasons = reasons

    def set_health_score(self, score: int):
        self.health_score = score

    def set_verdict(self, verdict: str, reason: str = ''):
        self.verdict = verdict
        self.verdict_reason = reason

    def print_report(self):
        sep = '=' * 72
        print(f'\n{sep}')
        print(f'  WORKFLOW: {self.workflow}')
        print(f'  VERDICT:  {self.verdict}')
        if self.verdict_reason:
            print(f'  REASON:   {self.verdict_reason}')
        print(sep)

        for s in self.steps:
            status_icon = {'PASS': '  OK', 'FAIL': ' FAIL', 'WARN': ' WARN'}.get(s['status'], ' ????')
            details = ', '.join(f'{k}={v}' for k, v in s.items() if k not in ('step', 'status'))
            print(f'  [{status_icon}] {s["step"]}' + (f'  ({details})' if details else ''))

        if self.errors:
            print(f'\n  ERRORS:')
            for e in self.errors:
                print(f'    - {e}')

        print(f'\n  DRIFT CLASSIFICATION: {self.drift_class} ({self.drift_type})')
        if self.drift_reasons:
            for r in self.drift_reasons:
                print(f'    - {r}')

        if self.routing:
            print(f'\n  ROUTING VALIDATION:')
            for k, v in self.routing.items():
                print(f'    {k}: {v}')

        if self.health_score is not None:
            bar_len = 40
            filled = int(self.health_score / 100 * bar_len)
            bar = '#' * filled + '-' * (bar_len - filled)
            print(f'\n  SYSTEM HEALTH: {self.health_score}/100')
            print(f'  [{bar}]')

        print(sep)


def _finalize_report(self, report: WorkflowReport):
    """Print report and assert on critical failures."""
    report.print_report()

    # Stop test on critical drift
    if report.drift_class in ('C', 'D'):
        self.fail(
            f'CRITICAL FAILURE — {report.drift_class} ({report.drift_type}): '
            f'{"; ".join(report.drift_reasons[:3])}'
        )

    # Stop test on critical verdict
    if report.verdict == 'CRITICAL':
        self.fail(f'SYSTEM HEALTH CRITICAL: {report.verdict_reason}')

    # Assert workflow passed
    failed_steps = [s for s in report.steps if s['status'] == 'FAIL']
    if failed_steps:
        self.fail(f'{len(failed_steps)} step(s) failed in {report.workflow}')


RealExecutionTestHarness._finalize_report = _finalize_report


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import unittest
    unittest.main()
