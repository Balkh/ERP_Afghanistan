"""
Tests for Enterprise Logging & Observability System.
"""
import json
import logging
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from core.logging.logger import Logger
from core.logging.audit import EventType, AuditEventLogger, audit_logger
from core.logging.formatters import JSONFormatter, HumanFormatter
from core.logging.config import logging_config, is_production
from core.logging.financial_trace import financial_trace
from core.logging.inventory_trace import inventory_trace

User = get_user_model()


class LoggerTests(TestCase):
    """Test central logger factory."""

    def test_get_logger_returns_instance(self):
        """Test get_logger returns a logging.Logger instance."""
        logger = Logger.get('erp.test')
        self.assertIsInstance(logger, logging.Logger)

    def test_get_logger_caches(self):
        """Test logger instances are cached."""
        logger1 = Logger.get('erp.cache_test')
        logger2 = Logger.get('erp.cache_test')
        self.assertIs(logger1, logger2)

    def test_specialized_loggers(self):
        """Test specialized logger getters."""
        self.assertIsInstance(Logger.audit(), logging.Logger)
        self.assertIsInstance(Logger.financial(), logging.Logger)
        self.assertIsInstance(Logger.inventory(), logging.Logger)
        self.assertIsInstance(Logger.security(), logging.Logger)
        self.assertIsInstance(Logger.api(), logging.Logger)
        self.assertIsInstance(Logger.performance(), logging.Logger)
        self.assertIsInstance(Logger.error(), logging.Logger)


class FormatterTests(TestCase):
    """Test logging formatters."""

    def test_json_formatter_outputs_valid_json(self):
        """Test JSONFormatter produces valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='erp.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        self.assertIn('timestamp', data)
        self.assertIn('level', data)
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Test message')

    def test_json_formatter_includes_request_id(self):
        """Test JSONFormatter includes request_id when present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='erp.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None,
        )
        record.request_id = 'test-uuid-123'
        result = formatter.format(record)
        data = json.loads(result)
        self.assertEqual(data['request_id'], 'test-uuid-123')

    def test_json_formatter_includes_exception(self):
        """Test JSONFormatter includes exception info."""
        formatter = JSONFormatter()
        try:
            raise ValueError('Test error')
        except ValueError:
            import sys
            record = logging.LogRecord(
                name='erp.test',
                level=logging.ERROR,
                pathname='test.py',
                lineno=1,
                msg='Error occurred',
                args=(),
                exc_info=sys.exc_info(),
            )
            result = formatter.format(record)
            data = json.loads(result)
            self.assertIn('exception', data)
            self.assertEqual(data['exception']['type'], 'ValueError')

    def test_human_formatter(self):
        """Test HumanFormatter produces human-readable output."""
        formatter = HumanFormatter()
        record = logging.LogRecord(
            name='erp.test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        self.assertIn('Test message', result)
        self.assertIn('INFO', result)


class AuditEventTests(TestCase):
    """Test audit event logging."""

    def test_event_types_exist(self):
        """Test all event type constants exist."""
        self.assertTrue(hasattr(EventType, 'AUTH_LOGIN'))
        self.assertTrue(hasattr(EventType, 'JOURNAL_POST'))
        self.assertTrue(hasattr(EventType, 'STOCK_IN'))
        self.assertTrue(hasattr(EventType, 'PAYMENT_RECEIVED'))
        self.assertTrue(hasattr(EventType, 'SYSTEM_ERROR'))

    def test_log_event_returns_data(self):
        """Test log_event returns structured data."""
        data = AuditEventLogger.log_event(
            event_type=EventType.AUTH_LOGIN,
            user='testuser',
            action='login',
            status='SUCCESS',
        )
        self.assertEqual(data['event_type'], EventType.AUTH_LOGIN)
        self.assertEqual(data['user'], 'testuser')
        self.assertEqual(data['status'], 'SUCCESS')

    def test_log_financial_event(self):
        """Test financial event logging."""
        data = AuditEventLogger.log_financial(
            event_type=EventType.JOURNAL_POST,
            journal_id='je-123',
            debit_total=1000,
            credit_total=1000,
        )
        self.assertEqual(data['journal_id'], 'je-123')
        self.assertTrue(data['balanced'])

    def test_log_inventory_event(self):
        """Test inventory event logging."""
        data = AuditEventLogger.log_inventory(
            event_type=EventType.STOCK_IN,
            product_id='prod-123',
            warehouse_id='wh-1',
            quantity=100,
        )
        self.assertEqual(data['product_id'], 'prod-123')
        self.assertEqual(data['quantity'], 100)

    def test_log_security_event_success(self):
        """Test security event logging - success."""
        data = AuditEventLogger.log_security(
            event_type=EventType.AUTH_LOGIN,
            user='testuser',
            ip_address='192.168.1.1',
            success=True,
        )
        self.assertTrue(data['success'])

    def test_log_security_event_failure(self):
        """Test security event logging - failure."""
        data = AuditEventLogger.log_security(
            event_type=EventType.AUTH_LOGIN_FAILED,
            user='testuser',
            ip_address='192.168.1.1',
            success=False,
        )
        self.assertFalse(data['success'])


class FinancialTraceTests(TestCase):
    """Test financial trace logging."""

    def test_log_journal_create(self):
        """Test journal creation trace."""
        financial_trace.log_journal_create('je-001', user='admin')

    def test_log_journal_post_balanced(self):
        """Test balanced journal posting trace."""
        financial_trace.log_journal_post(
            journal_id='je-001',
            debit_total=1000,
            credit_total=1000,
        )

    def test_log_journal_post_unbalanced(self):
        """Test unbalanced journal posting trace."""
        financial_trace.log_journal_post(
            journal_id='je-002',
            debit_total=1000,
            credit_total=900,
        )

    def test_log_journal_reverse(self):
        """Test journal reversal trace."""
        financial_trace.log_journal_reverse('je-003', 'je-001')

    def test_log_rollback(self):
        """Test rollback trace."""
        financial_trace.log_rollback('je-001', 'Insufficient funds')


class InventoryTraceTests(TestCase):
    """Test inventory trace logging."""

    def test_log_stock_in(self):
        """Test stock-in trace."""
        inventory_trace.log_stock_in(
            product_id='prod-1',
            quantity=100,
            warehouse_id='wh-1',
        )

    def test_log_stock_out(self):
        """Test stock-out trace."""
        inventory_trace.log_stock_out(
            product_id='prod-1',
            quantity=50,
            warehouse_id='wh-1',
        )

    def test_log_adjustment(self):
        """Test stock adjustment trace."""
        inventory_trace.log_adjustment(
            product_id='prod-1',
            quantity=-10,
            warehouse_id='wh-1',
            reason='Damaged goods',
        )

    def test_log_transfer(self):
        """Test warehouse transfer trace."""
        inventory_trace.log_transfer(
            product_id='prod-1',
            quantity=25,
            source_warehouse='wh-1',
            dest_warehouse='wh-2',
        )

    def test_log_fefo_allocation(self):
        """Test FEFO allocation trace."""
        inventory_trace.log_fefo_allocation(
            product_id='prod-1',
            quantity=10,
            batch_id='batch-1',
            warehouse_id='wh-1',
        )

    def test_log_fifo_allocation(self):
        """Test FIFO allocation trace."""
        inventory_trace.log_fifo_allocation(
            product_id='prod-1',
            quantity=10,
            batch_id='batch-1',
            warehouse_id='wh-1',
        )

    def test_log_stock_failure(self):
        """Test stock failure trace."""
        inventory_trace.log_stock_failure(
            product_id='prod-1',
            warehouse_id='wh-1',
            error='Insufficient stock',
        )


class MiddlewareTests(TestCase):
    """Test observability middleware."""

    def setUp(self):
        self.factory = APIRequestFactory()

    @override_settings(ROOT_URLCONF='security.urls')
    def test_request_id_injected(self):
        """Test middleware injects request_id."""
        request = self.factory.post('/api/auth/login/', {}, format='json')
        request.user = MagicMock(is_authenticated=False)
        from core.logging.middleware import ObservabilityMiddleware
        middleware = ObservabilityMiddleware(lambda r: None)
        middleware.process_request(request)
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertIsNotNone(request.request_id)

    @override_settings(ROOT_URLCONF='security.urls')
    def test_duration_tracked(self):
        """Test middleware tracks execution time."""
        request = self.factory.get('/api/auth/login/')
        request._start_time = __import__('time').time()
        request.user = MagicMock(is_authenticated=False)

        response = MagicMock(status_code=200)
        from core.logging.middleware import ObservabilityMiddleware
        middleware = ObservabilityMiddleware(lambda r: None)
        result = middleware.process_response(request, response)
        self.assertEqual(result, response)


class ConfigTests(TestCase):
    """Test logging configuration."""

    def test_logging_config_returns_dict(self):
        """Test logging_config returns a valid dict."""
        config = logging_config()
        self.assertIsInstance(config, dict)
        self.assertIn('version', config)
        self.assertIn('handlers', config)
        self.assertIn('loggers', config)

    def test_logging_config_has_erp_loggers(self):
        """Test config includes all ERP loggers."""
        config = logging_config()
        self.assertIn('erp', config['loggers'])
        self.assertIn('erp.audit', config['loggers'])
        self.assertIn('erp.financial', config['loggers'])
        self.assertIn('erp.inventory', config['loggers'])
        self.assertIn('erp.security', config['loggers'])
        self.assertIn('erp.performance', config['loggers'])
