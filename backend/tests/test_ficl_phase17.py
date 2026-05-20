"""Tests for Phase 17: Financial Intelligence + Operational Completeness Layer (FICL).

Covers all 6 modules:
1. Anomaly Detection Engine (read-only)
2. Reconciliation Assistance V2 (guided matching)
3. Credit Risk Intelligence (advisory)
4. Cashflow Observability (on-demand)
5. Financial Explainability (read-only trace)
6. Financial Diagnostics (health scoring)
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from sales.models import Customer, SalesInvoice, CustomerPayment, PaymentAllocation
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation
from accounting.models import Account, JournalEntry


def ensure_accounts():
    """Ensure required accounting accounts exist."""
    accounts_data = [
        ('1200', 'Accounts Receivable', 'ASSET'),
        ('2100', 'Accounts Payable', 'LIABILITY'),
        ('4100', 'Sales Revenue', 'REVENUE'),
        ('5100', 'Cost of Goods Sold', 'EXPENSE'),
        ('1300', 'Inventory', 'ASSET'),
        ('1010', 'Cash', 'ASSET'),
    ]
    for code, name, acct_type in accounts_data:
        Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'is_active': True},
        )


def ensure_payment_account():
    """Ensure a default payment account and methods exist for payment processing."""
    from payments.models import PaymentAccount, PaymentMethod
    cash_account = Account.objects.filter(code='1010').first()
    if not cash_account:
        cash_account = Account.objects.create(
            code='1010', name='Cash', account_type='ASSET', is_active=True
        )
    pa, created = PaymentAccount.objects.get_or_create(
        code='CASH-MAIN',
        defaults={
            'name': 'Main Cash',
            'account_type': 'CASH',
            'accounting_account': cash_account,
            'currency': 'AFN',
            'is_active': True,
            'current_balance': Decimal('1000000.00'),
        },
    )
    if not created:
        pa.current_balance = Decimal('1000000.00')
        pa.save(update_fields=['current_balance'])
    for method_type, name, code in [
        ('CASH', 'Cash', 'CASH'),
        ('BANK_TRANSFER', 'Bank Transfer', 'BANK'),
        ('CHEQUE', 'Cheque', 'CHEQUE'),
        ('CREDIT_CARD', 'Credit Card', 'CC'),
    ]:
        PaymentMethod.objects.get_or_create(
            code=code,
            defaults={'name': name, 'method_type': method_type, 'is_active': True},
        )
    return pa


# =========================================================================
# 1. Anomaly Detection Engine
# =========================================================================

class AnomalyDetectionTest(TestCase):
    """Test read-only anomaly detection across financial domains."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.customer = Customer.objects.create(
            name='Anomaly Customer',
            code='ANOM-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('5000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Anomaly Supplier',
            code='ANOM-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_detect_all_returns_structured_report(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        report = AnomalyDetectionEngine.detect_all()
        self.assertIn('scan_timestamp', report)
        self.assertIn('total_anomalies', report)
        self.assertIn('summary', report)
        self.assertIn('anomalies', report)
        self.assertIsInstance(report['anomalies'], list)

    def test_detect_payment_anomalies_empty(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
        self.assertIsInstance(anomalies, list)

    def test_detect_orphan_payment(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
        orphan = [a for a in anomalies if a['anomaly_type'] == 'ORPHAN_PAYMENT']
        self.assertTrue(len(orphan) > 0)

    def test_detect_invoice_anomalies_empty(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        anomalies = AnomalyDetectionEngine.detect_invoice_anomalies()
        self.assertIsInstance(anomalies, list)

    def test_detect_past_due_invoices(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        past_date = self.today - timedelta(days=60)
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='ANOM-INV-001',
            order_date=past_date,
            invoice_date=past_date,
            due_date=past_date - timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
        )
        anomalies = AnomalyDetectionEngine.detect_invoice_anomalies(days_past_due_threshold=30)
        past_due = [a for a in anomalies if a['anomaly_type'] == 'UNPAID_PAST_DUE']
        self.assertTrue(len(past_due) > 0)

    def test_severity_levels_defined(self):
        from core.services.anomaly_detection import Severity
        self.assertEqual(Severity.LOW, 'LOW')
        self.assertEqual(Severity.MEDIUM, 'MEDIUM')
        self.assertEqual(Severity.HIGH, 'HIGH')
        self.assertEqual(Severity.CRITICAL, 'CRITICAL')

    def test_anomaly_types_defined(self):
        from core.services.anomaly_detection import AnomalyType
        self.assertEqual(AnomalyType.ORPHAN_PAYMENT, 'ORPHAN_PAYMENT')
        self.assertEqual(AnomalyType.OVERPAYMENT_EDGE, 'OVERPAYMENT_EDGE')
        self.assertEqual(AnomalyType.UNPAID_PAST_DUE, 'UNPAID_PAST_DUE')

    def test_detect_all_is_read_only(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        initial_customer_count = Customer.objects.count()
        initial_invoice_count = SalesInvoice.objects.count()
        AnomalyDetectionEngine.detect_all()
        self.assertEqual(Customer.objects.count(), initial_customer_count)
        self.assertEqual(SalesInvoice.objects.count(), initial_invoice_count)

    def test_results_bounded(self):
        from core.services.anomaly_detection import AnomalyDetectionEngine
        report = AnomalyDetectionEngine.detect_all()
        self.assertLessEqual(len(report['anomalies']), 200)


# =========================================================================
# 2. Reconciliation Assistance V2
# =========================================================================

class ReconciliationAssistanceV2Test(TestCase):
    """Test smart reconciliation matching with confidence scores."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.customer = Customer.objects.create(
            name='Rec Customer',
            code='REC-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Rec Supplier',
            code='REC-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_suggest_customer_matches_empty(self):
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        suggestions = ReconciliationAssistanceV2.suggest_customer_matches(self.customer)
        self.assertIsInstance(suggestions, list)
        self.assertEqual(len(suggestions), 0)

    def test_suggest_customer_matches_with_data(self):
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='REC-INV-001',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
        )
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('1000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        suggestions = ReconciliationAssistanceV2.suggest_customer_matches(self.customer)
        self.assertEqual(len(suggestions), 1)
        self.assertGreaterEqual(suggestions[0]['confidence_score'], 70)
        self.assertEqual(suggestions[0]['match_type'], 'EXACT')

    def test_suggest_supplier_matches(self):
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        invoice = PurchaseInvoice.objects.create(
            supplier=self.supplier,
            invoice_number='REC-PI-001',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('2000.00'),
            status='CONFIRMED',
        )
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('2000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        suggestions = ReconciliationAssistanceV2.suggest_supplier_matches(self.supplier)
        self.assertEqual(len(suggestions), 1)
        self.assertGreaterEqual(suggestions[0]['confidence_score'], 70)

    def test_get_unresolved_items_returns_structure(self):
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        result = ReconciliationAssistanceV2.get_unresolved_items()
        self.assertIn('orphan_payments', result)
        self.assertIn('partial_settlements', result)
        self.assertIn('summary', result)

    def test_reconcile_invoice_payments(self):
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='REC-INV-002',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('500.00'),
            paid_amount=Decimal('250.00'),
            status='PARTIAL_PAID',
        )
        result = ReconciliationAssistanceV2.reconcile_invoice_payments(invoice)
        self.assertEqual(result['invoice_number'], 'REC-INV-002')
        self.assertEqual(result['remaining'], '250.00')

    def test_no_auto_apply(self):
        """Verify reconciliation V2 does NOT auto-apply matches."""
        from core.services.reconciliation_v2 import ReconciliationAssistanceV2
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='REC-INV-003',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status='CONFIRMED',
        )
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        suggestions = ReconciliationAssistanceV2.suggest_customer_matches(self.customer)
        self.assertEqual(len(suggestions), 1)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('0.00'))


# =========================================================================
# 3. Credit Risk Intelligence
# =========================================================================

class CreditRiskIntelligenceTest(TestCase):
    """Test advisory credit risk scoring and predictive signals."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Risk Customer',
            code='RISK-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.today = date.today()

    def test_assess_customer_risk_returns_structure(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        assessment = CreditRiskIntelligence.assess_customer_risk(self.customer)
        self.assertIn('risk_score', assessment)
        self.assertIn('risk_level', assessment)
        self.assertIn('payment_delay', assessment)
        self.assertIn('utilization_trend', assessment)
        self.assertIn('predictive_signals', assessment)

    def test_low_risk_customer(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        assessment = CreditRiskIntelligence.assess_customer_risk(self.customer)
        self.assertLess(assessment['risk_score'], 40)

    def test_high_utilization_increases_risk(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        old_date = self.today - timedelta(days=60)
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='RISK-INV-001',
            order_date=old_date,
            invoice_date=old_date,
            due_date=old_date + timedelta(days=30),
            total_amount=Decimal('9000.00'),
            status='CONFIRMED',
        )
        assessment = CreditRiskIntelligence.assess_customer_risk(self.customer)
        self.assertGreaterEqual(assessment['risk_score'], 20)

    def test_get_high_risk_customers(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        results = CreditRiskIntelligence.get_high_risk_customers(threshold=60)
        self.assertIsInstance(results, list)

    def test_predict_credit_breach(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        prediction = CreditRiskIntelligence.predict_credit_breach(self.customer, days_ahead=30)
        self.assertIn('will_breach', prediction)
        self.assertIn('projected_balance', prediction)

    def test_predict_no_credit_limit(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        no_limit_customer = Customer.objects.create(
            name='No Limit Customer',
            code='NO-LIMIT',
            balance=Decimal('0.00'),
            credit_limit=Decimal('0.00'),
        )
        prediction = CreditRiskIntelligence.predict_credit_breach(no_limit_customer)
        self.assertFalse(prediction['will_breach'])

    def test_risk_level_categories(self):
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        assessment = CreditRiskIntelligence.assess_customer_risk(self.customer)
        self.assertIn(assessment['risk_level'], ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'MINIMAL'])


# =========================================================================
# 4. Cashflow Observability
# =========================================================================

class CashflowObservabilityTest(TestCase):
    """Test on-demand cashflow visibility."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.customer = Customer.objects.create(
            name='Cash Customer',
            code='CASH-CUST',
            balance=Decimal('0.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Cash Supplier',
            code='CASH-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_cashflow_summary_returns_structure(self):
        from core.services.cashflow_observability import CashflowObservability
        summary = CashflowObservability.get_cashflow_summary(days=30)
        self.assertIn('total_inflow', summary)
        self.assertIn('total_outflow', summary)
        self.assertIn('net_liquidity', summary)
        self.assertIn('daily_breakdown', summary)

    def test_cashflow_empty_data(self):
        from core.services.cashflow_observability import CashflowObservability
        summary = CashflowObservability.get_cashflow_summary(days=30)
        self.assertEqual(summary['total_inflow'], '0.00')
        self.assertEqual(summary['total_outflow'], '0.00')
        self.assertEqual(summary['net_liquidity'], '0.00')

    def test_cashflow_with_payments(self):
        from core.services.cashflow_observability import CashflowObservability
        CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('1000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        summary = CashflowObservability.get_cashflow_summary(days=30)
        self.assertEqual(Decimal(summary['total_inflow']), Decimal('1000.00'))
        self.assertEqual(Decimal(summary['total_outflow']), Decimal('500.00'))
        self.assertEqual(Decimal(summary['net_liquidity']), Decimal('500.00'))

    def test_liquidity_snapshot_returns_structure(self):
        from core.services.cashflow_observability import CashflowObservability
        snapshot = CashflowObservability.get_liquidity_snapshot()
        self.assertIn('total_receivables', snapshot)
        self.assertIn('total_payables', snapshot)
        self.assertIn('net_exposure', snapshot)

    def test_outstanding_exposure_returns_structure(self):
        from core.services.cashflow_observability import CashflowObservability
        exposure = CashflowObservability.get_outstanding_exposure()
        self.assertIn('receivables_aging', exposure)
        self.assertIn('payables_aging', exposure)
        self.assertIn('total_outstanding_receivables', exposure)
        self.assertIn('total_outstanding_payables', exposure)

    def test_daily_breakdown_bounded(self):
        from core.services.cashflow_observability import CashflowObservability
        summary = CashflowObservability.get_cashflow_summary(days=90)
        self.assertLessEqual(len(summary['daily_breakdown']), 14)


# =========================================================================
# 5. Financial Explainability
# =========================================================================

class FinancialExplainabilityTest(TestCase):
    """Test read-only financial trace and explainability."""

    def setUp(self):
        ensure_accounts()
        ensure_payment_account()
        self.customer = Customer.objects.create(
            name='Explain Customer',
            code='EXP-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Explain Supplier',
            code='EXP-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_explain_customer_balance_returns_structure(self):
        from core.services.financial_explainability import FinancialExplainability
        explanation = FinancialExplainability.explain_customer_balance(self.customer)
        self.assertIn('derived_balance', explanation)
        self.assertIn('stored_balance', explanation)
        self.assertIn('formula', explanation)
        self.assertIn('invoice_breakdown', explanation)
        self.assertIn('payment_breakdown', explanation)
        self.assertIn('journal_entries', explanation)
        self.assertIn('explanation', explanation)

    def test_explain_supplier_balance_returns_structure(self):
        from core.services.financial_explainability import FinancialExplainability
        explanation = FinancialExplainability.explain_supplier_balance(self.supplier)
        self.assertIn('derived_balance', explanation)
        self.assertIn('stored_balance', explanation)
        self.assertIn('invoice_breakdown', explanation)
        self.assertIn('payment_breakdown', explanation)

    def test_trace_invoice_returns_structure(self):
        from core.services.financial_explainability import FinancialExplainability
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='EXP-INV-001',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
        )
        trace = FinancialExplainability.trace_invoice(invoice)
        self.assertIn('invoice_number', trace)
        self.assertIn('trace_chain', trace)
        self.assertEqual(trace['entity_type'], 'SalesInvoice')

    def test_trace_payment_returns_structure(self):
        from core.services.financial_explainability import FinancialExplainability
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('500.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        trace = FinancialExplainability.trace_payment(payment)
        self.assertIn('payment_reference', trace)
        self.assertIn('trace_chain', trace)
        self.assertEqual(trace['entity_type'], 'CustomerPayment')

    def test_trace_with_fifo_allocations(self):
        from core.services.financial_explainability import FinancialExplainability
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='EXP-INV-002',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
        )
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            amount=Decimal('1000.00'),
            payment_method='CASH',
            payment_date=self.today,
        )
        PaymentAllocation.objects.create(
            payment=payment,
            invoice=invoice,
            allocated_amount=Decimal('1000.00'),
        )
        trace = FinancialExplainability.trace_invoice(invoice)
        fifo_traces = [t for t in trace['trace_chain'] if t['type'] == 'FIFO_ALLOCATION']
        self.assertEqual(len(fifo_traces), 1)

    def test_explainability_is_read_only(self):
        from core.services.financial_explainability import FinancialExplainability
        initial_count = SalesInvoice.objects.count()
        FinancialExplainability.explain_customer_balance(self.customer)
        self.assertEqual(SalesInvoice.objects.count(), initial_count)


# =========================================================================
# 6. Financial Diagnostics
# =========================================================================

class FinancialDiagnosticsTest(TestCase):
    """Test financial system health diagnostics."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Health Customer',
            code='HEALTH-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='Health Supplier',
            code='HEALTH-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_full_health_check_returns_structure(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        health = FinancialDiagnostics.run_full_health_check()
        self.assertIn('health_score', health)
        self.assertIn('status', health)
        self.assertIn('timestamp', health)
        self.assertIn('components', health)
        self.assertIn('warnings', health)
        self.assertIn('critical', health)

    def test_health_score_range(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        health = FinancialDiagnostics.run_full_health_check()
        self.assertGreaterEqual(health['health_score'], 0)
        self.assertLessEqual(health['health_score'], 100)

    def test_ssot_consistency_check(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        result = FinancialDiagnostics.check_ssot_consistency()
        self.assertIn('total_entities_checked', result)
        self.assertIn('mismatch_count', result)
        self.assertIn('consistency_pct', result)

    def test_ledger_integrity_check(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        result = FinancialDiagnostics.check_ledger_integrity()
        self.assertIn('issues_found', result)
        self.assertIn('critical_count', result)
        self.assertIn('status', result)

    def test_fifo_allocation_integrity_check(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        result = FinancialDiagnostics.check_fifo_allocation_integrity()
        self.assertIn('customer', result)
        self.assertIn('supplier', result)
        self.assertIn('allocation_rate_pct', result)

    def test_credit_enforcement_coverage_check(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        result = FinancialDiagnostics.check_credit_enforcement_coverage()
        self.assertIn('total_active_customers', result)
        self.assertIn('credit_limit_coverage_pct', result)

    def test_reconciliation_lag_check(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        result = FinancialDiagnostics.check_reconciliation_lag()
        self.assertIn('unreconciled_customer_payments', result)
        self.assertIn('unreconciled_supplier_payments', result)
        self.assertIn('status', result)

    def test_health_status_categories(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        health = FinancialDiagnostics.run_full_health_check()
        self.assertIn(health['status'], ['HEALTHY', 'GOOD', 'DEGRADED', 'WARNING', 'CRITICAL'])

    def test_diagnostics_read_only(self):
        from core.services.financial_diagnostics import FinancialDiagnostics
        initial_customer_count = Customer.objects.count()
        FinancialDiagnostics.run_full_health_check()
        self.assertEqual(Customer.objects.count(), initial_customer_count)


# =========================================================================
# API Endpoint Tests
# =========================================================================

class FICLAPITest(TestCase):
    """Test FICL API endpoints."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='API Customer',
            code='API-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.supplier = Supplier.objects.create(
            name='API Supplier',
            code='API-SUPP',
            balance=Decimal('0.00'),
        )
        self.today = date.today()

    def test_anomalies_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/anomalies/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_cashflow_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/cashflow/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_liquidity_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/cashflow/liquidity/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_health_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('health_score', data['data'])

    def test_explain_customer_endpoint(self):
        response = self.client.get(f'/api/v1/financial-intelligence/explain/customer/{self.customer.pk}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_explain_customer_not_found(self):
        response = self.client.get('/api/v1/financial-intelligence/explain/customer/00000000-0000-0000-0000-000000000000/')
        self.assertEqual(response.status_code, 404)

    def test_credit_risk_assess_endpoint(self):
        response = self.client.get(f'/api/v1/financial-intelligence/credit-risk/assess/{self.customer.pk}/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        inner = result.get('data', {})
        self.assertIn('risk_score', inner)

    def test_reconciliation_suggest_customer_endpoint(self):
        response = self.client.get(f'/api/v1/financial-intelligence/reconciliation/suggest/customer/{self.customer.pk}/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_unresolved_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/reconciliation/unresolved/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_health_ssot_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/ssot/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_health_ledger_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/ledger/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_health_fifo_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/fifo/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_health_credit_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/credit/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_health_reconciliation_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/reconciliation/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_anomalies_payments_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/anomalies/payments/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_anomalies_invoices_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/anomalies/invoices/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_anomalies_ledger_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/anomalies/ledger/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_exposure_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/cashflow/exposure/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_high_risk_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/credit-risk/high-risk/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])

    def test_predict_credit_breach_endpoint(self):
        response = self.client.get(f'/api/v1/financial-intelligence/credit-risk/predict/{self.customer.pk}/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        inner = result.get('data', {})
        self.assertIn('will_breach', inner)

    def test_health_endpoint(self):
        response = self.client.get('/api/v1/financial-intelligence/health/')
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        inner = result.get('data', {})
        self.assertIn('health_score', inner)
