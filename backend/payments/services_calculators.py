"""
Payment calculators.

Extracted from PaymentEngine in Sprint 4.
Pure math — no DB writes, no transaction boundaries, no save calls.
"""
from decimal import Decimal
from typing import Iterable, Optional, Tuple

from payments.models import PaymentMethod, PaymentAccount, FinancialTransaction


CENTS = Decimal('0.01')


def compute_fee(amount: Decimal, payment_method: PaymentMethod, fee_override: Optional[Decimal] = None) -> Decimal:
    """
    Calculate the transaction fee, optionally overridden.
    Result is quantized to 2 decimal places.
    """
    fee = fee_override if fee_override is not None else payment_method.calculate_fee(amount)
    return fee.quantize(CENTS)


def compute_net_amount(amount: Decimal, fee: Decimal) -> Decimal:
    """
    Calculate the net amount for a receipt: amount minus fee.
    Result is quantized to 2 decimal places.
    """
    return (amount - fee).quantize(CENTS)


def compute_total_deduction(amount: Decimal, fee: Decimal) -> Decimal:
    """
    Calculate the total deduction for a payment: amount plus fee.
    Result is quantized to 2 decimal places.
    """
    return (amount + fee).quantize(CENTS)


def compute_settlement_included_amount(
    txn: FinancialTransaction,
    payment_account: PaymentAccount,
) -> Decimal:
    """
    Determine how much of a transaction's amount applies to a given payment account
    for a settlement batch. Caller must verify the account is involved.
    """
    if txn.destination_account_id == payment_account.id:
        return Decimal(txn.net_amount)
    return -(Decimal(txn.amount) + Decimal(txn.fee))


def compute_transaction_totals(
    transactions: Iterable[FinancialTransaction],
    account: PaymentAccount,
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Aggregate total in / out / fees over a queryset of transactions
    that involve the given account.
    """
    total_in = Decimal('0.00')
    total_out = Decimal('0.00')
    total_fees = Decimal('0.00')

    for txn in transactions:
        if txn.destination_account_id == account.id:
            total_in += Decimal(txn.net_amount)
        if txn.source_account_id == account.id:
            total_out += Decimal(txn.amount) + Decimal(txn.fee)
        total_fees += Decimal(txn.fee)

    return total_in, total_out, total_fees
