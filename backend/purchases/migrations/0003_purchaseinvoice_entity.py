"""
Migration to add entity_id to PurchaseInvoice for multi-company support.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0002_purchaseinvoice_journal_entry_id'),
        ('entities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseinvoice',
            name='entity',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name='purchase_invoices',
                to='entities.Entity',
                verbose_name='Company/Entity'
            ),
        ),
    ]