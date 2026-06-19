from django.core.management.base import BaseCommand
from backup.backup_system import BackupManager


class Command(BaseCommand):
    help = 'Restore a backup of the Pharmacy ERP database'

    def add_arguments(self, parser):
        parser.add_argument('backup_path', type=str,
                          help='Path to the backup file to restore')
        parser.add_argument('--target-db', type=str, default=None,
                          help='Target database path (default: from config)')
        parser.add_argument('--password', type=str, default=None,
                          help='Encryption password (if backup is encrypted)')
        parser.add_argument('--no-verify', action='store_true',
                          help='Skip verification after restore')

    def handle(self, *args, **options):
        self.stdout.write(f'Starting restore from: {options["backup_path"]}')
        
        backup_manager = BackupManager()
        
        result = backup_manager.restore_backup(
            backup_path=options['backup_path'],
            target_db_path=options['target_db'],
            password=options['password'],
            verify=not options['no_verify']
        )
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS('✓ Backup restored successfully'))
            self.stdout.write(f'  Target: {result["target_path"]}')
            self.stdout.write(f'  Duration: {result.get("duration", 0):.2f} seconds')
        else:
            self.stderr.write(self.style.ERROR(f'✗ Restore failed: {result.get("error", "Unknown error")}'))