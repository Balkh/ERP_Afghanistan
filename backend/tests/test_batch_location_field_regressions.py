"""Regression tests for stale `Batch.warehouse` references after migration 0015
reverted the warehouse FK back to a `location` CharField.

Each of these code paths previously raised FieldError / AttributeError because
they referenced a removed field. They must now run cleanly against `location`.
"""
import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone

from inventory.models import Batch, Product, Category, Unit, Warehouse, StockMovement


def _product():
    cat = Category.objects.create(name=f'Cat {uuid.uuid4().hex[:6]}')
    unit = Unit.objects.create(name=f'Unit {uuid.uuid4().hex[:6]}', symbol='U')
    return Product.objects.create(
        name='P', generic_name='G', brand_name='B', category=cat, unit=unit,
        strength='100mg', form='Tablet', manufacturer='M',
        barcode=f'BC{uuid.uuid4().hex[:10]}', sku=f'SKU{uuid.uuid4().hex[:8]}',
    )


def _batch(product, wh, qty=Decimal('100.00')):
    return Batch.objects.create(
        product=product, batch_number=f'B-{uuid.uuid4().hex[:8]}',
        manufacturing_date=timezone.now().date() - timedelta(days=30),
        expiry_date=timezone.now().date() + timedelta(days=10),
        purchase_price=Decimal('10.00'), sale_price=Decimal('15.00'),
        quantity=qty, remaining_quantity=qty, location=str(wh.id),
    )


@pytest.mark.django_db
def test_inventory_valuation_report_runs():
    from accounting.services.advanced_reports import AdvancedReportsService
    wh = Warehouse.objects.create(name='WH', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    p = _product()
    _batch(p, wh, qty=Decimal('100.00'))  # purchase_price 10.00 -> value 1000.00
    report = AdvancedReportsService.get_inventory_valuation()
    assert isinstance(report, dict)
    # Previously crashed twice: select_related('warehouse') then batch.cost_price.
    # Value must be computed from batch.purchase_price (10.00) * remaining (100).
    assert report['total_value'] == pytest.approx(1000.0)
    product = report['products'][0]
    assert product['warehouse'] == str(wh.id)
    assert product['avg_cost'] == pytest.approx(10.0)
    # Per-batch cost_price is now sourced from batch.purchase_price.
    assert product['batches'][0]['cost_price'] == pytest.approx(10.0)


@pytest.mark.django_db
def test_low_stock_notification_job_runs():
    from security.notification_service import check_low_stock
    wh = Warehouse.objects.create(name='WH', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    p = _product()
    _batch(p, wh, qty=Decimal('1.00'))  # below default threshold
    # Previously raised FieldError on select_related('warehouse').
    created = check_low_stock()
    assert isinstance(created, int)


@pytest.mark.django_db
def test_expiring_batches_notification_job_runs():
    from security.notification_service import check_expiring_batches
    wh = Warehouse.objects.create(name='WH', code=f'WH{uuid.uuid4().hex[:4]}'.upper())
    p = _product()
    b = _batch(p, wh)
    # Force expiry exactly 7 days out (one of the checked windows).
    b.expiry_date = timezone.now().date() + timedelta(days=7)
    b.save(update_fields=['expiry_date'])
    created = check_expiring_batches()
    assert isinstance(created, int)
