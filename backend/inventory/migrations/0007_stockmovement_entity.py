"""
Migration to add entity_id to StockMovement for multi-company support.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_add_warehouse_transfer'),
        ('entities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovement',
            name='entity',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name='stock_movements',
                to='entities.Entity',
                verbose_name='Company/Entity'
            ),
        ),
    ]