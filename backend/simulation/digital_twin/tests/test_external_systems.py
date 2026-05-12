"""
Tests for Phase — External System Integration Simulators.
Deterministic via seed parameter. No real randomness.
"""
import unittest

from simulation.digital_twin.external.banking_api import (
    BankingAPISimulator,
)
from simulation.digital_twin.external.coordinator import (
    ExternalSystemCoordinator,
)
from simulation.digital_twin.external.credit_api import (
    CustomerCreditAPISimulator,
)
from simulation.digital_twin.external.payment_gateway import (
    PaymentGatewaySimulator,
)
from simulation.digital_twin.external.supplier_system import (
    SupplierSystemSimulator,
)
from simulation.digital_twin.external.tax_authority import (
    TaxAuthorityAPISimulator,
)


class TestBankingAPISimulator(unittest.TestCase):
    def setUp(self):
        self.bank = BankingAPISimulator(seed=42)

    def test_process_payment_success(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = bank.process_payment(
            amount=1000.0, currency='AFN', target_account='ACC-001'
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['settled_amount'], 1000.0)
        self.assertEqual(result['currency'], 'AFN')
        self.assertEqual(result['status'], 'settled')
        self.assertIn('payment_id', result)
        self.assertEqual(result['payment_id'], 'PAY-000001')

    def test_process_payment_timeout(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 1.0, 'failure_modes': ['timeout']},
            seed=42,
        )
        result = bank.process_payment(
            amount=500.0, currency='AFN', target_account='ACC-002'
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'timeout')

    def test_process_payment_reversal(self):
        bank = BankingAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['reversal'],
            },
            seed=42,
        )
        result = bank.process_payment(
            amount=250.0, currency='USD', target_account='ACC-003'
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'reversal')
        self.assertEqual(result['reversal_amount'], 250.0)

    def test_reverse_payment(self):
        result = self.bank.reverse_payment(payment_id='PAY-000001')
        self.assertTrue(result['success'])
        self.assertTrue(result['reversed'])
        self.assertEqual(result['payment_id'], 'PAY-000001')

    def test_health_tracking(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        bank.process_payment(100.0, 'AFN', 'ACC-001')
        bank.process_payment(200.0, 'USD', 'ACC-002')
        health = bank.get_health()
        self.assertEqual(health['name'], 'BankingAPI')
        self.assertEqual(health['total_requests'], 2)
        self.assertEqual(health['failure_count'], 0)
        self.assertEqual(health['success_rate'], 100.0)

    def test_request_history(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        bank.process_payment(100.0, 'AFN', 'ACC-001')
        history = bank.get_request_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['operation'], 'process_payment')
        self.assertTrue(history[0]['response']['success'])

    def test_reset(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        bank.process_payment(100.0, 'AFN', 'ACC-001')
        bank.reset()
        health = bank.get_health()
        self.assertEqual(health['total_requests'], 0)
        self.assertEqual(health['failure_count'], 0)

    def test_clear(self):
        bank = BankingAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        bank.process_payment(100.0, 'AFN', 'ACC-001')
        bank.clear()
        self.assertEqual(len(bank.get_request_history()), 0)
        health = bank.get_health()
        self.assertEqual(health['total_requests'], 0)

    def test_deterministic_seed(self):
        bank1 = BankingAPISimulator(seed=42)
        bank2 = BankingAPISimulator(seed=42)
        r1 = bank1.process_payment(100.0, 'AFN', 'ACC-001')
        r2 = bank2.process_payment(100.0, 'AFN', 'ACC-001')
        self.assertEqual(r1, r2)


class TestPaymentGatewaySimulator(unittest.TestCase):
    def setUp(self):
        self.gateway = PaymentGatewaySimulator(seed=42)

    def test_authorize_success(self):
        gw = PaymentGatewaySimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = gw.authorize(
            amount=500.0, method='credit_card', currency='AFN'
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['approved_amount'], 500.0)
        self.assertIn('auth_code', result)

    def test_authorize_partial_approval(self):
        gw = PaymentGatewaySimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['partial_approval'],
            },
            seed=42,
        )
        result = gw.authorize(
            amount=1000.0, method='credit_card', currency='AFN'
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['approved_amount'], 500.0)

    def test_capture_success(self):
        gw = PaymentGatewaySimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = gw.capture(
            auth_code='AUTH-000001', amount=500.0
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['captured_amount'], 500.0)
        self.assertIn('capture_id', result)

    def test_capture_split_handling(self):
        gw = PaymentGatewaySimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['split_handling'],
            },
            seed=42,
        )
        result = gw.capture(
            auth_code='AUTH-000001', amount=1000.0
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['captured_amount'], 800.0)

    def test_refund_success(self):
        gw = PaymentGatewaySimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = gw.refund(
            transaction_id='CAP-000001', amount=200.0
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['refunded_amount'], 200.0)
        self.assertEqual(result['transaction_id'], 'CAP-000001')

    def test_authorize_counter_increment(self):
        gw = PaymentGatewaySimulator(
            config={'failure_rate': 0.0}, seed=99
        )
        r1 = gw.authorize(100.0, 'card', 'AFN')
        r2 = gw.authorize(200.0, 'card', 'USD')
        self.assertEqual(r1['auth_code'], 'AUTH-000001')
        self.assertEqual(r2['auth_code'], 'AUTH-000002')


class TestSupplierSystemSimulator(unittest.TestCase):
    def setUp(self):
        self.supplier = SupplierSystemSimulator(seed=42)

    def test_submit_po_success(self):
        sup = SupplierSystemSimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = sup.submit_po(
            po_data={
                'item': 'Medicine A',
                'quantity': 100,
                'supplier': 'PharmaCo',
            }
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'confirmed')
        self.assertIn('po_id', result)

    def test_submit_po_delay(self):
        sup = SupplierSystemSimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['delay'],
            },
            seed=42,
        )
        result = sup.submit_po(
            po_data={'item': 'Medicine B', 'quantity': 50}
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'pending')

    def test_submit_po_rejection(self):
        sup = SupplierSystemSimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['rejection'],
            },
            seed=42,
        )
        result = sup.submit_po(
            po_data={'item': 'Medicine C', 'quantity': 200}
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'rejected')

    def test_check_status(self):
        sup = SupplierSystemSimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        po_result = sup.submit_po(
            po_data={'item': 'Medicine A', 'quantity': 100}
        )
        po_id = po_result['po_id']
        status = sup.check_status(po_id=po_id)
        self.assertTrue(status['success'])
        self.assertEqual(status['status'], 'confirmed')

    def test_check_status_unknown(self):
        result = self.supplier.check_status(po_id='PO-NONEXIST')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'unknown')


class TestCustomerCreditAPISimulator(unittest.TestCase):
    def setUp(self):
        self.credit = CustomerCreditAPISimulator(seed=42)

    def test_check_credit_success(self):
        cr = CustomerCreditAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = cr.check_credit(
            customer_id='CUST-001', amount=5000.0
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['approved_limit'], 5000.0)
        self.assertIn('approval_code', result)

    def test_check_credit_downtime(self):
        cr = CustomerCreditAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['downtime'],
            },
            seed=42,
        )
        result = cr.check_credit(
            customer_id='CUST-002', amount=3000.0
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'downtime')

    def test_check_credit_rejection(self):
        cr = CustomerCreditAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['rejection'],
            },
            seed=42,
        )
        result = cr.check_credit(
            customer_id='CUST-003', amount=10000.0
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'rejection')
        self.assertEqual(result['reason'], 'insufficient_credit')

    def test_hold_credit(self):
        cr = CustomerCreditAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = cr.hold_credit(
            customer_id='CUST-001', amount=2000.0
        )
        self.assertTrue(result['success'])
        self.assertIn('hold_id', result)
        self.assertEqual(result['held_amount'], 2000.0)

    def test_release_hold(self):
        cr = CustomerCreditAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        hold = cr.hold_credit('CUST-001', 2000.0)
        hold_id = hold['hold_id']
        result = cr.release_hold(hold_id=hold_id)
        self.assertTrue(result['success'])
        self.assertTrue(result['released'])

    def test_release_nonexistent_hold(self):
        result = self.credit.release_hold(hold_id='HOLD-NONEXIST')
        self.assertTrue(result['success'])
        self.assertFalse(result['released'])


class TestTaxAuthorityAPISimulator(unittest.TestCase):
    def setUp(self):
        self.tax = TaxAuthorityAPISimulator(seed=42)

    def test_validate_return_success(self):
        tx = TaxAuthorityAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = tx.validate_return(
            tax_data={'period': '2024-Q1', 'amount': 15000.0}
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['is_valid'])
        self.assertIn('validation_id', result)

    def test_validate_return_downtime(self):
        tx = TaxAuthorityAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['downtime'],
            },
            seed=42,
        )
        result = tx.validate_return(
            tax_data={'period': '2024-Q2', 'amount': 20000.0}
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'downtime')

    def test_submit_return_posted(self):
        tx = TaxAuthorityAPISimulator(
            config={'failure_rate': 0.0}, seed=42
        )
        result = tx.submit_return(
            tax_data={'period': '2024-Q1', 'amount': 15000.0}
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'posted')
        self.assertIn('submission_id', result)

    def test_submit_return_deferred(self):
        tx = TaxAuthorityAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['deferred'],
            },
            seed=42,
        )
        result = tx.submit_return(
            tax_data={'period': '2024-Q3', 'amount': 25000.0}
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'deferred')
        self.assertIn('deferred_until', result)

    def test_validate_return_deferred_soft_failure(self):
        tx = TaxAuthorityAPISimulator(
            config={
                'failure_rate': 1.0,
                'failure_modes': ['deferred'],
            },
            seed=42,
        )
        result = tx.validate_return(
            tax_data={'period': '2024-Q4', 'amount': 5000.0}
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['is_valid'])
        self.assertTrue(result.get('deferred', False))


class TestExternalSystemCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = ExternalSystemCoordinator(seed=42)

    def test_execute_with_retry_success_on_first_try(self):
        coord = ExternalSystemCoordinator(
            config={
                'banking': {'failure_rate': 0.0},
            },
            seed=42,
        )
        result = coord.execute_with_retry(
            system='banking',
            operation='process_payment',
            params={
                'amount': 500.0,
                'currency': 'AFN',
                'target_account': 'ACC-001',
            },
            max_retries=3,
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['final'])
        self.assertEqual(result['attempts'], 1)
        self.assertTrue(result['response']['success'])

    def test_execute_with_retry_all_fail(self):
        coord = ExternalSystemCoordinator(
            config={
                'banking': {
                    'failure_rate': 1.0,
                    'failure_modes': ['timeout'],
                },
            },
            seed=42,
        )
        result = coord.execute_with_retry(
            system='banking',
            operation='process_payment',
            params={
                'amount': 500.0,
                'currency': 'AFN',
                'target_account': 'ACC-001',
            },
            max_retries=2,
        )
        self.assertFalse(result['success'])
        self.assertTrue(result['final'])
        self.assertEqual(result['attempts'], 3)

    def test_execute_with_retry_unknown_system(self):
        result = self.coordinator.execute_with_retry(
            system='nonexistent',
            operation='process_payment',
            params={'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
            max_retries=3,
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Unknown system: nonexistent')

    def test_execute_with_retry_unknown_operation(self):
        result = self.coordinator.execute_with_retry(
            system='banking',
            operation='nonexistent_op',
            params={},
            max_retries=3,
        )
        self.assertFalse(result['success'])
        self.assertEqual(
            result['error'], 'Unknown operation: nonexistent_op'
        )

    def test_handle_failure_timeout(self):
        compensation = self.coordinator.handle_failure(
            system='banking',
            request={'amount': 100.0},
            response={'success': False, 'error': 'timeout'},
        )
        self.assertEqual(compensation['system'], 'banking')
        self.assertEqual(compensation['failure_mode'], 'timeout')
        self.assertEqual(compensation['compensation_action'], 'retry_later')

    def test_handle_failure_reversal(self):
        compensation = self.coordinator.handle_failure(
            system='banking',
            request={'amount': 500.0},
            response={
                'success': False,
                'error': 'reversal',
                'reversal_amount': 500.0,
            },
        )
        self.assertEqual(compensation['failure_mode'], 'reversal')
        self.assertEqual(
            compensation['compensation_action'], 'notify_accounting'
        )

    def test_handle_failure_delay(self):
        compensation = self.coordinator.handle_failure(
            system='supplier',
            request={},
            response={'success': True, 'status': 'pending'},
        )
        self.assertEqual(compensation['failure_mode'], 'delay')
        self.assertEqual(compensation['compensation_action'], 'escalate')

    def test_handle_failure_deferred(self):
        compensation = self.coordinator.handle_failure(
            system='tax',
            request={},
            response={
                'success': True,
                'status': 'deferred',
                'deferred_until': 10,
            },
        )
        self.assertEqual(compensation['failure_mode'], 'deferred')
        self.assertEqual(
            compensation['compensation_action'], 'schedule_retry'
        )

    def test_handle_failure_insufficient_credit(self):
        compensation = self.coordinator.handle_failure(
            system='credit',
            request={'amount': 10000.0},
            response={
                'success': False,
                'error': 'rejection',
                'reason': 'insufficient_credit',
            },
        )
        self.assertEqual(compensation['failure_mode'], 'insufficient_credit')
        self.assertEqual(
            compensation['compensation_action'], 'request_alternative'
        )

    def test_handle_failure_partial_approval(self):
        compensation = self.coordinator.handle_failure(
            system='payment_gateway',
            request={'amount': 1000.0},
            response={
                'success': True,
                'approved_amount': 500.0,
            },
        )
        self.assertEqual(compensation['failure_mode'], 'partial_approval')
        self.assertEqual(
            compensation['compensation_action'], 'adjust_order'
        )

    def test_handle_failure_split_handling(self):
        compensation = self.coordinator.handle_failure(
            system='payment_gateway',
            request={'amount': 1000.0},
            response={
                'success': True,
                'captured_amount': 800.0,
            },
        )
        self.assertEqual(compensation['failure_mode'], 'split_handling')
        self.assertEqual(
            compensation['compensation_action'], 'reconcile_difference'
        )

    def test_get_system_health(self):
        coord = ExternalSystemCoordinator(seed=42)
        health = coord.get_system_health()
        self.assertIn('banking', health)
        self.assertIn('payment_gateway', health)
        self.assertIn('supplier', health)
        self.assertIn('credit', health)
        self.assertIn('tax', health)
        for name, h in health.items():
            self.assertEqual(h['total_requests'], 0)
            self.assertEqual(h['success_rate'], 100.0)

    def test_get_system_health_after_operations(self):
        coord = ExternalSystemCoordinator(
            config={
                'banking': {'failure_rate': 0.0},
                'payment_gateway': {'failure_rate': 0.0},
            },
            seed=42,
        )
        coord.execute_with_retry(
            'banking', 'process_payment',
            {'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
        )
        coord.execute_with_retry(
            'payment_gateway', 'authorize',
            {'amount': 200.0, 'method': 'card', 'currency': 'AFN'},
        )
        health = coord.get_system_health()
        self.assertEqual(health['banking']['total_requests'], 1)
        self.assertEqual(health['payment_gateway']['total_requests'], 1)

    def test_reset(self):
        coord = ExternalSystemCoordinator(seed=42)
        coord.execute_with_retry(
            'banking', 'process_payment',
            {'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
        )
        coord.reset()
        health = coord.get_system_health()
        for h in health.values():
            self.assertEqual(h['total_requests'], 0)

    def test_clear(self):
        coord = ExternalSystemCoordinator(seed=42)
        coord.execute_with_retry(
            'banking', 'process_payment',
            {'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
        )
        coord.clear()
        health = coord.get_system_health()
        for h in health.values():
            self.assertEqual(h['total_requests'], 0)

    def test_handle_failure_unknown_error(self):
        compensation = self.coordinator.handle_failure(
            system='banking',
            request={},
            response={'success': False, 'error': 'bizarro_error'},
        )
        self.assertEqual(compensation['failure_mode'], 'bizarro_error')
        self.assertEqual(
            compensation['compensation_action'], 'manual_review'
        )

    def test_deterministic_coordinator(self):
        c1 = ExternalSystemCoordinator(seed=42)
        c2 = ExternalSystemCoordinator(seed=42)
        r1 = c1.execute_with_retry(
            'banking', 'process_payment',
            {'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
        )
        r2 = c2.execute_with_retry(
            'banking', 'process_payment',
            {'amount': 100.0, 'currency': 'AFN', 'target_account': 'ACC'},
        )
        self.assertEqual(r1, r2)
