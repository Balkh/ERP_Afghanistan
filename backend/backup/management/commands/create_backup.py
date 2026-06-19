from django.core.management.base import BaseCommand
from backup.backup_system import BackupManager
import json


class Command(BaseCommand):
    help = 'Create a backup of the Pharmacy ERP database'

    def add_arguments(self, parser):
        parser.add_argument('--description', type=str, default='Manual backup via management command',
                          help='Description for the backup')
        parser.add_argument('--db-path', type=str, default=None,
                          help='Path to the database file')
        parser.add_argument('--include-files', type=str, nargs='*', default=[],
                          help='Additional files to include in backup')
        parser.add_argument('--format', type=str, choices=['json', 'text'], default='text',
                          help='Output format')

    def handle(self, *args, **options):
        self.stdout.write('Starting backup creation...')
        
        backup_manager = BackupManager()
        
        # If db_path not specified, get from config
        db_path = options['db_path']
        if not db_path:
            db_path = backup_manager.config.get('database', {}).get('path')
        
        if not db_path:
            self.stderr.write(self.style.ERROR('Database path not configured'))
            return
        
        result = backup_manager.create_backup(
            db_path=db_path,
            include_files=options['include_files'],
            description=options['description']
        )
        
        if result['success']:
            metadata = result['metadata']
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(result, indent=2, default=str))
            else:
                self.stdout.write(self.style.SUCCESS('✓ Backup created successfully'))
                self.stdout.write(f'  Filename: {metadata["filename"]}')
                self.stdout.write(f'  Size: {metadata["size_mb"]} MB')
                self.stdout.write(f'  Duration: {metadata.get("duration", 0):.2f} seconds')
                self.stdout.write(f'  Checksum: {result["checksum"]}')
                self.stdout.write(f'  Path: {result["backup_path"]}')
        else:
            self.stderr.write(self.style.ERROR(f'✗ Backup failed: {result.get("error", "Unknown error")}'))