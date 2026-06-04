"""
Payment DTO mappers.

Extracted from PaymentEngine in Sprint 4.
Pure formatting — no DB writes, no transaction boundaries, no save calls.
"""
from payments.models import FinancialTransaction


def format_transaction_dict(txn: FinancialTransaction) -> dict:
    """
    Format a FinancialTransaction into a DTO for API responses.
    """
    return {
        'transaction_number': txn.transaction_number,
        'transaction_type': txn.transaction_type,
        'status': txn.status,
        'amount': str(txn.amount),
        'fee': str(txn.fee),
        'net_amount': str(txn.net_amount),
        'currency': txn.currency,
        'description': txn.description,
        'reference_number': txn.reference_number,
        'transaction_date': txn.transaction_date.isoformat(),
        'is_settled': txn.is_settled,
    }


def format_account_summary(
    account,
    total_in,
    total_out,
    total_fees,
    transaction_count,
) -> dict:
    """
    Format a payment account summary DTO.
    """
    return {
        'total_in': str(total_in),
        'total_out': str(total_out),
        'total_fees': str(total_fees),
        'transaction_count': transaction_count,
    }
