"""
Payment validators.

Extracted from PaymentEngine in Sprint 4.
Pure query + check logic — no DB writes, no transaction boundaries, no save calls.
"""
from typing import List, Optional

from payments.models import PaymentMethod, PaymentAccount
from accounting.models import Account


REQUIRED_ACCOUNT_CODES = {
    '1000': 'Cash/Bank',
    '1200': 'Accounts Receivable',
    '1300': 'Inventory',
    '2100': 'Tax Payable',
    '4100': 'Sales Revenue',
    '5100': 'COGS',
    '6100': 'Operating Expenses',
}


def validate_required_accounts() -> List[str]:
    """
    Validate that required accounting accounts exist.

    Returns list of missing account codes (formatted "code (name)") if any are missing.
    """
    missing = []
    for code, name in REQUIRED_ACCOUNT_CODES.items():
        if not Account.objects.filter(code=code, is_active=True).exists():
            missing.append(f"{code} ({name})")
    return missing


def validate_payment_method(payment_method_code: str) -> Optional[PaymentMethod]:
    """
    Resolve a payment method by code. Returns None if not found or inactive.
    """
    try:
        return PaymentMethod.objects.get(code=payment_method_code, is_active=True)
    except PaymentMethod.DoesNotExist:
        return None


def validate_payment_account_for_update(account_code: str) -> Optional[PaymentAccount]:
    """
    Resolve and lock a payment account by code. Returns None if not found or inactive.
    """
    try:
        return PaymentAccount.objects.select_for_update().get(code=account_code, is_active=True)
    except PaymentAccount.DoesNotExist:
        return None


def find_cash_method() -> Optional[PaymentMethod]:
    """
    Find the default CASH payment method, falling back to any CASH method.
    Returns None if no CASH method is configured.
    """
    try:
        return PaymentMethod.objects.get(method_type='CASH', is_default=True)
    except PaymentMethod.DoesNotExist:
        return PaymentMethod.objects.filter(method_type='CASH').first()
