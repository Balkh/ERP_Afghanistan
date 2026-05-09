from decimal import Decimal
from django.core.management.base import BaseCommand
from payments.models import PaymentMethod, PaymentAccount
from accounting.models import Account


class Command(BaseCommand):
    help = 'Seed default payment methods and accounts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding payment methods...')
        self._seed_payment_methods()
        self.stdout.write(self.style.SUCCESS('Payment methods seeded.'))

        self.stdout.write('Seeding payment accounts...')
        self._seed_payment_accounts()
        self.stdout.write(self.style.SUCCESS('Payment accounts seeded.'))

    def _seed_payment_methods(self):
        methods = [
            {
                'name': 'Cash',
                'code': 'CASH',
                'method_type': 'CASH',
                'description': 'Cash payments',
                'is_active': True,
                'is_default': True,
                'fee_percentage': Decimal('0.00'),
                'fee_fixed': Decimal('0.00'),
                'ref_prefix': 'CASH',
            },
            {
                'name': 'Bank Transfer',
                'code': 'BANK',
                'method_type': 'BANK_TRANSFER',
                'description': 'Direct bank transfers',
                'is_active': True,
                'is_default': True,
                'provider_name': 'Afghanistan International Bank',
                'provider_code': 'AIB',
                'fee_percentage': Decimal('0.50'),
                'fee_fixed': Decimal('50.00'),
                'ref_prefix': 'BANK',
            },
            {
                'name': 'Mobile Money',
                'code': 'MOBILE',
                'method_type': 'MOBILE_MONEY',
                'description': 'Mobile money payments',
                'is_active': True,
                'is_default': True,
                'provider_name': 'M-Paisa',
                'provider_code': 'MPAIS',
                'fee_percentage': Decimal('1.50'),
                'fee_fixed': Decimal('10.00'),
                'ref_prefix': 'MOB',
            },
            {
                'name': 'Hawala',
                'code': 'HAWALA',
                'method_type': 'HAWALA',
                'description': 'Hawala money transfer',
                'is_active': True,
                'is_default': True,
                'provider_name': 'Al-Farooq Hawala',
                'provider_code': 'AFHAW',
                'fee_percentage': Decimal('2.00'),
                'fee_fixed': Decimal('100.00'),
                'ref_prefix': 'HAW',
            },
            {
                'name': 'Cheque',
                'code': 'CHEQUE',
                'method_type': 'CHEQUE',
                'description': 'Cheque payments',
                'is_active': True,
                'is_default': False,
                'fee_percentage': Decimal('0.00'),
                'fee_fixed': Decimal('0.00'),
                'ref_prefix': 'CHQ',
            },
            {
                'name': 'Credit Card',
                'code': 'CC',
                'method_type': 'CREDIT_CARD',
                'description': 'Credit card payments',
                'is_active': True,
                'is_default': False,
                'provider_name': 'Visa/Mastercard',
                'provider_code': 'VISA',
                'fee_percentage': Decimal('2.50'),
                'fee_fixed': Decimal('0.00'),
                'ref_prefix': 'CC',
            },
        ]

        created_count = 0
        for method_data in methods:
            _, created = PaymentMethod.objects.get_or_create(
                code=method_data['code'],
                defaults=method_data
            )
            if created:
                created_count += 1

        self.stdout.write(f'  Created {created_count} payment methods')

    def _seed_payment_accounts(self):
        # Find accounting accounts to link to - use proper hierarchy
        try:
            # Get parent accounts
            cash_parent = Account.objects.filter(code='1110', is_active=True).first()  # Cash
            bank_parent = Account.objects.filter(code='1120', is_active=True).first()   # Bank Accounts
            
            # Create or get specific accounts under the parents
            cash_account, _ = Account.objects.get_or_create(
                code='1111',
                defaults={
                    'name': 'Cash on Hand',
                    'account_type': 'ASSET',
                    'account_category': 'CURRENT_ASSET',
                    'parent': cash_parent,
                    'is_active': True,
                    'is_system': False,
                    'currency': None  # Will be set per payment account
                }
            )
            
            bank_account, _ = Account.objects.get_or_create(
                code='1121',
                defaults={
                    'name': 'Bank Account - AIB',
                    'account_type': 'ASSET',
                    'account_category': 'CURRENT_ASSET',
                    'parent': bank_parent,
                    'is_active': True,
                    'is_system': False,
                    'currency': None  # Will be set per payment account
                }
            )
            
            mobile_account, _ = Account.objects.get_or_create(
                code='1112',
                defaults={
                    'name': 'Mobile Money Account',
                    'account_type': 'ASSET',
                    'account_category': 'CURRENT_ASSET',
                    'parent': cash_parent,
                    'is_active': True,
                    'is_system': False,
                    'currency': None  # Will be set per payment account
                }
            )
            
            hawala_account, _ = Account.objects.get_or_create(
                code='1113',
                defaults={
                    'name': 'Hawala Account',
                    'account_type': 'ASSET',
                    'account_category': 'CURRENT_ASSET',
                    'parent': cash_parent,
                    'is_active': True,
                    'is_system': False,
                    'currency': None  # Will be set per payment account
                }
            )
        except Exception as e:
            print(f"Error getting/creating accounts: {e}")
            # Fallback to generic asset account
            cash_parent = Account.objects.filter(account_type='ASSET', is_active=True).first()
            cash_account = bank_account = mobile_account = hawala_account = cash_parent

        accounts = [
            {
                'name': 'Main Cash Drawer',
                'code': 'CA-001',
                'account_type': 'CASH',
                'accounting_account': cash_account,
                'currency': 'AFN',
                'is_active': True,
                'is_default': True,
                'location': 'Main Counter',
            },
            {
                'name': 'USD Cash Drawer',
                'code': 'CA-002',
                'account_type': 'CASH',
                'accounting_account': cash_account,
                'currency': 'USD',
                'is_active': True,
                'is_default': False,
                'location': 'Main Counter',
            },
            {
                'name': 'AIB Bank Account',
                'code': 'BA-001',
                'account_type': 'BANK',
                'accounting_account': bank_account,
                'provider_name': 'Afghanistan International Bank',
                'account_number': 'AF1234567890',
                'currency': 'AFN',
                'is_active': True,
                'is_default': True,
            },
            {
                'name': 'M-Paisa Wallet',
                'code': 'MW-001',
                'account_type': 'MOBILE_WALLET',
                'accounting_account': mobile_account,
                'provider_name': 'M-Paisa',
                'account_number': '+93700000001',
                'currency': 'AFN',
                'is_active': True,
                'is_default': True,
            },
            {
                'name': 'Al-Farooq Hawala',
                'code': 'HA-001',
                'account_type': 'HAWALA',
                'accounting_account': hawala_account,
                'provider_name': 'Al-Farooq Hawala',
                'currency': 'AFN',
                'is_active': True,
                'is_default': True,
            },
        ]

        created_count = 0
        for account_data in accounts:
            if not account_data['accounting_account']:
                continue
            _, created = PaymentAccount.objects.get_or_create(
                code=account_data['code'],
                defaults=account_data
            )
            if created:
                created_count += 1

        self.stdout.write(f'  Created {created_count} payment accounts')