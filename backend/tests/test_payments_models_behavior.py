"""
Payments model behavior tests - simplified.
"""

from decimal import Decimal
from django.test import TestCase

from payments.models import PaymentMethod


class PaymentMethodModelTest(TestCase):
    """Test PaymentMethod model."""

    def test_create_payment_method(self):
        """Test creating a payment method."""
        method = PaymentMethod.objects.create(
            name='Cash',
            code='CASH',
            method_type='CASH',
            is_active=True
        )
        self.assertEqual(method.name, 'Cash')

    def test_payment_method_str(self):
        """Test payment method string representation."""
        method = PaymentMethod.objects.create(name='Bank Transfer', code='BANK', method_type='BANK_TRANSFER')
        self.assertIn('Bank', str(method))