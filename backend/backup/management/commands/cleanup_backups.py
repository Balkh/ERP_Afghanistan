from django.core.management.base import BaseCommand
from backup.backup_system import BackupManager


class Command(BaseCommand):
    help = 'Clean up old backups based on retention policy'

    def add_arguments(self, parser):
        parser.add_argument('--max-backups', type=int, default=None,
                          help='Maximum number of backups to keep')
        parser.add_argument('--max-age-days', type=int, default=None,
                          help='Maximum age of backups in days')
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be deleted without actually deleting')

    def handle(self, *args, **options):
        backup_manager = BackupManager()
        
        # Override config if arguments provided
        if options['max_backups'] is not None:
            backup_manager.config['retention']['max_backups'] = options['max_backups']
        if options['max_age_days'] is not None:
            backup_manager.config['retention']['max_age_days'] = options['max_age_days']
        
        backups = backup_manager.list_backups()
        self.stdout.write(f'Found {len(backups)} backups')
        
        if options['dry_run']:
            self.stdout.write('\nDry run - showing what would be cleaned up:\n')
            # Show backups that would be deleted based on retention policy
            max_backups = backup_manager.config['retention']['max_backups']
            max_age_days = backup_manager.config['retention']['max_age_days']
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            for i, backup in enumerate(backups):
                reason = []
                if i >= max_backups:
                    reason.append('exceeds max backups')
                try:
                    backup_date = datetime.fromisoformat(backup['timestamp'].split('+')[0])
                    if backup_date < cutoff_date:
                        reason.append('older than max age')
                except:
                    pass
                
                if reason:
                    self.stdout.write(f'  Would delete: {backup["filename"]} ({", ".join(reason)})')
        else:
            self.stdout.write('\nCleaning up old backups...')
            backup_manager.cleanup_old_backups()
            
            # Show remaining backups
            remaining = backup_manager.list_backups()
            self.stdout.write(self.style.SUCCESS(f'✓ Cleanup complete'))
            self.stdout.write(f'  Remaining backups: {len(remaining)}')