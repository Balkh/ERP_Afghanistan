"""
HR model behavior tests - simplified.
"""

from decimal import Decimal
from django.test import TestCase


class HRModelTest(TestCase):
    """Test HR models - simplified."""

    def test_hr_department_import(self):
        """Test HR Department can be imported."""
        from hr.models import Department
        dept = Department.objects.create(name='Pharmacy', code='PH', is_active=True)
        self.assertEqual(dept.name, 'Pharmacy')

    def test_hr_department_str(self):
        """Test Department string representation."""
        from hr.models import Department
        dept = Department.objects.create(name='Sales', code='SL')
        self.assertIn('Sales', str(dept))


class PayrollModelTest(TestCase):
    """Test Payroll models - simplified."""

    def test_payroll_allowance_import(self):
        """Test Payroll Allowance can be imported."""
        from payroll.models import Allowance
        allowance = Allowance.objects.create(
            name='Transport',
            amount=Decimal('5000.00'),
            is_active=True
        )
        self.assertEqual(allowance.name, 'Transport')