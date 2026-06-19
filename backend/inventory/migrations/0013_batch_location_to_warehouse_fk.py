"""
Data + Schema migration: Convert Batch.location CharField to Batch.warehouse ForeignKey.

Step 1: Drop old index on location column (SQLite needs this before RemoveField)
Step 2: Add nullable warehouse FK field
Step 3: Populate warehouse from location string UUID values
Step 4: Remove old location CharField
"""
import uuid
import logging
from django.db import migrations, models
import django.db.models.deletion

logger = logging.getLogger('erp.migrations')


def forwards(apps, schema_editor):
    """Convert Batch.location string UUIDs to Batch.warehouse FK references."""
    Batch = apps.get_model('inventory', 'Batch')
    Warehouse = apps.get_model('inventory', 'Warehouse')

    # Build a lookup: string UUID -> Warehouse instance
    warehouse_cache = {}
    total = Batch.objects.count()
    converted = 0
    skipped = 0

    for batch in Batch.objects.all().iterator():
        location_value = batch.location  # old CharField value
        if not location_value:
            skipped += 1
            continue

        # Try to parse as UUID and look up warehouse
        try:
            wh_uuid = uuid.UUID(str(location_value))
        except (ValueError, AttributeError):
            # Not a valid UUID string -- skip
            skipped += 1
            continue

        if wh_uuid not in warehouse_cache:
            try:
                warehouse_cache[wh_uuid] = Warehouse.objects.get(id=wh_uuid)
            except Warehouse.DoesNotExist:
                warehouse_cache[wh_uuid] = None
                skipped += 1
                continue

        warehouse = warehouse_cache[wh_uuid]
        if warehouse is None:
            skipped += 1
            continue

        Batch.objects.filter(id=batch.id).update(warehouse=warehouse)
        converted += 1

    logger.info(
        "Batch.location -> Batch.warehouse migration: "
        "%d converted, %d skipped, %d total",
        converted, skipped, total,
    )


def backwards(apps, schema_editor):
    """No-op: we cannot reliably convert FK back to string UUID without losing data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_stockmovement_created_by'),
    ]

    operations = [
        # Step 1: Drop old index on location column before removing the field
        migrations.RemoveIndex(
            model_name='batch',
            name='inventory_b_locatio_5ba194_idx',
        ),
        # Step 2: Add nullable warehouse FK
        migrations.AddField(
            model_name='batch',
            name='warehouse',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='batches',
                to='inventory.warehouse',
                verbose_name='Warehouse',
            ),
        ),
        # Step 3: Data migration -- populate warehouse from location string
        migrations.RunPython(forwards, migrations.RunPython.noop),
        # Step 4: Remove old location field
        migrations.RemoveField(
            model_name='batch',
            name='location',
        ),
    ]
