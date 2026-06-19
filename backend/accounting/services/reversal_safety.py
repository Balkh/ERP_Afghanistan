"""Reversal Safety Engine — ensures all reversal flows are safe, traceable, and atomic.

This service provides:
1. Reversal impact analysis (preview before execution)
2. Reversal chain validation (prevent loops, double-reversals)
3. Period-lock enforcement for reversals
4. Reversal chain visualization
5. Mandatory reason validation

All reversals MUST pass through this safety layer before execution.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounting.models import (
    JournalEntry,
    JournalEntryLine,
    Account,
    is_period_locked,
    get_open_period_for_date,
)
from core.services.journal_gateway import JournalGateway

logger = logging.getLogger('erp.reversal_safety')


class ReversalImpact:
    """Result of reversal impact analysis."""

    def __init__(self, entry: JournalEntry):
        self.entry = entry
        self.is_safe = True
        self.blockers: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.affected_accounts: List[Dict[str, Any]] = []
        self.reversal_chain: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def add_blocker(self, code: str, message: str):
        self.is_safe = False
        self.blockers.append({'code': code, 'message': message})

    def add_warning(self, code: str, message: str):
        self.warnings.append({'code': code, 'message': message})

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_id': str(self.entry.id),
            'entry_number': self.entry.entry_number,
            'entry_type': self.entry.entry_type,
            'entry_date': str(self.entry.entry_date),
            'description': self.entry.description,
            'total_amount': str(self.entry.total_debit),
            'is_safe': self.is_safe,
            'blocker_count': len(self.blockers),
            'warning_count': len(self.warnings),
            'blockers': self.blockers,
            'warnings': self.warnings,
            'affected_accounts': self.affected_accounts,
            'reversal_chain': self.reversal_chain,
            'summary': self.summary,
        }


class ReversalSafetyService:
    """Validates and executes safe journal entry reversals."""

    @classmethod
    def analyze_impact(cls, entry_id: str) -> ReversalImpact:
        """Analyze the impact of reversing a journal entry without executing."""
        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError(f'Journal entry {entry_id} not found.')

        impact = ReversalImpact(entry)

        cls._validate_entry_reversible(entry, impact)
        cls._check_period_lock(entry, impact)
        cls._check_reversal_loop(entry, impact)
        cls._check_double_reversal(entry, impact)
        cls._analyze_affected_accounts(entry, impact)
        cls._build_reversal_chain(entry, impact)

        impact.summary = {
            'line_count': entry.lines.count(),
            'total_debit': str(entry.total_debit),
            'total_credit': str(entry.total_credit),
            'source_module': entry.source_module or '',
            'source_document': entry.source_document or '',
        }

        return impact

    @classmethod
    @transaction.atomic
    def execute_reversal(
        cls,
        entry_id: str,
        reason: str,
        reversed_by: str = '',
        entity_type: str = '',
        entity_id: str = '',
        company=None,
    ) -> Dict[str, Any]:
        """Execute a reversal with full safety validation."""
        if not reason or len(reason.strip()) < 10:
            raise ValidationError('Reversal reason is required (minimum 10 characters).')

        impact = cls.analyze_impact(entry_id)

        if not impact.is_safe:
            blocker_messages = '; '.join(b['message'] for b in impact.blockers)
            raise ValidationError(
                f'Reversal is not safe: {blocker_messages}'
            )

        result = JournalGateway.reverse_entry(
            entry_id=entry_id,
            reason=reason,
            reversed_by=reversed_by,
            entity_type=entity_type,
            entity_id=entity_id,
            company=company,
        )

        logger.info(
            f'[REVERSAL_SAFETY] Entry {impact.entry.entry_number} reversed. '
            f'Reason: {reason}. Reversal ID: {result.get("reversal_entry_id")}'
        )

        return {
            'success': True,
            'original_entry_id': entry_id,
            'original_entry_number': impact.entry.entry_number,
            'reversal_entry_id': result.get('reversal_entry_id'),
            'transaction_id': result.get('transaction_id'),
            'audit_id': result.get('audit_id'),
            'impact_analysis': impact.to_dict(),
        }

    @classmethod
    def _validate_entry_reversible(cls, entry: JournalEntry, impact: ReversalImpact):
        """Validate that the entry can be reversed."""
        if not entry.is_posted:
            impact.add_blocker(
                'ENTRY_NOT_POSTED',
                f'Entry {entry.entry_number} must be posted before reversal.',
            )

        if entry.entry_type == 'REVERSAL':
            impact.add_blocker(
                'ALREADY_REVERSAL',
                f'Entry {entry.entry_number} is already a reversal entry and cannot be reversed.',
            )

    @classmethod
    def _check_period_lock(cls, entry: JournalEntry, impact: ReversalImpact):
        """Check if the entry's period is locked."""
        if is_period_locked(entry.entry_date):
            period = get_open_period_for_date(entry.entry_date)
            period_info = f' (period: {period.code})' if period else ''
            impact.add_blocker(
                'PERIOD_LOCKED',
                f'Entry date {entry.entry_date} falls in a locked/closed period{period_info}.',
            )

    @classmethod
    def _check_reversal_loop(cls, entry: JournalEntry, impact: ReversalImpact):
        """Check for reversal loops — prevent A -> B -> A chains."""
        chain = cls._get_reversal_chain(entry)

        if entry in chain[1:]:
            impact.add_blocker(
                'REVERSAL_LOOP_DETECTED',
                f'Reversal loop detected: {entry.entry_number} would create a circular chain.',
            )

    @classmethod
    def _check_double_reversal(cls, entry: JournalEntry, impact: ReversalImpact):
        """Check if entry has already been reversed."""
        if hasattr(entry, 'reversed_by_entry') and entry.reversed_by_entry:
            impact.add_blocker(
                'ALREADY_REVERSED',
                f'Entry {entry.entry_number} has already been reversed by {entry.reversed_by_entry.entry_number}.',
            )

    @classmethod
    def _analyze_affected_accounts(cls, entry: JournalEntry, impact: ReversalImpact):
        """Analyze which accounts will be affected by the reversal."""
        for line in entry.lines.all():
            impact.affected_accounts.append({
                'account_code': line.account.code,
                'account_name': line.account.name,
                'account_type': line.account.account_type,
                'current_debit': str(line.debit),
                'current_credit': str(line.credit),
                'reversal_debit': str(line.credit),
                'reversal_credit': str(line.debit),
            })

    @classmethod
    def _build_reversal_chain(cls, entry: JournalEntry, impact: ReversalImpact):
        """Build the full reversal chain for visualization."""
        chain = cls._get_reversal_chain(entry)

        for chain_entry in chain:
            impact.reversal_chain.append({
                'entry_id': str(chain_entry.id),
                'entry_number': chain_entry.entry_number,
                'entry_type': chain_entry.entry_type,
                'entry_date': str(chain_entry.entry_date),
                'description': chain_entry.description,
                'is_posted': chain_entry.is_posted,
            })

    @classmethod
    def _get_reversal_chain(cls, entry: JournalEntry) -> List[JournalEntry]:
        """Get the full reversal chain for an entry."""
        chain: List[JournalEntry] = [entry]
        visited: Set[str] = {str(entry.id)}

        current = entry

        while current.original_entry:
            if str(current.original_entry.id) in visited:
                break
            visited.add(str(current.original_entry.id))
            chain.insert(0, current.original_entry)
            current = current.original_entry

        current = entry

        while hasattr(current, 'reversed_entries') and current.reversed_entries.exists():
            reversed_entry = current.reversed_entries.first()
            if str(reversed_entry.id) in visited:
                break
            visited.add(str(reversed_entry.id))
            chain.append(reversed_entry)
            current = reversed_entry

        return chain

    @classmethod
    def get_reversal_chain_visualization(cls, entry_id: str) -> Dict[str, Any]:
        """Get a visualization-ready reversal chain."""
        try:
            entry = JournalEntry.objects.get(id=entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError(f'Journal entry {entry_id} not found.')

        chain = cls._get_reversal_chain(entry)

        nodes = []
        edges = []

        for i, chain_entry in enumerate(chain):
            nodes.append({
                'id': str(chain_entry.id),
                'entry_number': chain_entry.entry_number,
                'entry_type': chain_entry.entry_type,
                'entry_date': str(chain_entry.entry_date),
                'total_amount': str(chain_entry.total_debit),
                'is_posted': chain_entry.is_posted,
                'is_original': chain_entry.original_entry is None,
            })

            if i > 0:
                edges.append({
                    'from': str(chain[i - 1].id),
                    'to': str(chain_entry.id),
                    'relationship': 'reversed_by' if chain_entry.entry_type == 'REVERSAL' else 'reverses',
                })

        return {
            'entry_id': entry_id,
            'chain_length': len(chain),
            'nodes': nodes,
            'edges': edges,
        }
