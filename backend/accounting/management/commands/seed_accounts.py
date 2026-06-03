"""Seed the canonical Chart of Accounts.

Idempotent — safe to run multiple times.
Only creates accounts that do not already exist (matched by code).
"""
from django.core.management.base import BaseCommand
from accounting.models import Account


CANONICAL_CHART_OF_ACCOUNTS = [
    {
        'code': '1000',
        'name': 'Cash',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': True,
    },
    {
        'code': '1010',
        'name': 'Main Cash AFN',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1100',
        'name': 'Cash',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1110',
        'name': 'Cash on Hand',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1111',
        'name': 'Cash on Hand',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1112',
        'name': 'Mobile Money Account',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1113',
        'name': 'Hawala Account',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1120',
        'name': 'Bank Accounts',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1121',
        'name': 'Bank Account - AIB',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '1200',
        'name': 'Accounts Receivable',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': True,
    },
    {
        'code': '1300',
        'name': 'Inventory',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': True,
    },
    {
        'code': '1400',
        'name': 'Inventory',
        'account_type': 'ASSET',
        'account_category': 'CURRENT_ASSET',
        'is_system': False,
    },
    {
        'code': '2100',
        'name': 'Accounts Payable',
        'account_type': 'LIABILITY',
        'account_category': 'CURRENT_LIABILITY',
        'is_system': True,
    },
    {
        'code': '2200',
        'name': 'Unearned Revenue',
        'account_type': 'LIABILITY',
        'account_category': 'CURRENT_LIABILITY',
        'is_system': False,
    },
    {
        'code': '4000',
        'name': 'Sales Revenue',
        'account_type': 'REVENUE',
        'account_category': 'OPERATING_REVENUE',
        'is_system': True,
    },
    {
        'code': '4100',
        'name': 'Sales Revenue',
        'account_type': 'REVENUE',
        'account_category': 'OPERATING_REVENUE',
        'is_system': True,
    },
    {
        'code': '4200',
        'name': 'Sales Returns',
        'account_type': 'REVENUE',
        'account_category': 'OPERATING_REVENUE',
        'is_system': False,
    },
    {
        'code': '5000',
        'name': 'Purchases',
        'account_type': 'EXPENSE',
        'account_category': 'COST_OF_GOODS_SOLD',
        'is_system': True,
    },
    {
        'code': '5100',
        'name': 'COGS',
        'account_type': 'EXPENSE',
        'account_category': 'COST_OF_GOODS_SOLD',
        'is_system': True,
    },
    {
        'code': '5200',
        'name': 'Purchase Returns',
        'account_type': 'EXPENSE',
        'account_category': 'COST_OF_GOODS_SOLD',
        'is_system': False,
    },
    {
        'code': '6100',
        'name': 'Operating Expenses',
        'account_type': 'EXPENSE',
        'account_category': 'OPERATING_EXPENSE',
        'is_system': True,
    },
]


class Command(BaseCommand):
    help = 'Seed the canonical Chart of Accounts (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-system',
            action='store_true',
            help='Do not skip system accounts (advanced). Default: skip if any account exists.',
        )

    def handle(self, *args, **options):
        existing_count = Account.objects.count()

        if existing_count > 0 and not options.get('reset_system'):
            self.stdout.write(
                f'Chart of Accounts already seeded ({existing_count} accounts). Skipping.'
            )
            return

        created = 0
        skipped = 0
        for account_data in CANONICAL_CHART_OF_ACCOUNTS:
            obj, was_created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults=account_data,
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {obj.code} - {obj.name}")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Chart of Accounts seeded: {created} created, {skipped} skipped (already exist).'
        ))


def seed_canonical_chart_of_accounts() -> int:
    """Programmatic API for the bootstrap orchestrator.

    Returns the number of accounts that were created (excludes skipped).
    Idempotent: re-running will not create duplicates.
    """
    if Account.objects.count() > 0:
        return 0

    created = 0
    for account_data in CANONICAL_CHART_OF_ACCOUNTS:
        _, was_created = Account.objects.get_or_create(
            code=account_data['code'],
            defaults=account_data,
        )
        if was_created:
            created += 1
    return created
