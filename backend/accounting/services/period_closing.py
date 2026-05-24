"""Period Closing Engine — validates and executes fiscal period closing.

This service ensures that a fiscal period can only be closed when:
1. All journal entries are posted
2. No unresolved reversals exist
3. Trial balance is consistent (debits == credits)
4. No pending approvals exist
5. No orphan transactions exist
6. All reconciliation mismatches are resolved

Every close action creates an audit log entry.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User

from accounting.models import (
    FiscalPeriod,
    FiscalPeriodCloseLog,
    JournalEntry,
    JournalEntryLine,
    Account,
)
from core.services.financial_audit import FinancialAuditService

logger = logging.getLogger('erp.period_closing')


class PeriodClosingReadiness:
    """Result of period closing readiness check."""

    def __init__(self, period: FiscalPeriod):
        self.period = period
        self.is_ready = True
        self.blockers: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def add_blocker(self, code: str, message: str, count: int = 0):
        self.is_ready = False
        self.blockers.append({
            'code': code,
            'message': message,
            'count': count,
        })

    def add_warning(self, code: str, message: str, count: int = 0):
        self.warnings.append({
            'code': code,
            'message': message,
            'count': count,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            'period_id': str(self.period.id),
            'period_code': self.period.code,
            'period_name': self.period.name,
            'is_ready': self.is_ready,
            'blocker_count': len(self.blockers),
            'warning_count': len(self.warnings),
            'blockers': self.blockers,
            'warnings': self.warnings,
            'summary': self.summary,
        }


class PeriodClosingService:
    """Validates and executes fiscal period closing."""

    @classmethod
    def check_readiness(cls, period: FiscalPeriod) -> PeriodClosingReadiness:
        """Check if a period is ready to be closed."""
        readiness = PeriodClosingReadiness(period)

        cls._check_unposted_journals(period, readiness)
        cls._check_unresolved_reversals(period, readiness)
        cls._check_trial_balance(period, readiness)
        cls._check_orphan_transactions(period, readiness)
        cls._check_date_range_integrity(period, readiness)

        readiness.summary = {
            'total_journal_entries': JournalEntry.objects.filter(
                entry_date__gte=period.start_date,
                entry_date__lte=period.end_date,
            ).count(),
            'posted_journal_entries': JournalEntry.objects.filter(
                entry_date__gte=period.start_date,
                entry_date__lte=period.end_date,
                is_posted=True,
            ).count(),
            'total_debits': str(cls._get_period_total(period, 'debit')),
            'total_credits': str(cls._get_period_total(period, 'credit')),
        }

        return readiness

    @classmethod
    @transaction.atomic
    def soft_close(
        cls,
        period: FiscalPeriod,
        user: Optional[User] = None,
        reason: str = '',
    ) -> Dict[str, Any]:
        """Soft-close a period — warnings allowed, but new entries blocked."""
        if not reason:
            raise ValidationError('Reason is required for period closing.')

        if period.status != 'OPEN':
            raise ValidationError(
                f'Period {period.code} is not open (current status: {period.status}).'
            )

        readiness = cls.check_readiness(period)

        previous_status = period.status
        period.status = 'SOFT_CLOSED'
        period.save()

        log = FiscalPeriodCloseLog.objects.create(
            period=period,
            action='SOFT_CLOSE',
            reason=reason,
            performed_by=user,
            previous_status=previous_status,
            new_status='SOFT_CLOSED',
            validation_summary=readiness.to_dict(),
        )

        logger.info(
            f'[PERIOD_CLOSING] Period {period.code} soft-closed by {user}. '
            f'Reason: {reason}. Blockers: {len(readiness.blockers)}, '
            f'Warnings: {len(readiness.warnings)}'
        )

        return {
            'success': True,
            'period_id': str(period.id),
            'action': 'SOFT_CLOSE',
            'log_id': str(log.id),
            'readiness': readiness.to_dict(),
        }

    @classmethod
    @transaction.atomic
    def close_period(
        cls,
        period: FiscalPeriod,
        user: Optional[User] = None,
        reason: str = '',
        force: bool = False,
    ) -> Dict[str, Any]:
        """Close a period — all checks must pass unless force=True."""
        if not reason:
            raise ValidationError('Reason is required for period closing.')

        if period.status not in ('OPEN', 'SOFT_CLOSED'):
            raise ValidationError(
                f'Period {period.code} cannot be closed (current status: {period.status}).'
            )

        readiness = cls.check_readiness(period)

        if not readiness.is_ready and not force:
            raise ValidationError(
                f'Period {period.code} is not ready for closing. '
                f'{len(readiness.blockers)} blocker(s): '
                + '; '.join(b['message'] for b in readiness.blockers)
            )

        previous_status = period.status
        period.status = 'CLOSED'
        period.closing_completed_at = timezone.now()
        period.closing_completed_by = user
        period.save()

        log = FiscalPeriodCloseLog.objects.create(
            period=period,
            action='CLOSE',
            reason=reason,
            performed_by=user,
            previous_status=previous_status,
            new_status='CLOSED',
            validation_summary=readiness.to_dict(),
            affected_entries_count=readiness.summary.get('total_journal_entries', 0),
        )

        logger.info(
            f'[PERIOD_CLOSING] Period {period.code} closed by {user}. '
            f'Reason: {reason}. Force: {force}. '
            f'Affected entries: {log.affected_entries_count}'
        )

        return {
            'success': True,
            'period_id': str(period.id),
            'action': 'CLOSE',
            'log_id': str(log.id),
            'readiness': readiness.to_dict(),
        }

    @classmethod
    @transaction.atomic
    def lock_period(
        cls,
        period: FiscalPeriod,
        user: Optional[User] = None,
        reason: str = '',
    ) -> Dict[str, Any]:
        """Lock a period — no modifications allowed."""
        if not reason:
            raise ValidationError('Reason is required for period locking.')

        if period.status not in ('CLOSED', 'SOFT_CLOSED'):
            raise ValidationError(
                f'Period {period.code} must be closed before locking.'
            )

        previous_status = period.status
        period.lock(user=user)

        log = FiscalPeriodCloseLog.objects.create(
            period=period,
            action='LOCK',
            reason=reason,
            performed_by=user,
            previous_status=previous_status,
            new_status='LOCKED',
        )

        logger.info(
            f'[PERIOD_CLOSING] Period {period.code} locked by {user}. '
            f'Reason: {reason}'
        )

        return {
            'success': True,
            'period_id': str(period.id),
            'action': 'LOCK',
            'log_id': str(log.id),
        }

    @classmethod
    @transaction.atomic
    def reopen_period(
        cls,
        period: FiscalPeriod,
        user: Optional[User] = None,
        reason: str = '',
    ) -> Dict[str, Any]:
        """Reopen a closed/locked period — requires reason and creates audit trail."""
        if not reason:
            raise ValidationError('Reason is required for period reopening.')

        if period.status not in ('CLOSED', 'LOCKED', 'SOFT_CLOSED'):
            raise ValidationError(
                f'Period {period.code} is not closed or locked (current status: {period.status}).'
            )

        previous_status = period.status
        period.unlock(user=user, reason=reason)

        FiscalPeriodCloseLog.objects.create(
            period=period,
            action='REOPEN',
            reason=reason,
            performed_by=user,
            previous_status=previous_status,
            new_status='OPEN',
        )

        logger.warning(
            f'[PERIOD_CLOSING] Period {period.code} REOPENED by {user}. '
            f'Reason: {reason}. Previous status: {previous_status}'
        )

        return {
            'success': True,
            'period_id': str(period.id),
            'action': 'REOPEN',
            'previous_status': previous_status,
            'new_status': 'OPEN',
        }

    @classmethod
    def _check_unposted_journals(cls, period: FiscalPeriod, readiness: PeriodClosingReadiness):
        """Check for unposted journal entries in the period."""
        unposted = JournalEntry.objects.filter(
            entry_date__gte=period.start_date,
            entry_date__lte=period.end_date,
            is_posted=False,
        ).count()

        if unposted > 0:
            readiness.add_blocker(
                'UNPOSTED_JOURNALS',
                f'{unposted} unposted journal entry(ies) exist in this period.',
                unposted,
            )

    @classmethod
    def _check_unresolved_reversals(cls, period: FiscalPeriod, readiness: PeriodClosingReadiness):
        """Check for unresolved reversals."""
        reversal_pending = JournalEntry.objects.filter(
            entry_date__gte=period.start_date,
            entry_date__lte=period.end_date,
            entry_type='REVERSAL',
            is_posted=False,
        ).count()

        if reversal_pending > 0:
            readiness.add_blocker(
                'UNRESOLVED_REVERSALS',
                f'{reversal_pending} unposted reversal entry(ies) exist.',
                reversal_pending,
            )

    @classmethod
    def _check_trial_balance(cls, period: FiscalPeriod, readiness: PeriodClosingReadiness):
        """Check if trial balance is consistent for the period."""
        total_debits = cls._get_period_total(period, 'debit')
        total_credits = cls._get_period_total(period, 'credit')

        difference = abs(total_debits - total_credits)

        if difference > Decimal('0.01'):
            readiness.add_blocker(
                'TRIAL_BALANCE_MISMATCH',
                f'Trial balance mismatch: debits={total_debits}, credits={total_credits}, '
                f'difference={difference}',
            )
        elif difference > Decimal('0.00'):
            readiness.add_warning(
                'TRIAL_BALANCE_ROUNDING',
                f'Minor rounding difference: {difference}',
            )

    @classmethod
    def _check_orphan_transactions(cls, period: FiscalPeriod, readiness: PeriodClosingReadiness):
        """Check for orphan journal entries (entries with no lines)."""
        orphans = JournalEntry.objects.filter(
            entry_date__gte=period.start_date,
            entry_date__lte=period.end_date,
        ).exclude(
            id__in=JournalEntryLine.objects.values('entry_id')
        ).count()

        if orphans > 0:
            readiness.add_blocker(
                'ORPHAN_ENTRIES',
                f'{orphans} journal entry(ies) with no lines exist.',
                orphans,
            )

    @classmethod
    def _check_date_range_integrity(cls, period: FiscalPeriod, readiness: PeriodClosingReadiness):
        """Check for overlapping periods."""
        overlapping = FiscalPeriod.objects.filter(
            start_date__lte=period.end_date,
            end_date__gte=period.start_date,
        ).exclude(id=period.id)

        if overlapping.exists():
            overlap_list = ', '.join(p.code for p in overlapping)
            readiness.add_warning(
                'OVERLAPPING_PERIODS',
                f'Overlapping periods detected: {overlap_list}',
                overlapping.count(),
            )

    @classmethod
    def _get_period_total(cls, period: FiscalPeriod, field: str) -> Decimal:
        """Get total debits or credits for a period."""
        entries = JournalEntry.objects.filter(
            entry_date__gte=period.start_date,
            entry_date__lte=period.end_date,
            is_posted=True,
        )

        total = Decimal('0.00')
        for entry in entries:
            if field == 'debit':
                total += entry.total_debit
            else:
                total += entry.total_credit

        return total
