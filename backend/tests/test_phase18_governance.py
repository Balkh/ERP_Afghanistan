"""Tests for Phase 18: Financial Operating System — Governance Lock.

Covers:
1. DecisionRecord model (bounded storage, lifecycle)
2. Financial Policy Engine (deterministic rules)
3. Control Tower API endpoints
4. SSOT conflict protection mode
5. Enforcement lifecycle
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from sales.models import Customer, SalesInvoice, CustomerPayment
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment
from accounting.models import Account
from core.models.decision_record import DecisionRecord
from core.services.financial_policy_engine import FinancialPolicyEngine


def ensure_accounts():
    accounts_data = [
        ('1200', 'Accounts Receivable', 'ASSET'),
        ('2100', 'Accounts Payable', 'LIABILITY'),
        ('4100', 'Sales Revenue', 'REVENUE'),
        ('1010', 'Cash', 'ASSET'),
    ]
    for code, name, acct_type in accounts_data:
        Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': acct_type, 'is_active': True},
        )


# =========================================================================
# 1. DecisionRecord Model Tests
# =========================================================================

class DecisionRecordModelTest(TestCase):
    """Test DecisionRecord model functionality."""

    def test_create_decision_record(self):
        record = DecisionRecord.objects.create(
            entity_type='Customer',
            entity_id='test-uuid',
            risk_score=50,
            decision_type='WARN',
            triggered_rules=['CREDIT_WARN_80'],
            explanation='Credit utilization at 85%',
        )
        self.assertEqual(record.decision_type, 'WARN')
        self.assertEqual(record.lifecycle_state, 'ACTIVE')
        self.assertEqual(record.risk_score, 50)

    def test_decision_record_str(self):
        record = DecisionRecord.objects.create(
            entity_type='Customer',
            entity_id='test-uuid',
            decision_type='HARD_BLOCK',
        )
        self.assertIn('HARD_BLOCK', str(record))
        self.assertIn('Customer', str(record))

    def test_enforce_bounded_storage(self):
        # Create 250 records
        for i in range(250):
            DecisionRecord.objects.create(
                entity_type='Customer',
                entity_id=f'test-{i}',
                decision_type='ALLOW',
            )
        DecisionRecord.enforce_bounded_storage(max_records=200)
        self.assertLessEqual(DecisionRecord.objects.count(), 200)

    def test_supersede_decision(self):
        customer_id = 'cust-001'
        r1 = DecisionRecord.objects.create(
            entity_type='Customer', entity_id=customer_id,
            decision_type='WARN',
        )
        r2 = DecisionRecord.objects.create(
            entity_type='Customer', entity_id=customer_id,
            decision_type='HARD_BLOCK',
        )
        DecisionRecord.supersede_decision('Customer', customer_id, r2.id)
        r1.refresh_from_db()
        self.assertEqual(r1.lifecycle_state, 'SUPERSEDED')
        r2.refresh_from_db()
        self.assertEqual(r2.lifecycle_state, 'ACTIVE')

    def test_expire_old_decisions(self):
        old_record = DecisionRecord.objects.create(
            entity_type='Customer', entity_id='old-cust',
            decision_type='WARN',
            timestamp=timezone.now() - timedelta(hours=48),
        )
        DecisionRecord.expire_old_decisions(hours=24)
        old_record.refresh_from_db()
        self.assertEqual(old_record.lifecycle_state, 'EXPIRED')

    def test_no_duplicate_active_decisions(self):
        """After supersede, only one active decision per entity."""
        customer_id = 'cust-dup'
        for i in range(5):
            r = DecisionRecord.objects.create(
                entity_type='Customer', entity_id=customer_id,
                decision_type='WARN',
            )
            DecisionRecord.supersede_decision('Customer', customer_id, r.id)
        active_count = DecisionRecord.objects.filter(
            entity_type='Customer',
            entity_id=customer_id,
            lifecycle_state='ACTIVE',
        ).count()
        self.assertEqual(active_count, 1)


# =========================================================================
# 2. Financial Policy Engine Tests
# =========================================================================

class FinancialPolicyEngineTest(TestCase):
    """Test deterministic policy rule evaluation."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='Policy Customer',
            code='POL-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.today = date.today()

    def test_evaluate_customer_allow(self):
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertEqual(decision.decision_type, 'ALLOW')
        self.assertFalse(decision.requires_review)

    def test_evaluate_customer_hard_block_credit(self):
        # Create invoice that pushes utilization above 95%
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='POL-INV-001',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('9600.00'),
            status='CONFIRMED',
        )
        # Sync stored balance to avoid SSOT conflict triggering safe mode
        self.customer.balance = Decimal('9600.00')
        self.customer.save()
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertEqual(decision.decision_type, 'HARD_BLOCK')
        self.assertIn('CREDIT_SAFETY_95', decision.triggered_rules)

    def test_evaluate_customer_warn_credit(self):
        # Create invoice that pushes utilization above 80% but below 95%
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='POL-INV-002',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('8500.00'),
            status='CONFIRMED',
        )
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertIn(decision.decision_type, ('WARN', 'HARD_BLOCK'))

    def test_evaluate_invoice_creation_allow(self):
        decision = FinancialPolicyEngine.evaluate_invoice_creation(
            self.customer, Decimal('1000.00')
        )
        self.assertEqual(decision.decision_type, 'ALLOW')

    def test_evaluate_invoice_creation_hard_block(self):
        # Existing balance + new invoice exceeds 95%
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='POL-INV-003',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('9000.00'),
            status='CONFIRMED',
        )
        self.customer.balance = Decimal('9000.00')
        self.customer.save()
        decision = FinancialPolicyEngine.evaluate_invoice_creation(
            self.customer, Decimal('1000.00')
        )
        self.assertEqual(decision.decision_type, 'HARD_BLOCK')

    def test_evaluate_payment_allow(self):
        decision = FinancialPolicyEngine.evaluate_payment(
            Decimal('500.00'), Decimal('1000.00')
        )
        self.assertEqual(decision.decision_type, 'ALLOW')

    def test_evaluate_payment_overpayment(self):
        decision = FinancialPolicyEngine.evaluate_payment(
            Decimal('1500.00'), Decimal('1000.00')
        )
        self.assertEqual(decision.decision_type, 'SOFT_BLOCK')
        self.assertIn('OVERPAYMENT_PREVENTION', decision.triggered_rules)

    def test_evaluate_system_health(self):
        decision = FinancialPolicyEngine.evaluate_system_health()
        self.assertIn(decision.decision_type, ('ALLOW', 'WARN'))
        self.assertIsInstance(decision.risk_score, int)

    def test_log_decision(self):
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        record = FinancialPolicyEngine.log_decision(
            entity_type='Customer',
            entity_id=str(self.customer.pk),
            decision=decision,
        )
        self.assertIsNotNone(record.id)
        self.assertEqual(record.decision_type, decision.decision_type)

    def test_re_evaluate_all(self):
        result = FinancialPolicyEngine.re_evaluate_all()
        self.assertIn('evaluated_count', result)
        self.assertIn('system_decision', result)
        self.assertIn('timestamp', result)

    def test_blocked_customer_hard_block(self):
        self.customer.status = 'BLOCKED'
        self.customer.save()
        decision = FinancialPolicyEngine.evaluate_invoice_creation(
            self.customer, Decimal('100.00')
        )
        self.assertEqual(decision.decision_type, 'HARD_BLOCK')
        self.assertIn('CUSTOMER_BLOCKED', decision.triggered_rules)

    def test_decision_risk_score_range(self):
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertGreaterEqual(decision.risk_score, 0)
        self.assertLessEqual(decision.risk_score, 100)


# =========================================================================
# 3. Control Tower API Tests
# =========================================================================

class ControlTowerAPITest(TestCase):
    """Test Control Tower API endpoints."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='CT Customer',
            code='CT-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )

    def test_summary_endpoint(self):
        response = self.client.get('/api/financial/control-tower/summary/')
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', response.json())
        self.assertIn('health_score', data)
        self.assertIn('anomaly_index', data)
        self.assertIn('safe_mode', data)

    def test_alerts_endpoint(self):
        response = self.client.get('/api/financial/control-tower/alerts/')
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', response.json())
        self.assertIn('active_alerts', data)
        self.assertIn('total_alerts', data)

    def test_decisions_endpoint(self):
        response = self.client.get('/api/financial/control-tower/decisions/')
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', response.json())
        self.assertIn('decisions', data)

    def test_reevaluate_endpoint(self):
        response = self.client.post('/api/financial/control-tower/re-evaluate/')
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', response.json())
        self.assertIn('evaluated_count', data)
        self.assertIn('system_decision', data)


# =========================================================================
# 4. SSOT Conflict Protection Tests
# =========================================================================

class SSOTConflictProtectionTest(TestCase):
    """Test SSOT conflict detection and safe mode."""

    def setUp(self):
        self.customer = Customer.objects.create(
            name='SSOT Customer',
            code='SSOT-CUST',
            balance=Decimal('0.00'),
            credit_limit=Decimal('10000.00'),
        )
        self.today = date.today()

    def test_no_conflict_when_balances_match(self):
        """When stored == derived, no SSOT conflict."""
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertFalse(decision.safe_mode)
        self.assertNotIn('SSOT_CONFLICT_SAFE_MODE', decision.triggered_rules)

    def test_safe_mode_when_balances_diverge(self):
        """When stored != derived, system enters safe mode."""
        self.customer.balance = Decimal('5000.00')
        self.customer.save()
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='SSOT-INV-001',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='CONFIRMED',
        )
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertTrue(decision.safe_mode)
        self.assertIn('SSOT_CONFLICT_SAFE_MODE', decision.triggered_rules)

    def test_safe_mode_downgrades_hard_block_to_warn(self):
        """In safe mode, HARD_BLOCK is downgraded to WARN."""
        self.customer.balance = Decimal('5000.00')
        self.customer.save()
        SalesInvoice.objects.create(
            customer=self.customer,
            invoice_number='SSOT-INV-002',
            order_date=self.today,
            invoice_date=self.today,
            due_date=self.today + timedelta(days=30),
            total_amount=Decimal('9600.00'),
            status='CONFIRMED',
        )
        decision = FinancialPolicyEngine.evaluate_customer(self.customer)
        self.assertNotEqual(decision.decision_type, 'HARD_BLOCK')
        self.assertIn(decision.decision_type, ('WARN', 'SOFT_BLOCK'))


# =========================================================================
# 5. Enforcement Lifecycle Tests
# =========================================================================

class EnforcementLifecycleTest(TestCase):
    """Test decision lifecycle states."""

    def test_lifecycle_states_exist(self):
        states = [s[0] for s in DecisionRecord.LIFECYCLE_STATES]
        self.assertIn('PENDING', states)
        self.assertIn('ACTIVE', states)
        self.assertIn('RESOLVED', states)
        self.assertIn('SUPERSEDED', states)
        self.assertIn('EXPIRED', states)

    def test_decision_types_exist(self):
        types = [t[0] for t in DecisionRecord.DECISION_TYPES]
        self.assertIn('ALLOW', types)
        self.assertIn('WARN', types)
        self.assertIn('SOFT_BLOCK', types)
        self.assertIn('HARD_BLOCK', types)
        self.assertIn('ESCALATE_MANAGER', types)

    def test_new_decision_supersedes_old(self):
        """New evaluation supersedes older decision for same entity."""
        customer_id = 'lifecycle-cust'
        r1 = DecisionRecord.objects.create(
            entity_type='Customer', entity_id=customer_id,
            decision_type='WARN', lifecycle_state='ACTIVE',
        )
        r2 = DecisionRecord.objects.create(
            entity_type='Customer', entity_id=customer_id,
            decision_type='HARD_BLOCK', lifecycle_state='ACTIVE',
        )
        DecisionRecord.supersede_decision('Customer', customer_id, r2.id)
        r1.refresh_from_db()
        r2.refresh_from_db()
        self.assertEqual(r1.lifecycle_state, 'SUPERSEDED')
        self.assertEqual(r2.lifecycle_state, 'ACTIVE')
