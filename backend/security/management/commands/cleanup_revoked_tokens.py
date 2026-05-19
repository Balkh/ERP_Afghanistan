"""
Management command to clean up expired revoked tokens.
Run periodically (e.g., via cron or scheduled task) to prevent table growth.
"""
from django.core.management.base import BaseCommand
from security.models import RevokedToken


class Command(BaseCommand):
    help = 'Clean up expired revoked tokens from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show count of expired tokens without deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            from django.utils import timezone
            count = RevokedToken.objects.filter(expires_at__lt=timezone.now()).count()
            self.stdout.write(
                self.style.WARNING(f'{count} expired revoked tokens would be deleted')
            )
        else:
            deleted = RevokedToken.cleanup_expired()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted} expired revoked tokens')
            )
