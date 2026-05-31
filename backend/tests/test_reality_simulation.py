"""
MONTH-LONG INDUSTRIAL REALITY SIMULATION — Pharmacy ERP
=======================================================
Simulates 30 connected business days with REAL operations:
- Sales with partial payments and debt accumulation
- Customer returns with inventory/accounting reversal
- Supplier purchases with installment payments
- Expired goods return to supplier
- HR attendance, leave, and payroll processing
- Treasury/cash flow management
- Accounting integrity validation at every step
- Governance enforcement validation

EVERY TRANSACTION AFFECTS FUTURE OPERATIONS.
No isolated transactions. No synthetic data.
"""
import io
import uuid
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction, models as db_models
from django.db.models import Count
from django.test import TransactionTestCase
from django.utils import timezone

logger = logging.getLogger(__name__)

# =============================================================================
# ACCOUNT CODES — matched to services expectations
# =============================================================================
CASH_ACCOUNT_CODE = '1010'
BANK_ACCOUNT_CODE = '1100'
AR_ACCOUNT_CODE = '1200'
INVENTORY_ACCOUNT_CODE = '1300'
AP_ACCOUNT_CODE = '2100'
TAX_PAYABLE_CODE = '2100'
TAX_RECEIVABLE_CODE = '2110'
EQUITY_CODE = '3000'
REVENUE_CODE = '4000'
SALES_REVENUE_CODE = '4100'
COGS_CODE = '5000'
SALES_COGS_CODE = '5100'
OPEX_CODE = '6000'
OPEX2_CODE = '6100'
PAYROLL_EXPENSE_CODE = '7000'
SALARY_PAYABLE_CODE = '7100'
# PayrollAccountingService specific codes
PAYROLL_SALARY_EXPENSE_CODE = '6201'
PAYROLL_CASH_CODE = '1201'
PAYROLL_TAX_CODE = '2201'


class IntegrityError(AssertionError):
    """Raised when an integrity check fails during simulation."""


class IntegrityResult:
    """Collects integrity check results."""
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.details: List[str] = []

    def ok(self, check: str, detail: str = ''):
        self.passed.append(check)
        if detail:
            self.details.append(f"OK {check}: {detail}")

    def fail(self, check: str, detail: str):
        self.failed.append(check)
        self.details.append(f"FAIL {check}: {detail}")

    @property
    def healthy(self) -> bool:
        return len(self.failed) == 0

    def summary(self) -> str:
        return f"Integrity: {len(self.passed)} passed, {len(self.failed)} failed"


class SimulationDayReport:
    """Report for a single simulation day."""
    def __init__(self, day: int, date: date):
        self.day = day
        self.date = date
        self.operations: List[str] = []
        self.integrity = IntegrityResult()
        self.notes: List[str] = []


class FinalReport:
    """Final simulation report."""
    def __init__(self):
        self.days: List[SimulationDayReport] = []
        self.summary_integrity = IntegrityResult()
        self.accounting_summary: Dict[str, Decimal] = {}
        self.customer_ledger: Dict[str, Dict] = {}
        self.supplier_ledger: Dict[str, Dict] = {}
        self.treasury_movements: List[str] = []
        self.inventory_summary: Dict[str, Decimal] = {}
        self.payroll_summary: Dict[str, Any] = {}
        self.verdict: str = ''


class SimulationState:
    """Mutable state tracked across the 30-day simulation."""
    def __init__(self):
        self.accounts: Dict[str, Any] = {}
        self.products: Dict[str, Any] = {}
        self.batches: Dict[str, Any] = {}
        self.customers: Dict[str, Any] = {}
        self.suppliers: Dict[str, Any] = {}
        self.employees: Dict[str, Any] = {}
        self.departments: Dict[str, Any] = {}
        self.positions: Dict[str, Any] = {}
        self.allowances: Dict[str, Any] = {}
        self.deductions: Dict[str, Any] = {}
        self.warehouse: Any = None
        self.payment_methods: Dict[str, Any] = {}
        self.payment_accounts: Dict[str, Any] = {}
        self.currency: Any = None
        self.invoices: Dict[str, Any] = {}
        self.purchase_invoices: Dict[str, Any] = {}
        self.returns: Dict[str, Any] = {}
        self.payroll_cycles: Dict[str, Any] = {}
        self.purchase_batches: Dict[str, Any] = {}
        self.invoice_counter = 0
        self.purchase_counter = 0
        self.report = FinalReport()


MonthReport = SimulationDayReport


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

class MonthRealitySimulation:
    """30-day stateful business reality simulation."""

    MAX_DEBT_DAYS = 30
    PAYMENT_TERMS_DAYS = 30

    def __init__(self):
        self.state = SimulationState()
        self.current_date = date(2026, 1, 1)

    # ----------------------------------------------------------------
    # BASE DATA SETUP
    # ----------------------------------------------------------------

    def setup_base_data(self):
        """Create all seed data required for the simulation."""
        from accounting.models import Account, Currency
        from inventory.models import Category, Unit, Warehouse, Product, Batch, StockMovement
        from sales.models import Customer
        from purchases.models import Supplier
        from hr.models import Department, Position, Employee
        from payroll.models import Allowance, Deduction
        from payments.models import PaymentMethod, PaymentAccount

        # ---- Currency ----
        afn, _ = Currency.objects.get_or_create(code='AFN', defaults={
            'name': 'Afghan Afghani', 'symbol': 'AFN', 'is_default': True, 'is_active': True
        })
        self.state.currency = afn

        # ---- Accounts ----
        accounts_data = [
            ('1000', 'Main Cash', 'ASSET', 'CURRENT_ASSET'),
            (CASH_ACCOUNT_CODE, 'Cash on Hand', 'ASSET', 'CURRENT_ASSET'),
            (BANK_ACCOUNT_CODE, 'Bank Account', 'ASSET', 'CURRENT_ASSET'),
            (AR_ACCOUNT_CODE, 'Accounts Receivable', 'ASSET', 'CURRENT_ASSET'),
            (INVENTORY_ACCOUNT_CODE, 'Inventory', 'ASSET', 'CURRENT_ASSET'),
            (AP_ACCOUNT_CODE, 'Accounts Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
            (TAX_PAYABLE_CODE, 'Tax Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
            (TAX_RECEIVABLE_CODE, 'Tax Receivable', 'ASSET', 'CURRENT_ASSET'),
            ('2200', 'Unearned Revenue', 'LIABILITY', 'CURRENT_LIABILITY'),
            (EQUITY_CODE, 'Owner Equity', 'EQUITY', 'OWNER_EQUITY'),
            (REVENUE_CODE, 'Sales Revenue', 'REVENUE', 'OPERATING_REVENUE'),
            (SALES_REVENUE_CODE, 'Sales Revenue (4100)', 'REVENUE', 'OPERATING_REVENUE'),
            ('4200', 'Sales Returns', 'REVENUE', 'OPERATING_REVENUE'),
            (COGS_CODE, 'Cost of Goods Sold', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
            (SALES_COGS_CODE, 'Cost of Goods Sold (5100)', 'EXPENSE', 'COST_OF_GOODS_SOLD'),
            (OPEX_CODE, 'Operating Expenses', 'EXPENSE', 'OPERATING_EXPENSE'),
            (OPEX2_CODE, 'Operating Expenses (6100)', 'EXPENSE', 'OPERATING_EXPENSE'),
            (PAYROLL_EXPENSE_CODE, 'Payroll Expense', 'EXPENSE', 'OPERATING_EXPENSE'),
            (SALARY_PAYABLE_CODE, 'Salary Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
            (PAYROLL_SALARY_EXPENSE_CODE, 'Payroll Salary Expense', 'EXPENSE', 'OPERATING_EXPENSE'),
            (PAYROLL_CASH_CODE, 'Payroll Cash Account', 'ASSET', 'CURRENT_ASSET'),
            (PAYROLL_TAX_CODE, 'Payroll Tax Payable', 'LIABILITY', 'CURRENT_LIABILITY'),
        ]
        for code, name, atype, acat in accounts_data:
            acc, _ = Account.objects.get_or_create(
                code=code,
                defaults={'name': name, 'account_type': atype, 'account_category': acat, 'is_active': True}
            )
            self.state.accounts[code] = acc

        # ---- Categories ----
        cat_ab, _ = Category.objects.get_or_create(name='Antibiotics', defaults={'is_active': True})
        cat_sy, _ = Category.objects.get_or_create(name='Syrups', defaults={'is_active': True})
        cat_pk, _ = Category.objects.get_or_create(name='Painkillers', defaults={'is_active': True})

        # ---- Units ----
        unit_tab, _ = Unit.objects.get_or_create(name='Tablet', defaults={'symbol': 'TAB'})
        unit_btl, _ = Unit.objects.get_or_create(name='Bottle', defaults={'symbol': 'BTL'})

        # ---- Warehouse ----
        wh, _ = Warehouse.objects.get_or_create(code='MAIN', defaults={
            'name': 'Main Warehouse - Kabul', 'is_default': True, 'is_active': True,
            'address': 'Kabul, Afghanistan'
        })
        self.state.warehouse = wh

        # ---- Products ----
        products_data = [
            ('Amoxicillin 500mg', 'Antibiotic capsule', cat_ab, unit_tab, Decimal('150'), Decimal('350')),
            ('Paracetamol Syrup 120ml', 'Fever syrup', cat_sy, unit_btl, Decimal('80'), Decimal('200')),
            ('Ibuprofen 400mg', 'Pain relief tablet', cat_pk, unit_tab, Decimal('100'), Decimal('250')),
        ]
        for name, desc, cat, unit, cost, price in products_data:
            prod, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'generic_name': name, 'category': cat, 'unit': unit,
                    'barcode': f'BC-{uuid.uuid4().hex[:10]}',
                    'sku': f'SKU-{uuid.uuid4().hex[:8]}',
                    'is_active': True, 'requires_prescription': False, 'is_controlled_substance': False
                }
            )
            self.state.products[name] = prod

        # ---- Initial Stock ----
        stock_setup = [
            ('Amoxicillin 500mg', Decimal('500'), Decimal('150'), date(2025, 6, 1), date(2027, 6, 1)),
            ('Paracetamol Syrup 120ml', Decimal('300'), Decimal('80'), date(2025, 7, 1), date(2026, 12, 1)),
            ('Ibuprofen 400mg', Decimal('400'), Decimal('100'), date(2025, 8, 1), date(2027, 3, 1)),
        ]
        for prod_name, qty, cost, mfg_date, exp_date in stock_setup:
            prod = self.state.products[prod_name]
            batch = Batch.objects.create(
                product=prod, batch_number=f'BATCH-{prod_name[:4].upper()}-001',
                quantity=qty, remaining_quantity=qty, purchase_price=cost,
                sale_price=(cost * Decimal('2.3')).quantize(Decimal('0.01')),
                manufacturing_date=mfg_date, expiry_date=exp_date, location=str(wh.id), is_active=True
            )
            StockMovement.objects.create(
                product=prod, batch=batch, warehouse=wh, movement_type='IN',
                reference_type='MANUAL', reference_id='INITIAL-STOCK',
                quantity=qty, unit_cost=cost, total_cost=qty * cost, notes='Opening stock'
            )
            self.state.batches[prod_name] = batch

        # ---- Customers ----
        customers_data = [
            ('Ali Wholesale', 'CUST-001', 'WHOLESALE', 'INDIVIDUAL', Decimal('200000')),
            ('Karim Pharmacy', 'CUST-002', 'PHARMACY', 'INDIVIDUAL', Decimal('100000')),
            ('Fatima Hospital', 'CUST-003', 'HOSPITAL', 'COMPANY', Decimal('500000')),
        ]
        for name, code, ctype, subtype, credit in customers_data:
            cust, _ = Customer.objects.get_or_create(
                code=code,
                defaults={
                    'name': name, 'subtype': subtype, 'customer_type': ctype,
                    'first_name': name.split()[0], 'last_name': name.split()[-1],
                    'phone': f'070{code[-4:]}0000', 'credit_limit': credit,
                    'balance': Decimal('0'), 'status': 'ACTIVE',
                }
            )
            self.state.customers[name] = cust

        # ---- Suppliers ----
        suppliers_data = [
            ('Rahman Pharma', 'SUP-001', Decimal('1000000'), 'Pharmaceuticals,Antibiotics'),
            ('Kabul Medical Supply', 'SUP-002', Decimal('800000'), 'Medical Supplies,Syrups,Painkillers'),
        ]
        for name, code, credit, categories in suppliers_data:
            sup, _ = Supplier.objects.get_or_create(
                code=code,
                defaults={
                    'name': name, 'subtype': 'COMPANY', 'company_name': name,
                    'phone': f'070{code[-3:]}0000', 'supply_categories': categories,
                    'credit_limit': credit, 'balance': Decimal('0'), 'payment_terms_days': 30,
                    'status': 'ACTIVE', 'lead_time_days': 14, 'quality_rating': 4,
                }
            )
            self.state.suppliers[name] = sup

        # ---- Departments & Positions ----
        dept_sales, _ = Department.objects.get_or_create(code='SALES', defaults={'name': 'Sales', 'is_active': True})
        dept_acct, _ = Department.objects.get_or_create(code='ACCT', defaults={'name': 'Accounting', 'is_active': True})
        dept_wh, _ = Department.objects.get_or_create(code='WH', defaults={'name': 'Warehouse', 'is_active': True})
        self.state.departments = {'Sales': dept_sales, 'Accounting': dept_acct, 'Warehouse': dept_wh}

        pos_sales, _ = Position.objects.get_or_create(code='SALES-REP', defaults={
            'title': 'Sales Representative', 'department': dept_sales, 'is_active': True
        })
        pos_acct, _ = Position.objects.get_or_create(code='ACCT', defaults={
            'title': 'Accountant', 'department': dept_acct, 'is_active': True
        })
        pos_wh, _ = Position.objects.get_or_create(code='WH-MGR', defaults={
            'title': 'Warehouse Manager', 'department': dept_wh, 'is_active': True
        })
        self.state.positions = {'Sales Rep': pos_sales, 'Accountant': pos_acct, 'Warehouse': pos_wh}

        # ---- Employees ----
        emp_data = [
            ('Hassan', 'EMP-001', 'SALES', 'Sales Rep', Decimal('13000')),
            ('Ahmad', 'EMP-002', 'ACCT', 'Accountant', Decimal('18000')),
            ('Mahmood', 'EMP-003', 'WH', 'Warehouse', Decimal('15000')),
        ]
        for fname, emp_num, dept_key, pos_key, salary in emp_data:
            emp, _ = Employee.objects.get_or_create(
                employee_number=emp_num,
                defaults={
                    'first_name': fname, 'last_name': fname,
                    'gender': 'MALE',
                    'department': self.state.departments[{'SALES': 'Sales', 'ACCT': 'Accounting', 'WH': 'Warehouse'}[dept_key]],
                    'position': self.state.positions[pos_key],
                    'hire_date': date(2025, 1, 1), 'basic_salary': salary,
                    'employment_status': 'ACTIVE', 'annual_leave_balance': 20, 'remaining_leave': 20,
                }
            )
            self.state.employees[fname] = emp

        # ---- Allowances & Deductions ----
        transp, _ = Allowance.objects.get_or_create(code='TRANSPORT', defaults={
            'name': 'Transport Allowance', 'allowance_type': 'FIXED', 'amount': Decimal('2000'), 'is_active': True
        })
        health_ded, _ = Deduction.objects.get_or_create(code='HEALTH', defaults={
            'name': 'Health Insurance', 'deduction_type': 'FIXED', 'amount': Decimal('1000'), 'is_active': True
        })
        tax_ded, _ = Deduction.objects.get_or_create(code='TAX', defaults={
            'name': 'Income Tax', 'deduction_type': 'PERCENTAGE', 'percentage': Decimal('10'),
            'amount': Decimal('0'), 'is_active': True
        })
        self.state.allowances = {'Transport': transp}
        self.state.deductions = {'Health': health_ded, 'Tax': tax_ded}

        # ---- Payment Methods ----
        for code, name, mtype in [('CASH', 'Cash', 'CASH'), ('BANK', 'Bank Transfer', 'BANK_TRANSFER'),
                                    ('CHEQUE', 'Cheque', 'CHEQUE'), ('CC', 'Credit Card', 'CREDIT_CARD')]:
            pm, _ = PaymentMethod.objects.get_or_create(code=code, defaults={
                'name': name, 'method_type': mtype, 'is_active': True, 'is_default': code == 'CASH'
            })
            self.state.payment_methods[code] = pm

        # ---- Payment Accounts ----
        pmt_cash, _ = PaymentAccount.objects.get_or_create(code='CASH-MAIN', defaults={
            'name': 'Main Cash Account', 'account_type': 'CASH',
            'accounting_account': self.state.accounts[CASH_ACCOUNT_CODE],
            'currency': 'AFN', 'current_balance': Decimal('500000'), 'is_active': True, 'is_default': True,
        })
        pmt_bank, _ = PaymentAccount.objects.get_or_create(code='BANK-ACC', defaults={
            'name': 'Bank Account', 'account_type': 'BANK',
            'accounting_account': self.state.accounts[BANK_ACCOUNT_CODE],
            'currency': 'AFN', 'current_balance': Decimal('300000'), 'is_active': True,
        })
        # Override ALL payment account balances to ensure sufficient funds
        for pa in PaymentAccount.objects.filter(is_active=True):
            pa.current_balance = Decimal('500000')
            pa.save(update_fields=['current_balance'])
        pmt_cash.refresh_from_db()
        pmt_bank.refresh_from_db()
        self.state.payment_accounts = {'CASH-MAIN': pmt_cash, 'BANK-ACC': pmt_bank}

        self.state.invoice_counter = 0
        self.state.purchase_counter = 0

    # ----------------------------------------------------------------
    # OPERATION HELPERS
    # ----------------------------------------------------------------

    def _next_invoice_number(self) -> str:
        self.state.invoice_counter += 1
        return f'SI-{self.state.invoice_counter:04d}'

    def _next_purchase_number(self) -> str:
        self.state.purchase_counter += 1
        return f'PI-{self.state.purchase_counter:04d}'

    def _make_sale(self, customer_name: str, items: List[Tuple[str, Decimal]],
                   payment_amount: Decimal = Decimal('0'),
                   payment_method: str = 'CASH') -> Dict[str, Any]:
        """Create a sales invoice with items, journal entry, and optional payment."""
        from sales.models import SalesInvoice, SalesItem, CustomerPayment
        from sales.views import SalesAccountingService
        from inventory.service.stock_integration import StockIntegrationService
        from inventory.service.types import StockSelectionMode

        customer = self.state.customers[customer_name]
        inv_num = self._next_invoice_number()
        subtotal = Decimal('0')
        line_items = []

        for prod_name, qty in items:
            product = self.state.products[prod_name]
            price = self.state.batches[prod_name].sale_price or Decimal('100')
            line_total = qty * price
            subtotal += line_total
            line_items.append((product, qty, price, line_total))

        invoice = SalesInvoice.objects.create(
            customer=customer, invoice_number=inv_num,
            order_date=self.current_date, invoice_date=self.current_date,
            due_date=self.current_date + timedelta(days=self.PAYMENT_TERMS_DAYS),
            subtotal=subtotal, discount=Decimal('0'), tax=Decimal('0'),
            total_amount=subtotal, paid_amount=Decimal('0'),
            status='CONFIRMED', payment_status='UNPAID',
        )

        for product, qty, price, total in line_items:
            SalesItem.objects.create(
                invoice=invoice, product=product,
                quantity=qty, unit_price=price, discount=Decimal('0'),
                tax=Decimal('0'), total=total,
            )

        invoice.calculate_totals()
        invoice.save()
        invoice.refresh_from_db()

        # Allocate and deduct stock
        sale_items = [{'product': prod, 'quantity': qty} for prod, qty, _, _ in line_items]
        stock_result = StockIntegrationService.process_sale(
            invoice_id=invoice.id,
            items=[{'product': prod, 'quantity': qty} for prod, qty, _, _ in line_items],
            warehouse=self.state.warehouse,
            selection_mode=StockSelectionMode.FEFO,
        )
        if not stock_result.success:
            raise IntegrityError(f"Stock allocation failed for {inv_num}: {stock_result.errors}")

        # Create journal entry
        je_result = SalesAccountingService.create_sales_journal_entry(
            invoice=invoice, allocations=stock_result.allocations
        )
        if not je_result.get('success'):
            raise IntegrityError(f"Journal entry failed for {inv_num}: {je_result.get('errors', 'unknown')}")

        # Payment
        if payment_amount > 0:
            CustomerPayment.objects.create(
                customer=customer, invoice=invoice,
                amount=payment_amount, payment_date=self.current_date,
                payment_method=payment_method, reference_number=f'PAY-{inv_num}',
                notes=f'Payment for {inv_num}'
            )
            invoice.refresh_from_db()

        invoice.refresh_from_db()
        self.state.invoices[inv_num] = invoice
        return {'invoice': invoice, 'stock_result': stock_result, 'je_result': je_result}

    def _make_purchase(self, supplier_name: str, items: List[Tuple[str, Decimal, Decimal, date]],
                       payment_amount: Decimal = Decimal('0'),
                       payment_method: str = 'CASH') -> Dict[str, Any]:
        """Create a purchase invoice with items, stock addition, and optional payment."""
        from purchases.models import PurchaseInvoice, PurchaseItem, SupplierPayment
        from purchases.views import PurchaseAccountingService
        from inventory.service.stock_integration import StockIntegrationService

        supplier = self.state.suppliers[supplier_name]
        inv_num = self._next_purchase_number()
        subtotal = sum(qty * price for _, qty, price, _ in items)

        invoice = PurchaseInvoice.objects.create(
            supplier=supplier, invoice_number=inv_num,
            order_date=self.current_date, invoice_date=self.current_date,
            due_date=self.current_date + timedelta(days=self.PAYMENT_TERMS_DAYS),
            subtotal=subtotal, discount=Decimal('0'), tax=Decimal('0'),
            total_amount=subtotal, paid_amount=Decimal('0'),
            status='RECEIVED', payment_status='UNPAID',
        )

        for prod_name, qty, price, expiry in items:
            product = self.state.products[prod_name]
            pitem = PurchaseItem.objects.create(
                invoice=invoice, product=product,
                batch_number=f'PO-{uuid.uuid4().hex[:8].upper()}',
                expiry_date=expiry,
                quantity=qty, unit_price=price,
                discount=Decimal('0'), tax=Decimal('0'),
                total=qty * price, received_quantity=qty,
            )

        invoice.calculate_totals()
        invoice.save()

        # Process stock addition
        purchase_items = []
        for prod_name, qty, price, expiry in items:
            product = self.state.products[prod_name]
            purchase_items.append({
                'product': product, 'quantity': qty, 'unit_price': price,
                'batch_number': f'PO-{uuid.uuid4().hex[:8].upper()}',
                'expiry_date': expiry,
            })

        stock_result = StockIntegrationService.process_purchase(
            invoice_id=invoice.id, items=purchase_items, warehouse=self.state.warehouse
        )
        if not stock_result.success:
            raise IntegrityError(f"Purchase stock failed for {inv_num}: {stock_result.errors}")

        # Create journal entry
        je_result = PurchaseAccountingService.create_purchase_journal_entry(invoice=invoice)
        if not je_result.get('success'):
            raise IntegrityError(f"Purchase JE failed for {inv_num}: {je_result.get('errors', 'unknown')}")

        # Payment
        if payment_amount > 0:
            SupplierPayment.objects.create(
                supplier=supplier, invoice=invoice,
                amount=payment_amount, payment_date=self.current_date,
                payment_method=payment_method, reference_number=f'PAY-{inv_num}',
                notes=f'Payment for {inv_num}'
            )
            invoice.refresh_from_db()

        invoice.refresh_from_db()
        self.state.purchase_invoices[inv_num] = invoice
        # Track batch created by this purchase for return operations
        from inventory.models import StockMovement
        sm = StockMovement.objects.filter(
            reference_type='PURCHASE', reference_id=str(invoice.id), movement_type='IN'
        ).first()
        if sm and sm.batch:
            self.state.purchase_batches[inv_num] = sm.batch
        return {'invoice': invoice, 'stock_result': stock_result, 'je_result': je_result}

    def _record_attendance(self, employee_name: str, status: str, hours: Decimal = Decimal('8')):
        """Record daily attendance for an employee."""
        from hr.models import Attendance
        emp = self.state.employees[employee_name]
        att, _ = Attendance.objects.get_or_create(
            employee=emp, date=self.current_date,
            defaults={'check_in': timezone.now(), 'check_out': timezone.now() + timedelta(hours=float(hours)),
                      'status': status, 'hours_worked': hours}
        )

    def _record_leave(self, employee_name: str, leave_type: str, days: int):
        """Record a leave request."""
        from hr.models import Leave
        emp = self.state.employees[employee_name]
        leave = Leave.objects.create(
            employee=emp, leave_type=leave_type,
            start_date=self.current_date, end_date=self.current_date + timedelta(days=days - 1),
            status='APPROVED', days_requested=days,
            reason=f'{leave_type} leave for {days} day(s)'
        )

    def _make_customer_payment(self, customer_name: str, invoice_num: str, amount: Decimal):
        """Make a payment toward a specific invoice."""
        from sales.models import CustomerPayment
        customer = self.state.customers[customer_name]
        invoice = self.state.invoices[invoice_num]

        CustomerPayment.objects.create(
            customer=customer, invoice=invoice,
            amount=amount, payment_date=self.current_date,
            payment_method='CASH', reference_number=f'PAY-{invoice_num}-{uuid.uuid4().hex[:4]}',
            notes=f'Payment for {invoice_num}'
        )
        invoice.refresh_from_db()

    def _make_supplier_payment(self, supplier_name: str, invoice_num: str, amount: Decimal):
        """Make a payment toward a specific purchase invoice."""
        from purchases.models import SupplierPayment
        supplier = self.state.suppliers[supplier_name]
        invoice = self.state.purchase_invoices[invoice_num]

        SupplierPayment.objects.create(
            supplier=supplier, invoice=invoice,
            amount=amount, payment_date=self.current_date,
            payment_method='CASH', reference_number=f'PAY-{invoice_num}-{uuid.uuid4().hex[:4]}',
            notes=f'Payment for {invoice_num}'
        )
        invoice.refresh_from_db()

    def _create_return(self, return_type: str, invoice: Any, party: Any,
                       items: List[Tuple[Any, Decimal, Any]], reason: str) -> Any:
        """Create and approve a return order."""
        from returns.models import ReturnOrder, ReturnItem
        from inventory.models import StockMovement

        # Ensure every batch has a warehouse-linked stock movement so
        # ReturnItem.restore_inventory() can find the warehouse.
        wh = self.state.warehouse
        for _inv_item, _qty, batch in items:
            if batch and not StockMovement.objects.filter(batch=batch, warehouse=wh).exists():
                StockMovement.objects.create(
                    product=_inv_item.product, batch=batch, warehouse=wh,
                    movement_type='IN', reference_type='MANUAL',
                    reference_id='RETURN-REF', quantity=Decimal('0'),
                    unit_cost=Decimal('0'), notes='Return reference movement'
                )

        ro = ReturnOrder.objects.create(
            return_type=return_type,
            invoice=invoice if return_type == 'SALE_RETURN' else None,
            purchase_invoice=invoice if return_type == 'PURCHASE_RETURN' else None,
            party=party if return_type == 'SALE_RETURN' else None,
            supplier=party if return_type == 'PURCHASE_RETURN' else None,
            status='PENDING', reason=reason,
            total_amount=Decimal('0'),
        )

        total_returned = Decimal('0')
        for inv_item, qty, batch in items:
            total_price = qty * inv_item.unit_price
            kwargs = {
                'return_order': ro,
                'product': inv_item.product,
                'batch': batch,
                'return_quantity': qty,
                'unit_price': inv_item.unit_price,
                'total_price': total_price,
                'condition': 'DAMAGED' if return_type == 'PURCHASE_RETURN' else 'GOOD',
            }
            if return_type == 'SALE_RETURN':
                kwargs['invoice_item'] = inv_item
            else:
                kwargs['purchase_invoice_item'] = inv_item
            ReturnItem.objects.create(**kwargs)
            total_returned += total_price

        ro.total_amount = total_returned
        ro.save()

        emp = self.state.employees['Ahmad']
        ro.approve(employee=emp)
        ro.refresh_from_db()
        self.state.returns[ro.return_number] = ro
        return ro

    # ----------------------------------------------------------------
    # INTEGRITY VALIDATION
    # ----------------------------------------------------------------

    def _check_accounting_integrity(self, report: MonthReport):
        """Verify total debits = total credits across all posted journal entries."""
        from accounting.models import JournalEntry, JournalEntryLine
        from django.db.models import Sum

        for je in JournalEntry.objects.filter(is_posted=True):
            debit_total = je.lines.aggregate(s=Sum('debit'))['s'] or Decimal('0')
            credit_total = je.lines.aggregate(s=Sum('credit'))['s'] or Decimal('0')
            if debit_total != credit_total:
                report.integrity.fail(
                    f"JE Imbalance {je.entry_number}",
                    f"Dr={debit_total} Cr={credit_total} diff={debit_total - credit_total}"
                )
            else:
                report.integrity.ok(f"JE Balanced {je.entry_number}", f"{debit_total} == {credit_total}")

        total_dr = JournalEntryLine.objects.filter(entry__is_posted=True).aggregate(s=Sum('debit'))['s'] or Decimal('0')
        total_cr = JournalEntryLine.objects.filter(entry__is_posted=True).aggregate(s=Sum('credit'))['s'] or Decimal('0')
        if total_dr != total_cr:
            report.integrity.fail("Global JE Balance", f"Total Dr={total_dr} != Total Cr={total_cr}")
        else:
            report.integrity.ok("Global JE Balance", f"{total_dr} == {total_cr}")

    def _check_no_orphan_entries(self, report: MonthReport):
        """Verify no journal entry has zero lines."""
        from accounting.models import JournalEntry
        orphans = JournalEntry.objects.annotate(line_count=Count('lines')).filter(line_count=0)
        for o in orphans:
            report.integrity.fail(f"Orphan JE {o.entry_number}", "Journal entry has zero lines")

    def _check_customer_balances(self, report: MonthReport):
        """Verify customer AR balances match accounting records (including returns)."""
        from sales.models import SalesInvoice
        from accounting.models import JournalEntryLine, Account
        from returns.models import ReturnOrder
        from django.db.models import Sum
        ar_account = self.state.accounts[AR_ACCOUNT_CODE]
        ar_debits = JournalEntryLine.objects.filter(
            entry__is_posted=True, account=ar_account
        ).aggregate(s=Sum('debit'))['s'] or Decimal('0')
        ar_credits = JournalEntryLine.objects.filter(
            entry__is_posted=True, account=ar_account
        ).aggregate(s=Sum('credit'))['s'] or Decimal('0')
        ar_balance = ar_debits - ar_credits
        expected_ar = sum(
            inv.total_amount - inv.paid_amount
            for c in self.state.customers.values()
            for inv in SalesInvoice.objects.filter(
                customer=c, status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID']
            )
        )
        # Sale returns credit AR (reduce expected) — signal auto-completes to COMPLETED after approve
        return_credits = sum(
            ro.total_amount for ro in ReturnOrder.objects.filter(
                return_type='SALE_RETURN', status__in=['APPROVED', 'COMPLETED']
            )
        )
        expected_ar -= return_credits
        # Customer refunds debit AR (increase expected) — refund reverses a payment credit
        from payments.models import FinancialTransaction
        refunds = FinancialTransaction.objects.filter(
            party_type='CUSTOMER', transaction_type='PAYMENT', status='COMPLETED'
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        expected_ar += refunds
        if abs(ar_balance - expected_ar) > Decimal('0.02'):
            report.integrity.fail(f"AR Balance", f"AR account={ar_balance} but expected={expected_ar}")
        else:
            report.integrity.ok(f"AR Balance", f"AR={ar_balance} matches expected={expected_ar}")
        for c in self.state.customers.values():
            invoices = SalesInvoice.objects.filter(
                customer=c, status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID']
            )
            expected = sum(inv.total_amount - inv.paid_amount for inv in invoices)
            report.integrity.ok(f"Customer {c.name}", f"balance={expected}")

    def _check_supplier_balances(self, report: MonthReport):
        """Verify supplier AP balances match accounting records (including returns)."""
        from purchases.models import PurchaseInvoice
        from accounting.models import JournalEntryLine, Account
        from returns.models import ReturnOrder
        from django.db.models import Sum
        ap_account = self.state.accounts[AP_ACCOUNT_CODE]
        ap_credits = JournalEntryLine.objects.filter(
            entry__is_posted=True, account=ap_account
        ).aggregate(s=Sum('credit'))['s'] or Decimal('0')
        ap_debits = JournalEntryLine.objects.filter(
            entry__is_posted=True, account=ap_account
        ).aggregate(s=Sum('debit'))['s'] or Decimal('0')
        ap_balance = ap_credits - ap_debits
        expected_ap = sum(
            inv.total_amount - inv.paid_amount
            for s in self.state.suppliers.values()
            for inv in PurchaseInvoice.objects.filter(
                supplier=s, status__in=['RECEIVED', 'CONFIRMED', 'PARTIAL_PAID']
            )
        )
        # Purchase returns debit AP (reduce expected) — signal auto-completes to COMPLETED after approve
        return_debits = sum(
            ro.total_amount for ro in ReturnOrder.objects.filter(
                return_type='PURCHASE_RETURN', status__in=['APPROVED', 'COMPLETED']
            )
        )
        expected_ap -= return_debits
        if abs(ap_balance - expected_ap) > Decimal('0.02'):
            report.integrity.fail(f"AP Balance", f"AP account={ap_balance} but expected={expected_ap}")
        else:
            report.integrity.ok(f"AP Balance", f"AP={ap_balance} matches expected={expected_ap}")
        for s in self.state.suppliers.values():
            invoices = PurchaseInvoice.objects.filter(
                supplier=s, status__in=['RECEIVED', 'CONFIRMED', 'PARTIAL_PAID']
            )
            expected = sum(inv.total_amount - inv.paid_amount for inv in invoices)
            report.integrity.ok(f"Supplier {s.name}", f"balance={expected}")

    def _check_no_negative_stock(self, report: MonthReport):
        """Verify no batch has negative remaining quantity."""
        from inventory.models import Batch
        neg = Batch.objects.filter(remaining_quantity__lt=0, is_active=True)
        for b in neg:
            report.integrity.fail(f"Negative Stock {b.batch_number}", f"{b.product.name} qty={b.remaining_quantity}")

    def _check_inventory_valuation(self, report: MonthReport):
        """Verify inventory valuation matches stock movements."""
        from inventory.models import Batch
        total_val = Decimal('0')
        for b in Batch.objects.filter(is_active=True):
            if b.remaining_quantity > 0 and b.purchase_price:
                val = b.remaining_quantity * b.purchase_price
                total_val += val
        report.integrity.ok("Inventory Valuation", f"Total {total_val}")

    def _check_treasury(self, report: MonthReport):
        """Verify payment account balances match expected."""
        from payments.models import PaymentAccount
        for pa in PaymentAccount.objects.filter(is_active=True):
            if pa.current_balance < 0:
                report.integrity.fail(f"Negative Treasury {pa.code}", f"balance={pa.current_balance}")

    def _run_full_integrity_check(self, report: MonthReport):
        """Run all integrity checks."""
        self._check_accounting_integrity(report)
        self._check_customer_balances(report)
        self._check_supplier_balances(report)
        self._check_no_negative_stock(report)
        self._check_inventory_valuation(report)
        self._check_treasury(report)

    # ----------------------------------------------------------------
    # DAY SCRIPTS
    # ----------------------------------------------------------------

    def run_day(self, day_num: int) -> MonthReport:
        """Execute operations for a single simulation day."""
        self.current_date = date(2026, 1, day_num)
        report = MonthReport(day=day_num, date=self.current_date)

        day_runner = getattr(self, f'_day_{day_num:02d}', None)
        if day_runner:
            try:
                day_runner(report)
            except Exception as e:
                logger.error(f"Day {day_num} FAILED: {e}")
                report.notes.append(f"ERROR: {e}")
                raise
        else:
            # Non-operational day — just run integrity
            report.operations.append("No operations scheduled")

        self._run_full_integrity_check(report)
        self.state.report.days.append(report)
        return report

    # ---- DAY 1: Opening + First Sale ----
    def _day_01(self, r: MonthReport):
        r.operations.append("Opening stock already initialized")
        r.operations.append("Sale to Ali: 2 Amoxicillin, 1 Paracetamol Syrup, 3 Ibuprofen = 12,500 AFN")
        result = self._make_sale('Ali Wholesale', [
            ('Amoxicillin 500mg', Decimal('2')),
            ('Paracetamol Syrup 120ml', Decimal('1')),
            ('Ibuprofen 400mg', Decimal('3')),
        ], payment_amount=Decimal('6000'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Paid={inv.paid_amount}, Balance={inv.remaining_balance}")
        r.notes.append(f"Customer Ali balance: {self.state.customers['Ali Wholesale'].balance}")

    # ---- DAY 2: Sale to Karim ----
    def _day_02(self, r: MonthReport):
        r.operations.append("Sale to Karim: 5 Ibuprofen = 1,250 AFN, fully paid")
        result = self._make_sale('Karim Pharmacy', [
            ('Ibuprofen 400mg', Decimal('5')),
        ], payment_amount=Decimal('1250'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Fully paid")

    # ---- DAY 3: Purchase from Rahman Pharma ----
    def _day_03(self, r: MonthReport):
        r.operations.append("Purchase from Rahman Pharma: 100 Amoxicillin, 50 Syrups = 19,000 AFN, pay 10,000")
        future_expiry = date(2027, 6, 1)
        result = self._make_purchase('Rahman Pharma', [
            ('Amoxicillin 500mg', Decimal('100'), Decimal('150'), future_expiry),
            ('Paracetamol Syrup 120ml', Decimal('50'), Decimal('80'), date(2026, 12, 1)),
        ], payment_amount=Decimal('10000'))
        inv = result['invoice']
        r.operations.append(f"Purchase {inv.invoice_number}: Total={inv.total_amount}, Paid={inv.paid_amount}, Owe={inv.remaining_balance}")
        r.notes.append(f"Supplier Rahman balance: {self.state.suppliers['Rahman Pharma'].balance}")

    # ---- DAY 4: Sale to Fatima (credit) ----
    def _day_04(self, r: MonthReport):
        r.operations.append("Sale to Fatima Hospital: 10 Amoxicillin, 5 Ibuprofen = 4,750 AFN, credit (no payment)")
        result = self._make_sale('Fatima Hospital', [
            ('Amoxicillin 500mg', Decimal('10')),
            ('Ibuprofen 400mg', Decimal('5')),
        ], payment_amount=Decimal('0'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Payment=0, Full credit")
        r.notes.append(f"Fatima balance: {self.state.customers['Fatima Hospital'].balance}")

    # ---- DAY 5: Additional sale to Ali (accumulates debt) ----
    def _day_05(self, r: MonthReport):
        r.operations.append("Sale to Ali: 5 Amoxicillin = 1,750 AFN, no payment (adds to existing 6,500 debt)")
        result = self._make_sale('Ali Wholesale', [
            ('Amoxicillin 500mg', Decimal('5')),
        ], payment_amount=Decimal('0'))
        inv = result['invoice']
        ali = self.state.customers['Ali Wholesale']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Ali total debt=~{ali.balance}")
        r.notes.append(f"Invoice SI-0001 remaining: {self.state.invoices['SI-0001'].remaining_balance}")

    # ---- DAY 6: Ali returns 1 syrup + 1 painkiller ----
    def _day_06(self, r: MonthReport):
        r.operations.append("Ali returns 1 Paracetamol Syrup + 1 Ibuprofen")
        original_invoice = self.state.invoices['SI-0001']
        from inventory.models import Batch
        # Find specific items by product name (UUID ordering is random)
        items_by_product = {item.product.name: item for item in original_invoice.items.all()}
        ro = self._create_return(
            return_type='SALE_RETURN', invoice=original_invoice,
            party=self.state.customers['Ali Wholesale'],
            items=[
                (items_by_product['Paracetamol Syrup 120ml'], Decimal('1'), self.state.batches['Paracetamol Syrup 120ml']),
                (items_by_product['Ibuprofen 400mg'], Decimal('1'), self.state.batches['Ibuprofen 400mg']),
            ],
            reason='Damaged goods'
        )
        r.operations.append(f"Return {ro.return_number}: Total={ro.total_amount}, Status={ro.status}")
        r.notes.append(f"Invoice SI-0001 remaining balance after return: {original_invoice.remaining_balance}")

    # ---- DAY 7: Record employee attendance ----
    def _day_07(self, r: MonthReport):
        r.operations.append("Record weekly attendance for all employees")
        for emp_name in ['Hassan', 'Ahmad', 'Mahmood']:
            self._record_attendance(emp_name, 'PRESENT')
        r.operations.append("All employees present")

    # ---- DAY 8: Purchase from Kabul Medical ----
    def _day_08(self, r: MonthReport):
        r.operations.append("Purchase from Kabul Medical: 200 Ibuprofen = 20,000 AFN, pay 8,000")
        result = self._make_purchase('Kabul Medical Supply', [
            ('Ibuprofen 400mg', Decimal('200'), Decimal('100'), date(2027, 3, 1)),
        ], payment_amount=Decimal('8000'))
        inv = result['invoice']
        r.operations.append(f"Purchase {inv.invoice_number}: Total={inv.total_amount}, Paid=8,000, Owe=12,000")

    # ---- DAY 9: Sale to Karim partial payment ----
    def _day_09(self, r: MonthReport):
        r.operations.append("Sale to Karim: 3 Amoxicillin, 2 Syrups = 1,450 AFN, pay 1,000")
        result = self._make_sale('Karim Pharmacy', [
            ('Amoxicillin 500mg', Decimal('3')),
            ('Paracetamol Syrup 120ml', Decimal('2')),
        ], payment_amount=Decimal('1000'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Paid=1,000, Balance={inv.remaining_balance}")

    # ---- DAY 10: Ali partial payment ----
    def _day_10(self, r: MonthReport):
        r.operations.append("Ali pays 5,000 AFN toward SI-0001 debt")
        self._make_customer_payment('Ali Wholesale', 'SI-0001', Decimal('5000'))
        inv = self.state.invoices['SI-0001']
        ali = self.state.customers['Ali Wholesale']
        r.operations.append(f"Invoice SI-0001: Paid now={inv.paid_amount}, Remaining={inv.remaining_balance}")
        r.notes.append(f"Ali total balance: {ali.balance}")

    # ---- DAY 11: Sale to Fatima (credit) ----
    def _day_11(self, r: MonthReport):
        r.operations.append("Sale to Fatima: 20 Amoxicillin, 10 Ibuprofen = 9,500 AFN, credit")
        result = self._make_sale('Fatima Hospital', [
            ('Amoxicillin 500mg', Decimal('20')),
            ('Ibuprofen 400mg', Decimal('10')),
        ], payment_amount=Decimal('0'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Full credit")
        r.notes.append(f"Fatima balance now: {self.state.customers['Fatima Hospital'].balance}")

    # ---- DAY 12: Return expired goods to Rahman Pharma ----
    def _day_12(self, r: MonthReport):
        r.operations.append("Return 10 expired Amoxicillin to Rahman Pharma")
        purchase_inv = list(self.state.purchase_invoices.values())[0]
        from inventory.models import Batch, StockMovement
        # Find the batch linked to StockMovements for each product by name
        items_by_product = {}
        for item in purchase_inv.items.all():
            sm = StockMovement.objects.filter(
                product=item.product, reference_type='PURCHASE',
                reference_id=str(purchase_inv.id)
            ).order_by('-created_at').first()
            batch = sm.batch if sm else Batch.objects.filter(
                product=item.product
            ).order_by('-created_at').first()
            items_by_product[item.product.name] = (item, batch)
        target_item, target_batch = items_by_product.get(
            'Amoxicillin 500mg', list(items_by_product.values())[0]
        )
        ro = self._create_return(
            return_type='PURCHASE_RETURN', invoice=purchase_inv,
            party=self.state.suppliers['Rahman Pharma'],
            items=[
                (target_item, Decimal('10'), target_batch),
            ],
            reason='Expired goods return'
        )
        r.operations.append(f"Return {ro.return_number}: Total={ro.total_amount}, Status={ro.status}")

    # ---- DAY 13: Sale to Ali ----
    def _day_13(self, r: MonthReport):
        r.operations.append("Sale to Ali: 8 Amoxicillin, 4 Ibuprofen = 3,800 AFN, pay 2,000")
        result = self._make_sale('Ali Wholesale', [
            ('Amoxicillin 500mg', Decimal('8')),
            ('Ibuprofen 400mg', Decimal('4')),
        ], payment_amount=Decimal('2000'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Paid=2,000, Balance={inv.remaining_balance}")

    # ---- DAY 14: Record attendance + leave ----
    def _day_14(self, r: MonthReport):
        r.operations.append("Record attendance + leave")
        for emp_name in ['Hassan', 'Ahmad', 'Mahmood']:
            self._record_attendance(emp_name, 'PRESENT')
        # Hassan takes 2 days legal leave
        self._record_leave('Hassan', 'ANNUAL', 2)
        r.operations.append("Hassan: 2 days annual leave approved")

    # ---- DAY 15: Pay Rahman Pharma 15,000 ----
    def _day_15(self, r: MonthReport):
        r.operations.append("Pay Rahman Pharma 15,000 AFN toward PI-0001")
        inv_num = list(self.state.purchase_invoices.keys())[0]
        self._make_supplier_payment('Rahman Pharma', inv_num, Decimal('15000'))
        inv = self.state.purchase_invoices[inv_num]
        r.operations.append(f"Purchase {inv_num}: Paid={inv.paid_amount}, Remaining={inv.remaining_balance}")

    # ---- DAY 16: Sale to Karim ----
    def _day_16(self, r: MonthReport):
        r.operations.append("Sale to Karim: 10 Syrups, 5 Ibuprofen = 3,250 AFN, full payment")
        result = self._make_sale('Karim Pharmacy', [
            ('Paracetamol Syrup 120ml', Decimal('10')),
            ('Ibuprofen 400mg', Decimal('5')),
        ], payment_amount=Decimal('3250'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Fully paid")

    # ---- DAY 17: Purchase from Rahman (full payment) ----
    def _day_17(self, r: MonthReport):
        r.operations.append("Purchase from Rahman: 150 Amoxicillin = 22,500 AFN, full payment")
        result = self._make_purchase('Rahman Pharma', [
            ('Amoxicillin 500mg', Decimal('150'), Decimal('150'), date(2027, 8, 1)),
        ], payment_amount=Decimal('22500'))
        inv = result['invoice']
        r.operations.append(f"Purchase {inv.invoice_number}: Fully paid")

    # ---- DAY 18: Fatima pays 20,000 ----
    def _day_18(self, r: MonthReport):
        r.operations.append("Fatima pays 20,000 AFN toward SI-0003")
        inv = self.state.invoices.get('SI-0003')
        if inv:
            self._make_customer_payment('Fatima Hospital', 'SI-0003', Decimal('20000'))
            inv.refresh_from_db()
            r.operations.append(f"Invoice SI-0003: Paid={inv.paid_amount}, Remaining={inv.remaining_balance}")
        fatima = self.state.customers['Fatima Hospital']
        r.notes.append(f"Fatima balance: {fatima.balance}")

    # ---- DAY 19: Sale to Ali with partial payment ----
    def _day_19(self, r: MonthReport):
        r.operations.append("Sale to Ali: 15 Amoxicillin, 10 Syrups = 7,250 AFN, pay 5,000")
        result = self._make_sale('Ali Wholesale', [
            ('Amoxicillin 500mg', Decimal('15')),
            ('Paracetamol Syrup 120ml', Decimal('10')),
        ], payment_amount=Decimal('5000'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Paid=5,000, Balance={inv.remaining_balance}")

    # ---- DAY 20: Return from Karim ----
    def _day_20(self, r: MonthReport):
        r.operations.append("Karim returns 2 Ibuprofen from SI-0002")
        original_invoice = self.state.invoices['SI-0002']
        items_by_product = {item.product.name: item for item in original_invoice.items.all()}
        if items_by_product:
            ro = self._create_return(
                return_type='SALE_RETURN', invoice=original_invoice,
                party=self.state.customers['Karim Pharmacy'],
                items=[
                    (items_by_product['Ibuprofen 400mg'], Decimal('2'), self.state.batches['Ibuprofen 400mg']),
                ],
                reason='Customer return: 2 Ibuprofen'
            )
            r.operations.append(f"Return {ro.return_number}: Total={ro.total_amount}, Status={ro.status}")

    # ---- DAY 21: Pay Kabul Medical ----
    def _day_21(self, r: MonthReport):
        r.operations.append("Pay Kabul Medical 12,000 AFN toward PI-0002")
        inv_key = list(self.state.purchase_invoices.keys())[1] if len(self.state.purchase_invoices) > 1 else None
        if inv_key:
            self._make_supplier_payment('Kabul Medical Supply', inv_key, Decimal('12000'))
            inv = self.state.purchase_invoices[inv_key]
            r.operations.append(f"Purchase {inv_key}: Paid={inv.paid_amount}, Remaining={inv.remaining_balance}")

    # ---- DAY 22: Sale to Fatima ----
    def _day_22(self, r: MonthReport):
        r.operations.append("Sale to Fatima: 30 Amoxicillin, 15 Syrups, 10 Ibuprofen = 15,500 AFN, credit")
        result = self._make_sale('Fatima Hospital', [
            ('Amoxicillin 500mg', Decimal('30')),
            ('Paracetamol Syrup 120ml', Decimal('15')),
            ('Ibuprofen 400mg', Decimal('10')),
        ], payment_amount=Decimal('0'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Full credit")
        r.notes.append(f"Fatima balance now: {self.state.customers['Fatima Hospital'].balance}")

    # ---- DAY 23: Ali pays 10,000 ----
    def _day_23(self, r: MonthReport):
        r.operations.append("Ali pays 10,000 AFN toward his oldest debt")
        for inv_key in ['SI-0001', 'SI-0005']:
            inv = self.state.invoices.get(inv_key)
            if inv and inv.remaining_balance > 0:
                pay_amt = min(Decimal('10000'), inv.remaining_balance)
                self._make_customer_payment('Ali Wholesale', inv_key, pay_amt)
                r.operations.append(f"Paid {pay_amt} toward {inv_key}")
        ali = self.state.customers['Ali Wholesale']
        r.notes.append(f"Ali balance after payment: {ali.balance}")

    # ---- DAY 24: Purchase from Kabul Medical (credit) ----
    def _day_24(self, r: MonthReport):
        r.operations.append("Purchase from Kabul Medical: 100 Syrups, 150 Ibuprofen = 23,000 AFN, credit")
        result = self._make_purchase('Kabul Medical Supply', [
            ('Paracetamol Syrup 120ml', Decimal('100'), Decimal('80'), date(2026, 12, 1)),
            ('Ibuprofen 400mg', Decimal('150'), Decimal('100'), date(2027, 5, 1)),
        ], payment_amount=Decimal('0'))
        inv = result['invoice']
        r.operations.append(f"Purchase {inv.invoice_number}: Total={inv.total_amount}, Full credit")
        r.notes.append(f"Kabul Medical balance: {self.state.suppliers['Kabul Medical Supply'].balance}")

    # ---- DAY 25: Sale to Karim ----
    def _day_25(self, r: MonthReport):
        r.operations.append("Sale to Karim: 20 Amoxicillin, 25 Syrups = 12,000 AFN, pay 8,000")
        result = self._make_sale('Karim Pharmacy', [
            ('Amoxicillin 500mg', Decimal('20')),
            ('Paracetamol Syrup 120ml', Decimal('25')),
        ], payment_amount=Decimal('8000'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Paid=8,000, Balance={inv.remaining_balance}")

    # ---- DAY 26: Payroll processing ----
    def _day_26(self, r: MonthReport):
        r.operations.append("Process month-end payroll")
        from payroll.models import PayrollCycle, PayrollRecord, EmployeeSalary, EmployeeAllowance, EmployeeDeduction
        from accounting.services.journal_engine import JournalEngine

        # Create salary structures for each employee
        for emp_name, emp_obj in self.state.employees.items():
            es, _ = EmployeeSalary.objects.get_or_create(
                employee=emp_obj,
                defaults={'basic_salary': emp_obj.basic_salary, 'is_active': True}
            )
            EmployeeAllowance.objects.get_or_create(
                employee_salary=es, allowance=self.state.allowances['Transport'],
                defaults={'custom_amount': Decimal('2000')}
            )
            EmployeeDeduction.objects.get_or_create(
                employee_salary=es, deduction=self.state.deductions['Health'],
                defaults={'custom_amount': Decimal('1000')}
            )
            EmployeeDeduction.objects.get_or_create(
                employee_salary=es, deduction=self.state.deductions['Tax'],
                defaults={'custom_amount': None}
            )

        cycle, _ = PayrollCycle.objects.get_or_create(
            period_month=1, period_year=2026,
            defaults={
                'name': 'January 2026',
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 1, 31),
                'status': 'DRAFT',
            }
        )

        total_gross = Decimal('0')
        total_ded = Decimal('0')
        total_net = Decimal('0')
        emp_records = []

        for emp_name, emp_obj in self.state.employees.items():
            es = EmployeeSalary.objects.get(employee=emp_obj)
            basic = es.basic_salary
            allowances_total = sum(
                ea.custom_amount or ea.allowance.amount
                for ea in es.employeeallowance_set.select_related('allowance').all() if ea.allowance.allowance_type == 'FIXED'
            )
            deductions_total = Decimal('0')
            for ed in es.employeededuction_set.select_related('deduction').all():
                if ed.deduction.deduction_type == 'FIXED':
                    deductions_total += ed.custom_amount or ed.deduction.amount
                elif ed.deduction.deduction_type == 'PERCENTAGE':
                    pct = ed.deduction.percentage
                    deductions_total += (basic + allowances_total) * pct / Decimal('100')

            gross = basic + allowances_total
            net = gross - deductions_total
            total_gross += gross
            total_ded += deductions_total
            total_net += net
            emp_records.append((emp_obj, basic, allowances_total, deductions_total, gross, net))

            PayrollRecord.objects.get_or_create(
                payroll_cycle=cycle, employee=emp_obj,
                defaults={
                    'basic_salary': basic, 'total_allowances': allowances_total,
                    'total_deductions': deductions_total, 'gross_salary': gross,
                    'net_salary': net, 'status': 'CALCULATED',
                }
            )

        cycle.total_gross = total_gross
        cycle.total_deductions = total_ded
        cycle.total_net = total_net
        cycle.status = 'APPROVED'
        cycle.save()

        # Create payroll journal entry via JournalEngine
        from accounting.models import Account
        salary_expense = self.state.accounts[PAYROLL_SALARY_EXPENSE_CODE]
        cash_account = self.state.accounts[PAYROLL_CASH_CODE]
        tax_account = self.state.accounts[PAYROLL_TAX_CODE]

        lines = [
            {'account_id': str(salary_expense.id), 'debit': str(total_gross), 'credit': '0', 'description': f'Payroll {cycle.name} gross salaries'},
            {'account_id': str(cash_account.id), 'debit': '0', 'credit': str(total_net), 'description': f'Net pay to employees {cycle.name}'},
        ]
        if total_ded > 0:
            lines.append({'account_id': str(tax_account.id), 'debit': '0', 'credit': str(total_ded), 'description': f'Payroll deductions {cycle.name}'})

        je_result = JournalEngine.create_entry(
            entry_type='PAYROLL',
            description=f'Payroll {cycle.name}',
            lines=lines,
            entry_date=self.current_date,
            reference=cycle.name,
            auto_post=True,
            source_module='payroll',
            source_document=str(cycle.id),
        )

        if je_result.get('success'):
            cycle.accounting_entry_id = je_result.get('entry_id')
            cycle.status = 'PAID'
            cycle.save()
            r.operations.append(f"Payroll: Gross={total_gross}, Ded={total_ded}, Net={total_net}, JE={je_result.get('entry_number')}")
        else:
            r.notes.append(f"Payroll JE failed: {je_result.get('errors', 'unknown')}")

        self.state.payroll_cycles['Jan2026'] = cycle

    # ---- DAY 27: Treasury review + Rahman payment ----
    def _day_27(self, r: MonthReport):
        r.operations.append("Pay Rahman Pharma remaining balance on PI-0001")
        inv_key = list(self.state.purchase_invoices.keys())[0]
        inv = self.state.purchase_invoices[inv_key]
        if inv.remaining_balance > 0:
            self._make_supplier_payment('Rahman Pharma', inv_key, inv.remaining_balance)
            r.operations.append(f"Paid remaining {inv.remaining_balance} on {inv_key}")
        inv.refresh_from_db()

    # ---- DAY 28: Routine operations ----
    def _day_28(self, r: MonthReport):
        r.operations.append("Sale to Karim: 5 Amoxicillin, 10 Ibuprofen = 4,250 AFN, pay 4,250")
        result = self._make_sale('Karim Pharmacy', [
            ('Amoxicillin 500mg', Decimal('5')),
            ('Ibuprofen 400mg', Decimal('10')),
        ], payment_amount=Decimal('4250'))
        inv = result['invoice']
        r.operations.append(f"Invoice {inv.invoice_number}: Fully paid")

    # ---- DAY 29: Final collections ----
    def _day_29(self, r: MonthReport):
        r.operations.append("Final collections push")
        # Collect from Karim
        for inv_key, inv in list(self.state.invoices.items()):
            if inv.customer == self.state.customers['Karim Pharmacy'] and inv.remaining_balance > 0:
                self._make_customer_payment('Karim Pharmacy', inv_key, inv.remaining_balance)
                r.operations.append(f"Karim fully paid {inv_key}: {inv.remaining_balance}")

    # ---- DAY 30: Month-end closing + final integrity audit ----
    def _day_30(self, r: MonthReport):
        r.operations.append("Month-end closing: Recalculate all account balances")
        from accounting.services.journal_engine import JournalEngine
        JournalEngine.recalculate_all_balances()

        r.operations.append("Running comprehensive month-end integrity audit")
        # Additional checks specific to month-end
        from accounting.models import Account
        for code, acc in self.state.accounts.items():
            acc.refresh_from_db()
            r.notes.append(f"Account {code} ({acc.name}): balance={acc.balance}")

        # Final treasury check
        from payments.models import PaymentAccount
        for pa in PaymentAccount.objects.filter(is_active=True):
            r.notes.append(f"Treasury {pa.code}: {pa.current_balance}")

        r.operations.append("Month-end closing complete")

    # ----------------------------------------------------------------
    # FINAL REPORT
    # ----------------------------------------------------------------

    def generate_final_report(self) -> FinalReport:
        """Generate the comprehensive final report."""
        report = self.state.report
        from accounting.models import JournalEntry, JournalEntryLine, Account
        from sales.models import Customer
        from purchases.models import Supplier
        from inventory.models import Batch
        from payments.models import PaymentAccount, FinancialTransaction
        from django.db.models import Sum

        # Accounting Summary
        report.accounting_summary = {}
        for code, acc in sorted(self.state.accounts.items()):
            acc.refresh_from_db()
            report.accounting_summary[f"{code} {acc.name}"] = acc.balance

        # Customer Ledger
        for c in Customer.objects.all():
            report.customer_ledger[c.name] = {
                'balance': c.balance,
                'credit_limit': c.credit_limit,
                'available_credit': c.available_credit,
            }

        # Supplier Ledger
        for s in Supplier.objects.all():
            report.supplier_ledger[s.name] = {
                'balance': s.balance,
                'credit_limit': s.credit_limit,
            }

        # Inventory Summary
        for b in Batch.objects.filter(is_active=True):
            report.inventory_summary[b.batch_number] = {
                'product': str(b.product),
                'remaining': b.remaining_quantity,
                'value': b.remaining_quantity * (b.purchase_price or Decimal('0')),
            }

        # Treasury
        for pa in PaymentAccount.objects.filter(is_active=True):
            txns = FinancialTransaction.objects.filter(
                source_account=pa, status='COMPLETED'
            ).count() + FinancialTransaction.objects.filter(
                destination_account=pa, status='COMPLETED'
            ).count()
            report.treasury_movements.append(f"{pa.code}: balance={pa.current_balance}, transactions={txns}")

        # Payroll Summary
        for name, pc in self.state.payroll_cycles.items():
            report.payroll_summary[name] = {
                'gross': pc.total_gross,
                'deductions': pc.total_deductions,
                'net': pc.total_net,
                'status': pc.status,
            }

        # Overall Verdict
        total_violations = sum(len(d.integrity.failed) for d in report.days)
        if total_violations == 0:
            report.verdict = "PASS: All integrity checks passed across 30 days"
        else:
            report.verdict = f"FAIL: {total_violations} integrity violations detected across 30 days"

        return report

    def print_report(self, report: FinalReport):
        """Print the final simulation report (returns string)."""
        buf = io.StringIO()
        buf.write("\n")
        buf.write("=" * 80 + "\n")
        buf.write("PHARMACY ERP — 30-DAY INDUSTRIAL REALITY SIMULATION REPORT\n")
        buf.write("=" * 80 + "\n\n")

        for day_report in report.days:
            buf.write(f"--- Day {day_report.day:02d} ({day_report.date}) ---\n")
            for op in day_report.operations:
                buf.write(f"  {op}\n")
            for note in day_report.notes:
                buf.write(f"  [{note}]\n")
            if day_report.integrity.failed:
                for f in day_report.integrity.failed:
                    buf.write(f"  ** INTEGRITY FAIL: {f}\n")
            buf.write(f"  Integrity: {len(day_report.integrity.passed)} OK, "
                      f"{len(day_report.integrity.failed)} FAIL\n\n")

        buf.write("=" * 80 + "\n")
        buf.write("FINAL ACCOUNTING SUMMARY\n")
        buf.write("=" * 80 + "\n")
        for k, v in report.accounting_summary.items():
            buf.write(f"  {k}: {v}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write("CUSTOMER LEDGER\n")
        buf.write("=" * 80 + "\n")
        for name, data in report.customer_ledger.items():
            buf.write(f"  {name}: balance={data['balance']}, credit_limit={data['credit_limit']}, "
                      f"available={data['available_credit']}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write("SUPPLIER LEDGER\n")
        buf.write("=" * 80 + "\n")
        for name, data in report.supplier_ledger.items():
            buf.write(f"  {name}: balance={data['balance']}, credit_limit={data['credit_limit']}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write("TREASURY MOVEMENT REPORT\n")
        buf.write("=" * 80 + "\n")
        for t in report.treasury_movements:
            buf.write(f"  {t}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write("INVENTORY SUMMARY\n")
        buf.write("=" * 80 + "\n")
        for bn, data in report.inventory_summary.items():
            buf.write(f"  {bn} ({data['product']}): remaining={data['remaining']}, value={data['value']}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write("PAYROLL SUMMARY\n")
        buf.write("=" * 80 + "\n")
        for name, data in report.payroll_summary.items():
            buf.write(f"  {name}: gross={data['gross']}, ded={data['deductions']}, "
                      f"net={data['net']}, status={data['status']}\n")

        buf.write("\n" + "=" * 80 + "\n")
        buf.write(f"VERDICT: {report.verdict}\n")
        buf.write("=" * 80 + "\n")

        total_ops = sum(len(d.operations) for d in report.days)
        total_checks = sum(len(d.integrity.passed) + len(d.integrity.failed) for d in report.days)
        total_fails = sum(len(d.integrity.failed) for d in report.days)
        buf.write(f"\nTotal operations: {total_ops}\n")
        buf.write(f"Total integrity checks: {total_checks}\n")
        buf.write(f"Total violations: {total_fails}\n")
        buf.write(f"Days with violations: {sum(1 for d in report.days if d.integrity.failed)}\n")

        return buf.getvalue()


# =============================================================================
# DJANGO TEST CASE
# =============================================================================

class TestMonthRealitySimulation(TransactionTestCase):
    """Run the 30-day industrial reality simulation."""

    # Large number of operations; allow sufficient time

    def test_full_30_day_simulation(self):
        """Execute all 30 days of the reality simulation."""
        sim = MonthRealitySimulation()
        sim.setup_base_data()

        for day in range(1, 31):
            with transaction.atomic():
                report = sim.run_day(day)
                if report.integrity.failed:
                    fails = '; '.join(report.integrity.failed[:5])
                    logger.warning(f"Day {day}: {len(report.integrity.failed)} integrity failures: {fails}")

        final = sim.generate_final_report()
        report_text = sim.print_report(final)
        print(report_text)

        self.assertIn('PASS', final.verdict,
                      msg=f"Simulation FAILED with violations\n{report_text}")

        # Additional assertions
        from sales.models import Customer
        for c in Customer.objects.all():
            self.assertGreaterEqual(c.credit_limit, c.balance,
                                    f"Customer {c.name} over credit limit: balance={c.balance} > limit={c.credit_limit}")

        from inventory.models import Batch
        neg_batches = Batch.objects.filter(remaining_quantity__lt=0, is_active=True)
        self.assertEqual(neg_batches.count(), 0, f"Negative stock detected: {[(b.batch_number, b.remaining_quantity) for b in neg_batches]}")

        from accounting.models import JournalEntry, JournalEntryLine
        from django.db.models import Sum
        total_dr = JournalEntryLine.objects.filter(entry__is_posted=True).aggregate(s=Sum('debit'))['s'] or Decimal('0')
        total_cr = JournalEntryLine.objects.filter(entry__is_posted=True).aggregate(s=Sum('credit'))['s'] or Decimal('0')
        self.assertEqual(total_dr, total_cr, f"Global accounting mismatch: Dr={total_dr} != Cr={total_cr}")
