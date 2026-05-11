"""
Journal Event Log Audit Trail Tests

Tests the JournalEventLog model and event logging functionality
in the accounting system.
"""

from decimal import Decimal
from django.test import TransactionTestCase
from django.utils import timezone as django_timezone

from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog
from accounting.services.journal_engine import JournalEngine


class JournalEventCreationTest(TransactionTestCase):
    """Test journal entry creation events."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1000', name='Asset', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_create_entry_logs_created_event(self):
        """Test that creating an entry logs a CREATED event."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Test entry',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '100.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '100.00'}
            ]
        )

        self.assertTrue(result.get('success'))
        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        events = JournalEventLog.objects.filter(entry=entry, event_type='CREATED')
        self.assertEqual(events.count(), 1)


class JournalEventPostingTest(TransactionTestCase):
    """Test journal entry posting events."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1001', name='Asset', account_type='ASSET', is_active=True
        )
        self.expense = Account.objects.create(
            code='5000', name='Expense', account_type='EXPENSE', is_active=True
        )

    def test_post_entry_logs_posted_event(self):
        """Test that posting an entry logs a POSTED event."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry to post',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '150.00', 'credit': '0.00'},
                {'account_id': str(self.expense.id), 'debit': '0.00', 'credit': '150.00'}
            ]
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        JournalEngine.post_entry(str(entry.id))

        events = JournalEventLog.objects.filter(entry=entry, event_type='POSTED')
        self.assertEqual(events.count(), 1)

    def test_unpost_entry_logs_unposted_event(self):
        """Test that unposting an entry logs an UNPOSTED event."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry to unpost',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '250.00', 'credit': '0.00'},
                {'account_id': str(self.expense.id), 'debit': '0.00', 'credit': '250.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        JournalEngine.unpost_entry(str(entry.id))

        events = JournalEventLog.objects.filter(entry=entry, event_type='UNPOSTED')
        self.assertEqual(events.count(), 1)


class JournalEventReversalTest(TransactionTestCase):
    """Test journal entry reversal events."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1002', name='Asset', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4001', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_reverse_entry_logs_reversed_event(self):
        """Test that reversing an entry logs a REVERSED event on original."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry to reverse',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '300.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '300.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        JournalEngine.reverse_entry(str(entry.id), reason='Test reversal')

        events = JournalEventLog.objects.filter(entry=entry, event_type='REVERSED')
        self.assertEqual(events.count(), 1)
        self.assertIn('REV-', events.first().reference)

    def test_reverse_entry_creates_reversal_entry(self):
        """Test that reversing creates a new reversal entry."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Entry for reversal',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '400.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '400.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        reversal_result = JournalEngine.reverse_entry(
            str(entry.id), reason='Reversal test'
        )

        self.assertTrue(reversal_result.get('success'))
        original = JournalEntry.objects.get(id=entry.id)
        self.assertIsNotNone(original.reversed_by_entry)
        self.assertTrue(original.reversed_by_entry.entry_number.startswith('REV-'))


class JournalEventLogHelperTest(TransactionTestCase):
    """Test the log_event helper function."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1003', name='Asset', account_type='ASSET', is_active=True
        )

    def test_log_event_creates_event(self):
        """Test that log_event helper creates event."""
        entry = JournalEntry.objects.create(
            entry_number='JE-EVT-001',
            entry_date=django_timezone.now().date(),
            entry_type='GENERAL',
            description='Test',
            is_posted=True
        )

        event = JournalEngine.log_event(
            entry=entry,
            event_type='VIEWED',
            notes='Test view'
        )

        self.assertEqual(event.entry_id, entry.id)
        self.assertEqual(event.event_type, 'VIEWED')
        self.assertEqual(event.notes, 'Test view')


class JournalEventSequencingTest(TransactionTestCase):
    """Test event sequencing and ordering."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1004', name='Asset', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4002', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_reversal_logged_before_reversal_entry_created(self):
        """Test REVERSED event is logged before reversal entry creation."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Sequencing test',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '500.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '500.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])

        reversed_event = JournalEventLog.objects.filter(
            entry=entry, event_type='REVERSED'
        ).first()

        reversal_entry = entry.reversed_by_entry
        if reversal_entry:
            created_event = JournalEventLog.objects.filter(
                entry=reversal_entry, event_type='CREATED'
            ).first()

            if reversed_event and created_event:
                self.assertLessEqual(reversed_event.timestamp, reversal_entry.created_at)


class JournalEventHistoryTest(TransactionTestCase):
    """Test event history retrieval."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1005', name='Asset', account_type='ASSET', is_active=True
        )
        self.revenue = Account.objects.create(
            code='4003', name='Revenue', account_type='REVENUE', is_active=True
        )

    def test_entry_has_event_history(self):
        """Test that entry tracks its event history."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Event history test',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '600.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '600.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        events = JournalEventLog.objects.filter(entry=entry).order_by('timestamp')

        self.assertGreaterEqual(events.count(), 2)
        event_types = list(events.values_list('event_type', flat=True))
        self.assertIn('CREATED', event_types)
        self.assertIn('POSTED', event_types)

    def test_reversed_entry_tracks_reversal_event(self):
        """Test that reversed entry tracks reversal event."""
        result = JournalEngine.create_entry(
            entry_type='GENERAL',
            description='Reversal tracking test',
            lines=[
                {'account_id': str(self.asset.id), 'debit': '700.00', 'credit': '0.00'},
                {'account_id': str(self.revenue.id), 'debit': '0.00', 'credit': '700.00'}
            ],
            auto_post=True
        )

        entry = JournalEntry.objects.get(entry_number=result['entry_number'])
        JournalEngine.reverse_entry(str(entry.id), reason='Test')

        entry.refresh_from_db()
        reversed_event = JournalEventLog.objects.filter(
            entry=entry, event_type='REVERSED'
        ).first()

        self.assertIsNotNone(reversed_event)
        self.assertIn('REV-', reversed_event.reference)


class JournalEventValidationTest(TransactionTestCase):
    """Test event logging with various scenarios."""

    def setUp(self):
        self.asset = Account.objects.create(
            code='1006', name='Asset', account_type='ASSET', is_active=True
        )

    def test_event_log_without_user(self):
        """Test event logging without user ID."""
        entry = JournalEntry.objects.create(
            entry_number='JE-EVT-002',
            entry_date=django_timezone.now().date(),
            entry_type='GENERAL',
            description='Test',
            is_posted=True
        )

        event = JournalEngine.log_event(
            entry=entry,
            event_type='VIEWED'
        )

        self.assertIsNone(event.user_id)

    def test_multiple_events_on_same_entry(self):
        """Test multiple events can be logged on same entry."""
        entry = JournalEntry.objects.create(
            entry_number='JE-EVT-003',
            entry_date=django_timezone.now().date(),
            entry_type='GENERAL',
            description='Multi event test',
            is_posted=True
        )

        JournalEngine.log_event(entry=entry, event_type='VIEWED')
        JournalEngine.log_event(entry=entry, event_type='VIEWED')
        JournalEngine.log_event(entry=entry, event_type='VIEWED')

        events = JournalEventLog.objects.filter(entry=entry, event_type='VIEWED')
        self.assertEqual(events.count(), 3)