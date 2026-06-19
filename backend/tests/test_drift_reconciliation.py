"""
Tests for StockDriftReconciliation service.
Verifies drift detection between Batch.remaining_quantity and StockMovement aggregates.
"""
import uuid
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from inventory.models import Batch, Product, Category, Unit, Warehouse, StockMovement
from inventory.services.drift_reconciliation import (
    StockDriftReconciliation,
    DriftReconciliationResult,
    BatchDrift,
)


class BaseReconciliationTestCase(TestCase):
    """Shared fixtures for reconciliation tests."""

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB')
        self.product = Product.objects.create(
            name='Test Product',
            generic_name='Generic Test',
            brand_name='Brand Test',
            category=self.category,
            unit=self.unit,
            strength='100mg',
            form='Tablet',
            manufacturer='Test Mfg',
            barcode=f'BC{uuid.uuid4().hex[:10]}',
            sku=f'SKU{uuid.uuid4().hex[:8]}',
        )
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            code=f'WH{uuid.uuid4().hex[:4]}'.upper(),
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number=f'BATCH-{uuid.uuid4().hex[:8]}',
            manufacturing_date=timezone.now().date() - timedelta(days=180),
            expiry_date=timezone.now().date() + timedelta(days=365),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id),
        )


class TestCheckBatchNoDrift(BaseReconciliationTestCase):
    """Test batch with matching remaining_quantity and movements."""

    def test_no_movements_zero_drift(self):
        """Batch with no movements and remaining_quantity=0 → no drift."""
        self.batch.remaining_quantity = Decimal('0')
        self.batch.save()

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNone(drift)

    def test_movements_match_stored_quantity(self):
        """Batch remaining_quantity matches sum of IN movements → no drift."""
        # Create IN movement of +100
        StockMovement.objects.create(
            product=self.product,
            batch=self.batch,
            warehouse=self.warehouse,
            movement_type='IN',
            reference_type='PURCHASE',
            reference_id='INV-001',
            quantity=Decimal('100.00'),
            unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNone(drift)

    def test_in_and_out_movements_match(self):
        """Batch with +100 IN and -30 OUT matches remaining_quantity=70 → no drift."""
        self.batch.remaining_quantity = Decimal('70.00')
        self.batch.save()

        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='OUT', reference_type='SALE', reference_id='S-1',
            quantity=Decimal('-30.00'), unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNone(drift)


class TestCheckBatchWithDrift(BaseReconciliationTestCase):
    """Test batch with mismatched remaining_quantity and movements."""

    def test_stored_higher_than_computed(self):
        """stored=100 but computed=80 → drift of +20."""
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('50.00'), unit_cost=Decimal('10.00'),
        )
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-2',
            quantity=Decimal('30.00'), unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNotNone(drift)
        self.assertEqual(drift.stored_quantity, Decimal('100.00'))
        self.assertEqual(drift.computed_quantity, Decimal('80.00'))
        self.assertEqual(drift.drift_amount, Decimal('20.00'))

    def test_stored_lower_than_computed(self):
        """stored=50 but computed=100 → drift of -50."""
        self.batch.remaining_quantity = Decimal('50.00')
        self.batch.save()

        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNotNone(drift)
        self.assertEqual(drift.drift_amount, Decimal('-50.00'))

    def test_transfer_movements_excluded(self):
        """TRANSFER movements should not count toward computed quantity."""
        self.batch.remaining_quantity = Decimal('100.00')
        self.batch.save()

        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )
        # Transfer OUT should NOT affect computed quantity
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='TRANSFER', reference_type='MANUAL', reference_id='T-1',
            quantity=Decimal('-50.00'), unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        # stored=100, computed=100 (transfer excluded) → no drift
        self.assertIsNone(drift)

    def test_inactive_movements_excluded(self):
        """is_active=False movements should not count."""
        self.batch.remaining_quantity = Decimal('100.00')
        self.batch.save()

        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='MANUAL', reference_id='M-1',
            quantity=Decimal('50.00'), unit_cost=Decimal('10.00'),
            is_active=False,
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNone(drift)

    def test_tolerance_allows_small_drift(self):
        """Drift within tolerance should not be reported."""
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('99.99'), unit_cost=Decimal('10.00'),
        )

        # stored=100, computed=99.99 → drift=0.01
        drift = StockDriftReconciliation.check_batch(
            self.batch, tolerance=Decimal('0.01'),
        )
        self.assertIsNone(drift)

        # But without tolerance, it IS drift
        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertIsNotNone(drift)

    def test_drift_includes_product_and_warehouse_names(self):
        """Drift result should include human-readable product and warehouse names."""
        self.batch.remaining_quantity = Decimal('50.00')
        self.batch.save()

        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )

        drift = StockDriftReconciliation.check_batch(self.batch)
        self.assertEqual(drift.product_name, str(self.product))
        self.assertEqual(drift.warehouse_name, str(self.warehouse.id))


class TestFullReconciliation(BaseReconciliationTestCase):
    """Test full reconciliation across multiple batches."""

    def setUp(self):
        super().setUp()
        # Create a second batch
        self.batch2 = Batch.objects.create(
            product=self.product,
            batch_number=f'BATCH-{uuid.uuid4().hex[:8]}',
            manufacturing_date=timezone.now().date() - timedelta(days=90),
            expiry_date=timezone.now().date() + timedelta(days=300),
            purchase_price=Decimal('12.00'),
            sale_price=Decimal('18.00'),
            quantity=Decimal('50.00'),
            remaining_quantity=Decimal('50.00'),
            location=str(self.warehouse.id),
        )

    def test_all_clean(self):
        """Both batches have matching movements → healthy result."""
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )
        StockMovement.objects.create(
            product=self.product, batch=self.batch2, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-2',
            quantity=Decimal('50.00'), unit_cost=Decimal('12.00'),
        )

        result = StockDriftReconciliation.run_full_reconciliation()
        self.assertTrue(result.is_healthy)
        self.assertEqual(result.total_batches_checked, 2)
        self.assertEqual(result.batches_clean, 2)
        self.assertEqual(result.batches_with_drift, 0)
        self.assertEqual(result.health_score, 100.0)

    def test_one_drifted(self):
        """One batch has drift → unhealthy result."""
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )
        # batch2 has no movements but remaining_quantity=50 → drift

        result = StockDriftReconciliation.run_full_reconciliation()
        self.assertFalse(result.is_healthy)
        self.assertEqual(result.total_batches_checked, 2)
        self.assertEqual(result.batches_clean, 1)
        self.assertEqual(result.batches_with_drift, 1)
        self.assertEqual(result.health_score, 50.0)

    def test_filter_by_product(self):
        """Filtering by product_id only checks that product's batches."""
        other_product = Product.objects.create(
            name='Other Product',
            generic_name='Other Generic',
            brand_name='Other Brand',
            category=self.category,
            unit=self.unit,
            strength='50mg',
            form='Tablet',
            manufacturer='Other Mfg',
            barcode=f'BC{uuid.uuid4().hex[:10]}',
            sku=f'SKU{uuid.uuid4().hex[:8]}',
        )
        # other_batch has remaining_quantity=200 but NO movements → would drift
        other_batch = Batch.objects.create(
            product=other_product,
            batch_number=f'BATCH-{uuid.uuid4().hex[:8]}',
            manufacturing_date=timezone.now().date() - timedelta(days=60),
            expiry_date=timezone.now().date() + timedelta(days=200),
            purchase_price=Decimal('8.00'),
            sale_price=Decimal('12.00'),
            quantity=Decimal('200.00'),
            remaining_quantity=Decimal('200.00'),
            location=str(self.warehouse.id),
        )

        # Only check our product → other_batch is excluded
        result = StockDriftReconciliation.run_full_reconciliation(
            product_id=self.product.id,
        )
        self.assertEqual(result.total_batches_checked, 2)  # batch + batch2
        # other_batch drift is NOT in results
        drifted_ids = [d.batch_id for d in result.drifts]
        self.assertNotIn(str(other_batch.id), drifted_ids)

    def test_empty_database(self):
        """No batches → healthy with 100% score."""
        Batch.objects.all().delete()

        result = StockDriftReconciliation.run_full_reconciliation()
        self.assertTrue(result.is_healthy)
        self.assertEqual(result.total_batches_checked, 0)
        self.assertEqual(result.health_score, 100.0)

    def test_drift_summary_dict(self):
        """get_drift_summary returns a well-formed dict."""
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=Decimal('100.00'), unit_cost=Decimal('10.00'),
        )

        summary = StockDriftReconciliation.get_drift_summary()
        self.assertIn('is_healthy', summary)
        self.assertIn('health_score', summary)
        self.assertIn('total_batches_checked', summary)
        self.assertIn('drifts', summary)
        self.assertIsInstance(summary['drifts'], list)


class TestReconciliationResult(BaseReconciliationTestCase):
    """Test DriftReconciliationResult dataclass behavior."""

    def test_health_score_with_zero_batches(self):
        result = DriftReconciliationResult()
        self.assertEqual(result.health_score, 100.0)

    def test_batch_with_null_warehouse(self):
        """Batch with warehouse=None should be handled gracefully."""
        # Add movement for setUp batch so it doesn't drift
        StockMovement.objects.create(
            product=self.product, batch=self.batch, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-1',
            quantity=self.batch.remaining_quantity, unit_cost=Decimal('10.00'),
        )

        batch_no_wh = Batch.objects.create(
            product=self.product,
            batch_number=f'BATCH-{uuid.uuid4().hex[:8]}',
            manufacturing_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=300),
            purchase_price=Decimal('5.00'),
            sale_price=Decimal('8.00'),
            quantity=Decimal('25.00'),
            remaining_quantity=Decimal('25.00'),
            location='',
        )
        StockMovement.objects.create(
            product=self.product, batch=batch_no_wh, warehouse=self.warehouse,
            movement_type='IN', reference_type='PURCHASE', reference_id='P-NULL',
            quantity=Decimal('25.00'), unit_cost=Decimal('5.00'),
        )

        drift = StockDriftReconciliation.check_batch(batch_no_wh)
        self.assertIsNone(drift)
        # Verify full reconciliation handles null-warehouse batch
        result = StockDriftReconciliation.run_full_reconciliation(
            product_id=self.product.id,
        )
        self.assertTrue(result.is_healthy)
