"""
Journal entry DTO mappers.

Extracted from JournalEngine in Sprint 4.
Pure formatting — no DB writes, no transaction boundaries, no save calls.
"""
from decimal import Decimal
from typing import Optional

from accounting.models import JournalEntryLine


def format_ledger_entry(
    line: JournalEntryLine,
    running_balance: Decimal,
) -> dict:
    """
    Format a journal entry line into a ledger DTO.
    The running_balance passed in is the balance AFTER this line.
    """
    return {
        'entry_number': line.entry.entry_number,
        'entry_date': line.entry.entry_date.isoformat(),
        'entry_type': line.entry.entry_type,
        'description': line.entry.description,
        'reference': line.entry.reference,
        'debit': line.debit,
        'credit': line.credit,
        'running_balance': running_balance,
    }
