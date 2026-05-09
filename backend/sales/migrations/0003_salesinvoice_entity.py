"""
Migration to add entity_id to SalesInvoice for multi-company support.
"""

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_salesinvoice_journal_entry_id'),
        ('entities', '0001_initial'),  # Add explicit dependency
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoice',
            name='entity',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name='sales_invoices',
                to='entities.Entity',
                verbose_name='Company/Entity'
            ),
        ),
    ]