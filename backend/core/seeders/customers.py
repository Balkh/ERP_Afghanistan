"""Customer seeder."""
import random
from decimal import Decimal
from sales.models import Customer
from core.seeders.utils import SeederUtils


class CustomerSeeder:
    """Seed customers with realistic data."""

    def __init__(self, company=None):
        self.created_count = 0
        self.skipped_count = 0

    def seed(self, count=50):
        """Create customers - idempotent with code uniqueness."""
        self.created_count = 0
        self.skipped_count = 0

        for i in range(count):
            code = f"CUST-{i+1:04d}"

            # Check if already exists (idempotent)
            if Customer.objects.filter(code=code).exists():
                self.skipped_count += 1
                continue

            is_company = random.random() < 0.40

            if is_company:
                name = f"{random.choice(SeederUtils.company_names())} Branch {i+1}"
                first_name = "Company"
                last_name = "Admin"
                company_name = name
                registration_number = f"REG-{random.randint(10000, 99999)}"
            else:
                first_name = random.choice(SeederUtils.afghan_names())
                last_name = random.choice(SeederUtils.afghan_last_names())
                name = f"{first_name} {last_name}"
                company_name = "N/A"
                registration_number = f"NID-{random.randint(100000, 999999)}"

            Customer.objects.create(
                name=name,
                code=code,
                subtype='COMPANY' if is_company else 'INDIVIDUAL',
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                registration_number=registration_number,
                phone=SeederUtils.generate_phone(),
                email=f"customer{i+1}@example.af",
                address=random.choice(SeederUtils.afghan_cities()),
                city=random.choice(SeederUtils.afghan_cities()),
                credit_limit=SeederUtils.random_decimal(50000, 500000),
                balance=Decimal('0.00'),
                status='ACTIVE' if random.random() > 0.1 else 'INACTIVE',
            )
            self.created_count += 1

        print(f"[OK] Created {self.created_count} customers, skipped {self.skipped_count} (already exists)")
        return Customer.objects.filter(code__startswith='CUST-').order_by('code')