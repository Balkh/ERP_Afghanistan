"""
Management command to replay buffered events (Phase 6 — Lightweight Replay Hook).
Only for admin/debug use. NEVER auto-triggered in production.
"""
from django.core.management.base import BaseCommand, CommandError

from core.events import EnterpriseEventBus
from core.events.safety import safety_buffer


class Command(BaseCommand):
    help = "Replay buffered events from the safety buffer. Admin/debug only."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max events to replay")
        parser.add_argument("--correlation-id", type=str, default=None, help="Filter by correlation_id")

    def handle(self, *args, **options):
        limit = options["limit"]
        correlation_id = options.get("correlation_id")

        if correlation_id:
            events = safety_buffer.replay_by_correlation(correlation_id)
        else:
            events = safety_buffer.replay(limit)

        if not events:
            self.stdout.write("No buffered events to replay.")
            return

        replayed = 0
        for envelope in events:
            try:
                EnterpriseEventBus.publish(envelope["name"], envelope)
                replayed += 1
            except Exception:
                self.stderr.write(f"Replay failed for event {envelope.get('name')} [{envelope.get('event_id')}]")

        self.stdout.write(f"Replayed {replayed}/{len(events)} events from safety buffer.")
