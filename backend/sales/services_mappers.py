"""
Sales mappers.

Extracted from SalesAccountingService in Sprint 4.
Pure lookups — no DB writes, no transaction boundaries, no save calls.
"""

PAYMENT_METHOD_ACCOUNT_OVERRIDES = {
    'CASH': None,
    'BANK_TRANSFER': '1020',
    'CHEQUE': '1030',
    'CREDIT_CARD': '1040',
    'INSURANCE': '1210',
}


def resolve_cash_account_code(payment_method: str, default_cash_code: str) -> str:
    """
    Get appropriate cash account code based on payment method.

    Falls back to `default_cash_code` for any method not in the override map
    or for the explicit CASH method.
    """
    override = PAYMENT_METHOD_ACCOUNT_OVERRIDES.get(payment_method)
    return override if override is not None else default_cash_code
