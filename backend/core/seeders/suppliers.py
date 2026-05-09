"""Supplier seeder."""
import random
from decimal import Decimal
from purchases.models import Supplier
from core.seeders.utils import SeederUtils


class SupplierSeeder:
    """Seed suppliers with realistic data."""

    def __init__(self, company=None):
        self.created_count = 0
        self.skipped_count = 0

    def seed(self, count=20):
        """Create suppliers - idempotent with code uniqueness."""
        self.created_count = 0
        self.skipped_count = 0

        for i in range(count):
            code = f"SUP-{i+1:03d}"

            # Check if already exists (idempotent)
            if Supplier.objects.filter(code=code).exists():
                self.skipped_count += 1
                continue

            is_company = random.random() < 0.60

            if is_company:
                name = random.choice(SeederUtils.company_names())
                company_name = name
            else:
                name = f"{random.choice(SeederUtils.afghan_names())} {random.choice(SeederUtils.afghan_last_names())} Supplier"
                company_name = "N/A"

            Supplier.objects.create(
                name=name,
                code=code,
                subtype='COMPANY' if is_company else 'INDIVIDUAL',
                company_name=company_name,
                phone=SeederUtils.generate_phone(),
                email=f"supplier{i+1}@example.af",
                address=random.choice(SeederUtils.afghan_cities()),
                city=random.choice(SeederUtils.afghan_cities()),
                supply_categories='Pharmaceuticals,Medical Supplies',
                bank_name=random.choice(['Afghanistan International Bank', 'Afghanistan National Development Bank', 'Maiwand Bank']),
                bank_account=f"AF{random.randint(100000000, 999999999)}",
                credit_limit=SeederUtils.random_decimal(100000, 1000000),
                balance=Decimal('0.00'),
                payment_terms_days=random.choice([30, 45, 60, 90]),
                lead_time_days=random.randint(3, 30),
                quality_rating=random.randint(1, 5),
                status='ACTIVE' if random.random() > 0.1 else 'INACTIVE',
            )
            self.created_count += 1

        print(f"[OK] Created {self.created_count} suppliers, skipped {self.skipped_count} (already exists)")
        return Supplier.objects.filter(code__startswith='SUP-').order_by('code')