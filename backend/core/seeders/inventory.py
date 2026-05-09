"""Inventory seeder."""
import random
from datetime import timedelta
from decimal import Decimal
from inventory.models import Product, Category, Warehouse, Batch, StockMovement
from core.seeders.utils import SeederUtils


class InventorySeeder:
    """Seed inventory with products, warehouses, and batches."""

    def __init__(self, company=None):
        self.company = company or SeederUtils.get_or_create_company()
        self.created_products = 0
        self.created_batches = 0
        self.skipped_products = 0
        self.skipped_batches = 0

    def seed(self, product_count=100, warehouse_count=10):
        """Create products, categories, warehouses, and batches - idempotent."""

        # Create categories (already uses get_or_create)
        categories = [
            'Analgesics', 'Antibiotics', 'Anti-inflammatory', 'Cardiovascular',
            'Gastrointestinal', 'Respiratory', 'Vitamins & Supplements',
            'Diabetes', 'Surgical', 'IV Solutions'
        ]

        category_objects = []
        for cat_name in categories:
            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={
                    'description': f'Pharmaceutical category: {cat_name}',
                    'is_active': True,
                }
            )
            category_objects.append(category)

        print(f"[OK] Created {len(category_objects)} categories")

        # Get or create default unit
        from inventory.models import Unit
        default_unit, _ = Unit.objects.get_or_create(
            name='Tablet',
            defaults={'symbol': 'tab', 'description': 'Tablet form', 'is_active': True}
        )

        # Create warehouses (already uses get_or_create)
        warehouses = []
        for i in range(warehouse_count):
            warehouse, created = Warehouse.objects.get_or_create(
                code=f"WH-{i+1:02d}",
                defaults={
                    'name': f"Warehouse {i+1} - {random.choice(SeederUtils.afghan_cities())}",
                    'address': random.choice(SeederUtils.afghan_cities()),
                    'is_active': True,
                    'is_default': i == 0,
                }
            )
            warehouses.append(warehouse)

        print(f"[OK] Created {len(warehouses)} warehouses")

        # Create products - one at a time with idempotent check
        product_names = SeederUtils.product_names()[:product_count]
        products = []

        for i, name in enumerate(product_names):
            sku = f"SKU-{random.randint(10000, 99999)}"

            # Check if SKU exists (idempotent)
            if Product.objects.filter(sku=sku).exists():
                self.skipped_products += 1
                continue

            category = random.choice(category_objects)
            product = Product.objects.create(
                name=name,
                sku=sku,
                barcode=f"BC{random.randint(100000000000, 999999999999)}",
                category=category,
                unit=default_unit,
                description=f"Pharmaceutical product: {name}",
                is_active=True,
            )
            products.append(product)
            self.created_products += 1

        print(f"[OK] Created {self.created_products} products, skipped {self.skipped_products} (already exists)")

        # Create batches with varying expiry dates
        self.created_batches = 0
        self.skipped_batches = 0

        for product in products:
            # Create 1-3 batches per product
            num_batches = random.randint(1, 3)

            for b in range(num_batches):
                batch_num = f"BATCH-{product.sku}-{b+1}"

                # Check if batch exists (idempotent)
                if Batch.objects.filter(batch_number=batch_num).exists():
                    self.skipped_batches += 1
                    continue

                # Some batches expired, some near expiry
                if random.random() < 0.15:
                    # Expired
                    expiry = SeederUtils.random_date(60, 0)
                elif random.random() < 0.20:
                    # Near expiry (within 30 days)
                    expiry = SeederUtils.random_date(30, 1)
                else:
                    # Good expiry
                    expiry = SeederUtils.random_date(365, 90)

                quantity = random.randint(100, 1000)
                remaining = int(quantity * random.uniform(0.3, 1.0))

                batch = Batch.objects.create(
                    batch_number=batch_num,
                    product=product,
                    quantity=quantity,
                    remaining_quantity=remaining,
                    purchase_price=SeederUtils.random_decimal(50, 500),
                    sale_price=SeederUtils.random_decimal(100, 1000),
                    manufacturing_date=SeederUtils.random_date(-30, -90),
                    expiry_date=expiry,
                    location=f"SHELF-{random.randint(1, 10)}",
                    is_active=True,
                )

                # Create stock movement for initial stock
                warehouse = random.choice(warehouses)
                movement = StockMovement.objects.create(
                    product=product,
                    warehouse=warehouse,
                    batch=batch,
                    movement_type='IN',
                    reference_type='MANUAL',
                    reference_id=f"INIT-{batch.batch_number}",
                    quantity=quantity,
                    unit_cost=batch.purchase_price,
                    total_cost=Decimal(quantity) * batch.purchase_price,
                    notes=f"Initial stock - {batch.batch_number}",
                    is_active=True,
                )
                self.created_batches += 1

        print(f"[OK] Created {self.created_batches} batches with stock movements, skipped {self.skipped_batches} (already exists)")

        return {
            'categories': category_objects,
            'warehouses': warehouses,
            'products': products,
            'batches': Batch.objects.all()[:self.created_batches],
        }
        
        print(f"[OK] Created {self.created_products} products")
        
        # Create batches with varying expiry dates
        batches = []
        movements = []
        
        for product in products:
            # Create 1-3 batches per product
            num_batches = random.randint(1, 3)
            
            for b in range(num_batches):
                # Some batches expired, some near expiry
                if random.random() < 0.15:
                    # Expired
                    expiry = SeederUtils.random_date(60, 0)
                    days_to_expiry = -abs(random.randint(1, 90))
                elif random.random() < 0.20:
                    # Near expiry (within 30 days)
                    expiry = SeederUtils.random_date(30, 1)
                    days_to_expiry = random.randint(1, 30)
                else:
                    # Good expiry
                    expiry = SeederUtils.random_date(365, 90)
                    days_to_expiry = random.randint(90, 365)
                
                quantity = random.randint(100, 1000)
                remaining = int(quantity * random.uniform(0.3, 1.0))
                
                batch = Batch(
                    batch_number=f"BATCH-{product.sku}-{b+1}",
                    product=product,
                    quantity=quantity,
                    remaining_quantity=remaining,
                    purchase_price=SeederUtils.random_decimal(50, 500),
                    sale_price=SeederUtils.random_decimal(100, 1000),
                    manufacturing_date=SeederUtils.random_date(-30, -90),
                    expiry_date=expiry,
                    location=f"SHELF-{random.randint(1, 10)}",
                    is_active=True,
                )
                batches.append(batch)
                
                # Create stock movement for initial stock
                warehouse = random.choice(warehouses)
                movement = StockMovement(
                    product=product,
                    warehouse=warehouse,
                    batch=batch,
                    movement_type='IN',
                    quantity=quantity,
                    unit_cost=batch.purchase_price,
                    total_cost=Decimal(quantity) * batch.purchase_price,
                    notes=f"Initial stock - {batch.batch_number}",
                    is_active=True,
                )
                movements.append(movement)
        
        Batch.objects.bulk_create(batches)
        StockMovement.objects.bulk_create(movements)
        self.created_batches = len(batches)
        
        print(f"[OK] Created {self.created_batches} batches with stock movements")
        
        return {
            'categories': category_objects,
            'warehouses': warehouses,
            'products': products,
            'batches': batches,
        }