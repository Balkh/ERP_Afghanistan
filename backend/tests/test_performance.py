import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.db import reset_queries
from datetime import date, timedelta
import uuid

User = get_user_model()


class TestDatabasePerformance(TestCase):
    """Test database query performance."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'perf_test_{uuid.uuid4().hex[:8]}',
            email=f'perf_{uuid.uuid4().hex[:8]}@test.com',
            password='testpass123'
        )

    def test_product_query_performance(self):
        """Test product list query count."""
        from inventory.models import Product, Category, Unit

        category = Category.objects.create(name=f"PerfCat{uuid.uuid4().hex[:6]}")
        unit = Unit.objects.create(name=f"Unit{uuid.uuid4().hex[:4]}", symbol=f"U{uuid.uuid4().hex[:4]}")

        for i in range(20):
            Product.objects.create(
                name=f"Product {i}",
                sku=f"SKU{uuid.uuid4().hex[:6]}{i}",
                barcode=f"BAR{uuid.uuid4().hex[:6]}",
                category=category,
                unit=unit,
                generic_name="Test",
                brand_name="Brand",
                strength="100mg",
                form="Tablet",
                manufacturer="Mfg"
            )

        reset_queries()
        start_time = time.time()

        products = Product.objects.select_related('category', 'unit').all()
        list(products)
        
        elapsed = time.time() - start_time
        query_count = len(connection.queries)
        
        self.assertLess(elapsed, 1.0, f"Query took {elapsed:.2f}s")
        self.assertLess(query_count, 10, f"Too many queries: {query_count}")

    def test_batch_creation_performance(self):
        """Test batch creation performance."""
        from inventory.models import Product, Batch, Category, Unit
        from django.utils import timezone

        category = Category.objects.create(name=f"BatchCat{uuid.uuid4().hex[:6]}")
        unit = Unit.objects.create(name=f"BatchUnit{uuid.uuid4().hex[:4]}", symbol=f"BU{uuid.uuid4().hex[:4]}")
        
        pid = uuid.uuid4().hex[:6]
        product = Product.objects.create(
            name=f"BatchProduct", 
            sku=f"BATCH{pid}", 
            barcode=f"BATCH{uuid.uuid4().hex[:6]}",
            category=category, 
            unit=unit,
            generic_name="Test", 
            brand_name="Brand", 
            strength="100mg",
            form="Tablet", 
            manufacturer="Mfg"
        )

        start_time = time.time()
        today = timezone.now().date()

        for i in range(20):
            Batch.objects.create(
                product=product,
                batch_number=f"BATCH{uuid.uuid4().hex[:6]}",
                quantity=100,
                remaining_quantity=100,
                purchase_price=10.00,
                sale_price=15.00,
                expiry_date=today + timedelta(days=365),
                manufacturing_date=today,
                location="WH"
            )

        elapsed = time.time() - start_time
        self.assertLess(elapsed, 3.0, f"Batch creation took {elapsed:.2f}s")

    def test_category_query_performance(self):
        """Test category query performance."""
        from inventory.models import Category, Product, Unit

        parent = Category.objects.create(name=f"Parent{uuid.uuid4().hex[:6]}")

        for i in range(30):
            Category.objects.create(name=f"Cat{i}_{uuid.uuid4().hex[:4]}", parent=parent)

        reset_queries()
        
        categories = Category.objects.prefetch_related('children').all()
        list(categories)
        
        query_count = len(connection.queries)
        self.assertLess(query_count, 5, f"Too many queries: {query_count}")

    def test_unit_query_performance(self):
        """Test unit query performance."""
        from inventory.models import Unit

        for i in range(50):
            Unit.objects.get_or_create(name=f"Unit{i}_{uuid.uuid4().hex[:4]}", symbol=f"U{uuid.uuid4().hex[:4]}")

        reset_queries()
        
        units = Unit.objects.all()
        list(units)
        
        query_count = len(connection.queries)
        self.assertLess(query_count, 5, f"Too many queries: {query_count}")


class TestSerializerPerformance(TestCase):
    """Test serializer performance."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'ser_test_{uuid.uuid4().hex[:8]}',
            email=f'ser_{uuid.uuid4().hex[:8]}@test.com',
            password='testpass123'
        )

    def test_product_serializer_efficiency(self):
        """Test product serializer efficiency."""
        from inventory.models import Product, Category, Unit
        from inventory.serializers import ProductSerializer

        category = Category.objects.create(name=f"SerCat{uuid.uuid4().hex[:6]}")
        unit = Unit.objects.create(name=f"SerUnit{uuid.uuid4().hex[:4]}", symbol=f"SU{uuid.uuid4().hex[:4]}")

        for i in range(20):
            Product.objects.create(
                name=f"Product {i}",
                sku=f"SKU{uuid.uuid4().hex[:6]}{i}",
                barcode=f"BAR{uuid.uuid4().hex[:6]}",
                category=category,
                unit=unit,
                generic_name="Test",
                brand_name="Brand",
                strength="100mg",
                form="Tablet",
                manufacturer="Mfg"
            )

        products = Product.objects.all()

        start_time = time.time()
        serializer = ProductSerializer(products, many=True)
        data = serializer.data
        elapsed = time.time() - start_time

        self.assertEqual(len(data), 20)
        self.assertLess(elapsed, 0.5, f"Serialization took {elapsed:.2f}s")

    def test_category_serializer_efficiency(self):
        """Test category serializer efficiency."""
        from inventory.models import Category
        from inventory.serializers import CategorySerializer

        for i in range(50):
            Category.objects.get_or_create(name=f"Cat{i}_{uuid.uuid4().hex[:4]}")

        categories = Category.objects.all()

        start_time = time.time()
        from inventory.serializers import CategorySerializer
        serializer = CategorySerializer(categories, many=True)
        data = serializer.data
        elapsed = time.time() - start_time

        self.assertEqual(len(data), 50)
        self.assertLess(elapsed, 0.5, f"Serialization took {elapsed:.2f}s")


class TestConcurrentOperations(TestCase):
    """Test concurrent database operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'conc_test_{uuid.uuid4().hex[:8]}',
            email=f'conc_{uuid.uuid4().hex[:8]}@test.com',
            password='testpass123'
        )

    def test_sequential_batch_creation(self):
        """Test sequential batch creation performance (concurrent test skipped due to SQLite)."""
        from inventory.models import Product, Batch, Category, Unit
        from django.utils import timezone

        category = Category.objects.create(name=f"ConcCat{uuid.uuid4().hex[:6]}")
        unit = Unit.objects.create(name=f"ConcUnit{uuid.uuid4().hex[:4]}", symbol=f"CU{uuid.uuid4().hex[:4]}")
        
        pid = uuid.uuid4().hex[:6]
        product = Product.objects.create(
            name="ConcProduct", 
            sku=f"CONC{pid}", 
            barcode=f"CONC{uuid.uuid4().hex[:6]}",
            category=category, 
            unit=unit,
            generic_name="Test", 
            brand_name="Brand", 
            strength="100mg",
            form="Tablet", 
            manufacturer="Mfg"
        )

        today = timezone.now().date()

        start_time = time.time()

        for i in range(10):
            Batch.objects.create(
                product=product,
                batch_number=f"CONCBATCH{uuid.uuid4().hex[:6]}",
                quantity=100,
                remaining_quantity=100,
                purchase_price=10.00,
                sale_price=15.00,
                expiry_date=today + timedelta(days=365),
                manufacturing_date=today,
                location="WH"
            )

        elapsed = time.time() - start_time

        self.assertLess(elapsed, 3.0, f"Sequential creation took {elapsed:.2f}s")


class TestLoadPerformance(TestCase):
    """Test load and stress scenarios."""

    def setUp(self):
        self.user = User.objects.create_user(
            username=f'load_test_{uuid.uuid4().hex[:8]}',
            email=f'load_{uuid.uuid4().hex[:8]}@test.com',
            password='testpass123'
        )

    def test_repeated_query_performance(self):
        """Test repeated query performance."""
        from inventory.models import Category

        for i in range(10):
            Category.objects.get_or_create(name=f"LoadCat{i}_{uuid.uuid4().hex[:4]}")

        times = []
        for _ in range(10):
            start = time.time()
            list(Category.objects.all())
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)
        self.assertLess(avg_time, 0.1, f"Average query time {avg_time:.4f}s too high")

    def test_bulk_create_performance(self):
        """Test bulk create performance."""
        from inventory.models import Category

        start_time = time.time()

        categories = [
            Category(name=f"BulkCat{i}_{uuid.uuid4().hex[:4]}")
            for i in range(50)
        ]
        Category.objects.bulk_create(categories)

        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0, f"Bulk create took {elapsed:.2f}s")

    def test_complex_join_performance(self):
        """Test complex join query performance."""
        from inventory.models import Product, Category, Unit
        from django.db.models import Count

        category = Category.objects.create(name=f"JoinCat{uuid.uuid4().hex[:6]}")
        unit = Unit.objects.create(name=f"JoinUnit{uuid.uuid4().hex[:4]}", symbol=f"JU{uuid.uuid4().hex[:4]}")

        for i in range(30):
            Product.objects.create(
                name=f"Product {i}",
                sku=f"SKU{uuid.uuid4().hex[:6]}{i}",
                barcode=f"BAR{uuid.uuid4().hex[:6]}",
                category=category,
                unit=unit,
                generic_name="Test",
                brand_name="Brand",
                strength="100mg",
                form="Tablet",
                manufacturer="Mfg"
            )

        start_time = time.time()

        result = Category.objects.annotate(
            product_count=Count('product')
        ).filter(id=category.id).values('name', 'product_count').first()

        elapsed = time.time() - start_time

        self.assertIsNotNone(result)
        self.assertEqual(result['product_count'], 30)
        self.assertLess(elapsed, 0.5, f"Join query took {elapsed:.2f}s")