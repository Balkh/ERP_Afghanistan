"""Regression: allocate_stock must filter batches by warehouse via the
`location` field (Batch has no `warehouse` FK after migration 0015)."""
import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.db import transaction
from django.utils import timezone

from inventory.models import Batch, Product, Category, Unit, Warehouse
from inventory.service import StockSelectionMode
from inventory.service.stock_integration import StockIntegrationService


def _make_product():
    cat = Category.objects.create(name=f'Cat {uuid.uuid4().hex[:6]}')
    unit = Unit.objects.create(name=f'Unit {uuid.uuid4().hex[:6]}', symbol='U')
    return Product.objects.create(
        name='P', generic_name='G', brand_name='B', category=cat, unit=unit,
        strength='100mg', form='Tablet', manufacturer='M',
        barcode=f'BC{uuid.uuid4().hex[:10]}', sku=f'SKU{uuid.uuid4().hex[:8]}',
    )


@pytest.mark.django_db
def test_allocate_stock_with_batch_id_and_warehouse():
    wh = Warehouse.objects.create(name='WH', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    product = _make_product()
    batch = Batch.objects.create(
        product=product, batch_number=f'B-{uuid.uuid4().hex[:8]}',
        manufacturing_date=timezone.now().date() - timedelta(days=30),
        expiry_date=timezone.now().date() + timedelta(days=300),
        purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
        quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'),
        location=str(wh.id),
    )

    # This path previously raised FieldError (filter(warehouse=...)).
    with transaction.atomic():
        result = StockIntegrationService.allocate_stock(
            product=product, quantity=Decimal('40.00'), warehouse=wh,
            selection_mode=StockSelectionMode.FEFO, batch_id=batch.id,
        )

    assert result.success is True
    assert len(result.allocations) == 1
    assert result.allocations[0].quantity == Decimal('40.00')
    assert result.allocations[0].batch_id == batch.id


@pytest.mark.django_db
def test_allocate_stock_batch_in_other_warehouse_excluded():
    wh1 = Warehouse.objects.create(name='WH1', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    wh2 = Warehouse.objects.create(name='WH2', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    product = _make_product()
    batch = Batch.objects.create(
        product=product, batch_number=f'B-{uuid.uuid4().hex[:8]}',
        manufacturing_date=timezone.now().date() - timedelta(days=30),
        expiry_date=timezone.now().date() + timedelta(days=300),
        purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
        quantity=Decimal('100.00'), remaining_quantity=Decimal('100.00'),
        location=str(wh1.id),
    )

    # Requesting the batch but constrained to a different warehouse -> no match.
    with transaction.atomic():
        result = StockIntegrationService.allocate_stock(
            product=product, quantity=Decimal('10.00'), warehouse=wh2,
            selection_mode=StockSelectionMode.FEFO, batch_id=batch.id,
        )

    assert result.success is False
