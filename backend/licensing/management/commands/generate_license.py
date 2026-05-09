from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from licensing.services import LicenseService


class Command(BaseCommand):
    help = 'Generate a device license for the current machine'

    def add_arguments(self, parser):
        parser.add_argument(
            '--license-key',
            type=str,
            help='License key to use (if not provided, will prompt)'
        )
        parser.add_argument(
            '--issued-to',
            type=str,
            help='Name/organization to issue license to (if not provided, will prompt)'
        )
        parser.add_argument(
            '--expires-date',
            type=str,
            help='Expiration date in YYYY-MM-DD format (leave blank for perpetual)'
        )
        parser.add_argument(
            '--notes',
            type=str,
            help='Additional notes (optional)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing license with same key'
        )

    def handle(self, *args, **options):
        license_key = options['license_key']
        issued_to = options['issued_to']
        expires_date_str = options['expires_date']
        notes = options['notes']
        force = options['force']

        # Prompt for missing information
        if not license_key:
            license_key = input('Enter license key: ').strip()
            if not license_key:
                self.stdout.write(
                    self.style.ERROR('License key is required')
                )
                return

        # Check if license key already exists
        from licensing.models import DeviceLicense
        if not force and DeviceLicense.objects.filter(license_key=license_key).exists():
            self.stdout.write(
                self.style.ERROR(
                    f"License key '{license_key}' already exists. "
                    "Use --force to overwrite."
                )
            )
            return

        if not issued_to:
            issued_to = input('Enter organization name: ').strip()
            if not issued_to:
                issued_to = 'Unknown'

        expires_date = None
        if expires_date_str:
            try:
                from datetime import datetime
                expires_date = datetime.strptime(expires_date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return

        try:
            license_obj = LicenseService.create_license(
                license_key=license_key,
                issued_to=issued_to,
                expires_date=expires_date,
                notes=notes
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created license for current device'
                )
            )
            self.stdout.write(f'License Key: {license_obj.license_key}')
            self.stdout.write(f'Device ID: {license_obj.device_id}')
            self.stdout.write(f'Issued To: {license_obj.issued_to}')
            self.stdout.write(f'Expires: {"Perpetual" if license_obj.expires_date is None else license_obj.expires_date}')
            
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Validation error: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating license: {e}')
            )